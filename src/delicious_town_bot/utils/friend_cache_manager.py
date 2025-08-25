from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from src.delicious_town_bot.db.session import DBSession
from src.delicious_town_bot.db.models import FriendCache, Account
from src.delicious_town_bot.actions.friend import FriendActions


class FriendCacheManager:
    """好友缓存管理器，用于缓存和管理好友数据"""

    def __init__(self):
        pass

    @contextmanager
    def get_db_session(self):
        """获取数据库会话上下文管理器"""
        session = DBSession()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_cached_friends(self, account_id: int, max_age_hours: int = 24) -> Optional[List[Dict[str, Any]]]:
        """
        从缓存获取好友列表
        :param account_id: 账号ID
        :param max_age_hours: 缓存最大有效时间（小时）
        :return: 好友列表或None
        """
        with self.get_db_session() as session:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # 查询缓存的好友数据
            cached_friends = session.query(FriendCache).filter(
                FriendCache.account_id == account_id,
                FriendCache.last_updated >= cutoff_time
            ).all()
            
            if not cached_friends:
                return None
            
            # 转换为标准格式
            friends_list = []
            for friend in cached_friends:
                friends_list.append({
                    'id': friend.friend_id,
                    'name': friend.friend_name,
                    'level': friend.friend_level,
                    'avatar': friend.friend_avatar
                })
            
            print(f"[Cache] 从缓存获取到 {len(friends_list)} 个好友 (账号ID: {account_id})")
            return friends_list

    def update_friends_cache(self, account_id: int, friends_data: List[Dict[str, Any]], key: str, cookie: Optional[Dict[str, str]] = None) -> bool:
        """
        更新好友缓存，通过用户卡片API获取每个好友的真正餐厅ID
        :param account_id: 账号ID
        :param friends_data: 好友数据列表（包含用户ID）
        :param key: 当前账号的key，用于调用用户卡片API
        :param cookie: 当前账号的cookie
        :return: 是否成功
        """
        try:
            with self.get_db_session() as session:
                # 删除旧缓存
                session.query(FriendCache).filter(
                    FriendCache.account_id == account_id
                ).delete()
                
                # 通过用户卡片API获取每个好友的餐厅ID
                from src.delicious_town_bot.actions.user_card import UserCardAction
                user_card_action = UserCardAction(key=key, cookie=cookie)
                
                now = datetime.now()
                cached_friends = []
                successful_count = 0
                
                print(f"[Cache] 开始获取 {len(friends_data)} 个好友的真正餐厅ID...")
                
                for i, friend in enumerate(friends_data):
                    user_id = friend.get('id')  # 这是用户ID，不是餐厅ID
                    friend_name = friend.get('name', '未知好友')
                    
                    try:
                        # 通过用户卡片API获取真正的餐厅ID
                        card_info = user_card_action.get_user_card(str(user_id))
                        
                        if card_info.get('success'):
                            restaurant_info = card_info['restaurant_info']
                            restaurant_id = restaurant_info.get('id')  # 真正的餐厅ID
                            restaurant_name = restaurant_info.get('name', friend_name)
                            
                            cache_entry = FriendCache(
                                account_id=account_id,
                                friend_id=restaurant_id,  # 存储真正的餐厅ID
                                friend_name=restaurant_name,  # 使用餐厅名称
                                friend_level=friend.get('level'),
                                friend_avatar=friend.get('avatar'),
                                last_updated=now
                            )
                            cached_friends.append(cache_entry)
                            session.add(cache_entry)
                            successful_count += 1
                            
                            # 显示详细进度（每10个或重要节点）
                            if (i + 1) % 10 == 0 or (i + 1) == len(friends_data) or (i + 1) <= 5:
                                print(f"[Cache] [{i + 1}/{len(friends_data)}] {friend_name} (用户ID:{user_id}) -> 餐厅ID:{restaurant_id}, 餐厅名:{restaurant_name}")
                        else:
                            print(f"[Warning] [{i + 1}/{len(friends_data)}] 获取 {friend_name} 的餐厅ID失败: {card_info.get('message', '未知错误')}")
                            
                            # 即使失败也保存基础信息，使用用户ID作为fallback
                            cache_entry = FriendCache(
                                account_id=account_id,
                                friend_id=user_id,  # fallback到用户ID
                                friend_name=friend_name,
                                friend_level=friend.get('level'),
                                friend_avatar=friend.get('avatar'),
                                last_updated=now
                            )
                            cached_friends.append(cache_entry)
                            session.add(cache_entry)
                            
                    except Exception as e:
                        print(f"[Error] [{i + 1}/{len(friends_data)}] 处理好友 {friend_name} 时发生异常: {e}")
                        
                        # 异常时也保存基础信息
                        cache_entry = FriendCache(
                            account_id=account_id,
                            friend_id=user_id,  # fallback到用户ID
                            friend_name=friend_name,
                            friend_level=friend.get('level'),
                            friend_avatar=friend.get('avatar'),
                            last_updated=now
                        )
                        cached_friends.append(cache_entry)
                        session.add(cache_entry)
                    
                    # 避免API调用过快，每5个请求暂停一下
                    if (i + 1) % 5 == 0:
                        import time
                        time.sleep(0.5)
                
                session.commit()
                print(f"[Cache] 缓存更新完成: 总计 {len(cached_friends)} 个好友, 成功获取餐厅ID: {successful_count} 个 (账号ID: {account_id})")
                return True
                
        except Exception as e:
            print(f"[Error] 更新好友缓存失败: {e}")
            return False

    def get_friends_with_cache(self, account_id: int, key: str, cookie: Optional[Dict[str, str]] = None, 
                             force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        获取好友列表（优先使用缓存）
        :param account_id: 账号ID
        :param key: 账号key
        :param cookie: 账号cookie
        :param force_refresh: 是否强制刷新
        :return: 好友列表
        """
        # 如果不强制刷新，先尝试从缓存获取
        if not force_refresh:
            cached_friends = self.get_cached_friends(account_id)
            if cached_friends:
                return cached_friends
        
        # 缓存未命中或强制刷新，从API获取
        print(f"[Cache] 缓存未命中或强制刷新，从API获取好友列表 (账号ID: {account_id})")
        try:
            friend_action = FriendActions(key=key, cookie=cookie)
            fresh_friends = friend_action.get_all_friends()
            
            if fresh_friends:
                # 更新缓存，传递key和cookie参数
                cache_success = self.update_friends_cache(account_id, fresh_friends, key, cookie)
                if cache_success:
                    # 缓存更新成功后，重新从缓存获取（这样返回的是带有真正餐厅ID的数据）
                    cached_friends = self.get_cached_friends(account_id)
                    if cached_friends:
                        return cached_friends
                
                # 如果缓存更新失败，返回原始数据
                print(f"[Warning] 缓存更新失败，返回原始好友数据")
                return fresh_friends
            else:
                print(f"[Error] 从API获取好友列表失败 (账号ID: {account_id})")
                return None
                
        except Exception as e:
            print(f"[Error] 获取好友列表时发生异常: {e}")
            return None

    def refresh_all_accounts_friends_cache(self, account_manager) -> Dict[str, Any]:
        """
        刷新所有账号的好友缓存
        :param account_manager: AccountManager实例
        :return: 刷新结果统计
        """
        print("[*] 开始刷新所有账号的好友缓存...")
        
        accounts = account_manager.list_accounts()
        
        # 立即提取所有账号的属性避免会话分离问题
        accounts_data = []
        for account in accounts:
            try:
                account_data = {
                    'id': account.id,
                    'username': account.username,
                    'key': account.key,
                    'cookie': account.cookie
                }
                accounts_data.append(account_data)
            except Exception as e:
                print(f"[Warning] 提取账号 {getattr(account, 'username', '未知')} 属性失败: {e}")
        
        results = {
            "total_accounts": len(accounts_data),
            "successful_refreshes": 0,
            "failed_refreshes": 0,
            "account_details": []
        }
        
        for account_data in accounts_data:
            
            if not account_data['key']:
                print(f"[Skip] 账号 {account_data['username']} 没有Key，跳过")
                continue
                
            print(f"[*] 刷新账号 {account_data['username']} 的好友缓存...")
            cookie_dict = {"PHPSESSID": account_data['cookie']} if account_data['cookie'] else None
            
            friends = self.get_friends_with_cache(
                account_id=account_data['id'],
                key=account_data['key'],
                cookie=cookie_dict,
                force_refresh=True
            )
            
            if friends:
                results["successful_refreshes"] += 1
                detail = {
                    "account_name": account_data['username'],
                    "friends_count": len(friends),
                    "success": True,
                    "message": f"成功缓存 {len(friends)} 个好友"
                }
                print(f"[Success] {account_data['username']}: 缓存了 {len(friends)} 个好友")
            else:
                results["failed_refreshes"] += 1
                detail = {
                    "account_name": account_data['username'],
                    "friends_count": 0,
                    "success": False,
                    "message": "获取好友列表失败"
                }
                print(f"[Failed] {account_data['username']}: 获取好友列表失败")
            
            results["account_details"].append(detail)
        
        # 输出统计结果
        success_rate = (results["successful_refreshes"] / results["total_accounts"] * 100) if results["total_accounts"] > 0 else 0
        
        print(f"\n[Summary] 好友缓存刷新完成:")
        print(f"  处理账号数: {results['total_accounts']}")
        print(f"  成功刷新: {results['successful_refreshes']}")
        print(f"  失败: {results['failed_refreshes']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return results

    def clean_old_cache(self, max_age_days: int = 7) -> int:
        """
        清理过期的缓存数据
        :param max_age_days: 缓存保留天数
        :return: 清理的记录数
        """
        try:
            with self.get_db_session() as session:
                cutoff_time = datetime.now() - timedelta(days=max_age_days)
                
                deleted_count = session.query(FriendCache).filter(
                    FriendCache.last_updated < cutoff_time
                ).delete()
                
                session.commit()
                print(f"[Cache] 清理了 {deleted_count} 条过期的好友缓存记录")
                return deleted_count
                
        except Exception as e:
            print(f"[Error] 清理过期缓存失败: {e}")
            return 0
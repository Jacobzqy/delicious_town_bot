"""
餐厅ID管理器
专门用于获取和管理账号的res_id（餐厅ID），避免重复API调用
"""
from typing import List, Dict, Any, Optional
from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.user_card import UserCardAction


class RestaurantIdManager:
    """餐厅ID管理器，用于批量获取和存储账号的res_id"""
    
    def __init__(self):
        self.account_manager = AccountManager()
    
    def get_account_restaurant_id(self, account_id: int, key: str, cookie: str) -> Optional[Dict[str, Any]]:
        """
        获取单个账号的餐厅ID
        :param account_id: 账号ID
        :param key: 账号key
        :param cookie: 账号cookie
        :return: 餐厅信息或None
        """
        try:
            cookie_dict = {"PHPSESSID": cookie}
            user_card_action = UserCardAction(key=key, cookie=cookie_dict)
            
            print(f"[*] 正在获取账号ID {account_id} 的餐厅信息...")
            card_info = user_card_action.get_user_card('')
            
            if card_info.get('success'):
                restaurant_info = card_info['restaurant_info']
                return {
                    'res_id': restaurant_info.get('id'),
                    'res_name': restaurant_info.get('name'),
                    'level': restaurant_info.get('level'),
                    'success': True
                }
            else:
                print(f"[Error] 获取账号ID {account_id} 餐厅信息失败: {card_info.get('message')}")
                return {'success': False, 'error': card_info.get('message')}
                
        except Exception as e:
            print(f"[Error] 获取账号ID {account_id} 餐厅信息异常: {e}")
            return {'success': False, 'error': str(e)}
    
    def batch_update_restaurant_ids(self, max_accounts: int = None) -> Dict[str, Any]:
        """
        批量更新所有账号的餐厅ID到数据库
        :param max_accounts: 最大处理账号数，None表示处理所有账号
        :return: 处理结果统计
        """
        print("[*] 开始批量更新账号餐厅ID...")
        
        # 获取所有账号
        accounts = self.account_manager.list_accounts()
        if max_accounts:
            accounts = accounts[:max_accounts]
        
        # 立即提取账号属性避免会话分离问题
        accounts_data = []
        for account in accounts:
            try:
                account_data = {
                    'id': account.id,
                    'username': account.username,
                    'key': account.key,
                    'cookie': account.cookie,
                    'current_restaurant': account.restaurant
                }
                accounts_data.append(account_data)
            except Exception as e:
                print(f"[Warning] 提取账号属性失败: {e}")
        
        results = {
            "total_accounts": len(accounts_data),
            "successful_updates": 0,
            "failed_updates": 0,
            "skipped_accounts": 0,
            "account_details": []
        }
        
        for i, account_data in enumerate(accounts_data):
            username = account_data['username']
            account_id = account_data['id']
            key = account_data['key']
            cookie = account_data['cookie']
            
            print(f"[*] [{i+1}/{len(accounts_data)}] 处理账号: {username}")
            
            if not key:
                print(f"[Skip] 账号 {username} 没有Key，跳过")
                results["skipped_accounts"] += 1
                results["account_details"].append({
                    "username": username,
                    "success": False,
                    "message": "没有Key",
                    "res_id": None
                })
                continue
            
            # 获取餐厅ID
            restaurant_info = self.get_account_restaurant_id(account_id, key, cookie)
            
            if restaurant_info and restaurant_info.get('success'):
                res_id = restaurant_info['res_id']
                res_name = restaurant_info['res_name']
                
                # 更新数据库
                try:
                    self.account_manager.update_account(
                        account_id=account_id,
                        restaurant=str(res_id)  # 存储数字格式的res_id
                    )
                    success = True
                    
                    if success:
                        results["successful_updates"] += 1
                        print(f"[Success] {username}: 餐厅ID={res_id}, 名称={res_name}")
                        results["account_details"].append({
                            "username": username,
                            "success": True,
                            "message": f"餐厅ID={res_id}, 名称={res_name}",
                            "res_id": res_id,
                            "res_name": res_name
                        })
                    else:
                        results["failed_updates"] += 1
                        print(f"[Error] {username}: 数据库更新失败")
                        results["account_details"].append({
                            "username": username,
                            "success": False,
                            "message": "数据库更新失败",
                            "res_id": res_id
                        })
                        
                except Exception as e:
                    results["failed_updates"] += 1
                    print(f"[Error] {username}: 数据库更新异常 - {e}")
                    results["account_details"].append({
                        "username": username,
                        "success": False,
                        "message": f"数据库更新异常: {e}",
                        "res_id": res_id
                    })
            else:
                results["failed_updates"] += 1
                error_msg = restaurant_info.get('error', '未知错误') if restaurant_info else '获取餐厅信息失败'
                print(f"[Failed] {username}: {error_msg}")
                results["account_details"].append({
                    "username": username,
                    "success": False,
                    "message": error_msg,
                    "res_id": None
                })
            
            # 避免请求过快
            if i < len(accounts_data) - 1:
                import time
                time.sleep(0.3)
        
        # 生成统计报告
        success_rate = (results["successful_updates"] / results["total_accounts"] * 100) if results["total_accounts"] > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"📊 餐厅ID批量更新完成:")
        print(f"  总账号数: {results['total_accounts']}")
        print(f"  成功更新: {results['successful_updates']}")
        print(f"  更新失败: {results['failed_updates']}")
        print(f"  跳过账号: {results['skipped_accounts']}")
        print(f"  成功率: {success_rate:.1f}%")
        print(f"{'='*60}")
        
        results["success_rate"] = success_rate
        results["summary"] = f"更新完成: 成功{results['successful_updates']}个, 失败{results['failed_updates']}个, 成功率{success_rate:.1f}%"
        
        return results
    
    def get_accounts_with_restaurant_ids(self, max_accounts: int = None) -> List[Dict[str, Any]]:
        """
        获取所有账号及其餐厅ID（从数据库读取）
        :param max_accounts: 最大账号数
        :return: 包含餐厅ID的账号列表
        """
        accounts = self.account_manager.list_accounts()
        if max_accounts:
            accounts = accounts[:max_accounts]
        
        accounts_with_res_id = []
        for account in accounts:
            try:
                account_data = {
                    'id': account.id,
                    'username': account.username,
                    'key': account.key,
                    'cookie': account.cookie,
                    'res_id': account.restaurant,  # 从数据库读取res_id
                    'has_res_id': bool(account.restaurant)
                }
                accounts_with_res_id.append(account_data)
            except Exception as e:
                print(f"[Warning] 提取账号 {getattr(account, 'username', '未知')} 信息失败: {e}")
        
        return accounts_with_res_id
    
    def check_accounts_restaurant_ids(self) -> Dict[str, Any]:
        """
        检查所有账号的餐厅ID状态
        :return: 检查结果统计
        """
        accounts = self.account_manager.list_accounts()
        
        results = {
            "total_accounts": len(accounts),
            "accounts_with_res_id": 0,
            "accounts_without_res_id": 0,
            "account_details": []
        }
        
        for account in accounts:
            try:
                username = account.username
                res_id = account.restaurant
                has_res_id = bool(res_id)
                
                if has_res_id:
                    results["accounts_with_res_id"] += 1
                else:
                    results["accounts_without_res_id"] += 1
                
                results["account_details"].append({
                    "username": username,
                    "res_id": res_id,
                    "has_res_id": has_res_id
                })
                
            except Exception as e:
                print(f"[Warning] 检查账号信息失败: {e}")
        
        return results


# ==============================================================================
#  独立测试脚本
# ==============================================================================
if __name__ == '__main__':
    manager = RestaurantIdManager()
    
    print("=" * 20 + " 餐厅ID管理器测试 " + "=" * 20)
    
    # 检查当前状态
    print("\n--- 1. 检查账号餐厅ID状态 ---")
    status = manager.check_accounts_restaurant_ids()
    print(f"总账号数: {status['total_accounts']}")
    print(f"有餐厅ID: {status['accounts_with_res_id']}")
    print(f"无餐厅ID: {status['accounts_without_res_id']}")
    
    # 批量更新餐厅ID
    print("\n--- 2. 批量更新餐厅ID ---")
    results = manager.batch_update_restaurant_ids(max_accounts=3)
    
    print("\n--- 3. 更新后状态检查 ---")
    updated_status = manager.check_accounts_restaurant_ids()
    print(f"更新后有餐厅ID: {updated_status['accounts_with_res_id']}")
    
    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
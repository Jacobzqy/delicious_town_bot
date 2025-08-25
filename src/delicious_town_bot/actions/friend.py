import re
import os
import time
import json
from dotenv import load_dotenv
from typing import Tuple, Dict, Any, Union, Optional, List

# 确保能正确导入基类和自定义异常
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class FriendActions(BaseAction):
    """封装所有与好友相关的游戏操作，包括好友列表、换菜等功能。"""

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        """
        初始化好友操作类。
        使用通用的 g=Res 作为 base_url，以便调用不同的模块(m=Friend, m=Food, m=CupboardGrid)。
        """
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key, base_url, cookie)

    # --- 好友列表相关操作 ---

    def get_friend_list(self, page: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        获取好友列表。
        :param page: 页码，从1开始
        :return: 好友列表，包含id、name、level、avatar等信息，或失败时返回 None
        """
        print(f"[*] 正在获取第 {page} 页好友列表...")
        try:
            response = self.get(action_path=f"m=Friend&a=get_list&page={page}")
            
            friends_data = response.get("data", [])
            if not isinstance(friends_data, list):
                print(f"[Warning] API返回的data字段不是列表类型: {type(friends_data)}")
                return None
            
            print(f"[Info] 获取到 {len(friends_data)} 个好友")
            return friends_data
            
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 获取好友列表失败: {e}")
            return None

    def get_all_friends(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取所有好友列表（自动翻页）。
        :return: 完整的好友列表，或失败时返回 None
        """
        print("[*] 正在获取所有好友列表...")
        all_friends = []
        page = 1
        max_pages = 100  # 防止无限循环的保险阈值
        
        while page <= max_pages:
            friends_on_page = self.get_friend_list(page)
            
            if friends_on_page is None:
                print(f"[Error] 获取第 {page} 页好友失败，停止翻页")
                return None if page == 1 else all_friends
            
            if not friends_on_page:
                print(f"[Info] 第 {page} 页为空，已获取所有好友")
                break
            
            # 检查是否有重复的好友（用于判断是否到达最后一页）
            existing_ids = {friend["id"] for friend in all_friends}
            new_friends = [f for f in friends_on_page if f["id"] not in existing_ids]
            
            if not new_friends:
                print(f"[Info] 第 {page} 页没有新好友，已获取所有好友")
                break
            
            all_friends.extend(new_friends)
            print(f"[Info] 第 {page} 页获取到 {len(new_friends)} 个新好友，累计 {len(all_friends)} 个")
            
            page += 1
            time.sleep(0.5)  # 避免请求过快
        
        print(f"[Success] 总共获取到 {len(all_friends)} 个好友")
        return all_friends

    # --- 好友食材查询相关操作 ---

    def query_friend_food(self, food_code: str, level: str) -> Optional[Dict[str, Any]]:
        """
        查询哪些好友拥有指定食材。
        :param food_code: 食材代码
        :param level: 食材等级
        :return: 包含 friend_list 和 food_list 的字典，或失败时返回 None
        """
        print(f"[*] 正在查询好友的食材: code={food_code}, level={level}...")
        
        try:
            payload = {
                "food_code": str(food_code),
                "level": str(level)
            }
            
            response = self.post(action_path="m=Food&a=get_friend_food", data=payload)
            
            result_data = response.get("data", {})
            if not isinstance(result_data, dict):
                print(f"[Warning] API返回的data字段不是字典类型: {type(result_data)}")
                return None
            
            friend_list = result_data.get("friend_list", [])
            food_list = result_data.get("food_list", [])
            
            print(f"[Info] 找到 {len(friend_list)} 个好友拥有该食材")
            
            return {
                "friend_list": friend_list,
                "food_list": food_list
            }
            
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 查询好友食材失败: {e}")
            return None

    def find_friends_with_food(self, food_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        根据食材名称查找拥有该食材的好友。
        :param food_name: 食材名称
        :return: 好友列表，包含食材数量等信息，或失败时返回 None
        """
        print(f"[*] 正在查找拥有 '{food_name}' 的好友...")
        
        # 首先从foods.json中查找对应的食材代码和等级
        food_info = self._find_food_by_name(food_name)
        if not food_info:
            print(f"[Error] 未找到食材 '{food_name}' 的信息")
            return None
        
        print(f"[Info] 找到食材信息: code={food_info['code']}, level={food_info['level']}")
        
        # 查询好友食材
        result = self.query_friend_food(food_info['code'], food_info['level'])
        if result is None:
            return None
        
        return result.get("friend_list", [])

    def _find_food_by_name(self, food_name: str) -> Optional[Dict[str, str]]:
        """
        从foods.json中查找食材信息。
        :param food_name: 食材名称
        :return: 包含code和level的字典，或未找到时返回None
        """
        try:
            # 读取食材数据文件
            foods_file_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "assets", "foods.json"
            )
            
            with open(foods_file_path, 'r', encoding='utf-8') as f:
                foods_data = json.load(f)
            
            # 在RECORDS中查找匹配的食材
            for record in foods_data.get("RECORDS", []):
                if record.get("name") == food_name:
                    return {
                        "code": record.get("code"),
                        "level": record.get("level"),
                        "name": record.get("name"),
                        "gold": record.get("gold"),
                        "descript": record.get("descript")
                    }
            
            return None
            
        except Exception as e:
            print(f"[Error] 读取食材数据失败: {e}")
            return None

    # --- 好友换菜相关操作 ---

    def exchange_food_with_friend(self, friend_res_id: str, friend_food_code: str, my_food_code: str) -> Tuple[bool, str]:
        """
        与好友交换食材。
        :param friend_res_id: 好友的餐厅ID
        :param friend_food_code: 好友的食材代码（我想要的）
        :param my_food_code: 我的食材代码（我要给出的）
        :return: (是否成功, 消息)
        """
        print(f"[*] 正在与好友 {friend_res_id} 交换食材: 我的{my_food_code} <-> 好友的{friend_food_code}...")
        
        try:
            payload = {
                "res_id": str(friend_res_id),
                "friend_code": str(friend_food_code),
                "my_code": str(my_food_code)
            }
            
            response = self.post(action_path="m=CupboardGrid&a=friend_exchange_food", data=payload)
            msg = response.get("msg", "未知消息").replace("<br>", " / ")
            
            print(f"[Success] 交换成功: {msg}")
            return True, msg
            
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 交换食材失败: {e}")
            return False, str(e)

    def batch_exchange_food(self, target_food_name: str, offer_food_name: str, max_exchanges: int = 10) -> Dict[str, Any]:
        """
        批量与好友交换食材。
        :param target_food_name: 想要获得的食材名称
        :param offer_food_name: 愿意给出的食材名称
        :param max_exchanges: 最大交换次数
        :return: 交换结果统计
        """
        print(f"[*] 开始批量交换: 用 '{offer_food_name}' 换取 '{target_food_name}'，最多 {max_exchanges} 次...")
        
        results = {
            "total_attempts": 0,
            "successful_exchanges": 0,
            "failed_exchanges": 0,
            "exchange_details": []
        }
        
        # 1. 查找拥有目标食材的好友
        friends_with_target = self.find_friends_with_food(target_food_name)
        if not friends_with_target:
            print(f"[Info] 没有好友拥有 '{target_food_name}'")
            return results
        
        # 2. 获取食材代码
        target_food_info = self._find_food_by_name(target_food_name)
        offer_food_info = self._find_food_by_name(offer_food_name)
        
        if not target_food_info or not offer_food_info:
            print(f"[Error] 无法找到食材信息")
            return results
        
        print(f"[Info] 找到 {len(friends_with_target)} 个好友拥有目标食材")
        
        # 3. 逐个尝试交换
        for friend in friends_with_target[:max_exchanges]:
            results["total_attempts"] += 1
            
            friend_name = friend.get("res_name", "未知好友")
            friend_id = friend.get("res_id")
            available_count = friend.get("num", 0)
            
            print(f"[*] 尝试与 '{friend_name}' 交换 (拥有 {available_count} 个)...")
            
            success, message = self.exchange_food_with_friend(
                friend_id, 
                target_food_info["code"],
                offer_food_info["code"]
            )
            
            detail = {
                "friend_name": friend_name,
                "friend_id": friend_id,
                "success": success,
                "message": message,
                "available_count": available_count
            }
            results["exchange_details"].append(detail)
            
            if success:
                results["successful_exchanges"] += 1
                print(f"[Success] 与 '{friend_name}' 交换成功")
            else:
                results["failed_exchanges"] += 1
                print(f"[Failed] 与 '{friend_name}' 交换失败: {message}")
            
            time.sleep(1)  # 避免请求过快
            
            if results["total_attempts"] >= max_exchanges:
                break
        
        # 4. 输出统计结果
        success_rate = (results["successful_exchanges"] / results["total_attempts"] * 100) if results["total_attempts"] > 0 else 0
        
        print(f"\n[Summary] 批量交换完成:")
        print(f"  总尝试: {results['total_attempts']}")
        print(f"  成功: {results['successful_exchanges']}")
        print(f"  失败: {results['failed_exchanges']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return results

    def get_user_restaurant_id(self) -> Optional[str]:
        """
        获取当前用户的餐厅ID
        :return: 餐厅ID字符串，或失败时返回None
        """
        print("[*] 正在获取当前用户的餐厅信息...")
        try:
            # 方法1: 尝试从用户卡片接口获取餐厅ID
            from src.delicious_town_bot.actions.user_card import UserCardAction
            user_card_action = UserCardAction(key=self.key, cookie=self.cookie)
            card_info = user_card_action.get_user_card("")  # 空字符串表示获取自己的信息
            
            restaurant_info = card_info.get("restaurant_info", {})
            res_id = restaurant_info.get("id")
            
            if res_id:
                print(f"[Success] 通过用户卡片接口获取到餐厅ID: {res_id}")
                return str(res_id)
            
            # 方法2: 尝试从好友列表接口获取（好友列表中会有自己的餐厅信息）
            print("[*] 尝试从好友列表获取餐厅ID...")
            friends = self.get_friend_list(page=1)
            if friends and len(friends) > 0:
                # 通常第一个好友就是自己，或者可以从好友申请中找到自己
                for friend in friends[:3]:  # 检查前几个好友
                    friend_id = friend.get("id")
                    if friend_id:
                        print(f"[Info] 尝试使用好友ID作为餐厅ID: {friend_id}")
                        return str(friend_id)
            
            # 方法3: 尝试直接从基本用户信息获取
            print("[*] 尝试从基本用户信息获取...")
            response = self.get(action_path="m=Index&a=index")
            user_data = response.get("data", {})
            res_id = user_data.get("res_id") or user_data.get("restaurant_id") or user_data.get("id")
            
            if res_id:
                print(f"[Success] 通过基本信息获取到餐厅ID: {res_id}")
                return str(res_id)
            
            print("[Warning] 所有方法都无法获取餐厅ID")
            return None
                
        except Exception as e:
            print(f"[Error] 获取用户餐厅信息失败: {e}")
            return None

    # --- 好友互动功能（原有功能保留） ---

    def use_activation_code(self, activation_code: str) -> Tuple[bool, str]:
        """使用激活码，通常用于新手开启社交功能。"""
        print(f"[*] 正在尝试使用激活码: {activation_code}...")
        payload = {"code": activation_code}
        try:
            response = self.post(action_path="m=Index&a=bind", data=payload)
            msg = response.get("msg", "未知成功消息")
            print(f"[Success] {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 使用激活码失败: {e}")
            return False, str(e)

    def add_friend(self, friend_res_id: Union[str, int]) -> Tuple[bool, str]:
        """向指定ID的用户发送好友申请。"""
        print(f"[*] 正在向餐厅 ID: {friend_res_id} 发送好友申请...")
        payload = {"res_id": str(friend_res_id)}
        try:
            response = self.post(action_path="m=Friend&a=apply_friend", data=payload)
            msg = response.get("msg", "未知成功消息")
            print(f"[Success] {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 添加好友失败: {e}")
            return False, str(e)

    def get_friend_requests(self, max_pages: int = 20) -> Optional[List[Dict[str, Any]]]:
        """获取所有收到的好友申请列表（支持分页）。"""
        print("[*] 正在获取收到的好友申请列表...")
        all_requests = []
        for page in range(1, max_pages + 1):
            try:
                response = self.get(action_path="m=Friend&a=get_apply_list", params={"page": str(page)})
                requests_on_page = response.get("data", [])
                if not requests_on_page: break
                all_requests.extend(requests_on_page)
            except (BusinessLogicError, ConnectionError) as e:
                print(f"[Error] 获取好友申请列表第 {page} 页失败: {e}")
                return None
        print(f"[Info] 成功获取到 {len(all_requests)} 条好友申请。")
        return all_requests

    def handle_friend_request(self, apply_id: Union[str, int], accept: bool = True) -> Tuple[bool, str]:
        """处理指定的好友申请（同意或拒绝）。"""
        action_text = "同意" if accept else "拒绝"
        action_type = "1" if accept else "2"  # 1=同意, 2=拒绝
        print(f"[*] 正在 {action_text} ID为 {apply_id} 的好友申请...")
        payload = {"apply_id": str(apply_id), "type": action_type}
        try:
            response = self.post(action_path="m=Friend&a=handleFriend", data=payload)
            msg = response.get("msg", "未知成功消息")
            print(f"[Success] {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 处理好友申请失败: {e}")
            return False, str(e)

    def batch_handle_friend_requests(self, accept_all: bool = True) -> Dict[str, Any]:
        """
        批量处理所有收到的好友申请
        :param accept_all: 是否全部同意（True）还是全部拒绝（False）
        :return: 处理结果统计
        """
        action_text = "同意" if accept_all else "拒绝"
        print(f"[*] 开始批量{action_text}好友申请...")
        
        results = {
            "total_requests": 0,
            "successful_handles": 0,
            "failed_handles": 0,
            "handle_details": []
        }
        
        # 1. 获取所有好友申请
        friend_requests = self.get_friend_requests()
        if not friend_requests:
            print("[Info] 没有收到好友申请")
            return results
        
        results["total_requests"] = len(friend_requests)
        print(f"[Info] 收到 {len(friend_requests)} 条好友申请，准备批量{action_text}")
        
        # 2. 逐个处理好友申请
        for i, request in enumerate(friend_requests):
            apply_id = request.get("id")
            apply_name = request.get("name", "未知用户")
            
            if not apply_id:
                print(f"[Skip] 好友申请缺少ID，跳过")
                continue
            
            print(f"[*] [{i+1}/{len(friend_requests)}] {action_text}来自 '{apply_name}' 的申请...")
            
            success, message = self.handle_friend_request(apply_id, accept_all)
            
            detail = {
                "apply_id": apply_id,
                "apply_name": apply_name,
                "action": action_text,
                "success": success,
                "message": message
            }
            results["handle_details"].append(detail)
            
            if success:
                results["successful_handles"] += 1
                print(f"[Success] {action_text}来自 '{apply_name}' 的申请成功")
            else:
                results["failed_handles"] += 1
                print(f"[Failed] {action_text}来自 '{apply_name}' 的申请失败: {message}")
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 3. 输出统计结果
        success_rate = (results["successful_handles"] / results["total_requests"] * 100) if results["total_requests"] > 0 else 0
        
        print(f"\n[Summary] 批量{action_text}好友申请完成:")
        print(f"  总申请数: {results['total_requests']}")
        print(f"  成功{action_text}: {results['successful_handles']}")
        print(f"  失败: {results['failed_handles']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return results

    def batch_handle_all_accounts_friend_requests(self, all_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量处理所有账号的好友申请
        :param all_accounts: 所有账号的列表
        :return: 处理结果统计
        """
        print(f"[*] 为 {len(all_accounts)} 个账号批量处理好友申请...")
        
        total_results = {
            "total_accounts": len(all_accounts),
            "processed_accounts": 0,
            "total_requests_handled": 0,
            "total_requests_successful": 0,
            "account_details": []
        }
        
        for i, account in enumerate(all_accounts):
            if not account.get('key'):
                print(f"[Skip] 账号 {account['username']} 没有Key，跳过")
                continue
            
            total_results["processed_accounts"] += 1
            current_username = account['username']
            
            print(f"[*] [{i+1}/{len(all_accounts)}] 处理账号 {current_username} 的好友申请...")
            
            try:
                # 使用当前账号创建FriendActions实例
                cookie_dict = {"PHPSESSID": account.get('cookie', '123')}
                friend_action = FriendActions(key=account['key'], cookie=cookie_dict)
                
                # 批量处理该账号的好友申请
                account_results = friend_action.batch_handle_friend_requests(accept_all=True)
                
                detail = {
                    "account_name": current_username,
                    "requests_handled": account_results.get("total_requests", 0),
                    "requests_successful": account_results.get("successful_handles", 0),
                    "requests_failed": account_results.get("failed_handles", 0),
                    "success": True
                }
                
                total_results["total_requests_handled"] += account_results.get("total_requests", 0)
                total_results["total_requests_successful"] += account_results.get("successful_handles", 0)
                
                if account_results.get("total_requests", 0) > 0:
                    print(f"[Success] {current_username}: 处理了 {account_results['total_requests']} 个申请，成功 {account_results['successful_handles']} 个")
                else:
                    print(f"[Info] {current_username}: 没有好友申请")
                
            except Exception as e:
                error_msg = f"处理好友申请时发生异常: {str(e)}"
                print(f"[Error] {current_username}: {error_msg}")
                detail = {
                    "account_name": current_username,
                    "requests_handled": 0,
                    "requests_successful": 0,
                    "requests_failed": 0,
                    "success": False,
                    "error": error_msg
                }
            
            total_results["account_details"].append(detail)
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 输出总体统计
        success_rate = (total_results["total_requests_successful"] / total_results["total_requests_handled"] * 100) if total_results["total_requests_handled"] > 0 else 0
        
        print(f"\n[Summary] 全账号好友申请处理完成:")
        print(f"  处理账号数: {total_results['processed_accounts']}/{total_results['total_accounts']}")
        print(f"  总申请数: {total_results['total_requests_handled']}")
        print(f"  成功处理: {total_results['total_requests_successful']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return total_results

    def get_friend_restaurant_info(self, friend_res_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        获取好友餐厅信息。
        :param friend_res_id: 好友餐厅ID
        :return: 餐厅信息字典，包含油量等信息，或失败时返回 None
        """
        print(f"[*] 正在获取好友 {friend_res_id} 的餐厅信息...")
        try:
            payload = {"res_id": str(friend_res_id)}
            response = self.post(action_path="m=Friend&a=getFriendInfo", data=payload)
            
            data = response.get("data", {})
            if not isinstance(data, dict):
                print(f"[Warning] API返回的data字段不是字典类型: {type(data)}")
                return None
            
            restaurant_info = {
                "bottle_num": data.get("bottle_num", 0),
                "res_id": friend_res_id
            }
            
            print(f"[Info] 获取好友餐厅信息成功: 油量 {restaurant_info['bottle_num']}")
            return restaurant_info
            
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 获取好友餐厅信息失败: {e}")
            return None

    def check_and_ensure_friendship(self, target_res_id: Union[str, int]) -> Tuple[bool, str]:
        """
        检查是否与目标用户是好友关系，如果不是则自动添加好友申请
        :param target_res_id: 目标用户的餐厅ID
        :return: (是否已建立好友关系, 消息)
        """
        target_res_id = str(target_res_id)
        
        # 1. 首先获取好友列表，检查是否已经是好友
        friends = self.get_all_friends()
        if friends:
            for friend in friends:
                if str(friend.get("id")) == target_res_id:
                    return True, f"用户 {target_res_id} 已经是好友"
        
        # 2. 如果不是好友，发送好友申请
        print(f"[*] 用户 {target_res_id} 不是好友，正在发送好友申请...")
        success, message = self.add_friend(target_res_id)
        if success:
            return True, f"已向用户 {target_res_id} 发送好友申请: {message}"
        else:
            return False, f"向用户 {target_res_id} 发送好友申请失败: {message}"
    
    def refill_oil_for_friend(self, friend_res_id: Union[str, int]) -> Tuple[bool, Union[str, Dict[str, int]]]:
        """为指定好友添油。"""
        print(f"[*] 正在为好友 {friend_res_id} 添油...")
        try:
            response = self.post(action_path="m=Friend&a=addFriendBottle", data={"res_id": str(friend_res_id)})
            msg = response.get("msg", "")
            details = self._parse_refill_oil_message(msg)
            print(f"[Success] {msg}")
            return True, details
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 为好友 {friend_res_id} 添油失败: {e}")
            return False, str(e)

    def _parse_refill_oil_message(self, msg: str) -> Dict[str, int]:
        """辅助方法，解析为好友添油成功的消息。"""
        details = {}
        # 更新正则表达式以匹配新的消息格式: "帮好友添油3740成功,金币-3740"
        oil_match = re.search(r"帮好友添油(\d+)成功", msg)
        if oil_match: 
            details['oil_added'] = int(oil_match.group(1))
        
        gold_match = re.search(r"金币-(\d+)", msg)
        if gold_match: 
            details['gold_cost'] = int(gold_match.group(1))
        
        if not details: 
            return {"raw_message": msg}
        return details

    def refill_oil_for_next_account(self, current_account_id: int, all_accounts: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        为当前账号的下一个小号添油（循环模式：1为2添，2为3添，...，最后一个为1添）
        :param current_account_id: 当前账号的ID
        :param all_accounts: 所有账号的列表，每个账号包含id, username, res_id等信息
        :return: (是否成功, 消息)
        """
        print(f"[*] 为账号ID {current_account_id} 查找下一个小号进行添油...")
        
        # 按ID排序账号列表
        sorted_accounts = sorted(all_accounts, key=lambda x: x['id'])
        
        # 找到当前账号的索引
        current_index = None
        for i, account in enumerate(sorted_accounts):
            if account['id'] == current_account_id:
                current_index = i
                break
        
        if current_index is None:
            return False, f"未找到账号ID {current_account_id}"
        
        # 计算下一个账号的索引（循环）
        next_index = (current_index + 1) % len(sorted_accounts)
        next_account = sorted_accounts[next_index]
        
        next_username = next_account['username']
        next_res_id = next_account.get('res_id')
        
        if not next_res_id:
            return False, f"下一个账号 {next_username} 没有餐厅ID信息"
        
        print(f"[*] 当前账号: {sorted_accounts[current_index]['username']}")
        print(f"[*] 下一个账号: {next_username} (餐厅ID: {next_res_id})")
        
        # 为下一个账号添油
        return self.refill_oil_for_friend(next_res_id)

    def batch_cycle_refill_oil(self, all_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量循环添油：每个账号为下一个小号添油（1为2添，2为3添，...，50为1添）
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key, res_id等信息
        :return: 添油结果统计
        """
        print(f"[*] 开始批量循环添油，共 {len(all_accounts)} 个账号...")
        
        results = {
            "total_attempts": 0,
            "successful_refills": 0,
            "failed_refills": 0,
            "total_oil_added": 0,
            "total_gold_cost": 0,
            "refill_details": []
        }
        
        # 按ID排序账号列表
        sorted_accounts = sorted(all_accounts, key=lambda x: x['id'])
        for i, current_account in enumerate(sorted_accounts):
            if not current_account.get('key'):
                print(f"[Skip] 账号 {current_account['username']} 没有Key，跳过")
                continue
                
            results["total_attempts"] += 1
            current_username = current_account['username']
            current_id = current_account['id']
            
            # 计算下一个账号
            next_index = (i + 1) % len(sorted_accounts)
            next_account = sorted_accounts[next_index]
            next_username = next_account['username']
            next_res_id = next_account.get('res_id')
            
            print(f"[*] [{i+1}/{len(sorted_accounts)}] {current_username} 为 {next_username} 添油...")
            
            if not next_res_id:
                error_msg = f"下一个账号 {next_username} 没有餐厅ID"
                print(f"[Failed] {error_msg}")
                results["failed_refills"] += 1
                results["refill_details"].append({
                    "current_account": current_username,
                    "target_account": next_username,
                    "success": False,
                    "message": error_msg
                })
                continue
            
            try:
                # 使用当前账号的Key和Cookie创建FriendActions实例
                cookie_dict = {"PHPSESSID": current_account.get('cookie', '123')}
                friend_action = FriendActions(key=current_account['key'], cookie=cookie_dict)
                
                # 直接为下一个账号添油
                success, message = friend_action.refill_oil_for_friend(next_res_id)
                
                detail = {
                    "current_account": current_username,
                    "target_account": next_username,
                    "target_res_id": next_res_id,
                    "success": success,
                    "message": message
                }
                
                if success and isinstance(message, dict):
                    oil_added = message.get("oil_added", 0)
                    gold_cost = message.get("gold_cost", 0)
                    results["total_oil_added"] += oil_added
                    results["total_gold_cost"] += gold_cost
                    detail["oil_added"] = oil_added
                    detail["gold_cost"] = gold_cost
                    results["successful_refills"] += 1
                    print(f"[Success] {current_username} → {next_username}: +{oil_added}油, -{gold_cost}金币")
                else:
                    results["failed_refills"] += 1
                    print(f"[Failed] {current_username} → {next_username}: {message}")
                
                results["refill_details"].append(detail)
                
            except Exception as e:
                error_msg = f"添油过程中发生异常: {str(e)}"
                print(f"[Error] {current_username} → {next_username}: {error_msg}")
                results["failed_refills"] += 1
                results["refill_details"].append({
                    "current_account": current_username,
                    "target_account": next_username,
                    "success": False,
                    "message": error_msg
                })
            
            # 避免请求过快
            import time
            time.sleep(1)
        
        # 输出统计结果
        success_rate = (results["successful_refills"] / results["total_attempts"] * 100) if results["total_attempts"] > 0 else 0
        
        print(f"\n[Summary] 批量循环添油完成:")
        print(f"  总尝试: {results['total_attempts']}")
        print(f"  成功: {results['successful_refills']}")
        print(f"  失败: {results['failed_refills']}")
        print(f"  成功率: {success_rate:.1f}%")
        print(f"  总添油量: {results['total_oil_added']}")
        print(f"  总花费金币: {results['total_gold_cost']}")
        
        return results

    def batch_refill_oil_for_friends(self, max_friends: int = 10) -> Dict[str, Any]:
        """
        批量为好友添油。
        :param max_friends: 最大添油好友数量
        :return: 添油结果统计
        """
        print(f"[*] 开始批量为好友添油，最多 {max_friends} 个好友...")
        
        results = {
            "total_attempts": 0,
            "successful_refills": 0,
            "failed_refills": 0,
            "total_oil_added": 0,
            "total_gold_cost": 0,
            "refill_details": []
        }
        
        # 1. 获取好友列表
        friends = self.get_all_friends()
        if not friends:
            print("[Error] 无法获取好友列表")
            return results
        
        print(f"[Info] 获取到 {len(friends)} 个好友，将为前 {min(max_friends, len(friends))} 个添油")
        
        # 2. 逐个为好友添油
        for i, friend in enumerate(friends[:max_friends]):
            results["total_attempts"] += 1
            
            friend_name = friend.get("name", "未知好友")
            friend_id = friend.get("id")
            
            print(f"[*] [{i+1}/{min(max_friends, len(friends))}] 为 '{friend_name}' 添油...")
            
            # 检查好友关系并自动添加（如果需要）
            friendship_success, friendship_msg = self.check_and_ensure_friendship(friend_id)
            if not friendship_success:
                print(f"[Warning] 为好友 '{friend_name}' 添油前检查好友关系失败: {friendship_msg}")
            
            # 先获取好友餐厅信息
            restaurant_info = self.get_friend_restaurant_info(friend_id)
            current_oil = restaurant_info.get("bottle_num", 0) if restaurant_info else 0
            
            success, message = self.refill_oil_for_friend(friend_id)
            
            detail = {
                "friend_name": friend_name,
                "friend_id": friend_id,
                "success": success,
                "message": message,
                "oil_before": current_oil
            }
            
            if success and isinstance(message, dict):
                oil_added = message.get("oil_added", 0)
                gold_cost = message.get("gold_cost", 0)
                results["total_oil_added"] += oil_added
                results["total_gold_cost"] += gold_cost
                detail["oil_added"] = oil_added
                detail["gold_cost"] = gold_cost
                results["successful_refills"] += 1
                print(f"[Success] 为 '{friend_name}' 添油成功: +{oil_added}油, -{gold_cost}金币")
            else:
                results["failed_refills"] += 1
                print(f"[Failed] 为 '{friend_name}' 添油失败: {message}")
            
            results["refill_details"].append(detail)
            
            # 避免请求过快
            time.sleep(1)
        
        # 3. 输出统计结果
        success_rate = (results["successful_refills"] / results["total_attempts"] * 100) if results["total_attempts"] > 0 else 0
        
        print(f"\n[Summary] 批量添油完成:")
        print(f"  总尝试: {results['total_attempts']}")
        print(f"  成功: {results['successful_refills']}")
        print(f"  失败: {results['failed_refills']}")
        print(f"  成功率: {success_rate:.1f}%")
        print(f"  总添油量: {results['total_oil_added']}")
        print(f"  总花费金币: {results['total_gold_cost']}")
        
        return results

    # --- 好友互动功能（放蟑螂、吃白食） ---

    def place_roach_for_friend(self, friend_res_id: Union[str, int]) -> Tuple[bool, str]:
        """在指定好友的餐厅放一只蟑螂。"""
        return self._perform_action_on_friend_seat(
            friend_res_id=friend_res_id,
            action_type="4",  # type=4 表示放蟑螂
            action_name="放蟑螂"
        )

    def dine_and_dash_at_friend(self, friend_res_id: Union[str, int]) -> Tuple[bool, str]:
        """在指定好友餐厅吃白食。"""
        return self._perform_action_on_friend_seat(
            friend_res_id=friend_res_id,
            action_type="3",  # type=3 表示吃白食
            action_name="吃白食"
        )

    def end_dine_and_dash(self) -> Tuple[bool, str]:
        """结束吃白食状态。"""
        print("[*] 正在结束吃白食状态...")
        try:
            response = self.post(action_path="m=Index&a=endBaishi")
            msg = response.get("msg", "未知消息").replace("<br>", " / ")
            print(f"[Success] 结束吃白食: {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 结束吃白食失败: {e}")
            return False, str(e)

    def _get_friend_empty_seat_id(self, friend_res_id: Union[str, int], max_pages: int = 20) -> Optional[int]:
        """【内部方法】获取指定好友的一个空座位ID。"""
        for page_type in range(1, max_pages + 1):  # 在好友座位列表里，'type' 参数用于翻页
            try:
                payload = {"res_id": str(friend_res_id), "page": "1", "type": str(page_type)}
                response = self.post(action_path="m=Seat&a=friend_get_list", data=payload)
                seats_on_page = response.get("data", [])
                if not seats_on_page: break
                for seat in seats_on_page:
                    if seat.get("type_name") == "空位":
                        return int(seat["id"])
            except (BusinessLogicError, ConnectionError) as e:
                print(f"[Error] 获取好友座位列表第 {page_type} 页失败: {e}")
                break
        return None

    def _perform_action_on_friend_seat(self, friend_res_id: Union[str, int], action_type: str, action_name: str) -> Tuple[bool, str]:
        """【内部重构方法】在好友的空座位上执行一个动作（放蟑螂/吃白食）。"""
        print(f"[*] 正在尝试为好友 {friend_res_id} {action_name}...")
        empty_seat_id = self._get_friend_empty_seat_id(friend_res_id)
        if not empty_seat_id:
            msg = f"未找到好友 {friend_res_id} 的空座位，无法{action_name}。"
            print(f"[Info] {msg}")
            return False, msg

        print(f"[Info] 在好友餐厅找到空座位 {empty_seat_id}，准备{action_name}...")

        try:
            payload = {"res_id": str(friend_res_id), "id": str(empty_seat_id), "type": action_type}
            # 调用 m=Seat&a=friend_go
            response = self.post(action_path="m=Seat&a=friend_go", data=payload)
            msg = response.get("msg", "未知成功消息")
            print(f"[Success] {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] {action_name}失败: {e}")
            return False, str(e)

    def batch_interact_with_friends(self, action_type: str, max_friends: int = 5) -> Dict[str, Any]:
        """
        批量与好友互动（放蟑螂或吃白食）。
        :param action_type: "roach" 或 "dine_and_dash"
        :param max_friends: 最大互动好友数量
        :return: 互动结果统计
        """
        action_map = {
            "roach": ("放蟑螂", self.place_roach_for_friend),
            "dine_and_dash": ("吃白食", self.dine_and_dash_at_friend)
        }
        
        if action_type not in action_map:
            print(f"[Error] 不支持的互动类型: {action_type}")
            return {"error": "不支持的互动类型"}
        
        action_name, action_func = action_map[action_type]
        print(f"[*] 开始批量{action_name}，最多 {max_friends} 个好友...")
        
        results = {
            "total_attempts": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "interaction_details": []
        }
        
        # 1. 获取好友列表
        friends = self.get_all_friends()
        if not friends:
            print("[Error] 无法获取好友列表")
            return results
        
        print(f"[Info] 获取到 {len(friends)} 个好友，将与前 {min(max_friends, len(friends))} 个进行{action_name}")
        
        # 2. 逐个进行互动
        for i, friend in enumerate(friends[:max_friends]):
            results["total_attempts"] += 1
            
            friend_name = friend.get("name", "未知好友")
            friend_id = friend.get("id")
            
            print(f"[*] [{i+1}/{min(max_friends, len(friends))}] 向 '{friend_name}' {action_name}...")
            
            success, message = action_func(friend_id)
            
            detail = {
                "friend_name": friend_name,
                "friend_id": friend_id,
                "success": success,
                "message": message
            }
            results["interaction_details"].append(detail)
            
            if success:
                results["successful_interactions"] += 1
                print(f"[Success] 向 '{friend_name}' {action_name}成功")
            else:
                results["failed_interactions"] += 1
                print(f"[Failed] 向 '{friend_name}' {action_name}失败: {message}")
            
            # 避免请求过快
            time.sleep(2)
        
        # 3. 输出统计结果
        success_rate = (results["successful_interactions"] / results["total_attempts"] * 100) if results["total_attempts"] > 0 else 0
        
        print(f"\n[Summary] 批量{action_name}完成:")
        print(f"  总尝试: {results['total_attempts']}")
        print(f"  成功: {results['successful_interactions']}")
        print(f"  失败: {results['failed_interactions']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return results

    def batch_cycle_place_roaches(self, all_accounts: List[Dict[str, Any]], roaches_per_account: int = 5) -> Dict[str, Any]:
        """
        批量循环放蟑螂：每个账号为接下来的N个账号放蟑螂（完成活跃任务需要放5只）
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key, res_id等信息
        :param roaches_per_account: 每个账号需要放的蟑螂数量，默认5只
        :return: 放蟑螂结果统计
        """
        print(f"[*] 开始批量循环放蟑螂，共 {len(all_accounts)} 个账号，每个账号放 {roaches_per_account} 只...")
        
        results = {
            "total_attempts": 0,
            "successful_roaches": 0,
            "failed_roaches": 0,
            "roach_details": []
        }
        
        # 按ID排序账号列表
        sorted_accounts = sorted(all_accounts, key=lambda x: x['id'])
        total_accounts = len(sorted_accounts)
        
        for i, current_account in enumerate(sorted_accounts):
            if not current_account.get('key'):
                print(f"[Skip] 账号 {current_account['username']} 没有Key，跳过")
                continue
            
            current_username = current_account['username']
            account_success_count = 0
            account_failed_count = 0
            
            print(f"\n[*] [{i+1}/{total_accounts}] {current_username} 开始放 {roaches_per_account} 只蟑螂...")
            
            # 使用当前账号的Key和Cookie创建FriendActions实例
            try:
                cookie_dict = {"PHPSESSID": current_account.get('cookie', '123')}
                friend_action = FriendActions(key=current_account['key'], cookie=cookie_dict)
                
                # 为接下来的N个账号放蟑螂
                for roach_num in range(roaches_per_account):
                    results["total_attempts"] += 1
                    
                    # 计算目标账号索引（循环）
                    target_index = (i + roach_num + 1) % total_accounts
                    target_account = sorted_accounts[target_index]
                    target_username = target_account['username']
                    target_res_id = target_account.get('res_id')
                    
                    print(f"  [{roach_num+1}/{roaches_per_account}] {current_username} → {target_username}...")
                    
                    if not target_res_id:
                        error_msg = f"目标账号 {target_username} 没有餐厅ID"
                        print(f"  [Failed] {error_msg}")
                        results["failed_roaches"] += 1
                        account_failed_count += 1
                        results["roach_details"].append({
                            "current_account": current_username,
                            "target_account": target_username,
                            "roach_number": roach_num + 1,
                            "success": False,
                            "message": error_msg
                        })
                        continue
                    
                    try:
                        # 放蟑螂
                        success, message = friend_action.place_roach_for_friend(target_res_id)
                        
                        detail = {
                            "current_account": current_username,
                            "target_account": target_username,
                            "target_res_id": target_res_id,
                            "roach_number": roach_num + 1,
                            "success": success,
                            "message": message
                        }
                        
                        if success:
                            results["successful_roaches"] += 1
                            account_success_count += 1
                            print(f"  [Success] 第 {roach_num+1} 只蟑螂放置成功")
                        else:
                            results["failed_roaches"] += 1
                            account_failed_count += 1
                            print(f"  [Failed] 第 {roach_num+1} 只蟑螂放置失败: {message}")
                        
                        results["roach_details"].append(detail)
                        
                        # 避免请求过快
                        time.sleep(0.5)
                        
                    except Exception as e:
                        error_msg = f"放第 {roach_num+1} 只蟑螂时发生异常: {str(e)}"
                        print(f"  [Error] {error_msg}")
                        results["failed_roaches"] += 1
                        account_failed_count += 1
                        results["roach_details"].append({
                            "current_account": current_username,
                            "target_account": target_username,
                            "roach_number": roach_num + 1,
                            "success": False,
                            "message": error_msg
                        })
                
                # 账号完成统计
                print(f"[Summary] {current_username} 完成: 成功 {account_success_count}/{roaches_per_account}")
                
            except Exception as e:
                error_msg = f"初始化 {current_username} 时发生异常: {str(e)}"
                print(f"[Error] {error_msg}")
                # 为该账号的所有尝试记录失败
                for roach_num in range(roaches_per_account):
                    results["total_attempts"] += 1
                    results["failed_roaches"] += 1
                    results["roach_details"].append({
                        "current_account": current_username,
                        "target_account": "未知",
                        "roach_number": roach_num + 1,
                        "success": False,
                        "message": error_msg
                    })
            
            # 账号间避免请求过快
            import time
            time.sleep(1)
        
        # 输出统计结果
        success_rate = (results["successful_roaches"] / results["total_attempts"] * 100) if results["total_attempts"] > 0 else 0
        
        print(f"\n[Summary] 批量循环放蟑螂完成:")
        print(f"  总尝试: {results['total_attempts']}")
        print(f"  成功: {results['successful_roaches']}")
        print(f"  失败: {results['failed_roaches']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return results

    def batch_clear_all_accounts_roaches(self, all_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量清理所有账号餐厅中的蟑螂
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key等信息
        :return: 清理结果统计
        """
        print(f"[*] 开始批量清理所有账号的蟑螂，共 {len(all_accounts)} 个账号...")
        
        total_results = {
            "total_accounts": len(all_accounts),
            "processed_accounts": 0,
            "total_roaches_cleared": 0,
            "successful_clears": 0,
            "failed_clears": 0,
            "account_details": []
        }
        
        for i, account in enumerate(all_accounts):
            if not account.get('key'):
                print(f"[Skip] 账号 {account['username']} 没有Key，跳过")
                continue
            
            total_results["processed_accounts"] += 1
            current_username = account['username']
            
            print(f"[*] [{i+1}/{len(all_accounts)}] 清理账号 {current_username} 的蟑螂...")
            
            try:
                # 使用当前账号创建RestaurantActions实例
                from src.delicious_town_bot.actions.restaurant import RestaurantActions
                cookie_dict = {"PHPSESSID": account.get('cookie', '123')}
                restaurant_action = RestaurantActions(key=account['key'], cookie=cookie_dict)
                
                # 获取餐厅中的蟑螂信息
                seat_map = restaurant_action._get_seats_by_types([("4", "蟑螂")])
                if seat_map is None:
                    detail = {
                        "account_name": current_username,
                        "roaches_found": 0,
                        "roaches_cleared": 0,
                        "success": False,
                        "message": "获取座位列表失败"
                    }
                    total_results["failed_clears"] += 1
                    print(f"[Failed] {current_username}: 获取座位列表失败")
                else:
                    roach_ids = seat_map.get("蟑螂", [])
                    roaches_count = len(roach_ids)
                    
                    if roaches_count == 0:
                        detail = {
                            "account_name": current_username,
                            "roaches_found": 0,
                            "roaches_cleared": 0,
                            "success": True,
                            "message": "餐厅内没有蟑螂"
                        }
                        total_results["successful_clears"] += 1
                        print(f"[Info] {current_username}: 餐厅内没有蟑螂")
                    else:
                        # 执行清理蟑螂
                        print(f"[*] {current_username}: 发现 {roaches_count} 只蟑螂，开始清理...")
                        
                        cleared_count = 0
                        for j, seat_id in enumerate(roach_ids):
                            try:
                                print(f"  [{j+1}/{roaches_count}] 清理第 {j+1} 只蟑螂...")
                                restaurant_action._clear_one_roach(seat_id)
                                cleared_count += 1
                                time.sleep(0.5)  # 避免请求过快
                            except Exception as e:
                                print(f"  [Warning] 清理第 {j+1} 只蟑螂失败: {e}")
                        
                        # 检查是否满足任务要求
                        task_completed = cleared_count >= 5
                        detail = {
                            "account_name": current_username,
                            "roaches_found": roaches_count,
                            "roaches_cleared": cleared_count,
                            "success": cleared_count > 0,
                            "task_completed": task_completed,
                            "message": f"清理了 {cleared_count}/{roaches_count} 只蟑螂" + (" ✅ 任务完成" if task_completed else f" ⚠️ 需要{5-cleared_count}只完成任务")
                        }
                        
                        total_results["total_roaches_cleared"] += cleared_count
                        if cleared_count == roaches_count and cleared_count > 0:
                            total_results["successful_clears"] += 1
                            if task_completed:
                                print(f"[Success] {current_username}: 成功清理 {cleared_count} 只蟑螂 ✅ 任务完成")
                            else:
                                print(f"[Success] {current_username}: 成功清理 {cleared_count} 只蟑螂 ⚠️ 还需{5-cleared_count}只")
                        else:
                            total_results["failed_clears"] += 1
                            print(f"[Partial] {current_username}: 清理了 {cleared_count}/{roaches_count} 只蟑螂")
                
            except Exception as e:
                error_msg = f"清理蟑螂时发生异常: {str(e)}"
                print(f"[Error] {current_username}: {error_msg}")
                detail = {
                    "account_name": current_username,
                    "roaches_found": 0,
                    "roaches_cleared": 0,
                    "success": False,
                    "message": error_msg
                }
                total_results["failed_clears"] += 1
            
            total_results["account_details"].append(detail)
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 输出总体统计
        success_rate = (total_results["successful_clears"] / total_results["processed_accounts"] * 100) if total_results["processed_accounts"] > 0 else 0
        
        print(f"\n[Summary] 批量清理蟑螂完成:")
        print(f"  处理账号数: {total_results['processed_accounts']}/{total_results['total_accounts']}")
        print(f"  成功清理: {total_results['successful_clears']}")
        print(f"  失败: {total_results['failed_clears']}")
        print(f"  总清理蟑螂数: {total_results['total_roaches_cleared']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return total_results

    def batch_roach_cycle_complete(self, all_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        完整的蟑螂任务循环：先放蟑螂，再清理蟑螂
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key, res_id等信息
        :return: 完整任务结果统计
        """
        print(f"[*] 开始完整的蟑螂任务循环，共 {len(all_accounts)} 个账号...")
        print(f"[*] 任务流程：循环放蟑螂 → 清理自己餐厅蟑螂")
        
        complete_results = {
            "total_accounts": len(all_accounts),
            "roach_place_results": {},
            "roach_clear_results": {},
            "overall_success": False,
            "summary": ""
        }
        
        try:
            # 第一步：循环放蟑螂
            print(f"\n{'='*60}")
            print(f"🪳 第一阶段：批量循环放蟑螂")
            print(f"{'='*60}")
            
            place_results = self.batch_cycle_place_roaches(all_accounts)
            complete_results["roach_place_results"] = place_results
            
            # 第二步：批量清理蟑螂  
            print(f"\n{'='*60}")
            print(f"🧹 第二阶段：批量清理蟑螂")
            print(f"{'='*60}")
            
            clear_results = self.batch_clear_all_accounts_roaches(all_accounts)
            complete_results["roach_clear_results"] = clear_results
            
            # 生成综合统计
            place_success = place_results.get("successful_roaches", 0)
            place_total = place_results.get("total_attempts", 0)
            clear_success = clear_results.get("successful_clears", 0)
            clear_total = clear_results.get("processed_accounts", 0)
            total_roaches_cleared = clear_results.get("total_roaches_cleared", 0)
            
            overall_success_rate = ((place_success + clear_success) / (place_total + clear_total) * 100) if (place_total + clear_total) > 0 else 0
            complete_results["overall_success"] = overall_success_rate > 50
            
            summary_lines = [
                f"🎯 蟑螂任务完整循环结果:",
                f"  🪳 放蟑螂: 成功 {place_success}/{place_total}",
                f"  🧹 清理蟑螂: 成功 {clear_success}/{clear_total}，清理 {total_roaches_cleared} 只",
                f"  📊 整体成功率: {overall_success_rate:.1f}%"
            ]
            
            summary = "\n".join(summary_lines)
            complete_results["summary"] = summary
            
            print(f"\n{'='*60}")
            print(summary)
            print(f"{'='*60}")
            
            return complete_results
            
        except Exception as e:
            error_msg = f"蟑螂任务循环执行失败: {str(e)}"
            print(f"\n[Error] {error_msg}")
            complete_results["summary"] = error_msg
            return complete_results

    # --- 吃白食批量循环方法 ---

    def get_accounts_with_restaurant_ids(self, all_accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        获取所有账号的餐厅ID（从数据库读取，避免重复API调用）
        :param all_accounts: 所有账号的列表
        :return: 包含餐厅ID的账号列表
        """
        print(f"[*] 正在从数据库获取 {len(all_accounts)} 个账号的餐厅ID...")
        
        accounts_with_res_id = []
        missing_res_id_accounts = []
        
        for account in all_accounts:
            if not account.get('key'):
                print(f"[Skip] 账号 {account['username']} 没有Key，跳过")
                continue
                
            # 从数据库中的restaurant字段读取res_id
            res_id = account.get('restaurant')  # 这应该是数字格式的res_id
            
            if res_id and res_id != 'None':
                # 账号已有餐厅ID，直接使用
                account_copy = account.copy()
                account_copy['res_id'] = res_id
                accounts_with_res_id.append(account_copy)
                print(f"[Database] {account['username']}: 餐厅ID={res_id}")
            else:
                # 账号缺少餐厅ID，记录下来
                missing_res_id_accounts.append(account['username'])
                print(f"[Warning] {account['username']}: 数据库中缺少餐厅ID")
        
        if missing_res_id_accounts:
            print(f"[*] 发现 {len(missing_res_id_accounts)} 个账号缺少餐厅ID: {', '.join(missing_res_id_accounts)}")
            print(f"[*] 请先使用 '🏪 更新餐厅ID' 按钮为这些账号获取餐厅ID")
        
        print(f"[*] 成功获取 {len(accounts_with_res_id)} 个账号的餐厅ID（从数据库）")
        return accounts_with_res_id

    def batch_cycle_eat_at_friends(self, all_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量循环吃白食：每个账号去下一个账号的餐厅吃白食以回复体力
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key, res_id等信息
        :return: 吃白食结果统计
        """
        print(f"[*] 开始批量循环吃白食，共 {len(all_accounts)} 个账号，每个账号去下一个账号的餐厅吃白食...")
        
        # 首先从数据库获取所有账号的餐厅ID
        accounts_with_res_id = self.get_accounts_with_restaurant_ids(all_accounts)
        
        if not accounts_with_res_id:
            return {
                "total_accounts": len(all_accounts),
                "processed_accounts": 0,
                "successful_eats": 0,
                "failed_eats": 0,
                "account_details": [],
                "error": "没有可处理的账号"
            }
        
        total_results = {
            "total_accounts": len(accounts_with_res_id),
            "processed_accounts": 0,
            "successful_eats": 0,
            "failed_eats": 0,
            "account_details": []
        }
        
        for i, account in enumerate(accounts_with_res_id):
            total_results["processed_accounts"] += 1
            current_username = account['username']
            
            print(f"[*] [{i+1}/{len(accounts_with_res_id)}] 账号 {current_username} 开始循环吃白食...")
            
            try:
                # 使用当前账号创建FriendActions实例
                from src.delicious_town_bot.actions.friend import FriendActions
                cookie_dict = {"PHPSESSID": account.get('cookie', '123')}
                friend_action = FriendActions(key=account['key'], cookie=cookie_dict)
                
                # 计算下一个账号的索引（循环模式：1->2, 2->3, ..., 最后一个->1）
                next_index = (i + 1) % len(accounts_with_res_id)
                target_account = accounts_with_res_id[next_index]
                
                target_res_id = target_account.get('res_id')
                target_username = target_account.get('username', '未知账号')
                
                # 1. 确保是好友关系
                print(f"  正在确保与目标账号 {target_username} 的好友关系...")
                friend_ok, friend_msg = friend_action.check_and_ensure_friendship(target_res_id)
                
                if friend_ok:
                    print(f"  ✅ 好友关系正常: {friend_msg}")
                    
                    # 2. 去目标账号餐厅吃白食
                    print(f"  尝试在 '{target_username}' 餐厅吃白食...")
                    
                    success, message = friend_action.dine_and_dash_at_friend(target_res_id)
                    if success:
                        total_results["successful_eats"] += 1
                        print(f"  ✅ 在 '{target_username}' 餐厅吃白食成功，体力已回复")
                        detail = {
                            "account_name": current_username,
                            "target_account": target_username,
                            "target_res_id": target_res_id,
                            "success": True,
                            "message": f"成功在 '{target_username}' 餐厅吃白食"
                        }
                    else:
                        total_results["failed_eats"] += 1
                        print(f"  ❌ 在 '{target_username}' 餐厅吃白食失败: {message}")
                        detail = {
                            "account_name": current_username,
                            "target_account": target_username,
                            "target_res_id": target_res_id,
                            "success": False,
                            "message": f"吃白食失败: {message}"
                        }
                else:
                    total_results["failed_eats"] += 1
                    print(f"  ❌ 好友关系处理失败: {friend_msg}")
                    detail = {
                        "account_name": current_username,
                        "target_account": target_username,
                        "target_res_id": target_res_id,
                        "success": False,
                        "message": f"好友关系处理失败: {friend_msg}"
                    }
                
            except Exception as e:
                error_msg = f"吃白食时发生异常: {str(e)}"
                print(f"[Error] {current_username}: {error_msg}")
                detail = {
                    "account_name": current_username,
                    "target_account": "未知",
                    "target_res_id": "未知",
                    "success": False,
                    "message": error_msg
                }
                total_results["failed_eats"] += 1
            
            total_results["account_details"].append(detail)
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 输出总体统计
        success_rate = (total_results["successful_eats"] / total_results["processed_accounts"] * 100) if total_results["processed_accounts"] > 0 else 0
        
        print(f"\n[Summary] 批量吃白食完成:")
        print(f"  处理账号数: {total_results['processed_accounts']}/{total_results['total_accounts']}")
        print(f"  成功吃白食: {total_results['successful_eats']}")
        print(f"  失败: {total_results['failed_eats']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return total_results

    def batch_end_dine_and_dash(self, all_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量结束所有账号的吃白食状态
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key等信息
        :return: 结束吃白食结果统计
        """
        print(f"[*] 开始批量结束吃白食，共 {len(all_accounts)} 个账号...")
        
        total_results = {
            "total_accounts": len(all_accounts),
            "processed_accounts": 0,
            "successful_ends": 0,
            "failed_ends": 0,
            "account_details": []
        }
        
        for i, account in enumerate(all_accounts):
            if not account.get('key'):
                print(f"[Skip] 账号 {account['username']} 没有Key，跳过")
                continue
            
            total_results["processed_accounts"] += 1
            current_username = account['username']
            
            print(f"[*] [{i+1}/{len(all_accounts)}] 账号 {current_username} 结束吃白食...")
            
            try:
                # 使用当前账号创建FriendActions实例
                from src.delicious_town_bot.actions.friend import FriendActions
                cookie_dict = {"PHPSESSID": account.get('cookie', '123')}
                friend_action = FriendActions(key=account['key'], cookie=cookie_dict)
                
                success, message = friend_action.end_dine_and_dash()
                if success:
                    total_results["successful_ends"] += 1
                    print(f"  ✅ {current_username}: 成功结束吃白食")
                    detail = {
                        "account_name": current_username,
                        "success": True,
                        "message": f"成功结束吃白食: {message}"
                    }
                else:
                    total_results["failed_ends"] += 1
                    print(f"  ❌ {current_username}: 结束吃白食失败: {message}")
                    detail = {
                        "account_name": current_username,
                        "success": False,
                        "message": f"结束吃白食失败: {message}"
                    }
                
            except Exception as e:
                error_msg = f"结束吃白食时发生异常: {str(e)}"
                print(f"[Error] {current_username}: {error_msg}")
                detail = {
                    "account_name": current_username,
                    "success": False,
                    "message": error_msg
                }
                total_results["failed_ends"] += 1
            
            total_results["account_details"].append(detail)
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 输出总体统计
        success_rate = (total_results["successful_ends"] / total_results["processed_accounts"] * 100) if total_results["processed_accounts"] > 0 else 0
        
        print(f"\n[Summary] 批量结束吃白食完成:")
        print(f"  处理账号数: {total_results['processed_accounts']}/{total_results['total_accounts']}")
        print(f"  成功结束: {total_results['successful_ends']}")
        print(f"  失败: {total_results['failed_ends']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return total_results

    def batch_eat_cycle_complete(self, all_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        完整的吃白食循环：吃白食回复体力
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key, res_id等信息
        :return: 完整任务结果统计
        """
        print(f"[*] 开始吃白食循环，共 {len(all_accounts)} 个账号...")
        print(f"[*] 任务流程：在好友餐厅吃白食回复体力")
        
        complete_results = {
            "total_accounts": len(all_accounts),
            "eat_results": {},
            "overall_success": False,
            "summary": ""
        }
        
        try:
            # 批量吃白食
            print(f"\n{'='*60}")
            print(f"🍽️ 开始批量吃白食")
            print(f"{'='*60}")
            
            eat_results = self.batch_cycle_eat_at_friends(all_accounts)
            complete_results["eat_results"] = eat_results
            
            # 生成综合统计
            eat_success = eat_results.get("successful_eats", 0)
            processed_accounts = eat_results.get("processed_accounts", 0)
            
            overall_success_rate = (eat_success / processed_accounts * 100) if processed_accounts > 0 else 0
            complete_results["overall_success"] = overall_success_rate > 50
            
            summary_lines = [
                f"🎯 吃白食循环结果:",
                f"  🍽️ 成功吃白食: {eat_success}/{processed_accounts}",
                f"  📊 成功率: {overall_success_rate:.1f}%"
            ]
            
            summary = "\n".join(summary_lines)
            complete_results["summary"] = summary
            
            print(f"\n{'='*60}")
            print(summary)
            print(f"{'='*60}")
            
            return complete_results
            
        except Exception as e:
            error_msg = f"吃白食循环执行失败: {str(e)}"
            print(f"\n[Error] {error_msg}")
            complete_results["summary"] = error_msg
            return complete_results

    # --- 翻橱柜相关功能 ---

    def find_cupboard_grid(self, friend_res_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        获取好友餐厅的橱柜格子信息
        :param friend_res_id: 好友餐厅ID
        :return: 橱柜格子信息，包含可翻的位置列表，或失败时返回None
        """
        print(f"[*] 正在获取好友 {friend_res_id} 的橱柜格子信息...")
        
        try:
            payload = {
                "res_id": str(friend_res_id),
                "key": self.key
            }
            
            response = self.post(action_path="m=CupboardGrid&a=find_cupboard_grid", data=payload)
            
            data = response.get("data", [])
            if not isinstance(data, list):
                print(f"[Warning] API返回的data字段不是列表类型: {type(data)}")
                return None
            
            # 过滤出status=1的可翻格子
            available_grids = [grid for grid in data if grid.get("status") == "1"]
            
            print(f"[Info] 找到 {len(available_grids)} 个可翻的橱柜格子")
            
            return {
                "res_id": friend_res_id,
                "available_grids": available_grids,
                "total_grids": len(data)
            }
            
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 获取橱柜格子信息失败: {e}")
            return None

    def go_cupboard(self, grid_id: Union[str, int], friend_res_id: Union[str, int]) -> Tuple[bool, str]:
        """
        翻指定的橱柜格子
        :param grid_id: 橱柜格子ID
        :param friend_res_id: 好友餐厅ID
        :return: (是否成功, 消息)
        """
        print(f"[*] 正在翻橱柜格子 {grid_id}...")
        
        try:
            payload = {
                "grid_id": str(grid_id),
                "res_id": str(friend_res_id),
                "key": self.key
            }
            
            response = self.post(action_path="m=CupboardGrid&a=go_cupboard", data=payload)
            msg = response.get("msg", "翻橱柜成功").replace("<br>", " / ")
            
            print(f"[Success] 翻橱柜成功: {msg}")
            return True, msg
            
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 翻橱柜失败: {e}")
            return False, str(e)

    def batch_cupboard_for_friend(self, friend_res_id: Union[str, int], max_grids: int = 5) -> Dict[str, Any]:
        """
        批量翻指定好友的橱柜（每次翻5个格子，消耗10体力）
        :param friend_res_id: 好友餐厅ID
        :param max_grids: 最大翻橱柜格子数量，默认5个
        :return: 翻橱柜结果统计
        """
        print(f"[*] 开始为好友 {friend_res_id} 批量翻橱柜，最多翻 {max_grids} 个格子...")
        
        results = {
            "friend_res_id": friend_res_id,
            "total_attempts": 0,
            "successful_cupboards": 0,
            "failed_cupboards": 0,
            "cupboard_details": [],
            "total_energy_cost": 0
        }
        
        # 1. 获取橱柜格子信息
        cupboard_info = self.find_cupboard_grid(friend_res_id)
        if not cupboard_info:
            print("[Error] 无法获取橱柜格子信息")
            return results
        
        available_grids = cupboard_info.get("available_grids", [])
        if not available_grids:
            print("[Info] 没有可翻的橱柜格子")
            return results
        
        print(f"[Info] 找到 {len(available_grids)} 个可翻的格子，将翻前 {min(max_grids, len(available_grids))} 个")
        
        # 2. 逐个翻橱柜
        for i, grid in enumerate(available_grids[:max_grids]):
            results["total_attempts"] += 1
            
            grid_id = grid.get("id")
            cup_num = grid.get("cup_num", "未知")
            
            print(f"[*] [{i+1}/{min(max_grids, len(available_grids))}] 翻第 {cup_num} 号格子 (ID: {grid_id})...")
            
            success, message = self.go_cupboard(grid_id, friend_res_id)
            
            detail = {
                "grid_id": grid_id,
                "cup_num": cup_num,
                "success": success,
                "message": message
            }
            results["cupboard_details"].append(detail)
            
            if success:
                results["successful_cupboards"] += 1
                results["total_energy_cost"] += 2  # 每次翻橱柜消耗2体力
                print(f"[Success] 第 {cup_num} 号格子翻橱柜成功")
            else:
                results["failed_cupboards"] += 1
                print(f"[Failed] 第 {cup_num} 号格子翻橱柜失败: {message}")
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 3. 输出统计结果
        success_rate = (results["successful_cupboards"] / results["total_attempts"] * 100) if results["total_attempts"] > 0 else 0
        
        print(f"\n[Summary] 好友 {friend_res_id} 翻橱柜完成:")
        print(f"  总尝试: {results['total_attempts']}")
        print(f"  成功: {results['successful_cupboards']}")
        print(f"  失败: {results['failed_cupboards']}")
        print(f"  成功率: {success_rate:.1f}%")
        print(f"  消耗体力: {results['total_energy_cost']}")
        
        return results

    def batch_cycle_cupboard_for_friends(self, all_accounts: List[Dict[str, Any]], cupboards_per_account: int = 5) -> Dict[str, Any]:
        """
        批量循环翻橱柜：每个账号去下一个账号的餐厅翻橱柜（完成每日任务）
        :param all_accounts: 所有账号的列表，每个账号应包含id, username, key, res_id等信息
        :param cupboards_per_account: 每个账号翻的橱柜格子数量，默认5个（消耗10体力）
        :return: 翻橱柜结果统计
        """
        print(f"[*] 开始批量循环翻橱柜，共 {len(all_accounts)} 个账号，每个账号翻 {cupboards_per_account} 个格子...")
        
        # 首先从数据库获取所有账号的餐厅ID
        accounts_with_res_id = self.get_accounts_with_restaurant_ids(all_accounts)
        
        if not accounts_with_res_id:
            return {
                "total_accounts": len(all_accounts),
                "processed_accounts": 0,
                "successful_cupboards": 0,
                "failed_cupboards": 0,
                "total_energy_cost": 0,
                "account_details": [],
                "error": "没有可处理的账号"
            }
        
        total_results = {
            "total_accounts": len(accounts_with_res_id),
            "processed_accounts": 0,
            "successful_cupboards": 0,
            "failed_cupboards": 0,
            "total_energy_cost": 0,
            "account_details": []
        }
        
        for i, account in enumerate(accounts_with_res_id):
            total_results["processed_accounts"] += 1
            current_username = account['username']
            
            print(f"[*] [{i+1}/{len(accounts_with_res_id)}] 账号 {current_username} 开始翻橱柜...")
            
            try:
                # 使用当前账号创建FriendActions实例
                cookie_dict = {"PHPSESSID": account.get('cookie', '123')}
                friend_action = FriendActions(key=account['key'], cookie=cookie_dict)
                
                # 计算下一个账号的索引（循环模式：1->2, 2->3, ..., 最后一个->1）
                next_index = (i + 1) % len(accounts_with_res_id)
                target_account = accounts_with_res_id[next_index]
                
                target_res_id = target_account.get('res_id')
                target_username = target_account.get('username', '未知账号')
                
                print(f"  目标账号: {target_username} (餐厅ID: {target_res_id})")
                
                # 1. 确保是好友关系
                print(f"  正在确保与目标账号 {target_username} 的好友关系...")
                friend_ok, friend_msg = friend_action.check_and_ensure_friendship(target_res_id)
                
                if friend_ok:
                    print(f"  ✅ 好友关系正常: {friend_msg}")
                    
                    # 2. 批量翻橱柜
                    cupboard_results = friend_action.batch_cupboard_for_friend(target_res_id, cupboards_per_account)
                    
                    # 累计统计
                    total_results["successful_cupboards"] += cupboard_results.get("successful_cupboards", 0)
                    total_results["failed_cupboards"] += cupboard_results.get("failed_cupboards", 0)
                    total_results["total_energy_cost"] += cupboard_results.get("total_energy_cost", 0)
                    
                    success_count = cupboard_results.get("successful_cupboards", 0)
                    failed_count = cupboard_results.get("failed_cupboards", 0)
                    
                    if success_count >= cupboards_per_account:
                        print(f"  ✅ {current_username} → {target_username}: 翻橱柜任务完成 ({success_count}/{cupboards_per_account})")
                        detail = {
                            "account_name": current_username,
                            "target_account": target_username,
                            "target_res_id": target_res_id,
                            "success": True,
                            "cupboards_success": success_count,
                            "cupboards_failed": failed_count,
                            "energy_cost": cupboard_results.get("total_energy_cost", 0),
                            "message": f"成功翻橱柜 {success_count}/{cupboards_per_account} 个格子"
                        }
                    else:
                        print(f"  ⚠️ {current_username} → {target_username}: 翻橱柜部分完成 ({success_count}/{cupboards_per_account})")
                        detail = {
                            "account_name": current_username,
                            "target_account": target_username,
                            "target_res_id": target_res_id,
                            "success": success_count > 0,
                            "cupboards_success": success_count,
                            "cupboards_failed": failed_count,
                            "energy_cost": cupboard_results.get("total_energy_cost", 0),
                            "message": f"部分完成翻橱柜 {success_count}/{cupboards_per_account} 个格子"
                        }
                else:
                    print(f"  ❌ 好友关系处理失败: {friend_msg}")
                    detail = {
                        "account_name": current_username,
                        "target_account": target_username,
                        "target_res_id": target_res_id,
                        "success": False,
                        "cupboards_success": 0,
                        "cupboards_failed": 0,
                        "energy_cost": 0,
                        "message": f"好友关系处理失败: {friend_msg}"
                    }
                
            except Exception as e:
                error_msg = f"翻橱柜时发生异常: {str(e)}"
                print(f"[Error] {current_username}: {error_msg}")
                detail = {
                    "account_name": current_username,
                    "target_account": "未知",
                    "target_res_id": "未知",
                    "success": False,
                    "cupboards_success": 0,
                    "cupboards_failed": 0,
                    "energy_cost": 0,
                    "message": error_msg
                }
            
            total_results["account_details"].append(detail)
            
            # 避免请求过快
            time.sleep(1)
        
        # 输出总体统计
        total_attempts = total_results["successful_cupboards"] + total_results["failed_cupboards"]
        success_rate = (total_results["successful_cupboards"] / total_attempts * 100) if total_attempts > 0 else 0
        
        print(f"\n[Summary] 批量翻橱柜完成:")
        print(f"  处理账号数: {total_results['processed_accounts']}/{total_results['total_accounts']}")
        print(f"  成功翻橱柜: {total_results['successful_cupboards']}")
        print(f"  失败: {total_results['failed_cupboards']}")
        print(f"  总消耗体力: {total_results['total_energy_cost']}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return total_results

    # --- 辅助方法 ---

    def get_friend_by_name(self, friend_name: str) -> Optional[Dict[str, Any]]:
        """
        根据好友名称查找好友信息。
        :param friend_name: 好友名称
        :return: 好友信息字典，或未找到时返回 None
        """
        all_friends = self.get_all_friends()
        if not all_friends:
            return None
        
        for friend in all_friends:
            if friend.get("name") == friend_name:
                return friend
        
        return None

    def list_available_foods(self) -> List[Dict[str, str]]:
        """
        列出所有可用的食材信息。
        :return: 食材信息列表
        """
        try:
            foods_file_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "assets", "foods.json"
            )
            
            with open(foods_file_path, 'r', encoding='utf-8') as f:
                foods_data = json.load(f)
            
            return foods_data.get("RECORDS", [])
            
        except Exception as e:
            print(f"[Error] 读取食材数据失败: {e}")
            return []

    def print_friend_summary(self, friends: List[Dict[str, Any]]):
        """
        打印好友摘要信息。
        :param friends: 好友列表
        """
        if not friends:
            print("[Info] 没有好友数据")
            return
        
        print(f"\n{'='*60}")
        print(f"好友列表摘要 (共 {len(friends)} 个好友)")
        print(f"{'='*60}")
        
        # 按等级分组统计
        level_stats = {}
        for friend in friends:
            level = int(friend.get("level", 0))
            level_stats[level] = level_stats.get(level, 0) + 1
        
        print("等级分布:")
        for level in sorted(level_stats.keys(), reverse=True):
            count = level_stats[level]
            print(f"  等级 {level}: {count} 人")
        
        print(f"\n前10个好友:")
        for i, friend in enumerate(friends[:10]):
            name = friend.get("name", "未知")
            level = friend.get("level", "0")
            friend_id = friend.get("id", "未知")
            avatar = "有头像" if friend.get("avatar") else "无头像"
            print(f"  {i+1:2d}. {name} (ID:{friend_id}, 等级:{level}, {avatar})")
        
        if len(friends) > 10:
            print(f"  ... 还有 {len(friends) - 10} 个好友")
        
        print(f"{'='*60}")

    def get_friend_cupboard(self, res_id: str, food_type: int = 1, page: int = 1) -> Optional[Dict[str, Any]]:
        """
        获取好友的食材库存
        :param res_id: 好友的餐厅ID
        :param food_type: 食材类型/等级 (1-5)
        :param page: 页码，从1开始
        :return: 好友库存数据，包含食材列表等信息
        """
        print(f"[*] 正在获取好友 {res_id} 的 {food_type} 级食材库存 (第 {page} 页)...")
        
        payload = {
            "page": page,
            "type": food_type,
            "res_id": res_id
        }
        
        try:
            response = self.post(action_path="m=Food&a=get_friend_cupboard", data=payload)
            
            # 检查返回数据
            foods = response.get("data", [])
            if not foods:
                print(f"[Warning] 好友 {res_id} 没有 {food_type} 级食材库存数据")
                return None
            
            # 确保foods是列表
            if not isinstance(foods, list):
                print(f"[Warning] 好友库存数据格式异常: {type(foods)}")
                return None
                
            print(f"[Info] 好友 {res_id} 的 {food_type} 级食材: {len(foods)} 种")
            
            return {
                "foods": foods,
                "page": page,
                "food_type": food_type,
                "res_id": res_id,
                "total_count": len(foods)
            }
            
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 获取好友库存失败: {e}")
            return None

    def get_friend_food_count(self, res_id: str, target_food_name: str) -> int:
        """
        获取好友拥有特定食材的数量
        :param res_id: 好友的餐厅ID
        :param target_food_name: 目标食材名称
        :return: 食材数量，如果没有则返回0
        """
        print(f"[*] 正在查询好友 {res_id} 的 '{target_food_name}' 数量...")
        
        # 获取食材信息以确定等级
        food_info = self._find_food_by_name(target_food_name)
        if not food_info:
            print(f"[Warning] 未找到食材 '{target_food_name}' 的信息")
            return 0
        
        food_level = food_info.get("level", 1)
        try:
            food_level = int(food_level)
        except (ValueError, TypeError):
            food_level = 1
        
        # 查询对应等级的库存
        cupboard_data = self.get_friend_cupboard(res_id, food_level, page=1)
        if not cupboard_data:
            return 0
        
        # 在食材列表中查找目标食材
        foods = cupboard_data.get("foods", [])
        for food in foods:
            # API返回的字段名是food_name，不是name
            if food.get("food_name") == target_food_name:
                count = food.get("num", 0)
                try:
                    count = int(count)
                    print(f"[Info] 好友 {res_id} 拥有 {target_food_name} x{count}")
                    return count
                except (ValueError, TypeError):
                    return 0
        
        print(f"[Info] 好友 {res_id} 没有 {target_food_name}")
        return 0

    def direct_friend_exchange(self, res_id: str, friend_code: str, my_code: str) -> Tuple[bool, str]:
        """
        直接好友兑换食材 (非VIP方式)
        :param res_id: 好友的餐厅ID
        :param friend_code: 好友食材代码
        :param my_code: 自己的食材代码
        :return: (是否成功, 消息)
        """
        print(f"[*] 直接兑换: 用我的食材代码{my_code} 换好友{res_id}的食材代码{friend_code}...")
        
        payload = {
            "res_id": res_id,
            "friend_code": friend_code,
            "my_code": my_code
        }
        
        try:
            response = self.post(action_path="m=CupboardGrid&a=friend_exchange_food", data=payload)
            
            # 检查返回结果
            if response.get("status"):
                msg = response.get("msg", "兑换成功")
                print(f"[Success] 兑换成功: {msg}")
                return True, msg
            else:
                msg = response.get("msg", "兑换失败")
                print(f"[Error] 兑换失败: {msg}")
                return False, msg
                
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 直接兑换失败: {e}")
            return False, str(e)


# =======================================================
#               可以直接运行此文件进行测试
# =======================================================
if __name__ == '__main__':
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY:
        raise ValueError("请在 .env 中设置 TEST_KEY")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR} if TEST_COOKIE_STR else None

    action = FriendActions(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "#" * 20 + "  好友管理模块完整测试  " + "#" * 20)

    # --- 测试 1: 获取好友列表 ---
    print("\n\n" + "=" * 20 + " 1. 开始测试获取好友列表 " + "=" * 20)
    friends = action.get_all_friends()
    if friends:
        action.print_friend_summary(friends)
    else:
        print("获取好友列表失败。")

    # --- 测试 2: 获取好友餐厅信息 ---
    print("\n\n" + "=" * 20 + " 2. 开始测试获取好友餐厅信息 " + "=" * 20)
    if friends and len(friends) > 0:
        test_friend = friends[0]
        test_friend_id = test_friend.get("id")
        test_friend_name = test_friend.get("name", "未知好友")
        print(f"测试好友: {test_friend_name} (ID: {test_friend_id})")
        
        restaurant_info = action.get_friend_restaurant_info(test_friend_id)
        if restaurant_info:
            print(f"餐厅信息: 油量 {restaurant_info.get('bottle_num', 0)}")
        else:
            print("获取餐厅信息失败")
    else:
        print("没有好友可测试")

    # --- 测试 3: 查找特定食材的好友 ---
    print("\n\n" + "=" * 20 + " 3. 开始测试查找拥有特定食材的好友 " + "=" * 20)
    target_food = "神秘金蟾菇"
    friends_with_food = action.find_friends_with_food(target_food)
    if friends_with_food:
        print(f"找到 {len(friends_with_food)} 个好友拥有 '{target_food}':")
        for i, friend in enumerate(friends_with_food[:5]):  # 只显示前5个
            name = friend.get("res_name", "未知")
            count = friend.get("num", 0)
            level = friend.get("level", 0)
            print(f"  {i+1}. {name} (等级:{level}, 数量:{count})")
    else:
        print(f"没有好友拥有 '{target_food}'")

    # --- 测试 4: 模拟交换食材（使用假数据避免真实交换） ---
    print("\n\n" + "=" * 20 + " 4. 开始测试交换食材功能 " + "=" * 20)
    if friends_with_food and len(friends_with_food) > 0:
        test_friend = friends_with_food[0]
        print(f"模拟与 '{test_friend.get('res_name')}' 交换食材...")
        # 注意：这里使用模拟数据，避免真实交换
        # success, msg = action.exchange_food_with_friend(
        #     test_friend.get('res_id'), '228', '6'
        # )
        print("(跳过真实交换以避免消耗食材)")
    else:
        print("没有可交换的好友")

    # --- 测试 5: 列出食材信息 ---
    print("\n\n" + "=" * 20 + " 5. 开始测试食材信息查询 " + "=" * 20)
    foods = action.list_available_foods()
    print(f"总共有 {len(foods)} 种食材")
    
    # 显示不同等级的食材统计
    level_counts = {}
    for food in foods:
        level = food.get("level", "未知")
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print("各等级食材统计:")
    for level in sorted(level_counts.keys()):
        count = level_counts[level]
        level_name = {
            "1": "一级",
            "2": "二级", 
            "3": "三级",
            "4": "四级",
            "5": "五级",
            "6": "六级",
            "7": "神秘",
            "9": "万能"
        }.get(str(level), f"{level}级")
        print(f"  {level_name}食材: {count} 种")

    print("\n\n" + "#" * 20 + "  所有测试结束  " + "#" * 20)
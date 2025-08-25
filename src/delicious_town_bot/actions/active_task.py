"""
活跃度任务模块
用于领取每日活跃度奖励
"""
import time
from typing import Dict, Any, Optional, List, Tuple
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class ActiveTaskAction(BaseAction):
    """
    活跃度任务操作类，处理活跃度奖励领取
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res&m=ActiveTask"
        super().__init__(key=key, cookie=cookie, base_url=base_url)
        # 更新 Referer
        self.http_client.headers.update({
            'Referer': 'http://117.72.123.195/wap/res/active_task.html'
        })

    def receive_award(self, award_id: int) -> Dict[str, Any]:
        """
        领取活跃度奖励
        
        Args:
            award_id: 奖励ID
            - 1: 每日30活跃度奖励
            - 2: 每日50活跃度奖励  
            - 3: 每日100活跃度奖励
            - 4: 每日150活跃度奖励
            - 5: 周活跃200奖励
            - 6: 周活跃500奖励
            - 7: 周活跃800奖励
            - 8: 周活跃1000奖励
            
        Returns:
            Dict包含领取结果:
            {
                "success": bool,
                "message": str,
                "reward_items": str,  # 获得的奖励物品
                "data": dict  # 如果有返回数据
            }
        """
        print(f"[*] 正在尝试领取活跃度奖励 (ID: {award_id})...")
        
        action_path = "a=receiveAward"
        payload = {
            "award_id": str(award_id),
            "key": self.key
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            # 检查响应状态
            if response_data.get('status'):
                message = response_data.get('msg', '领取成功')
                
                # 解析奖励信息
                reward_items = ""
                if "获得物品:" in message:
                    # 提取获得物品信息
                    reward_start = message.find("获得物品:")
                    if reward_start != -1:
                        reward_items = message[reward_start:].replace("<br>", " ").strip()
                
                print(f"[+] 活跃度奖励领取成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "reward_items": reward_items,
                    "data": response_data.get('data', {})
                }
            else:
                error_msg = response_data.get('msg', '领取失败')
                print(f"[!] 活跃度奖励领取失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "reward_items": "",
                    "data": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 领取活跃度奖励失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "reward_items": "",
                "data": {}
            }

    def batch_receive_awards(self, award_ids: List[int] = None, interval: float = 1.0) -> Dict[str, Any]:
        """
        批量领取活跃度奖励
        
        Args:
            award_ids: 要领取的奖励ID列表，默认为[1,2,3,4,5,6,7,8]（全部奖励）
            interval: 每次领取间隔（秒）
            
        Returns:
            批量领取结果
        """
        if award_ids is None:
            award_ids = [1, 2, 3, 4, 5, 6, 7, 8]  # 默认尝试领取所有奖励
        
        print(f"[*] 开始批量领取活跃度奖励，奖励ID: {award_ids}...")
        
        results = {
            "success": True,
            "total_attempts": len(award_ids),
            "success_count": 0,
            "failed_count": 0,
            "award_details": [],
            "total_rewards": [],
            "message": ""
        }
        
        award_names = {
            1: "每日30活跃度奖励",
            2: "每日50活跃度奖励", 
            3: "每日100活跃度奖励",
            4: "每日150活跃度奖励",
            5: "周活跃200奖励",
            6: "周活跃500奖励",
            7: "周活跃800奖励",
            8: "周活跃1000奖励"
        }
        
        for i, award_id in enumerate(award_ids):
            award_name = award_names.get(award_id, f"奖励{award_id}")
            print(f"[*] 第 {i+1}/{len(award_ids)} 个奖励: {award_name}...")
            
            receive_result = self.receive_award(award_id)
            
            award_detail = {
                "award_id": award_id,
                "award_name": award_name,
                "success": receive_result["success"],
                "message": receive_result["message"],
                "reward_items": receive_result["reward_items"]
            }
            
            if receive_result["success"]:
                results["success_count"] += 1
                if receive_result["reward_items"]:
                    results["total_rewards"].append(receive_result["reward_items"])
                print(f"[+] {award_name} 领取成功")
            else:
                results["failed_count"] += 1
                print(f"[!] {award_name} 领取失败: {receive_result['message']}")
            
            results["award_details"].append(award_detail)
            
            # 间隔等待
            if i < len(award_ids) - 1:  # 最后一次不需要等待
                time.sleep(interval)
        
        # 生成总结
        success_rate = (results["success_count"] / len(award_ids) * 100) if award_ids else 0
        if results["success_count"] == len(award_ids):
            results["message"] = f"✅ 活跃度奖励全部领取成功！成功领取 {results['success_count']}/{len(award_ids)} 个奖励"
            results["success"] = True
        elif results["success_count"] > 0:
            results["message"] = f"⚠️ 活跃度奖励部分领取成功，成功 {results['success_count']} 个，失败 {results['failed_count']} 个 (成功率: {success_rate:.1f}%)"
            results["success"] = True  # 部分成功也算成功
        else:
            results["message"] = f"❌ 活跃度奖励领取失败，全部 {len(award_ids)} 个奖励都未能领取"
            results["success"] = False
        
        print(f"[+] {results['message']}")
        
        # 显示获得的奖励
        if results["total_rewards"]:
            print(f"[+] 总共获得奖励: {'; '.join(results['total_rewards'])}")
        
        return results

    def batch_receive_daily_awards(self, interval: float = 1.0) -> Dict[str, Any]:
        """
        批量领取每日活跃度奖励（奖励ID 1-4）
        
        Args:
            interval: 每次领取间隔（秒）
            
        Returns:
            批量领取结果
        """
        daily_award_ids = [1, 2, 3, 4]  # 每日活跃度奖励
        print(f"[*] 开始批量领取每日活跃度奖励...")
        return self.batch_receive_awards(award_ids=daily_award_ids, interval=interval)

    def batch_receive_weekly_awards(self, interval: float = 1.0) -> Dict[str, Any]:
        """
        批量领取周活跃度奖励（奖励ID 5-8）
        
        Args:
            interval: 每次领取间隔（秒）
            
        Returns:
            批量领取结果
        """
        weekly_award_ids = [5, 6, 7, 8]  # 周活跃度奖励
        print(f"[*] 开始批量领取周活跃度奖励...")
        return self.batch_receive_awards(award_ids=weekly_award_ids, interval=interval)

    def get_active_task_info(self) -> Dict[str, Any]:
        """
        获取活跃度任务信息
        
        Returns:
            活跃度任务信息
        """
        print(f"[*] 正在获取活跃度任务信息...")
        
        action_path = "a=index"
        
        try:
            response_data = self.get(action_path)
            
            if response_data.get('status'):
                data = response_data.get('data', {})
                print(f"[+] 活跃度任务信息获取成功")
                return {
                    "success": True,
                    "message": "获取活跃度任务信息成功",
                    "data": data
                }
            else:
                error_msg = response_data.get('msg', '获取活跃度任务信息失败')
                print(f"[Error] {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "data": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取活跃度任务信息失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "data": {}
            }


# ==============================================================================
#  独立测试脚本
# ==============================================================================
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")
    
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}

    active_task_action = ActiveTaskAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "=" * 20 + " 活跃度奖励功能测试 " + "=" * 20)

    # 测试获取活跃度任务信息
    print("\n--- 1. 获取活跃度任务信息 ---")
    task_info = active_task_action.get_active_task_info()
    if task_info.get("success"):
        print("活跃度任务信息获取成功")
    
    # 测试单个奖励领取
    print("\n--- 2. 测试领取每日30活跃度奖励 ---")
    single_result = active_task_action.receive_award(award_id=1)
    print(f"领取结果: {single_result}")
    
    # 测试领取周活跃度奖励
    print("\n--- 3. 测试领取周活跃200奖励 ---")
    weekly_result = active_task_action.receive_award(award_id=5)
    print(f"领取结果: {weekly_result}")
    
    # 测试批量领取（可以注释掉避免实际领取）
    print("\n--- 4. 测试批量领取所有活跃度奖励 ---")
    print("注意：这会实际领取奖励，确认后取消注释以下代码")
    # batch_result = active_task_action.batch_receive_awards()
    # print(f"批量领取所有奖励结果: {batch_result}")
    
    # 测试分别批量领取
    print("\n--- 5. 测试分别批量领取每日和周活跃度奖励 ---")
    print("注意：这会实际领取奖励，确认后取消注释以下代码")
    # daily_result = active_task_action.batch_receive_daily_awards()
    # print(f"每日活跃度奖励结果: {daily_result}")
    # weekly_result = active_task_action.batch_receive_weekly_awards()
    # print(f"周活跃度奖励结果: {weekly_result}")
    
    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
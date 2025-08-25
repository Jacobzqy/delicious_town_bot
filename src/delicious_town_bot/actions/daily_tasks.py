"""
日常任务管理模块
用于获取和完成日常活跃度任务
"""
from typing import Dict, Any, Optional, List
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class DailyTasksAction(BaseAction):
    """
    日常任务操作类，处理各种活跃度任务功能
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key=key, cookie=cookie, base_url=base_url)
        # 更新 Referer
        self.http_client.headers.update({
            'Referer': 'http://117.72.123.195/wap/res/active_task.html'
        })

    def get_daily_tasks(self, task_type: int = 1) -> Dict[str, Any]:
        """
        获取日常任务列表
        
        Args:
            task_type: 任务类型 (1=每日任务, 2=每周任务)
            
        Returns:
            Dict包含任务列表和奖励信息:
            {
                "success": bool,
                "message": str,
                "tasks": List[Dict],  # 任务列表
                "rewards": List[Dict],  # 奖励列表
                "user_info": Dict  # 用户活跃度信息
            }
        """
        print(f"[*] 正在获取{'每日' if task_type == 1 else '每周'}任务列表...")
        
        action_path = "m=ActiveTask&a=taskList"
        payload = {
            "type": str(task_type)
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            # 检查响应状态
            if response_data.get('status'):
                data = response_data.get('data', {})
                
                tasks = data.get('list', [])
                rewards = data.get('reward_list', [])
                user_info = data.get('info', {})
                
                print(f"[+] 成功获取任务列表: {len(tasks)} 个任务, {len(rewards)} 个奖励")
                
                return {
                    "success": True,
                    "message": "获取任务列表成功",
                    "tasks": tasks,
                    "rewards": rewards,
                    "user_info": user_info
                }
            else:
                error_msg = response_data.get('msg', '获取任务列表失败')
                print(f"[!] 获取任务列表失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "tasks": [],
                    "rewards": [],
                    "user_info": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取任务列表失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "tasks": [],
                "rewards": [],
                "user_info": {}
            }

    def get_task_summary(self, username: str = "") -> Dict[str, Any]:
        """
        获取任务完成情况汇总
        
        Returns:
            Dict包含每日和每周任务汇总信息
        """
        print(f"[*] 正在获取 {username} 的任务完成情况汇总...")
        
        summary = {
            "success": True,
            "username": username,
            "daily_summary": {},
            "weekly_summary": {},
            "daily_success": False,
            "weekly_success": False
        }
        
        # 获取每日任务
        daily_result = self.get_daily_tasks(task_type=1)
        summary["daily_success"] = daily_result["success"]
        if daily_result["success"]:
            tasks = daily_result["tasks"]
            user_info = daily_result["user_info"]
            
            completed_count = sum(1 for task in tasks if int(task.get("finish_num", 0)) >= int(task.get("max_num", 1)))
            total_count = len(tasks)
            daily_active = int(user_info.get("active_num_day", 0))
            
            summary["daily_summary"] = {
                "completed_tasks": completed_count,
                "total_tasks": total_count,
                "completion_rate": (completed_count / total_count * 100) if total_count > 0 else 0,
                "daily_active_points": daily_active,
                "tasks": tasks
            }
        else:
            # 每日任务加载失败时的默认数据
            summary["daily_summary"] = {
                "completed_tasks": 0,
                "total_tasks": 0,
                "completion_rate": 0,
                "daily_active_points": 0,
                "tasks": [],
                "error": daily_result.get("message", "未知错误")
            }
        
        # 获取每周任务
        weekly_result = self.get_daily_tasks(task_type=2)
        summary["weekly_success"] = weekly_result["success"]
        if weekly_result["success"]:
            tasks = weekly_result["tasks"]
            user_info = weekly_result["user_info"]
            
            completed_count = sum(1 for task in tasks if int(task.get("finish_num", 0)) >= int(task.get("max_num", 1)))
            total_count = len(tasks)
            weekly_active = int(user_info.get("active_num_week", 0))
            
            summary["weekly_summary"] = {
                "completed_tasks": completed_count,
                "total_tasks": total_count,
                "completion_rate": (completed_count / total_count * 100) if total_count > 0 else 0,
                "weekly_active_points": weekly_active,
                "tasks": tasks
            }
        else:
            # 每周任务加载失败时的默认数据
            summary["weekly_summary"] = {
                "completed_tasks": 0,
                "total_tasks": 0,
                "completion_rate": 0,
                "weekly_active_points": 0,
                "tasks": [],
                "error": weekly_result.get("message", "未知错误")
            }
        
        # 只有当两个都成功时，整体才算成功
        summary["success"] = summary["daily_success"] and summary["weekly_success"]
        
        return summary

    def get_incomplete_tasks(self, task_type: int = 1) -> List[Dict[str, Any]]:
        """
        获取未完成的任务列表
        
        Args:
            task_type: 任务类型 (1=每日任务, 2=每周任务)
            
        Returns:
            List[Dict] 未完成的任务列表
        """
        result = self.get_daily_tasks(task_type)
        if not result["success"]:
            return []
        
        tasks = result["tasks"]
        incomplete_tasks = []
        
        for task in tasks:
            try:
                finish_num = int(task.get("finish_num", 0))
                max_num = int(task.get("max_num", 1))
                
                if finish_num < max_num:
                    task["remaining_count"] = max_num - finish_num
                    incomplete_tasks.append(task)
            except (ValueError, TypeError):
                # 如果转换失败，跳过这个任务
                print(f"[Warning] 跳过任务 {task.get('name', 'Unknown')}: 数据格式异常")
                continue
        
        return incomplete_tasks

    def get_completable_tasks(self) -> Dict[str, List[Dict]]:
        """
        获取可以通过Bot完成的任务列表
        
        Returns:
            Dict包含可完成的每日和每周任务
        """
        # 定义可以自动完成的任务代码
        completable_task_codes = {
            "sign",  # 签到
            "tower",  # 成功挑战厨塔npc
            "shrine",  # 击败神殿守卫
            "monster",  # 打怪兽
            "strengthen_equip",  # 强化厨具
            "add_ins",  # 摆放一个设施
            "cookbook"  # 学习/升级食谱
        }
        
        result = {
            "daily_completable": [],
            "weekly_completable": []
        }
        
        # 获取每日未完成任务
        daily_incomplete = self.get_incomplete_tasks(task_type=1)
        for task in daily_incomplete:
            if task.get("code") in completable_task_codes:
                result["daily_completable"].append(task)
        
        # 获取每周未完成任务
        weekly_incomplete = self.get_incomplete_tasks(task_type=2)
        for task in weekly_incomplete:
            if task.get("code") in completable_task_codes:
                result["weekly_completable"].append(task)
        
        return result


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

    daily_tasks_action = DailyTasksAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "=" * 20 + " 日常任务功能测试 " + "=" * 20)

    # 测试获取每日任务
    print("\n--- 1. 获取每日任务列表 ---")
    daily_result = daily_tasks_action.get_daily_tasks(task_type=1)
    if daily_result["success"]:
        print(f"每日任务数量: {len(daily_result['tasks'])}")
        for task in daily_result['tasks'][:3]:  # 显示前3个任务
            print(f"- {task['name']}: {task['finish_num']}/{task['max_num']} (活跃度+{task['active_num']})")
    
    # 测试获取任务汇总
    print("\n--- 2. 获取任务汇总 ---")
    summary = daily_tasks_action.get_task_summary("测试账号")
    daily_summary = summary.get("daily_summary", {})
    if daily_summary:
        print(f"每日任务完成度: {daily_summary['completed_tasks']}/{daily_summary['total_tasks']} ({daily_summary['completion_rate']:.1f}%)")
        print(f"今日活跃度: {daily_summary['daily_active_points']}")
    
    # 测试获取可完成任务
    print("\n--- 3. 获取可完成任务 ---")
    completable = daily_tasks_action.get_completable_tasks()
    print(f"可完成每日任务: {len(completable['daily_completable'])} 个")
    for task in completable['daily_completable']:
        print(f"- {task['name']} ({task['code']}): 剩余 {task['remaining_count']} 次")

    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
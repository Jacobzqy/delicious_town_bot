import re
from src.delicious_town_bot.action.base_action import BaseAction, BusinessLogicError
from typing import Tuple, Dict, Any, Union


class TaskActions(BaseAction):
    """封装所有与任务（Task）相关的游戏操作。"""

    def __init__(self, key: str, cookie: Dict[str, str]):
        base_url = "http://117.72.123.195/index.php?g=Res&m=Task"
        super().__init__(key, base_url, cookie)

    def accept_task(self, task_id: int) -> Tuple[bool, str]:
        """
        接收一个新任务。

        :param task_id: 要接收的任务的 ID。
        :return: 一个元组 (是否成功, 服务器消息)。
        """
        print(f"[*] 正在尝试接收任务, ID: {task_id}...")
        payload = {"task_id": str(task_id)}
        try:
            response = self.post(action="add_task", data=payload)
            msg = response.get("msg", "未知成功消息")
            print(f"[Success] {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 接收任务 {task_id} 失败。")
            return False, str(e)

    def claim_task_reward(self, task_id: int) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        领取已完成任务的奖励。
        此方法现在会尝试解析奖励内容。

        :param task_id: 要领取奖励的任务的 ID。
        :return: 一个元组 (是否成功, 奖励字典或错误消息字符串)。
                 成功时，第二个元素是字典，例如: {'gold': 5000, 'exp': 100, 'items': '搬家卡x1'}
                 失败时，第二个元素是错误消息字符串。
        """
        print(f"[*] 正在尝试领取任务奖励, ID: {task_id}...")
        payload = {"task_id": str(task_id)}
        try:
            # action 名已根据抓包结果从 'get_task_reward' 更正为 'finish'
            response = self.post(action="finish", data=payload)
            msg = response.get("msg", "")

            # --- 新增：解析奖励内容 ---
            rewards = self._parse_rewards(msg)
            print(f"[Success] {msg}")

            return True, rewards

        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 领取任务 {task_id} 的奖励失败。")
            return False, str(e)

    def _parse_rewards(self, msg: str) -> Dict[str, Any]:
        """一个辅助方法，用于从消息字符串中解析奖励。"""
        rewards = {}

        # 使用正则表达式查找金币
        gold_match = re.search(r"金币:(\d+)", msg)
        if gold_match:
            rewards['gold'] = int(gold_match.group(1))

        # 使用正则表达式查找经验
        exp_match = re.search(r"经验:(\d+)", msg)
        if exp_match:
            rewards['exp'] = int(exp_match.group(1))

        # 使用正则表达式查找物品
        items_match = re.search(r"获得物品:(.+)", msg)
        if items_match:
            rewards['items'] = items_match.group(1).strip()

        # 如果什么都没解析到，至少返回原始消息
        if not rewards:
            return {'raw_message': msg}

        return rewards


# =======================================================
#               可以直接运行此文件进行测试
# =======================================================
if __name__ == '__main__':
    # --- 填写你的测试信息 ---
    TEST_KEY = "bbdb766a15d8ae600b31f6514a08cce3"
    TEST_COOKIE = {"PHPSESSID": "n4emj7fje28h1bpcnt4g32ta37"}
    # -----------------------

    print("--- 开始测试 TaskActions (v2) ---")

    task_action = TaskActions(key=TEST_KEY, cookie=TEST_COOKIE)

    # 2. 测试接收新手任务1
    # 根据你的 curl，新手任务ID是 1
    success, message = task_action.accept_task(task_id=1)
    print(f"操作结果: Success={success}, Message='{message}'")

    print("\n" + "=" * 30 + "\n")

    # --- 测试领取奖励 ---
    # 使用你抓包得到的已完成任务ID进行测试
    COMPLETED_TASK_ID = 14201

    success, result = task_action.claim_task_reward(task_id=COMPLETED_TASK_ID)

    print("\n--- 操作结果 ---")
    print(f"是否成功: {success}")

    if success:
        print("解析出的奖励:")
        # result 是一个字典，我们可以漂亮地打印它
        for key, value in result.items():
            print(f"  - {key}: {value}")
    else:
        # result 是一个错误消息字符串
        print(f"错误信息: {result}")

    print("\n--- TaskActions 测试结束 ---")
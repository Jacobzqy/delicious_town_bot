import re
import os
from dotenv import load_dotenv
from typing import Tuple, Dict, Union, Optional

# 确保能正确导入基类和自定义异常
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class DailyActions(BaseAction):
    """封装所有与每日福利、签到、抽奖等相关的游戏操作。"""

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        """
        初始化每日福利操作类。
        """
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key, base_url, cookie)

    def sign_in(self) -> Tuple[bool, Union[str, Dict[str, str]]]:
        """
        执行每日签到。

        :return: (是否成功, 包含奖励物品的字典或错误/成功消息字符串)。
        """
        print("[*] 正在尝试进行每日签到...")
        try:
            # 调用 m=Sign&a=sign
            response = self.post(action_path="m=Sign&a=sign")
            msg = response.get("msg", "")
            details = self._parse_signin_reward(msg)
            print(f"[Success] {msg}")
            return True, details
        except (BusinessLogicError, ConnectionError) as e:
            # 签到失败（例如今天已经签过）会由 BusinessLogicError 捕获
            print(f"[Info] 签到操作未能成功: {e}")
            return False, str(e)

    def _parse_signin_reward(self, msg: str) -> Dict[str, str]:
        """辅助方法，用于从签到成功的消息中解析奖励。"""
        # msg 格式: "签到成功!获得:获得物品:今日礼包x1"
        match = re.search(r"获得物品:(.+)", msg)
        if match:
            return {"item_gained": match.group(1).strip()}
        return {"raw_message": msg}

    # --- 后续待实现的功能占位 ---

    def claim_activity_reward(self, reward_id: Union[int, str]) -> Tuple[bool, str]:
        """(待实现) 领取指定的活跃度奖励。"""
        print(f"[Info] 'claim_activity_reward' 功能尚未实现。")
        return False, "功能未实现"

    def perform_lottery_draw(self) -> Tuple[bool, str]:
        """(待实现) 执行一次抽奖。"""
        print(f"[Info] 'perform_lottery_draw' 功能尚未实现。")
        return False, "功能未实现"

    def play_rock_paper_scissors(self, choice: int) -> Tuple[bool, str]:
        """
        (待实现) 进行一次猜拳游戏。
        :param choice: 可能是 1=石头, 2=剪刀, 3=布。
        """
        print(f"[Info] 'play_rock_paper_scissors' 功能尚未实现。")
        return False, "功能未实现"

    def play_guess_the_cup(self, choice: int) -> Tuple[bool, str]:
        """
        (待实现) 进行一次猜酒杯游戏。
        :param choice: 选择的杯子编号。
        """
        print(f"[Info] 'play_guess_the_cup' 功能尚未实现。")
        return False, "功能未实现"

    def exchange_mystic_ingredient(self, target_ingredient_id: int) -> Tuple[bool, str]:
        """(待实现) 使用某种道具兑换指定的神秘食材。"""
        print(f"[Info] 'exchange_mystic_ingredient' 功能尚未实现。")
        return False, "功能未实现"


# =======================================================
#               可以直接运行此文件进行测试
# =======================================================
if __name__ == '__main__':
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY: raise ValueError("请在 .env 中设置 TEST_KEY")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR} if TEST_COOKIE_STR else None

    action = DailyActions(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "#" * 20 + "  每日福利模块测试  " + "#" * 20)

    # --- 测试 1: 每日签到 ---
    print("\n\n" + "=" * 20 + " 1. 开始测试每日签到 " + "=" * 20)

    success, result = action.sign_in()

    print("\n--- 签到结果 ---")
    print(f"是否成功: {success}")
    if success:
        print("解析出的奖励:", result)
    else:
        print(f"服务器消息: {result}")

    print("\n\n" + "#" * 20 + "  所有测试结束  " + "#" * 20)
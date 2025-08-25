import os
import random
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from delicious_town_bot.constants import Move, GameResult, GuessCupResult
from delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


# --- 数据类定义 ---
@dataclass
class CupGameState:
    """封装猜酒杯游戏当前状态的数据结构，使代码更清晰、易用。"""
    level: int  # 当前轮数
    max_cup_number: int  # 可选的最大酒杯编号 (level + 1)
    potential_rewards: str  # 从 msg 字段解析出的奖励信息


# --- Action 类实现 ---
class LotteryActions(BaseAction):
    """
    封装所有抽奖相关的操作 (对应游戏中的“酒吧”模块)。
    包含了猜拳、猜酒杯等功能。
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]]):
        """
        初始化抽奖操作实例。
        """
        base_url = "http://117.72.123.195/index.php?g=Res&m=Bar"
        super().__init__(key=key, base_url=base_url, cookie=cookie)

    def play_rock_paper_scissors(self, move: Move) -> Tuple[GameResult, str]:
        """
        执行一次猜拳操作。

        :param move: 你要出的拳，使用 Move 枚举 (Move.ROCK, Move.SCISSORS, Move.PAPER)。
        :return: 一个元组，包含游戏结果 (GameResult 枚举) 和结果信息。
        """
        print(f"[Info] 开始猜拳，出拳: {move.name}")

        action_path = 'a=cq'
        data = {'type': move.value}

        try:
            response = self.post(action_path, data=data)
            msg = response.get('msg', '')
            # print(f"[Debug] 收到猜拳响应: {msg}") # 如需详细调试可取消此行注释

            if "平局" in msg:
                result = GameResult.DRAW
                details = "平局，不消耗礼券"
            elif "恭喜你赢了" in msg:
                result = GameResult.WIN
                details = msg.split('<br>')[-1] if '<br>' in msg else "未知奖励"
            elif "你输了" in msg:
                result = GameResult.LOSS
                details = msg.split(',')[-1] if ',' in msg else "未知惩罚"
            else:
                print(f"[Warning] 无法解析的猜拳结果: {msg}")
                result = GameResult.DRAW
                details = f"未知结果: {msg}"

            print(f"[Info] 猜拳结果: {result.value}, 详情: {details}")
            return result, details

        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 猜拳时发生错误: {e}")
            raise

    def get_cup_game_info(self) -> CupGameState:
        """
        获取当前猜酒杯游戏的状态信息。

        :return: 一个 CupGameState 对象，包含了轮数、可选杯子数量和奖励信息。
        :raises BusinessLogicError: 如果游戏已结束或未开始。
        :raises ValueError: 如果 API 响应格式不正确。
        """
        print("[Info] 正在获取猜酒杯游戏状态...")
        action_path = 'a=cjb_info'

        try:
            response = self.post(action_path)
            game_data = response.get('data')
            if not isinstance(game_data, dict):
                raise ValueError(f"API返回的'data'字段格式不正确，期望是字典，实际是 {type(game_data)}")

            level = int(game_data.get('level', 0))
            msg = response.get('msg', '')

            if level == 0:
                if "已经全部猜完" in msg or "活动尚未开始" in msg:
                    raise BusinessLogicError(msg)
                else:
                    raise ValueError("无法从API响应中获取有效的 'level' 值。")

            max_cups = level + 1
            rewards_info = msg.replace('<br>', '\n')

            print(f"[Info] 获取状态成功: 当前第 {level} 轮, 可选酒杯范围 1-{max_cups}。")

            return CupGameState(
                level=level,
                max_cup_number=max_cups,
                potential_rewards=rewards_info
            )
        except (BusinessLogicError, ValueError) as e:
            print(f"[Warning] 获取猜酒杯状态失败: {e}")
            raise
        except ConnectionError as e:
            print(f"[Error] 获取猜酒杯状态时网络连接失败: {e}")
            raise

    def guess_cup(self, cup_number: int) -> Tuple[GuessCupResult, str]:
        """
        选择一个酒杯进行猜测。

        :param cup_number: 你要选择的酒杯编号 (例如 1, 2, 3...)。
        :return: 一个元组，包含猜测结果 (GuessCupResult 枚举) 和详细信息 (奖励列表或结束语)。
        """
        print(f"[Info] 执行猜酒杯操作，选择: 第 {cup_number} 号酒杯")
        action_path = 'a=cjb'
        data = {'type': cup_number}

        try:
            response = self.post(action_path, data=data)
            msg = response.get('msg', '')
            # print(f"[Debug] 收到猜酒杯响应: {msg}") # 如需详细调试可取消此行注释
            details = msg.replace('<br>', '\n')

            if "恭喜你猜中了最后一轮" in msg:
                result = GuessCupResult.GUESSED_CORRECT_FINAL
            elif "恭喜你猜中了" in msg:
                result = GuessCupResult.GUESSED_CORRECT_CONTINUE
            elif "猜错" in msg or "遗憾" in msg:
                result = GuessCupResult.GUESSED_WRONG_END
            else:
                print(f"[Error] 无法解析的猜酒杯结果: {msg}")
                result = GuessCupResult.GUESSED_WRONG_END
                details = f"未知结果: {msg}"

            print(f"[Info] 猜酒杯结果: {result.value}")
            return result, details

        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 猜测酒杯 #{cup_number} 时发生错误: {e}")
            raise


# ==============================================================================
#  独立测试脚本 (Standalone Test Script)
# ==============================================================================
if __name__ == '__main__':
    # --- 环境设置 ---
    from dotenv import load_dotenv

    # 加载 .env 文件中的环境变量
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")

    # 校验环境变量
    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在项目根目录的 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")

    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}

    # 实例化 Action 类
    lottery_bot = LotteryActions(key=TEST_KEY, cookie=TEST_COOKIE_DICT)
    print("\n--- LotteryActions 全面测试开始 ---\n")

    # --- 1. 猜拳功能测试 ---
    print("--- 1. 测试猜拳功能 (play_rock_paper_scissors) ---")
    lottery_bot.play_rock_paper_scissors(Move.PAPER)
    print(f"[*] 调用演示: lottery_bot.play_rock_paper_scissors(Move.PAPER)")
    print("[!] 注意：为防止消耗您的游戏券，实际调用已被注释。")
    time.sleep(1)

    # --- 2. 猜酒杯工作流测试 ---
    print("\n--- 2. 测试猜酒杯完整工作流 ---")

    # [测试 2.1] 获取游戏状态
    print("\n--- [测试 2.1] 获取猜酒杯状态 (get_cup_game_info) ---")
    try:
        game_state = lottery_bot.get_cup_game_info()
        print(f"[+] 成功获取游戏状态: 当前第 {game_state.level} 轮, 可选 {game_state.max_cup_number} 个杯子。")
        print(f"[*] 本轮潜在奖励预览:\n{game_state.potential_rewards}")
    except (BusinessLogicError, ConnectionError, ValueError) as e:
        print(f"[!] 获取游戏状态失败: {e}")
        game_state = None

    time.sleep(1)

    # [测试 2.2] 执行一次猜测
    if game_state:
        print("\n--- [测试 2.2] 执行单次猜测 (guess_cup) ---")
        choice = random.randint(1, game_state.max_cup_number)
        lottery_bot.guess_cup(cup_number=choice)
        print(f"[*] 调用演示: lottery_bot.guess_cup(cup_number={choice})")
        print("[!] 注意：为防止消耗您的游戏机会，实际调用已被注释。")
    else:
        print("\n[!] 因未能获取游戏状态，跳过单次猜测测试。")

    time.sleep(1)

    # --- 3. 集成/策略测试 ---
    print("\n--- 3. 测试完整的自动化游戏策略 (play_one_full_cup_game_test) ---")


    def play_one_full_cup_game_test(action_bot: LotteryActions):
        """用于测试的完整游戏策略函数。"""
        print("[*] 开始执行一轮完整的猜酒杯游戏策略...")
        while True:
            try:
                state = action_bot.get_cup_game_info()
                print(f"    - [状态] 当前第 {state.level} 轮, 可选 1-{state.max_cup_number}。")

                choice = random.randint(1, state.max_cup_number)
                print(f"    - [决策] 随机选择第 {choice} 号。")

                result, details = action_bot.guess_cup(choice)

                if result == GuessCupResult.GUESSED_CORRECT_CONTINUE:
                    print(f"    - [结果] ✅ 猜对了！准备进入下一轮。")
                    time.sleep(2)
                    continue
                else:
                    if result == GuessCupResult.GUESSED_CORRECT_FINAL:
                        print(f"    - [结果] 🎉 赢得最终大奖！")
                    else:
                        print(f"    - [结果] ❌ 猜错了，游戏结束。")
                    print(f"    - [结算详情]\n{details}")
                    break
            except BusinessLogicError as e:
                print(f"    - [中断] 游戏无法继续: {e}")
                break
            except Exception as e:
                print(f"    - [异常] 发生未知错误: {e}")
                break


    play_one_full_cup_game_test(lottery_bot)
    print("[*] 完整策略函数 'play_one_full_cup_game_test' 已定义。")
    print("[!] 注意：这是一个消耗性的集成测试，默认不执行。请在需要时取消对上面一行的注释来运行。")

    print("\n--- LotteryActions 所有测试执行完毕 ---")
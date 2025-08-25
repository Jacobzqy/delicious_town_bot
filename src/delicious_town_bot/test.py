# run_cup_game.py

import os
import random
import time
from collections import Counter
from typing import List

from dotenv import load_dotenv

# 导入我们封装好的 Action 类和相关定义
from delicious_town_bot.actions.lottery import (
    LotteryActions,
    GuessCupResult,
    BusinessLogicError,
)


def parse_rewards(details_text: str) -> List[str]:
    """
    从服务器返回的详情文本中解析出具体的奖励物品列表。

    :param details_text: guess_cup 方法返回的详情字符串。
    :return: 一个包含所有奖励物品的列表，例如 ["粉条x1", "米酒x1"]。
    """
    rewards = []
    # 按行分割，处理多行奖励
    lines = details_text.strip().split('\n')

    for line in lines:
        cleaned_line = line.strip()
        # 核心筛选逻辑：我们认为包含'x'且不包含':'的非空行就是奖励行
        # 这可以有效过滤掉 "获得食材:"、"恭喜你..." 等非奖励行
        if cleaned_line and 'x' in cleaned_line and ':' not in cleaned_line:
            rewards.append(cleaned_line)

    return rewards


def run_automated_cup_game():
    """
    主函数，执行完整的自动化猜酒杯流程。
    """
    # --- 1. 初始化 ---
    print("=" * 40)
    print("      自动猜酒杯脚本启动      ")
    print("=" * 40)

    # 加载 .env 文件中的环境变量
    load_dotenv()
    key = os.getenv("TEST_KEY")
    cookie_str = os.getenv("TEST_COOKIE")

    # 校验环境变量
    if not key or not cookie_str:
        print("[Error] 请在项目根目录的 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")
        return

    cookie = {"PHPSESSID": cookie_str}

    # 实例化 Action
    action_bot = LotteryActions(key=key, cookie=cookie)

    # 用于存储所有获得的奖励
    total_rewards_list: List[str] = []
    game_count = 0

    # --- 2. 主循环：持续玩游戏 ---
    try:
        while True:
            game_count += 1
            print(f"\n--- 开始第 {game_count} 场游戏 ---")

            # --- 内部循环：进行一整场游戏（从第1轮到结束） ---
            while True:
                try:
                    # 获取当前轮的状态
                    game_state = action_bot.get_cup_game_info()
                    print(f"  [状态] 当前第 {game_state.level} 轮, 可选 1-{game_state.max_cup_number}。")

                except BusinessLogicError as e:
                    # 这是主要的退出点，通常是因为礼券不足
                    print(f"\n[!] 无法开始新一轮游戏: {e}")
                    print("[!] 脚本即将退出...")
                    # 跳出所有循环，执行最终的奖励统计
                    raise StopIteration from e

                # 制定策略：随机选择一个
                my_choice = random.randint(1, game_state.max_cup_number)
                print(f"  [决策] 随机选择第 {my_choice} 号。")

                # 执行猜测并获取结果
                result, details = action_bot.guess_cup(my_choice)

                # 如果游戏结束，解析并记录奖励
                if result in [GuessCupResult.GUESSED_CORRECT_FINAL, GuessCupResult.GUESSED_WRONG_END]:
                    current_rewards = parse_rewards(details)
                    if current_rewards:
                        print(f"  [结算] 本场获得奖励: {', '.join(current_rewards)}")
                        total_rewards_list.extend(current_rewards)

                    if result == GuessCupResult.GUESSED_CORRECT_FINAL:
                        print("  [结果] 🎉 赢得最终大奖！本场游戏结束。")
                    else:
                        print("  [结果] ❌ 猜错了，本场游戏结束。")

                    # 跳出内部循环，以开始下一场新游戏
                    break
                else:  # GUESSED_CORRECT_CONTINUE
                    print("  [结果] ✅ 猜对了！准备进入下一轮。")
                    time.sleep(random.uniform(0.1, 0.2))  # 随机等待1.5-3秒，模拟人类操作

            # 一场游戏结束后，稍作等待
            print("--- 本场游戏结束，准备开始下一场 ---")
            time.sleep(random.uniform(0.1, 0.2))

    except (StopIteration, KeyboardInterrupt):
        # 捕获我们自己抛出的 StopIteration 或用户按 Ctrl+C 来正常退出
        print("\n脚本已停止。")
    except ConnectionError as e:
        print(f"\n[Fatal] 网络连接失败，脚本被迫终止: {e}")
    except Exception as e:
        print(f"\n[Fatal] 发生未知严重错误，脚本被迫终止: {e}")

    # --- 3. 最终奖励总结 ---
    finally:
        print("\n" + "=" * 40)
        print("      本次运行总奖励统计      ")
        print("=" * 40)

        if not total_rewards_list:
            print("本次运行没有获得任何奖励。")
        else:
            # 使用 Counter 来自动统计每种物品的数量
            reward_summary = Counter(total_rewards_list)
            # 为了美观，找到最长的物品名称，用于对齐
            max_len = max(len(item) for item in reward_summary.keys()) if reward_summary else 0

            for item, count in sorted(reward_summary.items()):
                print(f"  - {item.ljust(max_len)} : {count} 个")

        print("\n脚本执行完毕。")


if __name__ == '__main__':
    run_automated_cup_game()
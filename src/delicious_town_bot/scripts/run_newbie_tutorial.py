#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_newbie_tutorial.py
----------------------
最终版新手任务脚本。
严格按照任务先后顺序，串行执行每一个任务的全流程。
包含最健壮的容错机制和状态刷新逻辑。
"""
import os
import json
import time
import random
from pathlib import Path
from typing import Callable, Any, Dict

# --- 核心模块导入 ---
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.delicious_town_bot.utils.account_manager import AccountManager, Account
from src.delicious_town_bot.actions.task import TaskActions
from src.delicious_town_bot.actions.restaurant import RestaurantActions
from src.delicious_town_bot.actions.food import FoodActions
from src.delicious_town_bot.actions.cooking import CookingActions
from src.delicious_town_bot.actions.daily import DailyActions
from src.delicious_town_bot.actions.friend import FriendActions

# --- 新手流程常量配置 ---
TASK_MAPPING = {
    "REFILL_OIL": {"accept_id": 1, "code": "101", "name": "添油任务"},
    "BUY_FOOD": {"accept_id": 6, "code": "106", "name": "买菜任务"},
    "LEARN_RECIPE": {"accept_id": 2, "code": "102", "name": "学习食谱任务"},
    "UPGRADE_STAR": {"accept_id": 3, "code": "103", "name": "升星级任务"},
    "PLACE_FACILITY": {"accept_id": 4, "code": "104", "name": "摆放设施任务"},
    "SIGN_IN": {"accept_id": 11, "code": "111", "name": "签到任务"},
    "OPEN_SHOP": {"accept_id": 5, "code": "105", "name": "开店成功任务"},
    "EXCHANGE_FOOD": {"accept_id": 12, "code": "112", "name": "兑换食材任务"},
    "ONLINE_30MIN": {"accept_id": 13, "code": "113", "name": "在线30分钟任务"},
    "PLAY_ONE_DAY": {"accept_id": 14, "code": "114", "name": "游戏一天任务"},
}
RECIPE_CODE_TO_LEARN = 488
FACILITY_CODE_TO_PLACE = 30201
FACILITY_POSITION = 1
FRIENDS_TO_ADD = [1271, 1272] + list(range(1277, 1328))


# --- 辅助函数 ---
def perform_sequential_task(task_actions: TaskActions, task_info: Dict, action_function: Callable = None,
                            *action_args: Any) -> bool:
    """
    完整地、串行地执行单个任务的全流程。
    包含最健壮的容错和刷新机制。
    """
    accept_id = task_info['accept_id']
    task_code = task_info.get('code')
    task_name = task_info['name']

    print(f"\n----- 开始串行任务: 【{task_name}】 (接受ID: {accept_id}) -----")

    # 步骤 1: 接受任务
    success, msg = task_actions.accept_task(accept_id)
    non_fatal_messages = ["已接", "已完成", "不能再接受"]
    is_real_failure = not success and not any(keyword in msg for keyword in non_fatal_messages)
    if is_real_failure:
        print(f"❌ 接受任务 '{task_name}' 失败: {msg}。中止该账号后续流程。")
        return False
    print(f"[*] 任务 '{task_name}' 已接受或确认已在任务列表中。")
    time.sleep(random.uniform(1.0, 1.5))

    # 步骤 2: 执行核心动作 (如果需要)
    if action_function:
        try:
            # 【新增】在执行动作前，调用一次任务查询接口来刷新服务器状态
            # time.sleep(1)
            print("[*] 正在刷新服务器状态...")
            task_actions.get_claimable_tasks_by_code()
            # time.sleep(1)
            print("[*] 正在刷新服务器状态...")
            task_actions.get_claimable_tasks_by_code()
            # time.sleep(1)
            print("[*] 正在刷新服务器状态...")
            task_actions.get_claimable_tasks_by_code()
            # time.sleep(1)

            print(f"[*] 正在为任务 '{task_name}' 执行核心动作...")
            action_function(*action_args)
            print(f"[✔] 核心动作执行完毕。")
        except Exception as e:
            print(f"❌ 核心动作执行失败: {e}。中止该账号后续流程。")
            return False

    time.sleep(random.uniform(1.0, 1.5))

    # 步骤 3: 领取奖励
    if task_code:
        # time.sleep(1)
        print("[*] 正在刷新服务器状态...")
        task_actions.get_claimable_tasks_by_code()
        # time.sleep(1)
        print("[*] 正在刷新服务器状态...")
        task_actions.get_claimable_tasks_by_code()
        # time.sleep(1)
        print("[*] 正在刷新服务器状态...")
        task_actions.get_claimable_tasks_by_code()
        # time.sleep(1)
        claimable_map = task_actions.get_claimable_tasks_by_code()
        claim_id = claimable_map.get(task_code)

        if not claim_id and not action_function:
            time.sleep(2)
            claimable_map = task_actions.get_claimable_tasks_by_code()
            claim_id = claimable_map.get(task_code)

        if claim_id:
            print(f"[*] 发现任务 '{task_name}' 的可领奖ID: {claim_id}，正在领取...")
            success, result = task_actions.claim_task_reward(int(claim_id))
            if not success and "已领取" not in str(result):
                print(f"❌ 领取任务 '{task_name}' 奖励 (ID:{claim_id}) 失败: {result}。中止该账号后续流程。")
                return False
            print(f"[✔] 任务 '{task_name}' 奖励已领取或确认已领取。")
        else:
            if task_name != "游戏一天任务":
                print(f"[Info] 未找到任务 '{task_name}' (Code: {task_code}) 的可领奖ID，可能已被领取。继续执行。")

    print(f"----- 任务 【{task_name}】 成功结束 -----")
    return True


def run_tutorial_for_account(account: Account):
    # ... (此函数无变化) ...
    print("\n" + "=" * 50)
    print(f"🚀 开始为账号【{account.username}】执行新手流程...")
    print("=" * 50)
    cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
    task_actions = TaskActions(key=account.key, cookie=cookie_dict)
    restaurant_actions = RestaurantActions(key=account.key, cookie=cookie_dict)
    food_actions = FoodActions(key=account.key, cookie=cookie_dict)
    cooking_actions = CookingActions(key=account.key, cookie=cookie_dict)
    daily_actions = DailyActions(key=account.key, cookie=cookie_dict)
    friend_actions = FriendActions(key=account.key, cookie=cookie_dict)
    try:
        if not perform_sequential_task(task_actions, TASK_MAPPING["REFILL_OIL"], restaurant_actions.refill_oil): return
        # food_list = food_actions.get_food_list()
        # if not food_list:
        #    print("❌ 未能获取蔬菜列表，无法执行买菜任务。中止该账号后续流程。")
        #    return
        # food_to_buy = food_list[0]['name']
        # print(f"[*] 动态选择购买的蔬菜是: {food_to_buy}")
        # if not perform_sequential_task(task_actions, TASK_MAPPING["BUY_FOOD"], food_actions.buy_food_by_name,
        #                               food_to_buy, 1): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["LEARN_RECIPE"], cooking_actions.learn_recipe,
        #                               RECIPE_CODE_TO_LEARN): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["UPGRADE_STAR"],
        #                                restaurant_actions.execute_star_upgrade): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["PLACE_FACILITY"], restaurant_actions.place_facility,
        #                               FACILITY_CODE_TO_PLACE, FACILITY_POSITION): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["SIGN_IN"], daily_actions.sign_in): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["OPEN_SHOP"]): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["EXCHANGE_FOOD"]): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["ONLINE_30MIN"]): return
        # if not perform_sequential_task(task_actions, TASK_MAPPING["PLAY_ONE_DAY"]): return
        # print(f"\n[*] 正在批量添加 {len(FRIENDS_TO_ADD)} 位好友...")
        # for friend_id in FRIENDS_TO_ADD:
        #    friend_actions.add_friend(friend_res_id=friend_id)
        #    time.sleep(random.uniform(0.3, 0.6))
        #print(f"[✔] 所有好友添加完毕。")
        print(f"\n✅ 账号【{account.username}】的新手流程执行完毕！")
    except Exception as e:
        print(f"❌❌❌ 账号【{account.username}】在执行过程中遇到严重错误: {e}", file=sys.stderr)
    print("=" * 50)


def main():
    # ... (此函数无变化) ...
    print("▶️  启动新手流程自动化脚本...")
    # time.sleep(600)
    account_manager = AccountManager()
    all_accounts = account_manager.list_accounts()
    print(f"[Info] 数据库中共有 {len(all_accounts)} 个账号。")
    print("\n--- 阶段一: 执行核心新手任务 ---")
    accounts_to_process = all_accounts
    print(f"[*] 根据指令，将从第2个账号开始处理，共 {len(accounts_to_process)} 个账号。")
    for account in accounts_to_process:
        if not account.key:
            print(f"⏭️  跳过账号 {account.username} (缺少key)")
            continue
        run_tutorial_for_account(account)
        # time.sleep(random.uniform(5, 10))
    exit(1)
    print("\n--- 阶段二: 所有账号统一处理好友申请 ---")
    for account in accounts_to_process:
        if not account.key: continue
        print(f"\n[*] 正在为账号【{account.username}】处理好友申请...")
        cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
        friend_actions = FriendActions(key=account.key, cookie=cookie_dict)
        requests_list = friend_actions.get_friend_requests()
        if requests_list:
            print(f"  - 发现 {len(requests_list)} 条好友申请。")
            for req in requests_list:
                req_id = req.get("id")
                req_name = req.get("name")
                if req_id:
                    print(f"    - 同意来自【{req_name}】的申请...")
                    friend_actions.handle_friend_request(apply_id=req_id, accept=True)
                    time.sleep(random.uniform(1.0, 1.5))
            print(f"[✔] 账号【{account.username}】的好友申请处理完毕。")
        elif requests_list == []:
            print("  - 没有新的好友申请。")
        else:
            print("  - 获取好友申请列表失败，跳过。")
    account_manager.close()
    print("\n🏁  所有账号的新手流程已执行完毕！")


if __name__ == "__main__":
    main()
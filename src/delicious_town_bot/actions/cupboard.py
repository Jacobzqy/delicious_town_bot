import re
import os
import time
import functools
from typing import List, Dict, Any, Optional, Tuple

# 假设 base_action.py 在同级目录下
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError
# 假设 constants.py 和 utils/ 在上一级目录中
from src.delicious_town_bot.constants import CupboardType
from src.delicious_town_bot.utils import game_data


def handle_lock_status(func):
    """
    装饰器：自动处理需要操作的食材的锁定状态。
    这是一个独立的函数，不再是类的方法。
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):  # 'self' 在这里是 CupboardAction 的实例
        if 'food_code' in kwargs:
            food_code = kwargs['food_code']
        elif args:
            food_code = args[0]
        else:
            raise TypeError(f"方法 {func.__name__} 缺少 'food_code' 参数。")

        # 通过 self 调用实例方法
        print(f"[*] [前置检查] 检查食材 {food_code} 的锁定状态...")
        item = self._get_food_item_by_code(food_code)

        if not item:
            print(f"[Warn] [前置检查] 未在橱柜中找到食材 {food_code}，无法检查锁定状态。将直接执行操作。")
            return func(self, *args, **kwargs)

        is_locked = item.get('is_lock') == '1'
        if not is_locked:
            print(f"[*] [前置检查] 食材 {food_code} 未锁定，直接执行操作。")
            return func(self, *args, **kwargs)

        print(
            f"[*] [自动操作] 食材 {food_code} ({game_data.get_food_by_code(food_code).get('name')}) 已锁定，执行临时解锁...")
        self.toggle_lock_status(food_code)
        try:
            return func(self, *args, **kwargs)
        finally:
            print(f"[*] [自动操作] 操作完成，恢复食材 {food_code} 的锁定状态...")
            self.toggle_lock_status(food_code)

    return wrapper


class CupboardAction(BaseAction):
    """
    封装所有与橱柜（个人仓库）相关的操作，如获取、锁定、合成、分解、购买食材等。
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        cupboard_base_url = "http://117.72.123.195/index.php?g=Res&m=Food"
        super().__init__(key=key, cookie=cookie, base_url=cupboard_base_url)

    def _get_food_item_by_code(self, food_code: str) -> Optional[Dict[str, Any]]:
        """
        【高效版】根据food_code查找并返回物品的完整动态信息（包含is_lock）。
        它首先通过静态数据确定物品等级，然后只对该等级的分类发起一次API请求。
        """
        # 第1步：查询“图鉴”获取等级，这是内存操作，速度飞快
        level = game_data.get_level_by_code(food_code)

        if level is None:
            print(f"[Warn] 在游戏数据(foods.json)中未找到 code={food_code} 的食材信息。")
            return None

        # 第2步：将等级映射到API分类
        try:
            category = CupboardType(level)
        except ValueError:
            print(f"[Warn] code={food_code} 的等级 {level} 没有对应的橱柜分类。")
            return None

        # 第3步：只对目标分类发起一次网络请求
        items_in_category = self.get_items(category)

        # 第4步：在返回的小范围结果中查找目标物品
        for item in items_in_category:
            if item.get('food_code') == food_code:
                return item  # 找到了！

        return None

    def get_items(self, category: CupboardType) -> List[Dict[str, Any]]:
        print(f"[*] 正在获取橱柜物品，分类: {category.name} ({category.value})")
        try:
            response_data = self.post("a=get_cupboard", data={"page": 1, "type": category.value})
            items = response_data.get('data', [])
            if not isinstance(items, list):
                print(f"[Warn] 获取物品失败: 服务器返回的data不是列表。")
                return []
            print(f"[+] 成功获取到 {len(items)} 件物品。")
            return items
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 获取橱柜物品时出错: {e}")
            return []

    def toggle_lock_status(self, food_code: str) -> Tuple[bool, str]:
        print(f"[*] 正在尝试切换食材代码 '{food_code}' 的锁定状态...")
        try:
            response_data = self.post("a=lock", data={"code": food_code})
            message = response_data.get('msg', '无消息')
            print(f"[+] 切换锁定状态成功: {message}")
            return True, message
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 切换锁定状态失败: {e}")
            return False, str(e)

    @handle_lock_status
    def synthesize_food(self, food_code: str, num: int) -> Tuple[bool, str]:
        food_level = game_data.get_level_by_code(food_code)
        if food_level is None:
            msg = f"未知食材代码: {food_code}"
            print(f"[Warn] {msg}")
            return False, msg
        if food_level >= 5:
            food_name = game_data.get_food_by_code(food_code).get('name', '')
            msg = f"食材 '{food_name}' 等级为 {food_level}，无法再合成。"
            print(f"[Info] {msg}")
            return False, msg

        print(f"[*] 正在尝试用 {num} 个 code={food_code} 的食材进行合成...")
        try:
            response_data = self.post("a=exchange", data={"code": food_code, "num": num})
            message = re.sub(r'<br\s*/?>', ' ', response_data.get('msg', '')).strip()
            print(f"[+] 合成成功: {message}")
            return True, message
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 合成失败: {e}")
            return False, str(e)

    @handle_lock_status
    def exchange_for_missile(self, food_code: str, num: int) -> Tuple[bool, str]:
        print(f"[*] 正在尝试用 {num} 个 code={food_code} 的五星食材兑换飞弹...")
        try:
            response_data = self.post("a=exchangeMissile", data={"code": food_code, "num": num})
            message = response_data.get('msg', '无消息')
            print(f"[+] 兑换成功: {message}")
            return True, message
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 兑换飞弹失败: {e}")
            return False, str(e)

    @handle_lock_status
    def resolve_food(self, food_code: str, num: int) -> Tuple[bool, str]:
        print(f"[*] 正在尝试分解 {num} 个 code={food_code} 的食材...")
        try:
            response_data = self.post("a=resolve", data={"code": food_code, "num": num})
            message = re.sub(r'<br\s*/?>', ' ', response_data.get('msg', '')).strip()
            print(f"[+] 分解成功: {message}")
            return True, message
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 分解失败: {e}")
            return False, str(e)

    def buy_random_food(self, level: int, num: int) -> Tuple[bool, str]:
        print(f"[*] 正在尝试用金币购买 {num} 个 {level}级 的随机食材...")
        try:
            response_data = self.post("a=buy_rand_food", data={"level": level, "num": num})
            message = re.sub(r'<br\s*/?>', '\n  ', response_data.get('msg', '')).strip()
            print(f"[+] 购买成功:\n  {message}")
            return True, message
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 购买失败: {e}")
            return False, str(e)


# ==============================================================================
#  独立测试脚本 (Standalone Test Script)
# ==============================================================================
if __name__ == '__main__':
    from dotenv import load_dotenv

    # --- 1. 加载配置 ---
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在项目根目录的 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}

    # --- 2. 实例化 Action 类 ---
    cupboard_action = CupboardAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)
    print("\n--- CupboardAction 全面测试开始 ---\n")

    # --- 3. 测试金币购买食材 ---
    print("--- 1. 测试金币购买食材 ---")
    cupboard_action.buy_random_food(level=2, num=5)

    time.sleep(1)  # 操作间稍作停顿

    # --- 4. 测试合成食材 ---
    print("\n--- 2. 测试合成食材 ---")
    level_1_foods = cupboard_action.get_items(CupboardType.LEVEL_1)
    food_to_synthesize = next((f for f in level_1_foods if int(f.get('num', 0)) >= 2), None)
    if food_to_synthesize:
        cupboard_action.synthesize_food(food_code=food_to_synthesize['food_code'], num=2)
    else:
        print("[!] 未找到足够数量的1级食材，跳过合成测试。")

    time.sleep(1)

    # --- 5. 测试分解食材 ---
    print("\n--- 3. 测试分解食材 ---")
    level_2_foods = cupboard_action.get_items(CupboardType.LEVEL_2)
    if level_2_foods:
        cupboard_action.resolve_food(food_code=level_2_foods[0]['food_code'], num=1)
    else:
        print("[!] 未找到2级食材，跳过分解测试。")

    time.sleep(1)

    # --- 6. 测试锁定与自动解锁装饰器 ---
    print("\n--- 4. 测试锁定与自动解锁 ---")
    level_1_foods_for_lock_test = cupboard_action.get_items(CupboardType.LEVEL_1)
    test_food_for_lock = next((f for f in level_1_foods_for_lock_test if int(f.get('num', 0)) >= 2), None)
    if test_food_for_lock:
        food_code = test_food_for_lock['food_code']
        food_name = test_food_for_lock['food_name']

        print(f"\n[*] [测试准备] 将对物品 '{food_name}' (code: {food_code}) 先加锁再合成，以测试装饰器。")
        cupboard_action.toggle_lock_status(food_code)  # 执行锁定

        print(f"\n[*] [开始测试] 对已锁定的物品 '{food_name}'(code: {food_code}) 进行合成...")
        cupboard_action.synthesize_food(food_code=food_code, num=2)
    else:
        print("[!] 未找到足够物品，跳过自动解锁测试。")

    print("\n--- 所有测试执行完毕 ---")
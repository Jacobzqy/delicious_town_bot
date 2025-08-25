import re
import os
import time
from dotenv import load_dotenv
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError
from typing import Tuple, Dict, Any, Union, Optional, List

# 导入 CaptchaSolver 类
from src.delicious_town_bot.utils.captcha_solver import CaptchaSolver


class FoodActions(BaseAction):
    """封装所有与菜市场（Food）相关的游戏操作。"""

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res&m=Food"
        super().__init__(key, base_url, cookie)

    def get_food_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取普通菜市场可购买的菜品列表。
        """
        print("[*] 正在获取普通菜场列表...")
        try:
            response = self.post(action_path="a=get_food")
            # 菜品列表在 response['data']['list'] 中
            food_list = response.get("data", {}).get("list")
            if not isinstance(food_list, list):
                print("[Warn] 未能获取到有效的菜品列表。")
                return None
            print(f"[Info] 成功获取到 {len(food_list)} 种普通菜品。")
            return food_list
        except (ConnectionError, Exception) as e:
            print(f"[Error] 获取普通菜场列表失败: {e}")
            return None

    def _buy_food_by_code(self, food_code: int, quantity: int) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        【内部方法】通过菜品代码购买普通菜。
        """
        print(f"[*] 正在尝试通过 Code: {food_code} 购买菜品, 数量: {quantity}...")
        payload = {"code": str(food_code), "num": str(quantity)}
        try:
            response = self.post(action_path="a=buy_food", data=payload)
            msg = response.get("msg", "")
            details = self._parse_buy_message(msg)
            print(f"[Success] {msg}")
            return True, details
        except (ConnectionError, Exception) as e:
            print(f"[Error] 购买菜品 Code:{food_code} 失败。")
            return False, str(e)

    def buy_food_by_name(self, food_name: str, quantity: int) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        【推荐使用】通过菜品名称购买普通菜。
        """
        food_list = self.get_food_list()
        if not food_list:
            return False, "无法获取菜品列表，无法购买"

        target_food = None
        for food in food_list:
            if food.get("name") == food_name:
                target_food = food
                break

        if not target_food:
            print(f"[Error] 在菜场中未找到名为 '{food_name}' 的菜品。")
            return False, f"未找到菜品: {food_name}"

        food_code = target_food.get("code")
        if not food_code:
            return False, f"找到的菜品 '{food_name}' 信息不完整 (缺少 code)"

        # 调用内部方法执行购买
        return self._buy_food_by_code(int(food_code), quantity)

    def _parse_buy_message(self, msg: str) -> Dict[str, Any]:
        details = {}
        item_match = re.search(r"\+(\d+)([\u4e00-\u9fa5a-zA-Z]+)", msg)
        if item_match:
            details['quantity_added'] = int(item_match.group(1))
            details['item_name'] = item_match.group(2)
        cost_match = re.search(r"-(\d+)金币", msg)
        if cost_match:
            details['gold_spent'] = int(cost_match.group(1))
        if not details:
            return {'raw_message': msg}
        return details

    def get_special_item_info(self) -> Optional[Dict[str, Any]]:
        print("[*] 正在获取特价菜信息...")
        try:
            response = self.post(action_path="a=get_special")
            item_info = self.dictify(response.get("data"))
            if not item_info:
                print("[Info] 当前没有特价菜。")
                return None
            print(f"[Info] 当前特价菜: {item_info.get('name')}, 剩余: {item_info.get('now_num')}")
            return item_info
        except (ConnectionError, Exception) as e:
            print(f"[Error] 获取特价菜信息失败: {e}")
            return None

    def exchange_food_with_gold(self, level: int, quantity: int, max_level: int = 5) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        使用金币兑换随机食材
        
        Args:
            level: 食材等级 (2-5)
            quantity: 兑换数量
            max_level: 最大可兑换等级（基于餐厅星级+1，最高5级）
            
        Returns:
            (是否成功, 结果信息或错误信息)
        """
        if level < 2 or level > 5:
            return False, "食材等级必须在2-5之间"
        
        if level > max_level:
            return False, f"当前餐厅最高只能兑换{max_level}级食材"
        
        print(f"[*] 正在使用金币购买{quantity}个{level}级随机食材...")
        
        try:
            payload = {
                "level": str(level),
                "num": str(quantity)
            }
            
            response = self.post(action_path="a=buy_rand_food", data=payload)
            msg = response.get("msg", "")
            
            # 解析兑换结果
            if response.get("status") and msg:
                details = self._parse_exchange_message(msg)
                print(f"[Success] {msg}")
                return True, details
            else:
                error_msg = msg if msg else "兑换失败，无错误信息"
                print(f"[Error] 兑换失败: {error_msg}")
                return False, error_msg
                
        except (BusinessLogicError, ConnectionError) as e:
            error_msg = f"兑换{level}级食材失败: {str(e)}"
            print(f"[Error] {error_msg}")
            return False, error_msg
    
    def _parse_exchange_message(self, msg: str) -> Dict[str, Any]:
        """解析兑换结果消息"""
        details = {"raw_message": msg}
        
        # 尝试解析获得的食材信息
        # 消息格式可能是: "成功兑换，获得: 猪肉 x3"
        gained_match = re.search(r"获得[：:]?\s*(.+?)\s*x?(\d+)", msg)
        if gained_match:
            details["gained_item"] = gained_match.group(1).strip()
            details["gained_quantity"] = int(gained_match.group(2))
        
        # 尝试解析花费的金币
        cost_match = re.search(r"花费[：:]?\s*(\d+)", msg)
        if cost_match:
            details["gold_spent"] = int(cost_match.group(1))
        
        return details
    
    def get_exchange_rates(self) -> Dict[int, Dict[str, Any]]:
        """
        获取不同等级食材的兑换汇率
        
        Returns:
            Dict: {level: {"gold_per_item": int, "description": str}}
        """
        # 根据游戏经验设置的预估兑换率
        rates = {
            2: {"gold_per_item": 2400, "description": "2级食材"},
            3: {"gold_per_item": 4800, "description": "3级食材"}, 
            4: {"gold_per_item": 9600, "description": "4级食材"},
            5: {"gold_per_item": 19200, "description": "5级食材"}
        }
        return rates
    
    def calculate_exchange_cost(self, level: int, quantity: int) -> int:
        """
        计算兑换指定数量指定等级食材需要的金币
        
        Args:
            level: 食材等级
            quantity: 数量
            
        Returns:
            总金币成本
        """
        rates = self.get_exchange_rates()
        if level not in rates:
            return 0
        
        return rates[level]["gold_per_item"] * quantity

    def buy_special_food(self, quantity: int, max_retries: int = 5) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        item_info = self.get_special_item_info()
        if not item_info:
            return False, "没有可购买的特价菜"
        item_id = item_info.get("id")
        item_name = item_info.get("name")
        if not item_id:
            return False, "获取到的特价菜信息不完整 (缺少 ID)"
        solver = CaptchaSolver()
        for attempt in range(1, max_retries + 1):
            print(f"\n--- 第 {attempt}/{max_retries} 次尝试购买 '{item_name}' ---")
            try:
                verify_code, code_key = solver.solve()
            except Exception as e:
                print(f"[Warn] 验证码求解过程中发生严重错误: {e}，准备重试...")
                time.sleep(2)
                continue
            print(f"[Info] 验证码识别结果: {verify_code}, 密钥: {code_key}")
            payload = {"id": str(item_id), "num": str(quantity), "verify": verify_code, "codekey": code_key}
            try:
                response = self.post(action_path="a=buy_special_food", data=payload)
                msg = response.get("msg", "")
                details = self._parse_buy_message(msg)
                print(f"[Success] 成功购买 '{item_name}'!")
                print(f"  └> {msg}")
                return True, details
            except BusinessLogicError as e:
                error_msg = str(e)
                if "验证码错误" in error_msg:
                    print(f"[Warn] 验证码错误，准备重试...")
                    time.sleep(2)
                elif "已卖完" in error_msg or "已售罄" in error_msg:
                    print(f"[Info] 特价菜 '{item_name}' 已售罄，放弃购买。")
                    return False, f"'{item_name}' 已售罄"
                else:
                    print(f"[Error] 购买时发生未知错误: {error_msg}")
                    return False, error_msg
        return False, f"连续 {max_retries} 次验证码错误或求解失败，放弃购买"


# =======================================================
#               可以直接运行此文件进行测试
# =======================================================
if __name__ == '__main__':
    # --- 从项目根目录 .env 文件加载配置 ---
    # 确保你的 .env 文件在项目根目录
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")

    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在项目根目录的 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")

    print(f"[*] 从 .env 加载的 TEST_COOKIE 值为: '{TEST_COOKIE_STR}'")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}
    print(f"[*] 已构建 Cookie 字典: {TEST_COOKIE_DICT}")

    # --- 初始化 Action 实例 ---
    food_action = FoodActions(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    # ==================== 测试 1: 购买普通菜 ====================
    print("\n\n" + "=" * 20 + " 开始测试购买普通菜 " + "=" * 20)

    # 1. 获取列表并选择一个菜购买
    available_foods = food_action.get_food_list()
    if available_foods:
        # 假设我们想买列表中的第一个菜
        food_to_buy = available_foods[0]
        food_name_to_buy = food_to_buy.get('name')
        print(f"\n[*] 计划购买普通菜: '{food_name_to_buy}'")

        success, result = food_action.buy_food_by_name(
            food_name=food_name_to_buy,
            quantity=1
        )

        print("\n--- 普通菜购买结果 ---")
        print(f"是否成功: {success}")
        if success:
            print("购买详情:", result)
        else:
            print("失败原因:", result)
    else:
        print("[Warn] 未能获取到普通菜列表，跳过购买测试。")

    # ==================== 测试 2: 购买特价菜 ====================
    print("\n\n" + "=" * 20 + " 开始测试购买特价菜 " + "=" * 20)
    # 注意: 这个测试需要你的 .env 文件中配置了打码平台信息

    success, result = food_action.buy_special_food(quantity=2)

    print("\n--- 特价菜购买结果 ---")
    print(f"是否成功: {success}")
    if success:
        print("购买详情:", result)
    else:
        print("失败原因:", result)

    print("\n\n" + "=" * 20 + " 所有测试结束 " + "=" * 20)
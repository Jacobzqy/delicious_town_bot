import re
import os
from dotenv import load_dotenv
from typing import Tuple, Dict, Any, Union, Optional

# 确保能正确导入基类和自定义异常
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class CookingActions(BaseAction):
    """封装所有与食谱学习、烹饪相关的游戏操作。"""

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        """
        初始化烹饪操作类。
        """
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key, base_url, cookie)

    def learn_recipe(self, recipe_code: Union[str, int]) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        学习一个新食谱。

        :param recipe_code: 要学习的食谱的ID (code)。
        :return: (是否成功, 包含学习详情的字典或错误消息字符串)。
        """
        print(f"[*] 正在尝试学习食谱, Code: {recipe_code}...")
        payload = {"code": str(recipe_code)}
        try:
            # 调用 m=cookbooks&a=study
            response = self.post(action_path="m=cookbooks&a=study", data=payload)
            msg = response.get("msg", "")
            details = self._parse_learn_recipe_message(msg)
            print(f"[Success] {msg}")
            return True, details
        except (BusinessLogicError, ConnectionError) as e:
            # 学习失败（例如食材不足）会由 BusinessLogicError 捕获
            print(f"[Error] 学习食谱 {recipe_code} 失败: {e}")
            return False, str(e)

    def _parse_learn_recipe_message(self, msg: str) -> Dict[str, Any]:
        """辅助方法，用于解析学习食谱成功的消息。"""
        # msg 格式: "学习家常豆腐成功!,扣除辣椒x-1豆腐x-1香葱x-1"
        details = {}

        # 解析学习的菜名
        name_match = re.search(r"学习(.*?)成功!", msg)
        if name_match:
            details['recipe_name'] = name_match.group(1)

        # 解析消耗的食材
        cost_match = re.search(r"扣除(.*)", msg)
        if cost_match:
            costs_str = cost_match.group(1).strip()
            # 使用 re.findall 查找所有 "名称x-数量" 的组合
            ingredients = re.findall(r"([\u4e00-\u9fa5a-zA-Z]+)x-(\d+)", costs_str)
            details['ingredients_consumed'] = {name: int(qty) for name, qty in ingredients}

        if not details:
            return {"raw_message": msg}
        return details

    # --- 后续待实现的功能占位 ---

    def cook_special_dish(self, recipe_id: Union[str, int], times: int) -> Tuple[bool, str]:
        """(待实现) 烹饪指定倍数的特色菜。"""
        print(f"[Info] 'cook_special_dish' 功能尚未实现。")
        return False, "功能未实现"

    def cook_regular_dish(self, recipe_id: Union[str, int], stove_id: Union[str, int]) -> Tuple[bool, str]:
        """(待实现) 在指定炉灶上烹饪普通菜。"""
        print(f"[Info] 'cook_regular_dish' 功能尚未实现。")
        return False, "功能未实现"

    def get_recipe_list(self, page: int = 1) -> Optional[list]:
        """(待实现) 获取可学习或可制作的食谱列表。"""
        print(f"[Info] 'get_recipe_list' 功能尚未实现。")
        return None


# =======================================================
#               可以直接运行此文件进行测试
# =======================================================
if __name__ == '__main__':
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY: raise ValueError("请在 .env 中设置 TEST_KEY")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR} if TEST_COOKIE_STR else None

    action = CookingActions(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "#" * 20 + "  烹饪模块测试  " + "#" * 20)

    # --- 测试 1: 学习食谱 ---
    print("\n\n" + "=" * 20 + " 1. 开始测试学习食谱 " + "=" * 20)
    # 使用你抓包得到的食谱 code
    RECIPE_CODE_TO_LEARN = 488

    success, result = action.learn_recipe(recipe_code=RECIPE_CODE_TO_LEARN)

    print("\n--- 学习结果 ---")
    print(f"是否成功: {success}")
    if success:
        import json

        print("解析出的学习详情:")
        # 使用 json.dumps 美化打印字典，确保中文正常显示
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"失败原因: {result}")

    print("\n\n" + "#" * 20 + "  所有测试结束  " + "#" * 20)
import json
import functools
from typing import Dict, Any, Optional

# 在Python 3.9+ 中，这是定位包内文件的标准方式
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Fallback for Python < 3.9
    import importlib_resources as pkg_resources

# --- 私有变量，用于缓存处理后的数据 ---

# 将从JSON加载的数据处理成以 food_code 为键的字典，用于O(1)复杂度的快速查找
_FOOD_DATA_MAP: Optional[Dict[str, Dict[str, Any]]] = None


def _load_food_data() -> Dict[str, Dict[str, Any]]:
    """
    加载并处理 foods.json 文件。
    将记录列表转换为以 'code' 为键的字典，并缓存结果。
    """
    global _FOOD_DATA_MAP
    if _FOOD_DATA_MAP is not None:
        return _FOOD_DATA_MAP

    print("[*] [GameData] 首次加载，正在读取并处理 foods.json...")

    # 使用 importlib.resources 安全地打开包内文件
    try:
        # 'delicious_town_bot.assets' 是包含文件的模块/包路径
        file_path = pkg_resources.files('delicious_town_bot.assets').joinpath('foods.json')
        with file_path.open('r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print("[Fatal] [GameData] 无法找到 foods.json 文件！")
        _FOOD_DATA_MAP = {}
        return _FOOD_DATA_MAP

    # 将列表转换为以 code 为 key 的字典
    processed_map = {
        record['code']: record
        for record in raw_data.get("RECORDS", [])
    }

    _FOOD_DATA_MAP = processed_map
    print(f"[*] [GameData] foods.json 加载并处理完成，共载入 {len(_FOOD_DATA_MAP)} 条记录。")
    return _FOOD_DATA_MAP


# --- 公共查询接口 ---

def get_food_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    根据食材代码(food_code)获取其所有信息。

    :param code: 食材的 'code'。
    :return: 包含食材所有信息的字典，如果未找到则返回 None。
    """
    data_map = _load_food_data()
    return data_map.get(code)


def get_level_by_code(code: str) -> Optional[int]:
    """
    根据食材代码(food_code)快速获取其等级。

    :param code: 食材的 'code'。
    :return: 食材的等级（整数），如果未找到则返回 None。
    """
    food_info = get_food_by_code(code)
    if food_info and 'level' in food_info:
        return int(food_info['level'])
    return None
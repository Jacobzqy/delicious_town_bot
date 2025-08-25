"""
特色菜食材礼包数据结构定义
包含特色菜食材礼包的配置信息
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class SpecialtyFoodPack:
    """特色菜食材礼包"""
    goods_id: int           # 商品ID
    name: str              # 礼包名称
    recipe_name: str       # 对应的特色菜名称
    description: str       # 礼包描述
    price: int             # 价格（金币）
    ingredients: List[str] # 包含的食材列表（每种3个）
    pack_code: str         # 礼包物品代码（用于打开礼包）
    icon: str              # 图标emoji
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "goods_id": self.goods_id,
            "name": self.name,
            "recipe_name": self.recipe_name,
            "description": self.description,
            "price": self.price,
            "ingredients": self.ingredients,
            "pack_code": self.pack_code,
            "icon": self.icon
        }


# 特色菜食材礼包配置
SPECIALTY_FOOD_PACKS = [
    SpecialtyFoodPack(
        goods_id=160,
        name="秘·薏米膳继·食材礼包(3份)",
        recipe_name="薏米膳继",
        description="包含薏米膳继所需的全部食材，每种3份",
        price=5000,
        ingredients=["薏仁", "糙米", "枸杞"],
        pack_code="10620",
        icon="🍚"
    ),
    SpecialtyFoodPack(
        goods_id=161,
        name="秘·酥卷佛手·食材礼包(3份)",
        recipe_name="酥卷佛手",
        description="包含酥卷佛手所需的全部食材，每种3份",
        price=10000,
        ingredients=["面粉", "金糕", "豆沙"],
        pack_code="10621",
        icon="🥐"
    ),
    SpecialtyFoodPack(
        goods_id=162,
        name="秘·宫保鹌鹑·食材礼包(3份)",
        recipe_name="宫保鹌鹑",
        description="包含宫保鹌鹑所需的全部食材，每种3份",
        price=20000,
        ingredients=["鹌鹑蛋", "花生", "郫县豆瓣"],
        pack_code="10622",
        icon="🍗"
    )
]


# 按食谱名称索引
FOOD_PACKS_BY_RECIPE = {pack.recipe_name: pack for pack in SPECIALTY_FOOD_PACKS}

# 按商品ID索引
FOOD_PACKS_BY_ID = {pack.goods_id: pack for pack in SPECIALTY_FOOD_PACKS}


def get_pack_by_recipe_name(recipe_name: str) -> Optional[SpecialtyFoodPack]:
    """根据特色菜名称获取对应的食材礼包"""
    return FOOD_PACKS_BY_RECIPE.get(recipe_name)


def get_pack_by_goods_id(goods_id: int) -> Optional[SpecialtyFoodPack]:
    """根据商品ID获取食材礼包"""
    return FOOD_PACKS_BY_ID.get(goods_id)


def get_all_recipe_names() -> List[str]:
    """获取所有有食材礼包的特色菜名称"""
    return list(FOOD_PACKS_BY_RECIPE.keys())


def calculate_total_ingredients_needed(recipe_name: str, multiplier: int = 1) -> Dict[str, int]:
    """
    计算特色菜所需食材总数
    
    Args:
        recipe_name: 特色菜名称
        multiplier: 倍数（默认1，即礼包中每种食材3个）
        
    Returns:
        Dict[str, int]: 食材名称和数量的映射
    """
    pack = get_pack_by_recipe_name(recipe_name)
    if not pack:
        return {}
    
    # 礼包中每种食材3个，可以根据multiplier调整
    base_count = 3
    return {ingredient: base_count * multiplier for ingredient in pack.ingredients}


def validate_purchase(goods_id: int, current_gold: int) -> Dict[str, Any]:
    """
    验证购买是否可行
    
    Args:
        goods_id: 商品ID
        current_gold: 当前金币数量
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    pack = get_pack_by_goods_id(goods_id)
    if not pack:
        return {
            "valid": False,
            "error": "食材礼包不存在",
            "error_code": "PACK_NOT_FOUND"
        }
    
    # 检查金币余额
    if pack.price > current_gold:
        return {
            "valid": False,
            "error": f"金币不足（需要{pack.price}金币，当前{current_gold}金币）",
            "error_code": "INSUFFICIENT_GOLD"
        }
    
    return {
        "valid": True,
        "pack": pack,
        "total_cost": pack.price,
        "remaining_gold": current_gold - pack.price
    }


def get_recommended_packs(current_gold: int) -> List[SpecialtyFoodPack]:
    """
    根据金币数量推荐可购买的食材礼包
    
    Args:
        current_gold: 当前金币数量
        
    Returns:
        List[SpecialtyFoodPack]: 推荐的食材礼包列表
    """
    recommended = []
    
    for pack in SPECIALTY_FOOD_PACKS:
        if pack.price <= current_gold:
            recommended.append(pack)
    
    # 按价格从低到高排序
    recommended.sort(key=lambda x: x.price)
    
    return recommended
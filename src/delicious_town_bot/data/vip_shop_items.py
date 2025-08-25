"""
VIP商店商品数据结构定义
包含所有VIP商店可购买商品的配置信息
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class VipShopItem:
    """VIP商店商品"""
    goods_id: int           # 商品ID
    name: str              # 商品名称
    description: str       # 商品描述
    voucher_cost: int      # VIP礼券消耗
    category: str          # 商品分类
    icon: str              # 图标emoji
    rarity: str           # 稀有度
    max_quantity: int     # 最大购买数量（0表示无限制）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "goods_id": self.goods_id,
            "name": self.name,
            "description": self.description,
            "voucher_cost": self.voucher_cost,
            "category": self.category,
            "icon": self.icon,
            "rarity": self.rarity,
            "max_quantity": self.max_quantity
        }


# VIP商店商品配置
VIP_SHOP_ITEMS = [
    VipShopItem(
        goods_id=130,
        name="搬家卡",
        description="可以将餐厅搬迁到其他街道的神奇卡片",
        voucher_cost=8,
        category="道具",
        icon="🏠",
        rarity="稀有",
        max_quantity=10
    ),
    VipShopItem(
        goods_id=127,
        name="高级油壶升级凭证（6000）",
        description="将油壶升级到6000容量的凭证",
        voucher_cost=5,
        category="升级道具",
        icon="🏺",
        rarity="普通",
        max_quantity=1
    ),
    VipShopItem(
        goods_id=135,
        name="小镇油壶升级凭证（7000）",
        description="将油壶升级到7000容量的凭证",
        voucher_cost=20,
        category="升级道具",
        icon="🏺",
        rarity="高级",
        max_quantity=1
    ),
    VipShopItem(
        goods_id=139,
        name="钻石油壶升级凭证（8000）",
        description="将油壶升级到8000容量的凭证",
        voucher_cost=50,
        category="升级道具",
        icon="💎",
        rarity="史诗",
        max_quantity=1
    ),
    VipShopItem(
        goods_id=140,
        name="梦想油壶升级凭证（10000）",
        description="将油壶升级到10000容量的顶级凭证",
        voucher_cost=100,
        category="升级道具",
        icon="⭐",
        rarity="传说",
        max_quantity=1
    ),
    VipShopItem(
        goods_id=152,
        name="10万金币礼包",
        description="包含10万金币的豪华礼包",
        voucher_cost=1,
        category="金币",
        icon="💰",
        rarity="普通",
        max_quantity=0  # 无限制
    ),
    VipShopItem(
        goods_id=136,
        name="神秘食谱",
        description="蕴含神秘烹饪技巧的特殊食谱",
        voucher_cost=10,
        category="食谱",
        icon="📜",
        rarity="稀有",
        max_quantity=5
    ),
    VipShopItem(
        goods_id=137,
        name="厨神玉玺",
        description="提升烹饪技能的神器道具",
        voucher_cost=10,
        category="道具",
        icon="🔱",
        rarity="稀有",
        max_quantity=3
    )
]


# 按分类组织商品
VIP_SHOP_CATEGORIES = {
    "道具": [item for item in VIP_SHOP_ITEMS if item.category == "道具"],
    "升级道具": [item for item in VIP_SHOP_ITEMS if item.category == "升级道具"],
    "金币": [item for item in VIP_SHOP_ITEMS if item.category == "金币"],
    "食谱": [item for item in VIP_SHOP_ITEMS if item.category == "食谱"]
}

# 按稀有度分类
VIP_SHOP_RARITY = {
    "普通": [item for item in VIP_SHOP_ITEMS if item.rarity == "普通"],
    "高级": [item for item in VIP_SHOP_ITEMS if item.rarity == "高级"],
    "稀有": [item for item in VIP_SHOP_ITEMS if item.rarity == "稀有"],
    "史诗": [item for item in VIP_SHOP_ITEMS if item.rarity == "史诗"],
    "传说": [item for item in VIP_SHOP_ITEMS if item.rarity == "传说"]
}

# 稀有度颜色映射
RARITY_COLORS = {
    "普通": "#6c757d",      # 灰色
    "高级": "#28a745",      # 绿色
    "稀有": "#007bff",      # 蓝色
    "史诗": "#9c27b0",      # 紫色
    "传说": "#ff6b35"       # 橙色
}

# ID到商品的映射
VIP_SHOP_ITEMS_BY_ID = {item.goods_id: item for item in VIP_SHOP_ITEMS}


def get_item_by_id(goods_id: int) -> VipShopItem:
    """根据商品ID获取商品信息"""
    return VIP_SHOP_ITEMS_BY_ID.get(goods_id)


def get_items_by_category(category: str) -> List[VipShopItem]:
    """根据分类获取商品列表"""
    return VIP_SHOP_CATEGORIES.get(category, [])


def get_items_by_rarity(rarity: str) -> List[VipShopItem]:
    """根据稀有度获取商品列表"""
    return VIP_SHOP_RARITY.get(rarity, [])


def get_all_categories() -> List[str]:
    """获取所有分类"""
    return list(VIP_SHOP_CATEGORIES.keys())


def get_all_rarities() -> List[str]:
    """获取所有稀有度"""
    return list(VIP_SHOP_RARITY.keys())


def calculate_total_cost(items: List[tuple]) -> int:
    """
    计算商品列表的总礼券消耗
    
    Args:
        items: 商品列表，格式为[(goods_id, quantity), ...]
        
    Returns:
        int: 总礼券消耗
    """
    total_cost = 0
    for goods_id, quantity in items:
        item = get_item_by_id(goods_id)
        if item:
            total_cost += item.voucher_cost * quantity
    return total_cost


def validate_purchase(goods_id: int, quantity: int, current_vouchers: int) -> Dict[str, Any]:
    """
    验证购买是否可行
    
    Args:
        goods_id: 商品ID
        quantity: 购买数量
        current_vouchers: 当前礼券数量
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    item = get_item_by_id(goods_id)
    if not item:
        return {
            "valid": False,
            "error": "商品不存在",
            "error_code": "ITEM_NOT_FOUND"
        }
    
    # 检查数量限制
    if item.max_quantity > 0 and quantity > item.max_quantity:
        return {
            "valid": False,
            "error": f"超出最大购买数量限制（最大{item.max_quantity}个）",
            "error_code": "QUANTITY_EXCEEDED"
        }
    
    # 检查礼券余额
    total_cost = item.voucher_cost * quantity
    if total_cost > current_vouchers:
        return {
            "valid": False,
            "error": f"礼券不足（需要{total_cost}张，当前{current_vouchers}张）",
            "error_code": "INSUFFICIENT_VOUCHERS"
        }
    
    return {
        "valid": True,
        "item": item,
        "total_cost": total_cost,
        "remaining_vouchers": current_vouchers - total_cost
    }


def get_recommended_items(voucher_count: int) -> List[VipShopItem]:
    """
    根据礼券数量推荐商品
    
    Args:
        voucher_count: 当前礼券数量
        
    Returns:
        List[VipShopItem]: 推荐商品列表
    """
    recommended = []
    
    # 优先推荐性价比高的商品
    for item in VIP_SHOP_ITEMS:
        if item.voucher_cost <= voucher_count:
            recommended.append(item)
    
    # 按性价比排序（礼券消耗从低到高）
    recommended.sort(key=lambda x: x.voucher_cost)
    
    return recommended
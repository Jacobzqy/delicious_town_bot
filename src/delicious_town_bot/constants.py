from enum import IntEnum, Enum


class ItemType(IntEnum):
    """仓库物品的宏观分类 (Depot)"""
    PROPS = 1       # 道具
    MATERIALS = 2   # 材料
    FACILITIES = 3  # 设施
    FRAGMENTS = 4   # 残卷（旧值，可能不正确）
    FRAGMENTS_CORRECT = 7  # 残卷（正确值，基于API响应）

class CupboardType(IntEnum):
    """橱柜物品的分类"""
    LEVEL_1 = 1  # 1级食材
    LEVEL_2 = 2  # 2级食材
    LEVEL_3 = 3  # 3级食材
    LEVEL_4 = 4  # 4级食材
    LEVEL_5 = 5  # 5级食材
    LEVEL_6 = 6  # 6级食材
    MYSTERY = 7  # 神秘食材
    UNIVERSAL = 9  # 万能食材
    SAFE_BOX = -1  # 保险柜
    RECENT = -2  # 最近

class Move(Enum):
    """猜拳时出的拳"""
    ROCK = 1
    SCISSORS = 2
    PAPER = 3

class GameResult(Enum):
    """通用游戏结果，适用于猜拳等简单游戏"""
    WIN = "赢"
    LOSS = "输"
    DRAW = "平局"

class GuessCupResult(Enum):
    """猜酒杯操作后的具体结果状态"""
    GUESSED_CORRECT_CONTINUE = "猜中，游戏继续"
    GUESSED_CORRECT_FINAL = "猜中最后一轮，游戏结束"
    GUESSED_WRONG_END = "猜错，游戏结束"

class CookbookType(IntEnum):
    """食谱的类型/状态"""
    UNLEARNED = -1  # 未学
    LEARNABLE = -2    # 已学
    PRIMARY = 1     # 初级
    SPECIAL = 2     # 特色
    FINE = 3        # 上品
    SUPER = 4       # 极品
    GOLD = 5        # 金牌

class MatchRankingType(IntEnum):
    """赛厨排行榜区域类型"""
    NOVICE = 1      # 低级区
    BEGINNER = 2    # 初级区
    INTERMEDIATE = 3 # 中级区
    ADVANCED = 4    # 高级区
    EXPERT = 5      # 顶级区
    PEAK = 6        # 巅峰区

class Street(IntEnum):
    """菜系分类 (也用于搬家卡等)"""
    CURRENT = -1   # 当前街道/全部
    HOMESTYLE = 0  # 家常 (新手街)
    XIANG = 1      # 湘菜 (湖南街)
    YUE = 2        # 粤菜 (广东街)
    CHUAN = 3      # 川菜 (四川街)
    MIN = 4        # 闽菜 (福建街)
    HUI = 5        # 徽菜 (安徽街)
    LU = 6         # 鲁菜 (山东街)
    ZHE = 7        # 浙菜 (浙江街)
    SU = 8         # 苏菜 (江苏街)
    ZONG1 = 9      # 综一 (综合一街)
    ZONG2 = 10     # 综二 (综合二街)

class MissileType(Enum):
    """神殿守卫攻击所用的飞弹类型 (值为字符串)"""
    REGULAR = "20202"
    EXPRESS = "20201"

class MonsterAttackItem(Enum):
    """攻击神殿怪兽所用的元素飞弹 (值为字符串)"""
    XIN = "20304"  # 辛
    GAN = "20305"  # 甘
    SUAN = "20306" # 酸
    KU = "20307"  # 苦
    XIAN = "20308" # 咸
    YI = "20309"   # 意

# 服务器返回的 attribute ID 到元素名称的映射
SHRINE_MONSTER_ATTRIBUTE_MAP = {
    1: "辛", 2: "甘", 3: "酸", 4: "苦", 5: "咸"
}

# 元素名称到对应飞弹枚举的映射
ELEMENT_NAME_TO_MISSILE_MAP = {
    "辛": MonsterAttackItem.XIN,
    "甘": MonsterAttackItem.GAN,
    "酸": MonsterAttackItem.SUAN,
    "苦": MonsterAttackItem.KU,
    "咸": MonsterAttackItem.XIAN,
    "意": MonsterAttackItem.YI,
}

# 元素克制循环：下一个元素克制上一个元素 (例如，甘克酸)
ELEMENT_COUNTER_CYCLE = ["酸", "甘", "苦", "辛", "咸"]

def get_counter_element_name(element_name: str) -> str:
    """
    根据输入的元素名称，返回克制它的元素名称。
    例如，输入'辛'，返回'甘'。
    """
    try:
        idx = ELEMENT_COUNTER_CYCLE.index(element_name)
        # 通过索引+1并取模来实现循环克制
        counter_idx = (idx + 1) % len(ELEMENT_COUNTER_CYCLE)
        return ELEMENT_COUNTER_CYCLE[counter_idx]
    except (ValueError, IndexError):
        # 如果输入的元素不在克制链中（如'意'），则没有克制关系
        return ""
# `ChallengeAction` 模块开发文档

**文档版本:** 1.0
**最后更新:** 2025年8月4日

## 1. 模块概述

`challenge_action.py` 模块封装了所有与游戏内高难度**“挑战”**相关的核心操作，目前主要包括**“厨塔”**和**“神殿”**两大功能。通过 `ChallengeAction` 类，开发者可以便捷地实现挑战特定层级、获取目标信息、执行攻击等复杂流程，而无需关心底层的API请求、不规则的ID映射、以及对服务器返回的复杂文本消息进行解析。

本模块的核心设计目标是**智能化**和**健壮性**。它不仅能稳定地处理各种API响应，还能基于实时的游戏数据（如怪兽元素、玩家库存）提供决策建议（如推荐克制飞弹），极大地简化了编写高级自动化策略的复杂度。

## 2. 快速入门

在开始使用前，请确保您的项目环境已按说明配置完毕。

### 2.1. 环境准备

1.  **配置文件 (`.env`)**: 确保项目根目录下存在 `.env` 文件，并已设置 `TEST_KEY` 和 `TEST_COOKIE`。
2.  **常量模块 (`constants.py`)**: 确保 `MissileType` 和 `MonsterAttackItem` 等相关枚举已按最新版本定义。

### 2.2. 实例化 `ChallengeAction`

所有操作都通过 `ChallengeAction` 的实例进行。

```python
import os
from dotenv import load_dotenv
# 假设您的项目结构与此类似
from your_project.actions.challenge_action import ChallengeAction

# 加载配置
load_dotenv()
KEY = os.getenv("TEST_KEY")
COOKIE_STR = os.getenv("TEST_COOKIE")
COOKIE_DICT = {"PHPSESSID": COOKIE_STR}

# 实例化
try:
    action = ChallengeAction(key=KEY, cookie=COOKIE_DICT)
    print("ChallengeAction 实例化成功！")
except ValueError as e:
    print(f"实例化失败: {e}")
```

### 2.3. 调用示例：智能攻击神殿怪兽

这是一个完整的“侦查-决策-攻击”流程，展示了本模块的强大之处。

```python
# 假设 action 已成功实例化

# 1. 侦查：获取怪兽实时信息
info_result = action.get_shrine_monster_info()

if info_result["success"]:
    monster_info = info_result["data"]
    
    # 2. 决策：让模块根据情报推荐最佳飞弹
    recommended_missile = action.recommend_monster_missile(monster_info)
    
    # 3. 攻击：如果推荐了飞弹，则执行攻击
    if recommended_missile:
        print(f"系统推荐使用 {recommended_missile.name} 飞弹进行攻击。")
        attack_result = action.attack_shrine_monster(recommended_missile)
        if attack_result["success"]:
            print("攻击成功！")
    else:
        print("没有可用的飞弹，取消攻击。")
```

## 3. 核心API参考

### 3.1. `ChallengeAction` 类

#### `__init__(self, key: str, cookie: Dict[str, str])`
* **功能描述**: 初始化一个挑战操作实例。
* **参数**:
    * `key` (str): 用户的会话密钥 (`key`)。
    * `cookie` (Dict[str, str]): 用户的会话Cookie，必须包含 `PHPSESSID`，格式如 `{"PHPSESSID": "..."}`。

---

### 3.2. 功能方法

#### `attack_tower(self, level: int) -> Dict[str, Any]`
* **功能描述**: 挑战厨塔的指定层级。
* **高级特性**: **(健壮解析)** 内置强大的响应解析器，能从服务器返回的HTML格式文本中精确提取所有奖励（金币、经验、声望、物品、食材），并结构化为字典返回。
* **参数**:
    * `level` (int): 要挑战的厨塔层级 (1-9)。方法内部会自动处理不规则的层级ID映射。
* **返回值**:
    * `Dict[str, Any]`: 包含挑战结果的字典，格式为 `{"success": bool, "message": str, "rewards": dict}`。

#### `get_shrine_info(self) -> Dict[str, Any]`
* **功能描述**: 获取神殿守卫的详细信息，包括守卫HP、挑战时间以及玩家拥有的普通/极速飞弹数量。
* **返回值**: `Dict[str, Any]`: 格式为 `{"success": bool, "data": dict}`，其中 `data` 键包含服务器返回的所有原始信息。

#### `attack_shrine_guard(self, missile_type: MissileType) -> Dict[str, Any]`
* **功能描述**: 使用普通或极速飞弹攻击神殿守卫。
* **参数**:
    * `missile_type` (`MissileType`): 要使用的飞弹类型，必须是 `MissileType.REGULAR` 或 `MissileType.EXPRESS`。
* **返回值**: `Dict[str, Any]`: 格式为 `{"success": bool, "message": str, "result": dict}`，其中 `result` 包含造成的伤害和消耗信息。

#### `get_shrine_monster_info(self) -> Dict[str, Any]`
* **功能描述**: 获取神殿怪兽的详细信息，包括怪兽的HP、元素属性、开始/结束时间，以及玩家拥有的所有元素飞弹库存。
* **返回值**: `Dict[str, Any]`: 格式为 `{"success": bool, "data": dict}`，其中 `data` 键包含服务器返回的所有原始信息。

#### `recommend_monster_missile(self, monster_info: Dict[str, Any]) -> Optional[MonsterAttackItem]`
* **功能描述**: **(决策辅助)** 核心辅助方法。它接收 `get_shrine_monster_info` 的结果，并根据怪兽的元素属性、元素克制链、以及玩家的飞弹库存，智能推荐出当前最应该使用的飞弹。
* **高级特性**: **(智能决策)** 自动处理元素克制逻辑。在没有克制飞弹时，会自动降级检查是否有“意”属性飞弹可用。
* **参数**:
    * `monster_info` (Dict[str, Any]): `get_shrine_monster_info()` 方法成功调用后返回的 `data` 字典。
* **返回值**:
    * `Optional[MonsterAttackItem]`: 推荐使用的 `MonsterAttackItem` 枚举成员。如果没有合适的飞弹（克制弹和意弹都没有），则返回 `None`。

#### `attack_shrine_monster(self, item: MonsterAttackItem) -> Dict[str, Any]`
* **功能描述**: 使用指定的元素飞弹攻击神殿怪兽。
* **参数**:
    * `item` (`MonsterAttackItem`): 要使用的元素飞弹，强烈建议使用 `recommend_monster_missile` 的返回值作为此参数。
* **返回值**: `Dict[str, Any]`: 格式为 `{"success": bool, "message": str}`。

## 4. 辅助模块与枚举

### 4.1. `MissileType` 枚举

用于 `attack_shrine_guard` 方法，指定攻击神殿守卫的飞弹类型。

| 枚举成员    | 值       | 描述     |
| ----------- | -------- | -------- |
| `REGULAR`   | "20202"  | 常规飞弹 |
| `EXPRESS`   | "20201"  | 极速飞弹 |

### 4.2. `MonsterAttackItem` 枚举

用于 `attack_shrine_monster` 方法，指定攻击神殿怪兽的元素飞弹。

| 枚举成员 | 值       | 描述         |
| -------- | -------- | ------------ |
| `XIN`    | "20304"  | 元素飞弹·辛  |
| `GAN`    | "20305"  | 元素飞弹·甘  |
| `SUAN`   | "20306"  | 元素飞弹·酸  |
| `KU`     | "20307"  | 元素飞弹·苦  |
| `XIAN`   | "20308"  | 元素飞弹·咸  |
| `YI`     | "20309"  | 元素飞弹·意  |
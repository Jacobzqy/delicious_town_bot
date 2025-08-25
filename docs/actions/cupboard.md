# `CupboardAction` 模块开发文档

**文档版本:** 1.0
**最后更新:** 2025年8月3日

## 1. 模块概述

`cupboard.py` 模块封装了所有与游戏内**“橱柜”**（即玩家的个人物品仓库）相关的核心操作。通过 `CupboardAction` 类，开发者可以方便地实现获取物品列表、合成、分解、锁定/解锁食材以及购买食材等功能，而无需关心底层的API请求、错误处理和状态管理细节。

本模块的核心设计目标是**易用性**和**健壮性**，特别是通过内置的装饰器自动处理了操作前置的“解锁”和操作后的“重新锁定”流程，极大地简化了调用逻辑。

## 2. 快速入门

在开始使用前，请确保您的项目环境已按说明配置完毕。

### 2.1. 环境准备

1.  **配置文件 (`.env`)**: 确保项目根目录下存在 `.env` 文件，并已设置 `TEST_KEY` 和 `TEST_COOKIE`。
2.  **静态数据 (`food.json`)**: 确保 `src/delicious_town_bot/assets/` 目录下存在 `food.json` 文件和 `__init__.py` 文件。

### 2.2. 实例化 `CupboardAction`

所有操作都通过 `CupboardAction` 的实例进行。

```python
import os
from dotenv import load_dotenv
from src.delicious_town_bot.actions.cupboard import CupboardAction
from src.delicious_town_bot.constants import CupboardType

# 加载配置
load_dotenv()
KEY = os.getenv("TEST_KEY")
COOKIE_STR = os.getenv("TEST_COOKIE")
COOKIE_DICT = {"PHPSESSID": COOKIE_STR}

# 实例化
try:
    action = CupboardAction(key=KEY, cookie=COOKIE_DICT)
    print("CupboardAction 实例化成功！")
except ValueError as e:
    print(f"实例化失败: {e}")
```

### 2.3. 调用示例：获取1级食材

```python
# 假设 action 已成功实例化
level_1_foods = action.get_items(CupboardType.LEVEL_1)

if level_1_foods:
    print(f"成功获取到 {len(level_1_foods)} 种1级食材。")
    # 打印前2个作为示例
    for food in level_1_foods[:2]:
        print(f"  - 名称: {food['food_name']}, 数量: {food['num']}, 锁定状态: {food['is_lock']}")
else:
    print("未能获取到1级食材或橱柜为空。")
```

## 3. 核心API参考

### 3.1. `CupboardAction` 类

#### `__init__(self, key: str, cookie: Dict[str, str])`
* **功能描述**: 初始化一个橱柜操作实例。
* **参数**:
    * `key` (str): 用户的会话密钥 (`key`)。
    * `cookie` (Dict[str, str]): 用户的会话Cookie，必须包含 `PHPSESSID`，格式如 `{"PHPSESSID": "..."}`。

---

### 3.2. 功能方法

#### `get_items(self, category: CupboardType) -> List[Dict[str, Any]]`
* **功能描述**: 获取橱柜中指定分类的所有物品列表。
* **参数**:
    * `category` (`CupboardType`): 要查询的物品分类。请使用从 `constants.py` 导入的 `CupboardType` 枚举成员。
* **返回值**:
    * `List[Dict[str, Any]]`: 包含物品信息字典的列表。如果该分类下无物品或请求失败，则返回空列表 `[]`。
* **示例**:
    ```python
    level_5_items = action.get_items(CupboardType.LEVEL_5)
    ```

#### `toggle_lock_status(self, food_code: str) -> Tuple[bool, str]`
* **功能描述**: 切换指定食材的锁定状态（加锁或解锁）。
* **参数**:
    * `food_code` (str): 目标食材的唯一代码（food\_code）。
* **返回值**:
    * `Tuple[bool, str]`: 一个元组 `(success, message)`。`success` 为布尔值，`message` 为服务器返回的操作结果消息。

#### `synthesize_food(self, food_code: str, num: int) -> Tuple[bool, str]`
* **功能描述**: 使用指定数量的同种低级食材合成一个或多个高一级食材（最高可到5级）。
* **高级特性**: **(自动解锁)** 无需关心食材是否锁定，方法会自动处理。
* **参数**:
    * `food_code` (str): 要用于合成的食材代码。
    * `num` (int): 计划用于合成的食材数量。服务器会自动处理奇数情况（如`num=3`只会用掉2个）。
* **返回值**:
    * `Tuple[bool, str]`: `(success, message)` 元组。

#### `resolve_food(self, food_code: str, num: int) -> Tuple[bool, str]`
* **功能描述**: 将指定数量的食材分解为低一级食材，此操作消耗体力。
* **高级特性**: **(自动解锁)** 无需关心食材是否锁定，方法会自动处理。
* **参数**:
    * `food_code` (str): 要分解的食材代码。
    * `num` (int): 要分解的数量。
* **返回值**:
    * `Tuple[bool, str]`: `(success, message)` 元组。失败消息可能是“体力不足”。

#### `exchange_for_missile(self, food_code: str, num: int) -> Tuple[bool, str]`
* **功能描述**: 使用指定数量的五级食材兑换随机飞弹，此操作消耗体力。
* **高级特性**: **(自动解锁)** 无需关心食材是否锁定，方法会自动处理。
* **参数**:
    * `food_code` (str): 要兑换的**五级**食材代码。
    * `num` (int): 要兑换的数量。
* **返回值**:
    * `Tuple[bool, str]`: `(success, message)` 元组。

#### `buy_random_food(self, level: int, num: int) -> Tuple[bool, str]`
* **功能描述**: 使用金币购买指定等级和数量的随机食材。
* **参数**:
    * `level` (int): 要购买的食材等级（例如 1, 2, 3...）。
    * `num` (int): 要购买的数量。
* **返回值**:
    * `Tuple[bool, str]`: `(success, message)` 元组。成功时消息会列出获得的所有食材。

## 4. 辅助模块与枚举

### `CupboardType` 枚举

在使用 `get_items` 方法时，必须使用此枚举来指定物品分类。

| 枚举成员        | 值   | 描述       |
| --------------- | ---- | ---------- |
| `LEVEL_1`       | 1    | 1级食材    |
| `LEVEL_2`       | 2    | 2级食材    |
| `LEVEL_3`       | 3    | 3级食材    |
| `LEVEL_4`       | 4    | 4级食材    |
| `LEVEL_5`       | 5    | 5级食材    |
| `LEVEL_6`       | 6    | 6级食材    |
| `MYSTERY`       | 7    | 神秘食材   |
| `UNIVERSAL`     | 9    | 万能食材   |
| `SAFE_BOX`      | -1   | 保险柜     |
| `RECENT`        | -2   | 最近获得   |

## 5. 高级主题：自动锁定/解锁机制

对于以下三个需要目标食材处于“未锁定”状态才能成功的方法：
* `synthesize_food`
* `resolve_food`
* `exchange_for_missile`

您**无需**在调用前手动检查或解锁食材。`CupboardAction` 类通过一个内部的 `@handle_lock_status` 装饰器，实现了全自动处理流程：
1.  **检查状态**：在执行操作前，自动通过API查询目标食材的当前锁定状态。
2.  **临时解锁**：如果食材已锁定，自动发送解锁请求。
3.  **执行操作**：执行您调用的核心功能（如合成）。
4.  **恢复锁定**：无论操作成功与否，`finally` 块都会确保将食材恢复到其原始的锁定状态。

这个机制保证了操作的便利性和账号物品的安全性。
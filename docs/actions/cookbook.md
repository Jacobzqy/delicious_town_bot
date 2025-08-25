# `CookbookAction` 模块开发文档

**文档版本:** 1.0
**最后更新:** 2025年8月3日

## 1. 模块概述

`cookbook.py` 模块封装了所有与游戏内**“食谱”**相关的核心操作。通过 `CookbookAction` 类，开发者可以方便地实现获取不同分类的食谱列表（如可学、未学、按等级分类等）以及学习新食谱的功能，而无需关心底层的API请求、复杂的服务器分页逻辑和错误处理。

本模块的核心设计目标是**易用性**和**健壮性**，特别是通过内置的循环机制自动处理了服务器在分页查询时可能返回重复数据的问题，确保能完整、正确地获取所有数据。

## 2. 快速入门

在开始使用前，请确保您的项目环境已按说明配置完毕。

### 2.1. 环境准备

1.  **配置文件 (`.env`)**: 确保项目根目录下存在 `.env` 文件，并已设置 `TEST_KEY` 和 `TEST_COOKIE`。
2.  **常量模块 (`constants.py`)**: 确保 `CookbookType` 和 `Street` 枚举已按最新版本定义。

### 2.2. 实例化 `CookbookAction`

所有操作都通过 `CookbookAction` 的实例进行。

```python
import os
from dotenv import load_dotenv
from src.delicious_town_bot.actions.cookbook import CookbookAction
from src.delicious_town_bot.constants import CookbookType

# 加载配置
load_dotenv()
KEY = os.getenv("TEST_KEY")
COOKIE_STR = os.getenv("TEST_COOKIE")
COOKIE_DICT = {"PHPSESSID": COOKIE_STR}

# 实例化
try:
    action = CookbookAction(key=KEY, cookie=COOKIE_DICT)
    print("CookbookAction 实例化成功！")
except ValueError as e:
    print(f"实例化失败: {e}")
```

### 2.3. 调用示例：获取当前可学的食谱

```python
# 假设 action 已成功实例化
learnable_recipes = action.get_all_cookbooks(CookbookType.LEARNABLE)

if learnable_recipes:
    print(f"成功获取到 {len(learnable_recipes)} 个当前可学的食谱。")
    # 打印第一个作为示例
    recipe = learnable_recipes[0]
    print(f"  - [{recipe['level_name']}/{recipe['street_name']}] {recipe['name']} (Code: {recipe['code']})")
else:
    print("当前没有可学的食谱。")
```

## 3. 核心API参考

### 3.1. `CookbookAction` 类

#### `__init__(self, key: str, cookie: Dict[str, str])`
* **功能描述**: 初始化一个食谱操作实例。
* **参数**:
    * `key` (str): 用户的会话密钥 (`key`)。
    * `cookie` (Dict[str, str]): 用户的会话Cookie，必须包含 `PHPSESSID`，格式如 `{"PHPSESSID": "..."}`。

---

### 3.2. 功能方法

#### `get_all_cookbooks(self, cookbook_type: CookbookType, street: Street = Street.CURRENT) -> List[Dict[str, Any]]`
* **功能描述**: 获取指定分类和菜系的所有食谱列表。方法内部会自动处理分页，一次性返回所有结果。
* **高级特性**: **(健壮分页)** 内置了重复数据检测机制，能正确处理因服务器API缺陷导致的分页死循环问题。
* **参数**:
    * `cookbook_type` (`CookbookType`): 要查询的食谱分类。必须使用从 `constants.py` 导入的 `CookbookType` 枚举成员。
    * `street` (`Street`): 要筛选的菜系。默认值为 `Street.CURRENT`。
* **重要提示**:
    * 根据最新测试，当 `cookbook_type` 为 `LEARNABLE` (-1) 或 `UNLEARNED` (-2) 时，`street` 参数会被服务器**忽略**，指定任何菜系都不会改变返回结果。因此，在查询这两种类型时，建议省略 `street` 参数或使用默认值。
    * 仅当按等级查询时（如 `PRIMARY`），`street` 参数才有效。
* **返回值**:
    * `List[Dict[str, Any]]`: 包含食谱信息字典的列表。如果该分类下无食谱或请求失败，则返回空列表 `[]`。
* **示例**:
    ```python
    # 获取所有初级、川菜的食谱
    primary_chuan_recipes = action.get_all_cookbooks(
        cookbook_type=CookbookType.PRIMARY,
        street=Street.CHUAN
    )
    ```

#### `study_recipe(self, recipe_code: str) -> Tuple[bool, str]`
* **功能描述**: 学习一个指定的食谱。这是一个有前置条件的操作，需要消耗对应食材。
* **参数**:
    * `recipe_code` (str): 目标食谱的唯一代码（`code`）。
* **返回值**:
    * `Tuple[bool, str]`: 一个元组 `(success, message)`。`success` 为布尔值，`message` 为服务器返回的操作结果消息。常见的失败消息是“当前食材不足!”。

## 4. 辅助模块与枚举

### 4.1. `CookbookType` 枚举

在使用 `get_all_cookbooks` 方法时，必须使用此枚举来指定食谱分类。

| 枚举成员      | 值   | 描述                                           |
| ------------- | ---- | ---------------------------------------------- |
| `LEARNABLE`   | -1   | **可学**: 可以立即学习的食谱（通常在当前街道） |
| `UNLEARNED`   | -2   | **未学**: 所有还不会的食谱（范围比`LEARNABLE`更广） |
| `PRIMARY`     | 1    | 初级食谱                                       |
| `SPECIAL`     | 2    | 特色食谱                                       |
| `FINE`        | 3    | 上品食谱                                       |
| `SUPER`       | 4    | 极品食谱                                       |
| `GOLD`        | 5    | 金牌食谱                                       |

### 4.2. `Street` 枚举

用于按菜系筛选食谱，主要在按等级查询时生效。

| 枚举成员      | 值   | 描述                                                                                                      |
| ------------- | ---- | --------------------------------------------------------------------------------------------------------- |
| `CURRENT`     | -1   | **上下文参数**：当按等级查询时，表示“所有街道”；在其他（如可学/未学）查询中，此参数被服务器忽略。 |
| `HOMESTYLE`   | 0    | 家常                                                                                                      |
| `XIANG`       | 1    | 湘菜                                                                                                      |
| `YUE`         | 2    | 粤菜                                                                                                      |
| `CHUAN`       | 3    | 川菜                                                                                                      |
| `MIN`         | 4    | 闽菜                                                                                                      |
| `HUI`         | 5    | 徽菜                                                                                                      |
| `LU`          | 6    | 鲁菜                                                                                                      |
| `ZHE`         | 7    | 浙菜                                                                                                      |
| `SU`          | 8    | 苏菜                                                                                                      |
| `ZONG1`       | 9    | 综一                                                                                                      |
| `ZONG2`       | 10   | 综二                                                                                                      |
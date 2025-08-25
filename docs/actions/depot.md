# `DepotAction` 模块开发文档

**文档版本:** 1.0
**最后更新:** 2025年8月3日

## 1. 模块概述

`depot.py` 模块封装了所有与游戏内**“仓库”**相关的核心操作。通过 `DepotAction` 类，开发者可以方便地实现获取各类物品列表、使用道具、分解残卷等功能，而无需关心底层的API请求、分页逻辑和复杂的错误处理。

本模块的核心设计目标是**易用性**和**健壮性**。它能自动处理API在分页查询时返回空列表的边界情况，确保能完整、正确地获取所有物品。此外，它还将一个功能上相关但技术上跨模块的操作（分解残卷）便捷地整合了进来。

## 2. 快速入门

在开始使用前，请确保您的项目环境已按说明配置完毕。

### 2.1. 环境准备

1.  **配置文件 (`.env`)**: 确保项目根目录下存在 `.env` 文件，并已设置 `TEST_KEY` 和 `TEST_COOKIE`。
2.  **常量模块 (`constants.py`)**: 确保 `ItemType` 和 `Street` 枚举已按最新版本定义。

### 2.2. 实例化 `DepotAction`

所有操作都通过 `DepotAction` 的实例进行。

```python
import os
from dotenv import load_dotenv
# 假设您的项目结构与此类似
from src.delicious_town_bot.actions.depot import DepotAction

# 加载配置
load_dotenv()
KEY = os.getenv("TEST_KEY")
COOKIE_STR = os.getenv("TEST_COOKIE")
COOKIE_DICT = {"PHPSESSID": COOKIE_STR}

# 实例化
try:
    action = DepotAction(key=KEY, cookie=COOKIE_DICT)
    print("DepotAction 实例化成功！")
except ValueError as e:
    print(f"实例化失败: {e}")
```

### 2.3. 调用示例：获取仓库中所有的材料

```python
from src.delicious_town_bot.constants import ItemType

# 假设 action 已成功实例化
all_materials = action.get_all_items(ItemType.MATERIALS)

if all_materials:
    print(f"成功获取到 {len(all_materials)} 个材料。")
    # 打印第一个作为示例
    item = all_materials[0]
    print(f"  - 物品: {item.get('goods_name')} (数量: {item.get('num')}, Code: {item.get('goods_code')})")
else:
    print("当前仓库中没有材料。")
```

## 3. 核心API参考

### 3.1. `DepotAction` 类

#### `__init__(self, key: str, cookie: Dict[str, str])`
* **功能描述**: 初始化一个仓库操作实例。
* **参数**:
    * `key` (str): 用户的会话密钥 (`key`)。
    * `cookie` (Dict[str, str]): 用户的会话Cookie，必须包含 `PHPSESSID`，格式如 `{"PHPSESSID": "..."}`。

---

### 3.2. 功能方法

#### `get_all_items(self, item_type: ItemType) -> List[Dict[str, Any]]`
* **功能描述**: 获取指定类型的所有物品列表。方法内部会自动处理分页，一次性返回所有结果。
* **高级特性**: **(健壮分页)** 内置了对API分页行为的正确处理。根据最新测试，当请求页码超出范围时，API会返回空列表，本方法能正确识别并终止翻页。
* **参数**:
    * `item_type` (`ItemType`): 要查询的物品类型。必须使用从 `constants.py` 导入的 `ItemType` 枚举成员。
* **返回值**:
    * `List[Dict[str, Any]]`: 包含物品信息字典的列表。如果该分类下无物品或请求失败，则返回空列表 `[]`。
* **示例**:
    ```python
    # 获取所有道具
    all_props = action.get_all_items(item_type=ItemType.PROPS)
    ```

#### `use_item(self, item_code: str, step_2_data: Optional[Any] = None) -> bool`
* **功能描述**: 使用一个指定的物品。此方法非常灵活，能自动处理单步使用和需要额外参数的两步使用场景。
* **参数**:
    * `item_code` (str): 目标物品的唯一代码 (`goods_code`)。
    * `step_2_data` (Optional[Any]): 两步操作所需的额外数据。例如：
        * **改名卡**: 此参数为字符串格式的新名字。
        * **搬家卡**: 此参数为目标街道的ID值，建议使用 `Street` 枚举（如 `Street.SU.value`）。
* **返回值**:
    * `bool`: `True` 表示操作成功，`False` 表示因业务逻辑错误（如“你当前就在xx街”）或网络问题导致的失败。详细信息会通过日志输出。

#### `resolve_fragment(self, fragment_code: str) -> bool`
* **功能描述**: 分解一个指定的残卷。
* **高级特性**: **(跨模块操作)** 这是一个便利的特殊方法。尽管分解操作的API属于 `MysteriousCookbooks` 模块，但为方便起见，已将其封装在此类中。方法内部会自动调用正确的API端点。
* **参数**:
    * `fragment_code` (str): 目标残卷的唯一代码 (`code`)。
* **返回值**:
    * `bool`: `True` 表示分解成功，`False` 表示失败。

## 4. 辅助模块与枚举

### 4.1. `ItemType` 枚举

在使用 `get_all_items` 方法时，必须使用此枚举来指定物品的宏观分类。

| 枚举成员      | 值   | 描述       |
| ------------- | ---- | ---------- |
| `PROPS`       | 1    | 道具       |
| `MATERIALS`   | 2    | 材料       |
| `FACILITIES`  | 3    | 设施       |
| `FRAGMENTS`   | 4    | 残卷       |

### 4.2. `Street` 枚举

用于 `use_item` 方法，在执行“搬家”等需要指定街道的操作时使用。

| 枚举成员      | 值   | 描述       |
| ------------- | ---- | ---------- |
| `CURRENT`     | -1   | 当前/全部  |
| `HOMESTYLE`   | 0    | 家常       |
| `XIANG`       | 1    | 湘菜       |
| `YUE`         | 2    | 粤菜       |
| `CHUAN`       | 3    | 川菜       |
| `MIN`         | 4    | 闽菜       |
| `HUI`         | 5    | 徽菜       |
| `LU`          | 6    | 鲁菜       |
| `ZHE`         | 7    | 浙菜       |
| `SU`          | 8    | 苏菜       |
| `ZONG1`       | 9    | 综一       |
| `ZONG2`       | 10   | 综二       |
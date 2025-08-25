# FriendActions - 好友操作模块

## 概述

FriendActions 模块封装了所有与好友相关的游戏操作，包括好友列表管理、食材交换、好友互动等功能。该模块支持批量操作，适合管理多个小号的好友互动需求。

## 主要功能

### 1. 好友列表管理

#### `get_friend_list(page=1)`
获取指定页的好友列表
- **参数**: `page` - 页码，从1开始
- **返回**: 好友列表或None
- **API**: `m=Friend&a=get_list&page=1`

#### `get_all_friends()`
自动翻页获取完整好友列表
- **返回**: 完整的好友列表
- **特性**: 自动去重，防止无限循环

#### `print_friend_summary(friends)`
打印好友摘要统计，包括等级分布等

### 2. 好友餐厅信息

#### `get_friend_restaurant_info(friend_res_id)`
获取好友餐厅信息
- **参数**: `friend_res_id` - 好友餐厅ID  
- **返回**: 餐厅信息字典，包含油量等
- **API**: `m=Friend&a=getFriendInfo`
- **响应示例**: `{"bottle_num": 10000}`

### 3. 好友添油功能

#### `refill_oil_for_friend(friend_res_id)`
为指定好友添油
- **参数**: `friend_res_id` - 好友餐厅ID
- **返回**: `(成功状态, 详细信息)`
- **API**: `m=Friend&a=addFriendBottle`
- **响应示例**: `"帮好友添油3740成功,金币-3740"`

#### `batch_refill_oil_for_friends(max_friends=10)`
批量为好友添油
- **参数**: `max_friends` - 最大添油好友数量
- **返回**: 详细统计结果
- **特性**: 
  - 自动获取好友油量信息
  - 统计总添油量和金币消耗
  - 计算成功率
  - 请求间隔控制

### 4. 食材交换功能

#### `query_friend_food(food_code, food_level)`
查询拥有指定食材的好友
- **参数**: `food_code`, `food_level` - 食材代码和等级
- **返回**: 包含friend_list和food_list的字典
- **API**: `m=Food&a=get_friend_food`
- **限制**: 需要VIP权限

#### `find_friends_with_food(food_name)`
根据食材名称查找拥有该食材的好友
- **参数**: `food_name` - 食材名称（如"神秘金蟾菇"）
- **返回**: 拥有该食材的好友列表
- **特性**: 自动从foods.json查找食材代码

#### `exchange_food_with_friend(friend_res_id, friend_food_code, my_food_code)`
与好友交换食材
- **参数**: 
  - `friend_res_id` - 好友餐厅ID
  - `friend_food_code` - 好友食材代码（我想要的）
  - `my_food_code` - 我的食材代码（我要给出的）
- **API**: `m=CupboardGrid&a=friend_exchange_food`

#### `batch_exchange_food(target_food_name, offer_food_name, max_exchanges=10)`
批量与好友交换食材
- **参数**:
  - `target_food_name` - 想要获得的食材名称
  - `offer_food_name` - 愿意给出的食材名称
  - `max_exchanges` - 最大交换次数
- **返回**: 交换结果统计

### 5. 好友互动功能

#### `place_roach_for_friend(friend_res_id)`
在指定好友的餐厅放一只蟑螂
- **参数**: `friend_res_id` - 好友餐厅ID
- **返回**: `(成功状态, 消息)`

#### `dine_and_dash_at_friend(friend_res_id)`
在指定好友餐厅吃白食
- **参数**: `friend_res_id` - 好友餐厅ID
- **返回**: `(成功状态, 消息)`

#### `batch_interact_with_friends(action_type, max_friends=5)`
批量与好友互动
- **参数**:
  - `action_type` - "roach"(放蟑螂) 或 "dine_and_dash"(吃白食)
  - `max_friends` - 最大互动好友数量
- **返回**: 互动结果统计

### 6. 辅助功能

#### `get_friend_by_name(friend_name)`
根据好友名称查找好友信息

#### `list_available_foods()`
列出所有可用的食材信息（从foods.json读取）

#### `_find_food_by_name(food_name)`
从foods.json中查找食材信息

## API映射

| 功能 | API路径 | 请求方式 | 参数 |
|------|---------|----------|------|
| 好友列表 | `m=Friend&a=get_list` | GET | `page` |
| 餐厅信息 | `m=Friend&a=getFriendInfo` | POST | `res_id` |
| 添油 | `m=Friend&a=addFriendBottle` | POST | `res_id` |
| 查询食材 | `m=Food&a=get_friend_food` | POST | `food_code`, `food_level` |
| 交换食材 | `m=CupboardGrid&a=friend_exchange_food` | POST | `res_id`, `friend_code`, `my_code` |
| 好友座位 | `m=Seat&a=friend_get_list` | POST | `res_id`, `page`, `type` |
| 座位操作 | `m=Seat&a=friend_go` | POST | `res_id`, `id`, `type` |

## 使用示例

```python
from src.delicious_town_bot.actions.friend import FriendActions

# 初始化
friend_actions = FriendActions(key="your_key", cookie={"PHPSESSID": "dummy"})

# 获取好友列表
friends = friend_actions.get_all_friends()

# 获取好友餐厅信息
restaurant_info = friend_actions.get_friend_restaurant_info("80")

# 为好友添油
success, result = friend_actions.refill_oil_for_friend("80")

# 批量添油
results = friend_actions.batch_refill_oil_for_friends(max_friends=5)

# 查找拥有特定食材的好友
friends_with_food = friend_actions.find_friends_with_food("神秘金蟾菇")

# 与好友交换食材
success, msg = friend_actions.exchange_food_with_friend("80", "228", "6")

# 批量互动
results = friend_actions.batch_interact_with_friends("roach", max_friends=3)
```

## 注意事项

1. **VIP限制**: 查询好友食材功能需要VIP权限
2. **请求间隔**: 批量操作包含请求间隔控制，避免服务器过载
3. **错误处理**: 完善的错误处理和类型检查
4. **数据安全**: 食材交换等操作会实际消耗游戏资源
5. **好友关系**: 放蟑螂、吃白食等操作可能影响好友关系

## 测试覆盖

- ✅ 好友列表获取和分页
- ✅ 好友餐厅信息查询  
- ✅ 单个和批量添油功能
- ✅ 食材查询和交换功能
- ✅ 好友互动功能（放蟑螂、吃白食）
- ✅ 错误处理和边界情况
- ✅ 批量操作统计和报告

## 集成建议

该模块可以轻松集成到50账号批量管理系统中：

1. **日常维护**: 批量为好友添油增进关系
2. **食材收集**: 批量交换稀有食材
3. **互动娱乐**: 适度的好友互动（放蟑螂等）
4. **数据分析**: 统计好友等级分布和活跃度

模块设计遵循现有的BaseAction架构，支持错误重试、日志记录等特性。
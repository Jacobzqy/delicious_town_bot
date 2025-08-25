# 赛厨排行榜模块 (Match Rankings)

## 概述

赛厨排行榜模块提供了获取和管理游戏中各区域排行榜数据的功能。通过该模块，用户可以查看不同等级区域的餐厅排名、等级信息，并进行数据分析。

## 核心组件

### MatchAction 类

位于 `src/delicious_town_bot/actions/match.py`

#### 主要方法

- `get_ranking_list(ranking_type, page)`: 获取指定区域和页码的排行榜数据
- `get_all_rankings(ranking_type)`: 获取指定区域的完整排行榜（100个位置）
- `get_active_restaurants(ranking_type)`: 获取指定区域的活跃餐厅列表
- `find_restaurant_by_name(name, ranking_type)`: 根据餐厅名称搜索餐厅信息
- `get_top_restaurants(ranking_type, top_n)`: 获取排行榜前N名餐厅
- `get_ranking_type_name(ranking_type)`: 获取排行榜区域类型的中文名称

#### 区域类型

使用 `MatchRankingType` 枚举定义的6个区域：

1. `NOVICE` (1) - 低级区
2. `BEGINNER` (2) - 初级区  
3. `INTERMEDIATE` (3) - 中级区
4. `ADVANCED` (4) - 高级区
5. `EXPERT` (5) - 顶级区
6. `PEAK` (6) - 巅峰区

### API 接口

**请求地址**: `http://117.72.123.195/index.php?g=Res&m=Match&a=getList`

**请求方法**: POST

**请求参数**:
- `key`: 用户会话密钥
- `type`: 区域类型 (1-6)
- `page`: 页码，每页100个位置

**响应格式**:
```json
{
  "status": true,
  "data": {
    "list": [
      {
        "id": "101",
        "res_id": "1275",
        "type": "2",
        "ranking_num": "1",
        "name": "雁后归",
        "level": "44"
      }
    ]
  }
}
```

## GUI 组件

### MatchRankingPage 类

位于 `src/delicious_town_bot/plugins/clicker/match_ranking_page.py`

#### 主要功能

1. **区域选择**: 支持6个排行榜区域的切换
2. **实时数据**: 点击刷新按钮获取最新排行榜数据
3. **数据筛选**: 支持按餐厅名称搜索和过滤
4. **数据导出**: 将排行榜数据导出为文本文件
5. **统计信息**: 显示活跃餐厅数量和平均等级

#### 界面布局

- **控制面板**: 区域选择、刷新按钮、导出功能、搜索框
- **排行榜表格**: 显示排名、餐厅名称、等级、餐厅ID
- **统计信息**: 显示数据统计和状态信息

## 使用示例

### 基本用法

```python
from src.delicious_town_bot.actions.match import MatchAction
from src.delicious_town_bot.constants import MatchRankingType

# 创建实例
match_action = MatchAction(key, {"PHPSESSID": cookie})

# 获取初级区活跃餐厅
restaurants = match_action.get_active_restaurants(MatchRankingType.BEGINNER)

# 获取前10名餐厅
top_10 = match_action.get_top_restaurants(MatchRankingType.BEGINNER, 10)

# 搜索特定餐厅
restaurant = match_action.find_restaurant_by_name("雁后归", MatchRankingType.BEGINNER)
```

### GUI 使用

1. 启动主程序: `uv run python src/delicious_town_bot/plugins/clicker/ui.py`
2. 在左侧导航栏选择"赛厨排行榜"
3. 选择要查看的区域（默认为初级区）
4. 点击"刷新数据"按钮获取最新排行榜
5. 使用搜索框过滤特定餐厅
6. 点击"导出数据"保存排行榜到文件

## 数据结构

### 活跃餐厅数据格式

```python
{
    "ranking_num": "1",      # 排名
    "name": "雁后归",         # 餐厅名称
    "level": 44,             # 等级 (整数)
    "res_id": "1275"         # 餐厅ID
}
```

### 完整排行榜数据格式

```python
{
    "id": "101",             # 内部ID
    "res_id": "1275",        # 餐厅ID
    "type": "2",             # 区域类型
    "ranking_num": "1",      # 排名
    "name": "雁后归",         # 餐厅名称 (可能为null)
    "level": "44"            # 等级 (可能为null)
}
```

## 特性

1. **多区域支持**: 覆盖从低级区到巅峰区的所有排行榜
2. **实时数据**: 直接从游戏服务器获取最新排行榜信息
3. **数据过滤**: 自动过滤出活跃餐厅（有名称和等级的餐厅）
4. **搜索功能**: 支持按餐厅名称快速查找
5. **统计分析**: 提供活跃餐厅数量和平均等级统计
6. **数据导出**: 支持将排行榜数据导出为文本文件
7. **用户友好**: 提供直观的GUI界面和详细的日志信息

## 测试

运行测试脚本验证功能：

```bash
# 基础功能测试
uv run python test_match_ranking.py

# 功能演示
uv run python demo_match_ranking.py
```

## 注意事项

1. 需要有效的账号key和cookie才能访问排行榜数据
2. 每个区域有100个排位，但并非所有排位都有活跃餐厅
3. 排行榜数据实时更新，不同时间获取的数据可能不同
4. 网络异常或服务器维护可能导致数据获取失败
5. 导出的文件保存在程序运行目录下
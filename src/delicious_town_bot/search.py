import os
import time
import pandas as pd
from collections import Counter
from typing import Set, Dict, Any

from dotenv import load_dotenv

# --- 真实模块导入 ---
# 使用您项目中的真实 Action 类和常量枚举
from delicious_town_bot.actions.cookbook import CookbookActions
from delicious_town_bot.constants import CookbookType, Street


def run_recipe_check():
    """
    主函数，执行完整的食谱检查与统计流程。
    """
    # --- 1. 初始化与环境准备 ---
    print("=" * 50)
    print("      未学食谱检查与食材统计脚本      ")
    print("=" * 50)

    # 加载 .env 文件中的环境变量
    load_dotenv()
    key = os.getenv("TEST_KEY")
    cookie_str = os.getenv("TEST_COOKIE")
    excel_path = "assets/cookbook.xlsx"  # 定义Excel文件路径

    # 校验环境变量和文件
    if not key or not cookie_str:
        print("[错误] 请在项目根目录的 .env 文件中设置 TEST_KEY 和 TEST_COOKIE。")
        return
    if not os.path.exists(excel_path):
        print(f"[错误] 无法找到食谱数据文件 '{excel_path}'。请确保文件存在于项目根目录。")
        return

    cookie = {"PHPSESSID": cookie_str}

    try:
        # 实例化 Action
        action_bot = CookbookActions(key=key, cookie=cookie)
        print("CookbookAction 已成功实例化。")

        # 从Excel加载全量食谱数据
        print(f"\n[步骤 1/4] 正在从 '{excel_path}' 加载全量食谱数据...")
        df_all_recipes = pd.read_excel(excel_path)
        all_recipes_set = set(df_all_recipes['食谱'].unique())
        print(f"  > 成功加载 {len(all_recipes_set)} 种不同的食谱。")

    except Exception as e:
        print(f"[致命错误] 初始化失败: {e}")
        return

    # --- 2. 构建已学食谱列表 ---
    print("\n[步骤 2/4] 开始通过API查询所有已学会的食谱...")
    print("  > 这可能需要一些时间，请耐心等待...")

    learned_recipes_set: Set[str] = set()
    # 定义需要遍历的街道和等级
    # 通过反射从枚举类中获取所有成员，排除特殊成员
    streets_to_check = [s.name for s in Street if s.value != -1]  # 排除 CURRENT
    levels_to_check = [t.name for t in CookbookType if t.value > 0]  # 排除 UNLEARNED 和 LEARNABLE

    total_requests = len(streets_to_check) * len(levels_to_check)
    request_count = 0

    try:
        for street_name in streets_to_check:
            for level_name in levels_to_check:
                request_count += 1
                street_enum = getattr(Street, street_name)
                level_enum = getattr(CookbookType, level_name)

                print(f"  ({request_count}/{total_requests}) 正在查询 [{street_name}] 的 [{level_name}] 食谱...")

                # 调用API获取数据
                learned_in_category = action_bot.get_all_cookbooks(
                    cookbook_type=level_enum,
                    street=street_enum
                )

                for recipe in learned_in_category:
                    learned_recipes_set.add(recipe['name'])

                # 友好地等待一下，避免请求过于频繁对服务器造成压力
                time.sleep(0.5)

        print(f"  > 查询完成！共发现 {len(learned_recipes_set)} 种已学会的食谱。")

    except Exception as e:
        print(f"[致命错误] 在查询API时发生错误: {e}")
        return

    # --- 3. 分析与计算 ---
    print("\n[步骤 3/4] 正在计算未学食谱并统计所需食材...")

    # 使用集合差集计算出未学食谱
    unlearned_recipes_set = all_recipes_set - learned_recipes_set

    if not unlearned_recipes_set:
        print("\n🎉 恭喜！所有食谱均已学完！脚本执行结束。")
        return

    print(f"  > 计算完成！发现 {len(unlearned_recipes_set)} 种未学习的食谱。")

    # 从总数据中筛选出所有未学食谱的条目
    df_unlearned = df_all_recipes[df_all_recipes['食谱'].isin(unlearned_recipes_set)].copy()

    # 统计未学完的街道
    streets_to_finish = set(df_unlearned['街道'].unique())

    # 统计所需食材
    # 因为Excel中每行是一个食材，直接用Counter统计“所需食材”列即可
    required_ingredients = Counter(df_unlearned['所需食材'])

    # --- 4. 结果总结 ---
    print("\n" + "=" * 50)
    print("      检查结果总结      ")
    print("=" * 50)

    print("\n【未学完的街道】")
    if not streets_to_finish:
        print("  (无)")
    else:
        for street in sorted(list(streets_to_finish)):
            print(f"  - {street}")

    print("\n【未学食谱列表】")
    for recipe_name in sorted(list(unlearned_recipes_set)):
        print(f"  - {recipe_name}")

    print("\n【补全所有食谱所需食材统计】")
    if not required_ingredients:
        print("  (无需任何食材)")
    else:
        # 为了美观，找到最长的物品名称，用于对齐
        max_len = max(len(str(item)) for item in required_ingredients.keys()) if required_ingredients else 0
        for item, count in sorted(required_ingredients.items()):
            print(f"  - {str(item).ljust(max_len)} : {count} 个")

    print("\n脚本执行完毕。")


if __name__ == '__main__':
    run_recipe_check()

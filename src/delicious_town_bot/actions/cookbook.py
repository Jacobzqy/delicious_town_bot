# actions/cookbook_actions.py

import os
import time
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

# 假设 base_action.py 等在上一级目录的相应位置
from delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError
from delicious_town_bot.constants import CookbookType, Street


class CookbookActions(BaseAction):
    """
    封装所有与食谱（Cookbook）相关的操作，如获取和学习食谱。
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res&m=Cookbooks"
        super().__init__(key=key, cookie=cookie, base_url=base_url)

    def get_all_cookbooks(
            self,
            cookbook_type: CookbookType = CookbookType.UNLEARNED,
            street: Street = Street.CURRENT
    ) -> List[Dict[str, Any]]:
        print(f"[*] 正在获取食谱: 类型='{cookbook_type.name}', 菜系='{street.name}'")
        all_recipes = []
        seen_recipe_codes = set()
        page = 1
        while True:
            try:
                payload = {
                    'page': page,
                    'type': cookbook_type.value,
                    'street': street.value,
                }

                response = self.post(action_path="a=my_cookbooks_list", data=payload)
                recipes_on_page = response.get('data')

                if not recipes_on_page:
                    if page == 1:
                        print(f"[*] 在此条件下未找到任何食谱。")
                    else:
                        print(f"[+] 已到达数据末尾（服务器返回空列表），共加载了 {len(all_recipes)} 个食谱。")
                    break

                current_page_codes = {recipe.get('code') for recipe in recipes_on_page}
                if current_page_codes.issubset(seen_recipe_codes):
                    print(f"[+] 检测到重复数据，判断为已到达最后一页。共加载了 {len(all_recipes)} 个食谱。")
                    break

                print(f"[*] 成功加载第 {page} 页，获得 {len(recipes_on_page)} 个食谱...")
                all_recipes.extend(recipes_on_page)
                seen_recipe_codes.update(current_page_codes)
                page += 1
                time.sleep(0.5)

            except (BusinessLogicError, ConnectionError) as e:
                print(f"[Error] 获取食谱列表时发生错误: {e}")
                break
        return all_recipes

    def study_recipe(self, recipe_code: str) -> Tuple[bool, str]:
        print(f"[*] 正在尝试学习食谱，代码: '{recipe_code}'...")
        try:
            response_data = self.post("a=study", data={"code": recipe_code})
            message = response_data.get('msg', '无消息')
            if not message:
                message = "学习成功！"
            print(f"[+] '学习食谱' 操作完成: {message}")
            return True, message
        except BusinessLogicError as e:
            print(f"[Error] 学习食谱失败 (业务逻辑): {e}")
            return False, str(e)
        except ConnectionError as e:
            print(f"[Error] 学习食谱失败 (网络): {e}")
            return False, str(e)


# ==============================================================================
#  独立测试脚本 (Standalone Test Script)
# ==============================================================================
if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在项目根目录的 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}

    cookbook_action = CookbookActions(key=TEST_KEY, cookie=TEST_COOKIE_DICT)
    print("\n--- CookbookActions 全面测试开始 ---\n")

    # --- 1. 常规功能测试 ---
    print("--- 1. 测试学习食谱 (常规流程) ---")
    unlearned_recipes_to_study = cookbook_action.get_all_cookbooks(
        cookbook_type=CookbookType.LEARNABLE,
        street=Street.CURRENT
    )
    if unlearned_recipes_to_study:
        recipe_to_study = unlearned_recipes_to_study[0]
        print(f"[*] 找到可学食谱: '{recipe_to_study.get('name')}'，尝试学习...")
        cookbook_action.study_recipe(recipe_to_study.get('code'))
    else:
        print("[!] 未找到可供学习的食谱，跳过学习测试。")

    time.sleep(1)

    # --- 2. 探索性测试 ---
    print("\n--- 2. 开始探索性API测试 ---")

    # --- 实验 2.1 ---
    print("\n--- [实验 2.1] 测试 'street=-1' 在 '初级' 分类中的作用 ---")
    primary_recipes = cookbook_action.get_all_cookbooks(
        cookbook_type=CookbookType.PRIMARY,
        street=Street.CURRENT  # street=-1
    )
    if primary_recipes:
        street_names = [recipe.get('street_name') for recipe in primary_recipes]
        street_counts = Counter(street_names)
        print(f"[+] 获取到 {len(primary_recipes)} 个初级食谱，街道分布如下:")
        for name, count in street_counts.items():
            print(f"  - {name}: {count} 个")

        if len(street_counts) == 1:
            print("[结论] street=-1 表现为【当前街道】过滤器。")
        else:
            print("[结论] street=-1 表现为【所有街道】过滤器，这是一个非常有用的发现！")
    else:
        print("[结论] 未获取到任何初级食谱，无法判断。")

    time.sleep(1)

    # --- 实验 2.2 ---
    print("\n--- [实验 2.2] 测试 '未学' + 特定菜系 (以湘菜为例) ---")
    unlearned_xiang = cookbook_action.get_all_cookbooks(
        cookbook_type=CookbookType.UNLEARNED,
        street=Street.XIANG
    )
    if unlearned_xiang:
        print(f"[+] 成功获取到 {len(unlearned_xiang)} 个【未学】的【湘菜】食谱。")
        print("[结论] 重大发现！API允许按菜系筛选未学食谱，可以实现精准学习！")
    else:
        print("[结论] 未获取到数据。这可能意味着API不允许此组合，或者你确实没有未学的湘菜食谱。")

    time.sleep(1)

    # --- 实验 2.3 ---
    print("\n--- [实验 2.3] 测试 '可学' + 特定菜系 (以湘菜为例) ---")
    learned_xiang = cookbook_action.get_all_cookbooks(
        cookbook_type=CookbookType.LEARNABLE,
        street=Street.XIANG
    )
    if learned_xiang:
        print(f"[+] 成功获取到 {len(learned_xiang)} 个【可学】的【湘菜】食谱。")
        print("[结论] API允许按菜系筛选可学食谱，可以方便地分类查看！")
    else:
        print("[结论] 未获取到数据。这可能意味着API不允许此组合，或者你确实没有可学的湘菜食谱。")

    print("\n--- 所有测试执行完毕 ---")
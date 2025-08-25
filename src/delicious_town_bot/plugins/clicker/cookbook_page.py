import json
import os
import pandas as pd
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QTextEdit, QMessageBox,
    QApplication, QHeaderView, QSplitter, QFrame, QProgressBar, QButtonGroup,
    QSpinBox, QGroupBox, QDialog, QAbstractItemView
)

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.cookbook import CookbookActions
from src.delicious_town_bot.actions.friend import FriendActions
from src.delicious_town_bot.actions.cupboard import CupboardAction
from src.delicious_town_bot.actions.food import FoodActions
from src.delicious_town_bot.actions.restaurant import RestaurantActions
from src.delicious_town_bot.constants import CookbookType, Street, CupboardType
from src.delicious_town_bot.utils import game_data

class RecipeIngredientCalculator:
    """食材需求计算器"""
    
    def __init__(self):
        self.foods_data = self._load_foods_data()
        self.cookbook_data = self._load_cookbook_data()
        
    def _load_foods_data(self) -> Dict[str, Any]:
        """加载食材数据"""
        try:
            # 修正路径：从 plugins/clicker 向上两级到达 src/delicious_town_bot，然后到 assets
            foods_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "assets", "foods.json"
            )
            with open(foods_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Error] 加载食材数据失败: {e}")
            print(f"[Debug] 尝试的路径: {foods_file_path if 'foods_file_path' in locals() else '未定义'}")
            return {"RECORDS": []}
    
    def _load_cookbook_data(self) -> pd.DataFrame:
        """加载食谱配方数据"""
        try:
            cookbook_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "assets", "cookbook.xlsx"
            )
            return pd.read_excel(cookbook_file_path)
        except Exception as e:
            print(f"[Error] 加载食谱数据失败: {e}")
            return pd.DataFrame()
    
    def get_recipe_ingredients(self, recipe_name: str, level: int, street_name: str) -> Dict[str, int]:
        """
        从Excel数据中获取真实的食谱食材需求
        :param recipe_name: 食谱名称
        :param level: 食谱等级
        :param street_name: 街道名称（来自API的街道名称）
        :return: 食材需求字典
        """
        if self.cookbook_data.empty:
            return self._simulate_recipe_ingredients({'name': recipe_name, 'level': level})
        
        # 先尝试直接匹配食谱名和等级，不限制街道
        recipe_data = self.cookbook_data[
            (self.cookbook_data['食谱'] == recipe_name) & 
            (self.cookbook_data['食谱等级'] == level)
        ]
        
        if recipe_data.empty:
            print(f"[Warning] 未找到食谱 '{recipe_name}' 等级 {level} 的配方数据，使用模拟数据")
            return self._simulate_recipe_ingredients({'name': recipe_name, 'level': level})
        
        # 如果找到数据，检查街道是否匹配
        excel_street = recipe_data.iloc[0]['街道']  # 获取Excel中的街道
        converted_street = self._convert_street_name(street_name)
        
        # 如果街道不匹配，记录但继续处理
        if excel_street != converted_street:
            print(f"[Info] 食谱 '{recipe_name}' 街道不匹配: API='{street_name}'({converted_street}) vs Excel='{excel_street}'，仍然使用Excel数据")
        
        # 统计食材需求
        ingredients = defaultdict(int)
        for _, row in recipe_data.iterrows():
            ingredient = row['所需食材']
            ingredients[ingredient] += 1  # 每行代表需要1个该食材
        
        return dict(ingredients)
    
    def _convert_street_name(self, street_name: str) -> str:
        """转换街道名称为Excel中的格式"""
        street_mapping = {
            # API返回的街道名 -> Excel中的街道名
            '湘菜': '湖南街',
            '川菜': '四川街', 
            '粤菜': '广东街',
            '闽菜': '福建街',
            '徽菜': '安徽街',
            '鲁菜': '山东街',
            '浙菜': '浙江街',
            '苏菜': '江苏街',
            '家常': '新手街',      # 修正：家常 -> 新手街
            '家常菜': '新手街',     # 兼容可能的变体
            '综一': '综合一街',
            '综二': '综合二街'
        }
        return street_mapping.get(street_name, street_name)
    
    def calculate_requirements(self, selected_recipes: List[Dict[str, Any]], 
                             current_street: str, exclude_expensive: bool = True) -> Dict[str, int]:
        """
        计算选中食谱的食材总需求（从当前等级学到最高可学等级）
        :param selected_recipes: 选中的食谱列表
        :param current_street: 当前街道
        :param exclude_expensive: 是否排除昂贵食材（鱼翅、鲍鱼、神秘）
        :return: 食材需求字典 {食材名称: 需要数量}
        """
        total_requirements = defaultdict(int)
        # 用户明确选择了食谱，就应该显示完整需求（包括神秘食材）
        # exclude_expensive主要用于限制学习等级，而不是过滤已选食谱的需求
        excluded_prefixes = []  # 不排除任何食材，显示真实完整需求
        
        for recipe in selected_recipes:
            # 检查是否可以学习（当前街道或新手街）
            recipe_street = recipe.get('street_name', '')
            if recipe_street == current_street or recipe_street == '新手街' or current_street == '全部':
                recipe_name = recipe.get('name', '')
                target_level = int(recipe.get('level', 1))  # 学习完成后将到达的等级
                
                # 对于"可学"状态的食谱，直接计算这一次学习的需求
                # 因为如果真的已达最高等级，就不会出现在"可学"列表中了
                ingredients = self.get_recipe_ingredients(recipe_name, target_level, recipe_street)
                
                for ingredient, count in ingredients.items():
                    # 根据设置排除神秘食材
                    if not exclude_expensive or not any(ingredient.startswith(prefix) for prefix in excluded_prefixes):
                        total_requirements[ingredient] += count
        
        return dict(total_requirements)
    
    def _get_max_learnable_level(self, recipe_name: str, street_name: str, exclude_expensive: bool = True) -> int:
        """
        获取食谱的最高可学等级
        :param recipe_name: 食谱名称
        :param street_name: 街道名称
        :param exclude_expensive: 是否排除昂贵食材
        :return: 最高可学等级（1-5）
        """
        if self.cookbook_data.empty:
            return 5  # 默认最高等级
        
        # 如果不排除昂贵食材，直接返回5级
        if not exclude_expensive:
            return 5
        
        # 检查每个等级是否包含神秘食材（鱼翅和鲍鱼允许，但神秘食材不允许）
        max_safe_level = 1
        for level in range(1, 6):  # 从1级往上检查
            try:
                ingredients = self.get_recipe_ingredients(recipe_name, level, street_name)
                
                if not ingredients:
                    continue
                
                # 只排除神秘食材，允许鱼翅和鲍鱼（因为用户明确选择了这些食谱）
                has_mystery = any(
                    ingredient.startswith('神秘')
                    for ingredient in ingredients.keys()
                )
                
                if not has_mystery:
                    max_safe_level = level
                else:
                    # 遇到神秘食材，停止提升等级
                    break
                    
            except Exception:
                continue
        
        return max_safe_level
    
    def classify_ingredient(self, ingredient: str) -> str:
        """
        分类食材类型
        
        正确的分类规则：
        - 鱼翅食材: 包含"鱼翅"
        - 鲍鱼食材: 包含"鲍鱼" 
        - 神秘食材: 仅限以"神秘"开头的7级食材
        - 基础食材: 其他所有食材（包括1-5级普通和高级食材）
        
        注意：4级、5级食材虽然是高级食材，但仍可通过好友兑换获得
        """
        if '鱼翅' in ingredient:
            return 'yu_chi'
        elif '鲍鱼' in ingredient:
            return 'bao_yu'
        elif ingredient.startswith('神秘'):
            return 'mystery'
        else:
            # 所有其他食材都归类为基础食材
            # 包括：1-3级普通食材、4-5级高级食材（如山黑猪肉、韩城花椒等）
            return 'basic'
    
    def _simulate_recipe_ingredients(self, recipe: Dict[str, Any]) -> Dict[str, int]:
        """
        模拟食谱食材需求（当无法从Excel获取时的备用方案）
        """
        # 根据食谱等级模拟食材需求
        level = int(recipe.get('level', 1))
        base_ingredients = {
            '醋': 1,
            '白菜': 1, 
            '猪肉': 1,
            '生菜': 1
        }
        
        # 高等级食谱需要更多食材
        multiplier = level
        return {ingredient: count * multiplier for ingredient, count in base_ingredients.items()}

class SmartExchangeStrategy:
    """智能兑换策略（集成橱柜+菜场购买）"""
    
    def __init__(self, friend_actions: FriendActions, cupboard_action: CupboardAction = None, food_action: FoodActions = None):
        self.friend_actions = friend_actions
        self.cupboard_action = cupboard_action
        self.food_action = food_action
        self.preferred_friends = ["黑心餐馆儿", "秋阳驿站"]
    
    def find_target_friend(self) -> Optional[Dict[str, Any]]:
        """查找目标兑换好友"""
        all_friends = self.friend_actions.get_all_friends()
        if not all_friends:
            return None
            
        for friend_name in self.preferred_friends:
            for friend in all_friends:
                if friend.get('name') == friend_name:
                    return friend
        
        return None
    
    def get_exchange_plan(self, required_ingredients: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        生成兑换计划（2个相同食材换1个同级食材）
        :param required_ingredients: 需要的食材
        :return: 兑换计划列表
        """
        print("[*] 生成兑换计划...")
        
        # 获取真实库存
        current_inventory = self.get_current_inventory()
        if not current_inventory:
            print("  ❌ 无法获取库存，取消兑换计划")
            return []
        
        # 获取可用于兑换的食材（数量>=2且有剩余）
        available_for_exchange = self.get_available_for_exchange(current_inventory, required_ingredients)
        
        print(f"  📊 需求: {required_ingredients}")
        print(f"  📦 库存: {len(current_inventory)}种食材")
        print(f"  🔄 可兑换: {len(available_for_exchange)}种食材")
        
        exchange_plan = []
        
        for need_ingredient, need_count in required_ingredients.items():
            current_count = current_inventory.get(need_ingredient, 0)
            deficit = need_count - current_count
            
            if deficit > 0:
                need_level = self._get_foods_json_level(need_ingredient)
                print(f"  🎯 缺少 {need_ingredient}(L{need_level}): {deficit}个")
                
                # 寻找同级的可兑换食材
                for my_ingredient, available_pairs in available_for_exchange.items():
                    if my_ingredient == need_ingredient:
                        continue
                        
                    my_level = self._get_foods_json_level(my_ingredient)
                    
                    # 严格同级兑换：2个相同食材换1个同级食材
                    if my_level == need_level:
                        max_can_exchange = available_pairs // 2  # 每2个换1个
                        actual_exchange = min(max_can_exchange, deficit)
                        
                        if actual_exchange > 0:
                            exchange_plan.append({
                                'give': my_ingredient,
                                'give_count': actual_exchange * 2,  # 给出的数量（2个一组）
                                'want': need_ingredient,
                                'want_count': actual_exchange,     # 想要的数量（1个）
                                'give_level': my_level,
                                'want_level': need_level,
                                'exchange_ratio': '2:1'
                            })
                            
                            deficit -= actual_exchange
                            available_for_exchange[my_ingredient] -= actual_exchange * 2
                            
                            print(f"    ✅ 计划: {actual_exchange*2}个{my_ingredient}(L{my_level}) → {actual_exchange}个{need_ingredient}(L{need_level})")
                            
                            if deficit <= 0:
                                break
                
                if deficit > 0:
                    print(f"    ⚠️  仍缺少 {deficit}个{need_ingredient}，需要购买")
                    
                    # 即使没有可兑换的食材，也要生成购买+兑换计划
                    # 计划：先购买同级食材，再兑换
                    exchange_plan.append({
                        'give': f'待购买的{need_level}级食材',  # 占位符，执行时会先购买
                        'give_count': deficit * 2,  # 需要购买的数量（2:1比例）
                        'want': need_ingredient,
                        'want_count': deficit,
                        'give_level': need_level,
                        'want_level': need_level,
                        'exchange_ratio': '2:1',
                        'requires_purchase': True,  # 标记需要先购买
                        'purchase_level': need_level
                    })
                    
                    print(f"    📋 生成购买计划: 购买{deficit*2}个{need_level}级食材 → 兑换{deficit}个{need_ingredient}")
        
        print(f"[+] 生成兑换计划: {len(exchange_plan)}项")
        return exchange_plan
    
    def _get_foods_json_level(self, ingredient_name: str) -> int:
        """获取foods.json中的原始等级（1-based）"""
        food_code = self._get_food_code(ingredient_name)
        level = game_data.get_level_by_code(food_code)
        return level if level is not None else 1
    
    def execute_exchange_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行兑换计划（严格2:1兑换，同级验证）"""
        target_friend = self.find_target_friend()
        if not target_friend:
            return {"success": False, "message": "未找到目标兑换好友"}
        
        print(f"[*] 开始执行兑换计划，目标好友: {target_friend.get('res_name', '未知')}")
        
        results = {
            "total_attempts": 0,
            "successful_exchanges": 0,
            "failed_exchanges": 0,
            "gold_purchases": 0,
            "exchange_details": [],
            "purchase_details": []
        }
        
        for exchange in plan:
            give_ingredient = exchange['give']
            want_ingredient = exchange['want']
            give_count = exchange['give_count']  # 给出数量（2个）
            want_count = exchange['want_count']  # 想要数量（1个）
            exchange_ratio = exchange.get('exchange_ratio', '2:1')
            requires_purchase = exchange.get('requires_purchase', False)
            
            print(f"[*] 执行兑换: {give_count}个{give_ingredient} → {want_count}个{want_ingredient} ({exchange_ratio})")
            
            # 如果需要先购买食材
            if requires_purchase:
                purchase_level = exchange.get('purchase_level', 1)
                needed_count = give_count  # 需要购买的数量
                
                print(f"  💰 需要先购买 {needed_count}个{purchase_level}级食材")
                
                # 执行购买
                purchase_success = self._handle_insufficient_ingredient(want_ingredient, needed_count)
                
                if purchase_success:
                    results["gold_purchases"] += 1
                    results["purchase_details"].append({
                        "ingredient": want_ingredient,
                        "level": purchase_level,
                        "count": needed_count,
                        "success": True
                    })
                    print(f"  ✅ 购买成功，继续执行兑换")
                else:
                    results["failed_exchanges"] += 1
                    results["purchase_details"].append({
                        "ingredient": want_ingredient,
                        "level": purchase_level,
                        "count": needed_count,
                        "success": False
                    })
                    print(f"  ❌ 购买失败，跳过此兑换")
                    continue
            
            # 验证兑换前的库存和等级（对于非购买计划）
            if not requires_purchase and not self._validate_exchange(exchange):
                print(f"  ❌ 兑换验证失败，跳过此项")
                results["failed_exchanges"] += 1
                continue
            
            # 执行多次1:1兑换来实现2:1效果
            exchange_successful = True
            total_exchanges_needed = want_count
            successful_individual_exchanges = 0
            
            # 重新设计的2换1兑换逻辑
            # 问题分析：游戏的2换1应该是一次性交易，不是分两步
            # 当前的friend接口可能不支持真正的2:1比例兑换
            # 暂时改为1:1兑换，但记录为2:1计划
            
            print(f"  ⚠️  当前实现限制：使用1:1兑换代替2:1兑换")
            print(f"  📝 计划执行: {give_count}个{give_ingredient} → {want_count}个{want_ingredient} (比例{exchange_ratio})")
            
            for i in range(want_count):  # 执行want_count次1:1兑换
                print(f"  第{i+1}/{want_count}次兑换: 1个{give_ingredient} → 1个{want_ingredient}")
                
                success, message = self.friend_actions.exchange_food_with_friend(
                    target_friend.get('id'),
                    self._get_food_code(want_ingredient),
                    self._get_food_code(give_ingredient)
                )
                
                if success:
                    print(f"    ✅ 兑换成功: {message}")
                    successful_individual_exchanges += 1
                else:
                    print(f"    ❌ 兑换失败: {message}")
                    
                    # 检查是否因为食材不足而失败
                    if "你选择的食材数量不足" in message:
                        print(f"    [*] 检测到食材不足: {give_ingredient}，尝试购买...")
                        if self._handle_insufficient_ingredient(give_ingredient, give_count):
                            print(f"    [*] 购买成功，重试兑换...")
                            # 重新尝试当前兑换
                            success_retry, message_retry = self.friend_actions.exchange_food_with_friend(
                                target_friend.get('id'),
                                self._get_food_code(want_ingredient),
                                self._get_food_code(give_ingredient)
                            )
                            if success_retry:
                                print(f"    ✅ 重试兑换成功: {message_retry}")
                                successful_individual_exchanges += 1
                            else:
                                print(f"    ❌ 重试兑换仍然失败: {message_retry}")
                                exchange_successful = False
                                break
                        else:
                            print(f"    ❌ 购买失败，终止兑换")
                            exchange_successful = False
                            break
                    else:
                        exchange_successful = False
                        break
            
            # 检查兑换是否完成
            if successful_individual_exchanges >= want_count:
                print(f"  ✅ 兑换完成: 成功{successful_individual_exchanges}/{want_count}")
            else:
                print(f"  ❌ 兑换失败: 仅完成 {successful_individual_exchanges}/{want_count}")
                exchange_successful = False
            
            results["total_attempts"] += 1
            
            detail = {
                "give": give_ingredient,
                "want": want_ingredient,
                "give_count": give_count,
                "want_count": want_count,
                "give_level": exchange.get('give_level', '?'),
                "want_level": exchange.get('want_level', '?'),
                "exchange_ratio": exchange_ratio,
                "success": exchange_successful,
                "individual_successes": successful_individual_exchanges,
                "message": f"完成 {successful_individual_exchanges}/{total_exchanges_needed} 次兑换"
            }
            results["exchange_details"].append(detail)
            
            if exchange_successful:
                results["successful_exchanges"] += 1
                print(f"  ✅ 兑换完成: {give_count}个{give_ingredient} → {want_count}个{want_ingredient}")
            else:
                results["failed_exchanges"] += 1
                print(f"  ❌ 兑换失败: 仅完成 {successful_individual_exchanges}/{total_exchanges_needed}")
        
        return results
    
    def _get_food_code(self, food_name: str) -> str:
        """根据食材名称获取食材代码"""
        try:
            # 加载食材数据
            foods_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "assets", "foods.json"
            )
            
            with open(foods_file_path, 'r', encoding='utf-8') as f:
                foods_data = json.load(f)
            
            # 在RECORDS中查找匹配的食材
            for record in foods_data.get("RECORDS", []):
                if record.get("name") == food_name:
                    return record.get("code", "1")
            
            # 如果未找到，使用备用映射
            food_codes = {
                '醋': '1',
                '白菜': '3', 
                '猪肉': '4',
                '生菜': '5'
            }
            return food_codes.get(food_name, '1')
            
        except Exception as e:
            print(f"[Error] 获取食材代码失败: {e}")
            return '1'
    
    def _get_ingredient_level(self, ingredient_name: str) -> int:
        """根据食材名称获取食材等级（橱柜API使用0-based）"""
        food_code = self._get_food_code(ingredient_name)
        level = game_data.get_level_by_code(food_code)
        # 橱柜API使用0-based等级：1级食材->level=0, 2级食材->level=1
        cupboard_level = (level - 1) if level is not None else 0
        return max(0, cupboard_level)  # 确保不为负数
    
    def _purchase_ingredient_with_gold(self, ingredient_name: str, needed_count: int) -> bool:
        """使用金币购买食材（1级用菜场，2级+用橱柜）"""
        foods_json_level = self._get_foods_json_level(ingredient_name)
        
        if foods_json_level == 1:
            # 1级食材使用菜场接口
            return self._purchase_from_market(ingredient_name, needed_count)
        else:
            # 2级及以上使用橱柜接口
            return self._purchase_from_cupboard(ingredient_name, needed_count, foods_json_level)
    
    def _purchase_from_market(self, ingredient_name: str, needed_count: int) -> bool:
        """从菜场购买1级食材（2换1策略）"""
        if not self.food_action:
            print("  ❌ 菜场接口未初始化，无法购买1级食材")
            return False
        
        # 2换1策略：需要needed_count个目标食材，买needed_count*2个任意1级食材
        purchase_count = needed_count * 2
        print(f"[*] 从菜场购买1级食材用于兑换: 目标{ingredient_name} {needed_count}个，需购买任意1级食材{purchase_count}个（2换1）")
        
        # 获取菜场可购买的食材列表
        available_foods = self.food_action.get_food_list()
        if not available_foods:
            print("  ❌ 无法获取菜场食材列表")
            return False
        
        # 选择第一个可购买的食材（通常是价格1200的1级食材）
        target_food = available_foods[0]
        food_name = target_food.get('name', '未知食材')
        
        print(f"  💰 菜场可购买: {[f.get('name') for f in available_foods]}")
        print(f"  🛒 选择购买: {food_name} x{purchase_count}")
        
        try:
            success, result = self.food_action.buy_food_by_name(food_name, purchase_count)
            if success:
                if isinstance(result, dict):
                    purchased_count = result.get('quantity_added', purchase_count)
                    gold_spent = result.get('gold_spent', 0)
                    print(f"  ✅ 菜场购买成功: 获得{purchased_count}个{food_name}，花费{gold_spent}金币")
                    
                    # 验证购买数量是否足够进行2换1兑换
                    can_exchange_count = purchased_count // 2  # 2个换1个
                    if can_exchange_count >= needed_count:
                        print(f"  🎯 购买足够: {purchased_count}个{food_name}可换{can_exchange_count}个{ingredient_name}（需要{needed_count}个）")
                        return True
                    else:
                        print(f"  ⚠️  购买不足: {purchased_count}个{food_name}只能换{can_exchange_count}个{ingredient_name}（需要{needed_count}个）")
                        return False
                else:
                    print(f"  ✅ 菜场购买成功: {result}")
                    return True  # 假设购买成功
            else:
                print(f"  ❌ 菜场购买失败: {result}")
                return False
                
        except Exception as e:
            print(f"  ❌ 菜场购买异常: {e}")
            return False
    
    def _purchase_from_cupboard(self, ingredient_name: str, needed_count: int, foods_json_level: int) -> bool:
        """从橱柜购买2级+食材"""
        if not self.cupboard_action:
            print("  ❌ 橱柜接口未初始化，无法购买高级食材")
            return False
        
        # 计算购买批次 (橱柜每次购买10个)
        batches_needed = (needed_count + 9) // 10  # 向上取整
        
        print(f"[*] 从橱柜购买{foods_json_level}级食材: {ingredient_name}，需要{needed_count}个，将购买{batches_needed}批次")
        
        # 橱柜API使用foods.json的等级值（已确认2级食材用level=2成功）
        cupboard_level = foods_json_level
        
        total_purchased = 0
        for batch in range(batches_needed):
            success, message = self.cupboard_action.buy_random_food(cupboard_level, 10)
            if success:
                total_purchased += 10
                print(f"  ✅ 第{batch+1}批次购买成功: {message}")
            else:
                print(f"  ❌ 第{batch+1}批次购买失败: {message}")
                break
        
        purchase_successful = total_purchased >= needed_count
        if purchase_successful:
            print(f"  🎉 橱柜购买完成: 获得{total_purchased}个食材（需要{needed_count}个）")
        else:
            print(f"  ⚠️  橱柜购买不足: 获得{total_purchased}个食材（需要{needed_count}个）")
        
        return purchase_successful
    
    def _attempt_2to1_exchange(self, target_friend: Dict[str, Any], want_ingredient: str, want_count: int) -> bool:
        """
        真正的2换1兑换策略
        
        根据游戏机制分析：
        - 游戏不支持直接的2:1兑换接口
        - 需要通过其他方式实现2换1的效果
        - 可能的方案：连续兑换或寻找其他好友
        """
        if not target_friend:
            return False
        
        print(f"    🔄 尝试实现2换1兑换: 获得{want_count}个{want_ingredient}")
        
        # 当前游戏接口限制：只支持1:1兑换
        # 暂时使用1:1兑换作为替代方案
        friend_id = target_friend.get('id')
        want_code = self._get_food_code(want_ingredient)
        
        # 获取菜场购买的食材作为兑换源
        available_foods = self.food_action.get_food_list() if self.food_action else []
        if not available_foods:
            print("    ❌ 无法获取菜场食材列表")
            return False
        
        source_food = available_foods[0]
        source_code = source_food.get('code', '1')
        source_name = source_food.get('name', '未知食材')
        
        print(f"    📋 兑换方案: 使用{source_name}兑换{want_ingredient}")
        
        successful_exchanges = 0
        
        for i in range(want_count):
            print(f"    第{i+1}/{want_count}次兑换...")
            
            try:
                success, message = self.friend_actions.exchange_food_with_friend(
                    friend_id,
                    want_code,
                    source_code
                )
                
                if success:
                    successful_exchanges += 1
                    print(f"      ✅ 兑换成功: {message}")
                else:
                    print(f"      ❌ 兑换失败: {message}")
                    # 分析失败原因
                    if "相同的食材" in message:
                        print(f"      💡 游戏限制：不能用相同食材兑换")
                    break
                    
            except Exception as e:
                print(f"      ❌ 兑换异常: {e}")
                break
        
        success_rate = successful_exchanges >= want_count
        if success_rate:
            print(f"    ✅ 兑换完成: {successful_exchanges}/{want_count}")
        else:
            print(f"    ❌ 兑换未完成: {successful_exchanges}/{want_count}")
        
        return success_rate
    
    def get_current_inventory(self) -> Dict[str, int]:
        """获取当前真实库存（从橱柜）"""
        if not self.cupboard_action:
            print("  ❌ 橱柜接口未初始化，无法获取库存")
            return {}
        
        print("[*] 正在获取当前库存...")
        inventory = {}
        
        # 获取所有等级的食材
        for cupboard_type in [CupboardType.LEVEL_1, CupboardType.LEVEL_2, CupboardType.LEVEL_3, 
                             CupboardType.LEVEL_4, CupboardType.LEVEL_5]:
            items = self.cupboard_action.get_items(cupboard_type)
            for item in items:
                food_name = item.get('food_name', '')
                food_count = int(item.get('num', 0))
                if food_name and food_count > 0:
                    inventory[food_name] = inventory.get(food_name, 0) + food_count
        
        print(f"[+] 当前库存: {len(inventory)}种食材，总计{sum(inventory.values())}个")
        return inventory
    
    def get_available_for_exchange(self, inventory: Dict[str, int], required: Dict[str, int]) -> Dict[str, int]:
        """获取可用于兑换的食材（数量>=2且不是必需的）"""
        available = {}
        
        for food_name, current_count in inventory.items():
            required_count = required.get(food_name, 0)
            surplus = current_count - required_count
            
            # 只有数量>=2且有剩余的才能用于兑换（2个换1个）
            if surplus >= 2:
                available[food_name] = (surplus // 2) * 2  # 确保是偶数，2个一组
        
        return available
    
    def _validate_exchange(self, exchange: Dict[str, Any]) -> bool:
        """验证兑换是否可行（库存充足，等级匹配）"""
        give_ingredient = exchange['give']
        want_ingredient = exchange['want']
        give_count = exchange['give_count']
        give_level = exchange['give_level']
        want_level = exchange['want_level']
        
        # 等级验证
        if give_level != want_level:
            print(f"    ❌ 等级不匹配: {give_ingredient}(L{give_level}) ≠ {want_ingredient}(L{want_level})")
            return False
        
        # 库存验证
        current_inventory = self.get_current_inventory()
        current_count = current_inventory.get(give_ingredient, 0)
        
        if current_count < give_count:
            print(f"    ❌ 库存不足: {give_ingredient} 需要{give_count}个，仅有{current_count}个")
            return False
        
        print(f"    ✅ 验证通过: {give_ingredient}(L{give_level}) 库存{current_count}个，需要{give_count}个")
        return True
    
    def _handle_insufficient_ingredient(self, ingredient_name: str, needed_count: int) -> bool:
        """处理食材不足情况"""
        print(f"    [*] 处理食材不足: {ingredient_name} 需要{needed_count}个")
        
        purchase_success = self._purchase_ingredient_with_gold(ingredient_name, needed_count)
        if purchase_success:
            print(f"    ✅ 购买成功，现在可以继续兑换")
            return True
        else:
            print(f"    ❌ 购买失败，无法继续兑换")
            return False

class CookbookWorker(QThread):
    """后台线程处理食谱查询"""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, cookbook_actions: CookbookActions, cookbook_type: CookbookType, street: Street):
        super().__init__()
        self.cookbook_actions = cookbook_actions
        self.cookbook_type = cookbook_type
        self.street = street
    
    def run(self):
        try:
            recipes = self.cookbook_actions.get_all_cookbooks(self.cookbook_type, self.street)
            self.finished.emit(recipes or [])
        except Exception as e:
            self.error.emit(str(e))

class CookbookPage(QWidget):
    """食谱管理页面"""
    
    def __init__(self, log_widget: QTextEdit, account_manager: AccountManager):
        super().__init__()
        self.log_widget = log_widget
        self.account_manager = account_manager
        self.calculator = RecipeIngredientCalculator()
        self.current_recipes = []
        self.selected_recipes = []
        self.current_gold = 0  # 当前金币数量
        self.restaurant_star = 0  # 餐厅星级
        self.max_exchange_level = 3  # 最大可兑换等级（星级+1，最高5）
        
        # 好友兑换相关
        self.available_friends = []  # 拥有目标食材的好友列表
        self.current_inventory = {}  # 当前库存
        self.surplus_foods = {}  # 可用于兑换的多余食材
        
        self._init_ui()
        self._populate_accounts()
        self._populate_filters()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar_layout = self._create_toolbar()
        layout.addLayout(toolbar_layout)
        
        # 分割器：食谱表格 + 统计面板
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 食谱表格
        self.recipes_table = self._create_recipes_table()
        splitter.addWidget(self.recipes_table)
        
        # 统计面板
        stats_panel = self._create_stats_panel()
        splitter.addWidget(stats_panel)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def _create_toolbar(self) -> QVBoxLayout:
        """创建工具栏"""
        toolbar_layout = QVBoxLayout()
        
        # 第一行：基本控件
        first_row = QHBoxLayout()
        
        # 账号选择
        first_row.addWidget(QLabel("选择账号:"))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(150)
        first_row.addWidget(self.account_combo)
        
        # 街道筛选
        first_row.addWidget(QLabel("街道筛选:"))
        self.street_combo = QComboBox()
        self.street_combo.setMinimumWidth(120)
        first_row.addWidget(self.street_combo)
        
        # 食谱类型
        first_row.addWidget(QLabel("食谱类型:"))
        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(100)
        first_row.addWidget(self.type_combo)
        
        # 查询按钮
        self.query_btn = QPushButton("查询食谱")
        self.query_btn.clicked.connect(self._query_recipes)
        first_row.addWidget(self.query_btn)
        
        first_row.addStretch()
        toolbar_layout.addLayout(first_row)
        
        # 第二行：多选功能
        second_row = QHBoxLayout()
        
        second_row.addWidget(QLabel("快速选择:"))
        
        self.select_basic_btn = QPushButton("全选基础菜")
        self.select_basic_btn.clicked.connect(lambda: self._select_by_type('basic'))
        second_row.addWidget(self.select_basic_btn)
        
        self.select_yu_chi_btn = QPushButton("选中鱼翅菜")
        self.select_yu_chi_btn.clicked.connect(lambda: self._select_by_type('yu_chi'))
        second_row.addWidget(self.select_yu_chi_btn)
        
        self.select_bao_yu_btn = QPushButton("选中鲍鱼菜")
        self.select_bao_yu_btn.clicked.connect(lambda: self._select_by_type('bao_yu'))
        second_row.addWidget(self.select_bao_yu_btn)
        
        self.select_mystery_btn = QPushButton("选中神秘菜")
        self.select_mystery_btn.clicked.connect(lambda: self._select_by_type('mystery'))
        second_row.addWidget(self.select_mystery_btn)
        
        self.clear_selection_btn = QPushButton("清除选择")
        self.clear_selection_btn.clicked.connect(self._clear_selection)
        second_row.addWidget(self.clear_selection_btn)
        
        # 学习规划按钮
        self.plan_btn = QPushButton("学习规划")
        self.plan_btn.clicked.connect(self._calculate_requirements)
        second_row.addWidget(self.plan_btn)
        
        # 查看当前库存按钮
        self.inventory_btn = QPushButton("查看当前库存")
        self.inventory_btn.clicked.connect(self._show_current_inventory)
        second_row.addWidget(self.inventory_btn)
        
        second_row.addStretch()
        toolbar_layout.addLayout(second_row)
        
        return toolbar_layout
    
    def _create_recipes_table(self) -> QTableWidget:
        """创建食谱表格"""
        table = QTableWidget()
        table.verticalHeader().setVisible(False)
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["选择", "食谱名称", "等级", "街道", "状态", "操作"])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        table.setColumnWidth(0, 50)
        table.setColumnWidth(2, 60)
        table.setColumnWidth(5, 180)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        
        return table
    
    def _create_stats_panel(self) -> QWidget:
        """创建统计面板"""
        panel = QFrame()
        panel.setObjectName("StatsPanel")
        layout = QVBoxLayout(panel)
        
        # 第一行：标题和金币信息
        header_layout = QHBoxLayout()
        
        title = QLabel("食材需求统计")
        title.setProperty("role", "Title")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 当前金币显示
        self.gold_label = QLabel("当前金币: 加载中...")
        self.gold_label.setStyleSheet("QLabel { color: #FFD700; font-weight: bold; }")
        header_layout.addWidget(self.gold_label)
        
        # 刷新金币按钮
        refresh_gold_btn = QPushButton("刷新金币")
        refresh_gold_btn.clicked.connect(self._refresh_gold)
        header_layout.addWidget(refresh_gold_btn)
        
        layout.addLayout(header_layout)
        
        # 统计文本
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(80)  # 降低统计结果显示高度
        layout.addWidget(self.stats_text)
        
        # 食材金币兑换面板
        exchange_panel = self._create_exchange_panel()
        layout.addWidget(exchange_panel)
        
        # 食材合成面板
        synthesis_panel = self._create_synthesis_panel()
        layout.addWidget(synthesis_panel)
        
        # 菜场购买面板
        market_panel = self._create_market_purchase_panel()
        layout.addWidget(market_panel)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.batch_learn_btn = QPushButton("开始批量学习")
        self.batch_learn_btn.clicked.connect(self._batch_learn)
        btn_layout.addWidget(self.batch_learn_btn)
        
        self.smart_exchange_btn = QPushButton("智能兑换缺少食材")
        self.smart_exchange_btn.clicked.connect(self._smart_exchange)
        btn_layout.addWidget(self.smart_exchange_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return panel
    
    def _create_exchange_panel(self) -> QWidget:
        """创建食材金币兑换面板"""
        exchange_group = QGroupBox("食材金币兑换")
        exchange_layout = QHBoxLayout(exchange_group)
        
        # 等级选择
        exchange_layout.addWidget(QLabel("食材等级:"))
        self.level_combo = QComboBox()
        # 初始化所有等级，后续根据餐厅星级动态启用/禁用
        self.level_combo.addItem("2级食材", 2)
        self.level_combo.addItem("3级食材", 3) 
        self.level_combo.addItem("4级食材", 4)
        self.level_combo.addItem("5级食材", 5)
        self.level_combo.currentTextChanged.connect(self._update_exchange_cost)
        exchange_layout.addWidget(self.level_combo)
        
        # 数量输入
        exchange_layout.addWidget(QLabel("兑换数量:"))
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.setMinimum(1)
        self.quantity_spinbox.setMaximum(999)
        self.quantity_spinbox.setValue(10)
        self.quantity_spinbox.valueChanged.connect(self._update_exchange_cost)
        exchange_layout.addWidget(self.quantity_spinbox)
        
        # 成本显示
        self.cost_label = QLabel("预估成本: 计算中...")
        self.cost_label.setStyleSheet("QLabel { color: #FFA500; font-weight: bold; }")
        exchange_layout.addWidget(self.cost_label)
        
        # 兑换按钮
        self.exchange_btn = QPushButton("开始兑换")
        self.exchange_btn.clicked.connect(self._exchange_food_with_gold)
        exchange_layout.addWidget(self.exchange_btn)
        
        exchange_layout.addStretch()
        
        # 初始化成本显示
        self._update_exchange_cost()
        
        return exchange_group
    
    def _create_synthesis_panel(self) -> QWidget:
        """创建简单食材合成面板"""
        synthesis_group = QGroupBox("食材合成")
        main_layout = QVBoxLayout(synthesis_group)
        
        # 说明文本
        info_label = QLabel("⚗️ 简单合成：2个同级食材 → 1个高一级食材（自动寻找多余食材）")
        info_label.setStyleSheet("QLabel { color: #28A745; font-style: italic; }")
        main_layout.addWidget(info_label)
        
        # 合成设置面板
        synthesis_layout = QHBoxLayout()
        
        # 目标等级选择
        synthesis_layout.addWidget(QLabel("合成等级:"))
        self.synthesis_level_combo = QComboBox()
        self.synthesis_level_combo.addItem("2级食材", 2)
        self.synthesis_level_combo.addItem("3级食材", 3)
        self.synthesis_level_combo.addItem("4级食材", 4)
        self.synthesis_level_combo.addItem("5级食材", 5)
        synthesis_layout.addWidget(self.synthesis_level_combo)
        
        # 合成数量
        synthesis_layout.addWidget(QLabel("合成数量:"))
        self.synthesis_quantity_spinbox = QSpinBox()
        self.synthesis_quantity_spinbox.setMinimum(1)
        self.synthesis_quantity_spinbox.setMaximum(100)
        self.synthesis_quantity_spinbox.setValue(5)
        synthesis_layout.addWidget(self.synthesis_quantity_spinbox)
        
        # 开始合成按钮
        self.start_synthesis_btn = QPushButton("开始合成")
        self.start_synthesis_btn.clicked.connect(self._start_simple_synthesis)
        synthesis_layout.addWidget(self.start_synthesis_btn)
        
        synthesis_layout.addStretch()
        main_layout.addLayout(synthesis_layout)
        
        return synthesis_group
    
    def _create_market_purchase_panel(self) -> QWidget:
        """创建菜场购买面板"""
        market_group = QGroupBox("菜场精准购买")
        main_layout = QVBoxLayout(market_group)
        
        # 说明文本
        info_label = QLabel("🏪 精准购买1级基础食材（解决金币兑换随机性问题）")
        info_label.setStyleSheet("QLabel { color: #28A745; font-style: italic; }")
        main_layout.addWidget(info_label)
        
        # 菜场食材显示区域
        foods_layout = QVBoxLayout()
        foods_layout.addWidget(QLabel("当前菜场售卖食材:"))
        
        self.market_foods_text = QTextEdit()
        self.market_foods_text.setMaximumHeight(60)
        self.market_foods_text.setReadOnly(True)
        self.market_foods_text.setPlaceholderText("点击'刷新菜场'查看当前售卖的食材...")
        foods_layout.addWidget(self.market_foods_text)
        main_layout.addLayout(foods_layout)
        
        # 购买控制面板
        purchase_layout = QHBoxLayout()
        
        # 刷新菜场按钮
        self.refresh_market_btn = QPushButton("刷新菜场")
        self.refresh_market_btn.clicked.connect(self._refresh_market_foods)
        purchase_layout.addWidget(self.refresh_market_btn)
        
        # 食材选择
        purchase_layout.addWidget(QLabel("选择食材:"))
        self.market_food_combo = QComboBox()
        self.market_food_combo.setMinimumWidth(120)
        purchase_layout.addWidget(self.market_food_combo)
        
        # 购买数量
        purchase_layout.addWidget(QLabel("数量:"))
        self.market_quantity_spinbox = QSpinBox()
        self.market_quantity_spinbox.setMinimum(1)
        self.market_quantity_spinbox.setMaximum(999)
        self.market_quantity_spinbox.setValue(10)
        purchase_layout.addWidget(self.market_quantity_spinbox)
        
        # 预估成本显示
        self.market_cost_label = QLabel("预估成本: 计算中...")
        self.market_cost_label.setStyleSheet("QLabel { color: #FFA500; font-weight: bold; }")
        self.market_quantity_spinbox.valueChanged.connect(self._update_market_cost)
        self.market_food_combo.currentTextChanged.connect(self._update_market_cost)
        purchase_layout.addWidget(self.market_cost_label)
        
        # 购买按钮
        self.buy_market_food_btn = QPushButton("购买食材")
        self.buy_market_food_btn.clicked.connect(self._buy_market_food)
        self.buy_market_food_btn.setEnabled(False)
        purchase_layout.addWidget(self.buy_market_food_btn)
        
        purchase_layout.addStretch()
        main_layout.addLayout(purchase_layout)
        
        return market_group
    
    def _start_simple_synthesis(self):
        """开始简单合成"""
        # 这是一个占位符方法，您可以根据需要实现具体逻辑
        QMessageBox.information(self, "提示", "简单合成功能尚未实现")
    
    def _refresh_market_foods(self):
        """刷新菜场食材"""
        # 这是一个占位符方法，您可以根据需要实现具体逻辑
        self.market_foods_text.setText("菜场食材刷新功能尚未实现")
    
    def _update_market_cost(self):
        """更新市场成本预估"""
        # 这是一个占位符方法，您可以根据需要实现具体逻辑
        quantity = self.market_quantity_spinbox.value()
        self.market_cost_label.setText(f"预估成本: {quantity * 50} 金币")
    
    def _buy_market_food(self):
        """购买市场食材"""
        # 这是一个占位符方法，您可以根据需要实现具体逻辑
        QMessageBox.information(self, "提示", "市场食材购买功能尚未实现")

    def _populate_accounts(self):
        """填充账号列表"""
        self.account_combo.clear()
        accounts = self.account_manager.list_accounts()
        for acc in accounts:
            self.account_combo.addItem(acc.username, userData=acc.id)
    
    def _populate_filters(self):
        """填充筛选器"""
        # 街道筛选 - 包含所有街道
        street_map = {
            "全部": Street.CURRENT,
            "家常菜": Street.HOMESTYLE,
            "湘菜": Street.XIANG,
            "粤菜": Street.YUE,
            "川菜": Street.CHUAN,
            "闽菜": Street.MIN,
            "徽菜": Street.HUI,
            "鲁菜": Street.LU,
            "浙菜": Street.ZHE,
            "苏菜": Street.SU,
            "综一": Street.ZONG1,
            "综二": Street.ZONG2
        }
        for name, street in street_map.items():
            self.street_combo.addItem(name, userData=street)
        
        # 食谱类型
        type_map = {
            "可学": CookbookType.LEARNABLE,
            "未学": CookbookType.UNLEARNED,
            "初级": CookbookType.PRIMARY,
            "特色": CookbookType.SPECIAL,
            "上品": CookbookType.FINE,
            "极品": CookbookType.SUPER,
            "金牌": CookbookType.GOLD
        }
        for name, cookbook_type in type_map.items():
            self.type_combo.addItem(name, userData=cookbook_type)
    
    @Slot()
    def _query_recipes(self):
        """查询食谱"""
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号")
            return
        
        # 获取账号信息
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效，请先刷新")
            return
        
        cookbook_type = self.type_combo.currentData()
        street = self.street_combo.currentData()
        
        self.log_widget.append(f"📚 正在查询 '{account.username}' 的食谱...")
        self.query_btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        # 创建CookbookActions实例
        cookbook_actions = CookbookActions(
            key=account.key,
            cookie={"PHPSESSID": account.cookie} if account.cookie else None
        )
        
        # 启动后台线程
        self.worker = CookbookWorker(cookbook_actions, cookbook_type, street)
        self.worker.finished.connect(self._on_recipes_loaded)
        self.worker.error.connect(self._on_recipes_error)
        self.worker.start()
    
    @Slot(list)
    def _on_recipes_loaded(self, recipes: List[Dict[str, Any]]):
        """食谱加载完成"""
        QApplication.restoreOverrideCursor()
        self.query_btn.setEnabled(True)
        
        self.current_recipes = recipes
        self._populate_recipes_table()
        
        self.log_widget.append(f"✅ 查询完成，共找到 {len(recipes)} 个食谱")
    
    @Slot(str)
    def _on_recipes_error(self, error_msg: str):
        """食谱查询错误"""
        QApplication.restoreOverrideCursor()
        self.query_btn.setEnabled(True)
        self.log_widget.append(f"❌ 查询失败: {error_msg}")
    
    def _populate_recipes_table(self):
        """填充食谱表格"""
        self.recipes_table.setRowCount(len(self.current_recipes))
        
        for row, recipe in enumerate(self.current_recipes):
            # 选择复选框
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(lambda state, r=row: self._on_recipe_selected(r, state))
            self.recipes_table.setCellWidget(row, 0, checkbox)
            
            # 食谱信息
            name_item = QTableWidgetItem(recipe.get('name', '未知'))
            level_item = QTableWidgetItem(str(recipe.get('level', '0')))
            street_item = QTableWidgetItem(recipe.get('street_name', '未知'))
            status_item = QTableWidgetItem(recipe.get('status_name', '未知'))
            
            for item in [name_item, level_item, street_item, status_item]:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            self.recipes_table.setItem(row, 1, name_item)
            self.recipes_table.setItem(row, 2, level_item)
            self.recipes_table.setItem(row, 3, street_item)
            self.recipes_table.setItem(row, 4, status_item)
            
            # 操作按钮
            self._add_recipe_action_buttons(row, recipe)
    
    def _add_recipe_action_buttons(self, row: int, recipe: Dict[str, Any]):
        """添加食谱操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        # 学习/升级按钮
        learn_btn = QPushButton("学习" if recipe.get('can_learn') else "升级")
        learn_btn.clicked.connect(lambda: self._learn_recipe(recipe))
        layout.addWidget(learn_btn)
        
        # 查看材料按钮
        materials_btn = QPushButton("查看材料")
        materials_btn.clicked.connect(lambda: self._show_materials(recipe))
        layout.addWidget(materials_btn)
        
        layout.addStretch()
        self.recipes_table.setCellWidget(row, 5, widget)
    
    def _on_recipe_selected(self, row: int, state: int):
        """食谱选择状态改变"""
        if state == Qt.CheckState.Checked.value:
            if row < len(self.current_recipes):
                recipe = self.current_recipes[row]
                if recipe not in self.selected_recipes:
                    self.selected_recipes.append(recipe)
        else:
            if row < len(self.current_recipes):
                recipe = self.current_recipes[row]
                if recipe in self.selected_recipes:
                    self.selected_recipes.remove(recipe)
    
    def _select_by_type(self, ingredient_type: str):
        """按食材类型选择食谱"""
        if not self.current_recipes:
            QMessageBox.information(self, "提示", "请先查询食谱")
            return
        
        selected_count = 0
        for row in range(len(self.current_recipes)):
            recipe = self.current_recipes[row]
            recipe_name = recipe.get('name', '')
            recipe_level = int(recipe.get('level', 1))
            street_name = recipe.get('street_name', '')
            
            # 获取真实食材需求
            ingredients = self.calculator.get_recipe_ingredients(recipe_name, recipe_level, street_name)
            
            # 检查是否包含对应类型的食材
            should_select = False
            if ingredient_type == 'basic':
                # 基础菜：不包含鱼翅、鲍鱼、神秘食材
                should_select = not any(
                    self.calculator.classify_ingredient(ing) in ['yu_chi', 'bao_yu', 'mystery'] 
                    for ing in ingredients.keys()
                )
            elif ingredient_type == 'yu_chi':
                should_select = any(
                    self.calculator.classify_ingredient(ing) == 'yu_chi' 
                    for ing in ingredients.keys()
                )
            elif ingredient_type == 'bao_yu':
                should_select = any(
                    self.calculator.classify_ingredient(ing) == 'bao_yu' 
                    for ing in ingredients.keys()
                )
            elif ingredient_type == 'mystery':
                should_select = any(
                    self.calculator.classify_ingredient(ing) == 'mystery' 
                    for ing in ingredients.keys()
                )
            
            # 更新复选框状态
            checkbox = self.recipes_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox) and should_select:
                checkbox.setChecked(True)
                # 手动更新selected_recipes，确保同步
                if recipe not in self.selected_recipes:
                    self.selected_recipes.append(recipe)
                selected_count += 1
        
        type_names = {
            'basic': '基础菜',
            'yu_chi': '鱼翅菜', 
            'bao_yu': '鲍鱼菜',
            'mystery': '神秘菜'
        }
        self.log_widget.append(f"✅ 已选中 {selected_count} 个{type_names[ingredient_type]}食谱")
    
    def _clear_selection(self):
        """清除所有选择"""
        for row in range(self.recipes_table.rowCount()):
            checkbox = self.recipes_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(False)
        
        self.selected_recipes.clear()
        self.log_widget.append("🔄 已清除所有选择")
    
    def _show_current_inventory(self):
        """显示当前真实库存"""
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效")
            return
        
        try:
            # 创建橱柜接口
            cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
            cupboard_action = CupboardAction(key=account.key, cookie=cookie_dict)
            
            # 创建策略实例获取库存
            strategy = SmartExchangeStrategy(None, cupboard_action, None)
            inventory = strategy.get_current_inventory()
            
            if not inventory:
                QMessageBox.information(self, "库存查询", "当前库存为空或无法获取库存数据")
                return
            
            # 按等级分组显示库存
            inventory_by_level = {}
            for food_name, count in inventory.items():
                level = strategy._get_foods_json_level(food_name)
                if level not in inventory_by_level:
                    inventory_by_level[level] = []
                inventory_by_level[level].append(f"{food_name}: {count}个")
            
            # 生成显示文本
            inventory_text = f"账号: {account.username}\n"
            inventory_text += f"总食材种类: {len(inventory)}种\n"
            inventory_text += f"总食材数量: {sum(inventory.values())}个\n\n"
            
            # 按等级显示
            for level in sorted(inventory_by_level.keys()):
                if level == 0:
                    continue  # 跳过未知等级
                
                level_foods = inventory_by_level[level]
                inventory_text += f"=== {level}级食材 ({len(level_foods)}种) ===\n"
                
                # 按名称排序显示
                for food_info in sorted(level_foods):
                    inventory_text += f"  {food_info}\n"
                inventory_text += "\n"
            
            # 创建可滚动的对话框
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle("当前库存")
            dialog.resize(500, 600)
            
            layout = QVBoxLayout(dialog)
            
            text_edit = QTextEdit()
            text_edit.setPlainText(inventory_text)
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("SF Pro Text", 10))
            layout.addWidget(text_edit)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取库存失败: {str(e)}")
    
    def _get_recipe_ingredient_types(self, recipe: Dict[str, Any]) -> List[str]:
        """获取食谱包含的食材类型"""
        recipe_name = recipe.get('name', '')
        recipe_level = int(recipe.get('level', 1))
        street_name = recipe.get('street_name', '')
        
        ingredients = self.calculator.get_recipe_ingredients(recipe_name, recipe_level, street_name)
        
        types = set()
        for ingredient in ingredients.keys():
            ingredient_type = self.calculator.classify_ingredient(ingredient)
            types.add(ingredient_type)
        
        return list(types)
    
    @Slot()
    def _calculate_requirements(self):
        """计算食材需求（集成真实库存）"""
        if not self.selected_recipes:
            QMessageBox.information(self, "提示", "请先选择要学习的食谱")
            return
        
        # 获取账号信息
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号以获取真实库存")
            return
        
        # 获取当前街道
        current_street = self.street_combo.currentText()
        
        # 计算需求（排除昂贵食材，学到极品级）
        requirements = self.calculator.calculate_requirements(
            self.selected_recipes, current_street, exclude_expensive=True
        )
        
        # 获取真实库存
        current_inventory = {}
        try:
            account = self.account_manager.get_account(account_id)
            if account and account.key:
                cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
                cupboard_action = CupboardAction(key=account.key, cookie=cookie_dict)
                strategy = SmartExchangeStrategy(None, cupboard_action, None)
                current_inventory = strategy.get_current_inventory()
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法获取库存数据: {str(e)}\n将使用默认值进行计算")
        
        # 生成学习路径信息 (对于"可学"状态的食谱，全部都是需要学习的)
        learning_paths = []
        
        for recipe in self.selected_recipes:
            recipe_name = recipe.get('name', '')
            recipe_street = recipe.get('street_name', '')
            target_level = int(recipe.get('level', 1))  # 学习完成后将到达的等级
            
            # 计算当前实际等级：目标等级-1
            current_actual_level = target_level - 1 if target_level > 1 else 1
            
            # 对于"可学"状态的食谱，显示学习路径
            learning_paths.append(f"{recipe_name}: {current_actual_level}级 → {target_level}级")
        
        # 显示统计信息 (对于"可学"状态，所有食谱都需要学习)
        stats_text = f"当前选择了 {len(self.selected_recipes)} 个「可学」状态食谱的学习计划:\n\n"
        
        # 显示学习路径
        if learning_paths:
            stats_text += "【学习路径】\n"
            for path in learning_paths[:8]:  # 显示前8个，避免过长
                stats_text += f"• {path}\n"
            if len(learning_paths) > 8:
                stats_text += f"• ... 还有 {len(learning_paths) - 8} 个食谱\n"
        else:
            stats_text += "【学习路径】\n"
            stats_text += "• 没有选择任何食谱\n"
        stats_text += "\n"
        
        if requirements:
            # 按食材类型分组
            basic_requirements = {}
            expensive_requirements = {}
            
            for ingredient, count in requirements.items():
                ingredient_type = self.calculator.classify_ingredient(ingredient)
                if ingredient_type in ['yu_chi', 'bao_yu', 'mystery']:
                    expensive_requirements[ingredient] = count
                else:
                    basic_requirements[ingredient] = count
            
            # 显示基础食材需求（包括1-5级所有可兑换食材）
            if basic_requirements:
                stats_text += "【基础食材需求】（包括1-5级食材）\n"
                for ingredient, count in basic_requirements.items():
                    # 使用真实库存数据
                    current_count = current_inventory.get(ingredient, 0)
                    deficit = max(0, count - current_count)
                    
                    # 状态标识
                    if current_count >= count:
                        status = "✅"
                    elif current_count > 0:
                        status = "⚠️"
                    else:
                        status = "❌"
                    
                    # 获取食材等级
                    ingredient_level = self._get_food_level(ingredient)
                    level_text = f"({ingredient_level}级)" if ingredient_level else ""
                    stats_text += f"• {status} {ingredient}{level_text}: 需要{count}个 (拥有{current_count}个)"
                    if deficit > 0:
                        stats_text += f" - 缺少{deficit}个"
                    stats_text += "\n"
            
            # 显示特殊食材需求（鱼翅、鲍鱼、神秘食材）
            if expensive_requirements:
                stats_text += "\n【特殊食材需求】（鱼翅/鲍鱼/神秘）⚠️\n"
                for ingredient, count in expensive_requirements.items():
                    ingredient_type = self.calculator.classify_ingredient(ingredient)
                    type_labels = {
                        'yu_chi': '🐟鱼翅',
                        'bao_yu': '🦪鲍鱼',
                        'mystery': '✨神秘'
                    }
                    label = type_labels.get(ingredient_type, '')
                    
                    # 使用真实库存数据
                    current_count = current_inventory.get(ingredient, 0)
                    deficit = max(0, count - current_count)
                    
                    # 状态标识
                    if current_count >= count:
                        status = "✅"
                    elif current_count > 0:
                        status = "⚠️"
                    else:
                        status = "❌"
                    
                    stats_text += f"• {status} {ingredient} {label}: 需要{count}个 (拥有{current_count}个)"
                    if deficit > 0:
                        stats_text += f" - 缺少{deficit}个"
                    stats_text += "\n"
                
                stats_text += "\n💰 提示: 特殊食材价格昂贵，建议优先学习基础食谱"
            
            # 添加总结统计
            total_basic = len(basic_requirements)
            total_expensive = len(expensive_requirements)
            
            if current_inventory:
                # 计算完成度
                total_needed = sum(requirements.values())
                total_owned = sum(current_inventory.get(ing, 0) for ing in requirements.keys())
                completion_rate = total_owned / total_needed * 100 if total_needed > 0 else 0
                
                # 计算缺少的食材数量
                total_shortage = sum(max(0, count - current_inventory.get(ingredient, 0)) 
                                   for ingredient, count in requirements.items())
                
                stats_text += f"\n📊 完成度统计:\n"
                stats_text += f"• 总需求: {total_needed}个食材\n"
                stats_text += f"• 总拥有: {total_owned}个食材\n" 
                stats_text += f"• 完成度: {completion_rate:.1f}%\n"
                stats_text += f"• 还需要: {total_shortage}个食材\n"
            
            stats_text += f"\n📈 分类统计: {total_basic}种基础食材（1-5级），{total_expensive}种特殊食材（鱼翅/鲍鱼/神秘）"
            
        else:
            stats_text += "未找到有效的食材需求"
        
        self.stats_text.setPlainText(stats_text)
        self.log_widget.append(f"📊 已计算 {len(self.selected_recipes)} 个食谱的食材需求（含特殊食材）")
    
    def _learn_recipe(self, recipe: Dict[str, Any]):
        """学习食谱"""
        account_id = self.account_combo.currentData()
        if account_id is None:
            return
        
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效")
            return
        
        cookbook_actions = CookbookActions(
            key=account.key,
            cookie={"PHPSESSID": account.cookie} if account.cookie else None
        )
        
        recipe_name = recipe.get('name', '未知食谱')
        recipe_code = recipe.get('code')
        
        self.log_widget.append(f"📖 正在学习食谱: {recipe_name}")
        
        success, message = cookbook_actions.study_recipe(recipe_code)
        if success:
            self.log_widget.append(f"✅ 学习成功: {message}")
        else:
            self.log_widget.append(f"❌ 学习失败: {message}")
    
    @Slot()
    def _batch_learn(self):
        """批量学习"""
        if not self.selected_recipes:
            QMessageBox.information(self, "提示", "请先选择要学习的食谱")
            return
        
        account_id = self.account_combo.currentData()
        if account_id is None:
            return
        
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效")
            return
        
        cookbook_actions = CookbookActions(
            key=account.key,
            cookie={"PHPSESSID": account.cookie} if account.cookie else None
        )
        
        self.log_widget.append(f"🎯 开始批量学习 {len(self.selected_recipes)} 个食谱...")
        
        success_count = 0
        for recipe in self.selected_recipes:
            recipe_name = recipe.get('name', '未知食谱')
            recipe_code = recipe.get('code')
            
            success, message = cookbook_actions.study_recipe(recipe_code)
            if success:
                success_count += 1
                self.log_widget.append(f"  ✅ {recipe_name}: {message}")
            else:
                self.log_widget.append(f"  ❌ {recipe_name}: {message}")
        
        self.log_widget.append(f"🏁 批量学习完成: 成功 {success_count}/{len(self.selected_recipes)} 个")
    
    @Slot()
    def _smart_exchange(self):
        """智能兑换（集成金币购买）"""
        account_id = self.account_combo.currentData()
        if account_id is None:
            return
        
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效")
            return
        
        # 创建Action实例
        cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
        
        friend_actions = FriendActions(
            key=account.key,
            cookie=cookie_dict
        )
        
        cupboard_action = CupboardAction(
            key=account.key,
            cookie=cookie_dict
        )
        
        food_action = FoodActions(
            key=account.key,
            cookie=cookie_dict
        )
        
        # 创建增强的智能兑换策略（橱柜+菜场）
        strategy = SmartExchangeStrategy(friend_actions, cupboard_action, food_action)
        
        # 获取真实的食材需求 - 基于选中的食谱计算
        current_street = self.street_combo.currentText()
        required_ingredients = self.calculator.calculate_requirements(
            self.selected_recipes, 
            current_street, 
            exclude_expensive=True
        )
        
        if not required_ingredients:
            self.log_widget.append("💡 没有选中食谱或无食材需求")
            return
        
        # 生成兑换计划（自动获取真实库存）
        plan = strategy.get_exchange_plan(required_ingredients)
        
        if not plan:
            self.log_widget.append("💡 当前库存充足，无需兑换")
            return
        
        self.log_widget.append(f"🔄 开始执行智能兑换计划 ({len(plan)} 项)...")
        self.log_widget.append(f"📊 食材需求: {required_ingredients}")
        
        # 执行兑换（自动处理食材不足情况）
        results = strategy.execute_exchange_plan(plan)
        
        # 详细报告结果
        total_exchanges = results["successful_exchanges"] + results["failed_exchanges"]
        self.log_widget.append(f"📈 兑换结果: {results['successful_exchanges']}/{total_exchanges} 成功")
        
        if results.get("gold_purchases", 0) > 0:
            self.log_widget.append(f"💰 金币购买: {results['gold_purchases']} 次")
        
        # 显示详细信息
        for detail in results.get("exchange_details", []):
            status = "✅" if detail["success"] else "❌"
            give_level = detail.get('give_level', '?')
            want_level = detail.get('want_level', '?')
            give_count = detail.get('give_count', detail.get('count', '?'))
            want_count = detail.get('want_count', 1)
            exchange_ratio = detail.get('exchange_ratio', '1:1')
            
            self.log_widget.append(f"  {status} {give_count}个{detail['give']}(L{give_level}) → {want_count}个{detail['want']}(L{want_level}) [{exchange_ratio}]: {detail['message']}")
        
        for purchase in results.get("purchase_details", []):
            status = "✅" if purchase["success"] else "❌"
            self.log_widget.append(f"  💰 {status} 购买 {purchase['ingredient']} x{purchase['count']}")
        
        if results["successful_exchanges"] > 0:
            self.log_widget.append("🎉 智能兑换完成！")
        else:
            self.log_widget.append("⚠️  兑换未成功，请检查账号状态或好友列表")
    
    def _show_materials(self, recipe: Dict[str, Any]):
        """显示食谱真实所需材料（需要vs拥有对比）"""
        recipe_name = recipe.get('name', '未知食谱')
        recipe_level = int(recipe.get('level', 1))
        street_name = recipe.get('street_name', '')
        
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号以查看库存对比")
            return
        
        # 从Excel获取真实食材需求
        materials = self.calculator.get_recipe_ingredients(recipe_name, recipe_level, street_name)
        
        materials_text = f"食谱: {recipe_name} (等级 {recipe_level})\n"
        materials_text += f"街道: {street_name}\n\n"
        
        if materials:
            # 获取当前库存
            current_inventory = {}
            try:
                account = self.account_manager.get_account(account_id)
                if account and account.key:
                    cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
                    cupboard_action = CupboardAction(key=account.key, cookie=cookie_dict)
                    strategy = SmartExchangeStrategy(None, cupboard_action, None)
                    current_inventory = strategy.get_current_inventory()
            except Exception as e:
                materials_text += f"⚠️ 无法获取当前库存: {str(e)}\n\n"
            
            materials_text += "学习/升级所需食材 (需要 vs 拥有):\n"
            materials_text += "=" * 50 + "\n"
            
            # 按食材类型分组显示
            basic_materials = []
            expensive_materials = []
            
            for ingredient, count in materials.items():
                ingredient_type = self.calculator.classify_ingredient(ingredient)
                current_count = current_inventory.get(ingredient, 0)
                
                # 状态标识
                if current_count >= count:
                    status = "✅"  # 充足
                elif current_count > 0:
                    status = "⚠️"  # 不足
                else:
                    status = "❌"  # 缺少
                
                ingredient_info = f"{status} {ingredient}: 需要{count}个, 拥有{current_count}个"
                if current_count < count:
                    shortage = count - current_count
                    ingredient_info += f" (缺少{shortage}个)"
                
                if ingredient_type in ['yu_chi', 'bao_yu', 'mystery']:
                    expensive_materials.append((ingredient_info, ingredient_type))
                else:
                    basic_materials.append(ingredient_info)
            
            # 显示基础食材
            if basic_materials:
                materials_text += "\n【基础食材】\n"
                for material_info in basic_materials:
                    materials_text += f"  {material_info}\n"
            
            # 显示特殊食材
            if expensive_materials:
                materials_text += "\n【特殊食材】\n"
                for material_info, ingredient_type in expensive_materials:
                    type_labels = {
                        'yu_chi': '🐟鱼翅',
                        'bao_yu': '🦪鲍鱼', 
                        'mystery': '✨神秘'
                    }
                    materials_text += f"  {material_info} ({type_labels.get(ingredient_type, '')})\n"
            
            # 添加库存统计
            if current_inventory:
                total_needed = sum(materials.values())
                total_owned = sum(current_inventory.get(ing, 0) for ing in materials.keys())
                materials_text += f"\n📊 食材统计:\n"
                materials_text += f"  总需求: {total_needed}个\n"
                materials_text += f"  总拥有: {total_owned}个\n"
                materials_text += f"  完成度: {total_owned/total_needed*100:.1f}%\n"
            
            # 添加提示信息
            if expensive_materials:
                materials_text += "\n💡 提示: 特殊食材价格昂贵，建议谨慎学习"
                
        else:
            materials_text += "❌ 未找到该食谱的食材配方数据"
        
        # 创建可滚动的对话框
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"食谱材料详情 - {recipe_name}")
        dialog.resize(550, 650)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(materials_text)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("SF Pro Text", 10))
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    @Slot()
    def _refresh_gold(self):
        """刷新当前金币数量"""
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效")
            return
        
        try:
            cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
            restaurant_actions = RestaurantActions(key=account.key, cookie=cookie_dict)
            
            status = restaurant_actions.get_status()
            if status and "gold" in status:
                self.current_gold = status["gold"]
                self.restaurant_star = status.get("star", 0)
                self.max_exchange_level = min(5, self.restaurant_star + 1)
                
                self.gold_label.setText(f"当前金币: {self.current_gold:,} | {self.restaurant_star}星餐厅")
                self._update_available_levels()  # 更新可用等级
                self._update_exchange_cost()  # 更新兑换成本显示
                self.log_widget.append(f"💰 状态刷新成功: 金币{self.current_gold:,}, {self.restaurant_star}星餐厅, 最高可兑换{self.max_exchange_level}级")
            else:
                self.gold_label.setText("当前金币: 获取失败")
                self.log_widget.append("❌ 获取餐厅状态失败")
                
        except Exception as e:
            self.gold_label.setText("当前金币: 获取失败")
            self.log_widget.append(f"❌ 刷新金币失败: {str(e)}")
    
    @Slot()
    def _update_exchange_cost(self):
        """更新兑换成本显示"""
        if not hasattr(self, 'level_combo') or not hasattr(self, 'quantity_spinbox'):
            return
            
        level = self.level_combo.currentData()
        quantity = self.quantity_spinbox.value()
        
        # 直接使用静态兑换率计算，不需要创建FoodActions实例
        cost = self._calculate_static_exchange_cost(level, quantity)
        
        # 更新显示
        self.cost_label.setText(f"预估成本: {cost:,} 金币")
        
        # 检查是否有足够金币和等级限制
        level = self.level_combo.currentData()
        
        # 检查等级限制
        if level > self.max_exchange_level:
            self.cost_label.setStyleSheet("QLabel { color: #FF4444; font-weight: bold; }")
            self.exchange_btn.setEnabled(False)
            self.exchange_btn.setText(f"需要{level-1}星以上餐厅")
            return
        
        # 检查金币是否充足
        if self.current_gold > 0:
            if cost > self.current_gold:
                self.cost_label.setStyleSheet("QLabel { color: #FF4444; font-weight: bold; }")
                self.exchange_btn.setEnabled(False)
                self.exchange_btn.setText("金币不足")
            else:
                self.cost_label.setStyleSheet("QLabel { color: #44FF44; font-weight: bold; }")
                self.exchange_btn.setEnabled(True)
                self.exchange_btn.setText("开始兑换")
        else:
            self.cost_label.setStyleSheet("QLabel { color: #FFA500; font-weight: bold; }")
            self.exchange_btn.setEnabled(True)
            self.exchange_btn.setText("开始兑换")
    
    @Slot()
    def _exchange_food_with_gold(self):
        """使用金币兑换食材"""
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效")
            return
        
        level = self.level_combo.currentData()
        quantity = self.quantity_spinbox.value()
        
        # 创建确认对话框
        cost = self._calculate_static_exchange_cost(level, quantity)
        msg = f"确认使用 {cost:,} 金币兑换 {quantity} 个 {level}级食材吗？"
        
        if self.current_gold > 0:
            remaining = self.current_gold - cost
            if remaining < 0:
                msg += f"\n\n⚠️ 金币不足！需要 {cost:,}，当前只有 {self.current_gold:,}"
            else:
                msg += f"\n\n兑换后剩余金币: {remaining:,}"
        
        reply = QMessageBox.question(self, "确认兑换", msg, 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 执行兑换
        try:
            cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
            food_actions = FoodActions(key=account.key, cookie=cookie_dict)
            
            self.log_widget.append(f"💰 开始兑换: {quantity}个{level}级食材，预估成本{cost:,}金币")
            
            success, result = food_actions.exchange_food_with_gold(level, quantity, self.max_exchange_level)
            
            if success:
                if isinstance(result, dict):
                    gained_item = result.get("gained_item", "未知食材")
                    gained_qty = result.get("gained_quantity", quantity)
                    gold_spent = result.get("gold_spent", cost)
                    
                    self.log_widget.append(f"✅ 兑换成功！获得: {gained_item} x{gained_qty}，花费: {gold_spent:,}金币")
                    
                    # 更新金币显示
                    if self.current_gold > 0:
                        self.current_gold -= gold_spent
                        self.gold_label.setText(f"当前金币: {self.current_gold:,}")
                        self._update_exchange_cost()
                else:
                    self.log_widget.append(f"✅ 兑换成功！{result}")
                    
                # 建议刷新金币
                self.log_widget.append("💡 建议点击'刷新金币'获取最新金币数量")
            else:
                self.log_widget.append(f"❌ 兑换失败: {result}")
                
        except Exception as e:
            self.log_widget.append(f"❌ 兑换异常: {str(e)}")
    
    def _update_available_levels(self):
        """根据餐厅星级更新可用的兑换等级"""
        if not hasattr(self, 'level_combo'):
            return
            
        # 更新等级选择的可用性和提示
        for i in range(self.level_combo.count()):
            level = self.level_combo.itemData(i)
            if level <= self.max_exchange_level:
                # 启用该等级
                model = self.level_combo.model()
                item = model.item(i)
                item.setEnabled(True)
                self.level_combo.setItemText(i, f"{level}级食材")
            else:
                # 禁用该等级
                model = self.level_combo.model()
                item = model.item(i)
                item.setEnabled(False)
                self.level_combo.setItemText(i, f"{level}级食材 (需要{level-1}星餐厅)")
        
        # 如果当前选择的等级不可用，切换到可用的最高等级
        current_level = self.level_combo.currentData()
        if current_level > self.max_exchange_level:
            for i in range(self.level_combo.count()):
                if self.level_combo.itemData(i) <= self.max_exchange_level:
                    self.level_combo.setCurrentIndex(i)
    
    def _calculate_static_exchange_cost(self, level: int, quantity: int) -> int:
        """
        静态计算兑换成本（不需要API调用）
        
        Args:
            level: 食材等级
            quantity: 数量
            
        Returns:
            总金币成本
        """
        # 静态兑换率（基于游戏经验）
        rates = {
            2: 2400,   # 2级食材每个2400金币
            3: 4800,   # 3级食材每个4800金币
            4: 9600,   # 4级食材每个9600金币
            5: 19200   # 5级食材每个19200金币
        }
        
        if level not in rates:
            return 0
        
        return rates[level] * quantity
    
    @Slot()
    def _update_target_food_list(self):
        """更新目标食材列表"""
        if not hasattr(self, 'friend_target_food_combo'):
            return
            
        level = self.friend_target_level_combo.currentData()
        self.friend_target_food_combo.clear()
        
        # 从foods.json中获取指定等级的食材
        try:
            foods_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "assets", "foods.json"
            )
            
            with open(foods_file_path, 'r', encoding='utf-8') as f:
                foods_data = json.load(f)
            
            # 筛选指定等级的食材
            level_foods = []
            for record in foods_data.get("RECORDS", []):
                # 处理level字段的类型转换（foods.json中level是字符串）
                record_level = record.get("level")
                try:
                    record_level = int(record_level) if record_level else 0
                except (ValueError, TypeError):
                    record_level = 0
                    
                if record_level == level:
                    level_foods.append({
                        "name": record.get("name", ""),
                        "code": record.get("code", ""),
                        "descript": record.get("descript", "")
                    })
            
            # 按名称排序并添加到下拉框
            level_foods.sort(key=lambda x: x["name"])
            for food in level_foods:
                display_name = f"{food['name']} ({food['descript']})" if food['descript'] else food['name']
                self.friend_target_food_combo.addItem(display_name, food)
                
        except Exception as e:
            print(f"[Error] 加载食材列表失败: {e}")
            self.friend_target_food_combo.addItem("加载失败", None)
    
    @Slot()
    def _smart_select_offer_foods(self):
        """智能选择可交换的食材"""
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account or not account.key:
            QMessageBox.warning(self, "提示", "账号Key无效")
            return
        
        self.log_widget.append("🔍 正在分析可交换食材...")
        
        try:
            # 获取当前库存
            cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
            cupboard_action = CupboardAction(key=account.key, cookie=cookie_dict)
            strategy = SmartExchangeStrategy(None, cupboard_action, None)
            self.current_inventory = strategy.get_current_inventory()
            
            if not self.current_inventory:
                QMessageBox.information(self, "提示", "无法获取库存数据")
                return
            
            # 计算选中食谱的需求
            current_street = self.street_combo.currentText()
            required_ingredients = self.calculator.calculate_requirements(
                self.selected_recipes, current_street, exclude_expensive=True
            ) if self.selected_recipes else {}
            
            # 获取目标食材等级（用于筛选同级给出食材）
            target_level = self.friend_target_level_combo.currentData()
            
            # 计算多余食材（可用于兑换）
            self.surplus_foods = {}
            same_level_surplus = {}  # 与目标食材同级的多余食材
            
            for food_name, current_count in self.current_inventory.items():
                required_count = required_ingredients.get(food_name, 0)
                surplus = current_count - required_count
                
                if surplus > 0:  # 有多余的食材可以用于兑换
                    self.surplus_foods[food_name] = surplus
                    
                    # 检查食材等级是否与目标等级匹配
                    food_level = self._get_food_level(food_name)
                    if food_level == target_level:
                        # 计算可兑换次数：2个相同食材换1个其他食材
                        exchangeable_pairs = surplus // 2
                        if exchangeable_pairs > 0:
                            same_level_surplus[food_name] = {
                                'surplus': surplus,
                                'exchangeable_pairs': exchangeable_pairs,
                                'level': food_level
                            }
            
            # 更新给出食材下拉框（显示可兑换的食材）
            self.friend_offer_food_combo.clear()
            if same_level_surplus:
                # 按可兑换次数排序，次数多的排在前面
                sorted_surplus = sorted(same_level_surplus.items(), key=lambda x: x[1]['exchangeable_pairs'], reverse=True)
                
                total_exchangeable = 0
                for food_name, food_data in sorted_surplus:
                    surplus_count = food_data['surplus']
                    exchangeable_pairs = food_data['exchangeable_pairs']
                    total_exchangeable += exchangeable_pairs
                    
                    display_text = f"{food_name} (多余{surplus_count}个, 可换{exchangeable_pairs}次)"
                    self.friend_offer_food_combo.addItem(display_text, {
                        "name": food_name,
                        "surplus": surplus_count,
                        "exchangeable_pairs": exchangeable_pairs,
                        "level": target_level
                    })
                
                self.log_widget.append(f"✅ 找到{len(same_level_surplus)}种{target_level}级可交换食材，总计可兑换{total_exchangeable}次")
                if len(same_level_surplus) < len(self.surplus_foods):
                    other_level_count = len(self.surplus_foods) - len(same_level_surplus)
                    self.log_widget.append(f"ℹ️ 另有{other_level_count}种其他等级食材不可用于{target_level}级兑换")
                
                # 启用智能兑换按钮
                self.smart_exchange_btn.setEnabled(True)
            else:
                self.friend_offer_food_combo.addItem(f"无{target_level}级多余食材可交换", None)
                if self.surplus_foods:
                    self.log_widget.append(f"⚠️ 没有{target_level}级多余食材，有{len(self.surplus_foods)}种其他等级多余食材")
                else:
                    self.log_widget.append("⚠️ 没有多余的食材可用于兑换")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析可交换食材失败: {str(e)}")
            self.log_widget.append(f"❌ 分析可交换食材失败: {str(e)}")
    
    def _get_food_level(self, food_name: str) -> int:
        """获取食材等级"""
        try:
            foods_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "assets", "foods.json"
            )
            
            with open(foods_file_path, 'r', encoding='utf-8') as f:
                foods_data = json.load(f)
            
            for record in foods_data.get("RECORDS", []):
                if record.get("name") == food_name:
                    level = record.get("level")
                    try:
                        return int(level) if level else 1
                    except (ValueError, TypeError):
                        return 1
            
            # 如果没找到，返回默认等级1
            return 1
            
        except Exception as e:
            print(f"[Error] 获取食材'{food_name}'等级失败: {e}")
            return 1
    
    def _get_food_code(self, food_name: str) -> str:
        """获取食材代码"""
        try:
            foods_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "assets", "foods.json"
            )
            
            with open(foods_file_path, 'r', encoding='utf-8') as f:
                foods_data = json.load(f)
            
            for record in foods_data.get("RECORDS", []):
                if record.get("name") == food_name:
                    return record.get("code", "")
            
            # 如果没找到，返回空字符串
            return ""
            
        except Exception as e:
            print(f"[Error] 获取食材'{food_name}'代码失败: {e}")
            return ""
    
    def _calculate_smart_exchange_plan(self, target_food_name: str, needed_count: int) -> List[Dict[str, Any]]:
        """
        计算智能兑换方案
        :param target_food_name: 目标食材名称
        :param needed_count: 需要的目标食材数量
        :return: 兑换计划列表
        """
        if not hasattr(self, 'surplus_foods') or not self.surplus_foods:
            return []
        
        target_level = self._get_food_level(target_food_name)
        exchange_plan = []
        remaining_needed = needed_count
        
        # 找到所有同级的多余食材
        available_foods = []
        for food_name, surplus_count in self.surplus_foods.items():
            food_level = self._get_food_level(food_name)
            if food_level == target_level and food_name != target_food_name:
                exchangeable_pairs = surplus_count // 2
                if exchangeable_pairs > 0:
                    available_foods.append({
                        'name': food_name,
                        'surplus': surplus_count,
                        'exchangeable_pairs': exchangeable_pairs
                    })
        
        # 按可兑换次数排序，优先使用数量多的
        available_foods.sort(key=lambda x: x['exchangeable_pairs'], reverse=True)
        
        # 计算兑换方案
        for food in available_foods:
            if remaining_needed <= 0:
                break
                
            food_name = food['name']
            available_pairs = food['exchangeable_pairs']
            
            # 计算这种食材能满足多少需求
            can_exchange = min(available_pairs, remaining_needed)
            
            if can_exchange > 0:
                exchange_plan.append({
                    'offer_food': food_name,
                    'offer_count': can_exchange * 2,  # 2个换1个
                    'target_food': target_food_name,
                    'target_count': can_exchange,
                    'level': target_level
                })
                remaining_needed -= can_exchange
        
        return exchange_plan
    
    @Slot()
    def _calculate_smart_exchange(self):
        """计算智能兑换方案"""
        # 检查是否已经进行了智能选择
        if not hasattr(self, 'surplus_foods') or not self.surplus_foods:
            QMessageBox.warning(self, "提示", "请先点击'智能选择可交换食材'进行分析")
            return
            
        target_food_data = self.friend_target_food_combo.currentData()
        if not target_food_data:
            QMessageBox.warning(self, "提示", "请先选择目标食材")
            return
        
        target_food_name = target_food_data.get("name")
        if not target_food_name:
            QMessageBox.warning(self, "提示", "目标食材数据无效")
            return
        
        # 获取需要的数量
        needed_count = self.friend_exchange_quantity.value()
        if needed_count <= 0:
            QMessageBox.warning(self, "提示", "请输入有效的兑换数量")
            return
        
        self.log_widget.append(f"🧮 计算智能兑换方案: 需要{needed_count}个{target_food_name}...")
        
        try:
            exchange_plan = self._calculate_smart_exchange_plan(target_food_name, needed_count)
            
            if not exchange_plan:
                self.log_widget.append(f"❌ 无法找到合适的兑换方案")
                return
            
            # 显示兑换方案
            total_can_get = sum(plan['target_count'] for plan in exchange_plan)
            self.log_widget.append(f"📋 智能兑换方案 (可获得{total_can_get}/{needed_count}个{target_food_name}):")
            
            for i, plan in enumerate(exchange_plan, 1):
                offer_food = plan['offer_food']
                offer_count = plan['offer_count']
                target_count = plan['target_count']
                self.log_widget.append(f"  {i}. 用{offer_count}个{offer_food} → 换{target_count}个{target_food_name}")
            
            if total_can_get < needed_count:
                shortage = needed_count - total_can_get
                self.log_widget.append(f"⚠️ 还缺少{shortage}个{target_food_name}，需要其他方式获取")
            else:
                self.log_widget.append(f"✅ 智能兑换方案可以完全满足需求！")
            
            # 保存兑换计划，供执行时使用
            self.current_exchange_plan = exchange_plan
                
            # 启用兑换按钮
            self.friend_exchange_btn.setEnabled(True)
            
        except Exception as e:
            self.log_widget.append(f"❌ 计算兑换方案失败: {str(e)}")
    
    @Slot()
    def _update_offer_food_by_level(self):
        """当目标等级变化时，更新可给出的食材选项"""
        if not hasattr(self, 'surplus_foods') or not self.surplus_foods:
            return
            
        target_level = self.friend_target_level_combo.currentData()
        if target_level is None:
            return
        
        # 重新筛选同级多余食材
        same_level_surplus = {}
        for food_name, surplus_count in self.surplus_foods.items():
            food_level = self._get_food_level(food_name)
            if food_level == target_level:
                # 计算可兑换次数：2个相同食材换1个其他食材
                exchangeable_pairs = surplus_count // 2
                if exchangeable_pairs > 0:
                    same_level_surplus[food_name] = {
                        'surplus': surplus_count,
                        'exchangeable_pairs': exchangeable_pairs,
                        'level': food_level
                    }
        
        # 更新给出食材下拉框
        self.friend_offer_food_combo.clear()
        if same_level_surplus:
            # 按可兑换次数排序
            sorted_surplus = sorted(same_level_surplus.items(), key=lambda x: x[1]['exchangeable_pairs'], reverse=True)
            
            total_exchangeable = 0
            for food_name, food_data in sorted_surplus:
                surplus_count = food_data['surplus']
                exchangeable_pairs = food_data['exchangeable_pairs']
                total_exchangeable += exchangeable_pairs
                
                display_text = f"{food_name} (多余{surplus_count}个, 可换{exchangeable_pairs}次)"
                self.friend_offer_food_combo.addItem(display_text, {
                    "name": food_name,
                    "surplus": surplus_count,
                    "exchangeable_pairs": exchangeable_pairs,
                    "level": target_level
                })
            
            self.log_widget.append(f"🔄 切换到{target_level}级：找到{len(same_level_surplus)}种可交换食材，总计{total_exchangeable}次")
            
            # 启用智能兑换按钮
            self.smart_exchange_btn.setEnabled(True)
        else:
            self.friend_offer_food_combo.addItem(f"无{target_level}级多余食材可交换", None)
            other_level_count = len(self.surplus_foods)
            if other_level_count > 0:
                self.log_widget.append(f"🔄 切换到{target_level}级：无可交换食材（有{other_level_count}种其他等级食材）")
            else:
                self.log_widget.append(f"🔄 切换到{target_level}级：无任何多余食材")
            
            # 禁用智能兑换按钮
            self.smart_exchange_btn.setEnabled(False)
    
    @Slot()

    @Slot()

    @Slot()

    def _execute_simple_exchange(self, friend_actions: FriendActions, target_food_code: str, 
                               offer_food_code: str, exchange_quantity: int, results: Dict[str, Any]) -> Dict[str, Any]:
        """执行简单兑换"""
        exchange_count = 0
        for friend in self.available_friends:
            if exchange_count >= exchange_quantity:
                break
                
            results["total_attempts"] += 1
            
            friend_name = friend.get("res_name", "未知好友")
            friend_id = friend.get("res_id")
            
            self.log_widget.append(f"🤝 第{exchange_count + 1}次兑换: 与 '{friend_name}' 兑换...")
            
            try:
                # 使用直接兑换方法 (非VIP)
                success, message = friend_actions.direct_friend_exchange(
                    friend_id,
                    target_food_code,  # 好友的食材代码
                    offer_food_code    # 我的食材代码
                )
                
                detail = {
                    "friend_name": friend_name,
                    "friend_id": friend_id,
                    "success": success,
                    "message": message,
                    "available_count": friend.get("num", 999)  # 手动模式假设数量
                }
                results["exchange_details"].append(detail)
                
                if success:
                    results["successful_exchanges"] += 1
                    exchange_count += 1
                    self.log_widget.append(f"  ✅ 与 '{friend_name}' 兑换成功: {message}")
                else:
                    results["failed_exchanges"] += 1
                    self.log_widget.append(f"  ❌ 与 '{friend_name}' 兑换失败: {message}")
                
                # 短暂延迟避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                results["failed_exchanges"] += 1
                self.log_widget.append(f"  ❌ 与 '{friend_name}' 兑换异常: {str(e)}")
        
        return results

    def _get_current_inventory_from_cupboard(self, cupboard_action) -> Dict[str, int]:
        """从橱柜获取当前真实库存"""
        from src.delicious_town_bot.constants import CupboardType
        
        inventory = {}
        
        # 获取所有等级的食材
        for cupboard_type in [CupboardType.LEVEL_1, CupboardType.LEVEL_2, CupboardType.LEVEL_3, 
                             CupboardType.LEVEL_4, CupboardType.LEVEL_5]:
            items = cupboard_action.get_items(cupboard_type)
            for item in items:
                food_name = item.get('food_name', '')
                food_count = int(item.get('num', 0))
                if food_name and food_count > 0:
                    inventory[food_name] = inventory.get(food_name, 0) + food_count
        
        return inventory

    def _calculate_surplus_foods(self, current_inventory: Dict[str, int]) -> Dict[str, int]:
        """计算多余食材（基于当前选中的食谱需求）"""
        # 获取当前选中食谱的总需求
        required_ingredients = self._get_total_required_ingredients()
        
        surplus_foods = {}
        for food_name, current_count in current_inventory.items():
            required_count = required_ingredients.get(food_name, 0)
            surplus = current_count - required_count
            
            if surplus > 0:  # 有多余的食材
                surplus_foods[food_name] = surplus
        
        return surplus_foods
    
    def _get_total_required_ingredients(self) -> Dict[str, int]:
        """获取当前选中食谱的总食材需求"""
        if not hasattr(self, 'selected_recipes') or not self.selected_recipes:
            return {}
        
        total_ingredients = {}
        
        for recipe in self.selected_recipes:
            # 解析食谱所需食材
            recipe_ingredients = self._get_recipe_ingredients(recipe)
            
            for ingredient, count in recipe_ingredients.items():
                total_ingredients[ingredient] = total_ingredients.get(ingredient, 0) + count
        
        return total_ingredients
    
    def _get_recipe_ingredients(self, recipe: Dict[str, Any]) -> Dict[str, int]:
        """获取单个食谱的食材需求"""
        try:
            # 尝试从Excel数据获取食材需求
            if hasattr(self, 'calculator') and self.calculator:
                recipe_name = recipe.get('name', '')
                recipe_level = int(recipe.get('level', 1))
                street_name = recipe.get('street_name', '')
                
                ingredients = self.calculator.get_recipe_ingredients(recipe_name, recipe_level, street_name)
                if ingredients:
                    return ingredients
            
            # 备用方案：模拟食材需求
            return self._simulate_recipe_ingredients(recipe)
            
        except Exception as e:
            # 如果获取失败，返回空字典
            print(f"[Debug] 获取食谱食材需求失败: {e}")
            return {}

    def _update_synthesis_strategy(self):
        """更新合成策略显示"""
        target_level = self.synthesis_target_level_combo.currentData()
        target_quantity = self.synthesis_target_quantity.value()
        
        if target_level:
            self.synthesis_strategy_label.setText(f"策略: 目标获得{target_quantity}个{target_level}级食材")
    
    def _calculate_synthesis_path(self):
        """计算智能合成路径"""
        self.log_widget.append("🧠 开始计算智能合成路径...")
        
        # 获取目标参数
        target_level = self.synthesis_target_level_combo.currentData()
        target_quantity = self.synthesis_target_quantity.value()
        
        if not target_level:
            self.log_widget.append("❌ 请选择目标等级")
            return
        
        # 获取当前选中的账号
        account_id = self.account_combo.currentData()
        if not account_id:
            self.log_widget.append("❌ 请选择账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account:
            self.log_widget.append("❌ 获取账号信息失败")
            return
        
        try:
            # 导入所需的Action类
            from src.delicious_town_bot.actions.cupboard import CupboardAction
            
            # 创建cupboard_action实例
            cupboard_action = CupboardAction(
                key=account.key,
                cookie={"PHPSESSID": account.cookie} if account.cookie else None
            )
            
            # 获取当前库存
            current_inventory = self._get_current_inventory_from_cupboard(cupboard_action)
            if not current_inventory:
                self.log_widget.append("❌ 无法获取库存信息")
                return
            
            # 计算多余食材
            surplus_foods = self._calculate_surplus_foods(current_inventory)
            
            # 计算智能合成路径
            synthesis_plan = self._calculate_recursive_synthesis_plan(
                target_level, target_quantity, surplus_foods, self.restaurant_star
            )
            
            if synthesis_plan['feasible']:
                # 显示合成路径
                path_text = "📋 智能合成路径:\n"
                
                for step in synthesis_plan['steps']:
                    if step['type'] == 'use_surplus':
                        # 处理两种不同的use_surplus格式
                        if 'source_food' in step and 'quantity' in step:
                            # _add_surplus_synthesis_steps生成的格式
                            path_text += f"• 使用多余: {step['quantity']}个{step['source_food']}({step['source_level']}级) → {step['result_quantity']}个{step['target_level']}级\n"
                        elif 'source_foods' in step and 'required_quantity' in step:
                            # _calculate_recursive_synthesis_plan生成的格式
                            foods_info = ', '.join([f'{name}({count}个)' for name, count in step['source_foods'].items()])
                            path_text += f"• 使用多余: {foods_info} → {step['result_quantity']}个{step['target_level']}级\n"
                        else:
                            # 兜底显示
                            path_text += f"• 使用多余食材({step.get('source_level', '?')}级) → {step.get('result_quantity', '?')}个{step.get('target_level', '?')}级\n"
                    elif step['type'] == 'buy_and_synthesize':
                        path_text += f"• 购买合成: {step['buy_quantity']}个{step['source_level']}级食材 → {step['result_quantity']}个{step['target_level']}级 (成本:{step.get('cost', 0)}金币)\n"
                    elif step['type'] == 'recursive_synthesis':
                        path_text += f"• 递归合成: {step['source_level']}级→{step['target_level']}级 (需要{step['required_quantity']}个{step['source_level']}级)\n"
                
                path_text += f"\n🎯 总结: 最终获得 {synthesis_plan['final_quantity']} 个 {target_level}级食材"
                path_text += f"\n💰 预估成本: {synthesis_plan['total_cost']} 金币"
                
                self.synthesis_path_text.setPlainText(path_text)
                self.execute_synthesis_btn.setEnabled(True)
                
                # 保存方案供执行使用
                self.current_synthesis_plan = synthesis_plan
                
                self.log_widget.append("✅ 智能合成路径计算完成")
                
            else:
                error_text = f"❌ 无法完成目标:\n{synthesis_plan['reason']}"
                self.synthesis_path_text.setPlainText(error_text)
                self.execute_synthesis_btn.setEnabled(False)
                self.log_widget.append(f"❌ {synthesis_plan['reason']}")
                
        except Exception as e:
            self.log_widget.append(f"❌ 计算合成路径失败: {e}")
    
    def _calculate_recursive_synthesis_plan(self, target_level: int, target_quantity: int, 
                                          surplus_foods: Dict[str, int], restaurant_star: int) -> Dict:
        """计算递归合成方案"""
        
        # 初始化结果
        plan = {
            'feasible': False,
            'steps': [],
            'final_quantity': 0,
            'total_cost': 0,
            'reason': ''
        }
        
        try:
            # 加载食材数据
            foods_path = os.path.join(os.path.dirname(__file__), "../../assets/foods.json")
            with open(foods_path, 'r', encoding='utf-8') as f:
                foods_json = json.load(f)
                # foods.json格式是 {"RECORDS": [...]}
                foods_data = foods_json.get("RECORDS", []) if isinstance(foods_json, dict) else foods_json
            
            # 按等级分组食材
            foods_by_level = {}
            for food in foods_data:
                level_str = food.get('level')
                try:
                    level = int(level_str) if level_str else 1
                except (ValueError, TypeError):
                    level = 1
                
                if level not in foods_by_level:
                    foods_by_level[level] = []
                foods_by_level[level].append(food)
            
            # 递归计算每个等级的合成方案
            total_cost = 0
            steps = []
            
            # 递归计算合成方案：从目标等级开始，逐级向下寻找原料
            remaining_needed = target_quantity
            
            for synthesis_target in range(target_level, 1, -1):  # 从目标等级向下到2级（1级不能被合成）
                if remaining_needed <= 0:
                    break
                
                # synthesis_target是我们要合成到的等级
                # source_level是合成原料的等级 (synthesis_target - 1)
                source_level = synthesis_target - 1
                
                # 检查是否有足够的source_level多余食材进行合成
                source_level_surplus = self._get_level_surplus(surplus_foods, source_level, foods_data)
                available_source = sum(source_level_surplus.values())
                needed_source = remaining_needed * 2  # 2:1合成比例
                
                if available_source >= needed_source:
                    # 多余食材足够，可以完全使用多余食材合成
                    steps.append({
                        'type': 'use_surplus',
                        'source_level': source_level,
                        'target_level': synthesis_target,
                        'source_foods': source_level_surplus,
                        'required_quantity': needed_source,
                        'result_quantity': remaining_needed
                    })
                    remaining_needed = 0  # 已满足需求
                    break
                elif available_source > 0:
                    # 部分使用多余食材
                    can_synthesize = available_source // 2
                    steps.append({
                        'type': 'use_surplus',
                        'source_level': source_level,
                        'target_level': synthesis_target,
                        'source_foods': source_level_surplus,
                        'required_quantity': available_source,
                        'result_quantity': can_synthesize
                    })
                    remaining_needed -= can_synthesize
                
                # 如果还有剩余需求，检查是否可以购买source_level食材
                if remaining_needed > 0:
                    max_buyable_level = min(restaurant_star + 1, 5)
                    
                    if source_level <= max_buyable_level:
                        # 可以购买source_level食材进行合成
                        still_needed_source = remaining_needed * 2
                        buy_cost = self._calculate_food_cost(source_level, still_needed_source)
                        
                        steps.append({
                            'type': 'buy_and_synthesize',
                            'source_level': source_level,
                            'target_level': synthesis_target,
                            'buy_quantity': still_needed_source,
                            'use_surplus': 0,
                            'result_quantity': remaining_needed,
                            'cost': buy_cost
                        })
                        total_cost += buy_cost
                        remaining_needed = 0  # 已满足需求
                        break
                    else:
                        # 不能购买source_level，需要继续向下一级寻找原料
                        # remaining_needed保持为当前synthesis_target的需求
                        # 下一轮循环会处理source_level作为synthesis_target的情况
                        remaining_needed = remaining_needed * 2  # 转换为下一级的需求量
                        continue
            
            if remaining_needed > 0:
                plan['reason'] = f"无法获得足够的{target_level-1}级食材进行合成（餐厅星级{restaurant_star}限制）"
            else:
                plan['feasible'] = True
                plan['steps'] = steps
                plan['final_quantity'] = target_quantity
                plan['total_cost'] = total_cost
                
        except Exception as e:
            plan['reason'] = f"计算错误: {e}"
        
        return plan
    
    def _get_level_surplus(self, surplus_foods: Dict[str, int], level: int, foods_data: List) -> Dict[str, int]:
        """获取指定等级的多余食材"""
        level_surplus = {}
        
        for food_name, surplus_count in surplus_foods.items():
            # 查找食材等级
            for food in foods_data:
                if food.get('name') == food_name:
                    food_level_str = food.get('level')
                    try:
                        food_level = int(food_level_str) if food_level_str else 1
                    except (ValueError, TypeError):
                        food_level = 1
                    
                    if food_level == level and surplus_count >= 2:  # 至少2个才能合成
                        level_surplus[food_name] = surplus_count
                    break
        
        return level_surplus
    
    def _add_surplus_synthesis_steps(self, steps: List, level_surplus: Dict[str, int], 
                                   needed_quantity: int, source_level: int, target_level: int):
        """添加多余食材合成步骤"""
        remaining = needed_quantity
        
        # 按多余数量排序，优先使用数量多的
        sorted_surplus = sorted(level_surplus.items(), key=lambda x: x[1], reverse=True)
        
        for food_name, surplus_count in sorted_surplus:
            if remaining <= 0:
                break
            
            can_synthesize = surplus_count // 2
            use_count = min(can_synthesize, remaining)
            
            if use_count > 0:
                steps.append({
                    'type': 'use_surplus',
                    'source_food': food_name,
                    'source_level': source_level,
                    'target_level': target_level,
                    'quantity': use_count * 2,  # 实际使用的食材数量
                    'result_quantity': use_count
                })
                remaining -= use_count
    
    def _calculate_food_cost(self, level: int, quantity: int) -> int:
        """计算购买食材的成本"""
        # 根据等级计算单个食材成本（这个需要根据实际游戏数据调整）
        base_costs = {1: 100, 2: 500, 3: 2000, 4: 8000, 5: 32000}
        unit_cost = base_costs.get(level, 1000)
        return unit_cost * quantity
    
    def _execute_smart_synthesis(self):
        """执行智能合成"""
        if not hasattr(self, 'current_synthesis_plan') or not self.current_synthesis_plan['feasible']:
            self.log_widget.append("❌ 请先计算合成路径")
            return
        
        self.log_widget.append("🚀 开始执行智能合成...")
        
        # 获取当前选中的账号
        account_id = self.account_combo.currentData()
        if not account_id:
            self.log_widget.append("❌ 请选择账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account:
            self.log_widget.append("❌ 获取账号信息失败")
            return
        
        try:
            # 导入所需的Action类
            from src.delicious_town_bot.actions.cupboard import CupboardAction
            from src.delicious_town_bot.actions.food import FoodActions
            
            # 创建action实例
            cupboard_action = CupboardAction(
                key=account.key,
                cookie={"PHPSESSID": account.cookie} if account.cookie else None
            )
            
            food_action = FoodActions(
                key=account.key,
                cookie={"PHPSESSID": account.cookie} if account.cookie else None
            )
            
            plan = self.current_synthesis_plan
            
            # 按步骤执行
            for i, step in enumerate(plan['steps']):
                self.log_widget.append(f"📋 执行步骤 {i+1}/{len(plan['steps'])}: {step['type']}")
                
                if step['type'] == 'use_surplus':
                    # 使用多余食材合成
                    self._execute_surplus_synthesis(cupboard_action, step)
                
                elif step['type'] == 'buy_and_synthesize':
                    # 购买并合成
                    self._execute_buy_and_synthesis(food_action, cupboard_action, step)
            
            self.log_widget.append(f"🎉 智能合成完成! 应该获得 {plan['final_quantity']} 个 {self.synthesis_target_level_combo.currentData()}级食材")
            self.log_widget.append("💡 建议重新查询库存确认结果")
            
        except Exception as e:
            self.log_widget.append(f"❌ 执行智能合成失败: {e}")
    
    def _execute_surplus_synthesis(self, cupboard_action, step):
        """执行多余食材合成"""
        source_food = step['source_food']
        quantity_to_use = step['quantity']
        result_quantity = step['result_quantity']
        
        self.log_widget.append(f"  🔄 使用{quantity_to_use}个{source_food}合成{result_quantity}个高级食材")
        
        # 获取食材代码
        food_code = self._get_food_code(source_food)
        if not food_code:
            self.log_widget.append(f"  ❌ 无法找到{source_food}的代码")
            return
        
        # 执行合成
        for i in range(result_quantity):
            try:
                success, message = cupboard_action.synthesize_food(food_code, 2)
                if success:
                    self.log_widget.append(f"    ✅ 第{i+1}次合成成功: {message}")
                else:
                    self.log_widget.append(f"    ❌ 第{i+1}次合成失败: {message}")
            except Exception as e:
                self.log_widget.append(f"    ❌ 第{i+1}次合成异常: {e}")
    
    def _execute_buy_and_synthesis(self, food_action, cupboard_action, step):
        """执行购买并合成"""
        source_level = step['source_level']
        buy_quantity = step['buy_quantity']
        result_quantity = step['result_quantity']
        
        self.log_widget.append(f"  💰 购买{buy_quantity}个{source_level}级食材进行合成")
        
        # 先购买食材
        try:
            success, message = cupboard_action.buy_random_food(source_level, buy_quantity)
            if success:
                self.log_widget.append(f"    ✅ 购买成功: {message}")
                
                # TODO: 这里需要获取具体购买到的食材，然后进行合成
                # 暂时用通用合成逻辑
                self.log_widget.append(f"    🔄 开始合成{result_quantity}个高级食材...")
                
            else:
                self.log_widget.append(f"    ❌ 购买失败: {message}")
                
        except Exception as e:
            self.log_widget.append(f"    ❌ 购买异常: {e}")

    def _refresh_market_foods(self):
        """刷新菜场食材列表"""
        self.log_widget.append("🏪 正在刷新菜场食材列表...")
        
        # 获取当前选中的账号
        account_id = self.account_combo.currentData()
        if not account_id:
            self.log_widget.append("❌ 请选择账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account:
            self.log_widget.append("❌ 获取账号信息失败")
            return
        
        try:
            # 导入并创建FoodActions实例
            from src.delicious_town_bot.actions.food import FoodActions
            
            food_action = FoodActions(
                key=account.key,
                cookie={"PHPSESSID": account.cookie} if account.cookie else None
            )
            
            # 获取菜场食材列表
            food_list = food_action.get_food_list()
            
            if food_list:
                self.log_widget.append(f"✅ 获取到{len(food_list)}种菜场食材")
                
                # 更新UI显示
                self.market_food_combo.clear()
                foods_display = []
                
                for food in food_list:
                    food_name = food.get('name', '未知食材')
                    food_code = food.get('code', '')
                    # API返回的是gold字段而不是price字段
                    food_price = food.get('gold', food.get('price', 0))
                    if isinstance(food_price, str):
                        food_price = int(food_price) if food_price.isdigit() else 0
                    
                    # 添加到下拉框
                    self.market_food_combo.addItem(
                        f"{food_name} ({food_price}金币/个)", 
                        {'name': food_name, 'code': food_code, 'price': int(food_price)}
                    )
                    
                    foods_display.append(f"{food_name}({food_price}金币/个)")
                
                # 更新显示文本
                display_text = "📋 当前菜场售卖:\n" + " | ".join(foods_display)
                self.market_foods_text.setPlainText(display_text)
                
                # 启用购买按钮
                self.buy_market_food_btn.setEnabled(True)
                
                # 更新成本显示
                self._update_market_cost()
                
            else:
                self.log_widget.append("❌ 未获取到菜场食材列表")
                self.market_foods_text.setPlainText("❌ 未获取到菜场食材")
                self.buy_market_food_btn.setEnabled(False)
                
        except Exception as e:
            self.log_widget.append(f"❌ 刷新菜场失败: {e}")
            self.market_foods_text.setPlainText(f"❌ 刷新失败: {e}")
    
    def _update_market_cost(self):
        """更新菜场购买成本显示"""
        current_food = self.market_food_combo.currentData()
        if not current_food:
            self.market_cost_label.setText("预估成本: 请先刷新菜场")
            return
        
        quantity = self.market_quantity_spinbox.value()
        price_per_item = current_food.get('price', 0)
        total_cost = price_per_item * quantity
        
        food_name = current_food.get('name', '')
        self.market_cost_label.setText(f"预估成本: {total_cost}金币 ({food_name} {price_per_item}金币×{quantity}个)")
    
    def _buy_market_food(self):
        """执行菜场购买"""
        self.log_widget.append("💰 开始菜场精准购买...")
        
        # 获取购买参数
        current_food = self.market_food_combo.currentData()
        if not current_food:
            self.log_widget.append("❌ 请先刷新菜场并选择食材")
            return
        
        food_name = current_food.get('name')
        quantity = self.market_quantity_spinbox.value()
        
        # 获取当前选中的账号
        account_id = self.account_combo.currentData()
        if not account_id:
            self.log_widget.append("❌ 请选择账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account:
            self.log_widget.append("❌ 获取账号信息失败")
            return
        
        try:
            # 导入并创建FoodActions实例
            from src.delicious_town_bot.actions.food import FoodActions
            
            food_action = FoodActions(
                key=account.key,
                cookie={"PHPSESSID": account.cookie} if account.cookie else None
            )
            
            # 执行购买
            self.log_widget.append(f"🛒 购买{quantity}个{food_name}...")
            
            success, result = food_action.buy_food_by_name(food_name, quantity)
            
            if success:
                # 解析购买结果
                if isinstance(result, dict):
                    gained_quantity = result.get('quantity_added', quantity)
                    spent_gold = result.get('gold_spent', 'N/A')
                    gained_item = result.get('item_name', food_name)
                    
                    self.log_widget.append(f"✅ 购买成功!")
                    self.log_widget.append(f"  📦 获得: {gained_item} x{gained_quantity}")
                    self.log_widget.append(f"  💰 花费: {spent_gold}金币")
                else:
                    self.log_widget.append(f"✅ 购买成功: {result}")
                
                # 建议刷新库存
                self.log_widget.append("💡 建议重新刷新菜场或查询库存")
                
            else:
                self.log_widget.append(f"❌ 购买失败: {result}")
                
        except Exception as e:
            self.log_widget.append(f"❌ 菜场购买过程失败: {e}")
    
    def _start_simple_synthesis(self):
        """开始简单合成"""
        self.log_widget.append("⚗️ 开始简单食材合成...")
        
        # 获取合成参数
        target_level = self.synthesis_level_combo.currentData()
        target_quantity = self.synthesis_quantity_spinbox.value()
        
        # 获取当前选中的账号
        account_id = self.account_combo.currentData()
        if not account_id:
            self.log_widget.append("❌ 请选择账号")
            return
        
        account = self.account_manager.get_account(account_id)
        if not account:
            self.log_widget.append("❌ 获取账号信息失败")
            return
        
        try:
            # 导入并创建CupboardAction实例
            from src.delicious_town_bot.actions.cupboard import CupboardAction
            
            cupboard_action = CupboardAction(
                key=account.key,
                cookie={"PHPSESSID": account.cookie} if account.cookie else None
            )
            
            # 获取当前库存
            self.log_widget.append("📦 正在获取当前库存...")
            current_inventory = self._get_current_inventory_from_cupboard(cupboard_action)
            
            if not current_inventory:
                self.log_widget.append("❌ 无法获取当前库存，取消合成")
                return
            
            # 计算多余食材（减去食谱需求）
            surplus_foods = self._calculate_surplus_foods(current_inventory)
            self.log_widget.append(f"📋 计算出{len(surplus_foods)}种多余食材")
            
            # 查找合成所需的源等级食材
            source_level = target_level - 1
            if source_level < 1:
                self.log_widget.append("❌ 无法合成1级食材")
                return
            
            # 寻找可用于合成的多余食材
            available_materials = {}
            total_available = 0
            
            for food_name, count in surplus_foods.items():
                food_level = self._get_food_level(food_name)
                if food_level == source_level and count >= 2:
                    available_pairs = count // 2  # 每2个可以合成1个
                    available_materials[food_name] = {
                        'count': count,
                        'pairs': available_pairs
                    }
                    total_available += available_pairs
            
            if not available_materials:
                self.log_widget.append(f"❌ 没有足够的{source_level}级多余食材进行合成")
                self.log_widget.append(f"💡 合成{target_level}级食材需要{source_level}级食材，且每种至少2个")
                return
            
            # 显示可用材料
            self.log_widget.append(f"✅ 找到{len(available_materials)}种{source_level}级多余食材:")
            for food_name, info in available_materials.items():
                self.log_widget.append(f"  • {food_name}: {info['count']}个 → 可合成{info['pairs']}个{target_level}级")
            
            self.log_widget.append(f"📊 总计可合成: {total_available}个{target_level}级食材")
            
            # 检查是否足够
            if total_available < target_quantity:
                self.log_widget.append(f"⚠️ 多余食材只能合成{total_available}个，但需要{target_quantity}个")
                self.log_widget.append("💡 将使用所有可用材料进行合成")
                actual_quantity = total_available
            else:
                actual_quantity = target_quantity
            
            # 开始合成
            self.log_widget.append(f"🔄 开始合成{actual_quantity}个{target_level}级食材...")
            
            synthesized_count = 0
            remaining_needed = actual_quantity
            
            for food_name, info in available_materials.items():
                if remaining_needed <= 0:
                    break
                
                available_pairs = info['pairs']
                pairs_to_use = min(available_pairs, remaining_needed)
                
                if pairs_to_use > 0:
                    self.log_widget.append(f"  🔄 使用{food_name}合成{pairs_to_use}个{target_level}级食材...")
                    
                    # 获取食材代码
                    food_code = self._get_food_code(food_name)
                    
                    # 执行合成（每次合成2个源食材→1个目标食材）
                    for i in range(pairs_to_use):
                        try:
                            success, message = cupboard_action.synthesize_food(food_code, 2)
                            if success:
                                synthesized_count += 1
                                remaining_needed -= 1
                                self.log_widget.append(f"    ✅ 第{i+1}次合成成功")
                            else:
                                self.log_widget.append(f"    ❌ 第{i+1}次合成失败: {message}")
                                # 如果连续失败，可能食材不足，停止使用这种食材
                                break
                        except Exception as e:
                            self.log_widget.append(f"    ❌ 第{i+1}次合成异常: {e}")
                            break
            
            # 总结结果
            if synthesized_count > 0:
                self.log_widget.append(f"🎉 合成完成! 成功合成{synthesized_count}个{target_level}级食材")
                if synthesized_count < target_quantity:
                    self.log_widget.append(f"⚠️ 目标是{target_quantity}个，实际合成{synthesized_count}个")
            else:
                self.log_widget.append("❌ 合成失败，没有成功合成任何食材")
            
            self.log_widget.append("💡 建议重新查询库存确认结果")
            
        except Exception as e:
            self.log_widget.append(f"❌ 合成过程失败: {e}")
            import traceback
            traceback.print_exc()

class FriendSelectionDialog(QDialog):
    """好友选择对话框"""
    
    def __init__(self, friends: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.friends = friends
        self.selected_friends = []
        self.setupUI()
    
    def setupUI(self):
        self.setWindowTitle("选择好友")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel(f"请选择要进行兑换的好友 (共{len(self.friends)}个好友)")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 好友列表
        self.friend_table = QTableWidget()
        self.friend_table.setColumnCount(3)
        self.friend_table.setHorizontalHeaderLabels(["选择", "好友名称", "ID"])
        
        # 设置表格样式
        header = self.friend_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        
        self.friend_table.setColumnWidth(0, 50)
        self.friend_table.setColumnWidth(2, 80)
        self.friend_table.setAlternatingRowColors(True)
        self.friend_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # 填充好友数据
        self.friend_table.setRowCount(len(self.friends))
        self.checkboxes = []
        
        for row, friend in enumerate(self.friends):
            # 选择复选框
            checkbox = QCheckBox()
            self.checkboxes.append(checkbox)
            self.friend_table.setCellWidget(row, 0, checkbox)
            
            # 好友名称
            name_item = QTableWidgetItem(friend.get("name", "未知好友"))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.friend_table.setItem(row, 1, name_item)
            
            # 好友ID
            id_item = QTableWidgetItem(str(friend.get("id", "")))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.friend_table.setItem(row, 2, id_item)
        
        layout.addWidget(self.friend_table)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        # 全选/全不选按钮
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("全不选")
        select_none_btn.clicked.connect(self._select_none)
        button_layout.addWidget(select_none_btn)
        
        # 快速选择按钮
        select_top_btn = QPushButton("选择前10个")
        select_top_btn.clicked.connect(lambda: self._select_top(10))
        button_layout.addWidget(select_top_btn)
        
        button_layout.addStretch()
        
        # 确认/取消按钮
        ok_btn = QPushButton("确认")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 状态显示
        self.status_label = QLabel("请选择好友")
        layout.addWidget(self.status_label)
    
    def _select_all(self):
        """全选"""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
        self._update_status()
    
    def _select_none(self):
        """全不选"""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
        self._update_status()
    
    def _select_top(self, count: int):
        """选择前N个"""
        for i, checkbox in enumerate(self.checkboxes):
            checkbox.setChecked(i < count)
        self._update_status()
    
    def _update_status(self):
        """更新状态显示"""
        selected_count = sum(1 for cb in self.checkboxes if cb.isChecked())
        self.status_label.setText(f"已选择 {selected_count} 个好友")
    
    def get_selected_friends(self) -> List[Dict[str, Any]]:
        """获取选中的好友"""
        selected = []
        for i, checkbox in enumerate(self.checkboxes):
            if checkbox.isChecked():
                selected.append(self.friends[i])
        return selected
    
    def accept(self):
        """确认选择"""
        selected = self.get_selected_friends()
        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个好友")
            return
        
        super().accept()


"""
赛厨排行榜模块 (Match Rankings)
处理赛厨相关操作，包括排行榜查询等。
"""

import os
from typing import Dict, List, Optional, Any

from .base_action import BaseAction
from .user_card import UserCardAction
from ..constants import MatchRankingType


class MatchAction(BaseAction):
    """处理赛厨排行榜相关操作的类"""

    def __init__(self, key: str, cookie: Dict[str, str]):
        base_url = f"{os.getenv('BASE_URL', 'http://117.72.123.195')}/index.php?g=Res&m=Match"
        super().__init__(key=key, base_url=base_url, cookie=cookie)
        # 创建用户卡片操作实例
        self.user_card_action = UserCardAction(key=key, cookie=cookie)

    def get_ranking_list(self, ranking_type: MatchRankingType = MatchRankingType.BEGINNER, 
                        page: int = 1) -> Dict[str, Any]:
        """
        获取赛厨排行榜列表
        
        :param ranking_type: 排行榜区域类型 (1=低级区, 2=初级区, 3=中级区, 4=高级区, 5=顶级区, 6=巅峰区)
        :param page: 页码，每页100个位置
        :return: 包含排行榜数据的字典
        """
        data = {
            "type": ranking_type.value,
            "page": page
        }
        
        response = self.post("a=getList", data)
        return response
    
    def get_all_rankings(self, ranking_type: MatchRankingType = MatchRankingType.BEGINNER) -> List[Dict[str, Any]]:
        """
        获取指定区域的完整排行榜（100个位置）
        
        :param ranking_type: 排行榜区域类型
        :return: 排行榜条目列表
        """
        response = self.get_ranking_list(ranking_type, page=1)
        if response.get("status"):
            return response.get("data", {}).get("list", [])
        return []
    
    def get_all_rankings_with_empty(self, ranking_type: MatchRankingType = MatchRankingType.BEGINNER) -> List[Dict[str, Any]]:
        """
        获取指定区域的完整排行榜，包括空位信息
        
        :param ranking_type: 排行榜区域类型
        :return: 完整排行榜列表（包括空位）
        """
        all_rankings = self.get_all_rankings(ranking_type)
        formatted_rankings = []
        
        for restaurant in all_rankings:
            ranking_num = int(restaurant.get("ranking_num", 0))
            name = restaurant.get("name")
            level = restaurant.get("level")
            res_id = restaurant.get("res_id", "0")
            
            if name and level:
                # 有餐厅占位
                formatted_rankings.append({
                    "ranking_num": ranking_num,
                    "name": name,
                    "level": int(level),
                    "res_id": res_id,
                    "is_empty": False
                })
            else:
                # 空位
                formatted_rankings.append({
                    "ranking_num": ranking_num,
                    "name": "空位",
                    "level": None,
                    "res_id": "0",
                    "is_empty": True
                })
        
        return formatted_rankings
    
    def get_active_restaurants(self, ranking_type: MatchRankingType = MatchRankingType.BEGINNER) -> List[Dict[str, Any]]:
        """
        获取指定区域的活跃餐厅（有名称和等级的餐厅）
        
        :param ranking_type: 排行榜区域类型
        :return: 活跃餐厅列表
        """
        all_rankings = self.get_all_rankings_with_empty(ranking_type)
        active_restaurants = []
        
        for restaurant in all_rankings:
            if not restaurant["is_empty"]:
                active_restaurants.append({
                    "ranking_num": restaurant["ranking_num"],
                    "name": restaurant["name"],
                    "level": restaurant["level"],
                    "res_id": restaurant["res_id"]
                })
        
        return active_restaurants
    
    def get_ranking_type_name(self, ranking_type: MatchRankingType) -> str:
        """获取排行榜区域类型的中文名称"""
        type_names = {
            MatchRankingType.NOVICE: "低级区",
            MatchRankingType.BEGINNER: "初级区", 
            MatchRankingType.INTERMEDIATE: "中级区",
            MatchRankingType.ADVANCED: "高级区",
            MatchRankingType.EXPERT: "顶级区",
            MatchRankingType.PEAK: "巅峰区"
        }
        return type_names.get(ranking_type, "未知区域")
    
    def find_restaurant_by_name(self, name: str, ranking_type: MatchRankingType = MatchRankingType.BEGINNER) -> Optional[Dict[str, Any]]:
        """
        根据餐厅名称查找餐厅信息
        
        :param name: 餐厅名称
        :param ranking_type: 排行榜区域类型
        :return: 餐厅信息字典，如果未找到则返回None
        """
        active_restaurants = self.get_active_restaurants(ranking_type)
        
        for restaurant in active_restaurants:
            if restaurant.get("name") == name:
                return restaurant
        
        return None
    
    def get_top_restaurants(self, ranking_type: MatchRankingType = MatchRankingType.BEGINNER, 
                          top_n: int = 10) -> List[Dict[str, Any]]:
        """
        获取排行榜前N名餐厅
        
        :param ranking_type: 排行榜区域类型
        :param top_n: 获取前几名，默认10名
        :return: 前N名餐厅列表
        """
        active_restaurants = self.get_active_restaurants(ranking_type)
        
        # 按排名排序并取前N名
        sorted_restaurants = sorted(active_restaurants, key=lambda x: int(x["ranking_num"]))
        return sorted_restaurants[:top_n]
    
    def get_restaurant_power_data(self, res_id: str) -> Optional[Dict[str, Any]]:
        """
        获取餐厅的厨力数据
        
        :param res_id: 餐厅ID
        :return: 餐厅厨力数据，如果失败返回None
        """
        try:
            user_card_data = self.user_card_action.get_user_card(res_id)
            if user_card_data.get("success"):
                basic_info = user_card_data.get("restaurant_info", {})
                cooking_power = user_card_data.get("cooking_power", {})
                equipment = user_card_data.get("equipment", [])
                speciality = user_card_data.get("speciality", {})
                
                # 计算真实厨力
                power_summary = self.user_card_action.get_cooking_power_summary(res_id)
                real_power = 0
                if power_summary.get("success"):
                    # 真实厨力计算公式
                    attrs = power_summary.get("attributes", {})
                    weights = {
                        "fire": 1.71,      # 火候
                        "cooking": 1.44,   # 厨艺  
                        "sword": 1.41,     # 刀工
                        "season": 1.5,     # 调味
                        "originality": 2.25 # 创意
                    }
                    
                    for attr_key, weight in weights.items():
                        if attr_key in attrs:
                            total_value = attrs[attr_key].get("total", 0)
                            real_power += total_value * weight
                    
                    # 加上特色菜营养值
                    if speciality:
                        nutritive = speciality.get("nutritive", 0)
                        real_power += nutritive * 1.8
                
                return {
                    "restaurant_name": basic_info.get("name", "未知餐厅"),
                    "restaurant_level": basic_info.get("level", 0),
                    "restaurant_star": basic_info.get("star", 0),
                    "street_name": basic_info.get("street_name", "未知街道"),
                    "cook_type": basic_info.get("cook_type", "未知菜系"),
                    "total_power": cooking_power.get("total_with_equip", 0),
                    "base_power": cooking_power.get("total_base", 0),
                    "equipment_bonus": cooking_power.get("total_with_equip", 0) - cooking_power.get("total_base", 0),
                    "real_power": round(real_power, 2),
                    "attributes": {
                        "fire": cooking_power.get("fire", 0) + cooking_power.get("fire_add", 0),
                        "cooking": cooking_power.get("cooking", 0) + cooking_power.get("cooking_add", 0),
                        "sword": cooking_power.get("sword", 0) + cooking_power.get("sword_add", 0),
                        "season": cooking_power.get("season", 0) + cooking_power.get("season_add", 0),
                        "originality": cooking_power.get("originality", 0) + cooking_power.get("originality_add", 0),
                        "luck": cooking_power.get("luck", 0) + cooking_power.get("luck_add", 0)
                    },
                    "equipment_count": len(equipment),
                    "speciality": {
                        "name": speciality.get("name", "无招牌菜"),
                        "nutritive": speciality.get("nutritive", 0),
                        "quality": speciality.get("quality", 0)
                    },
                    "vip_level": basic_info.get("vip_level", 0),
                    "prestige": basic_info.get("prestige", 0),
                    "gold": basic_info.get("gold", 0),
                    "exp": basic_info.get("exp", 0)
                }
        except Exception as e:
            print(f"获取餐厅厨力数据失败: {str(e)}")
            
        return None
    
    def challenge_match(self, ranking_type: MatchRankingType, ranking_num: int) -> Dict[str, Any]:
        """
        挑战排行榜指定排名
        
        :param ranking_type: 排行榜区域类型
        :param ranking_num: 要挑战的排名位置
        :return: 挑战结果字典
        """
        data = {
            "type": ranking_type.value,
            "ranking_num": ranking_num
        }
        
        try:
            response = self.post("a=attackMatch", data)
            if response.get("status"):
                return {
                    "success": True,
                    "message": response.get("msg", ""),
                    "data": response.get("data", []),
                    "raw_response": response
                }
            else:
                return {
                    "success": False,
                    "message": response.get("msg", "挑战失败"),
                    "raw_response": response
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"挑战请求失败: {str(e)}"
            }
    
    def occupy_empty_slot(self, ranking_type: MatchRankingType, ranking_num: int) -> Dict[str, Any]:
        """
        占领空位排名
        
        :param ranking_type: 排行榜区域类型
        :param ranking_num: 要占领的空位排名
        :return: 占领结果字典
        """
        data = {
            "type": ranking_type.value,
            "ranking_num": ranking_num
        }
        
        try:
            response = self.post("a=attackMatch", data)
            if response.get("status"):
                return {
                    "success": True,
                    "message": response.get("msg", ""),
                    "data": response.get("data", []),
                    "raw_response": response,
                    "action_type": "occupy"  # 标识这是占领行为
                }
            else:
                return {
                    "success": False,
                    "message": response.get("msg", "占领失败"),
                    "raw_response": response,
                    "action_type": "occupy"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"占领请求失败: {str(e)}",
                "action_type": "occupy"
            }
    
    def parse_challenge_result(self, challenge_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析挑战结果
        
        :param challenge_response: 挑战响应数据
        :return: 解析后的结果数据
        """
        if not challenge_response.get("success"):
            return challenge_response
        
        message = challenge_response.get("message", "")
        action_type = challenge_response.get("action_type", "challenge")
        
        result = {
            "success": True,
            "action_type": action_type,
            "opponent_name": "",
            "opponent_level": 0,
            "vitality_cost": 0,
            "victory": False,
            "prestige_change": 0,
            "total_score": {"my": 0, "opponent": 0},
            "evaluations": [],
            "occupied_ranking": 0  # 占领的排名位置
        }
        
        try:
            import re
            
            # 检查是否是占领空位
            if action_type == "occupy" or "你占领了排名第" in message:
                result["action_type"] = "occupy"
                result["victory"] = True  # 占领总是成功的
                
                # 解析占领的排名 "你占领了排名第98的位置"
                occupy_match = re.search(r'你占领了排名第(\d+)的位置', message)
                if occupy_match:
                    result["occupied_ranking"] = int(occupy_match.group(1))
                
                # 解析体力消耗
                vitality_match = re.search(r'你的体力-(\d+)', message)
                if vitality_match:
                    result["vitality_cost"] = int(vitality_match.group(1))
                    
            else:
                # 挑战其他餐厅的解析逻辑
                result["action_type"] = "challenge"
                
                # 解析对手信息 "你挑战了 [小笨餐厅(45级)]"
                opponent_match = re.search(r'你挑战了 \[([^(]+)\((\d+)级\)\]', message)
                if opponent_match:
                    result["opponent_name"] = opponent_match.group(1)
                    result["opponent_level"] = int(opponent_match.group(2))
                
                # 解析体力消耗 "你的体力-10"
                vitality_match = re.search(r'你的体力-(\d+)', message)
                if vitality_match:
                    result["vitality_cost"] = int(vitality_match.group(1))
                
                # 解析胜负 "你赢了!" 或其他
                result["victory"] = "你赢了!" in message
                
                # 解析声望变化 "你的声望+10"
                prestige_match = re.search(r'你的声望([+\-]\d+)', message)
                if prestige_match:
                    prestige_str = prestige_match.group(1)
                    result["prestige_change"] = int(prestige_str)
                
                # 解析总比分 "总比分:808.1:426.7"
                score_match = re.search(r'总比分:([0-9.]+):([0-9.]+)', message)
                if score_match:
                    result["total_score"]["my"] = float(score_match.group(1))
                    result["total_score"]["opponent"] = float(score_match.group(2))
                
                # 解析评价详情
                evaluation_patterns = [
                    r'(\w+)评价(\w+)\s+([0-9.]+):([0-9.]+)\s+\[([^\]]+)\]'
                ]
                
                for pattern in evaluation_patterns:
                    matches = re.findall(pattern, message)
                    for match in matches:
                        judge, category, my_score, opp_score, evaluation = match
                        result["evaluations"].append({
                            "judge": judge,
                            "category": category,
                            "my_score": float(my_score),
                            "opponent_score": float(opp_score),
                            "evaluation": evaluation
                        })
            
            result["raw_message"] = message
            
        except Exception as e:
            result["parse_error"] = f"解析结果失败: {str(e)}"
            result["raw_message"] = message
        
        return result
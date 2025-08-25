"""
特色菜管理相关操作
包括神秘食谱鉴定、材料查询等功能
"""
import logging
from typing import Dict, Any, Optional, List
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class SpecialtyFoodAction(BaseAction):
    """特色菜管理操作类"""
    
    def __init__(self, key: str, cookie: Optional[Dict[str, str]]):
        """初始化特色菜管理操作实例"""
        self.shrine_base_url = "http://117.72.123.195/index.php?g=Res&m=Shrine"
        super().__init__(key=key, base_url=self.shrine_base_url, cookie=cookie)
    
    def appraise_cookbook(self, goods_code: str, num: int = 1) -> Dict[str, Any]:
        """
        鉴定神秘食谱
        
        Args:
            goods_code: 道具代码 (20903=厨神玉玺, 其他为小仙鉴定书)
            num: 使用数量
            
        Returns:
            Dict[str, Any]: 鉴定结果
        """
        try:
            logging.info(f"开始鉴定神秘食谱，使用道具代码: {goods_code}, 数量: {num}")
            
            response = self.post(
                action_path="a=appraisalCookbooks",
                data={
                    "goods_code": goods_code,
                    "num": num
                }
            )
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            data = response.get("data", [])
            
            if success:
                logging.info(f"神秘食谱鉴定成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "data": data,
                    "raw_response": response
                }
            else:
                logging.warning(f"神秘食谱鉴定失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "data": data,
                    "raw_response": response
                }
                
        except BusinessLogicError as e:
            logging.error(f"神秘食谱鉴定业务逻辑错误: {e}")
            return {
                "success": False,
                "message": f"鉴定失败: {e}",
                "data": [],
                "raw_response": {}
            }
        except Exception as e:
            logging.error(f"神秘食谱鉴定异常: {e}")
            return {
                "success": False,
                "message": f"鉴定异常: {e}",
                "data": [],
                "raw_response": {}
            }
    
    def get_appraisal_materials_count(self, depot_action) -> Dict[str, int]:
        """
        获取鉴定相关材料数量
        
        Args:
            depot_action: DepotAction实例
            
        Returns:
            Dict[str, int]: 材料数量统计
        """
        try:
            from src.delicious_town_bot.constants import ItemType
            
            # 获取所有材料
            materials = depot_action.get_all_items(ItemType.MATERIALS)
            
            # 统计特定材料数量
            material_counts = {
                "神秘食谱": 0,
                "小仙鉴定书": 0,
                "厨神玉玺": 0
            }
            
            for item in materials:
                # 尝试多种可能的字段名
                item_name = item.get("goods_name", item.get("name", ""))
                item_num = item.get("num", 0)
                
                # 调试输出
                logging.debug(f"材料物品: {item_name}, 数量: {item_num}")
                
                if "神秘食谱" in item_name:
                    material_counts["神秘食谱"] += int(item_num) if item_num else 0
                elif "小仙鉴定书" in item_name:
                    material_counts["小仙鉴定书"] += int(item_num) if item_num else 0
                elif "厨神玉玺" in item_name:
                    material_counts["厨神玉玺"] += int(item_num) if item_num else 0
            
            logging.info(f"鉴定材料统计: {material_counts}")
            return material_counts
            
        except Exception as e:
            logging.error(f"获取鉴定材料数量失败: {e}")
            return {
                "神秘食谱": 0,
                "小仙鉴定书": 0,
                "厨神玉玺": 0
            }
    
    def get_fragments_count(self, depot_action) -> Dict[str, Any]:
        """
        获取残卷数量统计
        
        Args:
            depot_action: DepotAction实例
            
        Returns:
            Dict[str, Any]: 残卷统计信息
        """
        try:
            from src.delicious_town_bot.constants import ItemType
            
            # 获取所有残卷 - 使用正确的类型值7
            fragments = depot_action.get_all_items(ItemType.FRAGMENTS_CORRECT)
            
            # 统计残卷信息
            fragment_stats = {
                "total_count": len(fragments),
                "total_num": 0,
                "fragments_by_type": {},
                "fragments_list": []
            }
            
            for item in fragments:
                # 尝试多种可能的字段名
                item_name = item.get("goods_name", item.get("name", "未知残卷"))
                item_num = item.get("num", 0)
                item_id = item.get("id", "")
                
                # 调试输出
                logging.debug(f"残卷物品: {item_name}, 数量: {item_num}, ID: {item_id}")
                
                try:
                    num_value = int(item_num) if item_num else 0
                except (ValueError, TypeError):
                    num_value = 0
                
                fragment_stats["total_num"] += num_value
                
                # 按类型分组
                if item_name not in fragment_stats["fragments_by_type"]:
                    fragment_stats["fragments_by_type"][item_name] = 0
                fragment_stats["fragments_by_type"][item_name] += num_value
                
                # 详细列表
                fragment_stats["fragments_list"].append({
                    "id": item_id,
                    "name": item_name,
                    "num": num_value,
                    "raw_data": item
                })
            
            logging.info(f"残卷统计: 总数 {fragment_stats['total_count']} 种, {fragment_stats['total_num']} 个")
            return fragment_stats
            
        except Exception as e:
            logging.error(f"获取残卷数量统计失败: {e}")
            return {
                "total_count": 0,
                "total_num": 0,
                "fragments_by_type": {},
                "fragments_list": []
            }
    
    def learn_fragment(self, fragment_code: str) -> Dict[str, Any]:
        """
        学习残卷（使用残卷）
        
        Args:
            fragment_code: 残卷的goods_code
            
        Returns:
            Dict[str, Any]: 学习结果
        """
        try:
            logging.info(f"开始学习残卷，代码: {fragment_code}")
            
            # 学习残卷使用Depot模块，而不是Shrine模块
            url = "http://117.72.123.195/index.php?g=Res&m=Depot&a=use_step_1"
            data = {
                "key": self.key,
                "code": fragment_code
            }
            
            response_raw = self.http_client.post(url, data=data, timeout=self.timeout)
            response_raw.raise_for_status()
            response = response_raw.json()
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            response_data = response.get("data", [])
            
            if success:
                logging.info(f"残卷学习成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "data": response_data,
                    "raw_response": response
                }
            else:
                logging.warning(f"残卷学习失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "data": response_data,
                    "raw_response": response
                }
                
        except BusinessLogicError as e:
            logging.error(f"残卷学习业务逻辑错误: {e}")
            return {
                "success": False,
                "message": f"学习失败: {e}",
                "data": [],
                "raw_response": {}
            }
        except Exception as e:
            logging.error(f"残卷学习异常: {e}")
            return {
                "success": False,
                "message": f"学习异常: {e}",
                "data": [],
                "raw_response": {}
            }
    
    def resolve_fragment(self, fragment_code: str) -> Dict[str, Any]:
        """
        分解残卷
        
        Args:
            fragment_code: 残卷的goods_code
            
        Returns:
            Dict[str, Any]: 分解结果
        """
        try:
            logging.info(f"开始分解残卷，代码: {fragment_code}")
            
            # 分解使用特殊的URL，需要直接请求
            import requests
            
            url = "http://117.72.123.195/index.php?g=Res&m=MysteriousCookbooks&a=resolve"
            data = {
                "key": self.key,
                "code": fragment_code
            }
            
            # 使用session发送请求
            response_raw = self.http_client.post(url, data=data, timeout=self.timeout)
            response_raw.raise_for_status()
            response = response_raw.json()
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            data = response.get("data", [])
            
            if success:
                logging.info(f"残卷分解成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "data": data,
                    "raw_response": response
                }
            else:
                logging.warning(f"残卷分解失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "data": data,
                    "raw_response": response
                }
                
        except BusinessLogicError as e:
            logging.error(f"残卷分解业务逻辑错误: {e}")
            return {
                "success": False,
                "message": f"分解失败: {e}",
                "data": [],
                "raw_response": {}
            }
        except Exception as e:
            logging.error(f"残卷分解异常: {e}")
            return {
                "success": False,
                "message": f"分解异常: {e}",
                "data": [],
                "raw_response": {}
            }
    
    def get_learned_recipes(self, page: int = 1) -> Dict[str, Any]:
        """
        获取已学特色菜列表
        
        Args:
            page: 页码，默认为1
            
        Returns:
            Dict[str, Any]: 已学特色菜列表
        """
        try:
            logging.info(f"获取已学特色菜列表，页码: {page}")
            
            url = "http://117.72.123.195/index.php?g=Res&m=MysteriousCookbooks&a=get_list"
            data = {
                "key": self.key,
                "page": page,
                "type": -1  # 获取所有已学特色菜
            }
            
            response_raw = self.http_client.post(url, data=data, timeout=self.timeout)
            response_raw.raise_for_status()
            response = response_raw.json()
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            response_data = response.get("data", {})
            
            if success:
                recipes_list = response_data.get("list", [])
                logging.info(f"成功获取 {len(recipes_list)} 道已学特色菜")
                return {
                    "success": True,
                    "message": message,
                    "recipes": recipes_list,
                    "level_exp_config": response_data.get("level_exp_config", []),
                    "level_name_config": response_data.get("level_name_config", []),
                    "raw_response": response
                }
            else:
                logging.warning(f"获取已学特色菜失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "recipes": [],
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"获取已学特色菜异常: {e}")
            return {
                "success": False,
                "message": f"获取失败: {e}",
                "recipes": [],
                "raw_response": {}
            }
    
    def get_recipe_info(self, recipe_id: str) -> Dict[str, Any]:
        """
        获取特色菜详细信息
        
        Args:
            recipe_id: 特色菜ID
            
        Returns:
            Dict[str, Any]: 特色菜详细信息
        """
        try:
            logging.info(f"获取特色菜详细信息，ID: {recipe_id}")
            
            url = "http://117.72.123.195/index.php?g=Res&m=MysteriousCookbooks&a=get_info"
            data = {
                "key": self.key,
                "id": recipe_id
            }
            
            response_raw = self.http_client.post(url, data=data, timeout=self.timeout)
            response_raw.raise_for_status()
            response = response_raw.json()
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            response_data = response.get("data", {})
            
            if success:
                logging.info(f"成功获取特色菜详细信息")
                return {
                    "success": True,
                    "message": message,
                    "recipe_info": response_data.get("info", {}),
                    "ingredients": response_data.get("food", []),
                    "raw_response": response
                }
            else:
                logging.warning(f"获取特色菜详细信息失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "recipe_info": {},
                    "ingredients": [],
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"获取特色菜详细信息异常: {e}")
            return {
                "success": False,
                "message": f"获取失败: {e}",
                "recipe_info": {},
                "ingredients": [],
                "raw_response": {}
            }
    
    def cook_recipe(self, recipe_id: str, times: int = 3) -> Dict[str, Any]:
        """
        烹饪特色菜
        
        Args:
            recipe_id: 特色菜ID
            times: 烹饪倍数 (3, 5, 10, 50, 100)
            
        Returns:
            Dict[str, Any]: 烹饪结果
        """
        try:
            logging.info(f"开始烹饪特色菜，ID: {recipe_id}, 倍数: {times}")
            
            url = "http://117.72.123.195/index.php?g=Res&m=MysteriousCookbooks&a=cook"
            data = {
                "key": self.key,
                "id": recipe_id,
                "times": times
            }
            
            response_raw = self.http_client.post(url, data=data, timeout=self.timeout)
            response_raw.raise_for_status()
            response = response_raw.json()
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            response_data = response.get("data", [])
            
            if success:
                logging.info(f"特色菜烹饪成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "data": response_data,
                    "raw_response": response
                }
            else:
                logging.warning(f"特色菜烹饪失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "data": response_data,
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"特色菜烹饪异常: {e}")
            return {
                "success": False,
                "message": f"烹饪失败: {e}",
                "data": [],
                "raw_response": {}
            }
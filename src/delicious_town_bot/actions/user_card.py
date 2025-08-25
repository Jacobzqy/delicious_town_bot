"""
用户卡片信息获取模块
用于获取用户餐厅信息、厨力属性、装备信息等
"""
import re
from typing import Dict, Any, Optional, List
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class UserCardAction(BaseAction):
    """
    用户卡片信息操作类，获取用户餐厅详细信息
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key=key, cookie=cookie, base_url=base_url)
        # 更新 Referer
        self.http_client.headers.update({
            'Referer': 'http://117.72.123.195/wap/res/user_card.html'
        })

    def get_user_card(self, res_id: str = "") -> Dict[str, Any]:
        """
        获取用户卡片信息
        
        Args:
            res_id: 餐厅ID，空字符串表示获取自己的信息
            
        Returns:
            Dict包含用户信息，格式如下：
            {
                "success": bool,
                "restaurant_info": {
                    "name": str,
                    "level": int,
                    "exp": int,
                    "gold": int,
                    "street": str,
                    "prestige": int,
                    "vip_level": int,
                    "seat_num": int,
                    ...
                },
                "cooking_power": {
                    "fire": int,           # 火候
                    "cooking": int,        # 厨艺  
                    "sword": int,          # 刀工
                    "season": int,         # 调味
                    "originality": int,    # 创意
                    "luck": int,           # 幸运
                    "total_base": int,     # 基础总厨力
                    "total_with_equip": int  # 装备加成后总厨力
                },
                "equipment": List[Dict],  # 装备信息
                "speciality": Dict,      # 特色菜信息
                "message": str
            }
        """
        print(f"[*] 正在获取用户卡片信息 (res_id: {res_id or '自己'})...")
        
        action_path = "m=Index&a=user_card"
        params = {"res_id": res_id}
        
        try:
            response_data = self.get(action_path, params=params)
            
            if not response_data.get('status'):
                error_msg = response_data.get('msg', '获取用户卡片信息失败')
                print(f"[Error] {error_msg}")
                return {"success": False, "message": error_msg}
            
            # 解析响应数据
            data = response_data.get('data', {})
            result = self._parse_user_card_data(data)
            result["success"] = True
            result["message"] = "获取用户卡片信息成功"
            
            print(f"[+] 用户卡片信息获取成功")
            return result
            
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取用户卡片信息失败: {e}")
            return {"success": False, "message": str(e)}

    def _parse_user_card_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析用户卡片数据
        
        Args:
            data: API返回的数据部分
            
        Returns:
            解析后的结构化数据
        """
        result = {
            "restaurant_info": {},
            "cooking_power": {},
            "equipment": [],
            "speciality": {},
            "income_info": {}
        }
        
        # 解析餐厅基础信息
        res_info = data.get('res', {})
        if res_info:
            result["restaurant_info"] = {
                "id": res_info.get('id'),
                "name": res_info.get('name'),
                "level": int(res_info.get('level', 0)),
                "star": int(res_info.get('star', 0)),
                "exp": int(res_info.get('exp', 0)),
                "gold": int(res_info.get('gold', 0)),
                "vit": int(res_info.get('vit', 0)),
                "vit_max": int(res_info.get('vit_num', 0)),
                "prestige": int(res_info.get('prestige_num', 0)),
                "vip_level": int(res_info.get('vip_level', 0)),
                "vip_time": res_info.get('vip_time'),
                "seat_num": int(res_info.get('seat_num', 0)),
                "floor_num": int(res_info.get('floor_num', 0)),
                "cupboard_num": int(res_info.get('cupboard_num', 0)),
                "cupboard_lock_num": int(res_info.get('cupboard_lock_num', 0)),
                "store_num": int(res_info.get('store_num', 0)),
                "street_id": res_info.get('street_id'),
                "is_active": res_info.get('is_active') == '1'
            }
        
        # 解析街道信息
        street_info = data.get('street_info', {})
        if street_info:
            result["restaurant_info"]["street_name"] = street_info.get('name')
            result["restaurant_info"]["cook_type"] = street_info.get('cook_name')
        
        # 解析厨力属性
        property_info = data.get('property', {})
        if property_info:
            result["cooking_power"] = {
                "fire": int(property_info.get('fire', 0)),
                "fire_add": int(property_info.get('fire_add', 0)),
                "cooking": int(property_info.get('cooking', 0)),
                "cooking_add": int(property_info.get('cooking_add', 0)),
                "sword": int(property_info.get('sword', 0)),
                "sword_add": int(property_info.get('sword_add', 0)),
                "season": int(property_info.get('season', 0)),
                "season_add": int(property_info.get('season_add', 0)),
                "originality": int(property_info.get('originality', 0)),
                "originality_add": int(property_info.get('originality_add', 0)),
                "luck": int(property_info.get('luck', 0)),
                "luck_add": int(property_info.get('luck_add', 0)),
                "total_base": int(property_info.get('total_num', 0)),
                "total_with_equip": int(property_info.get('total_num', 0)) + int(property_info.get('total_add_num', 0))
            }
        
        # 解析装备信息
        equip_list = data.get('equip_list', [])
        if equip_list:
            result["equipment"] = []
            for equip in equip_list:
                equipment_item = {
                    "id": equip.get('id'),
                    "name": equip.get('goods_name'),
                    "code": equip.get('goods_code'),
                    "part_type": int(equip.get('part_type', 0)),
                    "level": int(equip.get('level', 0)),
                    "strengthen_num": int(equip.get('strengthen_num', 0)),
                    "strengthen_name": equip.get('strengthen_name'),
                    "hole": int(equip.get('hole', 0)),
                    "is_use": equip.get('is_use') == '1',  # 添加装备使用状态
                    "attributes": {
                        "fire": int(equip.get('fire', 0)),
                        "cooking": int(equip.get('cooking', 0)),
                        "sword": int(equip.get('sword', 0)),
                        "season": int(equip.get('season', 0)),
                        "originality": int(equip.get('originality', 0)),
                        "luck": int(equip.get('luck', 0))
                    },
                    "attribute_adds": {
                        "fire_add": int(equip.get('fire_add', 0)),
                        "cooking_add": int(equip.get('cooking_add', 0)),
                        "sword_add": int(equip.get('sword_add', 0)),
                        "season_add": int(equip.get('season_add', 0)),
                        "originality_add": int(equip.get('originality_add', 0)),
                        "luck_add": int(equip.get('luck_add', 0))
                    },
                    "hole_adds": {
                        "fire_hole_add": int(equip.get('fire_hole_add', 0)),
                        "cooking_hole_add": int(equip.get('cooking_hole_add', 0)),
                        "sword_hole_add": int(equip.get('sword_hole_add', 0)),
                        "season_hole_add": int(equip.get('season_hole_add', 0)),
                        "originality_hole_add": int(equip.get('originality_hole_add', 0)),
                        "luck_hole_add": int(equip.get('luck_hole_add', 0))
                    }
                }
                result["equipment"].append(equipment_item)
        
        # 解析特色菜信息
        speciality = data.get('specialities_cook', {})
        if speciality:
            result["speciality"] = {
                "id": speciality.get('cookbooks_id'),
                "name": speciality.get('cookbooks_name'),
                "quality": int(speciality.get('quality', 0)),
                "times": int(speciality.get('times', 0)),
                "num": int(speciality.get('num', 0)),
                "price": int(speciality.get('price', 0)),
                "nutritive": int(speciality.get('nutritive', 0)),
                "level": int(speciality.get('level', 0)),
                "state": speciality.get('state') == '1'
            }
        
        # 解析收入信息
        income_info = data.get('last_ge_count', {})
        if income_info:
            result["income_info"] = {
                "gold_num": int(income_info.get('gold_num', 0)),
                "exp_num": int(income_info.get('exp_num', 0)),
                "last_time": income_info.get('last_time'),
                "next_time": income_info.get('next_time'),
                "seat_num": int(income_info.get('seat_num', 0)),
                "nitpick_num": int(income_info.get('nitpick_num', 0)),
                "nitpick_success_num": int(income_info.get('nitpick_success_num', 0))
            }
            
            # 解析收入详情JSON
            try:
                import json
                gold_data = json.loads(income_info.get('gold_json', '{}'))
                exp_data = json.loads(income_info.get('exp_json', '{}'))
                result["income_info"]["gold_detail"] = gold_data
                result["income_info"]["exp_detail"] = exp_data
            except:
                pass
        
        return result

    def get_cooking_power_summary(self, res_id: str = "") -> Dict[str, Any]:
        """
        获取厨力属性摘要
        
        Args:
            res_id: 餐厅ID
            
        Returns:
            厨力属性摘要
        """
        print(f"[*] 正在获取厨力属性摘要...")
        
        card_info = self.get_user_card(res_id)
        if not card_info.get("success"):
            return card_info
        
        cooking_power = card_info.get("cooking_power", {})
        restaurant_info = card_info.get("restaurant_info", {})
        
        # 计算各属性总值
        attributes = ["fire", "cooking", "sword", "season", "originality", "luck"]
        summary = {
            "restaurant_name": restaurant_info.get("name"),
            "restaurant_level": restaurant_info.get("level"),
            "attributes": {},
            "total_base": cooking_power.get("total_base", 0),
            "total_with_equip": cooking_power.get("total_with_equip", 0),
            "equipment_bonus": cooking_power.get("total_with_equip", 0) - cooking_power.get("total_base", 0)
        }
        
        for attr in attributes:
            base_value = cooking_power.get(attr, 0)
            add_value = cooking_power.get(f"{attr}_add", 0)
            summary["attributes"][attr] = {
                "name": self._get_attribute_name(attr),
                "base": base_value,
                "equipment_add": add_value,
                "total": base_value + add_value
            }
        
        summary["success"] = True
        summary["message"] = "获取厨力属性摘要成功"
        print(f"[+] 厨力属性摘要获取成功")
        
        return summary

    def _get_attribute_name(self, attr: str) -> str:
        """获取属性中文名称"""
        name_map = {
            "fire": "火候",
            "cooking": "厨艺", 
            "sword": "刀工",
            "season": "调味",
            "originality": "创意",
            "luck": "幸运"
        }
        return name_map.get(attr, attr)

    def get_equipment_summary(self, res_id: str = "") -> Dict[str, Any]:
        """
        获取装备信息摘要
        
        Args:
            res_id: 餐厅ID
            
        Returns:
            装备信息摘要
        """
        print(f"[*] 正在获取装备信息摘要...")
        
        card_info = self.get_user_card(res_id)
        if not card_info.get("success"):
            return card_info
        
        equipment = card_info.get("equipment", [])
        
        # 装备部位名称映射
        part_names = {
            1: "铲子",
            2: "刀具", 
            3: "锅具",
            4: "调料瓶",
            5: "厨师帽"
        }
        
        summary = {
            "equipment_count": len(equipment),
            "equipment_list": [],
            "total_attributes": {
                "fire": 0, "cooking": 0, "sword": 0,
                "season": 0, "originality": 0, "luck": 0
            }
        }
        
        for equip in equipment:
            part_type = equip.get("part_type", 0)
            equip_summary = {
                "id": equip.get("id"),  # 添加装备ID，用于强化操作
                "name": equip.get("name"),
                "part_name": part_names.get(part_type, f"未知部位{part_type}"),
                "strengthen_num": equip.get("strengthen_num", 0),  # 保持原始字段名
                "strengthen_level": equip.get("strengthen_num", 0),  # 兼容字段名
                "strengthen_name": equip.get("strengthen_name"),
                "is_use": equip.get("is_use", False),  # 添加装备使用状态
                "total_attributes": {}
            }
            
            # 计算装备总属性
            attributes = equip.get("attributes", {})
            attribute_adds = equip.get("attribute_adds", {})
            hole_adds = equip.get("hole_adds", {})
            
            for attr in ["fire", "cooking", "sword", "season", "originality", "luck"]:
                base = attributes.get(attr, 0)
                add = attribute_adds.get(f"{attr}_add", 0)
                hole = hole_adds.get(f"{attr}_hole_add", 0)
                total = base + add + hole
                
                equip_summary["total_attributes"][attr] = total
                summary["total_attributes"][attr] += total
            
            summary["equipment_list"].append(equip_summary)
        
        summary["success"] = True
        summary["message"] = "获取装备信息摘要成功"
        print(f"[+] 装备信息摘要获取成功")
        
        return summary

    def get_equipment_list(self, part_type: int = None, page: int = 1) -> Dict[str, Any]:
        """
        获取装备列表
        
        Args:
            part_type: 装备部位类型 (1-5，None表示所有类型)
            page: 页码
            
        Returns:
            装备列表数据
        """
        print(f"[*] 正在获取装备列表 (部位类型: {part_type or '全部'}, 页码: {page})...")
        
        action_path = "m=Equip&a=get_list"
        payload = {
            "page": str(page)
        }
        
        if part_type is not None:
            payload["type"] = str(part_type)
        else:
            payload["type"] = "1"  # 默认获取铲子类型
        
        try:
            response_data = self.post(action_path, data=payload)
            
            if not response_data.get('status'):
                error_msg = response_data.get('msg', '获取装备列表失败')
                print(f"[Error] {error_msg}")
                return {"success": False, "message": error_msg, "equipment_list": []}
            
            # 解析装备列表
            equipment_data = response_data.get('data', [])
            equipment_list = []
            
            for item in equipment_data:
                equipment_item = {
                    "id": item.get('id'),
                    "name": item.get('goods_name'),
                    "goods_code": item.get('goods_code'),
                    "part_type": int(item.get('part_type', 0)),
                    "part_name": self._get_part_name(int(item.get('part_type', 0))),
                    "level": int(item.get('level', 0)),
                    "strengthen_num": int(item.get('strengthen_num', 0)),
                    "strengthen_name": item.get('strengthen_name', ''),
                    "hole": int(item.get('hole', 0)),
                    "is_use": item.get('is_use') == '1',
                    "depot_id": item.get('depot_id'),
                    "base_attributes": {
                        "fire": int(item.get('fire', 0)),
                        "cooking": int(item.get('cooking', 0)),
                        "sword": int(item.get('sword', 0)),
                        "season": int(item.get('season', 0)),
                        "originality": int(item.get('originality', 0)),
                        "luck": int(item.get('luck', 0))
                    },
                    "strengthen_adds": {
                        "fire_add": int(item.get('fire_add', 0)),
                        "cooking_add": int(item.get('cooking_add', 0)),
                        "sword_add": int(item.get('sword_add', 0)),
                        "season_add": int(item.get('season_add', 0)),
                        "originality_add": int(item.get('originality_add', 0)),
                        "luck_add": int(item.get('luck_add', 0))
                    },
                    "hole_adds": {
                        "fire_hole_add": int(item.get('fire_hole_add', 0)),
                        "cooking_hole_add": int(item.get('cooking_hole_add', 0)),
                        "sword_hole_add": int(item.get('sword_hole_add', 0)),
                        "season_hole_add": int(item.get('season_hole_add', 0)),
                        "originality_hole_add": int(item.get('originality_hole_add', 0)),
                        "luck_hole_add": int(item.get('luck_hole_add', 0))
                    }
                }
                
                # 计算总属性
                equipment_item["total_attributes"] = {}
                for attr in ["fire", "cooking", "sword", "season", "originality", "luck"]:
                    base = equipment_item["base_attributes"][attr]
                    strengthen = equipment_item["strengthen_adds"][f"{attr}_add"]
                    hole = equipment_item["hole_adds"][f"{attr}_hole_add"]
                    equipment_item["total_attributes"][attr] = base + strengthen + hole
                
                equipment_list.append(equipment_item)
            
            print(f"[+] 装备列表获取成功，共 {len(equipment_list)} 件装备")
            return {
                "success": True,
                "message": f"获取装备列表成功，共 {len(equipment_list)} 件装备",
                "equipment_list": equipment_list,
                "total_count": len(equipment_list)
            }
            
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取装备列表失败: {e}")
            return {"success": False, "message": str(e), "equipment_list": []}

    def _get_part_name(self, part_type: int) -> str:
        """获取装备部位名称"""
        part_names = {
            1: "铲子",
            2: "刀具", 
            3: "锅具",
            4: "调料瓶",
            5: "厨师帽"
        }
        return part_names.get(part_type, f"未知部位{part_type}")

    def get_novice_equipment_count(self) -> Dict[str, Any]:
        """
        获取见习装备数量统计
        
        Returns:
            见习装备数量统计
        """
        print(f"[*] 正在统计见习装备数量...")
        
        novice_equipment_codes = ["40101", "40102", "40103"]  # 见习之铲、刀、锅的goods_code
        novice_names = ["见习之铲", "见习之刀", "见习之锅"]
        
        result = {
            "success": True,
            "message": "见习装备统计完成",
            "novice_equipment": {},
            "total_count": 0
        }
        
        # 获取各部位装备并统计见习装备
        for part_type in range(1, 4):  # 铲子、刀具、锅具
            equipment_result = self.get_equipment_list(part_type=part_type)
            if equipment_result.get("success"):
                equipment_list = equipment_result.get("equipment_list", [])
                
                # 统计该部位的见习装备
                novice_code = novice_equipment_codes[part_type - 1]
                novice_name = novice_names[part_type - 1]
                
                novice_count = 0
                novice_items = []
                
                for equipment in equipment_list:
                    if equipment.get("goods_code") == novice_code:
                        novice_count += 1
                        novice_items.append({
                            "id": equipment.get("id"),
                            "strengthen_num": equipment.get("strengthen_num", 0),
                            "strengthen_name": equipment.get("strengthen_name", ""),
                            "is_use": equipment.get("is_use", False)
                        })
                
                result["novice_equipment"][novice_name] = {
                    "count": novice_count,
                    "items": novice_items
                }
                result["total_count"] += novice_count
        
        print(f"[+] 见习装备统计完成，总计 {result['total_count']} 件")
        return result

    def intensify_equipment(self, equipment_id: str) -> Dict[str, Any]:
        """
        强化装备
        
        Args:
            equipment_id: 装备ID
            
        Returns:
            强化结果
        """
        print(f"[*] 正在强化装备 (ID: {equipment_id})...")
        
        action_path = "m=Equip&a=intensify"
        payload = {
            "id": str(equipment_id)
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            if response_data.get('status'):
                message = response_data.get('msg', '强化成功')
                
                # 解析强化结果消息
                enhance_result = self._parse_enhance_message(message)
                
                # 根据消息内容判断是否真正成功，而非仅仅依赖API状态码
                actual_success = enhance_result.get("success", False)
                
                if actual_success:
                    print(f"[+] 装备强化成功: {message}")
                else:
                    print(f"[!] 装备强化失败: {message}")
                
                return {
                    "success": actual_success,
                    "message": message,
                    "equipment_id": equipment_id,
                    "enhance_result": enhance_result
                }
            else:
                error_msg = response_data.get('msg', '强化失败')
                print(f"[Error] 装备强化失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "equipment_id": equipment_id
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 强化装备失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "equipment_id": equipment_id
            }

    def resolve_equipment(self, equipment_id: str) -> Dict[str, Any]:
        """
        分解装备
        
        Args:
            equipment_id: 装备ID
            
        Returns:
            分解结果
        """
        print(f"[*] 正在分解装备 (ID: {equipment_id})...")
        
        action_path = "m=Equip&a=resolve_equip"
        payload = {
            "id": str(equipment_id)
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            if response_data.get('status'):
                message = response_data.get('msg', '分解成功')
                print(f"[+] 装备分解成功: {message}")
                
                # 解析分解结果消息
                resolve_result = self._parse_resolve_message(message)
                
                return {
                    "success": True,
                    "message": message,
                    "equipment_id": equipment_id,
                    "resolve_result": resolve_result
                }
            else:
                error_msg = response_data.get('msg', '分解失败')
                print(f"[Error] 装备分解失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "equipment_id": equipment_id
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 分解装备失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "equipment_id": equipment_id
            }

    def _parse_enhance_message(self, message: str) -> Dict[str, Any]:
        """解析强化结果消息"""
        # 更精确的成功判断：检查失败标识符
        is_failure = any(keyword in message for keyword in [
            "强化失败", "失败", "照样扣除", "没有成功"
        ])
        
        result = {
            "success": "强化成功" in message and not is_failure,
            "attributes": []
        }
        
        # 解析属性提升 (例如: "创意+3")
        import re
        attr_pattern = r'(火候|厨艺|刀工|调味|创意|幸运)\+(\d+)'
        matches = re.findall(attr_pattern, message)
        
        for attr_name, value in matches:
            result["attributes"].append({
                "name": attr_name,
                "increase": int(value)
            })
        
        return result

    def _parse_resolve_message(self, message: str) -> Dict[str, Any]:
        """解析分解结果消息"""
        result = {
            "success": "分解成功" in message,
            "items": []
        }
        
        # 解析获得的物品 (例如: "强化石+1", "厨具精华+5")
        import re
        item_pattern = r'([^\+<>\s]+)\+(\d+)'
        matches = re.findall(item_pattern, message)
        
        for item_name, quantity in matches:
            if item_name and item_name != "br":  # 过滤HTML标签
                result["items"].append({
                    "name": item_name,
                    "quantity": int(quantity)
                })
        
        return result

    def equip_equipment(self, equipment_id: str) -> Dict[str, Any]:
        """
        装备厨具
        
        Args:
            equipment_id: 装备ID
            
        Returns:
            装备结果
        """
        print(f"[*] 正在装备厨具 (ID: {equipment_id})...")
        
        action_path = "m=Equip&a=fit"
        payload = {
            "id": str(equipment_id)
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            # 添加详细的调试信息
            print(f"[Debug] 装备接口响应: {response_data}")
            
            if response_data.get('status'):
                message = response_data.get('msg', '装备成功')
                print(f"[+] 厨具装备成功: {message}")
                
                return {
                    "success": True,
                    "message": message,
                    "equipment_id": equipment_id
                }
            else:
                error_msg = response_data.get('msg', '装备失败')
                print(f"[Error] 厨具装备失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "equipment_id": equipment_id
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 装备厨具失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "equipment_id": equipment_id
            }

    def auto_process_novice_equipment(self) -> Dict[str, Any]:
        """
        自动处理见习装备：先强化一个完成每日任务，然后分解所有见习装备（包括强化后的装备）
        
        流程：
        1. 强化1件见习装备（完成每日强化任务）
        2. 重新获取所有见习装备列表（包括强化后的装备）
        3. 分解所有见习装备（包括强化后的装备）
        
        Returns:
            处理结果
        """
        print(f"[*] 开始自动处理见习装备...")
        
        results = {
            "success": True,
            "enhanced_equipment": None,
            "resolved_equipment": [],
            "failed_operations": [],
            "total_processed": 0,
            "message": ""
        }
        
        try:
            # 获取见习装备统计
            novice_result = self.get_novice_equipment_count()
            if not novice_result.get("success"):
                return {
                    "success": False,
                    "message": "获取见习装备列表失败",
                    "details": results
                }
            
            # 收集所有见习装备
            all_novice_items = []
            novice_equipment = novice_result.get("novice_equipment", {})
            
            for name, data in novice_equipment.items():
                items = data.get("items", [])
                for item in items:
                    if not item.get("is_use", False):  # 只处理未使用的装备
                        all_novice_items.append({
                            "id": item.get("id"),
                            "name": name,
                            "strengthen_num": item.get("strengthen_num", 0)
                        })
            
            if not all_novice_items:
                return {
                    "success": True,
                    "message": "没有可处理的见习装备（所有装备都在使用中）",
                    "details": results
                }
            
            print(f"[*] 找到 {len(all_novice_items)} 件可处理的见习装备")
            
            # 步骤1: 强化一个见习装备完成每日任务
            # 选择强化等级最低的装备
            enhance_item = min(all_novice_items, key=lambda x: x["strengthen_num"])
            
            print(f"[*] 强化装备完成每日任务: {enhance_item['name']} (强化等级: {enhance_item['strengthen_num']})")
            enhance_result = self.intensify_equipment(enhance_item["id"])
            
            if enhance_result.get("success"):
                results["enhanced_equipment"] = {
                    "name": enhance_item["name"],
                    "id": enhance_item["id"],
                    "result": enhance_result
                }
                results["total_processed"] += 1
                print(f"[+] 每日强化任务完成: {enhance_item['name']}")
            else:
                print(f"[!] 强化失败: {enhance_result.get('message')}")
                results["failed_operations"].append({
                    "operation": "强化",
                    "equipment": enhance_item["name"],
                    "error": enhance_result.get("message")
                })
            
            # 步骤2: 重新获取所有见习装备（包括强化后的装备）
            print(f"[*] 重新获取见习装备列表...")
            import time
            time.sleep(1)  # 等待1秒让强化操作生效
            
            updated_novice_result = self.get_novice_equipment_count()
            if not updated_novice_result.get("success"):
                print(f"[!] 重新获取见习装备列表失败")
                # 使用原有列表继续分解
                items_to_resolve = all_novice_items
            else:
                # 收集所有见习装备（包括强化后的装备）
                items_to_resolve = []
                updated_novice_equipment = updated_novice_result.get("novice_equipment", {})
                
                for name, data in updated_novice_equipment.items():
                    items = data.get("items", [])
                    for item in items:
                        if not item.get("is_use", False):  # 只处理未使用的装备
                            items_to_resolve.append({
                                "id": item.get("id"),
                                "name": name,
                                "strengthen_num": item.get("strengthen_num", 0)
                            })
            
            # 步骤3: 分解所有见习装备（包括强化后的装备）
            print(f"[*] 开始分解所有 {len(items_to_resolve)} 件见习装备（包括强化后的装备）...")
            
            for item in items_to_resolve:
                print(f"[*] 分解装备: {item['name']}")
                resolve_result = self.resolve_equipment(item["id"])
                
                if resolve_result.get("success"):
                    results["resolved_equipment"].append({
                        "name": item["name"],
                        "id": item["id"],
                        "result": resolve_result
                    })
                    results["total_processed"] += 1
                    print(f"[+] 分解成功: {item['name']}")
                else:
                    print(f"[!] 分解失败: {resolve_result.get('message')}")
                    results["failed_operations"].append({
                        "operation": "分解",
                        "equipment": item["name"],
                        "error": resolve_result.get("message")
                    })
                
                # 分解间隔500ms
                import time
                time.sleep(0.5)
            
            # 生成总结消息
            enhanced_count = 1 if results["enhanced_equipment"] else 0
            resolved_count = len(results["resolved_equipment"])
            failed_count = len(results["failed_operations"])
            
            if failed_count == 0:
                results["message"] = f"✅ 见习装备处理完成！强化 {enhanced_count} 件，分解 {resolved_count} 件"
                results["success"] = True
            else:
                results["message"] = f"⚠️ 见习装备处理完成，成功处理 {results['total_processed']} 件，失败 {failed_count} 件"
                results["success"] = results["total_processed"] > 0
            
            print(f"[+] {results['message']}")
            return results
            
        except Exception as e:
            print(f"[Error] 自动处理见习装备失败: {e}")
            return {
                "success": False,
                "message": f"自动处理见习装备异常: {str(e)}",
                "details": results
            }

    def get_tower_info(self) -> Dict[str, Any]:
        """
        获取厨塔信息，包括各层属性和用户厨力
        
        Returns:
            厨塔信息和用户属性数据
        """
        print(f"[*] 正在获取厨塔信息...")
        
        action_path = "m=Tower&a=get_info"
        
        try:
            response_data = self.post(action_path, data={})
            
            if response_data.get('status'):
                data = response_data.get('data', {})
                
                result = {
                    "success": True,
                    "message": "获取厨塔信息成功",
                    "tower_floors": data.get('list', []),
                    "user_property": data.get('property', {}),
                    "special_dish": data.get('specialities_cook', {}),
                    "raw_data": data
                }
                
                print(f"[+] 厨塔信息获取成功，共 {len(result['tower_floors'])} 层")
                return result
            else:
                error_msg = response_data.get('msg', '获取厨塔信息失败')
                print(f"[Error] {error_msg}")
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取厨塔信息失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def calculate_real_cooking_power(self, property_data: Dict[str, Any], special_dish: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        计算真实厨力
        
        真实厨力公式：
        厨艺×1.44 + 刀工×1.41 + 调味×1.5 + 火候×1.71 + 创意×2.25 + 特色菜营养值×1.8
        
        Args:
            property_data: 用户属性数据
            special_dish: 特色菜数据
            
        Returns:
            真实厨力计算结果
        """
        print(f"[*] 正在计算真实厨力...")
        
        # 属性权重
        weights = {
            "cooking": 1.44,    # 厨艺
            "sword": 1.41,      # 刀工
            "season": 1.5,      # 调味
            "fire": 1.71,       # 火候
            "originality": 2.25, # 创意
            "nutritive": 1.8    # 特色菜营养值
        }
        
        # 计算各属性总值（基础值 + 装备加成）
        attributes = {}
        total_power = 0
        
        for attr in ["fire", "cooking", "sword", "season", "originality"]:
            base = int(property_data.get(attr, 0))
            add = int(property_data.get(f"{attr}_add", 0))
            total = base + add
            weight = weights[attr]
            weighted_value = total * weight
            
            attributes[attr] = {
                "base": base,
                "equipment_add": add,
                "total": total,
                "weight": weight,
                "weighted_value": weighted_value
            }
            total_power += weighted_value
        
        # 特色菜营养值
        nutritive_value = 0
        if special_dish:
            nutritive_value = int(special_dish.get("nutritive", 0))
            nutritive_weighted = nutritive_value * weights["nutritive"]
            total_power += nutritive_weighted
            
            attributes["nutritive"] = {
                "value": nutritive_value,
                "weight": weights["nutritive"],
                "weighted_value": nutritive_weighted,
                "dish_name": special_dish.get("cookbooks_name", "")
            }
        
        result = {
            "success": True,
            "total_real_power": round(total_power, 2),
            "attributes": attributes,
            "special_dish_power": round(nutritive_value * weights["nutritive"], 2) if nutritive_value > 0 else 0,
            "formula": "厨艺×1.44 + 刀工×1.41 + 调味×1.5 + 火候×1.71 + 创意×2.25 + 特色菜营养值×1.8"
        }
        
        print(f"[+] 真实厨力计算完成: {result['total_real_power']}")
        return result

    def calculate_tower_floor_power(self, floor_data: Dict[str, Any]) -> float:
        """
        计算厨塔层级的真实厨力
        
        Args:
            floor_data: 厨塔层级数据
            
        Returns:
            该层的真实厨力
        """
        weights = {
            "cooking": 1.44,
            "sword": 1.41,
            "season": 1.5,
            "fire": 1.71,
            "originality": 2.25
        }
        
        total_power = 0
        for attr in ["fire", "cooking", "sword", "season", "originality"]:
            base = int(floor_data.get(attr, 0))
            add = int(floor_data.get(f"{attr}_add", 0))
            total = base + add
            total_power += total * weights[attr]
        
        return round(total_power, 2)

    def recommend_tower_floors(self, user_power: float, tower_floors: List[Dict[str, Any]], safety_margin: float = 0.9) -> Dict[str, Any]:
        """
        推荐合适的厨塔层数
        
        Args:
            user_power: 用户真实厨力
            tower_floors: 厨塔层级列表
            safety_margin: 安全边际（0.9表示用户厨力需要达到层级厨力的90%以上）
            
        Returns:
            推荐结果
        """
        print(f"[*] 正在分析厨塔层级，用户厨力: {user_power}")
        
        recommendations = {
            "user_power": user_power,
            "safe_floors": [],      # 稳定通过的层级
            "challenge_floors": [], # 有挑战性的层级
            "impossible_floors": [], # 无法通过的层级
            "best_floor": None,     # 最佳推荐层级
            "max_safe_floor": None  # 最高安全层级
        }
        
        for floor in tower_floors:
            floor_power = self.calculate_tower_floor_power(floor)
            floor_level = int(floor.get("level", 0))
            floor_name = floor.get("name", "")
            
            power_ratio = user_power / floor_power if floor_power > 0 else float('inf')
            
            floor_info = {
                "level": floor_level,
                "name": floor_name,
                "floor_power": floor_power,
                "power_ratio": round(power_ratio, 3),
                "power_diff": round(user_power - floor_power, 2)
            }
            
            if power_ratio >= 1.2:  # 用户厨力超过层级厨力20%以上
                recommendations["safe_floors"].append(floor_info)
            elif power_ratio >= safety_margin:  # 用户厨力达到安全边际
                recommendations["challenge_floors"].append(floor_info)
            else:  # 用户厨力不足
                recommendations["impossible_floors"].append(floor_info)
        
        # 确定最佳推荐层级
        if recommendations["challenge_floors"]:
            # 选择挑战性层级中厨力最接近的
            recommendations["best_floor"] = max(
                recommendations["challenge_floors"], 
                key=lambda x: x["level"]
            )
        elif recommendations["safe_floors"]:
            # 选择安全层级中最高的
            recommendations["best_floor"] = max(
                recommendations["safe_floors"], 
                key=lambda x: x["level"]
            )
        
        # 确定最高安全层级
        if recommendations["safe_floors"]:
            recommendations["max_safe_floor"] = max(
                recommendations["safe_floors"], 
                key=lambda x: x["level"]
            )
        
        if recommendations["best_floor"]:
            print(f"[+] 推荐厨塔层级: {recommendations['best_floor']['level']}层 ({recommendations['best_floor']['name']})")
        else:
            print(f"[!] 暂无合适的厨塔层级")
        
        return recommendations

    def get_tower_recommendations(self) -> Dict[str, Any]:
        """
        获取厨塔推荐（完整流程）
        
        Returns:
            完整的厨塔推荐结果
        """
        print(f"[*] 开始获取厨塔推荐...")
        
        try:
            # 获取厨塔信息
            tower_info = self.get_tower_info()
            if not tower_info.get("success"):
                return tower_info
            
            # 计算用户真实厨力
            user_property = tower_info["user_property"]
            special_dish = tower_info["special_dish"]
            power_result = self.calculate_real_cooking_power(user_property, special_dish)
            
            if not power_result.get("success"):
                return power_result
            
            user_power = power_result["total_real_power"]
            tower_floors = tower_info["tower_floors"]
            
            # 获取推荐
            recommendations = self.recommend_tower_floors(user_power, tower_floors)
            
            # 组合结果
            result = {
                "success": True,
                "message": "厨塔推荐获取成功",
                "user_power_analysis": power_result,
                "tower_recommendations": recommendations,
                "tower_floors_count": len(tower_floors)
            }
            
            print(f"[+] 厨塔推荐获取成功")
            return result
            
        except Exception as e:
            print(f"[Error] 获取厨塔推荐失败: {e}")
            return {
                "success": False,
                "message": f"获取厨塔推荐失败: {str(e)}"
            }


# ==============================================================================
#  独立测试脚本
# ==============================================================================
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")
    
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}

    user_card_action = UserCardAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "=" * 20 + " 用户卡片信息测试 " + "=" * 20)

    # 测试获取用户卡片信息
    print("\n--- 1. 获取完整用户卡片信息 ---")
    card_result = user_card_action.get_user_card()
    if card_result.get("success"):
        print(f"餐厅名称: {card_result['restaurant_info']['name']}")
        print(f"餐厅等级: {card_result['restaurant_info']['level']}")
        print(f"总厨力: {card_result['cooking_power']['total_with_equip']}")
        print(f"装备数量: {len(card_result['equipment'])}")
    
    # 测试获取厨力摘要
    print("\n--- 2. 获取厨力属性摘要 ---")
    power_result = user_card_action.get_cooking_power_summary()
    if power_result.get("success"):
        print(f"餐厅: {power_result['restaurant_name']} (Lv.{power_result['restaurant_level']})")
        print(f"基础厨力: {power_result['total_base']}")
        print(f"装备加成: +{power_result['equipment_bonus']}")
        print(f"总厨力: {power_result['total_with_equip']}")
        print("属性详情:")
        for attr, info in power_result['attributes'].items():
            print(f"  {info['name']}: {info['base']}+{info['equipment_add']} = {info['total']}")
    
    # 测试获取装备摘要
    print("\n--- 3. 获取装备信息摘要 ---")
    equip_result = user_card_action.get_equipment_summary()
    if equip_result.get("success"):
        print(f"装备数量: {equip_result['equipment_count']}")
        for equip in equip_result['equipment_list']:
            print(f"  {equip['part_name']}: {equip['name']} (+{equip['strengthen_level']} {equip['strengthen_name']})")
    
    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
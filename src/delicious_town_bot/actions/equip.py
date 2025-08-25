"""
装备管理模块
用于处理装备查询、宝石镶嵌、卸下、打孔等操作
"""
import time
from typing import Dict, Any, List, Optional, Tuple
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class EquipAction(BaseAction):
    """
    装备操作类，处理装备详情查询和宝石管理
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res&m=Equip"
        super().__init__(key=key, cookie=cookie, base_url=base_url)

    def get_equipment_detail(self, equip_id: str) -> Dict[str, Any]:
        """
        获取装备详细信息（包括镶嵌的宝石）
        
        Args:
            equip_id: 装备ID
            
        Returns:
            Dict包含装备详情:
            {
                "success": bool,
                "equipment": dict,  # 装备基础信息
                "gems": dict,       # 镶嵌的宝石信息
                "holes": dict,      # 孔位信息
                "message": str
            }
        """
        print(f"[*] 正在获取装备详情 (ID: {equip_id})...")
        
        try:
            response = self.post(
                action_path="a=equip_info",
                data={"key": self.key, "id": equip_id}
            )
            
            if response.get("status"):
                equipment_data = response.get("data", {})
                
                # 调试：打印原始数据
                print(f"[Debug] 装备原始数据: {equipment_data}")
                
                # 解析装备基础信息
                equipment = {
                    "id": equipment_data.get("id"),
                    "name": equipment_data.get("goods_name"),
                    "part_type": equipment_data.get("part_type"),
                    "level": equipment_data.get("level"),
                    "strengthen_level": equipment_data.get("strengthen_num"),
                    "strengthen_name": equipment_data.get("strengthen_name"),
                    "is_equipped": equipment_data.get("is_use") == "1",
                    "holes_total": int(equipment_data.get("hole", 0)),
                    "properties": {
                        "fire": int(equipment_data.get("fire", 0)),
                        "cooking": int(equipment_data.get("cooking", 0)),
                        "sword": int(equipment_data.get("sword", 0)),
                        "season": int(equipment_data.get("season", 0)),
                        "originality": int(equipment_data.get("originality", 0)),
                        "luck": int(equipment_data.get("luck", 0))
                    },
                    "property_adds": {
                        "fire": int(equipment_data.get("fire_add", 0)),
                        "cooking": int(equipment_data.get("cooking_add", 0)),
                        "sword": int(equipment_data.get("sword_add", 0)),
                        "season": int(equipment_data.get("season_add", 0)),
                        "originality": int(equipment_data.get("originality_add", 0)),
                        "luck": int(equipment_data.get("luck_add", 0))
                    },
                    "hole_adds": {
                        "fire": int(equipment_data.get("fire_hole_add", 0)),
                        "cooking": int(equipment_data.get("cooking_hole_add", 0)),
                        "sword": int(equipment_data.get("sword_hole_add", 0)),
                        "season": int(equipment_data.get("season_hole_add", 0)),
                        "originality": int(equipment_data.get("originality_hole_add", 0)),
                        "luck": int(equipment_data.get("luck_hole_add", 0))
                    }
                }
                
                # 解析镶嵌的宝石信息
                gems = {}
                hole_list = equipment_data.get("hole_list", {})
                
                # 处理hole_list可能是字典或列表的情况
                if isinstance(hole_list, dict):
                    # hole_list是字典的情况
                    for hole_id, gem_info in hole_list.items():
                        if gem_info and isinstance(gem_info, dict) and gem_info.get("goods_name"):  # 确保gem_info有效且有宝石名称
                            gems[hole_id] = {
                                "hole_id": gem_info.get("id"),
                                "gem_code": gem_info.get("goods_code"),
                                "gem_name": gem_info.get("goods_name"),
                                "properties": {
                                    "fire": int(gem_info.get("fire", 0)),
                                    "cooking": int(gem_info.get("cooking", 0)),
                                    "sword": int(gem_info.get("sword", 0)),
                                    "season": int(gem_info.get("season", 0)),
                                    "originality": int(gem_info.get("originality", 0)),
                                    "luck": int(gem_info.get("luck", 0))
                                },
                                "position": int(gem_info.get("num", hole_id))
                            }
                elif isinstance(hole_list, list):
                    # hole_list是列表的情况
                    for i, gem_info in enumerate(hole_list):
                        if gem_info and isinstance(gem_info, dict) and gem_info.get("goods_name"):  # 确保gem_info有效且有宝石名称
                            hole_id = str(i + 1)  # 使用位置作为hole_id
                            gems[hole_id] = {
                                "hole_id": gem_info.get("id"),
                                "gem_code": gem_info.get("goods_code"),
                                "gem_name": gem_info.get("goods_name"),
                                "properties": {
                                    "fire": int(gem_info.get("fire", 0)),
                                    "cooking": int(gem_info.get("cooking", 0)),
                                    "sword": int(gem_info.get("sword", 0)),
                                    "season": int(gem_info.get("season", 0)),
                                    "originality": int(gem_info.get("originality", 0)),
                                    "luck": int(gem_info.get("luck", 0))
                                },
                                "position": int(gem_info.get("num", i + 1))
                            }
                
                # 计算孔位状态
                holes = {
                    "total": equipment["holes_total"],
                    "used": len(gems),
                    "available": equipment["holes_total"] - len(gems),
                    "details": gems
                }
                
                print(f"[+] 装备详情获取成功: {equipment['name']}")
                return {
                    "success": True,
                    "equipment": equipment,
                    "gems": gems,
                    "holes": holes,
                    "message": f"装备详情获取成功: {equipment['name']}",
                    "raw_response": response  # 添加原始响应数据
                }
            else:
                error_msg = response.get("msg", "获取装备详情失败")
                print(f"[!] {error_msg}")
                return {
                    "success": False,
                    "equipment": {},
                    "gems": {},
                    "holes": {},
                    "message": error_msg
                }
                
        except Exception as e:
            print(f"[Error] 获取装备详情异常: {e}")
            return {
                "success": False,
                "equipment": {},
                "gems": {},
                "holes": {},
                "message": f"获取装备详情异常: {str(e)}"
            }

    def remove_gem(self, equip_id: str, hole_id: str) -> Dict[str, Any]:
        """
        卸下装备上的宝石
        
        Args:
            equip_id: 装备ID
            hole_id: 孔位ID
            
        Returns:
            Dict包含操作结果
        """
        print(f"[*] 正在卸下宝石 (装备ID: {equip_id}, 孔位ID: {hole_id})...")
        
        try:
            response = self.post(
                action_path="a=debus_stone",
                data={
                    "key": self.key,
                    "equip_id": equip_id,
                    "hole_id": hole_id
                }
            )
            
            if response.get("status"):
                msg = response.get("msg", "宝石卸下成功")
                print(f"[+] {msg}")
                return {
                    "success": True,
                    "message": msg
                }
            else:
                error_msg = response.get("msg", "卸下宝石失败")
                print(f"[!] {error_msg}")
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except Exception as e:
            print(f"[Error] 卸下宝石异常: {e}")
            return {
                "success": False,
                "message": f"卸下宝石异常: {str(e)}"
            }

    def install_gem(self, equip_id: str, hole_id: str, stone_code: str) -> Dict[str, Any]:
        """
        镶嵌宝石到装备
        
        Args:
            equip_id: 装备ID
            hole_id: 孔位ID
            stone_code: 宝石代码
            
        Returns:
            Dict包含操作结果
        """
        print(f"[*] 正在镶嵌宝石 (装备ID: {equip_id}, 孔位ID: {hole_id}, 宝石代码: {stone_code})...")
        
        try:
            response = self.post(
                action_path="a=add_stone",
                data={
                    "key": self.key,
                    "equip_id": equip_id,
                    "hole_id": hole_id,
                    "stone_code": stone_code
                }
            )
            
            if response.get("status"):
                msg = response.get("msg", "宝石镶嵌成功")
                print(f"[+] {msg}")
                return {
                    "success": True,
                    "message": msg
                }
            else:
                error_msg = response.get("msg", "镶嵌宝石失败")
                print(f"[!] {error_msg}")
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except Exception as e:
            print(f"[Error] 镶嵌宝石异常: {e}")
            return {
                "success": False,
                "message": f"镶嵌宝石异常: {str(e)}"
            }

    def add_hole(self, equip_id: str, num: int = 1) -> Dict[str, Any]:
        """
        为装备打孔
        
        Args:
            equip_id: 装备ID
            num: 打孔数量
            
        Returns:
            Dict包含操作结果
        """
        print(f"[*] 正在为装备打孔 (装备ID: {equip_id}, 数量: {num})...")
        
        try:
            response = self.post(
                action_path="a=add_hole",
                data={
                    "key": self.key,
                    "id": equip_id,
                    "num": str(num)
                }
            )
            
            if response.get("status"):
                msg = response.get("msg", f"装备打孔成功，增加{num}个孔位")
                print(f"[+] {msg}")
                return {
                    "success": True,
                    "message": msg,
                    "holes_added": num
                }
            else:
                error_msg = response.get("msg", "装备打孔失败")
                print(f"[!] {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "holes_added": 0
                }
                
        except Exception as e:
            print(f"[Error] 装备打孔异常: {e}")
            return {
                "success": False,
                "message": f"装备打孔异常: {str(e)}",
                "holes_added": 0
            }

    def buy_drill_stone(self, num: int = 1) -> Dict[str, Any]:
        """
        购买打孔石
        
        Args:
            num: 购买数量
            
        Returns:
            Dict包含购买结果
        """
        print(f"[*] 正在购买打孔石 (数量: {num})...")
        
        try:
            # 切换到Shop模块购买打孔石 (goods_id=14)
            from src.delicious_town_bot.actions.shop import ShopAction
            shop_action = ShopAction(key=self.key, cookie=self.http_client.cookies)
            
            # 购买打孔石
            result = shop_action.buy_item(goods_id=14, num=num)
            
            if result.get("success"):
                msg = f"成功购买{num}个打孔石"
                print(f"[+] {msg}")
                return {
                    "success": True,
                    "message": msg,
                    "quantity": num
                }
            else:
                error_msg = result.get("message", "购买打孔石失败")
                print(f"[!] {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "quantity": 0
                }
                
        except Exception as e:
            print(f"[Error] 购买打孔石异常: {e}")
            return {
                "success": False,
                "message": f"购买打孔石异常: {str(e)}",
                "quantity": 0
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

    equip_action = EquipAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "=" * 20 + " 装备管理功能测试 " + "=" * 20)

    # 测试获取装备详情
    print("\n--- 1. 测试获取装备详情 ---")
    # 需要提供一个真实的装备ID进行测试
    test_equip_id = "632431"  # 示例装备ID
    detail_result = equip_action.get_equipment_detail(test_equip_id)
    print(f"获取装备详情结果: {detail_result}")
    
    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
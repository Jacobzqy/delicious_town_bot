"""
商店购买模块
用于购买游戏商店中的物品，包括装备、道具等
"""
import time
from typing import Dict, Any, Optional, List, Tuple
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError
from src.delicious_town_bot.data.specialty_food_packs import (
    SpecialtyFoodPack, get_pack_by_recipe_name, get_pack_by_goods_id,
    get_all_recipe_names, validate_purchase, SPECIALTY_FOOD_PACKS
)


class ShopAction(BaseAction):
    """
    商店购买操作类，处理各种商店购买功能
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key=key, cookie=cookie, base_url=base_url)
        # 更新 Referer
        self.http_client.headers.update({
            'Referer': 'http://117.72.123.195/'
        })

    def buy_item(self, goods_id: int, num: int = 1) -> Dict[str, Any]:
        """
        购买商店物品
        
        Args:
            goods_id: 商品ID
            num: 购买数量
            
        Returns:
            Dict包含购买结果:
            {
                "success": bool,
                "message": str,
                "data": dict  # 如果有返回数据
            }
        """
        print(f"[*] 正在尝试购买商品 (ID: {goods_id}, 数量: {num})...")
        
        action_path = "m=Shop&a=buy"
        payload = {
            "goods_id": str(goods_id),
            "num": str(num)
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            # 检查响应状态
            if response_data.get('status'):
                message = response_data.get('msg', '购买成功')
                print(f"[+] 购买成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "data": response_data.get('data', {})
                }
            else:
                error_msg = response_data.get('msg', '购买失败')
                print(f"[!] 购买失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "data": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 购买商品失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "data": {}
            }

    def buy_novice_equipment_daily(self) -> Dict[str, Any]:
        """
        每日购买见习装备 (见习之铲、刀、锅各4次)
        
        见习装备goods_id:
        - 11: 见习之铲
        - 12: 见习之刀  
        - 13: 见习之锅
        
        Returns:
            Dict包含购买结果汇总
        """
        print(f"[*] 开始每日见习装备购买...")
        
        # 见习装备配置
        novice_equipment = [
            {"goods_id": 11, "name": "见习之铲"},
            {"goods_id": 12, "name": "见习之刀"},
            {"goods_id": 13, "name": "见习之锅"}
        ]
        
        results = {
            "success": True,
            "total_purchased": 0,
            "equipment_results": [],
            "failed_purchases": [],
            "message": ""
        }
        
        for equipment in novice_equipment:
            goods_id = equipment["goods_id"]
            name = equipment["name"]
            
            print(f"[*] 正在购买 {name} (ID: {goods_id}) - 4次...")
            
            equipment_result = {
                "name": name,
                "goods_id": goods_id,
                "success_count": 0,
                "failed_count": 0,
                "messages": []
            }
            
            # 购买4次，每次1个
            for i in range(4):
                print(f"[*] 第 {i+1}/4 次购买 {name}...")
                
                purchase_result = self.buy_item(goods_id, num=1)
                
                if purchase_result["success"]:
                    equipment_result["success_count"] += 1
                    results["total_purchased"] += 1
                    equipment_result["messages"].append(f"第{i+1}次: ✅ {purchase_result['message']}")
                else:
                    equipment_result["failed_count"] += 1
                    equipment_result["messages"].append(f"第{i+1}次: ❌ {purchase_result['message']}")
                    results["failed_purchases"].append({
                        "equipment": name,
                        "attempt": i+1,
                        "error": purchase_result["message"]
                    })
                
                # 间隔1秒避免请求过快
                if i < 3:  # 最后一次不需要等待
                    time.sleep(1)
            
            results["equipment_results"].append(equipment_result)
            
            # 设备之间间隔2秒
            if equipment != novice_equipment[-1]:  # 不是最后一个设备
                time.sleep(2)
        
        # 生成总结消息
        total_attempts = len(novice_equipment) * 4
        success_rate = (results["total_purchased"] / total_attempts * 100) if total_attempts > 0 else 0
        
        if results["total_purchased"] == total_attempts:
            results["message"] = f"✅ 每日见习装备购买完成！成功购买 {results['total_purchased']}/{total_attempts} 件装备"
            results["success"] = True
        else:
            failed_count = total_attempts - results["total_purchased"]
            results["message"] = f"⚠️ 每日见习装备购买完成，成功 {results['total_purchased']} 件，失败 {failed_count} 件 (成功率: {success_rate:.1f}%)"
            results["success"] = results["total_purchased"] > 0  # 至少购买成功一件就算部分成功
        
        print(f"[+] {results['message']}")
        return results

    def get_shop_info(self) -> Dict[str, Any]:
        """
        获取商店信息
        
        Returns:
            商店信息
        """
        print(f"[*] 正在获取商店信息...")
        
        action_path = "m=Shop&a=index"
        
        try:
            response_data = self.get(action_path)
            
            if response_data.get('status'):
                data = response_data.get('data', {})
                print(f"[+] 商店信息获取成功")
                return {
                    "success": True,
                    "message": "获取商店信息成功",
                    "data": data
                }
            else:
                error_msg = response_data.get('msg', '获取商店信息失败')
                print(f"[Error] {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "data": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取商店信息失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "data": {}
            }

    def batch_buy_item(self, goods_id: int, times: int, interval: float = 1.0) -> Dict[str, Any]:
        """
        批量购买指定物品（每次购买1个，重复多次）
        
        Args:
            goods_id: 商品ID
            times: 购买次数
            interval: 每次购买间隔（秒）
            
        Returns:
            批量购买结果
        """
        print(f"[*] 开始批量购买商品 (ID: {goods_id}, {times}次)...")
        
        results = {
            "success": True,
            "goods_id": goods_id,
            "total_attempts": times,
            "success_count": 0,
            "failed_count": 0,
            "purchase_details": [],
            "message": ""
        }
        
        for i in range(times):
            print(f"[*] 第 {i+1}/{times} 次购买...")
            
            purchase_result = self.buy_item(goods_id, num=1)
            
            purchase_detail = {
                "attempt": i+1,
                "success": purchase_result["success"],
                "message": purchase_result["message"]
            }
            
            if purchase_result["success"]:
                results["success_count"] += 1
                print(f"[+] 第{i+1}次购买成功")
            else:
                results["failed_count"] += 1
                print(f"[!] 第{i+1}次购买失败: {purchase_result['message']}")
            
            results["purchase_details"].append(purchase_detail)
            
            # 间隔等待
            if i < times - 1:  # 最后一次不需要等待
                time.sleep(interval)
        
        # 生成总结
        success_rate = (results["success_count"] / times * 100) if times > 0 else 0
        if results["success_count"] == times:
            results["message"] = f"✅ 批量购买完成！成功购买 {results['success_count']}/{times} 次"
            results["success"] = True
        else:
            results["message"] = f"⚠️ 批量购买完成，成功 {results['success_count']} 次，失败 {results['failed_count']} 次 (成功率: {success_rate:.1f}%)"
            results["success"] = results["success_count"] > 0
        
        print(f"[+] {results['message']}")
        return results

    def buy_intermediate_equipment(self) -> Dict[str, Any]:
        """
        购买中厨装备 (中厨之铲、刀、锅各1件)
        
        中厨装备goods_id:
        - 21: 中厨之铲
        - 22: 中厨之锅  
        - 23: 中厨之刀
        
        Returns:
            Dict包含购买结果汇总
        """
        print(f"[*] 开始购买中厨装备...")
        
        # 中厨装备配置
        intermediate_equipment = [
            {"goods_id": 21, "name": "中厨之铲"},
            {"goods_id": 22, "name": "中厨之锅"},
            {"goods_id": 23, "name": "中厨之刀"}
        ]
        
        results = {
            "success": True,
            "total_purchased": 0,
            "equipment_results": [],
            "failed_purchases": [],
            "message": ""
        }
        
        for equipment in intermediate_equipment:
            goods_id = equipment["goods_id"]
            name = equipment["name"]
            
            print(f"[*] 正在购买 {name} (ID: {goods_id})...")
            
            purchase_result = self.buy_item(goods_id, num=1)
            
            equipment_result = {
                "name": name,
                "goods_id": goods_id,
                "success": purchase_result["success"],
                "message": purchase_result["message"]
            }
            
            if purchase_result["success"]:
                results["total_purchased"] += 1
                print(f"[+] {name} 购买成功")
            else:
                results["failed_purchases"].append({
                    "equipment": name,
                    "error": purchase_result["message"]
                })
                print(f"[!] {name} 购买失败: {purchase_result['message']}")
            
            results["equipment_results"].append(equipment_result)
            
            # 设备之间间隔1秒
            if equipment != intermediate_equipment[-1]:  # 不是最后一个设备
                time.sleep(1)
        
        # 生成总结消息
        total_attempts = len(intermediate_equipment)
        if results["total_purchased"] == total_attempts:
            results["message"] = f"✅ 中厨装备购买完成！成功购买 {results['total_purchased']}/{total_attempts} 件装备"
            results["success"] = True
        else:
            failed_count = total_attempts - results["total_purchased"]
            results["message"] = f"⚠️ 中厨装备购买完成，成功 {results['total_purchased']} 件，失败 {failed_count} 件"
            results["success"] = results["total_purchased"] > 0
        
        print(f"[+] {results['message']}")
        return results

    def buy_gem_refining_materials(self) -> Dict[str, Any]:
        """
        购买精炼宝石所需材料（智慧原石+原石精华）
        
        宝石材料goods_id:
        - 15: 智慧原石(1星) - 10000金币
        - 78: 原石精华 - 价格待确认
        
        Returns:
            Dict包含购买结果汇总
        """
        print(f"[*] 开始购买精炼宝石材料...")
        
        # 宝石材料配置
        gem_materials = [
            {"goods_id": 15, "name": "智慧原石(1星)", "price": 10000},
            {"goods_id": 78, "name": "原石精华", "price": "未知"}
        ]
        
        results = {
            "success": True,
            "total_purchased": 0,
            "material_results": [],
            "failed_purchases": [],
            "total_cost": 0,
            "message": ""
        }
        
        for material in gem_materials:
            goods_id = material["goods_id"]
            name = material["name"]
            estimated_price = material["price"]
            
            print(f"[*] 正在购买 {name} (ID: {goods_id})...")
            
            purchase_result = self.buy_item(goods_id, num=1)
            
            material_result = {
                "name": name,
                "goods_id": goods_id,
                "success": purchase_result["success"],
                "message": purchase_result["message"]
            }
            
            if purchase_result["success"]:
                results["total_purchased"] += 1
                
                # 尝试从消息中提取金币消耗
                message = purchase_result["message"]
                if "金币-" in message:
                    try:
                        import re
                        cost_match = re.search(r"金币-(\d+)", message)
                        if cost_match:
                            cost = int(cost_match.group(1))
                            results["total_cost"] += cost
                            material_result["cost"] = cost
                    except:
                        pass
                
                print(f"[+] {name} 购买成功")
            else:
                results["failed_purchases"].append({
                    "material": name,
                    "error": purchase_result["message"]
                })
                print(f"[!] {name} 购买失败: {purchase_result['message']}")
            
            results["material_results"].append(material_result)
            
            # 材料之间间隔1秒
            if material != gem_materials[-1]:  # 不是最后一个材料
                time.sleep(1)
        
        # 生成总结消息
        total_attempts = len(gem_materials)
        if results["total_purchased"] == total_attempts:
            cost_info = f"，消耗 {results['total_cost']} 金币" if results["total_cost"] > 0 else ""
            results["message"] = f"✅ 精炼宝石材料购买完成！成功购买 {results['total_purchased']}/{total_attempts} 种材料{cost_info}"
            results["success"] = True
        else:
            failed_count = total_attempts - results["total_purchased"]
            results["message"] = f"⚠️ 精炼宝石材料购买完成，成功 {results['total_purchased']} 种，失败 {failed_count} 种"
            results["success"] = results["total_purchased"] > 0
        
        print(f"[+] {results['message']}")
        return results

    def buy_specialty_food_pack(self, recipe_name: str) -> Dict[str, Any]:
        """
        购买特色菜食材礼包
        
        Args:
            recipe_name: 特色菜名称（如"薏米膳继"）
            
        Returns:
            Dict包含购买结果
        """
        print(f"[*] 正在购买特色菜食材礼包: {recipe_name}")
        
        # 获取对应的礼包信息
        pack = get_pack_by_recipe_name(recipe_name)
        if not pack:
            error_msg = f"未找到特色菜 '{recipe_name}' 对应的食材礼包"
            print(f"[Error] {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "data": {}
            }
        
        print(f"[*] 礼包信息: {pack.name} (ID: {pack.goods_id}, 价格: {pack.price}金币)")
        
        # 购买礼包
        purchase_result = self.buy_item(pack.goods_id, num=1)
        
        if purchase_result["success"]:
            print(f"[+] 特色菜食材礼包购买成功: {pack.name}")
            return {
                "success": True,
                "message": purchase_result["message"],
                "pack": pack.to_dict(),
                "data": purchase_result["data"]
            }
        else:
            print(f"[!] 特色菜食材礼包购买失败: {purchase_result['message']}")
            return {
                "success": False,
                "message": purchase_result["message"],
                "pack": pack.to_dict(),
                "data": {}
            }

    def open_specialty_food_pack(self, pack_code: str) -> Dict[str, Any]:
        """
        打开特色菜食材礼包
        
        Args:
            pack_code: 礼包物品代码（如"10620"）
            
        Returns:
            Dict包含打开结果
        """
        print(f"[*] 正在打开特色菜食材礼包 (代码: {pack_code})")
        
        action_path = "m=Depot&a=use_step_1"
        payload = {
            "code": str(pack_code)
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            if response_data.get('status'):
                message = response_data.get('msg', '礼包打开成功')
                print(f"[+] 礼包打开成功: {message}")
                
                # 解析获得的食材信息
                ingredients_info = self._parse_pack_rewards(message)
                
                return {
                    "success": True,
                    "message": message,
                    "ingredients": ingredients_info,
                    "data": response_data.get('data', {})
                }
            else:
                error_msg = response_data.get('msg', '礼包打开失败')
                print(f"[!] 礼包打开失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "ingredients": [],
                    "data": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 打开礼包失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "ingredients": [],
                "data": {}
            }

    def buy_and_open_specialty_pack(self, recipe_name: str) -> Dict[str, Any]:
        """
        一键购买并打开特色菜食材礼包
        
        Args:
            recipe_name: 特色菜名称
            
        Returns:
            Dict包含完整操作结果
        """
        print(f"[*] 开始一键购买并打开特色菜食材礼包: {recipe_name}")
        
        results = {
            "success": False,
            "recipe_name": recipe_name,
            "purchase_result": {},
            "open_result": {},
            "total_ingredients": [],
            "message": ""
        }
        
        # 第一步：购买礼包
        purchase_result = self.buy_specialty_food_pack(recipe_name)
        results["purchase_result"] = purchase_result
        
        if not purchase_result["success"]:
            results["message"] = f"购买礼包失败: {purchase_result['message']}"
            return results
        
        print(f"[+] 礼包购买成功，等待2秒后打开礼包...")
        time.sleep(2)  # 等待一下确保礼包进入背包
        
        # 第二步：获取礼包代码并打开
        pack = purchase_result.get("pack", {})
        pack_code = pack.get("pack_code")
        
        if not pack_code:
            results["message"] = "无法获取礼包代码，无法自动打开"
            return results
        
        open_result = self.open_specialty_food_pack(pack_code)
        results["open_result"] = open_result
        
        if open_result["success"]:
            results["success"] = True
            results["total_ingredients"] = open_result.get("ingredients", [])
            results["message"] = f"✅ {recipe_name} 食材礼包购买并打开成功！获得食材: {len(results['total_ingredients'])} 种"
        else:
            results["message"] = f"礼包购买成功但打开失败: {open_result['message']}"
        
        print(f"[+] {results['message']}")
        return results

    def _parse_pack_rewards(self, reward_message: str) -> List[Dict[str, Any]]:
        """
        解析礼包打开后的奖励信息
        
        Args:
            reward_message: 奖励消息（如"获得食材:薏仁x3<br>糙米x3<br>枸杞x3<br>"）
            
        Returns:
            List[Dict]: 食材信息列表
        """
        ingredients = []
        
        try:
            # 分割消息，查找食材信息
            if "获得食材:" in reward_message:
                # 按<br>分割各种食材
                ingredient_lines = reward_message.split("<br>")
                
                for line in ingredient_lines:
                    if "x" in line and line.strip():
                        try:
                            # 解析 "薏仁x3" 格式
                            if ":" in line:
                                line = line.split(":")[-1]  # 去掉前缀
                            
                            parts = line.strip().split("x")
                            if len(parts) == 2:
                                name = parts[0].strip()
                                count = int(parts[1].strip())
                                
                                if name and count > 0:
                                    ingredients.append({
                                        "name": name,
                                        "count": count
                                    })
                        except:
                            continue
                            
        except Exception as e:
            print(f"[Warning] 解析礼包奖励失败: {e}")
        
        return ingredients

    def batch_buy_specialty_packs(self, recipe_names: List[str]) -> Dict[str, Any]:
        """
        批量购买并打开特色菜食材礼包
        
        Args:
            recipe_names: 特色菜名称列表
            
        Returns:
            Dict包含批量操作结果
        """
        print(f"[*] 开始批量购买特色菜食材礼包: {recipe_names}")
        
        results = {
            "success": True,
            "total_recipes": len(recipe_names),
            "success_count": 0,
            "failed_count": 0,
            "pack_results": [],
            "all_ingredients": [],
            "message": ""
        }
        
        for i, recipe_name in enumerate(recipe_names):
            print(f"[*] 处理第 {i+1}/{len(recipe_names)} 个食谱: {recipe_name}")
            
            pack_result = self.buy_and_open_specialty_pack(recipe_name)
            results["pack_results"].append(pack_result)
            
            if pack_result["success"]:
                results["success_count"] += 1
                results["all_ingredients"].extend(pack_result.get("total_ingredients", []))
            else:
                results["failed_count"] += 1
            
            # 礼包之间间隔3秒
            if i < len(recipe_names) - 1:
                time.sleep(3)
        
        # 生成总结
        if results["success_count"] == results["total_recipes"]:
            results["message"] = f"✅ 批量购买完成！成功处理 {results['success_count']}/{results['total_recipes']} 个食谱"
            results["success"] = True
        else:
            results["message"] = f"⚠️ 批量购买完成，成功 {results['success_count']} 个，失败 {results['failed_count']} 个"
            results["success"] = results["success_count"] > 0
        
        print(f"[+] {results['message']}")
        return results

    def get_available_specialty_packs(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的特色菜食材礼包信息
        
        Returns:
            List[Dict]: 所有礼包信息
        """
        return [pack.to_dict() for pack in SPECIALTY_FOOD_PACKS]

    def buy_essence_material(self, essence_type: str, num: int = 1) -> Dict[str, Any]:
        """
        购买精华材料
        
        Args:
            essence_type: 精华类型 ("原石精华", "魔石精华", 等)
            num: 购买数量
            
        Returns:
            Dict包含购买结果
        """
        # 精华材料goods_id映射（根据提供的数据）
        essence_goods_mapping = {
            "原石精华": 78,   # goods_id: 78, price: 10000
            "魔石精华": 79,   # goods_id: 79, price: 20000
            "灵石精华": 80,   # goods_id: 80, price: 50000
            "神石精华": 81,   # goods_id: 81, price: 100000
            "原玉精华": 183,  # goods_id: 183, price: 6000000
            "魔玉精华": 184,  # goods_id: 184, price: 12000000
            # "灵玉精华": ???,  # 暂时未知goods_id
            # "神玉精华": ???   # 暂时未知goods_id
        }
        
        if essence_type not in essence_goods_mapping:
            return {
                "success": False,
                "message": f"不支持购买 {essence_type}，可能是未知的精华类型或暂未实现"
            }
        
        goods_id = essence_goods_mapping[essence_type]
        print(f"[*] 正在购买 {essence_type} x{num} (goods_id: {goods_id})...")
        
        # 调用通用购买方法
        return self.buy_item(goods_id=goods_id, num=num)

    def buy_all_essence_materials(self, quantities: Dict[str, int]) -> Dict[str, Any]:
        """
        批量购买多种精华材料
        
        Args:
            quantities: 精华类型和数量的映射 {"原石精华": 5, "魔石精华": 2}
            
        Returns:
            Dict包含批量购买结果
        """
        print(f"[*] 开始批量购买 {len(quantities)} 种精华材料...")
        
        results = {
            "success": True,
            "total_items": len(quantities),
            "success_count": 0,
            "failed_count": 0,
            "purchase_details": [],
            "total_cost": 0,
            "message": ""
        }
        
        # 精华材料价格映射
        essence_prices = {
            "原石精华": 10000,
            "魔石精华": 20000,
            "灵石精华": 50000,
            "神石精华": 100000,
            "原玉精华": 6000000,
            "魔玉精华": 12000000
        }
        
        for essence_type, quantity in quantities.items():
            if quantity <= 0:
                continue
                
            print(f"[*] 购买 {essence_type} x{quantity}...")
            purchase_result = self.buy_essence_material(essence_type, quantity)
            
            # 计算成本
            item_cost = essence_prices.get(essence_type, 0) * quantity
            
            purchase_detail = {
                "essence_type": essence_type,
                "quantity": quantity,
                "success": purchase_result.get("success", False),
                "message": purchase_result.get("message", ""),
                "cost": item_cost if purchase_result.get("success") else 0
            }
            
            results["purchase_details"].append(purchase_detail)
            
            if purchase_result.get("success"):
                results["success_count"] += 1
                results["total_cost"] += item_cost
                print(f"[+] {essence_type} x{quantity} 购买成功，花费 {item_cost} 金币")
            else:
                results["failed_count"] += 1
                results["success"] = False
                error_msg = purchase_result.get("message", "未知错误")
                print(f"[!] {essence_type} x{quantity} 购买失败: {error_msg}")
            
            # 购买间隔，避免请求过快
            time.sleep(0.5)
        
        # 生成总结消息
        if results["failed_count"] == 0:
            results["message"] = f"✅ 批量购买完成！成功购买 {results['success_count']} 种精华材料，总花费 {results['total_cost']} 金币"
            results["success"] = True
        else:
            results["message"] = f"⚠️ 批量购买完成，成功 {results['success_count']} 种，失败 {results['failed_count']} 种，总花费 {results['total_cost']} 金币"
            results["success"] = results["success_count"] > 0
        
        print(f"[+] {results['message']}")
        return results


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

    shop_action = ShopAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "=" * 20 + " 商店购买功能测试 " + "=" * 20)

    # 测试获取商店信息
    print("\n--- 1. 获取商店信息 ---")
    shop_info = shop_action.get_shop_info()
    if shop_info.get("success"):
        print("商店信息获取成功")
    
    # 测试单次购买
    print("\n--- 2. 测试单次购买见习之铲 ---")
    single_result = shop_action.buy_item(goods_id=11, num=1)
    print(f"购买结果: {single_result}")
    
    # 测试每日见习装备购买（可以注释掉避免实际购买）
    print("\n--- 3. 测试每日见习装备购买 ---")
    print("注意：这会实际购买装备，确认后取消注释以下代码")
    # daily_result = shop_action.buy_novice_equipment_daily()
    # print(f"每日购买结果: {daily_result}")
    
    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
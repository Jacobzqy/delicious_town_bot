import re
import os
import time
import json
from dotenv import load_dotenv
from typing import Tuple, Dict, Any, Union, Optional, List

# 确保能正确导入基类和自定义异常
# 这个路径假定 actions 文件夹和 utils 在同一个父目录(src/delicious_town_bot)下
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class RestaurantActions(BaseAction):
    """封装所有与餐厅管理、升级、维护相关的游戏操作。"""

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        """
        初始化餐厅操作类。
        使用通用的 g=Res 作为 base_url，以便调用不同的模块(m=Index, m=Seat, m=Isoc)。
        """
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key, base_url, cookie)

    # --- 餐厅状态与基础维护 ---

    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        获取餐厅的核心状态，包括油量和特色菜数量。
        :return: 包含状态信息的字典，或失败时返回 None。
        """
        print("[*] 正在获取餐厅状态...")
        try:
            # 调用 m=Index&a=index
            response = self.post(action_path="m=Index&a=index")
            
            # 安全获取data字段，确保它是字典类型
            raw_data = response.get("data", {})
            if not isinstance(raw_data, dict):
                print(f"[Warning] API返回的data字段不是字典类型: {type(raw_data)}, 值: {raw_data}")
                # 如果data不是字典，使用空字典作为fallback
                d = {}
            else:
                d = raw_data
            
            # 安全获取嵌套字段
            bottle_info = d.get("bottle", {}) if isinstance(d.get("bottle"), dict) else {}
            specialities_info = d.get("specialities_cook", {}) if isinstance(d.get("specialities_cook"), dict) else {}
            
            # 从res对象中获取金币信息
            res_info = d.get("res", {}) if isinstance(d.get("res"), dict) else {}
            
            status = {
                "oil_current": int(bottle_info.get("num", 0)),
                "oil_max": int(bottle_info.get("max_num", 0)),
                "special_dish_remaining": int(specialities_info.get("num", 0)),
                "gold": int(res_info.get("gold", 0)),  # 从res字段获取金币数量
                "level": int(res_info.get("level", 0)),  # 餐厅等级
                "star": int(res_info.get("star", 0)),   # 餐厅星级
                "prestige": int(res_info.get("prestige_num", 0))  # 声望值
            }
            print(
                f"[Info] 获取状态成功: 油量 {status['oil_current']}/{status['oil_max']}, 特色菜剩余 {status['special_dish_remaining']}")
            return status
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 获取餐厅状态失败: {e}")
            return None

    def visit_shop(self) -> Dict[str, Any]:
        """
        巡店 - 获取自己餐厅的所有座位信息，完成每日巡店任务
        
        通过分页获取所有类型的座位信息（type=1顾客, type=0空位, type=2挑剔, type=3白食, type=4蟑螂）
        
        Returns:
            Dict包含巡店结果:
            {
                "success": bool,
                "message": str,
                "seat_info": dict  # 座位信息
            }
        """
        print("[*] 正在执行巡店任务...")
        try:
            all_seats = []
            
            # 遍历所有座位类型：0=空位, 1=顾客, 2=挑剔顾客, 3=吃白食, 4=蟑螂
            seat_types = [0, 1, 2, 3, 4]
            
            for seat_type in seat_types:
                print(f"[*] 获取类型 {seat_type} 的座位信息...")
                page = 1
                
                while page <= 20:  # 最大20页防止无限循环
                    payload = {
                        "key": self.key,
                        "page": str(page),
                        "type": str(seat_type)
                    }
                    
                    try:
                        response = self.post(action_path="m=Seat&a=get_list", data=payload)
                        
                        if not response.get("status"):
                            print(f"[!] 类型 {seat_type} 第 {page} 页请求失败")
                            break
                        
                        page_data = response.get("data", [])
                        if not page_data or not isinstance(page_data, list):
                            print(f"[*] 类型 {seat_type} 第 {page} 页无数据，结束")
                            break
                        
                        # 检查是否有重复数据（分页结束标志）
                        new_seat_ids = {seat.get("id") for seat in page_data}
                        existing_seat_ids = {seat.get("id") for seat in all_seats}
                        
                        if new_seat_ids.issubset(existing_seat_ids):
                            print(f"[*] 类型 {seat_type} 第 {page} 页数据重复，分页结束")
                            break
                        
                        # 添加新座位数据
                        for seat in page_data:
                            if seat.get("id") not in existing_seat_ids:
                                all_seats.append(seat)
                        
                        print(f"[*] 类型 {seat_type} 第 {page} 页获取到 {len(page_data)} 个座位")
                        page += 1
                        
                        # 短暂延迟避免请求过快
                        import time
                        time.sleep(0.2)
                        
                    except Exception as e:
                        print(f"[!] 类型 {seat_type} 第 {page} 页请求异常: {e}")
                        break
            
            print(f"[*] 总共获取到 {len(all_seats)} 个座位信息")
            
            # 解析座位信息
            seat_info = {
                "total_seats": len(all_seats),
                "occupied_seats": 0,      # type=1 顾客
                "empty_seats": 0,         # type=0 空位
                "picky_seats": 0,         # type=2 挑剔顾客
                "dine_and_dash_seats": 0, # type=3 吃白食
                "roach_seats": 0,         # type=4 蟑螂
                "seats_detail": []
            }
            
            # 统计不同类型的座位
            for seat in all_seats:
                seat_detail = {
                    "id": seat.get("id", ""),
                    "seat_num": seat.get("seat_num", ""),
                    "type": seat.get("type", ""),
                    "type_name": seat.get("type_name", ""),
                    "status": seat.get("status", ""),
                    "end_time": seat.get("end_time", ""),
                    "cookbooks_code": seat.get("cookbooks_code", "")
                }
                seat_info["seats_detail"].append(seat_detail)
                
                seat_type = int(seat.get("type", 0))
                if seat_type == 1:      # 顾客
                    seat_info["occupied_seats"] += 1
                elif seat_type == 0:    # 空位
                    seat_info["empty_seats"] += 1
                elif seat_type == 2:    # 挑剔顾客
                    seat_info["picky_seats"] += 1
                elif seat_type == 3:    # 吃白食
                    seat_info["dine_and_dash_seats"] += 1
                elif seat_type == 4:    # 蟑螂
                    seat_info["roach_seats"] += 1
            
            # 构建成功消息
            details = []
            details.append(f"总座位: {seat_info['total_seats']}")
            if seat_info["occupied_seats"] > 0:
                details.append(f"顾客: {seat_info['occupied_seats']}")
            if seat_info["picky_seats"] > 0:
                details.append(f"挑剔: {seat_info['picky_seats']}")
            if seat_info["empty_seats"] > 0:
                details.append(f"空座: {seat_info['empty_seats']}")
            if seat_info["roach_seats"] > 0:
                details.append(f"蟑螂: {seat_info['roach_seats']}")
            if seat_info["dine_and_dash_seats"] > 0:
                details.append(f"白食: {seat_info['dine_and_dash_seats']}")
            
            success_message = f"✅ 巡店完成！{'; '.join(details)}"
            
            print(f"[+] {success_message}")
            return {
                "success": True,
                "message": success_message,
                "seat_info": seat_info
            }
            
        except (BusinessLogicError, ConnectionError, Exception) as e:
            error_message = f"巡店失败: {str(e)}"
            print(f"[Error] {error_message}")
            return {
                "success": False,
                "message": error_message,
                "seat_info": {}
            }

    def refill_oil(self) -> Tuple[bool, str]:
        """为油壶添满油。"""
        print("[*] 正在尝试添油...")
        try:
            # 调用 m=Index&a=add_bottle (GET请求)
            response = self.get(action_path="m=Index&a=add_bottle")
            msg = response.get("msg", "未知消息").replace("<br>", " / ")
            print(f"[Success] {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 添油失败: {e}")
            return False, str(e)

    def buy_facility(self, goods_id: int, num: int = 1) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        购买设施
        
        :param goods_id: 设施的物品ID (4=老鼠夹, 7=节油器)
        :param num: 购买数量，默认为1
        :return: (是否成功, 购买结果或错误信息)
        """
        print(f"[*] 正在尝试购买设施, ID: {goods_id}, 数量: {num}...")
        payload = {
            "key": self.key,
            "goods_id": str(goods_id),
            "num": str(num)
        }
        try:
            # 调用 m=Shop&a=buy
            response = self.post(action_path="m=Shop&a=buy", data=payload)
            msg = response.get("msg", "")
            print(f"[Success] {msg}")
            return True, {"message": msg, "goods_id": goods_id, "num": num}
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 购买设施 {goods_id} 失败: {e}")
            return False, str(e)

    def clear_facility(self, position: int) -> Tuple[bool, str]:
        """
        清空指定位置的设施
        
        :param position: 设施位置编号
        :return: (是否成功, 结果消息)
        """
        print(f"[*] 正在清空设施位置 {position}...")
        try:
            # 调用 m=Index&a=del_ins
            response = self.get(action_path=f"m=Index&a=del_ins&key={self.key}&num={position}")
            msg = response.get("msg", "清空成功")
            print(f"[Success] {msg}")
            return True, msg
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 清空设施位置 {position} 失败: {e}")
            return False, str(e)

    def place_facility(self, goods_code: int, position: int) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        在餐厅中摆放一个设施。

        :param goods_code: 设施的物品代码。
        :param position: 【已修正】要摆放到的设施位编号 (API字段为'num')。
        :return: (是否成功, 包含物品名称的字典或错误信息字符串)。
        """
        print(f"[*] 正在尝试摆放设施, Code: {goods_code}, 位置: {position}...")
        payload = {
            "goods_code": str(goods_code),
            "num": str(position)  # 后端接口要求字段名为'num'
        }
        try:
            # 调用 m=Index&a=add_ins
            response = self.post(action_path="m=Index&a=add_ins", data=payload)
            msg = response.get("msg", "")
            details = self._parse_place_facility_message(msg)
            print(f"[Success] {msg}")
            return True, details
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 摆放设施 {goods_code} 失败: {e}")
            return False, str(e)

    def _parse_place_facility_message(self, msg: str) -> Dict[str, Any]:
        """辅助方法，用于解析摆放设施成功的消息。"""
        # msg 格式: "摆放设施:[小仙宣传海报]成功!"
        match = re.search(r"摆放设施:\[(.*?)]成功!", msg)
        if match:
            return {"item_name": match.group(1)}
        return {"raw_message": msg}

    def complete_facility_placement_task(self) -> Dict[str, Any]:
        """
        完成摆放设施每日任务
        
        完整流程：
        1. 购买老鼠夹 (goods_id=4)
        2. 购买节油器 (goods_id=7)  
        3. 清空位置1和2的现有设施
        4. 在位置1摆放老鼠夹 (goods_code=30301)
        5. 在位置2摆放节油器 (goods_code=30401)
        
        Returns:
            Dict包含任务结果:
            {
                "success": bool,
                "message": str,
                "details": dict  # 详细执行结果
            }
        """
        print("[*] 开始执行摆放设施每日任务...")
        
        results = {
            "success": True,
            "message": "",
            "details": {
                "buy_mousetrap": {"success": False, "message": ""},
                "buy_fuel_saver": {"success": False, "message": ""},
                "clear_position_1": {"success": False, "message": ""},
                "clear_position_2": {"success": False, "message": ""},
                "place_mousetrap": {"success": False, "message": ""},
                "place_fuel_saver": {"success": False, "message": ""}
            }
        }
        
        failed_steps = []
        
        try:
            # 步骤1: 购买老鼠夹 (goods_id=4)
            print("[*] 步骤1: 购买老鼠夹...")
            success, result = self.buy_facility(goods_id=4, num=1)
            results["details"]["buy_mousetrap"]["success"] = success
            results["details"]["buy_mousetrap"]["message"] = str(result)
            if not success:
                failed_steps.append("购买老鼠夹失败")
                
            import time
            time.sleep(0.5)
            
            # 步骤2: 购买节油器 (goods_id=7)
            print("[*] 步骤2: 购买节油器...")
            success, result = self.buy_facility(goods_id=7, num=1)
            results["details"]["buy_fuel_saver"]["success"] = success
            results["details"]["buy_fuel_saver"]["message"] = str(result)
            if not success:
                failed_steps.append("购买节油器失败")
                
            time.sleep(0.5)
            
            # 步骤3: 清空位置1的现有设施
            print("[*] 步骤3: 清空位置1...")
            success, message = self.clear_facility(position=1)
            results["details"]["clear_position_1"]["success"] = success
            results["details"]["clear_position_1"]["message"] = message
            if not success:
                failed_steps.append("清空位置1失败")
                
            time.sleep(0.5)
            
            # 步骤4: 清空位置2的现有设施
            print("[*] 步骤4: 清空位置2...")
            success, message = self.clear_facility(position=2)
            results["details"]["clear_position_2"]["success"] = success
            results["details"]["clear_position_2"]["message"] = message
            if not success:
                failed_steps.append("清空位置2失败")
                
            time.sleep(0.5)
            
            # 步骤5: 在位置1摆放老鼠夹 (goods_code=30301)
            print("[*] 步骤5: 在位置1摆放老鼠夹...")
            success, result = self.place_facility(goods_code=30301, position=1)
            results["details"]["place_mousetrap"]["success"] = success
            results["details"]["place_mousetrap"]["message"] = str(result)
            if not success:
                failed_steps.append("摆放老鼠夹失败")
                
            time.sleep(0.5)
            
            # 步骤6: 在位置2摆放节油器 (goods_code=30401)
            print("[*] 步骤6: 在位置2摆放节油器...")
            success, result = self.place_facility(goods_code=30401, position=2)
            results["details"]["place_fuel_saver"]["success"] = success
            results["details"]["place_fuel_saver"]["message"] = str(result)
            if not success:
                failed_steps.append("摆放节油器失败")
            
            # 生成总结消息
            if not failed_steps:
                results["message"] = "✅ 摆放设施任务完成！成功购买并摆放老鼠夹和节油器"
                results["success"] = True
                print("[+] 摆放设施每日任务全部完成！")
            else:
                results["message"] = f"⚠️ 摆放设施任务部分完成，失败步骤: {'; '.join(failed_steps)}"
                results["success"] = len(failed_steps) < 3  # 如果失败步骤少于一半，仍算部分成功
                print(f"[!] 摆放设施任务部分失败: {'; '.join(failed_steps)}")
                
        except Exception as e:
            error_message = f"摆放设施任务执行异常: {str(e)}"
            results["success"] = False
            results["message"] = error_message
            print(f"[Error] {error_message}")
            
        return results

    # --- 座位相关操作 (除蟑螂、抓白食) ---

    def clear_all_roaches(self) -> None:
        """清理餐厅中所有的蟑螂。"""
        print("\n[*] 正在检查并清理所有蟑螂...")
        # 调用通用的座位查找方法
        seat_map = self._get_seats_by_types([("4", "蟑螂")])
        if seat_map is None:
            print("[Error] 因获取座位列表失败，无法开始清理蟑螂。")
            return

        roach_ids = seat_map.get("蟑螂", [])
        if not roach_ids:
            print("[Info] 餐厅内没有发现蟑螂。")
            return

        print(f"[Info] 检测到 {len(roach_ids)} 只蟑螂，开始逐一清理...")
        for seat_id in roach_ids:
            self._clear_one_roach(seat_id)
            time.sleep(0.5)  # 模拟操作延迟，避免请求过快
        print("[Success] 所有蟑螂清理完毕。")

    def catch_all_dine_and_dashers(self) -> None:
        """抓住所有吃白食的顾客。"""
        print("\n[*] 正在检查并抓捕所有吃白食的顾客...")
        # 调用通用的座位查找方法，type=3表示吃白食
        seat_map = self._get_seats_by_types([("3", "白食")])
        if seat_map is None:
            print("[Error] 因获取座位列表失败，无法开始抓捕。")
            return

        dasher_ids = seat_map.get("白食", [])
        if not dasher_ids:
            print("[Info] 餐厅内没有发现吃白食的顾客。")
            return

        print(f"[Info] 检测到 {len(dasher_ids)} 名吃白食的顾客，开始逐一抓捕...")
        for seat_id in dasher_ids:
            self._catch_one_dasher(seat_id)
            time.sleep(0.5)
        print("[Success] 所有吃白食的顾客处理完毕。")

    def _get_seats_by_types(self, targets: List[Tuple[str, str]]) -> Optional[Dict[str, List[int]]]:
        """
        【内部重构方法】通用方法，按类型查找座位ID。
        :param targets: 一个元组列表，每个元组是 (type_id_string, type_name_for_dict_key)。
        :return: 一个字典，键是 type_name, 值是座位ID列表。
        """
        all_seats = []
        seen_ids = set()
        for page_type in range(1, 21):  # 设置一个20页的保险阈值，防止无限循环
            try:
                response = self.post(action_path="m=Seat&a=get_list", data={"page": "1", "type": str(page_type)})
                seats_on_page = response.get("data", [])
                if not seats_on_page or (seats_on_page and seats_on_page[0].get("id") in seen_ids): break
                for seat in seats_on_page:
                    if seat.get("id") not in seen_ids:
                        all_seats.append(seat)
                        seen_ids.add(seat.get("id"))
            except (BusinessLogicError, ConnectionError) as e:
                print(f"[Error] 获取座位列表第 {page_type} 页时失败: {e}")
                return None

        result_map = {name: [] for _, name in targets}
        target_ids = {type_id for type_id, _ in targets}

        for seat in all_seats:
            seat_type_str = str(seat.get("type"))
            if seat_type_str in target_ids:
                for type_id, name in targets:
                    if seat_type_str == type_id:
                        result_map[name].append(int(seat["id"]))
                        break
        return result_map

    def _clear_one_roach(self, seat_id: int) -> None:
        """【内部方法】清理单个蟑螂。"""
        try:
            response = self.post(action_path="m=Seat&a=my_go", data={"id": str(seat_id)})
            msg = response.get("msg", "未知消息").replace("<br>", " / ")
            print(f"  └> 清理座位 {seat_id} (蟑螂): {msg}")
        except (BusinessLogicError, ConnectionError) as e:
            print(f"  └> 清理座位 {seat_id} (蟑螂) 失败: {e}")

    def _catch_one_dasher(self, seat_id: int) -> None:
        """【内部方法】抓捕单个吃白食的。"""
        try:
            response = self.post(action_path="m=Seat&a=my_go", data={"id": str(seat_id)})
            msg = response.get("msg", "未知消息").replace("<br>", " / ")
            print(f"  └> 抓捕座位 {seat_id} (白食): {msg}")
        except (BusinessLogicError, ConnectionError) as e:
            print(f"  └> 抓捕座位 {seat_id} (白食) 失败: {e}")

    # --- 升星相关操作 ---

    def get_star_upgrade_requirements(self) -> Optional[Dict[str, Any]]:
        """查询下一次升星所需要的条件。"""
        print("\n[*] 正在查询升星条件...")
        try:
            response = self.post(action_path="m=Isoc&a=up_star", data={"type": "1"})
            msg = response.get("msg", "")
            if "需要" in msg:
                details = self._parse_requirements_message(msg)
                print("[Info] 成功获取到升星条件。")
                return details
            else:
                print(f"[Info] 获取到升星信息，但可能不是条件查询结果: {msg}")
                return {"raw_message": msg}
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 查询升星条件失败: {e}")
            return None

    def execute_star_upgrade(self) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """执行升星操作。"""
        print(f"\n[*] 正在尝试执行升星操作...")
        try:
            response = self.post(action_path="m=Isoc&a=up_star", data={"type": "2"})
            msg = response.get("msg", "")
            details = self._parse_upgrade_star_message(msg)
            print(f"[Success] {msg}")
            return True, details
        except (BusinessLogicError, ConnectionError) as e:
            print(f"[Error] 执行升星失败: {e}")
            return False, str(e)

    def _parse_requirements_message(self, msg: str) -> Dict[str, Any]:
        """辅助方法，用于解析升星条件的消息。"""
        details = {"target": {}, "requirements": {}, "current": {}}
        target_match = re.search(r"升级\[(.*?)]需要", msg)
        if target_match: details["target"]["level_name"] = target_match.group(1)
        level_match = re.search(r"等级:(\d+)\((\d+)\)", msg)
        if level_match:
            details["requirements"]["level"] = int(level_match.group(1))
            details["current"]["level"] = int(level_match.group(2))
        gold_match = re.search(r"金币:(\d+)\((\d+)\)", msg)
        if gold_match:
            details["requirements"]["gold"] = int(gold_match.group(1))
            details["current"]["gold"] = int(gold_match.group(2))
        return details

    def _parse_upgrade_star_message(self, msg: str) -> Dict[str, Any]:
        """辅助方法，用于从升星成功的消息中解析出具体收益。"""
        details = {}
        slots_match = re.search(r"设施位\+(\d+)", msg)
        if slots_match: details['facility_slots_added'] = int(slots_match.group(1))
        picky_match = re.search(r"挑剔顾客数\+(\d+)%", msg)
        if picky_match: details['picky_customers_increase_pct'] = int(picky_match.group(1))
        items_match = re.search(r"获得:(.+)", msg)
        if items_match: details['items_gained'] = items_match.group(1).strip()
        if not details: return {'raw_message': msg}
        return details


# =======================================================
#               可以直接运行此文件进行测试
# =======================================================
if __name__ == '__main__':
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY: raise ValueError("请在 .env 中设置 TEST_KEY")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR} if TEST_COOKIE_STR else None

    action = RestaurantActions(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "#" * 20 + "  餐厅管理模块完整测试  " + "#" * 20)

    # --- 测试 1: 获取状态 ---
    print("\n\n" + "=" * 20 + " 1. 开始测试获取餐厅状态 " + "=" * 20)
    action.get_status()

    # --- 测试 2: 巡店 ---
    print("\n\n" + "=" * 20 + " 2. 开始测试巡店 " + "=" * 20)
    visit_result = action.visit_shop()
    if visit_result.get("success"):
        print("巡店成功，座位信息:")
        seat_info = visit_result.get("seat_info", {})
        print(json.dumps(seat_info, indent=2, ensure_ascii=False))
    else:
        print(f"巡店失败: {visit_result.get('message')}")

    # --- 测试 3: 添油 ---
    print("\n\n" + "=" * 20 + " 3. 开始测试添油 " + "=" * 20)
    action.refill_oil()

    # --- 测试 4: 摆放设施 ---
    print("\n\n" + "=" * 20 + " 4. 开始测试摆放设施 " + "=" * 20)
    FACILITY_CODE = 30201  # 小仙宣传海报
    action.place_facility(goods_code=FACILITY_CODE, position=1)

    # --- 测试 5: 除蟑螂 ---
    print("\n\n" + "=" * 20 + " 5. 开始测试除蟑螂 " + "=" * 20)
    action.clear_all_roaches()

    # --- 测试 6: 抓捕吃白食的 ---
    print("\n\n" + "=" * 20 + " 6. 开始测试抓捕吃白食的 " + "=" * 20)
    action.catch_all_dine_and_dashers()

    # --- 测试 7: 查询升星条件 ---
    print("\n\n" + "=" * 20 + " 7. 开始测试查询升星条件 " + "=" * 20)
    requirements = action.get_star_upgrade_requirements()
    if requirements:
        print(json.dumps(requirements, indent=2, ensure_ascii=False))
    else:
        print("查询失败。")

    # --- 测试 8: 执行升星操作 ---
    print("\n\n" + "=" * 20 + " 8. 开始测试执行升星操作 " + "=" * 20)
    success, result = action.execute_star_upgrade()
    print(f"是否成功: {success}")
    if success:
        print("解析出的升星收益:", result)
    else:
        print(f"失败原因: {result}")

    print("\n\n" + "#" * 20 + "  所有测试结束  " + "#" * 20)
"""
精炼宝石模块
用于精炼宝石，完成每日精炼任务
"""
import time
from typing import Dict, Any, Optional, List
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class GemRefiningAction(BaseAction):
    """
    精炼宝石操作类，处理宝石精炼功能
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key=key, cookie=cookie, base_url=base_url)
        # 更新 Referer
        self.http_client.headers.update({
            'Referer': 'http://117.72.123.195/wap/res/my_equip.html'
        })

    def get_gem_list(self, page: int = 1) -> Dict[str, Any]:
        """
        获取宝石列表
        
        Args:
            page: 页码，默认为1
            
        Returns:
            Dict包含宝石列表:
            {
                "success": bool,
                "message": str,
                "gems": List[Dict],  # 宝石列表
                "data": dict  # 原始返回数据
            }
        """
        print(f"[*] 正在获取宝石列表 (页码: {page})...")
        
        action_path = "m=Depot&a=get_list"
        payload = {
            "key": self.key,
            "page": str(page),
            "type": "5"  # type=5 表示宝石类型
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            # 检查响应状态
            if response_data.get('status'):
                gems = response_data.get('data', [])
                
                print(f"[+] 宝石列表获取成功，找到 {len(gems)} 个宝石")
                return {
                    "success": True,
                    "message": f"获取到 {len(gems)} 个宝石",
                    "gems": gems,
                    "data": response_data.get('data', [])
                }
            else:
                error_msg = response_data.get('msg', '获取宝石列表失败')
                print(f"[!] 宝石列表获取失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "gems": [],
                    "data": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取宝石列表失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "gems": [],
                "data": {}
            }

    def refine_gem(self, stone_code: str, is_fixed: int = 0) -> Dict[str, Any]:
        """
        精炼宝石
        
        Args:
            stone_code: 宝石代码 (如: 50211)
            is_fixed: 是否固定精炼，默认为0
            
        Returns:
            Dict包含精炼结果:
            {
                "success": bool,
                "message": str,
                "result_gem": str,  # 精炼后的宝石信息
                "data": dict  # 如果有返回数据
            }
        """
        print(f"[*] 正在精炼宝石 (代码: {stone_code})...")
        
        action_path = "m=Stone&a=strengthenStone"
        payload = {
            "stone_code": stone_code,
            "key": self.key,
            "is_fixed": str(is_fixed)
        }
        
        try:
            response_data = self.post(action_path, data=payload)
            
            # 检查响应状态
            if response_data.get('status'):
                message = response_data.get('msg', '精炼成功')
                
                # 解析精炼结果
                result_gem = ""
                if "获得" in message:
                    # 提取获得的宝石信息
                    result_gem = message.replace("<br>", " ").strip()
                
                print(f"[+] 宝石精炼成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "result_gem": result_gem,
                    "data": response_data.get('data', {})
                }
            else:
                error_msg = response_data.get('msg', '精炼失败')
                print(f"[!] 宝石精炼失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "result_gem": "",
                    "data": {}
                }
                
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 精炼宝石失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "result_gem": "",
                "data": {}
            }

    def find_wisdom_gems(self, gems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从宝石列表中找出智慧原石
        
        Args:
            gems: 宝石列表
            
        Returns:
            智慧原石列表
        """
        wisdom_gems = []
        for gem in gems:
            goods_name = gem.get("goods_name", "")
            goods_code = gem.get("goods_code", "")
            
            # 检查是否为智慧原石 (包含"智慧"且以"502"开头的代码)
            if "智慧" in goods_name and goods_code.startswith("502"):
                wisdom_gems.append(gem)
        
        print(f"[Info] 找到 {len(wisdom_gems)} 个智慧原石")
        return wisdom_gems

    def auto_refine_wisdom_gem(self) -> Dict[str, Any]:
        """
        自动精炼智慧原石（完成每日精炼任务）
        
        流程：
        1. 获取宝石列表
        2. 查找智慧原石
        3. 精炼一个智慧原石
        
        Returns:
            精炼结果
        """
        print(f"[*] 开始自动精炼智慧原石...")
        
        results = {
            "success": True,
            "refined_gem": None,
            "message": ""
        }
        
        try:
            # 1. 获取宝石列表
            gem_list_result = self.get_gem_list()
            if not gem_list_result.get("success"):
                return {
                    "success": False,
                    "message": f"获取宝石列表失败: {gem_list_result.get('message')}",
                    "details": results
                }
            
            gems = gem_list_result.get("gems", [])
            if not gems:
                return {
                    "success": False,
                    "message": "没有找到任何宝石",
                    "details": results
                }
            
            # 2. 查找智慧原石
            wisdom_gems = self.find_wisdom_gems(gems)
            if not wisdom_gems:
                return {
                    "success": False,
                    "message": "没有找到智慧原石，无法进行精炼",
                    "details": results
                }
            
            # 3. 选择第一个智慧原石进行精炼
            selected_gem = wisdom_gems[0]
            stone_code = selected_gem.get("goods_code")
            gem_name = selected_gem.get("goods_name")
            
            print(f"[*] 选择精炼宝石: {gem_name} (代码: {stone_code})")
            
            # 4. 执行精炼
            refine_result = self.refine_gem(stone_code)
            
            if refine_result.get("success"):
                results["refined_gem"] = {
                    "original_name": gem_name,
                    "original_code": stone_code,
                    "result": refine_result
                }
                results["message"] = f"✅ 智慧原石精炼完成！原宝石: {gem_name}"
                print(f"[+] {results['message']}")
            else:
                error_msg = refine_result.get("message", "精炼失败")
                results["success"] = False
                results["message"] = f"❌ 智慧原石精炼失败: {error_msg}"
                print(f"[!] {results['message']}")
            
            return results
            
        except Exception as e:
            print(f"[Error] 自动精炼智慧原石失败: {e}")
            return {
                "success": False,
                "message": f"自动精炼智慧原石异常: {str(e)}",
                "details": results
            }

    def complete_daily_gem_refining(self) -> Dict[str, Any]:
        """
        完成每日宝石精炼任务的完整流程
        
        流程：
        1. 购买精炼材料（智慧原石+原石精华）
        2. 精炼智慧原石
        
        Returns:
            完整流程结果
        """
        print(f"[*] 开始每日宝石精炼任务...")
        
        results = {
            "success": True,
            "purchase_result": None,
            "refine_result": None,
            "total_cost": 0,
            "message": ""
        }
        
        try:
            # 1. 购买精炼材料
            from src.delicious_town_bot.actions.shop import ShopAction
            
            # 使用相同的key和cookie创建ShopAction
            shop_action = ShopAction(key=self.key, cookie=self.http_client.cookies.get_dict())
            
            print(f"[*] 第1步: 购买精炼宝石材料...")
            purchase_result = shop_action.buy_gem_refining_materials()
            results["purchase_result"] = purchase_result
            results["total_cost"] = purchase_result.get("total_cost", 0)
            
            if not purchase_result.get("success"):
                results["success"] = False
                results["message"] = f"❌ 购买精炼材料失败: {purchase_result.get('message')}"
                return results
            
            # 等待片刻让材料生效
            time.sleep(2)
            
            # 2. 自动精炼智慧原石
            print(f"[*] 第2步: 精炼智慧原石...")
            refine_result = self.auto_refine_wisdom_gem()
            results["refine_result"] = refine_result
            
            if refine_result.get("success"):
                cost_info = f"，消耗 {results['total_cost']} 金币" if results['total_cost'] > 0 else ""
                results["message"] = f"✅ 每日宝石精炼任务完成！{cost_info}"
                results["success"] = True
            else:
                error_msg = refine_result.get("message", "精炼失败")
                results["message"] = f"⚠️ 材料购买成功，但精炼失败: {error_msg}"
                results["success"] = False
            
            print(f"[+] {results['message']}")
            return results
            
        except Exception as e:
            print(f"[Error] 每日宝石精炼任务失败: {e}")
            return {
                "success": False,
                "message": f"每日宝石精炼任务异常: {str(e)}",
                "details": results
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

    gem_action = GemRefiningAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "=" * 20 + " 精炼宝石功能测试 " + "=" * 20)

    # 测试获取宝石列表
    print("\n--- 1. 获取宝石列表 ---")
    gem_list_result = gem_action.get_gem_list()
    if gem_list_result.get("success"):
        print("宝石列表获取成功")
        gems = gem_list_result.get("gems", [])
        if gems:
            print(f"找到 {len(gems)} 个宝石:")
            for gem in gems[:3]:  # 只显示前3个
                name = gem.get("goods_name", "未知")
                code = gem.get("goods_code", "未知")
                print(f"  - {name} (代码: {code})")
    
    # 测试精炼功能（注释掉避免实际精炼）
    print("\n--- 2. 测试精炼功能 ---")
    print("注意：这会实际精炼宝石，确认后取消注释以下代码")
    # complete_result = gem_action.complete_daily_gem_refining()
    # print(f"完整任务结果: {complete_result}")
    
    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
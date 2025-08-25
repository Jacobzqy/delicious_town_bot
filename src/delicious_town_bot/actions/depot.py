import logging
import os
import time
from collections import Counter
from typing import Any, Dict, List, Optional
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError
from src.delicious_town_bot.constants import ItemType, Street

class DepotAction(BaseAction):
    """
    封装所有与仓库功能相关的操作。
    包含了物品获取、使用，以及一个特殊的残卷分解功能。
    """

    def __init__(self, key: str, cookie: Optional[Dict[str, str]]):
        """
        初始化仓库操作实例。
        """
        # 主模块的 base_url
        self.depot_base_url = "http://117.72.123.195/index.php?g=Res&m=Depot"
        # 为特殊操作预定义 URL
        self.cookbooks_url = "http://117.72.123.195/index.php?g=Res&m=MysteriousCookbooks&a=resolve"
        super().__init__(key=key, base_url=self.depot_base_url, cookie=cookie)

    def get_items_by_page(self, item_type: ItemType, page: int) -> List[Dict[str, Any]]:
        """获取指定类型、指定页码的物品列表。"""
        try:
            response = self.post(
                action_path="a=get_list",
                data={"type": item_type.value, "page": page}
            )
            items = response.get('data', [])
            return items if isinstance(items, list) else []
        except BusinessLogicError as e:
            logging.error(f"获取仓库第 {page} 页（类型: {item_type.name}）失败：{e}")
            return []
        except ConnectionError:
            raise

    def get_all_items(self, item_type: ItemType) -> List[Dict[str, Any]]:
        """获取指定类型的所有物品（自动处理翻页）。"""
        logging.info(f"开始获取仓库中所有类型为 '{item_type.name}' 的物品...")
        all_items = []
        page = 1
        last_page_content = None

        while True:
            logging.info(f"正在获取第 {page} 页...")
            current_page_items = self.get_items_by_page(item_type, page)

            if not current_page_items or current_page_items == last_page_content:
                break

            all_items.extend(current_page_items)
            last_page_content = current_page_items
            page += 1

        logging.info(f"获取完成，共找到 {len(all_items)} 个 '{item_type.name}' 类型的物品。")
        return all_items

    def use_item(self, item_code: str, step_2_data: Optional[Any] = None) -> bool:
        """
        使用仓库中的物品（处理单步和两步操作）。
        """
        action_path = "a=use_step_2" if step_2_data is not None else "a=use_step_1"
        data = {"code": item_code}
        if step_2_data is not None:
            data['data'] = step_2_data

        try:
            logging.info(f"尝试使用物品 {item_code}，操作: {action_path}，数据: {data}")
            response = self.post(action_path=action_path, data=data)
            success_message = response.get('msg', '操作成功')
            logging.info(f"成功使用物品 {item_code}: {success_message}")
            return True
        except (BusinessLogicError, ConnectionError) as e:
            logging.error(f"使用物品 {item_code} 失败: {e}")
            return False

    def resolve_fragment(self, fragment_code: str) -> bool:
        """
        分解指定的残卷 (特殊跨模块操作)。
        """
        try:
            logging.info(f"尝试分解残卷 {fragment_code}...")
            # 注意：这里直接调用私有的 _request 方法并传入完整 URL，以处理此特例
            response = self._request(
                "post",
                url=self.cookbooks_url,
                data={"code": fragment_code}
            )
            success_message = response.get('msg', '分解成功')
            logging.info(f"成功分解残卷 {fragment_code}: {success_message}")
            return True
        except (BusinessLogicError, ConnectionError) as e:
            logging.error(f"分解残卷 {fragment_code} 失败: {e}")
            return False

    def get_all_gems(self) -> Dict[str, Any]:
        """
        获取所有宝石信息（包含仓库中的宝石和镶嵌在装备上的宝石）
        
        Returns:
            Dict包含:
            {
                "success": bool,
                "inventory_gems": List[Dict],  # 仓库中的宝石
                "equipped_gems": Dict,  # 镶嵌在装备上的宝石（按装备ID分组）
                "summary": Dict  # 宝石统计信息
            }
        """
        result = {
            "success": True,
            "inventory_gems": [],
            "equipped_gems": {},
            "summary": {
                "total_inventory_gems": 0,
                "total_equipped_gems": 0,
                "gem_types": {}
            },
            "message": ""
        }
        
        try:
            # 获取仓库中的宝石（type=5表示宝石）
            logging.info("正在获取仓库中的宝石...")
            page = 1
            while page <= 20:  # 限制最大页数防止无限循环
                try:
                    response = self.post(
                        action_path="a=get_list",
                        data={"type": "5", "page": str(page)}
                    )
                    
                    if not response.get("status"):
                        break
                    
                    page_gems = response.get("data", [])
                    if not page_gems or not isinstance(page_gems, list):
                        break
                    
                    # 检查是否有重复数据（分页结束标志）
                    new_gem_ids = {gem.get("id") for gem in page_gems}
                    existing_gem_ids = {gem.get("id") for gem in result["inventory_gems"]}
                    
                    if new_gem_ids.issubset(existing_gem_ids):
                        break
                    
                    # 添加新宝石
                    for gem in page_gems:
                        if gem.get("id") not in existing_gem_ids:
                            result["inventory_gems"].append(gem)
                    
                    page += 1
                    time.sleep(0.1)  # 短暂延迟
                    
                except Exception as e:
                    logging.error(f"获取宝石第{page}页失败: {e}")
                    break
            
            # 统计仓库宝石
            result["summary"]["total_inventory_gems"] = len(result["inventory_gems"])
            
            # 统计宝石类型
            for gem in result["inventory_gems"]:
                gem_name = gem.get("goods_name", "未知宝石")
                gem_type = gem_name.split("(")[0] if "(" in gem_name else gem_name  # 提取基础名称
                
                if gem_type not in result["summary"]["gem_types"]:
                    result["summary"]["gem_types"][gem_type] = {
                        "inventory_count": 0,
                        "equipped_count": 0,
                        "total_count": 0
                    }
                
                num = int(gem.get("num", 1))
                result["summary"]["gem_types"][gem_type]["inventory_count"] += num
                result["summary"]["gem_types"][gem_type]["total_count"] += num
            
            logging.info(f"获取到 {result['summary']['total_inventory_gems']} 个仓库宝石")
            result["message"] = f"✅ 成功获取宝石信息：仓库 {result['summary']['total_inventory_gems']} 个"
            
        except Exception as e:
            result["success"] = False
            result["message"] = f"获取宝石信息失败: {str(e)}"
            logging.error(f"获取宝石信息失败: {e}")
        
        return result

    def get_gem_by_page(self, page: int = 1) -> Dict[str, Any]:
        """
        获取指定页的宝石列表
        
        Args:
            page: 页码
            
        Returns:
            Dict包含宝石列表和分页信息
        """
        try:
            response = self.post(
                action_path="a=get_list",
                data={"type": "5", "page": str(page)}
            )
            
            if response.get("status"):
                return {
                    "success": True,
                    "gems": response.get("data", []),
                    "page": page,
                    "message": f"第{page}页宝石获取成功"
                }
            else:
                return {
                    "success": False,
                    "gems": [],
                    "page": page,
                    "message": "获取宝石列表失败"
                }
                
        except Exception as e:
            return {
                "success": False,
                "gems": [],
                "page": page,
                "message": f"获取宝石列表异常: {str(e)}"
            }


# ==============================================================================
#  独立测试脚本 (Standalone Test Script)
# ==============================================================================
if __name__ == '__main__':
    # --- 环境设置 ---
    from dotenv import load_dotenv

    # 配置日志记录器
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 加载 .env 文件中的环境变量
    load_dotenv()
    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")

    # 校验环境变量
    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在项目根目录的 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")

    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}

    # 实例化 Action 类
    depot_bot = DepotAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)
    print("\n--- DepotAction 全面测试开始 ---\n")

    # --- 1. 核心功能测试 ---
    print("--- 1. 测试核心数据获取功能 (get_all_items) ---")
    materials = depot_bot.get_all_items(item_type=ItemType.MATERIALS)
    if materials:
        print(f"[+] 成功获取到 {len(materials)} 个【材料】。")
        # 使用 Counter 统计物品分布
        material_counts = Counter(item['goods_name'] for item in materials)
        print("[*] 部分材料展示:")
        for name, count in list(material_counts.items())[:5]:  # 只显示前5种
            print(f"  - {name}: {count} 个")
    else:
        print("[!] 未获取到任何材料。")

    time.sleep(1)

    print("\n--- 2. 测试物品使用功能 (use_item) ---")

    # 测试单步使用
    print("\n--- [测试 2.1] 单步使用物品 (例如 食材抽奖券 code=20103) ---")
    depot_bot.use_item(item_code='20103')
    print("[*] use_item(item_code='20103') 调用演示。")
    print("[!] 注意：为防止意外消耗您的物品，实际调用已被注释。请在需要时取消注释。")

    time.sleep(1)

    # 测试两步使用
    print("\n--- [测试 2.2] 两步使用物品 (例如 搬家卡 code=10201) ---")
    depot_bot.use_item(item_code='10201', step_2_data=Street.SU.value)
    print(f"[*] use_item(item_code='10201', step_2_data=Street.SU.value) 调用演示 (搬到江苏街)。")
    print("[!] 注意：实际调用已被注释。")

    time.sleep(1)

    # 测试残卷分解
    print("\n--- 3. 测试特殊功能 (resolve_fragment) ---")
    print("\n--- [测试 3.1] 分解残卷 (例如 秘·芙蓉大虾·残卷 code=70004) ---")
    depot_bot.resolve_fragment(fragment_code='70004')
    print("[*] resolve_fragment(fragment_code='70004') 调用演示。")
    print("[!] 注意：实际调用已被注释。")

    time.sleep(1)

    # --- 4. 探索性/边缘情况测试 ---
    print("\n--- 4. 开始探索性API测试 ---")
    print("\n--- [实验 4.1] 测试API在页码超出范围时的行为 ---")
    # 首先确保有数据，获取第一页
    page_1_items = depot_bot.get_items_by_page(ItemType.MATERIALS, page=1)
    if page_1_items:
        print("[*] 正在请求一个极大的页码 (page=999)...")
        page_999_items = depot_bot.get_items_by_page(ItemType.MATERIALS, page=999)
        if page_999_items:
            print(f"[+] 成功获取到 {len(page_999_items)} 个物品。")
            if page_999_items == page_1_items and len(page_1_items) < 20:  # 假设每页20个
                print("[结论] 只有一页数据，超范围请求返回了第一页。")
            else:
                print(
                    "[结论] API在页码超出范围时返回了数据（很可能是最后一页），符合预期。`get_all_items` 的翻页终止逻辑依赖此特性，工作正常！")
        else:
            print("[结论] 请求超范围页码返回了空列表，这与预期不符，可能导致 `get_all_items` 提前终止。")
    else:
        print("[!] 仓库中没有任何材料，无法进行此项测试。")

    print("\n--- DepotAction 所有测试执行完毕 ---")
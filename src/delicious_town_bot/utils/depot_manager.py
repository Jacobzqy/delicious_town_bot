from typing import List, Dict, Any, Optional

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.depot import DepotAction
from src.delicious_town_bot.constants import ItemType


class DepotManager:
    def __init__(self):
        self.account_mgr = AccountManager()

    def _get_action_for_account(self, account_id: int) -> Optional[DepotAction]:
        all_accounts = self.account_mgr.list_accounts()
        account = next((acc for acc in all_accounts if acc.id == account_id), None)

        if not account:
            print(f"DepotManager Error: 无法找到 ID={account_id} 的账号。")
            return None

        if not account.key or account.cookie is None:
            print(f"DepotManager Error: 账号 ID={account_id} 缺少 key 或 cookie。")
            return None

        try:
            cookie_dict = {"PHPSESSID": str(account.cookie)}
            return DepotAction(key=account.key, cookie=cookie_dict)
        except Exception as e:
            print(f"DepotManager Error: 实例化 DepotAction 失败 for account ID={account_id}. Error: {e}")
            return None

    def get_items_for_account(self, account_id: int, item_type: ItemType) -> List[Dict[str, Any]]:
        action = self._get_action_for_account(account_id)
        if not action: return []
        try:
            return action.get_all_items(item_type)
        except Exception as e:
            print(f"获取物品时出错 (account_id={account_id}, item_type={item_type.name}): {e}")
            return []

    # [核心修改] 增加 step_2_data 参数
    def use_item_for_account(self, account_id: int, item_code: str, step_2_data: Optional[Any] = None) -> bool:
        """为指定账号使用一个物品，支持额外数据。"""
        action = self._get_action_for_account(account_id)
        if not action:
            return False

        try:
            # 将 step_2_data 传递给底层的 Action
            success = action.use_item(item_code=item_code, step_2_data=step_2_data)
            return success
        except Exception as e:
            print(f"使用物品时出错 (account_id={account_id}, item_code={item_code}): {e}")
            return False

    def resolve_fragment_for_account(self, account_id: int, fragment_code: str) -> bool:
        action = self._get_action_for_account(account_id)
        if not action: return False
        try:
            return action.resolve_fragment(fragment_code=fragment_code)
        except Exception as e:
            print(f"分解残卷时出错 (account_id={account_id}, fragment_code={fragment_code}): {e}")
            return False

    def close(self):
        self.account_mgr.close()
#!/usr/bin/env python3
"""
好友添油管理器 - 专门用于管理账号间的循环添油功能
"""

from typing import List, Dict, Any, Optional
from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.friend import FriendActions
import time


class FriendOilManager:
    """好友添油管理器"""
    
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
    
    def collect_account_restaurant_ids(self, max_accounts: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        收集所有账号的餐厅ID（从数据库读取，避免重复API调用）
        :param max_accounts: 最大处理账号数量，None表示处理所有账号
        :return: 包含账号信息和餐厅ID的列表
        """
        print("[*] 开始从数据库收集所有账号的餐厅ID...")
        
        # 获取所有有Key的账号
        all_accounts = self.account_manager.list_accounts()
        valid_accounts = [acc for acc in all_accounts if acc.key]
        
        if max_accounts:
            valid_accounts = valid_accounts[:max_accounts]
        
        print(f"[*] 找到 {len(valid_accounts)} 个有Key的账号")
        
        accounts_with_res_id = []
        
        for i, account in enumerate(valid_accounts):
            print(f"[*] [{i+1}/{len(valid_accounts)}] 获取 {account.username} 的餐厅ID...")
            
            try:
                # 从数据库中的restaurant字段读取res_id
                res_id = account.restaurant if account.restaurant and account.restaurant != 'None' else None
                
                account_data = {
                    'id': account.id,
                    'username': account.username,
                    'key': account.key,
                    'cookie': account.cookie or '123',
                    'restaurant': res_id,  # 保持原有字段名，确保兼容性
                    'res_id': res_id
                }
                
                if res_id:
                    print(f"[Database] {account.username} 餐厅ID: {res_id}")
                    accounts_with_res_id.append(account_data)
                else:
                    print(f"[Warning] {account.username} 数据库中缺少餐厅ID")
                    # 仍然添加到列表，但res_id为None
                    account_data['restaurant'] = None
                    account_data['res_id'] = None
                    accounts_with_res_id.append(account_data)
                
            except Exception as e:
                print(f"[Error] 获取 {account.username} 餐厅ID失败: {e}")
                # 添加失败的账号信息
                accounts_with_res_id.append({
                    'id': account.id,
                    'username': account.username,
                    'key': account.key,
                    'cookie': account.cookie or '123',
                    'restaurant': None,
                    'res_id': None,
                    'error': str(e)
                })
        
        successful_count = sum(1 for acc in accounts_with_res_id if acc['res_id'])
        print(f"[Summary] 成功获取 {successful_count}/{len(accounts_with_res_id)} 个账号的餐厅ID")
        
        return accounts_with_res_id
    
    def execute_cycle_refill_oil(self, accounts_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        执行循环添油操作
        :param accounts_data: 账号数据列表，如果为None则自动收集
        :return: 添油结果统计
        """
        if accounts_data is None:
            print("[*] 未提供账号数据，开始自动收集...")
            accounts_data = self.collect_account_restaurant_ids()
        
        # 过滤出有餐厅ID的账号
        valid_accounts = [acc for acc in accounts_data if acc.get('res_id')]
        
        if not valid_accounts:
            return {
                "error": "没有找到有效的餐厅ID",
                "total_attempts": 0,
                "successful_refills": 0,
                "failed_refills": 0
            }
        
        print(f"[*] 开始循环添油，共 {len(valid_accounts)} 个有效账号...")
        
        # 使用第一个账号的FriendActions实例执行批量循环添油
        first_account = valid_accounts[0]
        cookie_dict = {"PHPSESSID": first_account['cookie']}
        friend_action = FriendActions(key=first_account['key'], cookie=cookie_dict)
        
        # 执行批量循环添油
        return friend_action.batch_cycle_refill_oil(valid_accounts)
    
    def preview_oil_cycle(self, max_accounts: Optional[int] = None) -> List[Dict[str, str]]:
        """
        预览添油循环顺序（不执行实际添油）
        :param max_accounts: 最大预览账号数量
        :return: 添油对应关系列表
        """
        print("[*] 预览添油循环顺序...")
        
        all_accounts = self.account_manager.list_accounts()
        valid_accounts = [acc for acc in all_accounts if acc.key]
        
        if max_accounts:
            valid_accounts = valid_accounts[:max_accounts]
        
        # 按ID排序
        sorted_accounts = sorted(valid_accounts, key=lambda x: x.id)
        
        cycle_pairs = []
        for i, current_account in enumerate(sorted_accounts):
            next_index = (i + 1) % len(sorted_accounts)
            next_account = sorted_accounts[next_index]
            
            cycle_pairs.append({
                'current_id': str(current_account.id),
                'current_username': current_account.username,
                'target_id': str(next_account.id),
                'target_username': next_account.username
            })
        
        print(f"[Preview] 添油循环顺序（共 {len(cycle_pairs)} 对）:")
        for i, pair in enumerate(cycle_pairs):
            print(f"  {i+1:2d}. {pair['current_username']} → {pair['target_username']}")
        
        return cycle_pairs


# 独立使用的工具函数
def quick_cycle_refill_oil(max_accounts: Optional[int] = None) -> Dict[str, Any]:
    """
    快速执行循环添油的便捷函数
    :param max_accounts: 最大处理账号数量
    :return: 添油结果统计
    """
    account_manager = AccountManager()
    oil_manager = FriendOilManager(account_manager)
    
    try:
        return oil_manager.execute_cycle_refill_oil()
    finally:
        account_manager.close()


if __name__ == "__main__":
    # 测试脚本
    account_manager = AccountManager()
    oil_manager = FriendOilManager(account_manager)
    
    try:
        print("=== 好友添油管理器测试 ===")
        
        # 1. 预览添油循环
        print("\n--- 1. 预览添油循环顺序 ---")
        cycle_pairs = oil_manager.preview_oil_cycle(max_accounts=5)
        
        # 2. 收集餐厅ID（测试前几个账号）
        print("\n--- 2. 测试收集餐厅ID ---")
        accounts_data = oil_manager.collect_account_restaurant_ids(max_accounts=3)
        
        print(f"\n收集到的账号数据:")
        for acc in accounts_data:
            status = "✅" if acc.get('res_id') else "❌"
            res_id = acc.get('res_id', 'N/A')
            error = acc.get('error', '')
            print(f"  {status} {acc['username']}: 餐厅ID={res_id} {error}")
        
        # 3. 执行添油（注释掉以避免真实执行）
        # print("\n--- 3. 执行循环添油 ---")
        # results = oil_manager.execute_cycle_refill_oil(accounts_data)
        # print(f"添油结果: {results}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        account_manager.close()
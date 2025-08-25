"""
特价菜任务管理器
专门用于管理每日特价菜购买任务的状态追踪和批量执行
"""
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from src.delicious_town_bot.db.session import DBSession
from src.delicious_town_bot.db.models import SpecialFoodTask, Account
from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.food import FoodActions


class SpecialFoodManager:
    """特价菜任务管理器，用于跟踪和执行每日特价菜购买任务"""
    
    def __init__(self):
        self.account_manager = AccountManager()
    
    @contextmanager
    def get_db_session(self):
        """获取数据库会话上下文管理器"""
        session = DBSession()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_today_task_status(self, account_id: int) -> Optional[SpecialFoodTask]:
        """
        获取指定账号今日的特价菜任务状态
        :param account_id: 账号ID
        :return: 今日任务记录或None
        """
        today = date.today()
        with self.get_db_session() as session:
            task = session.query(SpecialFoodTask).filter(
                SpecialFoodTask.account_id == account_id,
                SpecialFoodTask.task_date == today
            ).first()
            
            if task:
                # 立即提取任务属性避免session分离
                return {
                    'id': task.id,
                    'account_id': task.account_id,
                    'task_date': task.task_date,
                    'completed': task.completed,
                    'food_name': task.food_name,
                    'quantity': task.quantity,
                    'gold_spent': task.gold_spent,
                    'completed_at': task.completed_at,
                    'error_message': task.error_message
                }
            return None
    
    def mark_task_completed(self, account_id: int, food_name: str, quantity: int, 
                          gold_spent: int) -> bool:
        """
        标记账号的今日特价菜任务为已完成
        :param account_id: 账号ID
        :param food_name: 购买的特价菜名称
        :param quantity: 购买数量
        :param gold_spent: 花费金币
        :return: 是否成功
        """
        today = date.today()
        now = datetime.now()
        
        try:
            with self.get_db_session() as session:
                # 查找今日任务记录
                task = session.query(SpecialFoodTask).filter(
                    SpecialFoodTask.account_id == account_id,
                    SpecialFoodTask.task_date == today
                ).first()
                
                if task:
                    # 更新现有记录
                    task.completed = True
                    task.food_name = food_name
                    task.quantity = quantity
                    task.gold_spent = gold_spent
                    task.completed_at = now
                    task.error_message = None
                else:
                    # 创建新记录
                    task = SpecialFoodTask(
                        account_id=account_id,
                        task_date=today,
                        completed=True,
                        food_name=food_name,
                        quantity=quantity,
                        gold_spent=gold_spent,
                        completed_at=now
                    )
                    session.add(task)
                
                session.commit()
                return True
                
        except Exception as e:
            print(f"[Error] 标记特价菜任务完成失败: {e}")
            return False
    
    def mark_task_failed(self, account_id: int, error_message: str) -> bool:
        """
        标记账号的今日特价菜任务为失败
        :param account_id: 账号ID
        :param error_message: 错误信息
        :return: 是否成功
        """
        today = date.today()
        
        try:
            with self.get_db_session() as session:
                # 查找今日任务记录
                task = session.query(SpecialFoodTask).filter(
                    SpecialFoodTask.account_id == account_id,
                    SpecialFoodTask.task_date == today
                ).first()
                
                if task:
                    # 更新现有记录
                    task.completed = False
                    task.error_message = error_message
                else:
                    # 创建新记录
                    task = SpecialFoodTask(
                        account_id=account_id,
                        task_date=today,
                        completed=False,
                        error_message=error_message
                    )
                    session.add(task)
                
                session.commit()
                return True
                
        except Exception as e:
            print(f"[Error] 标记特价菜任务失败失败: {e}")
            return False
    
    def get_all_accounts_task_status(self) -> Dict[str, Any]:
        """
        获取所有账号今日的特价菜任务状态
        :return: 任务状态统计
        """
        today = date.today()
        
        try:
            with self.get_db_session() as session:
                # 获取所有账号
                accounts = session.query(Account).all()
                
                # 获取今日所有任务记录
                tasks = session.query(SpecialFoodTask).filter(
                    SpecialFoodTask.task_date == today
                ).all()
                
                # 创建任务字典，便于查找
                task_dict = {}
                for task in tasks:
                    task_dict[task.account_id] = {
                        'completed': task.completed,
                        'food_name': task.food_name,
                        'quantity': task.quantity,
                        'gold_spent': task.gold_spent,
                        'completed_at': task.completed_at,
                        'error_message': task.error_message
                    }
                
                # 统计结果
                results = {
                    'total_accounts': len(accounts),
                    'completed_accounts': 0,
                    'failed_accounts': 0,
                    'pending_accounts': 0,
                    'account_details': []
                }
                
                for account in accounts:
                    task_info = task_dict.get(account.id, {})
                    
                    if account.id in task_dict:
                        if task_info.get('completed'):
                            status = 'completed'
                            results['completed_accounts'] += 1
                        else:
                            status = 'failed'
                            results['failed_accounts'] += 1
                    else:
                        status = 'pending'
                        results['pending_accounts'] += 1
                    
                    results['account_details'].append({
                        'username': account.username,
                        'account_id': account.id,
                        'status': status,
                        'has_key': bool(account.key),
                        'task_info': task_info
                    })
                
                return results
                
        except Exception as e:
            print(f"[Error] 获取任务状态失败: {e}")
            return {'error': str(e)}
    
    def buy_special_food_for_account(self, account_id: int, key: str, cookie: str, 
                                   quantity: int = 1, force: bool = False) -> Dict[str, Any]:
        """
        为单个账号购买特价菜
        :param account_id: 账号ID
        :param key: 账号key
        :param cookie: 账号cookie
        :param quantity: 购买数量
        :param force: 是否强制购买（忽略已完成状态）
        :return: 购买结果
        """
        try:
            # 检查今日是否已完成（除非强制购买）
            if not force:
                task_status = self.get_today_task_status(account_id)
                if task_status and task_status.get('completed'):
                    return {
                        'success': False,
                        'message': '今日特价菜任务已完成',
                        'already_completed': True
                    }
            
            # 创建FoodActions实例
            cookie_dict = {"PHPSESSID": cookie}
            food_action = FoodActions(key=key, cookie=cookie_dict)
            
            # 购买特价菜
            success, result = food_action.buy_special_food(quantity=quantity)
            
            if success:
                # 解析购买结果
                if isinstance(result, dict):
                    food_name = result.get('item_name', '特价菜')
                    gold_spent = result.get('gold_spent', 0)
                    actual_quantity = result.get('quantity_added', quantity)
                else:
                    food_name = '特价菜'
                    gold_spent = 0
                    actual_quantity = quantity
                
                # 标记任务完成
                self.mark_task_completed(account_id, food_name, actual_quantity, gold_spent)
                
                return {
                    'success': True,
                    'message': f'成功购买 {actual_quantity} 个 {food_name}',
                    'food_name': food_name,
                    'quantity': actual_quantity,
                    'gold_spent': gold_spent
                }
            else:
                # 标记任务失败
                error_msg = str(result)
                self.mark_task_failed(account_id, error_msg)
                
                return {
                    'success': False,
                    'message': error_msg,
                    'is_sold_out': '已售罄' in error_msg or '已卖完' in error_msg
                }
                
        except Exception as e:
            error_msg = f'购买特价菜时发生异常: {str(e)}'
            self.mark_task_failed(account_id, error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def batch_buy_special_food(self, max_accounts: int = None, quantity: int = 1) -> Dict[str, Any]:
        """
        批量为所有账号购买特价菜
        :param max_accounts: 最大处理账号数
        :param quantity: 每个账号购买数量
        :return: 批量购买结果
        """
        print(f"[*] 开始批量购买特价菜，每个账号购买 {quantity} 个...")
        
        # 获取账号列表
        accounts = self.account_manager.list_accounts()
        if max_accounts:
            accounts = accounts[:max_accounts]
        
        # 立即提取账号属性避免会话分离
        accounts_data = []
        for account in accounts:
            try:
                account_data = {
                    'id': account.id,
                    'username': account.username,
                    'key': account.key,
                    'cookie': account.cookie
                }
                accounts_data.append(account_data)
            except Exception as e:
                print(f"[Warning] 提取账号 {getattr(account, 'username', '未知')} 属性失败: {e}")
        
        results = {
            "total_accounts": len(accounts_data),
            "processed_accounts": 0,
            "successful_purchases": 0,
            "failed_purchases": 0,
            "already_completed": 0,
            "sold_out_detected": False,
            "account_details": []
        }
        
        for i, account_data in enumerate(accounts_data):
            username = account_data['username']
            account_id = account_data['id']
            key = account_data['key']
            cookie = account_data['cookie']
            
            print(f"[*] [{i+1}/{len(accounts_data)}] 处理账号: {username}")
            
            if not key:
                print(f"[Skip] 账号 {username} 没有Key，跳过")
                results["account_details"].append({
                    "username": username,
                    "success": False,
                    "message": "没有Key",
                    "already_completed": False
                })
                continue
            
            results["processed_accounts"] += 1
            
            # 购买特价菜
            purchase_result = self.buy_special_food_for_account(
                account_id, key, cookie, quantity
            )
            
            if purchase_result.get('success'):
                results["successful_purchases"] += 1
                print(f"[Success] {username}: {purchase_result['message']}")
            elif purchase_result.get('already_completed'):
                results["already_completed"] += 1
                print(f"[Skip] {username}: 今日特价菜任务已完成")
            else:
                results["failed_purchases"] += 1
                print(f"[Failed] {username}: {purchase_result['message']}")
                
                # 检查是否售罄
                if purchase_result.get('is_sold_out'):
                    results["sold_out_detected"] = True
                    print(f"[Info] 检测到特价菜已售罄，停止后续购买")
                    # 为剩余账号标记失败
                    for remaining_account in accounts_data[i+1:]:
                        if remaining_account['key']:  # 只处理有Key的账号
                            self.mark_task_failed(
                                remaining_account['id'], 
                                "特价菜已售罄"
                            )
                    break
            
            results["account_details"].append({
                "username": username,
                "success": purchase_result.get('success', False),
                "message": purchase_result.get('message', ''),
                "already_completed": purchase_result.get('already_completed', False),
                "food_name": purchase_result.get('food_name'),
                "quantity": purchase_result.get('quantity'),
                "gold_spent": purchase_result.get('gold_spent')
            })
            
            # 避免请求过快，特价菜购买间隔稍长一些
            if i < len(accounts_data) - 1:
                import time
                time.sleep(1)
        
        # 生成统计报告
        success_rate = (results["successful_purchases"] / results["processed_accounts"] * 100) if results["processed_accounts"] > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"📊 特价菜批量购买完成:")
        print(f"  总账号数: {results['total_accounts']}")
        print(f"  处理账号: {results['processed_accounts']}")
        print(f"  成功购买: {results['successful_purchases']}")
        print(f"  购买失败: {results['failed_purchases']}")
        print(f"  已完成: {results['already_completed']}")
        print(f"  成功率: {success_rate:.1f}%")
        if results["sold_out_detected"]:
            print(f"  ⚠️ 特价菜已售罄")
        print(f"{'='*60}")
        
        results["success_rate"] = success_rate
        results["summary"] = f"购买完成: 成功{results['successful_purchases']}个, 失败{results['failed_purchases']}个, 已完成{results['already_completed']}个, 成功率{success_rate:.1f}%"
        
        return results


# ==============================================================================
#  独立测试脚本
# ==============================================================================
if __name__ == '__main__':
    manager = SpecialFoodManager()
    
    print("=" * 20 + " 特价菜任务管理器测试 " + "=" * 20)
    
    # 获取所有账号的任务状态
    print("\n--- 1. 检查所有账号的特价菜任务状态 ---")
    status = manager.get_all_accounts_task_status()
    if 'error' not in status:
        print(f"总账号数: {status['total_accounts']}")
        print(f"已完成: {status['completed_accounts']}")
        print(f"失败: {status['failed_accounts']}")
        print(f"待处理: {status['pending_accounts']}")
        
        print("\n前5个账号状态:")
        for detail in status['account_details'][:5]:
            print(f"  {detail['username']}: {detail['status']} (Key: {'有' if detail['has_key'] else '无'})")
    
    # 批量购买测试（只测试前2个账号）
    print("\n--- 2. 测试批量购买特价菜（前2个账号） ---")
    # results = manager.batch_buy_special_food(max_accounts=2, quantity=1)
    # print(f"批量购买结果: {results['summary']}")
    
    print("\n" + "=" * 20 + " 测试完成 " + "=" * 20)
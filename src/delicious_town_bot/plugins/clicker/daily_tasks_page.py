"""
日常任务管理页面 - 支持查看任务完成情况和批量完成任务
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QCheckBox, QProgressBar, QTextEdit, QMessageBox, QFrame,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QTabWidget, QSizePolicy
)
from PySide6.QtGui import QFont, QColor

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.daily_tasks import DailyTasksAction
from src.delicious_town_bot.actions.daily import DailyActions
from src.delicious_town_bot.utils.friend_oil_manager import FriendOilManager
from src.delicious_town_bot.utils.restaurant_id_manager import RestaurantIdManager
from src.delicious_town_bot.utils.special_food_manager import SpecialFoodManager
from src.delicious_town_bot.actions.lottery import LotteryActions
from src.delicious_town_bot.actions.active_task import ActiveTaskAction
from src.delicious_town_bot.constants import Move, GameResult, GuessCupResult


class TaskLoadWorker(QThread):
    """任务数据加载工作线程"""
    finished = Signal(object)  # 使用object类型来传递复杂数据
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, account_list: List[Dict]):
        super().__init__()
        self.account_list = account_list
        
    def run(self):
        """加载所有账号的任务数据"""
        try:
            all_data = {}
            total_count = len(self.account_list)
            # print(f"[Debug] TaskLoadWorker 开始运行，账号数量: {total_count}")
            
            for i, account in enumerate(self.account_list):
                if not account.get("key"):
                    continue
                    
                username = account["username"]
                self.progress.emit(f"正在加载 {username} 的任务数据...")
                
                try:
                    cookie_value = account.get("cookie", "123")
                    cookie_dict = {"PHPSESSID": cookie_value}
                    daily_tasks_action = DailyTasksAction(key=account["key"], cookie=cookie_dict)
                    
                    # 获取任务汇总
                    summary = daily_tasks_action.get_task_summary(username)
                    
                    all_data[account["id"]] = {
                        "account": account,
                        "summary": summary,
                        "load_time": datetime.now()
                    }
                    
                except Exception as e:
                    print(f"[Error] 加载 {username} 任务数据失败: {e}")
                    all_data[account["id"]] = {
                        "account": account,
                        "summary": {"success": False, "error": str(e)},
                        "load_time": datetime.now()
                    }
                
                # 短暂延迟避免请求过快
                time.sleep(0.5)
            
            # print(f"[Debug] TaskLoadWorker 完成，准备发送 {len(all_data)} 个账号数据")
            self.finished.emit(all_data)
            
        except Exception as e:
            self.error.emit(f"加载任务数据失败: {str(e)}")


class BatchCycleOilWorker(QThread):
    """批量循环添油工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    oil_finished = Signal(str, str, bool, str)     # 当前账号, 目标账号, 是否成功, 消息
    batch_finished = Signal(bool, str, dict)       # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager, max_accounts: int = None):
        super().__init__()
        self.manager = manager
        self.max_accounts = max_accounts
        self.is_cancelled = False
        
    def run(self):
        """执行批量循环添油"""
        try:
            # 创建添油管理器
            oil_manager = FriendOilManager(self.manager)
            
            # 收集账号餐厅ID
            self.progress_updated.emit(0, 0, "正在收集账号餐厅ID", "准备中...")
            accounts_data = oil_manager.collect_account_restaurant_ids(self.max_accounts)
            
            if self.is_cancelled:
                return
            
            # 过滤有效账号
            valid_accounts = [acc for acc in accounts_data if acc.get('res_id')]
            
            if not valid_accounts:
                self.batch_finished.emit(False, "没有找到有效的餐厅ID", {})
                return
            
            # 使用更新后的批量循环添油方法
            from src.delicious_town_bot.actions.friend import FriendActions
            
            # 使用第一个有效账号创建FriendActions实例来调用批量方法
            first_account = valid_accounts[0]
            cookie_dict = {"PHPSESSID": first_account['cookie']}
            friend_action = FriendActions(key=first_account['key'], cookie=cookie_dict)
            
            # 设置进度监控
            total_count = len(valid_accounts)
            self.progress_updated.emit(0, total_count, "开始批量处理", "正在处理好友申请和添油...")
            
            # 调用更新后的批量循环添油方法
            results = friend_action.batch_cycle_refill_oil(valid_accounts)
            
            if self.is_cancelled:
                return
            
            # 发送每个账号的详细结果信号
            for detail in results.get("refill_details", []):
                if self.is_cancelled:
                    break
                    
                current_account = detail.get("current_account", "")
                target_account = detail.get("target_account", "")
                success = detail.get("success", False)
                
                if success and isinstance(detail.get("message"), dict):
                    oil_added = detail["message"].get("oil_added", detail.get("oil_added", 0))
                    gold_cost = detail["message"].get("gold_cost", detail.get("gold_cost", 0))
                    detail_msg = f"添油{oil_added}，花费{gold_cost}金币"
                else:
                    detail_msg = str(detail.get("message", "未知错误"))
                
                self.oil_finished.emit(current_account, target_account, success, detail_msg)
            
            # 发送完成信号
            if not self.is_cancelled:
                success_count = results.get("successful_refills", 0)
                failed_count = results.get("failed_refills", 0)
                total_attempts = results.get("total_attempts", 0)
                success_rate = (success_count / total_attempts * 100) if total_attempts > 0 else 0
                
                # 包含好友申请处理的摘要信息
                friend_summary = results.get("friend_request_summary", {})
                friend_requests_handled = friend_summary.get("total_requests_handled", 0)
                
                if friend_requests_handled > 0:
                    summary = f"循环添油完成：处理{friend_requests_handled}个好友申请，添油成功{success_count}个，失败{failed_count}个，成功率{success_rate:.1f}%"
                else:
                    summary = f"循环添油完成：成功{success_count}个，失败{failed_count}个，成功率{success_rate:.1f}%"
                
                stats = {"success": success_count, "failed": failed_count, "total": total_attempts}
                self.batch_finished.emit(True, summary, stats)
                
        except Exception as e:
            self.batch_finished.emit(False, f"执行失败: {str(e)}", {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchRoachWorker(QThread):
    """批量蟑螂任务循环工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前阶段, 状态
    phase_finished = Signal(str, bool, str)        # 阶段名称, 是否成功, 消息
    batch_finished = Signal(bool, str, dict)       # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager, max_accounts: int = None):
        super().__init__()
        self.manager = manager
        self.max_accounts = max_accounts
        self.is_cancelled = False
        
    def run(self):
        """执行完整的蟑螂任务循环"""
        try:
            # 创建添油管理器来收集账号数据
            from src.delicious_town_bot.utils.friend_oil_manager import FriendOilManager
            oil_manager = FriendOilManager(self.manager)
            
            # 收集账号餐厅ID
            self.progress_updated.emit(0, 0, "准备阶段", "正在收集账号餐厅ID...")
            accounts_data = oil_manager.collect_account_restaurant_ids(self.max_accounts)
            
            if self.is_cancelled:
                return
            
            # 过滤有效账号
            valid_accounts = [acc for acc in accounts_data if acc.get('res_id')]
            
            if not valid_accounts:
                self.batch_finished.emit(False, "没有找到有效的餐厅ID", {})
                return
            
            # 使用更新后的完整蟑螂任务循环方法
            from src.delicious_town_bot.actions.friend import FriendActions
            
            # 使用第一个有效账号创建FriendActions实例来调用批量方法
            first_account = valid_accounts[0]
            cookie_dict = {"PHPSESSID": first_account['cookie']}
            friend_action = FriendActions(key=first_account['key'], cookie=cookie_dict)
            
            # 设置进度监控
            total_phases = 3  # 处理好友申请、放蟑螂、清理蟑螂
            current_phase = 0
            
            self.progress_updated.emit(current_phase, total_phases, "开始蟑螂任务", "正在启动完整任务循环...")
            
            # 调用完整的蟑螂任务循环方法
            results = friend_action.batch_roach_cycle_complete(valid_accounts)
            
            if self.is_cancelled:
                return
            
            # 发送阶段完成信号
            place_results = results.get("roach_place_results", {})
            clear_results = results.get("roach_clear_results", {})
            
            # 放蟑螂阶段
            place_success = place_results.get("successful_roaches", 0)
            place_total = place_results.get("total_attempts", 0)
            self.phase_finished.emit("放蟑螂", place_success == place_total, f"成功 {place_success}/{place_total}")
            
            # 清理蟑螂阶段
            clear_success = clear_results.get("successful_clears", 0)
            clear_total = clear_results.get("processed_accounts", 0)
            total_roaches_cleared = clear_results.get("total_roaches_cleared", 0)
            self.phase_finished.emit("清理蟑螂", clear_success > 0, f"成功 {clear_success}/{clear_total}，清理 {total_roaches_cleared} 只")
            
            # 发送完成信号
            if not self.is_cancelled:
                overall_success = results.get("overall_success", False)
                summary = results.get("summary", "蟑螂任务完成")
                
                stats = {
                    "place_success": place_success,
                    "place_total": place_total,
                    "clear_success": clear_success,
                    "clear_total": clear_total,
                    "total_roaches_cleared": total_roaches_cleared
                }
                self.batch_finished.emit(overall_success, summary, stats)
                
        except Exception as e:
            self.batch_finished.emit(False, f"执行失败: {str(e)}", {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchFriendRequestWorker(QThread):
    """批量好友申请处理工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, int, int, bool, str)  # 账号名, 申请数, 成功数, 是否成功, 消息
    batch_finished = Signal(bool, str, dict)       # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager, max_accounts: int = None):
        super().__init__()
        self.manager = manager
        self.max_accounts = max_accounts
        self.is_cancelled = False
        
    def run(self):
        """执行批量好友申请处理"""
        try:
            # 获取所有有效账号
            all_accounts = self.manager.list_accounts()
            valid_accounts = [acc for acc in all_accounts if acc.key]
            
            if self.max_accounts:
                valid_accounts = valid_accounts[:self.max_accounts]
            
            if not valid_accounts:
                self.batch_finished.emit(False, "没有找到有效的账号", {})
                return
                
            # 使用第一个有效账号创建FriendActions实例来调用批量方法
            first_account = valid_accounts[0]
            cookie_dict = {"PHPSESSID": first_account.get('cookie', '123')}
            
            from src.delicious_town_bot.actions.friend import FriendActions
            friend_action = FriendActions(key=first_account['key'], cookie=cookie_dict)
            
            # 设置进度监控
            total_accounts = len(valid_accounts)
            self.progress_updated.emit(0, total_accounts, "开始处理", "正在处理好友申请...")
            
            # 调用批量处理好友申请方法
            results = friend_action.batch_handle_all_accounts_friend_requests(valid_accounts)
            
            if self.is_cancelled:
                return
            
            # 发送每个账号的结果信号
            for detail in results.get("account_details", []):
                if self.is_cancelled:
                    break
                    
                account_name = detail.get("account_name", "")
                requests_handled = detail.get("requests_handled", 0)
                requests_successful = detail.get("requests_successful", 0)
                success = detail.get("success", False)
                message = detail.get("message", "")
                
                self.account_finished.emit(account_name, requests_handled, requests_successful, success, message)
            
            # 发送完成信号
            if not self.is_cancelled:
                total_handled = results.get("total_requests_handled", 0)
                total_successful = results.get("total_requests_successful", 0)
                processed_accounts = results.get("processed_accounts", 0)
                
                if total_handled > 0:
                    success_rate = (total_successful / total_handled * 100)
                    summary = f"好友申请处理完成：处理{processed_accounts}个账号，同意{total_successful}/{total_handled}个申请，成功率{success_rate:.1f}%"
                else:
                    summary = f"好友申请处理完成：检查了{processed_accounts}个账号，没有收到好友申请"
                
                stats = {
                    "total_handled": total_handled,
                    "total_successful": total_successful,
                    "processed_accounts": processed_accounts
                }
                self.batch_finished.emit(True, summary, stats)
                
        except Exception as e:
            self.batch_finished.emit(False, f"执行失败: {str(e)}", {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchEatWorker(QThread):
    """批量吃白食任务工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前阶段, 状态
    phase_finished = Signal(str, bool, str)        # 阶段名称, 是否成功, 消息
    batch_finished = Signal(bool, str, dict)       # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager, max_accounts: int = None):
        super().__init__()
        self.manager = manager
        self.max_accounts = max_accounts
        self.is_cancelled = False
        
    def run(self):
        """执行完整的吃白食任务循环"""
        try:
            # 创建添油管理器来收集账号数据
            from src.delicious_town_bot.utils.friend_oil_manager import FriendOilManager
            oil_manager = FriendOilManager(self.manager)
            
            # 收集账号餐厅ID
            self.progress_updated.emit(0, 0, "准备阶段", "正在收集账号餐厅ID...")
            accounts_data = oil_manager.collect_account_restaurant_ids(self.max_accounts)
            
            if self.is_cancelled:
                return
            
            # 过滤有效账号
            valid_accounts = [acc for acc in accounts_data if acc.get('res_id')]
            
            if not valid_accounts:
                self.batch_finished.emit(False, "没有找到有效的餐厅ID", {})
                return
            
            # 使用吃白食任务循环方法
            from src.delicious_town_bot.actions.friend import FriendActions
            
            # 使用第一个有效账号创建FriendActions实例来调用批量方法
            first_account = valid_accounts[0]
            cookie_dict = {"PHPSESSID": first_account['cookie']}
            friend_action = FriendActions(key=first_account['key'], cookie=cookie_dict)
            
            # 设置进度监控
            total_phases = 1  # 只有吃白食一个阶段
            current_phase = 0
            
            self.progress_updated.emit(current_phase, total_phases, "开始吃白食任务", "正在启动吃白食循环...")
            
            # 调用完整的吃白食任务循环方法
            results = friend_action.batch_eat_cycle_complete(valid_accounts)
            
            if self.is_cancelled:
                return
            
            # 提取结果数据
            eat_results = results.get("eat_results", {})
            overall_success = results.get("overall_success", False)
            summary = results.get("summary", "")
            
            # 发送阶段完成信号
            self.phase_finished.emit("吃白食循环", overall_success, "完成批量吃白食")
            
            # 构建统计数据
            if eat_results:
                eat_success = eat_results.get("successful_eats", 0)
                processed_accounts = eat_results.get("processed_accounts", 0)
                
                stats = {
                    "eat_success": eat_success,
                    "processed_accounts": processed_accounts
                }
                self.batch_finished.emit(overall_success, summary, stats)
                
        except Exception as e:
            self.batch_finished.emit(False, f"执行失败: {str(e)}", {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchEndEatWorker(QThread):
    """批量结束吃白食工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str)      # 账号名, 是否成功, 消息
    batch_finished = Signal(bool, str, dict)       # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager, max_accounts: int = None):
        super().__init__()
        self.manager = manager
        self.max_accounts = max_accounts
        self.is_cancelled = False
        
    def run(self):
        """执行批量结束吃白食"""
        try:
            # 创建添油管理器来收集账号数据
            from src.delicious_town_bot.utils.friend_oil_manager import FriendOilManager
            oil_manager = FriendOilManager(self.manager)
            
            # 收集账号数据
            self.progress_updated.emit(0, 0, "准备阶段", "正在收集账号数据...")
            accounts_data = oil_manager.collect_account_restaurant_ids(self.max_accounts)
            
            if self.is_cancelled:
                return
            
            # 过滤有效账号
            valid_accounts = [acc for acc in accounts_data if acc.get('key')]
            
            if not valid_accounts:
                self.batch_finished.emit(False, "没有找到有效的账号", {})
                return
            
            # 使用结束吃白食方法
            from src.delicious_town_bot.actions.friend import FriendActions
            
            # 使用第一个有效账号创建FriendActions实例来调用批量方法
            first_account = valid_accounts[0]
            cookie_dict = {"PHPSESSID": first_account['cookie']}
            friend_action = FriendActions(key=first_account['key'], cookie=cookie_dict)
            
            # 调用批量结束吃白食方法
            results = friend_action.batch_end_dine_and_dash(valid_accounts)
            
            if self.is_cancelled:
                return
            
            # 提取结果数据
            overall_success = results.get("successful_ends", 0) > results.get("failed_ends", 0)
            processed_accounts = results.get("processed_accounts", 0)
            successful_ends = results.get("successful_ends", 0)
            
            # 发送每个账号的结果信号
            for detail in results.get("account_details", []):
                if self.is_cancelled:
                    break
                    
                account_name = detail.get("account_name", "")
                success = detail.get("success", False)
                message = detail.get("message", "")
                
                self.account_finished.emit(account_name, success, message)
            
            # 发送完成信号
            if not self.is_cancelled:
                if processed_accounts > 0:
                    success_rate = (successful_ends / processed_accounts * 100)
                    summary = f"结束吃白食完成：处理{processed_accounts}个账号，成功{successful_ends}个，成功率{success_rate:.1f}%"
                else:
                    summary = "结束吃白食完成：没有找到有效账号"
                
                stats = {
                    "successful_ends": successful_ends,
                    "processed_accounts": processed_accounts
                }
                self.batch_finished.emit(overall_success, summary, stats)
                
        except Exception as e:
            self.batch_finished.emit(False, f"执行失败: {str(e)}", {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class RefreshFriendsCacheWorker(QThread):
    """刷新好友缓存工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, int, bool, str)  # 账号名, 好友数, 是否成功, 消息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager):
        super().__init__()
        self.manager = manager
        self.is_cancelled = False
        
    def run(self):
        """执行刷新好友缓存"""
        try:
            from src.delicious_town_bot.utils.friend_cache_manager import FriendCacheManager
            cache_manager = FriendCacheManager()
            
            # 调用批量刷新方法
            results = cache_manager.refresh_all_accounts_friends_cache(self.manager)
            
            if self.is_cancelled:
                return
            
            # 发送每个账号的结果信号
            for detail in results.get("account_details", []):
                if self.is_cancelled:
                    break
                    
                account_name = detail.get("account_name", "")
                friends_count = detail.get("friends_count", 0)
                success = detail.get("success", False)
                message = detail.get("message", "")
                
                self.account_finished.emit(account_name, friends_count, success, message)
            
            # 发送完成信号
            if not self.is_cancelled:
                successful_refreshes = results.get("successful_refreshes", 0)
                total_accounts = results.get("total_accounts", 0)
                
                if total_accounts > 0:
                    success_rate = (successful_refreshes / total_accounts * 100)
                    summary = f"好友缓存刷新完成：处理{total_accounts}个账号，成功{successful_refreshes}个，成功率{success_rate:.1f}%"
                    overall_success = successful_refreshes > 0
                else:
                    summary = "好友缓存刷新完成：没有找到有效账号"
                    overall_success = False
                
                stats = {
                    "successful_refreshes": successful_refreshes,
                    "total_accounts": total_accounts
                }
                self.batch_finished.emit(overall_success, summary, stats)
                
        except Exception as e:
            self.batch_finished.emit(False, f"执行失败: {str(e)}", {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchSigninWorker(QThread):
    """批量签到工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    signin_finished = Signal(int, str, bool, str)  # 账号ID, 账号名, 是否成功, 消息
    batch_finished = Signal(bool, str, dict)    # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, account_list: List[Dict], interval_seconds: int = 1):
        super().__init__()
        self.account_list = account_list
        self.interval_seconds = interval_seconds
        self.is_cancelled = False
        self.stats = {"success": 0, "failed": 0, "skipped": 0}
        
    def run(self):
        """批量执行签到"""
        total_count = len(self.account_list)
        
        for i, account in enumerate(self.account_list):
            if self.is_cancelled:
                break
                
            account_id = account["id"]
            username = account["username"]
            key = account.get("key")
            
            # 发送进度信号
            self.progress_updated.emit(i + 1, total_count, username, "正在签到...")
            
            # 检查Key是否有效
            if not key:
                self.signin_finished.emit(account_id, username, False, "账号无Key，跳过")
                self.stats["skipped"] += 1
                continue
            
            # 执行签到
            try:
                cookie_value = account.get("cookie", "123")
                cookie_dict = {"PHPSESSID": cookie_value}
                daily_action = DailyActions(key=key, cookie=cookie_dict)
                
                success, result = daily_action.sign_in()
                
                if success:
                    self.stats["success"] += 1
                    # 提取奖励信息
                    if isinstance(result, dict) and "item_gained" in result:
                        message = f"签到成功，获得: {result['item_gained']}"
                    else:
                        message = "签到成功"
                else:
                    self.stats["failed"] += 1
                    message = str(result)
                
                # 发送结果信号
                self.signin_finished.emit(account_id, username, success, message)
                
            except Exception as e:
                error_msg = f"签到异常: {str(e)}"
                self.signin_finished.emit(account_id, username, False, error_msg)
                self.stats["failed"] += 1
            
            # 间隔等待
            if i < total_count - 1 and not self.is_cancelled:
                time.sleep(self.interval_seconds)
        
        # 发送批次完成信号
        if not self.is_cancelled:
            success_rate = self.stats["success"] / total_count * 100 if total_count > 0 else 0
            summary = f"批量签到完成：成功{self.stats['success']}个，失败{self.stats['failed']}个，跳过{self.stats['skipped']}个，成功率{success_rate:.1f}%"
            self.batch_finished.emit(True, summary, self.stats)
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class RestaurantIdUpdateWorker(QThread):
    """餐厅ID更新工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, str)  # 账号名, 是否成功, 餐厅ID, 消息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager, max_accounts: int = None):
        super().__init__()
        self.manager = manager
        self.max_accounts = max_accounts
        self.is_cancelled = False
        
    def run(self):
        """执行餐厅ID批量更新"""
        try:
            # 创建餐厅ID管理器
            restaurant_manager = RestaurantIdManager()
            
            # 执行批量更新
            self.progress_updated.emit(0, 0, "正在批量更新餐厅ID", "准备中...")
            
            results = restaurant_manager.batch_update_restaurant_ids(self.max_accounts)
            
            if self.is_cancelled:
                return
            
            # 发送每个账号的结果信号
            for detail in results.get("account_details", []):
                if self.is_cancelled:
                    break
                    
                account_name = detail.get("username", "")
                success = detail.get("success", False)
                res_id = detail.get("res_id", "")
                message = detail.get("message", "")
                
                self.account_finished.emit(account_name, success, str(res_id), message)
            
            # 发送批次完成信号
            if not self.is_cancelled:
                overall_success = results.get("successful_updates", 0) > 0
                summary = results.get("summary", "")
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"餐厅ID更新失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class SpecialFoodBuyWorker(QThread):
    """特价菜批量购买工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, account_list: List[Dict], quantity: int = 1):
        super().__init__()
        self.account_list = account_list
        self.quantity = quantity
        self.is_cancelled = False
        
    def run(self):
        """执行特价菜批量购买"""
        try:
            from src.delicious_town_bot.utils.special_food_manager import SpecialFoodManager
            
            # 创建特价菜管理器
            special_food_manager = SpecialFoodManager()
            
            total_accounts = len(self.account_list)
            successful_purchases = 0
            failed_purchases = 0
            already_completed = 0
            sold_out_detected = False
            account_details = []
            
            self.progress_updated.emit(0, total_accounts, "准备中...", "初始化")
            
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                
                username = account['username']
                account_id = account['id'] 
                key = account['key']
                cookie = account['cookie']
                
                self.progress_updated.emit(i + 1, total_accounts, username, "购买中...")
                
                if not key:
                    message = "没有Key"
                    self.account_finished.emit(username, False, message, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": message,
                        "already_completed": False
                    })
                    continue
                
                # 为单个账号购买特价菜（强制购买，因为是用户选中的）
                purchase_result = special_food_manager.buy_special_food_for_account(
                    account_id, key, cookie, self.quantity, force=True
                )
                
                success = purchase_result.get('success', False)
                message = purchase_result.get('message', '')
                already_done = purchase_result.get('already_completed', False)
                
                # 构建详细信息
                detail_info = {}
                if purchase_result.get("food_name"):
                    detail_info["food_name"] = purchase_result["food_name"]
                if purchase_result.get("quantity"):
                    detail_info["quantity"] = purchase_result["quantity"]
                if purchase_result.get("gold_spent"):
                    detail_info["gold_spent"] = purchase_result["gold_spent"]
                
                # 发送单个账号完成信号
                self.account_finished.emit(username, success, message, detail_info)
                
                # 更新统计
                if success:
                    successful_purchases += 1
                elif already_done:
                    already_completed += 1
                else:
                    failed_purchases += 1
                    # 检查是否售罄
                    if purchase_result.get('is_sold_out'):
                        sold_out_detected = True
                        # 为剩余账号标记失败
                        for remaining in self.account_list[i+1:]:
                            if remaining['key']:
                                special_food_manager.mark_task_failed(
                                    remaining['id'], "特价菜已售罄"
                                )
                        break
                
                account_details.append({
                    "username": username,
                    "success": success,
                    "message": message,
                    "already_completed": already_done,
                    "food_name": detail_info.get("food_name"),
                    "quantity": detail_info.get("quantity"),
                    "gold_spent": detail_info.get("gold_spent")
                })
                
                # 避免请求过快
                if i < total_accounts - 1:
                    import time
                    time.sleep(1)
            
            # 计算成功率和生成汇总
            processed_accounts = successful_purchases + failed_purchases + already_completed
            success_rate = (successful_purchases / processed_accounts * 100) if processed_accounts > 0 else 0
            
            # 构建结果字典
            results = {
                "total_accounts": total_accounts,
                "processed_accounts": processed_accounts,
                "successful_purchases": successful_purchases,
                "failed_purchases": failed_purchases,
                "already_completed": already_completed,
                "sold_out_detected": sold_out_detected,
                "success_rate": success_rate,
                "account_details": account_details
            }
            
            summary = f"购买完成: 成功{successful_purchases}个, 失败{failed_purchases}个, 已完成{already_completed}个, 成功率{success_rate:.1f}%"
            
            # 发送批次完成信号
            if not self.is_cancelled:
                overall_success = successful_purchases > 0
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"特价菜批量购买失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class ActiveRewardWorker(QThread):
    """活跃度奖励领取工作线程"""
    finished = Signal(bool, str)
    progress = Signal(str)
    
    def __init__(self, accounts: List[Any]):
        super().__init__()
        self.accounts = accounts
        self.should_stop = False
    
    def stop(self):
        """停止操作"""
        self.should_stop = True
    
    def run(self):
        """执行活跃度奖励领取"""
        try:
            total_accounts = len(self.accounts)
            success_count = 0
            failed_count = 0
            
            self.progress.emit(f"开始为 {total_accounts} 个账号领取活跃度奖励...")
            
            for i, account in enumerate(self.accounts):
                if self.should_stop:
                    self.progress.emit("操作已被用户取消")
                    break
                
                username = account.username
                self.progress.emit(f"[{i+1}/{total_accounts}] 正在为账号 {username} 领取活跃度奖励...")
                
                try:
                    # 检查账号是否有key
                    if not account.key:
                        self.progress.emit(f"[{i+1}/{total_accounts}] 账号 {username} 没有Key，跳过")
                        failed_count += 1
                        continue
                    
                    # 创建活跃度任务操作实例
                    cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
                    active_task_action = ActiveTaskAction(key=account.key, cookie=cookie_dict)
                    
                    # 批量领取所有活跃度奖励
                    result = active_task_action.batch_receive_awards()
                    
                    if result["success"]:
                        success_count += 1
                        reward_info = ""
                        if result["total_rewards"]:
                            reward_info = f" - 获得: {'; '.join(result['total_rewards'])}"
                        self.progress.emit(f"[{i+1}/{total_accounts}] ✅ {username}: 成功领取 {result['success_count']}/{result['total_attempts']} 个奖励{reward_info}")
                    else:
                        failed_count += 1
                        self.progress.emit(f"[{i+1}/{total_accounts}] ❌ {username}: {result['message']}")
                
                except Exception as e:
                    failed_count += 1
                    self.progress.emit(f"[{i+1}/{total_accounts}] ❌ {username}: 领取活跃度奖励时发生异常: {str(e)}")
                
                # 避免请求过快
                if i < len(self.accounts) - 1:
                    time.sleep(1)
            
            # 生成最终结果
            if self.should_stop:
                summary = f"操作被取消 - 已处理 {success_count + failed_count}/{total_accounts} 个账号"
                self.finished.emit(False, summary)
            else:
                success_rate = (success_count / total_accounts * 100) if total_accounts > 0 else 0
                summary = f"活跃度奖励领取完成！成功: {success_count}，失败: {failed_count}，成功率: {success_rate:.1f}%"
                self.finished.emit(success_count > 0, summary)
                
        except Exception as e:
            self.finished.emit(False, f"活跃度奖励领取过程中发生异常: {str(e)}")


class BatchCupboardWorker(QThread):
    """批量翻橱柜工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, manager: AccountManager, max_accounts: int = None):
        super().__init__()
        self.manager = manager
        self.max_accounts = max_accounts
        self.is_cancelled = False
        
    def run(self):
        """执行批量翻橱柜任务"""
        try:
            # 创建添油管理器来收集账号数据
            from src.delicious_town_bot.utils.friend_oil_manager import FriendOilManager
            oil_manager = FriendOilManager(self.manager)
            
            # 收集账号餐厅ID
            self.progress_updated.emit(0, 0, "准备阶段", "正在收集账号餐厅ID...")
            accounts_data = oil_manager.collect_account_restaurant_ids(self.max_accounts)
            
            if self.is_cancelled:
                return
            
            # 过滤有效账号
            valid_accounts = [acc for acc in accounts_data if acc.get('res_id')]
            
            if not valid_accounts:
                self.batch_finished.emit(False, "没有找到有效的餐厅ID", {})
                return
            
            # 使用FriendActions调用批量翻橱柜方法
            from src.delicious_town_bot.actions.friend import FriendActions
            
            # 使用第一个有效账号创建FriendActions实例来调用批量方法
            first_account = valid_accounts[0]
            cookie_dict = {"PHPSESSID": first_account['cookie']}
            friend_action = FriendActions(key=first_account['key'], cookie=cookie_dict)
            
            # 设置进度监控
            total_count = len(valid_accounts)
            self.progress_updated.emit(0, total_count, "开始批量处理", "正在翻橱柜...")
            
            # 调用批量循环翻橱柜方法
            results = friend_action.batch_cycle_cupboard_for_friends(valid_accounts)
            
            if self.is_cancelled:
                return
            
            # 发送每个账号的详细结果信号
            for detail in results.get("account_details", []):
                if self.is_cancelled:
                    break
                    
                account_name = detail.get("account_name", "")
                target_account = detail.get("target_account", "")
                success = detail.get("success", False)
                cupboards_success = detail.get("cupboards_success", 0)
                cupboards_failed = detail.get("cupboards_failed", 0)
                energy_cost = detail.get("energy_cost", 0)
                
                if success:
                    detail_msg = f"翻橱柜 {cupboards_success} 个格子，消耗 {energy_cost} 体力"
                else:
                    detail_msg = detail.get("message", "翻橱柜失败")
                
                detail_info = {
                    "target_account": target_account,
                    "cupboards_success": cupboards_success,
                    "cupboards_failed": cupboards_failed,
                    "energy_cost": energy_cost
                }
                
                self.account_finished.emit(account_name, success, detail_msg, detail_info)
            
            # 发送完成信号
            if not self.is_cancelled:
                successful_cupboards = results.get("successful_cupboards", 0)
                failed_cupboards = results.get("failed_cupboards", 0)
                processed_accounts = results.get("processed_accounts", 0)
                total_energy_cost = results.get("total_energy_cost", 0)
                
                total_attempts = successful_cupboards + failed_cupboards
                success_rate = (successful_cupboards / total_attempts * 100) if total_attempts > 0 else 0
                
                summary = f"翻橱柜完成：处理{processed_accounts}个账号，成功翻{successful_cupboards}个格子，失败{failed_cupboards}个，消耗{total_energy_cost}体力，成功率{success_rate:.1f}%"
                
                stats = {
                    "successful_cupboards": successful_cupboards,
                    "failed_cupboards": failed_cupboards,
                    "processed_accounts": processed_accounts,
                    "total_energy_cost": total_energy_cost
                }
                
                overall_success = successful_cupboards > 0
                self.batch_finished.emit(overall_success, summary, stats)
                
        except Exception as e:
            self.batch_finished.emit(False, f"执行失败: {str(e)}", {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchEquipmentEnhanceWorker(QThread):
    """批量强化厨具工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, account_list: List[Dict]):
        super().__init__()
        self.account_list = account_list
        self.is_cancelled = False
        
    def run(self):
        """执行批量强化厨具任务"""
        try:
            from src.delicious_town_bot.actions.shop import ShopAction
            from src.delicious_town_bot.actions.user_card import UserCardAction
            
            total_accounts = len(self.account_list)
            successful_accounts = 0
            failed_accounts = 0
            account_details = []
            total_equipment_processed = 0
            
            self.progress_updated.emit(0, total_accounts, "准备中...", "初始化")
            
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                
                username = account['username']
                key = account['key']
                cookie = account['cookie']
                
                self.progress_updated.emit(i + 1, total_accounts, username, "开始强化厨具任务...")
                
                if not key:
                    message = "没有Key"
                    self.account_finished.emit(username, False, message, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": message,
                        "equipment_processed": 0
                    })
                    failed_accounts += 1
                    continue
                
                try:
                    # 创建必要的Action实例
                    cookie_dict = {"PHPSESSID": cookie}
                    shop_action = ShopAction(key=key, cookie=cookie_dict)
                    user_card_action = UserCardAction(key=key, cookie=cookie_dict)
                    
                    account_equipment_processed = 0
                    account_success = True
                    details = []
                    
                    # 步骤1: 购买12次见习装备（3种装备，每种4次）
                    self.progress_updated.emit(i + 1, total_accounts, username, "购买见习装备...")
                    print(f"[*] {username}: 开始购买见习装备")
                    
                    purchase_result = shop_action.buy_novice_equipment_daily()
                    
                    if purchase_result.get("success"):
                        purchased_count = purchase_result.get("total_purchased", 0)
                        details.append(f"购买见习装备: {purchased_count}/12 件")
                        print(f"[+] {username}: 购买见习装备成功 {purchased_count}/12 件")
                        
                        if purchased_count < 12:
                            details.append(f"⚠️ 购买不完整，将处理现有装备")
                    else:
                        details.append(f"❌ 购买见习装备失败: {purchase_result.get('message', '未知错误')}")
                        account_success = False
                        print(f"[!] {username}: 购买见习装备失败")
                    
                    # 步骤2: 等待片刻让装备生效
                    import time
                    time.sleep(2)
                    
                    # 步骤3: 自动处理见习装备（强化1个，分解其余）
                    if account_success or purchase_result.get("total_purchased", 0) > 0:
                        self.progress_updated.emit(i + 1, total_accounts, username, "处理见习装备...")
                        print(f"[*] {username}: 开始自动处理见习装备")
                        
                        process_result = user_card_action.auto_process_novice_equipment()
                        
                        if process_result.get("success"):
                            processed_count = process_result.get("total_processed", 0)
                            enhanced_equipment = process_result.get("enhanced_equipment")
                            resolved_equipment = process_result.get("resolved_equipment", [])
                            
                            account_equipment_processed = processed_count
                            total_equipment_processed += processed_count
                            
                            if enhanced_equipment:
                                details.append(f"✅ 强化: {enhanced_equipment['name']}")
                            
                            if resolved_equipment:
                                details.append(f"⚡ 分解: {len(resolved_equipment)} 件装备")
                            
                            details.append(f"总处理: {processed_count} 件装备")
                            print(f"[+] {username}: 装备处理成功，处理 {processed_count} 件装备")
                        else:
                            error_msg = process_result.get("message", "处理失败")
                            details.append(f"❌ 装备处理失败: {error_msg}")
                            account_success = False
                            print(f"[!] {username}: 装备处理失败: {error_msg}")
                    
                    # 构建账号结果
                    if account_success:
                        successful_accounts += 1
                        final_message = "强化厨具任务完成：" + "；".join(details)
                        success_icon = "✅"
                    else:
                        failed_accounts += 1
                        final_message = "强化厨具任务失败：" + "；".join(details)
                        success_icon = "❌"
                    
                    detail_info = {
                        "equipment_processed": account_equipment_processed,
                        "details": details
                    }
                    
                    self.account_finished.emit(username, account_success, final_message, detail_info)
                    
                    account_details.append({
                        "username": username,
                        "success": account_success,
                        "message": final_message,
                        "equipment_processed": account_equipment_processed
                    })
                    
                    print(f"{success_icon} {username}: {final_message}")
                    
                except Exception as e:
                    failed_accounts += 1
                    error_msg = f"强化厨具任务异常: {str(e)}"
                    self.account_finished.emit(username, False, error_msg, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": error_msg,
                        "equipment_processed": 0
                    })
                    print(f"[Error] {username}: {error_msg}")
                
                # 避免请求过快
                if i < total_accounts - 1:
                    time.sleep(2)
            
            # 计算结果统计
            success_rate = (successful_accounts / total_accounts * 100) if total_accounts > 0 else 0
            
            results = {
                "total_accounts": total_accounts,
                "successful_accounts": successful_accounts,
                "failed_accounts": failed_accounts,
                "success_rate": success_rate,
                "total_equipment_processed": total_equipment_processed,
                "account_details": account_details
            }
            
            # 生成总结消息
            if successful_accounts == total_accounts:
                summary = f"✅ 强化厨具任务全部完成！成功 {successful_accounts} 个账号，总计处理 {total_equipment_processed} 件装备，成功率 100%"
                overall_success = True
            elif successful_accounts > 0:
                summary = f"⚠️ 强化厨具任务部分完成：成功 {successful_accounts} 个，失败 {failed_accounts} 个，总计处理 {total_equipment_processed} 件装备，成功率 {success_rate:.1f}%"
                overall_success = True
            else:
                summary = f"❌ 强化厨具任务全部失败：{total_accounts} 个账号都未能完成任务"
                overall_success = False
            
            if not self.is_cancelled:
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"批量强化厨具任务失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchGemRefiningWorker(QThread):
    """批量精炼宝石工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, account_list: List[Dict]):
        super().__init__()
        self.account_list = account_list
        self.is_cancelled = False
        
    def run(self):
        """执行批量精炼宝石任务"""
        try:
            from src.delicious_town_bot.actions.gem_refining import GemRefiningAction
            
            total_accounts = len(self.account_list)
            successful_accounts = 0
            failed_accounts = 0
            account_details = []
            total_cost = 0
            total_refined = 0
            
            self.progress_updated.emit(0, total_accounts, "准备中...", "初始化")
            
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                
                username = account['username']
                key = account['key']
                cookie = account['cookie']
                
                self.progress_updated.emit(i + 1, total_accounts, username, "开始精炼宝石任务...")
                
                if not key:
                    message = "没有Key"
                    self.account_finished.emit(username, False, message, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": message,
                        "cost": 0,
                        "refined": False
                    })
                    failed_accounts += 1
                    continue
                
                try:
                    # 创建精炼宝石Action实例
                    cookie_dict = {"PHPSESSID": cookie}
                    gem_action = GemRefiningAction(key=key, cookie=cookie_dict)
                    
                    account_cost = 0
                    account_refined = False
                    account_success = True
                    details = []
                    
                    # 执行完整的每日宝石精炼任务
                    self.progress_updated.emit(i + 1, total_accounts, username, "执行精炼宝石任务...")
                    print(f"[*] {username}: 开始每日宝石精炼任务")
                    
                    result = gem_action.complete_daily_gem_refining()
                    
                    if result.get("success"):
                        # 任务成功
                        successful_accounts += 1
                        account_cost = result.get("total_cost", 0)
                        total_cost += account_cost
                        
                        # 检查是否成功精炼
                        refine_result = result.get("refine_result", {})
                        refined_gem = refine_result.get("refined_gem")
                        if refined_gem:
                            account_refined = True
                            total_refined += 1
                            original_name = refined_gem.get("original_name", "智慧原石")
                            details.append(f"✅ 精炼: {original_name}")
                        
                        # 购买信息
                        purchase_result = result.get("purchase_result", {})
                        if purchase_result.get("success"):
                            purchased_count = purchase_result.get("total_purchased", 0)
                            details.append(f"🛒 购买材料: {purchased_count}/2 种")
                        
                        if account_cost > 0:
                            details.append(f"💰 消耗: {account_cost} 金币")
                        
                        final_message = f"精炼宝石任务完成：{'; '.join(details)}"
                        success_icon = "✅"
                        
                        print(f"[+] {username}: 精炼宝石任务成功，消耗 {account_cost} 金币")
                    else:
                        # 任务失败
                        failed_accounts += 1
                        account_success = False
                        error_msg = result.get("message", "精炼宝石任务失败")
                        
                        # 尝试获取部分成功信息
                        purchase_result = result.get("purchase_result")
                        if purchase_result and purchase_result.get("success"):
                            account_cost = purchase_result.get("total_cost", 0)
                            total_cost += account_cost
                            purchased_count = purchase_result.get("total_purchased", 0)
                            details.append(f"🛒 购买材料: {purchased_count}/2 种")
                            if account_cost > 0:
                                details.append(f"💰 消耗: {account_cost} 金币")
                        
                        details.append(f"❌ 错误: {error_msg}")
                        final_message = f"精炼宝石任务失败：{'; '.join(details)}"
                        success_icon = "❌"
                        
                        print(f"[!] {username}: 精炼宝石任务失败: {error_msg}")
                    
                    # 构建账号结果
                    detail_info = {
                        "cost": account_cost,
                        "refined": account_refined,
                        "details": details
                    }
                    
                    self.account_finished.emit(username, account_success, final_message, detail_info)
                    
                    account_details.append({
                        "username": username,
                        "success": account_success,
                        "message": final_message,
                        "cost": account_cost,
                        "refined": account_refined
                    })
                    
                    print(f"{success_icon} {username}: {final_message}")
                    
                except Exception as e:
                    failed_accounts += 1
                    error_msg = f"精炼宝石任务异常: {str(e)}"
                    self.account_finished.emit(username, False, error_msg, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": error_msg,
                        "cost": 0,
                        "refined": False
                    })
                    print(f"[Error] {username}: {error_msg}")
                
                # 避免请求过快
                if i < total_accounts - 1:
                    time.sleep(2)
            
            # 计算结果统计
            success_rate = (successful_accounts / total_accounts * 100) if total_accounts > 0 else 0
            
            results = {
                "total_accounts": total_accounts,
                "successful_accounts": successful_accounts,
                "failed_accounts": failed_accounts,
                "success_rate": success_rate,
                "total_cost": total_cost,
                "total_refined": total_refined,
                "account_details": account_details
            }
            
            # 生成总结消息
            cost_info = f"，总消耗 {total_cost} 金币" if total_cost > 0 else ""
            refined_info = f"，成功精炼 {total_refined} 颗宝石" if total_refined > 0 else ""
            
            if successful_accounts == total_accounts:
                summary = f"✅ 精炼宝石任务全部完成！成功 {successful_accounts} 个账号{cost_info}{refined_info}，成功率 100%"
                overall_success = True
            elif successful_accounts > 0:
                summary = f"⚠️ 精炼宝石任务部分完成：成功 {successful_accounts} 个，失败 {failed_accounts} 个{cost_info}{refined_info}，成功率 {success_rate:.1f}%"
                overall_success = True
            else:
                summary = f"❌ 精炼宝石任务全部失败：{total_accounts} 个账号都未能完成任务"
                overall_success = False
            
            if not self.is_cancelled:
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"批量精炼宝石任务失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class ShrineGuardWorker(QThread):
    """神殿守卫攻击工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, account_list: List[Dict]):
        super().__init__()
        self.account_list = account_list
        self.is_cancelled = False
        
    def run(self):
        """执行神殿守卫批量攻击"""
        try:
            from src.delicious_town_bot.actions.challenge import ChallengeAction
            from src.delicious_town_bot.constants import MissileType
            
            total_accounts = len(self.account_list)
            successful_attacks = 0
            failed_attacks = 0
            total_attacks = 0
            account_details = []
            
            self.progress_updated.emit(0, total_accounts, "准备中...", "初始化")
            
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                
                username = account['username']
                key = account['key']
                cookie = account['cookie']
                
                self.progress_updated.emit(i + 1, total_accounts, username, "攻击神殿守卫...")
                
                if not key:
                    message = "没有Key"
                    self.account_finished.emit(username, False, message, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": message,
                        "attacks": 0
                    })
                    continue
                
                # 创建挑战动作实例
                cookie_dict = {"PHPSESSID": cookie}
                challenge_action = ChallengeAction(key=key, cookie=cookie_dict)
                
                account_attacks = 0
                account_successful = 0
                last_message = ""
                
                # 为每个账号攻击神殿守卫，直到守卫被击败
                while True:
                    if self.is_cancelled:
                        break
                        
                    try:
                        # 获取神殿守卫信息，检查HP状态
                        shrine_info = challenge_action.get_shrine_info()
                        
                        if not shrine_info.get("success"):
                            last_message = f"获取神殿信息失败: {shrine_info.get('message', '未知错误')}"
                            break
                        
                        # 检查守卫HP
                        guard_data = shrine_info.get("data", {}).get("shrine_guard_info", {})
                        try:
                            guard_hp = int(guard_data.get("guard_hp", -1))
                        except (TypeError, ValueError):
                            guard_hp = -1
                        
                        # 如果守卫已被击败（HP <= 0），结束攻击
                        if guard_hp == 0:
                            last_message = f"神殿守卫已被击败！总共攻击{account_attacks}次"
                            break
                        
                        # 使用常规飞弹攻击神殿守卫
                        attack_result = challenge_action.attack_shrine_guard(MissileType.REGULAR)
                        account_attacks += 1
                        total_attacks += 1
                        
                        if attack_result.get("success"):
                            account_successful += 1
                            successful_attacks += 1
                            
                            # 解析攻击结果和检测击杀关键字
                            attack_info = attack_result.get("result", {})
                            damage = attack_info.get("damage", 0)
                            cost = attack_info.get("cost", 0)
                            attack_msg = attack_result.get("message", "")
                            
                            # 检测击杀关键字
                            if ("击杀" in attack_msg or "打败" in attack_msg or "胜利" in attack_msg):
                                last_message = f"成功击败神殿守卫！总共攻击{account_attacks}次，造成{damage}伤害"
                                break
                            else:
                                last_message = f"攻击成功{account_attacks}次，造成{damage}伤害，继续攻击..."
                        else:
                            error_message = attack_result.get('message', '未知错误')
                            
                            # 如果飞弹不足，尝试自动购买飞弹
                            if ("飞弹不足" in error_message or "没有飞弹" in error_message or 
                                "普通飞弹数量不足" in error_message or "需要:" in error_message):
                                try:
                                    # 尝试自动购买飞弹
                                    from src.delicious_town_bot.actions.shop import ShopAction
                                    import re
                                    
                                    shop_action = ShopAction(key=key, cookie=cookie_dict)
                                    
                                    # 神殿守卫常规飞弹的商品ID是5（根据参考代码）
                                    missile_goods_id = 5
                                    
                                    # 如果消息中包含"需要:N"，解析所需数量并购买10倍
                                    if "需要:" in error_message:
                                        match = re.search(r"需要:(\d+)", error_message)
                                        if match:
                                            needed = int(match.group(1))
                                            purchase_quantity = needed * 10  # 购买10倍所需数量
                                            print(f"[*] {username} 还差{needed}发飞弹，购买{purchase_quantity}个常规飞弹...")
                                        else:
                                            purchase_quantity = 100  # 默认购买100个
                                    else:
                                        purchase_quantity = 50  # 一般飞弹不足时购买50个
                                    
                                    purchase_result = shop_action.buy_item(goods_id=missile_goods_id, num=purchase_quantity)
                                    
                                    if purchase_result.get("success"):
                                        purchase_msg = purchase_result.get("message", "购买成功")
                                        print(f"[*] {username} 飞弹购买成功，继续攻击: {purchase_msg}")
                                        # 购买成功，继续下一次攻击（不计入失败）
                                        continue
                                    else:
                                        purchase_error = purchase_result.get("message", "购买失败")
                                        last_message = f"攻击失败: {error_message}，自动购买飞弹失败: {purchase_error}"
                                        failed_attacks += 1
                                        break
                                        
                                except Exception as e:
                                    last_message = f"攻击失败: {error_message}，自动购买飞弹时发生异常: {str(e)}"
                                    failed_attacks += 1
                                    break
                            else:
                                # 其他攻击失败原因
                                failed_attacks += 1
                                last_message = f"攻击失败: {error_message}"
                                break
                        
                        # 攻击间隔
                        import time
                        time.sleep(1)
                        
                    except Exception as e:
                        failed_attacks += 1
                        last_message = f"攻击异常: {str(e)}"
                        break
                
                # 构建详细信息
                detail_info = {
                    "attacks": account_attacks,
                    "successful": account_successful,
                    "failed": account_attacks - account_successful
                }
                
                success = account_attacks > 0
                final_message = f"完成{account_attacks}次攻击，成功{account_successful}次"
                
                # 发送单个账号完成信号
                self.account_finished.emit(username, success, final_message, detail_info)
                
                account_details.append({
                    "username": username,
                    "success": success,
                    "message": final_message,
                    "attacks": account_attacks,
                    "successful": account_successful
                })
                
                # 账号间隔
                if i < total_accounts - 1:
                    import time
                    time.sleep(1)
            
            # 计算成功率和生成汇总
            success_rate = (successful_attacks / total_attacks * 100) if total_attacks > 0 else 0
            
            # 构建结果字典
            results = {
                "total_accounts": total_accounts,
                "total_attacks": total_attacks,
                "successful_attacks": successful_attacks,
                "failed_attacks": failed_attacks,
                "success_rate": success_rate,
                "account_details": account_details
            }
            
            summary = f"神殿守卫攻击完成: 总攻击{total_attacks}次，成功{successful_attacks}次，失败{failed_attacks}次，成功率{success_rate:.1f}%"
            
            # 发送批次完成信号
            if not self.is_cancelled:
                overall_success = successful_attacks > 0
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"神殿守卫批量攻击失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class RockPaperScissorsWorker(QThread):
    """猜拳成功一次工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, account_list: List[Dict]):
        super().__init__()
        self.account_list = account_list
        self.is_cancelled = False
        
    def run(self):
        """执行猜拳任务"""
        try:
            import random
            
            total_accounts = len(self.account_list)
            successful_count = 0
            failed_count = 0
            account_details = []
            
            self.progress_updated.emit(0, total_accounts, "准备中...", "初始化")
            
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                
                username = account['username']
                key = account['key']
                cookie = account['cookie']
                
                self.progress_updated.emit(i + 1, total_accounts, username, "猜拳中...")
                
                if not key:
                    message = "没有Key"
                    self.account_finished.emit(username, False, message, {})
                    account_details.append({"username": username, "success": False, "message": message})
                    failed_count += 1
                    continue
                
                try:
                    # 创建LotteryActions实例
                    cookie_dict = {"PHPSESSID": cookie}
                    lottery_action = LotteryActions(key=key, cookie=cookie_dict)
                    
                    # 尝试猜拳直到成功一次（最多尝试20次）
                    max_attempts = 20
                    success = False
                    last_result = ""
                    
                    print(f"[Info] {username} 开始猜拳任务，目标：成功一次")
                    
                    for attempt in range(max_attempts):
                        if self.is_cancelled:
                            break
                            
                        print(f"[Info] {username} 第{attempt+1}次尝试猜拳")
                        
                        # 随机选择出拳
                        move = random.choice([Move.ROCK, Move.SCISSORS, Move.PAPER])
                        result, details = lottery_action.play_rock_paper_scissors(move)
                        
                        print(f"[Debug] {username} 猜拳结果: result={result}, result.value={result.value}, details={details}")
                        print(f"[Debug] {username} GameResult.WIN={GameResult.WIN}, result==GameResult.WIN={result == GameResult.WIN}")
                        print(f"[Debug] {username} type(result)={type(result)}, type(GameResult.WIN)={type(GameResult.WIN)}")
                        
                        # 使用字符串值比较而不是枚举比较
                        if result.value == "赢":
                            success = True
                            last_result = f"第{attempt+1}次尝试成功！{details}"
                            print(f"[Success] {username} 猜拳任务完成！第{attempt+1}次尝试成功")
                            break
                        elif result.value == "平局":
                            last_result = f"第{attempt+1}次平局，继续尝试... ({details})"
                            print(f"[Info] {username} 第{attempt+1}次平局，继续尝试")
                        else:  # 输
                            last_result = f"第{attempt+1}次失败，继续尝试... ({details})"
                            print(f"[Info] {username} 第{attempt+1}次失败，继续尝试")
                        
                        # 短暂延迟
                        import time
                        time.sleep(0.5)
                    
                    if not success:
                        print(f"[Warning] {username} 尝试{max_attempts}次都未成功")
                    
                    if success:
                        successful_count += 1
                        self.account_finished.emit(username, True, "猜拳成功一次", {"details": last_result})
                        account_details.append({"username": username, "success": True, "message": "猜拳成功一次"})
                    else:
                        failed_count += 1
                        message = f"猜拳{max_attempts}次都未成功"
                        self.account_finished.emit(username, False, message, {"details": last_result})
                        account_details.append({"username": username, "success": False, "message": message})
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = f"猜拳时发生异常: {str(e)}"
                    self.account_finished.emit(username, False, error_msg, {})
                    account_details.append({"username": username, "success": False, "message": error_msg})
                
                # 避免请求过快
                if i < total_accounts - 1:
                    import time
                    time.sleep(1)
            
            # 计算结果
            success_rate = (successful_count / total_accounts * 100) if total_accounts > 0 else 0
            
            results = {
                "total_accounts": total_accounts,
                "successful_count": successful_count,
                "failed_count": failed_count,
                "success_rate": success_rate,
                "account_details": account_details
            }
            
            summary = f"猜拳任务完成: 成功{successful_count}个, 失败{failed_count}个, 成功率{success_rate:.1f}%"
            
            if not self.is_cancelled:
                overall_success = successful_count > 0
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"猜拳批量任务失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class GuessCupWorker(QThread):
    """猜酒杯成功一次工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, account_list: List[Dict]):
        super().__init__()
        self.account_list = account_list
        self.is_cancelled = False
        
    def run(self):
        """执行猜酒杯任务"""
        try:
            import random
            
            total_accounts = len(self.account_list)
            successful_count = 0
            failed_count = 0
            account_details = []
            
            self.progress_updated.emit(0, total_accounts, "准备中...", "初始化")
            
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                
                username = account['username']
                key = account['key']
                cookie = account['cookie']
                
                self.progress_updated.emit(i + 1, total_accounts, username, "猜酒杯中...")
                
                if not key:
                    message = "没有Key"
                    self.account_finished.emit(username, False, message, {})
                    account_details.append({"username": username, "success": False, "message": message})
                    failed_count += 1
                    continue
                
                try:
                    # 创建LotteryActions实例
                    cookie_dict = {"PHPSESSID": cookie}
                    lottery_action = LotteryActions(key=key, cookie=cookie_dict)
                    
                    # 尝试猜酒杯直到成功一次（最多尝试10次）
                    max_attempts = 10
                    success = False
                    last_result = ""
                    
                    print(f"[Info] {username} 开始猜酒杯任务，目标：成功一次")
                    
                    for attempt in range(max_attempts):
                        if self.is_cancelled:
                            break
                            
                        try:
                            print(f"[Info] {username} 第{attempt+1}次尝试猜酒杯")
                            
                            # 获取游戏状态
                            game_state = lottery_action.get_cup_game_info()
                            
                            # 随机选择一个杯子
                            choice = random.randint(1, game_state.max_cup_number)
                            result, details = lottery_action.guess_cup(choice)
                            
                            print(f"[Debug] {username} 猜酒杯结果: result={result}, result.value={result.value}, details={details}")
                            
                            # 使用字符串值比较
                            if result.value in ["猜中，游戏继续", "猜中最后一轮，游戏结束"]:
                                success = True
                                last_result = f"第{attempt+1}次尝试成功！{details}"
                                print(f"[Success] {username} 猜酒杯任务完成！第{attempt+1}次尝试成功")
                                break
                            else:  # 猜错，游戏结束
                                last_result = f"第{attempt+1}次猜错，继续尝试... ({details})"
                                print(f"[Info] {username} 第{attempt+1}次猜错，继续尝试")
                                
                        except Exception as game_error:
                            # 可能游戏已结束或未开始，尝试下一次
                            last_result = f"第{attempt+1}次游戏状态异常: {str(game_error)}"
                            print(f"[Warning] {username} 第{attempt+1}次游戏状态异常: {game_error}")
                            
                        # 短暂延迟
                        import time
                        time.sleep(1)
                    
                    if not success:
                        print(f"[Warning] {username} 尝试{max_attempts}次都未成功")
                    
                    if success:
                        successful_count += 1
                        self.account_finished.emit(username, True, "猜酒杯成功一次", {"details": last_result})
                        account_details.append({"username": username, "success": True, "message": "猜酒杯成功一次"})
                    else:
                        failed_count += 1
                        message = f"猜酒杯{max_attempts}次都未成功"
                        self.account_finished.emit(username, False, message, {"details": last_result})
                        account_details.append({"username": username, "success": False, "message": message})
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = f"猜酒杯时发生异常: {str(e)}"
                    self.account_finished.emit(username, False, error_msg, {})
                    account_details.append({"username": username, "success": False, "message": error_msg})
                
                # 避免请求过快
                if i < total_accounts - 1:
                    import time
                    time.sleep(1)
            
            # 计算结果
            success_rate = (successful_count / total_accounts * 100) if total_accounts > 0 else 0
            
            results = {
                "total_accounts": total_accounts,
                "successful_count": successful_count,
                "failed_count": failed_count,
                "success_rate": success_rate,
                "account_details": account_details
            }
            
            summary = f"猜酒杯任务完成: 成功{successful_count}个, 失败{failed_count}个, 成功率{success_rate:.1f}%"
            
            if not self.is_cancelled:
                overall_success = successful_count > 0
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"猜酒杯批量任务失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchVisitShopWorker(QThread):
    """批量巡店工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    account_finished = Signal(str, bool, str, dict)  # 账号名, 是否成功, 消息, 详细信息
    batch_finished = Signal(bool, str, dict)        # 是否全部成功, 总结消息, 统计数据

    def __init__(self, account_list: List[Dict]):
        super().__init__()
        self.account_list = account_list
        self.is_cancelled = False
        
    def run(self):
        """执行批量巡店任务"""
        try:
            from src.delicious_town_bot.actions.restaurant import RestaurantActions
            
            total_accounts = len(self.account_list)
            successful_accounts = 0
            failed_accounts = 0
            account_details = []
            
            self.progress_updated.emit(0, total_accounts, "准备中...", "初始化")
            
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                
                username = account["username"]
                key = account.get("key")
                cookie = account.get("cookie")
                
                self.progress_updated.emit(i + 1, total_accounts, username, "开始巡店...")
                
                if not key:
                    message = "没有Key"
                    self.account_finished.emit(username, False, message, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": message
                    })
                    failed_accounts += 1
                    continue
                
                try:
                    # 创建餐厅操作实例
                    cookie_dict = {"PHPSESSID": cookie} if cookie else None
                    restaurant_action = RestaurantActions(key=key, cookie=cookie_dict)
                    
                    # 执行巡店
                    self.progress_updated.emit(i + 1, total_accounts, username, "正在巡店...")
                    print(f"[*] {username}: 开始巡店")
                    
                    result = restaurant_action.visit_shop()
                    
                    if result.get("success"):
                        # 巡店成功
                        successful_accounts += 1
                        account_success = True
                        
                        # 获取座位信息
                        seat_info = result.get("seat_info", {})
                        details = []
                        
                        if seat_info.get("total_seats", 0) > 0:
                            details.append(f"总座位: {seat_info['total_seats']}")
                        
                        if seat_info.get("occupied_seats", 0) > 0:
                            details.append(f"占用: {seat_info['occupied_seats']}")
                        
                        if seat_info.get("roach_seats", 0) > 0:
                            details.append(f"蟑螂: {seat_info['roach_seats']}")
                        
                        if seat_info.get("dine_and_dash_seats", 0) > 0:
                            details.append(f"白食: {seat_info['dine_and_dash_seats']}")
                        
                        final_message = f"巡店完成：{'; '.join(details)}"
                        success_icon = "✅"
                        
                        print(f"[+] {username}: 巡店成功")
                    else:
                        # 巡店失败
                        failed_accounts += 1
                        account_success = False
                        error_msg = result.get("message", "巡店失败")
                        final_message = f"巡店失败：{error_msg}"
                        success_icon = "❌"
                        seat_info = {}
                        
                        print(f"[!] {username}: 巡店失败: {error_msg}")
                    
                    # 构建账号结果
                    detail_info = {
                        "username": username,
                        "success": account_success,
                        "message": final_message,
                        "seat_info": seat_info
                    }
                    
                    account_details.append(detail_info)
                    
                    # 发送账号完成信号
                    self.account_finished.emit(username, account_success, f"{success_icon} {final_message}", detail_info)
                    
                    # 短暂延迟
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    failed_accounts += 1
                    error_msg = f"巡店任务异常: {str(e)}"
                    self.account_finished.emit(username, False, error_msg, {})
                    account_details.append({
                        "username": username, 
                        "success": False, 
                        "message": error_msg
                    })
                    print(f"[!] {username}: {error_msg}")
            
            # 生成最终统计
            success_rate = (successful_accounts / total_accounts * 100) if total_accounts > 0 else 0
            
            results = {
                "total_accounts": total_accounts,
                "successful_accounts": successful_accounts,
                "failed_accounts": failed_accounts,
                "success_rate": success_rate,
                "account_details": account_details
            }
            
            if successful_accounts == total_accounts:
                summary = f"✅ 巡店任务全部完成！成功 {successful_accounts} 个账号，成功率 100%"
                overall_success = True
            elif successful_accounts > 0:
                summary = f"⚠️ 巡店任务部分完成：成功 {successful_accounts} 个，失败 {failed_accounts} 个，成功率 {success_rate:.1f}%"
                overall_success = True
            else:
                summary = f"❌ 巡店任务全部失败：{total_accounts} 个账号都未能完成巡店"
                overall_success = False
            
            if not self.is_cancelled:
                self.batch_finished.emit(overall_success, summary, results)
                
        except Exception as e:
            error_msg = f"批量巡店任务失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class BatchFacilityPlacementWorker(QThread):
    """批量摆放设施工作线程"""
    progress_updated = Signal(int, int, str, str)
    account_finished = Signal(str, bool, str, dict)
    batch_finished = Signal(bool, str, dict)
    
    def __init__(self, account_list):
        super().__init__()
        self.account_list = account_list
        self.is_cancelled = False
    
    def run(self):
        """执行批量摆放设施任务"""
        total_accounts = len(self.account_list)
        successful_accounts = 0
        failed_accounts = 0
        results = {}
        
        try:
            for i, account in enumerate(self.account_list):
                if self.is_cancelled:
                    break
                    
                username = account['username']
                key = account['key']
                cookie_dict = account.get('cookie_dict', {})
                
                try:
                    self.progress_updated.emit(i + 1, total_accounts, username, "开始摆放设施...")
                    
                    # 导入餐厅操作模块
                    from src.delicious_town_bot.actions.restaurant import RestaurantActions
                    
                    # 创建餐厅操作实例
                    try:
                        restaurant_action = RestaurantActions(key=key, cookie=cookie_dict)
                    except Exception as e:
                        self.progress_updated.emit(i + 1, total_accounts, username, f"初始化失败: {str(e)}")
                        self.account_finished.emit(username, False, f"初始化失败: {str(e)}", {})
                        failed_accounts += 1
                        continue
                    
                    # 执行摆放设施任务
                    self.progress_updated.emit(i + 1, total_accounts, username, "正在摆放设施...")
                    print(f"[*] {username}: 开始摆放设施任务")
                    
                    result = restaurant_action.complete_facility_placement_task()
                    
                    if result.get("success"):
                        # 摆放设施成功
                        successful_accounts += 1
                        
                        # 解析详细结果
                        details = result.get("details", {})
                        summary_parts = []
                        
                        if details.get("buy_mousetrap", {}).get("success"):
                            summary_parts.append("购买老鼠夹✓")
                        if details.get("buy_fuel_saver", {}).get("success"):
                            summary_parts.append("购买节油器✓")
                        if details.get("place_mousetrap", {}).get("success"):
                            summary_parts.append("摆放老鼠夹✓")
                        if details.get("place_fuel_saver", {}).get("success"):
                            summary_parts.append("摆放节油器✓")
                        
                        final_message = f"摆放设施完成：{'; '.join(summary_parts)}"
                        results[username] = {"success": True, "message": final_message, "details": details}
                        
                        print(f"[+] {username}: 摆放设施任务成功")
                        self.account_finished.emit(username, True, final_message, details)
                    else:
                        # 摆放设施失败
                        failed_accounts += 1
                        
                        error_msg = result.get("message", "摆放设施失败")
                        final_message = f"摆放设施失败：{error_msg}"
                        
                        results[username] = {"success": False, "message": final_message, "details": result.get("details", {})}
                        
                        print(f"[!] {username}: 摆放设施任务失败: {error_msg}")
                        self.account_finished.emit(username, False, final_message, result.get("details", {}))
                    
                    # 更新进度
                    self.progress_updated.emit(i + 1, total_accounts, username, "完成")
                    
                    # 短暂延迟避免请求过快
                    import time
                    time.sleep(1)
                    
                except Exception as e:
                    failed_accounts += 1
                    error_msg = f"摆放设施任务异常: {str(e)}"
                    results[username] = {"success": False, "message": error_msg, "details": {}}
                    
                    print(f"[Error] {username}: {error_msg}")
                    self.account_finished.emit(username, False, error_msg, {})
            
            # 生成批量执行总结
            if self.is_cancelled:
                summary = "❌ 摆放设施任务已取消"
                self.batch_finished.emit(False, summary, results)
            elif successful_accounts == total_accounts:
                summary = f"✅ 摆放设施任务全部完成！成功 {successful_accounts} 个账号，成功率 100%"
                self.batch_finished.emit(True, summary, results)
            elif successful_accounts > 0:
                success_rate = (successful_accounts / total_accounts) * 100
                summary = f"⚠️ 摆放设施任务部分完成：成功 {successful_accounts} 个，失败 {failed_accounts} 个，成功率 {success_rate:.1f}%"
                self.batch_finished.emit(True, summary, results)
            else:
                summary = f"❌ 摆放设施任务全部失败：{total_accounts} 个账号都未能完成摆放设施"
                self.batch_finished.emit(False, summary, results)
                
        except Exception as e:
            error_msg = f"批量摆放设施任务失败: {str(e)}"
            print(f"[Error] {error_msg}")
            self.batch_finished.emit(False, error_msg, {})
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True


class DailyTasksPage(QWidget):
    """日常任务管理主页面"""
    
    def __init__(self, manager: AccountManager, log_widget=None):
        super().__init__()
        self.manager = manager
        self.log_widget = log_widget
        self.task_data = {}  # 存储所有账号的任务数据
        
        self.load_worker = None
        self.signin_worker = None
        self.signin_thread = None
        self.oil_worker = None
        self.oil_thread = None
        self.roach_worker = None
        self.roach_thread = None
        self.friend_worker = None
        self.friend_thread = None
        self.restaurant_id_worker = None
        self.restaurant_id_thread = None
        self.special_food_worker = None
        self.special_food_thread = None
        self.rock_paper_scissors_worker = None
        self.rock_paper_scissors_thread = None
        self.guess_cup_worker = None
        self.guess_cup_thread = None
        self.shrine_guard_worker = None
        self.shrine_guard_thread = None
        self.active_reward_worker = None
        self.active_reward_thread = None
        self.cupboard_worker = None
        self.cupboard_thread = None
        self.equipment_worker = None
        self.equipment_thread = None
        self.gem_refining_worker = None
        self.gem_refining_thread = None
        self.visit_shop_worker = None
        self.visit_shop_thread = None
        self.facility_placement_worker = None
        self.facility_placement_thread = None
        
        self.setupUI()
        self.load_accounts()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("日常任务管理")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 控制面板（左对齐显示）
        control_panel_layout = QHBoxLayout()
        control_panel = self.create_control_panel()
        control_panel_layout.addWidget(control_panel)
        control_panel_layout.addStretch()  # 右侧留空
        control_panel_widget = QWidget()
        control_panel_widget.setLayout(control_panel_layout)
        layout.addWidget(control_panel_widget)
        
        # 主内容区域 - 改为垂直布局以适应小屏幕
        content_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上方：任务概览表格
        self.tasks_overview_widget = self.create_tasks_overview()
        content_splitter.addWidget(self.tasks_overview_widget)
        
        # 下方：详细任务信息
        self.task_details_widget = self.create_task_details()
        content_splitter.addWidget(self.task_details_widget)
        
        # 设置分割比例 - 由于表格有固定高度，调整比例更合理
        content_splitter.setStretchFactor(0, 1)  # 概览表格（固定高度）
        content_splitter.setStretchFactor(1, 1)  # 详细信息
        
        layout.addWidget(content_splitter)
        
        # 底部状态栏
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("准备就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.status_layout.addWidget(self.status_label)
        self.status_layout.addWidget(self.progress_bar)
        self.status_layout.addStretch()
        
        layout.addLayout(self.status_layout)
    
    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QGroupBox("操作控制")
        panel.setMinimumWidth(800)  # 拉宽基础操作框，更好利用水平空间
        panel.setMaximumWidth(960)  # 适当增加最大宽度
        layout = QVBoxLayout(panel)
        
        # 基础按钮 - 简化文字，设置统一样式（压缩高度）
        btn_style = "QPushButton { font-weight: bold; padding: 4px 6px; min-height: 22px; font-size: 12px; }"
        
        self.refresh_btn = QPushButton("🔄 刷新数据")
        self.refresh_btn.setStyleSheet(btn_style + "QPushButton { background-color: #17a2b8; color: white; }")
        self.refresh_btn.clicked.connect(self.refresh_task_data)
        
        self.batch_signin_btn = QPushButton("✅ 签到")
        self.batch_signin_btn.setStyleSheet(btn_style + "QPushButton { background-color: #28a745; color: white; }")
        self.batch_signin_btn.clicked.connect(self.start_batch_signin)
        
        self.batch_oil_btn = QPushButton("⛽ 添油")
        self.batch_oil_btn.setStyleSheet(btn_style + "QPushButton { background-color: #fd7e14; color: white; }")
        self.batch_oil_btn.clicked.connect(self.start_batch_cycle_oil)
        
        self.batch_roach_btn = QPushButton("🪳 蟑螂")
        self.batch_roach_btn.setStyleSheet(btn_style + "QPushButton { background-color: #6f42c1; color: white; }")
        self.batch_roach_btn.clicked.connect(self.start_batch_roach_cycle)
        
        self.batch_eat_btn = QPushButton("🍽️ 吃白食")
        self.batch_eat_btn.setStyleSheet(btn_style + "QPushButton { background-color: #dc3545; color: white; }")
        self.batch_eat_btn.clicked.connect(self.start_batch_eat_cycle)
        
        self.end_eat_btn = QPushButton("🚫 结束")
        self.end_eat_btn.setStyleSheet(btn_style + "QPushButton { background-color: #6c757d; color: white; }")
        self.end_eat_btn.clicked.connect(self.start_batch_end_eat)
        
        self.refresh_friends_btn = QPushButton("👥 好友")
        self.refresh_friends_btn.setStyleSheet(btn_style + "QPushButton { background-color: #17a2b8; color: white; }")
        self.refresh_friends_btn.clicked.connect(self.start_refresh_friends_cache)
        
        self.update_restaurant_id_btn = QPushButton("🏪 餐厅")
        self.update_restaurant_id_btn.setStyleSheet(btn_style + "QPushButton { background-color: #007bff; color: white; }")
        self.update_restaurant_id_btn.clicked.connect(self.start_update_restaurant_ids)
        
        self.special_food_btn = QPushButton("🛒 特价菜")
        self.special_food_btn.setStyleSheet(btn_style + "QPushButton { background-color: #ffc107; color: black; }")
        self.special_food_btn.clicked.connect(self.start_batch_special_food_buy)
        
        # 选择按钮 - 小尺寸（进一步压缩）
        small_btn_style = "QPushButton { font-size: 10px; padding: 3px 5px; min-height: 20px; }"
        
        self.select_all_btn = QPushButton("☑️ 全选")
        self.select_all_btn.setStyleSheet(small_btn_style + "QPushButton { background-color: #6c757d; color: white; }")
        self.select_all_btn.clicked.connect(self.select_all_accounts)
        
        self.select_none_btn = QPushButton("☐ 清空")
        self.select_none_btn.setStyleSheet(small_btn_style + "QPushButton { background-color: #6c757d; color: white; }")
        self.select_none_btn.clicked.connect(self.select_none_accounts)
        
        self.select_pending_btn = QPushButton("⏳ 待购")
        self.select_pending_btn.setStyleSheet(small_btn_style + "QPushButton { background-color: #17a2b8; color: white; }")
        self.select_pending_btn.clicked.connect(self.select_pending_accounts)
        
        self.select_with_key_btn = QPushButton("🔑 有Key")
        self.select_with_key_btn.setStyleSheet(small_btn_style + "QPushButton { background-color: #28a745; color: white; }")
        self.select_with_key_btn.clicked.connect(self.select_accounts_with_key)
        
        # 游戏任务按钮
        self.rock_paper_scissors_btn = QPushButton("✂️ 猜拳")
        self.rock_paper_scissors_btn.setStyleSheet(btn_style + "QPushButton { background-color: #fd7e14; color: white; }")
        self.rock_paper_scissors_btn.clicked.connect(self.start_batch_rock_paper_scissors)
        
        self.guess_cup_btn = QPushButton("🍷 猜杯")
        self.guess_cup_btn.setStyleSheet(btn_style + "QPushButton { background-color: #6f42c1; color: white; }")
        self.guess_cup_btn.clicked.connect(self.start_batch_guess_cup)
        
        self.batch_friend_btn = QPushButton("👫 申请")
        self.batch_friend_btn.setStyleSheet(btn_style + "QPushButton { background-color: #20c997; color: white; }")
        self.batch_friend_btn.clicked.connect(self.start_batch_friend_requests)
        
        self.shrine_guard_btn = QPushButton("🛡️ 守卫")
        self.shrine_guard_btn.setStyleSheet(btn_style + "QPushButton { background-color: #e83e8c; color: white; }")
        self.shrine_guard_btn.clicked.connect(self.start_batch_shrine_guard)
        
        self.active_reward_btn = QPushButton("🎁 活跃奖励")
        self.active_reward_btn.setStyleSheet(btn_style + "QPushButton { background-color: #17a2b8; color: white; }")
        self.active_reward_btn.clicked.connect(self.start_batch_active_rewards)
        
        self.batch_cupboard_btn = QPushButton("🗂️ 翻橱柜")
        self.batch_cupboard_btn.setStyleSheet(btn_style + "QPushButton { background-color: #28a745; color: white; }")
        self.batch_cupboard_btn.clicked.connect(self.start_batch_cupboard_cycle)
        
        self.batch_equipment_btn = QPushButton("🔧 强化厨具")
        self.batch_equipment_btn.setStyleSheet(btn_style + "QPushButton { background-color: #6f42c1; color: white; }")
        self.batch_equipment_btn.clicked.connect(self.start_batch_equipment_enhance)
        
        self.batch_gem_refining_btn = QPushButton("💎 精炼宝石")
        self.batch_gem_refining_btn.setStyleSheet(btn_style + "QPushButton { background-color: #e83e8c; color: white; }")
        self.batch_gem_refining_btn.clicked.connect(self.start_batch_gem_refining)
        
        self.batch_visit_shop_btn = QPushButton("🏪 巡店")
        self.batch_visit_shop_btn.setStyleSheet(btn_style + "QPushButton { background-color: #fd7e14; color: white; }")
        self.batch_visit_shop_btn.clicked.connect(self.start_batch_visit_shop)
        
        self.batch_facility_placement_btn = QPushButton("🔧 摆放设施")
        self.batch_facility_placement_btn.setStyleSheet(btn_style + "QPushButton { background-color: #6f42c1; color: white; }")
        self.batch_facility_placement_btn.clicked.connect(self.start_batch_facility_placement)
        
        # 控制按钮
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.setStyleSheet(btn_style + "QPushButton { background-color: #ffc107; color: black; }")
        self.pause_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.setStyleSheet(btn_style + "QPushButton { background-color: #dc3545; color: white; }")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_operations)
        
        # 创建6列布局，充分利用更宽的水平空间（压缩垂直空间）
        main_grid = QGridLayout()
        main_grid.setSpacing(4)  # 减少间距以节省垂直空间
        main_grid.setContentsMargins(12, 6, 12, 6)  # 减少上下边距
        
        # 基础操作 - 6列布局，更好地利用宽度（压缩标签高度）
        basic_label = QLabel("📋 基础操作")
        basic_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px; margin: 2px 0;")
        main_grid.addWidget(basic_label, 0, 0, 1, 6)  # 跨6列
        
        main_grid.addWidget(self.refresh_btn, 1, 0)
        main_grid.addWidget(self.batch_signin_btn, 1, 1)
        main_grid.addWidget(self.batch_oil_btn, 1, 2)
        main_grid.addWidget(self.batch_roach_btn, 1, 3)
        main_grid.addWidget(self.batch_eat_btn, 1, 4)
        main_grid.addWidget(self.end_eat_btn, 1, 5)
        main_grid.addWidget(self.refresh_friends_btn, 2, 0)
        main_grid.addWidget(self.update_restaurant_id_btn, 2, 1)
        main_grid.addWidget(self.batch_cupboard_btn, 2, 2)
        main_grid.addWidget(self.batch_equipment_btn, 2, 3)
        main_grid.addWidget(self.batch_gem_refining_btn, 2, 4)
        main_grid.addWidget(self.batch_visit_shop_btn, 2, 5)
        main_grid.addWidget(self.batch_facility_placement_btn, 3, 0)
        
        # 特价菜操作（减少上下间距）
        special_label = QLabel("🛒 特价菜")
        special_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px; margin: 4px 0 2px 0;")
        main_grid.addWidget(special_label, 4, 0, 1, 6)
        
        # 选择按钮 - 前4列
        main_grid.addWidget(self.select_all_btn, 5, 0)
        main_grid.addWidget(self.select_none_btn, 5, 1)
        main_grid.addWidget(self.select_with_key_btn, 5, 2)
        main_grid.addWidget(self.select_pending_btn, 5, 3)
        
        # 特价菜购买按钮 - 跨2列，位置4-5
        main_grid.addWidget(self.special_food_btn, 5, 4, 1, 2)
        
        # 游戏任务（减少上下间距）
        game_label = QLabel("🎮 游戏任务")
        game_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px; margin: 4px 0 2px 0;")
        main_grid.addWidget(game_label, 6, 0, 1, 6)
        
        main_grid.addWidget(self.rock_paper_scissors_btn, 7, 0)
        main_grid.addWidget(self.guess_cup_btn, 7, 1)
        main_grid.addWidget(self.batch_friend_btn, 7, 2)
        main_grid.addWidget(self.shrine_guard_btn, 7, 3)
        main_grid.addWidget(self.active_reward_btn, 7, 4, 1, 2)  # 跨2列显示
        
        # 控制按钮（减少上下间距）
        control_label = QLabel("⚙️ 控制")
        control_label.setStyleSheet("font-weight: bold; color: #495057; font-size: 11px; margin: 4px 0 2px 0;")
        main_grid.addWidget(control_label, 8, 0, 1, 6)
        
        main_grid.addWidget(self.pause_btn, 9, 2)
        main_grid.addWidget(self.cancel_btn, 9, 3)
        
        # 设置列的拉伸因子，使布局更均匀
        main_grid.setColumnStretch(0, 1)
        main_grid.setColumnStretch(1, 1)
        main_grid.setColumnStretch(2, 1)
        main_grid.setColumnStretch(3, 1)
        main_grid.setColumnStretch(4, 1)
        main_grid.setColumnStretch(5, 1)
        
        # 应用网格布局（不添加stretch以压缩垂直空间）
        layout.addLayout(main_grid)
        # layout.addStretch()  # 移除stretch以压缩高度
        
        return panel
    
    def create_tasks_overview(self) -> QWidget:
        """创建任务概览表格"""
        widget = QGroupBox("账号任务概览")
        layout = QVBoxLayout(widget)
        
        # 概览表格
        self.overview_table = QTableWidget()
        self.overview_table.setColumnCount(9)
        self.overview_table.setHorizontalHeaderLabels([
            "选择", "账号", "每日完成", "每日活跃度", "每周完成", "每周活跃度", "特价菜", "Key状态", "更新时间"
        ])
        
        # 设置表格属性
        self.overview_table.verticalHeader().setVisible(False)
        self.overview_table.setAlternatingRowColors(True)
        self.overview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.overview_table.horizontalHeader().setStretchLastSection(True)
        self.overview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # 设置更紧凑的固定高度，节省垂直空间（约显示5-6行数据）
        self.overview_table.setFixedHeight(200)
        
        # 双击查看详情
        self.overview_table.itemDoubleClicked.connect(self.show_task_details)
        
        layout.addWidget(self.overview_table)
        
        return widget
    
    def create_task_details(self) -> QWidget:
        """创建任务详细信息面板"""
        widget = QGroupBox("任务详细信息")
        layout = QVBoxLayout(widget)
        
        # 账号选择
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("查看账号:"))
        
        self.detail_account_combo = QComboBox()
        self.detail_account_combo.setMinimumWidth(150)
        self.detail_account_combo.currentIndexChanged.connect(self.update_task_details)
        account_layout.addWidget(self.detail_account_combo)
        
        account_layout.addStretch()
        layout.addLayout(account_layout)
        
        # 任务类型标签页
        self.detail_tab_widget = QTabWidget()
        
        # 每日任务标签页
        self.daily_tasks_table = QTableWidget()
        self.daily_tasks_table.setColumnCount(6)
        self.daily_tasks_table.setHorizontalHeaderLabels([
            "任务名称", "完成情况", "活跃度", "状态", "可完成", "操作"
        ])
        self.daily_tasks_table.verticalHeader().setVisible(False)
        self.daily_tasks_table.setAlternatingRowColors(True)
        self.daily_tasks_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.daily_tasks_table.setMaximumHeight(180)  # 限制每日任务表格高度
        
        self.detail_tab_widget.addTab(self.daily_tasks_table, "每日任务")
        
        # 每周任务标签页
        self.weekly_tasks_table = QTableWidget()
        self.weekly_tasks_table.setColumnCount(6)
        self.weekly_tasks_table.setHorizontalHeaderLabels([
            "任务名称", "完成情况", "活跃度", "状态", "可完成", "操作"
        ])
        self.weekly_tasks_table.verticalHeader().setVisible(False)
        self.weekly_tasks_table.setAlternatingRowColors(True)
        self.weekly_tasks_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.weekly_tasks_table.setMaximumHeight(180)  # 限制每周任务表格高度
        
        self.detail_tab_widget.addTab(self.weekly_tasks_table, "每周任务")
        
        layout.addWidget(self.detail_tab_widget)
        
        return widget
    
    def load_accounts(self):
        """加载账号列表"""
        # 更新详情面板的账号选择
        self.detail_account_combo.clear()
        accounts = self.manager.list_accounts()
        
        for account in accounts:
            if account.key:  # 只显示有Key的账号
                display_text = f"{account.username} ({account.restaurant or '未知餐厅'})"
                self.detail_account_combo.addItem(display_text, account.id)
    
    def refresh_task_data(self):
        """刷新任务数据"""
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度
        self.status_label.setText("正在加载任务数据...")
        
        # 获取所有账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号（需要有Key的账号）")
            self.refresh_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
        
        # 转换为字典格式
        account_list = []
        for acc in valid_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "restaurant": acc.restaurant,
                "key": acc.key,
                "cookie": acc.cookie or "123"
            })
        
        # 清理之前的线程
        if hasattr(self, 'load_worker') and self.load_worker and self.load_worker.isRunning():
            self.load_worker.quit()
            self.load_worker.wait()
        
        # 启动加载线程
        self.load_worker = TaskLoadWorker(account_list)
        self.load_worker.finished.connect(self.on_task_data_loaded)
        self.load_worker.error.connect(self.on_load_error)
        self.load_worker.progress.connect(self.on_load_progress)
        self.load_worker.start()
    
    def on_load_progress(self, message: str):
        """加载进度更新"""
        self.status_label.setText(message)
    
    def on_task_data_loaded(self, data):
        """任务数据加载完成"""
        # print(f"[Debug] 接收到 {len(data)} 个账号的数据")
        # for acc_id, acc_data in data.items():
        #     summary = acc_data["summary"]
        #     print(f"[Debug] 账号ID {acc_id}: success={summary.get('success')}, daily_success={summary.get('daily_success')}, weekly_success={summary.get('weekly_success')}")
            
        self.task_data = data
        self.update_overview_table()
        self.update_task_details()
        
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(f"数据加载完成 - {datetime.now().strftime('%H:%M:%S')}")
        
        if self.log_widget:
            success_count = sum(1 for d in data.values() if d["summary"].get("success"))
            self.log_widget.append(f"📋 任务数据刷新完成: 成功加载 {success_count}/{len(data)} 个账号")
    
    def on_load_error(self, error_msg: str):
        """加载错误处理"""
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(f"加载失败: {error_msg}")
        QMessageBox.critical(self, "加载失败", error_msg)
    
    def update_overview_table(self):
        """更新概览表格"""
        # print(f"[Debug] 开始更新概览表格，共有 {len(self.task_data)} 个账号数据")
        self.overview_table.setRowCount(0)
        
        # 获取特价菜任务状态
        try:
            special_food_manager = SpecialFoodManager()
            all_special_food_status = special_food_manager.get_all_accounts_task_status()
            special_food_details = {detail['account_id']: detail for detail in all_special_food_status.get('account_details', [])}
        except Exception as e:
            print(f"[Warning] 获取特价菜状态失败: {e}")
            special_food_details = {}
        
        for account_id, data in self.task_data.items():
            account = data["account"]
            summary = data["summary"]
            load_time = data["load_time"]
            
            # 总是显示账号，即使加载失败
            row = self.overview_table.rowCount()
            self.overview_table.insertRow(row)
            
            # 0. 选择框
            checkbox = QCheckBox()
            checkbox.setChecked(False)  # 默认不选中，让用户自己选择
            checkbox.setProperty("account_id", account_id)
            self.overview_table.setCellWidget(row, 0, checkbox)
            
            # 1. 账号名
            username_item = QTableWidgetItem(account["username"])
            username_item.setData(Qt.ItemDataRole.UserRole, account_id)
            self.overview_table.setItem(row, 1, username_item)
            
            # 2. 每日任务完成情况
            daily_summary = summary.get("daily_summary", {})
            daily_success = summary.get("daily_success", False)
            
            if daily_success and daily_summary:
                daily_completed = int(daily_summary.get("completed_tasks", 0))
                daily_total = int(daily_summary.get("total_tasks", 0))
                daily_rate = float(daily_summary.get("completion_rate", 0))
                daily_active = int(daily_summary.get("daily_active_points", 0))
                
                daily_progress = QTableWidgetItem(f"{daily_completed}/{daily_total} ({daily_rate:.0f}%)")
                daily_progress.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if daily_rate >= 90:
                    daily_progress.setForeground(QColor("#28a745"))
                elif daily_rate >= 50:
                    daily_progress.setForeground(QColor("#ffc107"))
                else:
                    daily_progress.setForeground(QColor("#dc3545"))
                
                self.overview_table.setItem(row, 2, daily_progress)
                
                # 3. 每日活跃度
                daily_active_item = QTableWidgetItem(str(daily_active))
                daily_active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.overview_table.setItem(row, 3, daily_active_item)
            else:
                error_msg = daily_summary.get("error", "加载失败") if daily_summary else "数据缺失"
                error_item = QTableWidgetItem("❌ 加载失败")
                error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                error_item.setForeground(QColor("#dc3545"))
                error_item.setToolTip(f"每日任务加载失败: {error_msg}")
                self.overview_table.setItem(row, 2, error_item)
                
                error_active = QTableWidgetItem("-")
                error_active.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                error_active.setForeground(QColor("#6c757d"))
                self.overview_table.setItem(row, 3, error_active)
            
            # 4. 每周任务完成情况
            weekly_summary = summary.get("weekly_summary", {})
            weekly_success = summary.get("weekly_success", False)
            
            if weekly_success and weekly_summary:
                weekly_completed = int(weekly_summary.get("completed_tasks", 0))
                weekly_total = int(weekly_summary.get("total_tasks", 0))
                weekly_rate = float(weekly_summary.get("completion_rate", 0))
                weekly_active = int(weekly_summary.get("weekly_active_points", 0))
                
                weekly_progress = QTableWidgetItem(f"{weekly_completed}/{weekly_total} ({weekly_rate:.0f}%)")
                weekly_progress.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if weekly_rate >= 90:
                    weekly_progress.setForeground(QColor("#28a745"))
                elif weekly_rate >= 50:
                    weekly_progress.setForeground(QColor("#ffc107"))
                else:
                    weekly_progress.setForeground(QColor("#dc3545"))
                
                self.overview_table.setItem(row, 4, weekly_progress)
                
                # 5. 每周活跃度
                weekly_active_item = QTableWidgetItem(str(weekly_active))
                weekly_active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.overview_table.setItem(row, 5, weekly_active_item)
            else:
                error_msg = weekly_summary.get("error", "加载失败") if weekly_summary else "数据缺失"
                error_item2 = QTableWidgetItem("❌ 加载失败")
                error_item2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                error_item2.setForeground(QColor("#dc3545"))
                error_item2.setToolTip(f"每周任务加载失败: {error_msg}")
                self.overview_table.setItem(row, 4, error_item2)
                
                error_active2 = QTableWidgetItem("-")
                error_active2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                error_active2.setForeground(QColor("#6c757d"))
                self.overview_table.setItem(row, 5, error_active2)
            
            # 6. 特价菜状态
            special_food_detail = special_food_details.get(account_id)
            if special_food_detail:
                if special_food_detail['status'] == 'completed':
                    task_info = special_food_detail.get('task_info', {})
                    food_name = task_info.get('food_name', '特价菜')
                    quantity = task_info.get('quantity', 0)
                    special_food_item = QTableWidgetItem(f"✅ 已完成 ({quantity}个{food_name})")
                    special_food_item.setForeground(QColor("#28a745"))
                elif special_food_detail['status'] == 'failed':
                    task_info = special_food_detail.get('task_info', {})
                    error_msg = task_info.get('error_message', '购买失败')
                    special_food_item = QTableWidgetItem(f"❌ 失败")
                    special_food_item.setForeground(QColor("#dc3545"))
                    special_food_item.setToolTip(f"失败原因: {error_msg}")
                else:  # pending
                    special_food_item = QTableWidgetItem("⏳ 待购买")
                    special_food_item.setForeground(QColor("#ffc107"))
            else:
                special_food_item = QTableWidgetItem("⏳ 待购买")
                special_food_item.setForeground(QColor("#ffc107"))
            
            special_food_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.overview_table.setItem(row, 6, special_food_item)
            
            # 7. Key状态
            if account.get("key"):
                key_status = QTableWidgetItem("有Key")
                key_status.setForeground(QColor("#28a745"))
            else:
                key_status = QTableWidgetItem("无Key")
                key_status.setForeground(QColor("#dc3545"))
            key_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.overview_table.setItem(row, 7, key_status)
            
            # 8. 更新时间
            if load_time:
                time_str = load_time.strftime("%H:%M:%S")
            else:
                time_str = "未知"
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not summary.get("success"):
                error_msg = summary.get("error", "未知错误")
                time_item.setToolTip(f"加载失败: {error_msg}")
                time_item.setForeground(QColor("#dc3545"))
            self.overview_table.setItem(row, 8, time_item)
    
    def show_task_details(self, item):
        """显示任务详情"""
        if item.column() != 1:  # 只有点击账号列才处理（现在是第1列）
            return
            
        account_id = item.data(Qt.ItemDataRole.UserRole)
        
        # 在详情面板中选择对应账号
        for i in range(self.detail_account_combo.count()):
            if self.detail_account_combo.itemData(i) == account_id:
                self.detail_account_combo.setCurrentIndex(i)
                break
    
    def update_task_details(self):
        """更新任务详细信息"""
        account_id = self.detail_account_combo.currentData()
        if not account_id or account_id not in self.task_data:
            # 清空表格
            self.daily_tasks_table.setRowCount(0)
            self.weekly_tasks_table.setRowCount(0)
            return
        
        data = self.task_data[account_id]
        summary = data["summary"]
        
        if not summary.get("success"):
            return
        
        # 更新每日任务表格
        daily_summary = summary.get("daily_summary", {})
        if daily_summary:
            self.update_task_table(self.daily_tasks_table, daily_summary.get("tasks", []))
        
        # 更新每周任务表格
        weekly_summary = summary.get("weekly_summary", {})
        if weekly_summary:
            self.update_task_table(self.weekly_tasks_table, weekly_summary.get("tasks", []))
    
    def update_task_table(self, table: QTableWidget, tasks: List[Dict]):
        """更新任务表格"""
        table.setRowCount(0)
        
        # 可以自动完成的任务代码
        completable_codes = {"sign", "tower", "shrine", "monster", "strengthen_equip", "add_ins", "cookbook"}
        
        for task in tasks:
            row = table.rowCount()
            table.insertRow(row)
            
            # 任务名称
            name_item = QTableWidgetItem(task.get("name", ""))
            table.setItem(row, 0, name_item)
            
            # 完成情况
            try:
                finish_num = int(task.get("finish_num", 0))
                max_num = int(task.get("max_num", 1))
            except (ValueError, TypeError):
                # 如果转换失败，使用默认值
                finish_num = 0
                max_num = 1
                
            progress_text = f"{finish_num}/{max_num}"
            
            progress_item = QTableWidgetItem(progress_text)
            progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if finish_num >= max_num:
                progress_item.setForeground(QColor("#28a745"))
            else:
                progress_item.setForeground(QColor("#dc3545"))
            
            table.setItem(row, 1, progress_item)
            
            # 活跃度
            try:
                active_num = int(task.get("active_num", 0))
            except (ValueError, TypeError):
                active_num = 0
            
            active_item = QTableWidgetItem(str(active_num))
            active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, active_item)
            
            # 状态
            if finish_num >= max_num:
                status_item = QTableWidgetItem("✅ 已完成")
                status_item.setForeground(QColor("#28a745"))
            else:
                status_item = QTableWidgetItem(f"⏳ 未完成 (剩余{max_num - finish_num})")
                status_item.setForeground(QColor("#dc3545"))
            
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 3, status_item)
            
            # 可完成
            task_code = task.get("code", "")
            if task_code in completable_codes:
                completable_item = QTableWidgetItem("✅ 是")
                completable_item.setForeground(QColor("#28a745"))
            else:
                completable_item = QTableWidgetItem("❌ 否")
                completable_item.setForeground(QColor("#6c757d"))
            
            completable_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 4, completable_item)
            
            # 操作
            if finish_num < max_num and task_code in completable_codes:
                action_item = QTableWidgetItem("🔧 可执行")
                action_item.setForeground(QColor("#17a2b8"))
            else:
                action_item = QTableWidgetItem("-")
                action_item.setForeground(QColor("#6c757d"))
            
            action_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 5, action_item)
    
    def start_batch_signin(self):
        """开始批量签到"""
        # 获取所有有Key的账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号进行签到！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量签到", 
            f"确定要为 {len(valid_accounts)} 个账号执行批量签到吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in valid_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie or "123"
            })
        
        # 更新UI状态
        self.batch_signin_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(account_list))
        self.progress_bar.setValue(0)
        
        # 启动签到线程
        self.signin_worker = BatchSigninWorker(account_list, interval_seconds=1)
        self.signin_thread = QThread()
        self.signin_worker.moveToThread(self.signin_thread)
        
        # 连接信号
        self.signin_thread.started.connect(self.signin_worker.run)
        self.signin_worker.progress_updated.connect(self.update_signin_progress)
        self.signin_worker.signin_finished.connect(self.log_signin_result)
        self.signin_worker.batch_finished.connect(self.on_signin_batch_finished)
        
        # 启动线程
        self.signin_thread.start()
    
    def start_batch_cycle_oil(self):
        """开始批量循环添油"""
        # 获取所有有Key的账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号进行循环添油！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认循环添油", 
            f"确定要执行循环添油吗？\n"
            f"共 {len(valid_accounts)} 个账号，每个账号为下一个小号添油\n"
            f"(1为2添，2为3添，...，{len(valid_accounts)}为1添)\n\n"
            f"注意：此操作会消耗金币！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 更新UI状态
        self.batch_signin_btn.setEnabled(False)
        self.batch_oil_btn.setEnabled(False)
        self.batch_roach_btn.setEnabled(False)
        self.batch_eat_btn.setEnabled(False)
        self.end_eat_btn.setEnabled(False)
        self.refresh_friends_btn.setEnabled(False)
        self.batch_friend_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(valid_accounts))
        self.progress_bar.setValue(0)
        
        # 启动循环添油线程
        self.oil_worker = BatchCycleOilWorker(self.manager)
        self.oil_thread = QThread()
        self.oil_worker.moveToThread(self.oil_thread)
        
        # 连接信号
        self.oil_thread.started.connect(self.oil_worker.run)
        self.oil_worker.progress_updated.connect(self.update_oil_progress)
        self.oil_worker.oil_finished.connect(self.log_oil_result)
        self.oil_worker.batch_finished.connect(self.on_oil_batch_finished)
        
        # 启动线程
        self.oil_thread.start()

    def start_batch_roach_cycle(self):
        """开始批量蟑螂任务循环"""
        # 获取所有有Key的账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号进行蟑螂任务！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认蟑螂任务循环", 
            f"确定要执行完整的蟑螂任务循环吗？\n"
            f"共 {len(valid_accounts)} 个账号\n\n"
            f"任务流程：\n"
            f"1️⃣ 每个账号向好友餐厅放 5只蟑螂\n"
            f"2️⃣ 清理自己餐厅的蟑螂 (需清理5只完成任务)\n\n"
            f"注意：此操作有助于完成打蟑螂活跃任务！\n"
            f"如需处理好友申请，请先点击「👥 好友申请」按钮",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 更新UI状态
        self.batch_signin_btn.setEnabled(False)
        self.batch_oil_btn.setEnabled(False)
        self.batch_roach_btn.setEnabled(False)
        self.batch_eat_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(3)  # 3个主要阶段
        self.progress_bar.setValue(0)
        
        # 启动蟑螂任务线程
        self.roach_worker = BatchRoachWorker(self.manager)
        self.roach_thread = QThread()
        self.roach_worker.moveToThread(self.roach_thread)
        
        # 连接信号
        self.roach_thread.started.connect(self.roach_worker.run)
        self.roach_worker.progress_updated.connect(self.update_roach_progress)
        self.roach_worker.phase_finished.connect(self.log_roach_phase)
        self.roach_worker.batch_finished.connect(self.on_roach_batch_finished)
        
        # 启动线程
        self.roach_thread.start()

    def start_batch_friend_requests(self):
        """开始批量处理好友申请"""
        # 获取所有有Key的账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号处理好友申请！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认处理好友申请", 
            f"确定要批量处理好友申请吗？\n"
            f"共 {len(valid_accounts)} 个账号\n\n"
            f"操作说明：\n"
            f"• 自动同意所有收到的好友申请\n"
            f"• 建议在添油/放蟑螂前执行一次\n"
            f"• 通常不需要频繁执行\n\n"
            f"注意：此操作会同意所有好友申请！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 更新UI状态
        self.batch_signin_btn.setEnabled(False)
        self.batch_oil_btn.setEnabled(False)
        self.batch_roach_btn.setEnabled(False)
        self.batch_eat_btn.setEnabled(False)
        self.end_eat_btn.setEnabled(False)
        self.refresh_friends_btn.setEnabled(False)
        self.batch_friend_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(valid_accounts))
        self.progress_bar.setValue(0)
        
        # 启动好友申请处理线程
        self.friend_worker = BatchFriendRequestWorker(self.manager)
        self.friend_thread = QThread()
        self.friend_worker.moveToThread(self.friend_thread)
        
        # 连接信号
        self.friend_thread.started.connect(self.friend_worker.run)
        self.friend_worker.progress_updated.connect(self.update_friend_progress)
        self.friend_worker.account_finished.connect(self.log_friend_account_result)
        self.friend_worker.batch_finished.connect(self.on_friend_batch_finished)
        
        # 启动线程
        self.friend_thread.start()
    
    @Slot(int, int, str, str)
    def update_oil_progress(self, current: int, total: int, username: str, status: str):
        """更新循环添油进度"""
        if total > 0:
            self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {username}: {status}")
    
    @Slot(str, str, bool, str)
    def log_oil_result(self, current_account: str, target_account: str, success: bool, message: str):
        """记录循环添油结果到日志"""
        if self.log_widget:
            status_icon = "✅" if success else "❌"
            log_message = f"🛢️ 循环添油 {status_icon} {current_account} → {target_account}: {message}"
            self.log_widget.append(log_message)
    
    @Slot(bool, str, dict)
    def on_oil_batch_finished(self, success: bool, summary: str, stats: dict):
        """循环添油批次完成处理"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"🛢️ 循环添油完成: {summary}")
        
        self.reset_ui_state()
        
        # 显示完成通知
        
    @Slot(int, int, str, str)
    def update_roach_progress(self, current: int, total: int, phase: str, status: str):
        """更新蟑螂任务进度"""
        if total > 0:
            self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {phase}: {status}")

    @Slot(str, bool, str)
    def log_roach_phase(self, phase_name: str, success: bool, message: str):
        """记录蟑螂任务阶段结果"""
        status_icon = "✅" if success else "❌"
        log_message = f"🪳 {phase_name} {status_icon} {message}"
        if self.log_widget:
            self.log_widget.append(log_message)

    @Slot(bool, str, dict)
    def on_roach_batch_finished(self, success: bool, summary: str, stats: dict):
        """蟑螂任务批次完成处理"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"🪳 蟑螂任务完成: {summary}")
            
            # 显示详细统计
            if stats:
                place_success = stats.get("place_success", 0)
                place_total = stats.get("place_total", 0)
                clear_success = stats.get("clear_success", 0) 
                total_roaches_cleared = stats.get("total_roaches_cleared", 0)
                
                detail_msg = f"📊 统计: 放蟑螂 {place_success}/{place_total}, 清理 {clear_success} 个账号, 总清理 {total_roaches_cleared} 只 (任务需5只/账号)"
                self.log_widget.append(detail_msg)
        
        self.reset_ui_state()
        
        # 显示完成通知
        QMessageBox.information(self, "蟑螂任务完成", summary)
        
        # 自动刷新任务数据（延迟执行）
        QTimer.singleShot(2000, self.refresh_task_data)

    def start_batch_eat_cycle(self):
        """开始批量吃白食任务循环"""
        # 获取所有有Key的账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号进行吃白食任务！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认吃白食任务", 
            f"确定要执行批量吃白食任务吗？\n"
            f"共 {len(valid_accounts)} 个账号\n\n"
            f"任务流程：\n"
            f"🍽️ 每个账号在好友餐厅吃白食 1次\n\n"
            f"注意：吃白食主要用于回复体力！\n"
            f"如需处理好友申请，请先点击「👥 好友申请」按钮",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 更新UI状态
        self.batch_signin_btn.setEnabled(False)
        self.batch_oil_btn.setEnabled(False)
        self.batch_roach_btn.setEnabled(False)
        self.batch_eat_btn.setEnabled(False)
        self.end_eat_btn.setEnabled(False)
        self.refresh_friends_btn.setEnabled(False)
        self.batch_friend_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(1)  # 1个主要阶段
        self.progress_bar.setValue(0)
        
        # 启动吃白食任务线程
        self.eat_worker = BatchEatWorker(self.manager)
        self.eat_thread = QThread()
        self.eat_worker.moveToThread(self.eat_thread)
        
        # 连接信号
        self.eat_thread.started.connect(self.eat_worker.run)
        self.eat_worker.progress_updated.connect(self.update_eat_progress)
        self.eat_worker.phase_finished.connect(self.log_eat_phase)
        self.eat_worker.batch_finished.connect(self.on_eat_batch_finished)
        
        # 启动线程
        self.eat_thread.start()

    @Slot(int, int, str, str)
    def update_eat_progress(self, current: int, total: int, phase: str, status: str):
        """更新吃白食任务进度"""
        if total > 0:
            self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {phase}: {status}")

    @Slot(str, bool, str)
    def log_eat_phase(self, phase_name: str, success: bool, message: str):
        """记录吃白食任务阶段结果"""
        status_icon = "✅" if success else "❌"
        log_message = f"🍽️ {phase_name} {status_icon} {message}"
        if self.log_widget:
            self.log_widget.append(log_message)

    @Slot(bool, str, dict)
    def on_eat_batch_finished(self, success: bool, summary: str, stats: dict):
        """吃白食任务批次完成处理"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"🍽️ 吃白食任务完成: {summary}")
            
            # 显示详细统计
            if stats:
                eat_success = stats.get("eat_success", 0)
                processed_accounts = stats.get("processed_accounts", 0)
                
                detail_msg = f"📊 统计: 成功吃白食 {eat_success}/{processed_accounts} 个账号 (用于回复体力)"
                self.log_widget.append(detail_msg)
        
        self.reset_ui_state()
        
        # 显示完成通知
        QMessageBox.information(self, "吃白食任务完成", summary)
        
        # 自动刷新任务数据（延迟执行）
        QTimer.singleShot(2000, self.refresh_task_data)

    def start_batch_end_eat(self):
        """开始批量结束吃白食"""
        # 获取所有有Key的账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号结束吃白食！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认结束吃白食", 
            f"确定要批量结束吃白食状态吗？\n"
            f"共 {len(valid_accounts)} 个账号\n\n"
            f"注意：这将结束所有账号的吃白食状态",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 更新UI状态
        self.batch_signin_btn.setEnabled(False)
        self.batch_oil_btn.setEnabled(False)
        self.batch_roach_btn.setEnabled(False)
        self.batch_eat_btn.setEnabled(False)
        self.end_eat_btn.setEnabled(False)
        self.refresh_friends_btn.setEnabled(False)
        self.batch_friend_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(valid_accounts))
        self.progress_bar.setValue(0)
        
        # 启动结束吃白食线程
        self.end_eat_worker = BatchEndEatWorker(self.manager)
        self.end_eat_thread = QThread()
        self.end_eat_worker.moveToThread(self.end_eat_thread)
        
        # 连接信号
        self.end_eat_thread.started.connect(self.end_eat_worker.run)
        self.end_eat_worker.progress_updated.connect(self.update_end_eat_progress)
        self.end_eat_worker.account_finished.connect(self.log_end_eat_account_result)
        self.end_eat_worker.batch_finished.connect(self.on_end_eat_batch_finished)
        
        # 启动线程
        self.end_eat_thread.start()

    @Slot(int, int, str, str)
    def update_end_eat_progress(self, current: int, total: int, phase: str, status: str):
        """更新结束吃白食进度"""
        if total > 0:
            self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {phase}: {status}")

    @Slot(str, bool, str)
    def log_end_eat_account_result(self, account_name: str, success: bool, message: str):
        """记录结束吃白食账号结果"""
        status_icon = "✅" if success else "❌"
        log_message = f"🚫 结束吃白食 {status_icon} {account_name}: {message}"
        if self.log_widget:
            self.log_widget.append(log_message)

    @Slot(bool, str, dict)
    def on_end_eat_batch_finished(self, success: bool, summary: str, stats: dict):
        """结束吃白食批次完成处理"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"🚫 结束吃白食完成: {summary}")
            
            # 显示详细统计
            if stats:
                successful_ends = stats.get("successful_ends", 0)
                processed_accounts = stats.get("processed_accounts", 0)
                
                detail_msg = f"📊 统计: 成功结束 {successful_ends}/{processed_accounts} 个账号"
                self.log_widget.append(detail_msg)
        
        self.reset_ui_state()
        
        # 显示完成通知
        QMessageBox.information(self, "结束吃白食完成", summary)
        
        # 自动刷新任务数据（延迟执行）
        QTimer.singleShot(2000, self.refresh_task_data)

    def start_refresh_friends_cache(self):
        """开始刷新好友缓存"""
        # 获取所有有Key的账号
        accounts = self.manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号刷新好友缓存！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认刷新好友缓存", 
            f"确定要刷新所有账号的好友缓存吗？\n"
            f"共 {len(valid_accounts)} 个账号\n\n"
            f"注意：这会从服务器重新获取好友列表并更新缓存\n"
            f"建议定期执行以保持数据最新",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 更新UI状态
        self.batch_signin_btn.setEnabled(False)
        self.batch_oil_btn.setEnabled(False)
        self.batch_roach_btn.setEnabled(False)
        self.batch_eat_btn.setEnabled(False)
        self.end_eat_btn.setEnabled(False)
        self.refresh_friends_btn.setEnabled(False)
        self.batch_friend_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(valid_accounts))
        self.progress_bar.setValue(0)
        
        # 启动刷新好友缓存线程
        self.refresh_friends_worker = RefreshFriendsCacheWorker(self.manager)
        self.refresh_friends_thread = QThread()
        self.refresh_friends_worker.moveToThread(self.refresh_friends_thread)
        
        # 连接信号
        self.refresh_friends_thread.started.connect(self.refresh_friends_worker.run)
        self.refresh_friends_worker.progress_updated.connect(self.update_refresh_friends_progress)
        self.refresh_friends_worker.account_finished.connect(self.log_refresh_friends_account_result)
        self.refresh_friends_worker.batch_finished.connect(self.on_refresh_friends_batch_finished)
        
        # 启动线程
        self.refresh_friends_thread.start()

    @Slot(int, int, str, str)
    def update_refresh_friends_progress(self, current: int, total: int, phase: str, status: str):
        """更新刷新好友缓存进度"""
        if total > 0:
            self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {phase}: {status}")

    @Slot(str, int, bool, str)
    def log_refresh_friends_account_result(self, account_name: str, friends_count: int, success: bool, message: str):
        """记录刷新好友缓存账号结果"""
        status_icon = "✅" if success else "❌"
        log_message = f"🔄 好友缓存 {status_icon} {account_name}: 缓存了{friends_count}个好友"
        if self.log_widget:
            self.log_widget.append(log_message)

    @Slot(bool, str, dict)
    def on_refresh_friends_batch_finished(self, success: bool, summary: str, stats: dict):
        """刷新好友缓存批次完成处理"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"🔄 好友缓存刷新完成: {summary}")
            
            # 显示详细统计
            if stats:
                successful_refreshes = stats.get("successful_refreshes", 0)
                total_accounts = stats.get("total_accounts", 0)
                
                detail_msg = f"📊 统计: 成功刷新 {successful_refreshes}/{total_accounts} 个账号的好友缓存"
                self.log_widget.append(detail_msg)
        
        self.reset_ui_state()
        
        # 显示完成通知
        QMessageBox.information(self, "好友缓存刷新完成", summary)
        
        # 自动刷新任务数据（延迟执行）
        QTimer.singleShot(2000, self.refresh_task_data)

    @Slot(int, int, str, str)
    def update_friend_progress(self, current: int, total: int, phase: str, status: str):
        """更新好友申请处理进度"""
        if total > 0:
            self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {phase}: {status}")

    @Slot(str, int, int, bool, str)
    def log_friend_account_result(self, account_name: str, requests_handled: int, requests_successful: int, success: bool, message: str):
        """记录好友申请处理结果"""
        if requests_handled > 0:
            status_icon = "✅" if success else "❌"
            log_message = f"👥 好友申请 {status_icon} {account_name}: 同意 {requests_successful}/{requests_handled} 个申请"
        else:
            log_message = f"👥 好友申请 ℹ️ {account_name}: 没有收到好友申请"
        
        if self.log_widget:
            self.log_widget.append(log_message)

    @Slot(bool, str, dict)
    def on_friend_batch_finished(self, success: bool, summary: str, stats: dict):
        """好友申请处理批次完成"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"👥 好友申请处理完成: {summary}")
            
            # 显示详细统计
            if stats:
                total_handled = stats.get("total_handled", 0)
                processed_accounts = stats.get("processed_accounts", 0)
                
                if total_handled > 0:
                    detail_msg = f"📊 统计: 处理 {processed_accounts} 个账号，同意 {total_handled} 个好友申请"
                    self.log_widget.append(detail_msg)
        
        self.reset_ui_state()
        
        # 显示完成通知
        QMessageBox.information(self, "好友申请处理完成", summary)
        
        # 自动刷新任务数据（延迟执行）
        QTimer.singleShot(2000, self.refresh_task_data)
    
    @Slot(int, int, str, str)
    def update_signin_progress(self, current: int, total: int, username: str, status: str):
        """更新签到进度"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {username}: {status}")
    
    @Slot(int, str, bool, str)
    def log_signin_result(self, account_id: int, username: str, success: bool, message: str):
        """记录签到结果到日志"""
        if self.log_widget:
            status_icon = "✅" if success else "❌"
            log_message = f"📝 批量签到 {status_icon} {username}: {message}"
            self.log_widget.append(log_message)
    
    @Slot(bool, str, dict)
    def on_signin_batch_finished(self, success: bool, summary: str, stats: dict):
        """签到批次完成处理"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"📝 批量签到完成: {summary}")
        
        self.reset_ui_state()
        
        # 显示完成通知
        QMessageBox.information(self, "签到完成", summary)
        
        # 自动刷新任务数据
        QTimer.singleShot(2000, self.refresh_task_data)
    
    def start_update_restaurant_ids(self):
        """开始餐厅ID批量更新"""
        try:
            # 检查当前是否有其他操作在运行
            if (self.signin_worker or self.oil_worker or self.roach_worker or 
                self.friend_worker or self.restaurant_id_worker):
                QMessageBox.warning(self, "操作冲突", "当前有其他操作正在进行，请稍后再试")
                return
            
            # 确认对话框
            reply = QMessageBox.question(
                self, 
                "确认更新餐厅ID", 
                "确定要批量更新所有账号的餐厅ID吗？\n\n这个操作会调用用户卡片API为每个账号获取正确的餐厅ID并保存到数据库。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # 禁用相关按钮
            self.update_restaurant_id_btn.setEnabled(False)
            self.batch_signin_btn.setEnabled(False)
            self.batch_oil_btn.setEnabled(False)
            self.batch_roach_btn.setEnabled(False)
            self.batch_eat_btn.setEnabled(False)
            self.end_eat_btn.setEnabled(False)
            self.refresh_friends_btn.setEnabled(False)
            self.batch_friend_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
            
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("正在批量更新餐厅ID...")
            
            # 创建并启动工作线程
            self.restaurant_id_worker = RestaurantIdUpdateWorker(self.manager)
            self.restaurant_id_thread = QThread()
            self.restaurant_id_worker.moveToThread(self.restaurant_id_thread)
            
            # 连接信号
            self.restaurant_id_worker.progress_updated.connect(self.update_restaurant_id_progress)
            self.restaurant_id_worker.account_finished.connect(self.log_restaurant_id_result)
            self.restaurant_id_worker.batch_finished.connect(self.on_restaurant_id_batch_finished)
            
            self.restaurant_id_thread.started.connect(self.restaurant_id_worker.run)
            self.restaurant_id_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动餐厅ID更新失败: {str(e)}")
            self.reset_ui_state()
    
    @Slot(int, int, str, str)
    def update_restaurant_id_progress(self, current: int, total: int, username: str, status: str):
        """更新餐厅ID更新进度"""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.status_label.setText(f"({current}/{total}) {username}: {status}")
        else:
            self.status_label.setText(f"{username}: {status}")
    
    @Slot(str, bool, str, str)
    def log_restaurant_id_result(self, username: str, success: bool, res_id: str, message: str):
        """记录餐厅ID更新结果到日志"""
        if self.log_widget:
            status_icon = "✅" if success else "❌"
            if success and res_id:
                log_message = f"🏪 餐厅ID更新 {status_icon} {username}: 餐厅ID={res_id}"
            else:
                log_message = f"🏪 餐厅ID更新 {status_icon} {username}: {message}"
            self.log_widget.append(log_message)
    
    @Slot(bool, str, dict)
    def on_restaurant_id_batch_finished(self, success: bool, summary: str, stats: dict):
        """餐厅ID更新批次完成处理"""
        self.status_label.setText(summary)
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"🏪 餐厅ID批量更新完成: {summary}")
        
        self.reset_ui_state()
        
        # 显示完成通知
        if success:
            QMessageBox.information(self, "餐厅ID更新完成", summary)
        else:
            QMessageBox.warning(self, "餐厅ID更新失败", summary)
    
    def get_selected_accounts(self):
        """获取界面上选中的账号"""
        selected_accounts = []
        for row in range(self.overview_table.rowCount()):
            checkbox = self.overview_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                account_id = checkbox.property("account_id")
                # 从管理器中获取完整的账号信息
                try:
                    account = self.manager.get_account(account_id)
                    if account and account.key:
                        selected_accounts.append(account)
                except Exception as e:
                    print(f"[Warning] 无法获取账号ID {account_id}: {e}")
        return selected_accounts

    def select_all_accounts(self):
        """全选所有账号"""
        for row in range(self.overview_table.rowCount()):
            checkbox = self.overview_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)

    def select_none_accounts(self):
        """取消选择所有账号"""
        for row in range(self.overview_table.rowCount()):
            checkbox = self.overview_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def select_pending_accounts(self):
        """仅选择待购买特价菜且有Key的账号"""
        for row in range(self.overview_table.rowCount()):
            checkbox = self.overview_table.cellWidget(row, 0)
            if checkbox:
                # 检查是否有Key（第7列）
                key_item = self.overview_table.item(row, 7)
                has_key = key_item and "有Key" in key_item.text()
                
                # 检查特价菜状态列（第6列）
                special_food_item = self.overview_table.item(row, 6)
                is_pending = special_food_item and "⏳ 待购买" in special_food_item.text()
                
                # 只有有Key且待购买的账号才选中
                checkbox.setChecked(has_key and is_pending)

    def select_accounts_with_key(self):
        """仅选择有Key的账号"""
        for row in range(self.overview_table.rowCount()):
            checkbox = self.overview_table.cellWidget(row, 0)
            if checkbox:
                # 检查是否有Key（第7列）
                key_item = self.overview_table.item(row, 7)
                has_key = key_item and "有Key" in key_item.text()
                checkbox.setChecked(has_key)

    def start_batch_rock_paper_scissors(self):
        """开始批量猜拳成功一次任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要执行猜拳任务的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量猜拳任务", 
            f"确定要为选中的 {len(selected_accounts)} 个账号执行猜拳成功一次任务吗？\n注意：这会消耗游戏礼券。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in selected_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie or "123"
            })
        
        # 更新UI状态
        self.rock_paper_scissors_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(account_list))
        self.progress_bar.setValue(0)
        
        # 启动猜拳任务线程
        self.rock_paper_scissors_worker = RockPaperScissorsWorker(account_list)
        self.rock_paper_scissors_thread = QThread()
        self.rock_paper_scissors_worker.moveToThread(self.rock_paper_scissors_thread)
        
        # 连接信号
        self.rock_paper_scissors_thread.started.connect(self.rock_paper_scissors_worker.run)
        self.rock_paper_scissors_worker.progress_updated.connect(self.update_rock_paper_scissors_progress)
        self.rock_paper_scissors_worker.account_finished.connect(self.log_rock_paper_scissors_result)
        self.rock_paper_scissors_worker.batch_finished.connect(self.handle_rock_paper_scissors_batch_finished)
        self.rock_paper_scissors_worker.finished.connect(self.rock_paper_scissors_thread.quit)
        self.rock_paper_scissors_worker.finished.connect(self.rock_paper_scissors_worker.deleteLater)
        self.rock_paper_scissors_thread.finished.connect(self.rock_paper_scissors_thread.deleteLater)
        
        # 启动线程
        self.rock_paper_scissors_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"✂️ 开始为 {len(account_list)} 个账号执行猜拳成功一次任务...")

    def update_rock_paper_scissors_progress(self, current: int, total: int, username: str, status: str):
        """更新猜拳进度"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"猜拳进度: {current}/{total} - {username}: {status}")

    def log_rock_paper_scissors_result(self, username: str, success: bool, message: str, details: dict):
        """记录猜拳结果"""
        if self.log_widget:
            if success:
                self.log_widget.append(f"✅ {username}: {message}")
            else:
                self.log_widget.append(f"❌ {username}: {message}")

    def handle_rock_paper_scissors_batch_finished(self, success: bool, summary: str, details: dict):
        """处理猜拳批量任务完成"""
        self.rock_paper_scissors_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("猜拳任务完成")
        
        if self.log_widget:
            self.log_widget.append(f"✂️ 猜拳任务完成: {summary}")
            
            # 显示详细统计
            total = details.get('total_accounts', 0)
            successful = details.get('successful_count', 0)
            failed = details.get('failed_count', 0)
            success_rate = details.get('success_rate', 0)
            
            self.log_widget.append(f"📊 统计结果: 成功 {successful}，失败 {failed}，成功率 {success_rate:.1f}%")
        
        # 显示完成对话框
        if success:
            QMessageBox.information(self, "猜拳任务完成", summary)
        else:
            QMessageBox.warning(self, "猜拳任务失败", summary)

    def start_batch_guess_cup(self):
        """开始批量猜酒杯成功一次任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要执行猜酒杯任务的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量猜酒杯任务", 
            f"确定要为选中的 {len(selected_accounts)} 个账号执行猜酒杯成功一次任务吗？\n注意：这会消耗游戏机会。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in selected_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie or "123"
            })
        
        # 更新UI状态
        self.guess_cup_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(account_list))
        self.progress_bar.setValue(0)
        
        # 启动猜酒杯任务线程
        self.guess_cup_worker = GuessCupWorker(account_list)
        self.guess_cup_thread = QThread()
        self.guess_cup_worker.moveToThread(self.guess_cup_thread)
        
        # 连接信号
        self.guess_cup_thread.started.connect(self.guess_cup_worker.run)
        self.guess_cup_worker.progress_updated.connect(self.update_guess_cup_progress)
        self.guess_cup_worker.account_finished.connect(self.log_guess_cup_result)
        self.guess_cup_worker.batch_finished.connect(self.handle_guess_cup_batch_finished)
        self.guess_cup_worker.finished.connect(self.guess_cup_thread.quit)
        self.guess_cup_worker.finished.connect(self.guess_cup_worker.deleteLater)
        self.guess_cup_thread.finished.connect(self.guess_cup_thread.deleteLater)
        
        # 启动线程
        self.guess_cup_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"🍷 开始为 {len(account_list)} 个账号执行猜酒杯成功一次任务...")

    def update_guess_cup_progress(self, current: int, total: int, username: str, status: str):
        """更新猜酒杯进度"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"猜酒杯进度: {current}/{total} - {username}: {status}")

    def log_guess_cup_result(self, username: str, success: bool, message: str, details: dict):
        """记录猜酒杯结果"""
        if self.log_widget:
            if success:
                self.log_widget.append(f"✅ {username}: {message}")
            else:
                self.log_widget.append(f"❌ {username}: {message}")

    def handle_guess_cup_batch_finished(self, success: bool, summary: str, details: dict):
        """处理猜酒杯批量任务完成"""
        self.guess_cup_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("猜酒杯任务完成")
        
        if self.log_widget:
            self.log_widget.append(f"🍷 猜酒杯任务完成: {summary}")
            
            # 显示详细统计
            total = details.get('total_accounts', 0)
            successful = details.get('successful_count', 0)
            failed = details.get('failed_count', 0)
            success_rate = details.get('success_rate', 0)
            
            self.log_widget.append(f"📊 统计结果: 成功 {successful}，失败 {failed}，成功率 {success_rate:.1f}%")
        
        # 显示完成对话框
        if success:
            QMessageBox.information(self, "猜酒杯任务完成", summary)
        else:
            QMessageBox.warning(self, "猜酒杯任务失败", summary)

    def start_batch_special_food_buy(self):
        """开始批量购买特价菜"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要购买特价菜的账号！")
            return
        
        # 检查是否有已完成的账号被选中
        completed_accounts = []
        for row in range(self.overview_table.rowCount()):
            checkbox = self.overview_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                special_food_item = self.overview_table.item(row, 6)
                if special_food_item and "✅ 已完成" in special_food_item.text():
                    username_item = self.overview_table.item(row, 1)
                    if username_item:
                        completed_accounts.append(username_item.text())
        
        # 构建确认信息
        confirm_msg = f"确定要为选中的 {len(selected_accounts)} 个账号购买特价菜吗？\n每个账号将购买 2 个特价菜。\n注意：特价菜限量，可能会售罄。"
        
        if completed_accounts:
            confirm_msg += f"\n\n⚠️ 警告：以下账号今日已完成特价菜购买，重复购买可能失败：\n" + "\n".join(completed_accounts)
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量购买特价菜", 
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in selected_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie or "123"
            })
        
        # 更新UI状态
        self.special_food_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(account_list))
        self.progress_bar.setValue(0)
        
        # 启动特价菜购买线程（默认购买2个）
        self.special_food_worker = SpecialFoodBuyWorker(account_list, quantity=2)
        self.special_food_thread = QThread()
        self.special_food_worker.moveToThread(self.special_food_thread)
        
        # 连接信号
        self.special_food_thread.started.connect(self.special_food_worker.run)
        self.special_food_worker.progress_updated.connect(self.update_special_food_progress)
        self.special_food_worker.account_finished.connect(self.log_special_food_result)
        self.special_food_worker.batch_finished.connect(self.handle_special_food_batch_finished)
        self.special_food_worker.finished.connect(self.special_food_thread.quit)
        self.special_food_worker.finished.connect(self.special_food_worker.deleteLater)
        self.special_food_thread.finished.connect(self.special_food_thread.deleteLater)
        
        # 启动线程
        self.special_food_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"🛒 开始为 {len(account_list)} 个账号批量购买特价菜...")
    
    def update_special_food_progress(self, current: int, total: int, username: str, status: str):
        """更新特价菜购买进度"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"特价菜购买进度: {current}/{total} - {username}: {status}")
    
    def log_special_food_result(self, username: str, success: bool, message: str, details: dict):
        """记录特价菜购买结果"""
        if self.log_widget:
            if success:
                food_name = details.get('food_name', '特价菜')
                quantity = details.get('quantity', 1)
                gold_spent = details.get('gold_spent', 0)
                self.log_widget.append(f"✅ {username}: 成功购买 {quantity} 个 {food_name}，花费 {gold_spent} 金币")
            else:
                self.log_widget.append(f"❌ {username}: {message}")
    
    def handle_special_food_batch_finished(self, success: bool, summary: str, details: dict):
        """处理特价菜批量购买完成"""
        self.special_food_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("特价菜购买完成")
        
        if self.log_widget:
            self.log_widget.append(f"🛒 特价菜批量购买完成: {summary}")
            
            # 显示详细统计
            total = details.get('total_accounts', 0)
            successful = details.get('successful_purchases', 0)
            failed = details.get('failed_purchases', 0)
            already_completed = details.get('already_completed', 0)
            success_rate = details.get('success_rate', 0)
            
            self.log_widget.append(f"📊 统计结果: 成功 {successful}，失败 {failed}，已完成 {already_completed}，成功率 {success_rate:.1f}%")
            
            if details.get('sold_out_detected'):
                self.log_widget.append(f"⚠️ 检测到特价菜已售罄，已停止后续购买")
        
        # 刷新表格显示最新的特价菜状态
        self.update_overview_table()
        
        # 显示完成对话框
        if success:
            QMessageBox.information(self, "特价菜购买完成", summary)
        else:
            QMessageBox.warning(self, "特价菜购买失败", summary)
    
    def start_batch_active_rewards(self):
        """开始批量领取活跃度奖励任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要领取活跃度奖励的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量领取活跃度奖励", 
            f"确定要为选中的 {len(selected_accounts)} 个账号领取活跃度奖励吗？\n\n"
            "⚠️ 将尝试领取以下奖励：\n"
            "• 每日活跃度奖励：30/50/100/150\n"
            "• 周活跃度奖励：200/500/800/1000\n\n"
            "注意：未达到条件的奖励会跳过。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用相关按钮
        self.active_reward_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_accounts))
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.active_reward_worker = ActiveRewardWorker(selected_accounts)
        self.active_reward_thread = QThread()
        self.active_reward_worker.moveToThread(self.active_reward_thread)
        
        # 连接信号
        self.active_reward_worker.progress.connect(self.on_active_reward_progress)
        self.active_reward_worker.finished.connect(self.on_active_reward_finished)
        self.active_reward_thread.started.connect(self.active_reward_worker.run)
        
        # 启动线程
        self.active_reward_thread.start()
        
        self.status_label.setText("正在领取活跃度奖励...")
        if self.log_widget:
            self.log_widget.append(f"🎁 开始为 {len(selected_accounts)} 个账号批量领取活跃度奖励")

    def on_active_reward_progress(self, message: str):
        """活跃度奖励进度更新"""
        self.status_label.setText(message)
        if self.log_widget:
            self.log_widget.append(message)
        
        # 更新进度条（简单估计）
        if "[" in message and "/" in message:
            try:
                # 从消息中提取当前进度
                start = message.find("[") + 1
                end = message.find("/", start)
                if start > 0 and end > start:
                    current = int(message[start:end])
                    self.progress_bar.setValue(current)
            except (ValueError, IndexError):
                pass

    def on_active_reward_finished(self, success: bool, summary: str):
        """活跃度奖励完成处理"""
        # 清理线程
        if self.active_reward_thread and self.active_reward_thread.isRunning():
            self.active_reward_thread.quit()
            self.active_reward_thread.wait()
        
        self.active_reward_worker = None
        self.active_reward_thread = None
        
        # 恢复UI状态
        self.active_reward_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("活跃度奖励领取完成")
        
        # 显示完成对话框
        if success:
            QMessageBox.information(self, "活跃度奖励领取完成", summary)
        else:
            QMessageBox.warning(self, "活跃度奖励领取失败", summary)
        
        if self.log_widget:
            self.log_widget.append(f"🎁 活跃度奖励领取任务完成: {summary}")

    def start_batch_cupboard_cycle(self):
        """开始批量翻橱柜任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要翻橱柜的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量翻橱柜", 
            f"确定要为选中的 {len(selected_accounts)} 个账号进行翻橱柜吗？\n每个账号将去下一个账号的餐厅翻5个格子（消耗10体力）。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 更新UI状态
        self.batch_cupboard_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # 显示进度信息
        self.status_label.setText("正在翻橱柜...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_accounts))
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.cupboard_worker = BatchCupboardWorker(self.manager, len(selected_accounts))
        self.cupboard_thread = QThread()
        self.cupboard_worker.moveToThread(self.cupboard_thread)
        
        # 连接信号
        self.cupboard_worker.progress_updated.connect(self.on_cupboard_progress)
        self.cupboard_worker.account_finished.connect(self.on_cupboard_account_finished)
        self.cupboard_worker.batch_finished.connect(self.on_cupboard_batch_finished)
        self.cupboard_thread.started.connect(self.cupboard_worker.run)
        
        # 启动线程
        self.cupboard_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"🗂️ 开始为 {len(selected_accounts)} 个账号批量翻橱柜")

    def on_cupboard_progress(self, current: int, total: int, account_name: str, status: str):
        """翻橱柜进度更新"""
        progress_text = f"[{current}/{total}] {account_name}: {status}"
        self.status_label.setText(progress_text)
        self.progress_bar.setValue(current)
        
        if self.log_widget:
            self.log_widget.append(progress_text)

    def on_cupboard_account_finished(self, account_name: str, success: bool, message: str, details: dict):
        """单个账号翻橱柜完成"""
        if success:
            icon = "✅"
            target_account = details.get("target_account", "")
            cupboards_success = details.get("cupboards_success", 0)
            energy_cost = details.get("energy_cost", 0)
            detail_msg = f"成功翻橱柜 {cupboards_success} 个格子 → {target_account}，消耗 {energy_cost} 体力"
        else:
            icon = "❌"
            detail_msg = message
        
        log_msg = f"{icon} {account_name}: {detail_msg}"
        
        if self.log_widget:
            self.log_widget.append(log_msg)

    def on_cupboard_batch_finished(self, success: bool, summary: str, stats: dict):
        """翻橱柜批次完成"""
        # 清理线程
        if self.cupboard_thread and self.cupboard_thread.isRunning():
            self.cupboard_thread.quit()
            self.cupboard_thread.wait()
        
        self.cupboard_worker = None
        self.cupboard_thread = None
        
        # 恢复UI状态
        self.batch_cupboard_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("翻橱柜任务完成")
        
        # 显示完成对话框
        if success:
            QMessageBox.information(self, "翻橱柜完成", summary)
        else:
            QMessageBox.warning(self, "翻橱柜失败", summary)
        
        if self.log_widget:
            self.log_widget.append(f"🗂️ 翻橱柜任务完成: {summary}")

    def start_batch_equipment_enhance(self):
        """开始批量强化厨具任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要强化厨具的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量强化厨具", 
            f"确定要为选中的 {len(selected_accounts)} 个账号进行强化厨具任务吗？\n\n"
            "⚠️ 操作内容：\n"
            "1. 购买见习装备（见习之铲、刀、锅各4次，共12件）\n"
            "2. 强化一件见习装备（完成每日强化任务）\n"
            "3. 分解所有见习装备（包括强化后的装备，获得材料）\n\n"
            "注意：此操作会消耗金币购买装备！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in selected_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie or "123"
            })
        
        # 更新UI状态
        self.batch_equipment_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # 显示进度信息
        self.status_label.setText("正在强化厨具...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(account_list))
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.equipment_worker = BatchEquipmentEnhanceWorker(account_list)
        self.equipment_thread = QThread()
        self.equipment_worker.moveToThread(self.equipment_thread)
        
        # 连接信号
        self.equipment_worker.progress_updated.connect(self.on_equipment_progress)
        self.equipment_worker.account_finished.connect(self.on_equipment_account_finished)
        self.equipment_worker.batch_finished.connect(self.on_equipment_batch_finished)
        self.equipment_thread.started.connect(self.equipment_worker.run)
        
        # 启动线程
        self.equipment_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"🔧 开始为 {len(account_list)} 个账号批量强化厨具")

    def on_equipment_progress(self, current: int, total: int, account_name: str, status: str):
        """强化厨具进度更新"""
        progress_text = f"[{current}/{total}] {account_name}: {status}"
        self.status_label.setText(progress_text)
        self.progress_bar.setValue(current)
        
        if self.log_widget:
            self.log_widget.append(progress_text)

    def on_equipment_account_finished(self, account_name: str, success: bool, message: str, details: dict):
        """单个账号强化厨具完成"""
        if success:
            icon = "✅"
            equipment_processed = details.get("equipment_processed", 0)
            detail_list = details.get("details", [])
            if detail_list:
                detail_msg = f"成功 - {'; '.join(detail_list[:3])}"  # 只显示前3个详情
            else:
                detail_msg = f"成功处理 {equipment_processed} 件装备"
        else:
            icon = "❌"
            detail_msg = message
        
        log_msg = f"{icon} {account_name}: {detail_msg}"
        
        if self.log_widget:
            self.log_widget.append(log_msg)

    def on_equipment_batch_finished(self, success: bool, summary: str, stats: dict):
        """强化厨具批次完成"""
        # 清理线程
        if self.equipment_thread and self.equipment_thread.isRunning():
            self.equipment_thread.quit()
            self.equipment_thread.wait()
        
        self.equipment_worker = None
        self.equipment_thread = None
        
        # 恢复UI状态
        self.batch_equipment_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("强化厨具任务完成")
        
        # 显示完成对话框
        if success:
            QMessageBox.information(self, "强化厨具完成", summary)
        else:
            QMessageBox.warning(self, "强化厨具失败", summary)
        
        if self.log_widget:
            self.log_widget.append(f"🔧 强化厨具任务完成: {summary}")

    def start_batch_gem_refining(self):
        """开始批量精炼宝石任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要精炼宝石的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量精炼宝石", 
            f"确定要为选中的 {len(selected_accounts)} 个账号进行精炼宝石任务吗？\n\n"
            "⚠️ 操作内容：\n"
            "1. 购买智慧原石（10000金币）\n"
            "2. 购买原石精华\n"
            "3. 精炼智慧原石（完成每日精炼任务）\n\n"
            "注意：此操作会消耗金币购买材料！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in selected_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie
            })
        
        # 停止当前操作
        self.cancel_operations()
        
        # 创建工作线程
        self.gem_refining_worker = BatchGemRefiningWorker(account_list)
        self.gem_refining_thread = QThread()
        self.gem_refining_worker.moveToThread(self.gem_refining_thread)
        
        # 连接信号
        self.gem_refining_worker.progress_updated.connect(self.on_gem_refining_progress)
        self.gem_refining_worker.account_finished.connect(self.on_gem_refining_account_finished)
        self.gem_refining_worker.batch_finished.connect(self.on_gem_refining_batch_finished)
        
        self.gem_refining_thread.started.connect(self.gem_refining_worker.run)
        self.gem_refining_thread.finished.connect(self.gem_refining_thread.deleteLater)
        
        # 启动线程
        self.gem_refining_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"💎 开始为 {len(account_list)} 个账号批量精炼宝石")

    def on_gem_refining_progress(self, current: int, total: int, account_name: str, status: str):
        """精炼宝石进度更新"""
        progress_text = f"[{current}/{total}] {account_name}: {status}"
        self.status_label.setText(progress_text)
        
        # 设置进度条
        progress_percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)

    def on_gem_refining_account_finished(self, account_name: str, success: bool, message: str, details: dict):
        """单个账号精炼宝石完成"""
        status_icon = "✅" if success else "❌"
        self.status_label.setText(f"{status_icon} {account_name}: {message}")
        
        if self.log_widget:
            self.log_widget.append(f"💎 {account_name}: {message}")

    def on_gem_refining_batch_finished(self, success: bool, summary: str, results: dict):
        """批量精炼宝石完成"""
        # 重置UI状态
        self.reset_ui_state()
        
        # 显示结果
        if success:
            QMessageBox.information(self, "精炼宝石完成", summary)
        else:
            QMessageBox.warning(self, "精炼宝石失败", summary)
        
        if self.log_widget:
            self.log_widget.append(f"💎 精炼宝石任务完成: {summary}")

    def start_batch_visit_shop(self):
        """开始批量巡店任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要巡店的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量巡店", 
            f"确定要为选中的 {len(selected_accounts)} 个账号执行巡店任务吗？\n\n"
            "⚠️ 操作内容：\n"
            "• 获取餐厅座位信息（完成每日巡店任务）\n"
            "• 统计座位占用情况（正常顾客、蟑螂、白食等）\n\n"
            "注意：巡店是每日任务，完成后可获得经验奖励。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in selected_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie
            })
        
        # 停止当前操作
        self.cancel_operations()
        
        # 创建工作线程
        self.visit_shop_worker = BatchVisitShopWorker(account_list)
        self.visit_shop_thread = QThread()
        self.visit_shop_worker.moveToThread(self.visit_shop_thread)
        
        # 连接信号
        self.visit_shop_worker.progress_updated.connect(self.on_visit_shop_progress)
        self.visit_shop_worker.account_finished.connect(self.on_visit_shop_account_finished)
        self.visit_shop_worker.batch_finished.connect(self.on_visit_shop_batch_finished)
        
        self.visit_shop_thread.started.connect(self.visit_shop_worker.run)
        self.visit_shop_thread.finished.connect(self.visit_shop_thread.deleteLater)
        
        # 启动线程
        self.visit_shop_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"🏪 开始为 {len(account_list)} 个账号批量巡店")

    def on_visit_shop_progress(self, current: int, total: int, account_name: str, status: str):
        """巡店进度更新"""
        progress_text = f"[{current}/{total}] {account_name}: {status}"
        self.status_label.setText(progress_text)
        
        # 设置进度条
        progress_percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)

    def on_visit_shop_account_finished(self, account_name: str, success: bool, message: str, details: dict):
        """单个账号巡店完成"""
        status_icon = "✅" if success else "❌"
        self.status_label.setText(f"{status_icon} {account_name}: {message}")
        
        if self.log_widget:
            self.log_widget.append(f"🏪 {account_name}: {message}")

    def on_visit_shop_batch_finished(self, success: bool, summary: str, results: dict):
        """批量巡店完成"""
        # 重置UI状态
        self.reset_ui_state()
        
        # 显示结果
        if success:
            QMessageBox.information(self, "巡店完成", summary)
        else:
            QMessageBox.warning(self, "巡店失败", summary)
        
        if self.log_widget:
            self.log_widget.append(f"🏪 巡店任务完成: {summary}")

    def start_batch_facility_placement(self):
        """开始批量摆放设施任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要摆放设施的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量摆放设施", 
            f"确定要为选中的 {len(selected_accounts)} 个账号执行摆放设施任务吗？\n\n"
            "该任务将执行以下步骤：\n"
            "• 购买老鼠夹和节油器\n"
            "• 清空位置1和2的现有设施\n"
            "• 重新摆放老鼠夹和节油器\n\n"
            "注意：摆放设施是每日任务，完成后可获得经验奖励。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # 禁用所有操作按钮
        self.disable_all_buttons()
        
        # 重置进度条和状态
        self.progress_bar.setValue(0)
        self.status_label.setText("正在执行摆放设施任务...")
        
        # 创建工作线程
        account_list = []
        for account in selected_accounts:
            account_dict = {
                'username': account.username,
                'key': account.key,
                'cookie_dict': {'PHPSESSID': account.cookie} if account.cookie else {}
            }
            account_list.append(account_dict)
        
        self.facility_placement_worker = BatchFacilityPlacementWorker(account_list)
        self.facility_placement_thread = QThread()
        self.facility_placement_worker.moveToThread(self.facility_placement_thread)
        
        # 连接信号
        self.facility_placement_worker.progress_updated.connect(self.on_facility_placement_progress)
        self.facility_placement_worker.account_finished.connect(self.on_facility_placement_account_finished)
        self.facility_placement_worker.batch_finished.connect(self.on_facility_placement_batch_finished)
        
        self.facility_placement_thread.started.connect(self.facility_placement_worker.run)
        self.facility_placement_thread.finished.connect(self.facility_placement_thread.deleteLater)
        
        # 启动线程
        self.facility_placement_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"🔧 开始为 {len(account_list)} 个账号批量摆放设施")

    def on_facility_placement_progress(self, current: int, total: int, account_name: str, status: str):
        """摆放设施进度更新"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"摆放设施进度: {current}/{total} - {account_name}: {status}")
        
        if self.log_widget:
            self.log_widget.append(f"🔧 ({current}/{total}) {account_name}: {status}")

    def on_facility_placement_account_finished(self, account_name: str, success: bool, message: str, details: dict):
        """单个账号摆放设施完成"""
        if self.log_widget:
            status_emoji = "✅" if success else "❌"
            self.log_widget.append(f"🔧 {status_emoji} {account_name}: {message}")

    def on_facility_placement_batch_finished(self, success: bool, summary: str, results: dict):
        """批量摆放设施完成"""
        self.progress_bar.setValue(100)
        self.status_label.setText("摆放设施任务完成")
        
        # 重新启用按钮
        self.enable_all_buttons()
        
        # 显示结果
        if success:
            QMessageBox.information(self, "摆放设施完成", summary)
        else:
            QMessageBox.warning(self, "摆放设施失败", summary)
        
        if self.log_widget:
            self.log_widget.append(f"🔧 摆放设施任务完成: {summary}")

    def start_batch_shrine_guard(self):
        """开始批量攻击神殿守卫任务"""
        # 获取选中的账号
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择要攻击神殿守卫的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量攻击神殿守卫", 
            f"确定要为选中的 {len(selected_accounts)} 个账号攻击神殿守卫吗？\n系统会持续攻击直到守卫被击败，并自动购买所需的普通飞弹。\n注意：需要消耗金币购买飞弹。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 转换为字典格式
        account_list = []
        for acc in selected_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key,
                "cookie": acc.cookie or "123"
            })
        
        # 更新UI状态
        self.shrine_guard_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(account_list))
        self.progress_bar.setValue(0)
        
        # 启动神殿守卫攻击线程
        self.shrine_guard_worker = ShrineGuardWorker(account_list)
        self.shrine_guard_thread = QThread()
        self.shrine_guard_worker.moveToThread(self.shrine_guard_thread)
        
        # 连接信号
        self.shrine_guard_thread.started.connect(self.shrine_guard_worker.run)
        self.shrine_guard_worker.progress_updated.connect(self.update_shrine_guard_progress)
        self.shrine_guard_worker.account_finished.connect(self.log_shrine_guard_result)
        self.shrine_guard_worker.batch_finished.connect(self.handle_shrine_guard_batch_finished)
        self.shrine_guard_worker.finished.connect(self.shrine_guard_thread.quit)
        self.shrine_guard_worker.finished.connect(self.shrine_guard_worker.deleteLater)
        self.shrine_guard_thread.finished.connect(self.shrine_guard_thread.deleteLater)
        
        # 启动线程
        self.shrine_guard_thread.start()
        
        if self.log_widget:
            self.log_widget.append(f"🛡️ 开始为 {len(account_list)} 个账号攻击神殿守卫...")
    
    def update_shrine_guard_progress(self, current: int, total: int, username: str, status: str):
        """更新神殿守卫攻击进度"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"神殿守卫攻击进度: {current}/{total} - {username}: {status}")
    
    def log_shrine_guard_result(self, username: str, success: bool, message: str, details: dict):
        """记录神殿守卫攻击结果"""
        if self.log_widget:
            if success:
                attacks = details.get('attacks', 0)
                successful = details.get('successful', 0)
                self.log_widget.append(f"✅ {username}: {message} (成功{successful}/{attacks})")
            else:
                self.log_widget.append(f"❌ {username}: {message}")
    
    def handle_shrine_guard_batch_finished(self, success: bool, summary: str, details: dict):
        """处理神殿守卫批量攻击完成"""
        self.shrine_guard_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("神殿守卫攻击完成")
        
        if self.log_widget:
            self.log_widget.append(f"🛡️ 神殿守卫批量攻击完成: {summary}")
            
            # 显示详细统计
            total = details.get('total_accounts', 0)
            total_attacks = details.get('total_attacks', 0)
            successful = details.get('successful_attacks', 0)
            failed = details.get('failed_attacks', 0)
            success_rate = details.get('success_rate', 0)
            
            self.log_widget.append(f"📊 统计结果: 总攻击{total_attacks}次，成功{successful}次，失败{failed}次，成功率{success_rate:.1f}%")
        
        # 显示完成对话框
        if success:
            QMessageBox.information(self, "神殿守卫攻击完成", summary)
        else:
            QMessageBox.warning(self, "神殿守卫攻击失败", summary)

    def cancel_operations(self):
        """取消操作"""
        if self.signin_worker:
            self.signin_worker.cancel()
        if self.oil_worker:
            self.oil_worker.cancel()
        if self.roach_worker:
            self.roach_worker.cancel()
        if self.special_food_worker:
            self.special_food_worker.cancel()
        if self.rock_paper_scissors_worker:
            self.rock_paper_scissors_worker.cancel()
        if self.guess_cup_worker:
            self.guess_cup_worker.cancel()
        if self.shrine_guard_worker:
            self.shrine_guard_worker.cancel()
        if self.active_reward_worker:
            self.active_reward_worker.stop()
        if self.cupboard_worker:
            self.cupboard_worker.cancel()
        if self.equipment_worker:
            self.equipment_worker.cancel()
        if self.gem_refining_worker:
            self.gem_refining_worker.cancel()
        if self.visit_shop_worker:
            self.visit_shop_worker.cancel()
        if self.facility_placement_worker:
            self.facility_placement_worker.cancel()
        if self.friend_worker:
            self.friend_worker.cancel()
        if self.restaurant_id_worker:
            self.restaurant_id_worker.cancel()
        self.reset_ui_state()
    
    def reset_ui_state(self):
        """重置UI状态"""
        self.batch_signin_btn.setEnabled(True)
        self.batch_oil_btn.setEnabled(True)
        self.batch_roach_btn.setEnabled(True)
        self.batch_eat_btn.setEnabled(True)
        self.end_eat_btn.setEnabled(True)
        self.refresh_friends_btn.setEnabled(True)
        self.update_restaurant_id_btn.setEnabled(True)
        self.special_food_btn.setEnabled(True)
        self.rock_paper_scissors_btn.setEnabled(True)
        self.guess_cup_btn.setEnabled(True)
        self.shrine_guard_btn.setEnabled(True)
        self.active_reward_btn.setEnabled(True)
        self.batch_cupboard_btn.setEnabled(True)
        self.batch_equipment_btn.setEnabled(True)
        self.batch_gem_refining_btn.setEnabled(True)
        self.batch_visit_shop_btn.setEnabled(True)
        self.batch_facility_placement_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.select_none_btn.setEnabled(True)
        self.select_with_key_btn.setEnabled(True)
        self.select_pending_btn.setEnabled(True)
        self.batch_friend_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # 清理签到线程
        if self.signin_thread and self.signin_thread.isRunning():
            self.signin_thread.quit()
            self.signin_thread.wait()
        self.signin_worker = None
        self.signin_thread = None
        
        # 清理循环添油线程
        if self.oil_thread and self.oil_thread.isRunning():
            self.oil_thread.quit()
            self.oil_thread.wait()
        self.oil_worker = None
        self.oil_thread = None
        
        # 清理蟑螂任务线程
        if self.roach_thread and self.roach_thread.isRunning():
            self.roach_thread.quit()
            self.roach_thread.wait()
        self.roach_worker = None
        self.roach_thread = None
        
        # 清理特价菜购买线程
        if self.special_food_thread and self.special_food_thread.isRunning():
            self.special_food_thread.quit()
            self.special_food_thread.wait()
        self.special_food_worker = None
        self.special_food_thread = None
        
        # 清理猜拳任务线程
        if self.rock_paper_scissors_thread and self.rock_paper_scissors_thread.isRunning():
            self.rock_paper_scissors_thread.quit()
            self.rock_paper_scissors_thread.wait()
        self.rock_paper_scissors_worker = None
        self.rock_paper_scissors_thread = None
        
        # 清理猜酒杯任务线程
        if self.guess_cup_thread and self.guess_cup_thread.isRunning():
            self.guess_cup_thread.quit()
            self.guess_cup_thread.wait()
        self.guess_cup_worker = None
        self.guess_cup_thread = None
        
        # 清理神殿守卫线程
        if self.shrine_guard_thread and self.shrine_guard_thread.isRunning():
            self.shrine_guard_thread.quit()
            self.shrine_guard_thread.wait()
        self.shrine_guard_worker = None
        self.shrine_guard_thread = None
        
        # 清理好友申请线程
        if self.friend_thread and self.friend_thread.isRunning():
            self.friend_thread.quit()
            self.friend_thread.wait()
        self.friend_worker = None
        self.friend_thread = None
        
        # 清理活跃度奖励线程
        if self.active_reward_thread and self.active_reward_thread.isRunning():
            self.active_reward_thread.quit()
            self.active_reward_thread.wait()
        self.active_reward_worker = None
        self.active_reward_thread = None
        
        # 清理翻橱柜线程
        if self.cupboard_thread and self.cupboard_thread.isRunning():
            self.cupboard_thread.quit()
            self.cupboard_thread.wait()
        self.cupboard_worker = None
        self.cupboard_thread = None
        
        # 清理强化厨具线程
        if self.equipment_thread and self.equipment_thread.isRunning():
            self.equipment_thread.quit()
            self.equipment_thread.wait()
        self.equipment_worker = None
        self.equipment_thread = None
        
        # 清理精炼宝石线程
        if self.gem_refining_thread and self.gem_refining_thread.isRunning():
            self.gem_refining_thread.quit()
            self.gem_refining_thread.wait()
        self.gem_refining_worker = None
        self.gem_refining_thread = None
        
        # 清理巡店线程
        if self.visit_shop_thread and self.visit_shop_thread.isRunning():
            self.visit_shop_thread.quit()
            self.visit_shop_thread.wait()
        self.visit_shop_worker = None
        self.visit_shop_thread = None
        
        # 清理餐厅ID更新线程
        if self.restaurant_id_thread and self.restaurant_id_thread.isRunning():
            self.restaurant_id_thread.quit()
            self.restaurant_id_thread.wait()
        self.restaurant_id_worker = None
        self.restaurant_id_thread = None
        
        # 清理摆放设施线程
        if self.facility_placement_thread and self.facility_placement_thread.isRunning():
            self.facility_placement_thread.quit()
            self.facility_placement_thread.wait()
        self.facility_placement_worker = None
        self.facility_placement_thread = None

    def disable_all_buttons(self):
        """禁用所有操作按钮"""
        self.batch_signin_btn.setEnabled(False)
        self.batch_oil_btn.setEnabled(False)
        self.batch_roach_btn.setEnabled(False)
        self.batch_eat_btn.setEnabled(False)
        self.end_eat_btn.setEnabled(False)
        self.refresh_friends_btn.setEnabled(False)
        self.update_restaurant_id_btn.setEnabled(False)
        self.special_food_btn.setEnabled(False)
        self.rock_paper_scissors_btn.setEnabled(False)
        self.guess_cup_btn.setEnabled(False)
        self.shrine_guard_btn.setEnabled(False)
        self.active_reward_btn.setEnabled(False)
        self.batch_cupboard_btn.setEnabled(False)
        self.batch_equipment_btn.setEnabled(False)
        self.batch_gem_refining_btn.setEnabled(False)
        self.batch_visit_shop_btn.setEnabled(False)
        self.batch_facility_placement_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.select_none_btn.setEnabled(False)
        self.select_with_key_btn.setEnabled(False)
        self.select_pending_btn.setEnabled(False)
        self.batch_friend_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)

    def enable_all_buttons(self):
        """启用所有操作按钮（重置UI状态的别名）"""
        self.reset_ui_state()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试用的AccountManager
    try:
        from src.delicious_town_bot.utils.account_manager import AccountManager
        manager = AccountManager()
        
        window = DailyTasksPage(manager)
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"测试运行失败: {e}")
        print("请确保数据库已正确配置")
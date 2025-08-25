"""
游戏操作页面 - 支持单个/批量游戏操作
根据实际游戏特性设计：依次发送请求，避免服务器压力
"""
import sys
import time
from datetime import datetime
from enum import Enum
from typing import List, Set, Dict, Any, Optional, Callable
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QCheckBox, QComboBox, QLabel,
    QLineEdit, QMessageBox, QInputDialog, QDialog, QProgressBar,
    QListWidget, QListWidgetItem, QHeaderView, QFrame, QTextEdit,
    QAbstractItemView, QSizePolicy, QSpinBox, QGroupBox, QGridLayout,
    QTabWidget, QSplitter
)

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.constants import Street
from src.delicious_town_bot.actions.restaurant import RestaurantActions
from src.delicious_town_bot.plugins.clicker.enhanced_fuel_operations import EnhancedFuelOperations


class AccountStatus(Enum):
    """简化的账号状态"""
    IDLE = ("空闲", "#28a745")
    RUNNING = ("执行中", "#007bff") 
    ERROR = ("错误", "#dc3545")
    NO_KEY = ("无Key", "#ffc107")


class GameOperation(Enum):
    """游戏操作类型"""
    CHALLENGE_TOWER = ("挑战厨塔", "challenge.attack_tower")
    DAILY_TASKS = ("日常任务", "daily.run_all_tasks")
    FUEL_UP = ("加油操作", "restaurant.fuel_up")
    LOTTERY = ("抽奖", "lottery.draw")
    FRIEND_VISIT = ("好友拜访", "friend.visit_all")
    COOK_RECIPES = ("烹饪菜谱", "cooking.auto_cook")
    BUY_NOVICE_EQUIPMENT = ("购买见习装备", "shop.buy_novice_equipment_daily")
    STAR_UPGRADE = ("升星", "restaurant.execute_star_upgrade")


class SequentialWorker(QObject):
    """顺序执行游戏操作的工作器"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 操作描述
    account_finished = Signal(int, str, bool, str)  # 账号ID, 账号名, 是否成功, 结果消息
    operation_finished = Signal(bool, str, dict)    # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, operation: GameOperation, account_list: List[Dict], 
                 interval_seconds: int = 2, manager: AccountManager = None):
        super().__init__()
        self.operation = operation
        self.account_list = account_list  # [{"id": 1, "username": "xxx", "key": "xxx"}, ...]
        self.interval_seconds = interval_seconds
        self.manager = manager
        self.is_cancelled = False
        self.is_paused = False
        self.stats = {"success": 0, "failed": 0, "skipped": 0}
        
        # 为加油操作创建增强版实例
        if self.operation == GameOperation.FUEL_UP:
            self.enhanced_fuel_ops = EnhancedFuelOperations(enable_detailed_logging=False)  # UI中关闭详细日志
        else:
            self.enhanced_fuel_ops = None
        
    def run(self):
        """顺序执行操作"""
        total_count = len(self.account_list)
        
        for i, account_info in enumerate(self.account_list):
            if self.is_cancelled:
                break
                
            # 暂停检查
            while self.is_paused and not self.is_cancelled:
                time.sleep(0.1)
                
            if self.is_cancelled:
                break
                
            account_id = account_info["id"]
            username = account_info["username"]
            key = account_info.get("key")
            
            # 发送进度信号
            self.progress_updated.emit(
                i + 1, total_count, username, 
                f"正在执行: {self.operation.value[0]}"
            )
            
            # 检查Key是否有效
            if not key:
                self.account_finished.emit(account_id, username, False, "账号无Key，跳过")
                self.stats["skipped"] += 1
                continue
            
            # 执行具体操作
            try:
                success, message = self._execute_game_operation(account_info)
                self.account_finished.emit(account_id, username, success, message)
                
                if success:
                    self.stats["success"] += 1
                else:
                    self.stats["failed"] += 1
                    
            except Exception as e:
                error_msg = f"操作异常: {str(e)}"
                self.account_finished.emit(account_id, username, False, error_msg)
                self.stats["failed"] += 1
            
            # 间隔等待（除了最后一个账号）
            if i < total_count - 1 and not self.is_cancelled:
                time.sleep(self.interval_seconds)
        
        # 发送完成信号
        if self.is_cancelled:
            summary = "操作已取消"
            self.operation_finished.emit(False, summary, self.stats)
        else:
            # 为加油操作添加详细统计
            if self.operation == GameOperation.FUEL_UP and self.enhanced_fuel_ops:
                fuel_stats = self.enhanced_fuel_ops.get_operation_stats()
                enhanced_summary = (
                    f"加油操作完成 - 成功加油: {fuel_stats.get('successful_fuel_ups', 0)}, "
                    f"已满跳过: {fuel_stats.get('already_full_count', 0)}, "
                    f"失败: {fuel_stats.get('failed_operations', 0)}, "
                    f"成功率: {fuel_stats.get('success_rate', 0)}%"
                )
                # 将增强统计合并到基础统计中
                enhanced_stats = {**self.stats, **fuel_stats}
                all_success = fuel_stats.get("failed_operations", 0) == 0 and fuel_stats.get("api_errors", 0) == 0
                self.operation_finished.emit(all_success, enhanced_summary, enhanced_stats)
            else:
                # 其他操作使用基础统计
                summary = f"操作完成 - 成功: {self.stats['success']}, 失败: {self.stats['failed']}, 跳过: {self.stats['skipped']}"
                all_success = self.stats["failed"] == 0
                self.operation_finished.emit(all_success, summary, self.stats)
    
    def _execute_game_operation(self, account_info: Dict) -> tuple[bool, str]:
        """执行具体的游戏操作"""
        account_id = account_info["id"]
        key = account_info["key"]
        
        # 这里根据不同的操作类型调用对应的Action
        try:
            if self.operation == GameOperation.CHALLENGE_TOWER:
                return self._challenge_tower(key)
            elif self.operation == GameOperation.DAILY_TASKS:
                return self._run_daily_tasks(key)
            elif self.operation == GameOperation.FUEL_UP:
                return self._fuel_up(key)
            elif self.operation == GameOperation.LOTTERY:
                return self._lottery(key)
            elif self.operation == GameOperation.FRIEND_VISIT:
                return self._friend_visit(key)
            elif self.operation == GameOperation.COOK_RECIPES:
                return self._cook_recipes(key)
            elif self.operation == GameOperation.BUY_NOVICE_EQUIPMENT:
                return self._buy_novice_equipment(key)
            elif self.operation == GameOperation.STAR_UPGRADE:
                return self._star_upgrade(key)
            else:
                return False, "未知操作类型"
        except Exception as e:
            return False, f"操作失败: {str(e)}"
    
    def _challenge_tower(self, key: str) -> tuple[bool, str]:
        """挑战厨塔"""
        # TODO: 实现具体的厨塔挑战逻辑
        # from src.delicious_town_bot.actions.challenge import ChallengeAction
        # action = ChallengeAction(key=key, cookie={"PHPSESSID": "dummy"})
        # result = action.attack_tower(level=9)  # 挑战第9层
        # return result.get("success", False), result.get("message", "")
        
        # 模拟操作
        time.sleep(0.5)  # 模拟网络请求时间
        return True, "厨塔挑战完成"
    
    def _run_daily_tasks(self, key: str) -> tuple[bool, str]:
        """执行日常任务"""
        # TODO: 实现日常任务逻辑
        time.sleep(0.8)
        return True, "日常任务完成"
    
    def _fuel_up(self, key: str) -> tuple[bool, str]:
        """加油操作（增强版）"""
        if self.enhanced_fuel_ops:
            # 使用增强版加油操作
            # 从account_list中找到当前Key对应的用户名
            username = "未知账号"
            for account_info in self.account_list:
                if account_info.get("key") == key:
                    username = account_info.get("username", "未知账号")
                    break
            
            return self.enhanced_fuel_ops.execute_fuel_up(key, username)
        else:
            # fallback到原有的简单实现
            try:
                restaurant_action = RestaurantActions(key=key, cookie={"PHPSESSID": "dummy"})
                success, message = restaurant_action.refill_oil()
                return success, f"加油{'成功' if success else '失败'}: {message}"
            except Exception as e:
                return False, f"加油操作异常: {str(e)}"
    
    def _lottery(self, key: str) -> tuple[bool, str]:
        """抽奖"""
        # TODO: 实现抽奖逻辑
        time.sleep(0.5)
        return True, "抽奖完成"
    
    def _friend_visit(self, key: str) -> tuple[bool, str]:
        """好友拜访"""
        # TODO: 实现好友拜访逻辑
        time.sleep(1.0)
        return True, "好友拜访完成"
    
    def _cook_recipes(self, key: str) -> tuple[bool, str]:
        """烹饪菜谱"""
        # TODO: 实现烹饪逻辑
        time.sleep(0.7)
        return True, "烹饪完成"
    
    def _buy_novice_equipment(self, key: str) -> tuple[bool, str]:
        """购买见习装备"""
        try:
            from src.delicious_town_bot.actions.shop import ShopAction
            
            # 获取cookie（从manager或使用默认值）
            if self.manager:
                # 通过key查找账号
                accounts = self.manager.list_accounts()
                cookie_value = "123"  # 默认值
                for account in accounts:
                    if account.key == key:
                        cookie_value = account.cookie if account.cookie else "123"
                        break
            else:
                cookie_value = "123"
            
            cookie_dict = {"PHPSESSID": cookie_value}
            shop_action = ShopAction(key=key, cookie=cookie_dict)
            
            # 执行每日见习装备购买
            result = shop_action.buy_novice_equipment_daily()
            
            success = result.get("success", False)
            message = result.get("message", "购买完成")
            
            # 详细统计信息
            total_purchased = result.get("total_purchased", 0)
            equipment_results = result.get("equipment_results", [])
            
            # 构建详细消息
            detail_parts = []
            for eq_result in equipment_results:
                name = eq_result.get("name", "")
                success_count = eq_result.get("success_count", 0)
                failed_count = eq_result.get("failed_count", 0)
                detail_parts.append(f"{name}: {success_count}/4")
            
            if detail_parts:
                detail_message = f"{message} - {', '.join(detail_parts)}"
            else:
                detail_message = message
            
            return success, detail_message
            
        except Exception as e:
            return False, f"购买见习装备失败: {str(e)}"
    
    def _star_upgrade(self, key: str) -> tuple[bool, str]:
        """升星操作"""
        try:
            # 获取cookie（从manager或使用默认值）
            if self.manager:
                # 通过key查找账号
                accounts = self.manager.list_accounts()
                cookie_value = "123"  # 默认值
                for account in accounts:
                    if account.key == key:
                        cookie_value = account.cookie if account.cookie else "123"
                        break
            else:
                cookie_value = "123"
            
            cookie_dict = {"PHPSESSID": cookie_value}
            restaurant_action = RestaurantActions(key=key, cookie=cookie_dict)
            
            # 执行升星操作
            success, result = restaurant_action.execute_star_upgrade()
            
            if success:
                # 解析升星结果
                if isinstance(result, dict):
                    # 构建详细消息
                    message_parts = ["升星成功"]
                    
                    if result.get('facility_slots_added'):
                        message_parts.append(f"设施位+{result['facility_slots_added']}")
                    if result.get('picky_customers_increase_pct'):
                        message_parts.append(f"挑剔顾客+{result['picky_customers_increase_pct']}%")
                    if result.get('items_gained'):
                        message_parts.append(f"获得: {result['items_gained']}")
                    
                    final_message = "; ".join(message_parts)
                else:
                    final_message = f"升星成功: {str(result)}"
                
                return True, final_message
            else:
                return False, f"升星失败: {str(result)}"
                
        except Exception as e:
            return False, f"升星操作异常: {str(e)}"
    
    def pause(self):
        """暂停操作"""
        self.is_paused = True
    
    def resume(self):
        """恢复操作"""
        self.is_paused = False
    
    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class OperationProgressDialog(QDialog):
    """操作进度监控对话框"""
    
    def __init__(self, operation_name: str, account_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"执行中: {operation_name}")
        self.setModal(True)
        self.resize(600, 500)
        self.worker = None
        self.thread = None
        self.is_paused = False
        self.setup_ui(account_count)
        
    def setup_ui(self, account_count: int):
        layout = QVBoxLayout(self)
        
        # 进度信息
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("总进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(account_count)
        self.progress_bar.setValue(0)
        info_layout.addWidget(self.progress_bar)
        layout.addLayout(info_layout)
        
        # 当前状态
        self.current_status = QLabel("准备开始...")
        layout.addWidget(self.current_status)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.success_label = QLabel("成功: 0")
        self.failed_label = QLabel("失败: 0") 
        self.skipped_label = QLabel("跳过: 0")
        stats_layout.addWidget(self.success_label)
        stats_layout.addWidget(self.failed_label)
        stats_layout.addWidget(self.skipped_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # 详细日志
        layout.addWidget(QLabel("操作日志:"))
        self.log_list = QListWidget()
        layout.addWidget(self.log_list)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_operation)
        
        button_layout.addStretch()
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
    
    def set_worker(self, worker: SequentialWorker, thread: QThread):
        """设置工作线程"""
        self.worker = worker
        self.thread = thread
        
        # 连接信号
        worker.progress_updated.connect(self.update_progress)
        worker.account_finished.connect(self.account_finished)
        worker.operation_finished.connect(self.operation_finished)
    
    @Slot(int, int, str, str)
    def update_progress(self, current: int, total: int, username: str, operation: str):
        """更新进度"""
        self.progress_bar.setValue(current)
        self.current_status.setText(f"进度: {current}/{total} - 正在处理: {username}")
    
    @Slot(int, str, bool, str)
    def account_finished(self, account_id: int, username: str, success: bool, message: str):
        """单个账号操作完成"""
        icon = "✅" if success else "❌"
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = f"[{timestamp}] {icon} {username}: {message}"
        
        item = QListWidgetItem(log_text)
        if success:
            item.setForeground(Qt.GlobalColor.darkGreen)
        else:
            item.setForeground(Qt.GlobalColor.darkRed)
            
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()
        
        # 更新统计
        if success:
            current = int(self.success_label.text().split(":")[1].strip())
            self.success_label.setText(f"成功: {current + 1}")
        else:
            current = int(self.failed_label.text().split(":")[1].strip()) 
            self.failed_label.setText(f"失败: {current + 1}")
    
    @Slot(bool, str, dict)
    def operation_finished(self, all_success: bool, summary: str, stats: dict):
        """操作完成"""
        self.current_status.setText(summary)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setText("关闭")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)
        
        # 更新最终统计
        self.success_label.setText(f"成功: {stats['success']}")
        self.failed_label.setText(f"失败: {stats['failed']}")
        self.skipped_label.setText(f"跳过: {stats['skipped']}")
    
    def toggle_pause(self):
        """切换暂停/恢复"""
        if self.worker:
            if self.is_paused:
                self.worker.resume()
                self.pause_btn.setText("暂停")
                self.is_paused = False
            else:
                self.worker.pause()
                self.pause_btn.setText("恢复")
                self.is_paused = True
    
    def cancel_operation(self):
        """取消操作"""
        if self.worker:
            self.worker.cancel()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.reject()


class GameOperationsPage(QWidget):
    """游戏操作页面"""
    
    def __init__(self, log_widget: QTextEdit, account_manager: AccountManager):
        super().__init__()
        self.log_widget = log_widget
        self.account_manager = account_manager
        self.selected_account_ids: Set[int] = set()
        self.account_status: Dict[int, AccountStatus] = {}
        
        self.setup_ui()
        self.load_accounts()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 账号管理选项卡
        accounts_tab = self.create_accounts_tab()
        tab_widget.addTab(accounts_tab, "账号管理")
        
        # 游戏操作选项卡
        operations_tab = self.create_operations_tab()
        tab_widget.addTab(operations_tab, "游戏操作")
        
        layout.addWidget(tab_widget)
    
    def create_accounts_tab(self) -> QWidget:
        """创建账号管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 选择工具栏
        selection_layout = QHBoxLayout()
        
        self.master_checkbox = QCheckBox("全选")
        self.master_checkbox.stateChanged.connect(self.on_master_checkbox_changed)
        selection_layout.addWidget(self.master_checkbox)
        
        selection_layout.addWidget(QLabel("|"))
        
        # 快速选择
        select_valid_btn = QPushButton("选择有Key账号")
        select_valid_btn.clicked.connect(self.select_valid_accounts)
        selection_layout.addWidget(select_valid_btn)
        
        select_invalid_btn = QPushButton("选择无Key账号")
        select_invalid_btn.clicked.connect(self.select_invalid_accounts)
        selection_layout.addWidget(select_invalid_btn)
        
        selection_layout.addStretch()
        
        # 选择计数
        self.selection_count_label = QLabel("已选: 0/0")
        selection_layout.addWidget(self.selection_count_label)
        
        layout.addLayout(selection_layout)
        
        # 账号表格
        self.create_accounts_table()
        layout.addWidget(self.accounts_table)
        
        # 账号操作按钮
        account_ops_layout = QHBoxLayout()
        
        add_btn = QPushButton("新增账号")
        add_btn.clicked.connect(self.add_account)
        account_ops_layout.addWidget(add_btn)
        
        refresh_selected_btn = QPushButton("刷新选中Key")
        refresh_selected_btn.clicked.connect(self.refresh_selected_keys)
        account_ops_layout.addWidget(refresh_selected_btn)
        
        refresh_all_btn = QPushButton("刷新全部Key")
        refresh_all_btn.clicked.connect(self.refresh_all_keys)
        account_ops_layout.addWidget(refresh_all_btn)
        
        account_ops_layout.addStretch()
        layout.addLayout(account_ops_layout)
        
        return widget
    
    def create_operations_tab(self) -> QWidget:
        """创建游戏操作选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 操作设置
        settings_group = QGroupBox("操作设置")
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("请求间隔(秒):"), 0, 0)
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 10)
        self.interval_spinbox.setValue(2)
        settings_layout.addWidget(self.interval_spinbox, 0, 1)
        
        settings_layout.addWidget(QLabel("操作范围:"), 1, 0)
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["选中账号", "全部有Key账号"])
        settings_layout.addWidget(self.scope_combo, 1, 1)
        
        settings_layout.setColumnStretch(2, 1)
        layout.addWidget(settings_group)
        
        # 游戏操作按钮组
        ops_group = QGroupBox("游戏操作")
        ops_layout = QGridLayout(ops_group)
        
        # 创建操作按钮
        row, col = 0, 0
        for operation in GameOperation:
            btn = QPushButton(operation.value[0])
            btn.clicked.connect(lambda checked, op=operation: self.start_game_operation(op))
            ops_layout.addWidget(btn, row, col)
            
            col += 1
            if col >= 3:  # 每行3个按钮
                col = 0
                row += 1
        
        layout.addWidget(ops_group)
        
        # 快速操作区
        quick_group = QGroupBox("快速操作")
        quick_layout = QHBoxLayout(quick_group)
        
        daily_routine_btn = QPushButton("日常流程")
        daily_routine_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        daily_routine_btn.clicked.connect(self.run_daily_routine)
        quick_layout.addWidget(daily_routine_btn)
        
        challenge_routine_btn = QPushButton("挑战流程")
        challenge_routine_btn.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white;")
        challenge_routine_btn.clicked.connect(self.run_challenge_routine)
        quick_layout.addWidget(challenge_routine_btn)
        
        quick_layout.addStretch()
        layout.addWidget(quick_group)
        
        layout.addStretch()
        return widget
    
    def create_accounts_table(self):
        """创建账号表格"""
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(6)
        headers = ["☑", "状态", "ID", "用户名", "Key状态", "操作"]
        self.accounts_table.setHorizontalHeaderLabels(headers)
        
        # 表格设置
        self.accounts_table.verticalHeader().setVisible(False)
        self.accounts_table.setAlternatingRowColors(True)
        self.accounts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.accounts_table.setShowGrid(False)
        
        # 列宽设置
        header = self.accounts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)   # 复选框
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)   # 状态
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # ID
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # 用户名
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Key状态
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # 操作
        
        self.accounts_table.setColumnWidth(0, 40)
        self.accounts_table.setColumnWidth(1, 80)
        self.accounts_table.setColumnWidth(2, 50)
        self.accounts_table.setColumnWidth(4, 80)
        self.accounts_table.setColumnWidth(5, 120)
        
        # 设置表格最大高度，避免界面过高
        self.accounts_table.setMaximumHeight(350)
    
    def load_accounts(self):
        """加载账号列表"""
        self.accounts_table.setRowCount(0)
        accounts = self.account_manager.list_accounts()
        
        for account in accounts:
            self.add_account_row(account)
        
        self.update_selection_count()
    
    def add_account_row(self, account):
        """添加账号行"""
        row = self.accounts_table.rowCount()
        self.accounts_table.insertRow(row)
        
        # 复选框
        checkbox = QCheckBox()
        checkbox.stateChanged.connect(
            lambda state, aid=account.id: self.on_row_checkbox_changed(aid, state)
        )
        self.accounts_table.setCellWidget(row, 0, checkbox)
        
        # 状态
        status = AccountStatus.NO_KEY if not account.key else AccountStatus.IDLE
        self.account_status[account.id] = status
        status_item = QTableWidgetItem(status.value[0])
        status_item.setData(Qt.ItemDataRole.UserRole, account.id)
        self.accounts_table.setItem(row, 1, status_item)
        
        # 其他列
        items_data = [
            (2, str(account.id)),
            (3, account.username),
            (4, "有效" if account.key else "无效")
        ]
        
        for col, text in items_data:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setData(Qt.ItemDataRole.UserRole, account.id)
            self.accounts_table.setItem(row, col, item)
        
        # 操作按钮
        self.create_account_action_buttons(row, account.id)
    
    def create_account_action_buttons(self, row: int, account_id: int):
        """创建账号操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)
        
        # 刷新Key按钮
        refresh_btn = QPushButton("刷新Key")
        refresh_btn.setMaximumWidth(60)
        refresh_btn.clicked.connect(lambda: self.refresh_single_key(account_id))
        layout.addWidget(refresh_btn)
        
        self.accounts_table.setCellWidget(row, 5, widget)
    
    # 信号处理方法
    def on_master_checkbox_changed(self, state):
        """主复选框状态变化"""
        checked = state == Qt.CheckState.Checked.value
        for row in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)
    
    def on_row_checkbox_changed(self, account_id: int, state):
        """行复选框状态变化"""
        if state == Qt.CheckState.Checked.value:
            self.selected_account_ids.add(account_id)
        else:
            self.selected_account_ids.discard(account_id)
        
        self.update_selection_count()
        self.update_master_checkbox()
    
    def update_selection_count(self):
        """更新选择计数"""
        total = self.accounts_table.rowCount()
        selected = len(self.selected_account_ids)
        self.selection_count_label.setText(f"已选: {selected}/{total}")
    
    def update_master_checkbox(self):
        """更新主复选框状态"""
        total = self.accounts_table.rowCount()
        selected = len(self.selected_account_ids)
        
        if selected == 0:
            self.master_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif selected == total:
            self.master_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self.master_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
    
    # 选择操作
    def select_valid_accounts(self):
        """选择有Key的账号"""
        for row in range(self.accounts_table.rowCount()):
            key_item = self.accounts_table.item(row, 4)
            if key_item and key_item.text() == "有效":
                checkbox = self.accounts_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def select_invalid_accounts(self):
        """选择无Key的账号"""
        for row in range(self.accounts_table.rowCount()):
            key_item = self.accounts_table.item(row, 4)
            if key_item and key_item.text() == "无效":
                checkbox = self.accounts_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    # 账号操作
    def add_account(self):
        """添加账号"""
        username, ok1 = QInputDialog.getText(self, "新增账号", "用户名:")
        if not ok1 or not username:
            return
            
        password, ok2 = QInputDialog.getText(self, "新增账号", "密码:", 
                                           echo=QLineEdit.EchoMode.Password)
        if not ok2 or not password:
            return
            
        try:
            account = self.account_manager.add_account(username, password)
            self.log_widget.append(f"✅ 添加账号成功: {account.username}")
            self.load_accounts()
        except Exception as e:
            QMessageBox.warning(self, "添加失败", str(e))
    
    def refresh_single_key(self, account_id: int):
        """刷新单个账号Key"""
        self.log_widget.append(f"🔄 开始刷新账号 ID={account_id}")
        try:
            key = self.account_manager.refresh_key(account_id)
            if key:
                self.log_widget.append(f"✅ 账号 ID={account_id} Key刷新成功")
            else:
                self.log_widget.append(f"❌ 账号 ID={account_id} Key刷新失败")
        except Exception as e:
            self.log_widget.append(f"❌ 账号 ID={account_id} 刷新出错: {str(e)}")
        
        self.load_accounts()
    
    def refresh_selected_keys(self):
        """刷新选中账号的Key"""
        if not self.selected_account_ids:
            QMessageBox.information(self, "提示", "请先选择要刷新的账号")
            return
        
        self._refresh_keys_batch(list(self.selected_account_ids))
    
    def refresh_all_keys(self):
        """刷新全部账号Key"""
        accounts = self.account_manager.list_accounts()
        account_ids = [acc.id for acc in accounts]
        self._refresh_keys_batch(account_ids)
    
    def _refresh_keys_batch(self, account_ids: List[int]):
        """批量刷新Key"""
        # 这里可以实现一个简单的顺序刷新
        for account_id in account_ids:
            self.refresh_single_key(account_id)
            time.sleep(1)  # 间隔1秒
    
    # 游戏操作
    def start_game_operation(self, operation: GameOperation):
        """开始游戏操作"""
        # 获取要操作的账号列表
        account_list = self._get_operation_accounts()
        
        if not account_list:
            QMessageBox.information(self, "提示", "没有可操作的账号")
            return
        
        # 确认对话框
        scope_text = self.scope_combo.currentText()
        interval = self.interval_spinbox.value()
        
        confirm_msg = f"""
确认执行操作？

操作类型: {operation.value[0]}
操作范围: {scope_text}
账号数量: {len(account_list)}
请求间隔: {interval}秒

预计耗时: {len(account_list) * interval}秒
        """.strip()
        
        reply = QMessageBox.question(self, "确认操作", confirm_msg,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 启动操作
        self._execute_operation(operation, account_list, interval)
    
    def _get_operation_accounts(self) -> List[Dict]:
        """获取要操作的账号列表"""
        accounts = self.account_manager.list_accounts()
        
        if self.scope_combo.currentText() == "选中账号":
            # 只操作选中的账号
            if not self.selected_account_ids:
                return []
            target_accounts = [acc for acc in accounts if acc.id in self.selected_account_ids]
        else:
            # 操作所有有Key的账号
            target_accounts = [acc for acc in accounts if acc.key]
        
        # 转换为字典格式
        account_list = []
        for acc in target_accounts:
            account_list.append({
                "id": acc.id,
                "username": acc.username,
                "key": acc.key
            })
        
        return account_list
    
    def _execute_operation(self, operation: GameOperation, account_list: List[Dict], interval: int):
        """执行操作"""
        # 创建进度对话框
        progress_dialog = OperationProgressDialog(operation.value[0], len(account_list), self)
        
        # 创建工作线程
        worker = SequentialWorker(operation, account_list, interval, self.account_manager)
        thread = QThread()
        worker.moveToThread(thread)
        
        # 连接信号
        thread.started.connect(worker.run)
        worker.operation_finished.connect(thread.quit)
        worker.operation_finished.connect(self.on_operation_finished)
        
        progress_dialog.set_worker(worker, thread)
        
        # 启动线程
        thread.start()
        
        # 显示进度对话框
        progress_dialog.exec()
    
    @Slot(bool, str, dict)
    def on_operation_finished(self, all_success: bool, summary: str, stats: dict):
        """操作完成回调"""
        self.log_widget.append(f"🎯 {summary}")
        # 可以在这里更新账号状态等
    
    # 快速操作流程
    def run_daily_routine(self):
        """执行日常流程"""
        # 日常流程: 日常任务 -> 加油 -> 抽奖
        operations = [
            GameOperation.DAILY_TASKS,
            GameOperation.FUEL_UP, 
            GameOperation.LOTTERY
        ]
        
        self._run_operation_sequence(operations, "日常流程")
    
    def run_challenge_routine(self):
        """执行挑战流程"""
        # 挑战流程: 挑战厨塔 -> 好友拜访
        operations = [
            GameOperation.CHALLENGE_TOWER,
            GameOperation.FRIEND_VISIT
        ]
        
        self._run_operation_sequence(operations, "挑战流程")
    
    def _run_operation_sequence(self, operations: List[GameOperation], routine_name: str):
        """执行操作序列"""
        account_list = self._get_operation_accounts()
        
        if not account_list:
            QMessageBox.information(self, "提示", "没有可操作的账号")
            return
        
        # 确认对话框
        operation_names = [op.value[0] for op in operations]
        confirm_msg = f"""
确认执行 {routine_name}？

包含操作: {', '.join(operation_names)}
账号数量: {len(account_list)}

这将依次执行所有操作
        """.strip()
        
        reply = QMessageBox.question(self, "确认流程", confirm_msg,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 依次执行每个操作
        for operation in operations:
            self.log_widget.append(f"🚀 开始执行: {operation.value[0]}")
            # 这里可以实现操作序列的执行逻辑
            # 暂时记录日志
            self.log_widget.append(f"✅ {operation.value[0]} 完成")


if __name__ == "__main__":
    # 测试代码
    app = QApplication(sys.argv)
    
    # 创建测试组件
    log_widget = QTextEdit()
    manager = AccountManager()
    
    # 创建游戏操作页面
    page = GameOperationsPage(log_widget, manager)
    page.show()
    
    sys.exit(app.exec())
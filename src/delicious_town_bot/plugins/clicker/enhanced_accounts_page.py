"""
增强版账号管理页面
支持50个账号的批量管理操作
"""
import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Set, Dict, Any, Optional
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QCheckBox, QComboBox, QLabel,
    QLineEdit, QMessageBox, QInputDialog, QDialog, QProgressBar,
    QListWidget, QListWidgetItem, QHeaderView, QFrame, QTextEdit,
    QAbstractItemView, QSizePolicy
)

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.constants import Street


class AccountStatus(Enum):
    """账号状态枚举"""
    IDLE = ("空闲", "#28a745")
    RUNNING = ("执行中", "#007bff")
    ERROR = ("错误", "#dc3545")
    OFFLINE = ("离线", "#6c757d")
    NO_KEY = ("无Key", "#ffc107")


class BatchOperationType(Enum):
    """批量操作类型"""
    REFRESH_KEY = "刷新Key"
    VERIFY_LOGIN = "验证登录"
    DELETE_ACCOUNTS = "删除账号"
    EXPORT_ACCOUNTS = "导出账号"


class AccountStatusManager(QObject):
    """账号状态管理器"""
    status_changed = Signal(int, str, str)  # 账号ID, 状态名, 状态颜色
    
    def __init__(self):
        super().__init__()
        self.account_status: Dict[int, AccountStatus] = {}
        self.last_activity: Dict[int, datetime] = {}
        
        # 定时器检查离线状态
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_offline_accounts)
        self.check_timer.start(30000)  # 30秒检查一次
        
    def update_status(self, account_id: int, status: AccountStatus):
        """更新账号状态"""
        self.account_status[account_id] = status
        self.last_activity[account_id] = datetime.now()
        self.status_changed.emit(account_id, status.value[0], status.value[1])
        
    def get_status(self, account_id: int) -> AccountStatus:
        """获取账号状态"""
        return self.account_status.get(account_id, AccountStatus.OFFLINE)
        
    def check_offline_accounts(self):
        """检查长时间无活动的账号，标记为离线"""
        offline_threshold = timedelta(minutes=10)
        current_time = datetime.now()
        
        for account_id, last_time in self.last_activity.items():
            if current_time - last_time > offline_threshold:
                if self.account_status.get(account_id) != AccountStatus.OFFLINE:
                    self.update_status(account_id, AccountStatus.OFFLINE)


class BatchWorker(QObject):
    """批量操作的后台处理器"""
    progress_updated = Signal(int, int, str)  # 当前进度, 总数, 消息
    account_finished = Signal(int, bool, str)  # 账号ID, 是否成功, 消息
    batch_finished = Signal(bool, str)  # 是否成功, 结果消息
    
    def __init__(self, operation_type: BatchOperationType, account_ids: List[int], manager: AccountManager):
        super().__init__()
        self.operation_type = operation_type
        self.account_ids = account_ids
        self.manager = manager
        self.is_cancelled = False
        self.success_count = 0
        self.error_count = 0
        
    def run(self):
        """执行批量操作"""
        total = len(self.account_ids)
        
        for i, account_id in enumerate(self.account_ids):
            if self.is_cancelled:
                break
                
            self.progress_updated.emit(i + 1, total, f"正在处理账号 ID={account_id}")
            
            try:
                success = self._process_single_account(account_id)
                if success:
                    self.success_count += 1
                    self.account_finished.emit(account_id, True, "操作成功")
                else:
                    self.error_count += 1
                    self.account_finished.emit(account_id, False, "操作失败")
            except Exception as e:
                self.error_count += 1
                self.account_finished.emit(account_id, False, f"错误: {str(e)}")
        
        # 发送完成信号
        if self.is_cancelled:
            self.batch_finished.emit(False, "操作已取消")
        else:
            success_msg = f"批量操作完成: 成功 {self.success_count}, 失败 {self.error_count}"
            self.batch_finished.emit(self.error_count == 0, success_msg)
    
    def _process_single_account(self, account_id: int) -> bool:
        """处理单个账号的操作"""
        if self.operation_type == BatchOperationType.REFRESH_KEY:
            try:
                key = self.manager.refresh_key(account_id)
                return bool(key)
            except:
                return False
        elif self.operation_type == BatchOperationType.DELETE_ACCOUNTS:
            try:
                self.manager.delete_account(account_id)
                return True
            except:
                return False
        # 其他操作类型的实现...
        return False
    
    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class BatchProgressDialog(QDialog):
    """批量操作进度监控窗口"""
    
    def __init__(self, operation_name: str, account_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"正在执行: {operation_name}")
        self.setModal(True)
        self.resize(500, 400)
        self.worker = None
        self.thread = None
        self.setup_ui(account_count)
        
    def setup_ui(self, account_count: int):
        layout = QVBoxLayout(self)
        
        # 总体进度条
        layout.addWidget(QLabel("整体进度:"))
        self.overall_progress = QProgressBar()
        self.overall_progress.setMaximum(account_count)
        self.overall_progress.setValue(0)
        layout.addWidget(self.overall_progress)
        
        # 当前状态标签
        self.current_status = QLabel("准备开始...")
        layout.addWidget(self.current_status)
        
        # 详细状态列表
        layout.addWidget(QLabel("详细状态:"))
        self.status_list = QListWidget()
        layout.addWidget(self.status_list)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_operation)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def set_worker(self, worker: BatchWorker, thread: QThread):
        """设置工作线程"""
        self.worker = worker
        self.thread = thread
        
        # 连接信号
        worker.progress_updated.connect(self.update_progress)
        worker.account_finished.connect(self.account_finished)
        worker.batch_finished.connect(self.batch_finished)
    
    @Slot(int, int, str)
    def update_progress(self, current: int, total: int, message: str):
        """更新进度"""
        self.overall_progress.setValue(current)
        self.current_status.setText(f"进度: {current}/{total} - {message}")
    
    @Slot(int, bool, str)
    def account_finished(self, account_id: int, success: bool, message: str):
        """单个账号操作完成"""
        icon = "✅" if success else "❌"
        item_text = f"{icon} ID={account_id}: {message}"
        item = QListWidgetItem(item_text)
        self.status_list.addItem(item)
        self.status_list.scrollToBottom()
    
    @Slot(bool, str)
    def batch_finished(self, success: bool, message: str):
        """批量操作完成"""
        self.current_status.setText(message)
        self.cancel_btn.setText("关闭")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)
    
    def cancel_operation(self):
        """取消操作"""
        if self.worker:
            self.worker.cancel()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.reject()


class EnhancedAccountsPage(QWidget):
    """增强版账号管理页面"""
    
    def __init__(self, log_widget: QTextEdit, manager: AccountManager):
        super().__init__()
        self.log_widget = log_widget
        self.manager = manager
        self.status_manager = AccountStatusManager()
        self.selected_account_ids: Set[int] = set()
        
        self.setup_ui()
        self.load_accounts()
        self.connect_signals()
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 第一行工具栏：选择工具
        selection_toolbar = self.create_selection_toolbar()
        layout.addLayout(selection_toolbar)
        
        # 第二行工具栏：批量操作
        batch_toolbar = self.create_batch_toolbar()
        layout.addLayout(batch_toolbar)
        
        # 第三行：筛选工具
        filter_toolbar = self.create_filter_toolbar()
        layout.addLayout(filter_toolbar)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 账号表格
        self.create_accounts_table()
        layout.addWidget(self.table)
        
    def create_selection_toolbar(self) -> QHBoxLayout:
        """创建选择工具栏"""
        layout = QHBoxLayout()
        
        # 全选复选框
        self.master_checkbox = QCheckBox("全选")
        self.master_checkbox.stateChanged.connect(self.on_master_checkbox_changed)
        layout.addWidget(self.master_checkbox)
        
        # 选择控制按钮
        self.invert_btn = QPushButton("反选")
        self.invert_btn.clicked.connect(self.invert_selection)
        layout.addWidget(self.invert_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_selection)
        layout.addWidget(self.clear_btn)
        
        # 分隔符
        layout.addWidget(self.create_separator())
        
        # 快速选择按钮
        self.select_idle_btn = QPushButton("选择空闲")
        self.select_idle_btn.clicked.connect(lambda: self.quick_select_by_status(AccountStatus.IDLE))
        layout.addWidget(self.select_idle_btn)
        
        self.select_error_btn = QPushButton("选择错误")
        self.select_error_btn.clicked.connect(lambda: self.quick_select_by_status(AccountStatus.ERROR))
        layout.addWidget(self.select_error_btn)
        
        self.select_no_key_btn = QPushButton("选择无Key")
        self.select_no_key_btn.clicked.connect(lambda: self.quick_select_by_status(AccountStatus.NO_KEY))
        layout.addWidget(self.select_no_key_btn)
        
        # 选择计数标签
        self.selection_count_label = QLabel("已选: 0/0")
        layout.addStretch()
        layout.addWidget(self.selection_count_label)
        
        return layout
    
    def create_batch_toolbar(self) -> QHBoxLayout:
        """创建批量操作工具栏"""
        layout = QHBoxLayout()
        
        # 批量操作按钮
        self.batch_refresh_btn = QPushButton("批量刷新Key")
        self.batch_refresh_btn.clicked.connect(lambda: self.start_batch_operation(BatchOperationType.REFRESH_KEY))
        layout.addWidget(self.batch_refresh_btn)
        
        self.batch_verify_btn = QPushButton("批量验证登录")
        self.batch_verify_btn.clicked.connect(lambda: self.start_batch_operation(BatchOperationType.VERIFY_LOGIN))
        layout.addWidget(self.batch_verify_btn)
        
        self.batch_delete_btn = QPushButton("批量删除")
        self.batch_delete_btn.clicked.connect(lambda: self.start_batch_operation(BatchOperationType.DELETE_ACCOUNTS))
        layout.addWidget(self.batch_delete_btn)
        
        layout.addWidget(self.create_separator())
        
        # 账号管理按钮
        self.add_account_btn = QPushButton("新增账号")
        self.add_account_btn.clicked.connect(self.add_account)
        layout.addWidget(self.add_account_btn)
        
        self.import_btn = QPushButton("导入账号")
        self.import_btn.clicked.connect(self.import_accounts)
        layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("导出选中")
        self.export_btn.clicked.connect(lambda: self.start_batch_operation(BatchOperationType.EXPORT_ACCOUNTS))
        layout.addWidget(self.export_btn)
        
        layout.addStretch()
        
        return layout
    
    def create_filter_toolbar(self) -> QHBoxLayout:
        """创建筛选工具栏"""
        layout = QHBoxLayout()
        
        # 搜索框
        layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入用户名或ID...")
        self.search_edit.textChanged.connect(self.apply_filters)
        layout.addWidget(self.search_edit)
        
        # 状态筛选
        layout.addWidget(QLabel("状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部", None)
        for status in AccountStatus:
            self.status_filter.addItem(status.value[0], status)
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        layout.addWidget(self.status_filter)
        
        # 街道筛选
        layout.addWidget(QLabel("街道:"))
        self.street_filter = QComboBox()
        self.street_filter.addItem("全部", None)
        for street in Street:
            if street.value > 0:  # 排除特殊值
                self.street_filter.addItem(street.name, street)
        self.street_filter.currentTextChanged.connect(self.apply_filters)
        layout.addWidget(self.street_filter)
        
        # Key状态筛选
        layout.addWidget(QLabel("Key:"))
        self.key_filter = QComboBox()
        self.key_filter.addItems(["全部", "有Key", "无Key"])
        self.key_filter.currentTextChanged.connect(self.apply_filters)
        layout.addWidget(self.key_filter)
        
        # 重置按钮
        self.reset_filter_btn = QPushButton("重置筛选")
        self.reset_filter_btn.clicked.connect(self.reset_filters)
        layout.addWidget(self.reset_filter_btn)
        
        layout.addStretch()
        
        return layout
    
    def create_accounts_table(self):
        """创建账号表格"""
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        headers = ["☑", "状态", "ID", "用户名", "餐厅", "街道", "Key?", "最后登录", "操作"]
        self.table.setHorizontalHeaderLabels(headers)
        
        # 表格设置
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        
        # 列宽设置
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 复选框
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # 状态
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 用户名
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # 餐厅
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # 街道
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Key?
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # 最后登录
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # 操作
        
        self.table.setColumnWidth(0, 40)   # 复选框
        self.table.setColumnWidth(1, 70)   # 状态
        self.table.setColumnWidth(2, 50)   # ID
        self.table.setColumnWidth(5, 80)   # 街道
        self.table.setColumnWidth(6, 60)   # Key?
        self.table.setColumnWidth(7, 140)  # 最后登录
        self.table.setColumnWidth(8, 120)  # 操作
    
    def create_separator(self) -> QFrame:
        """创建分隔符"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator
    
    def connect_signals(self):
        """连接信号"""
        self.status_manager.status_changed.connect(self.on_account_status_changed)
    
    def load_accounts(self):
        """加载账号列表"""
        self.table.setRowCount(0)
        accounts = self.manager.list_accounts()
        
        for account in accounts:
            self.add_account_row(account)
        
        self.update_selection_count()
    
    def add_account_row(self, account):
        """添加账号行"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # 复选框
        checkbox = QCheckBox()
        checkbox.stateChanged.connect(lambda state, aid=account.id: self.on_row_checkbox_changed(aid, state))
        self.table.setCellWidget(row, 0, checkbox)
        
        # 状态
        status = AccountStatus.NO_KEY if not account.key else AccountStatus.IDLE
        status_item = QTableWidgetItem(status.value[0])
        status_item.setBackground(Qt.GlobalColor.transparent)
        status_item.setForeground(Qt.GlobalColor.black)
        status_item.setData(Qt.ItemDataRole.UserRole, account.id)
        self.table.setItem(row, 1, status_item)
        
        # 其他列
        items_data = [
            (2, str(account.id)),
            (3, account.username),
            (4, account.restaurant or "-"),
            (5, "-"),  # 街道信息需要从游戏数据获取
            (6, "Y" if account.key else "N"),
            (7, account.last_login.strftime("%Y-%m-%d %H:%M") if account.last_login else "-")
        ]
        
        for col, text in items_data:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setData(Qt.ItemDataRole.UserRole, account.id)
            self.table.setItem(row, col, item)
        
        # 操作按钮
        self.create_action_buttons(row, account.id)
        
        # 更新状态管理器
        self.status_manager.update_status(account.id, status)
    
    def create_action_buttons(self, row: int, account_id: int):
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(2)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setMaximumWidth(50)
        refresh_btn.clicked.connect(lambda: self.refresh_single_account(account_id))
        layout.addWidget(refresh_btn)
        
        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setMaximumWidth(50)
        delete_btn.clicked.connect(lambda: self.delete_single_account(account_id))
        layout.addWidget(delete_btn)
        
        self.table.setCellWidget(row, 8, widget)
    
    # 信号处理方法
    @Slot(int, str, str)
    def on_account_status_changed(self, account_id: int, status_name: str, status_color: str):
        """账号状态变化处理"""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item and item.data(Qt.ItemDataRole.UserRole) == account_id:
                item.setText(status_name)
                # 这里可以添加颜色设置
                break
    
    def on_master_checkbox_changed(self, state):
        """主复选框状态变化"""
        checked = state == Qt.CheckState.Checked.value
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
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
        total = self.table.rowCount()
        selected = len(self.selected_account_ids)
        self.selection_count_label.setText(f"已选: {selected}/{total}")
    
    def update_master_checkbox(self):
        """更新主复选框状态"""
        total = self.table.rowCount()
        selected = len(self.selected_account_ids)
        
        if selected == 0:
            self.master_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif selected == total:
            self.master_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self.master_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
    
    # 操作方法
    def invert_selection(self):
        """反选"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(not checkbox.isChecked())
    
    def clear_selection(self):
        """清空选择"""
        self.master_checkbox.setChecked(False)
    
    def quick_select_by_status(self, target_status: AccountStatus):
        """按状态快速选择"""
        self.clear_selection()
        for row in range(self.table.rowCount()):
            status_item = self.table.item(row, 1)
            if status_item and status_item.text() == target_status.value[0]:
                checkbox = self.table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def apply_filters(self):
        """应用筛选条件"""
        search_text = self.search_edit.text().lower()
        status_filter = self.status_filter.currentData()
        street_filter = self.street_filter.currentData()
        key_filter = self.key_filter.currentText()
        
        for row in range(self.table.rowCount()):
            show_row = True
            
            # 搜索筛选
            if search_text:
                username_item = self.table.item(row, 3)
                id_item = self.table.item(row, 2)
                if username_item and id_item:
                    username = username_item.text().lower()
                    account_id = id_item.text().lower()
                    if search_text not in username and search_text not in account_id:
                        show_row = False
            
            # 状态筛选
            if status_filter and show_row:
                status_item = self.table.item(row, 1)
                if status_item and status_item.text() != status_filter.value[0]:
                    show_row = False
            
            # Key状态筛选
            if key_filter != "全部" and show_row:
                key_item = self.table.item(row, 6)
                if key_item:
                    has_key = key_item.text() == "Y"
                    if (key_filter == "有Key" and not has_key) or (key_filter == "无Key" and has_key):
                        show_row = False
            
            self.table.setRowHidden(row, not show_row)
    
    def reset_filters(self):
        """重置筛选条件"""
        self.search_edit.clear()
        self.status_filter.setCurrentIndex(0)
        self.street_filter.setCurrentIndex(0)
        self.key_filter.setCurrentIndex(0)
        
        # 显示所有行
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)
    
    def start_batch_operation(self, operation_type: BatchOperationType):
        """启动批量操作"""
        if not self.selected_account_ids:
            QMessageBox.information(self, "提示", "请先选择要操作的账号")
            return
        
        # 确认对话框
        account_count = len(self.selected_account_ids)
        confirm_msg = f"确定要对选中的 {account_count} 个账号执行 {operation_type.value} 操作吗？"
        
        if operation_type == BatchOperationType.DELETE_ACCOUNTS:
            confirm_msg += "\n\n⚠️ 删除操作无法撤销！"
        
        reply = QMessageBox.question(self, "确认操作", confirm_msg,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 创建进度对话框
        progress_dialog = BatchProgressDialog(operation_type.value, account_count, self)
        
        # 创建工作线程
        worker = BatchWorker(operation_type, list(self.selected_account_ids), self.manager)
        thread = QThread()
        worker.moveToThread(thread)
        
        # 连接信号
        thread.started.connect(worker.run)
        worker.batch_finished.connect(thread.quit)
        worker.batch_finished.connect(self.on_batch_finished)
        
        progress_dialog.set_worker(worker, thread)
        
        # 启动线程
        thread.start()
        
        # 显示进度对话框
        progress_dialog.exec()
    
    @Slot(bool, str)
    def on_batch_finished(self, success: bool, message: str):
        """批量操作完成"""
        self.log_widget.append(f"📊 批量操作完成: {message}")
        self.load_accounts()  # 重新加载账号列表
        self.clear_selection()  # 清空选择
    
    def add_account(self):
        """添加单个账号"""
        username, ok1 = QInputDialog.getText(self, "新增账号", "用户名:")
        if not ok1 or not username:
            return
            
        password, ok2 = QInputDialog.getText(self, "新增账号", "密码:", 
                                           echo=QLineEdit.EchoMode.Password)
        if not ok2 or not password:
            return
            
        try:
            account = self.manager.add_account(username, password)
            self.log_widget.append(f"✅ 添加账号成功: ID={account.id}, 用户名={account.username}")
            self.load_accounts()
        except Exception as e:
            QMessageBox.warning(self, "添加失败", str(e))
    
    def refresh_single_account(self, account_id: int):
        """刷新单个账号"""
        self.status_manager.update_status(account_id, AccountStatus.RUNNING)
        self.log_widget.append(f"🔄 开始刷新账号 ID={account_id}")
        
        try:
            key = self.manager.refresh_key(account_id)
            if key:
                self.status_manager.update_status(account_id, AccountStatus.IDLE)
                self.log_widget.append(f"✅ 账号 ID={account_id} 刷新成功")
            else:
                self.status_manager.update_status(account_id, AccountStatus.ERROR)
                self.log_widget.append(f"❌ 账号 ID={account_id} 刷新失败")
        except Exception as e:
            self.status_manager.update_status(account_id, AccountStatus.ERROR)
            self.log_widget.append(f"❌ 账号 ID={account_id} 刷新出错: {str(e)}")
        
        self.load_accounts()
    
    def delete_single_account(self, account_id: int):
        """删除单个账号"""
        reply = QMessageBox.question(self, "确认删除", f"确定要删除账号 ID={account_id} 吗？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self.manager.delete_account(account_id)
            self.log_widget.append(f"✅ 删除账号成功: ID={account_id}")
            self.load_accounts()
        except Exception as e:
            QMessageBox.warning(self, "删除失败", str(e))
    
    def import_accounts(self):
        """导入账号"""
        # TODO: 实现导入功能
        QMessageBox.information(self, "功能开发中", "导入账号功能正在开发中...")
    
    def closeEvent(self, event):
        """关闭事件"""
        # 清理资源
        if hasattr(self, 'status_manager'):
            self.status_manager.check_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    # 测试代码
    app = QApplication(sys.argv)
    
    # 创建测试组件
    log_widget = QTextEdit()
    manager = AccountManager()
    
    # 创建增强版账号页面
    page = EnhancedAccountsPage(log_widget, manager)
    page.show()
    
    sys.exit(app.exec())
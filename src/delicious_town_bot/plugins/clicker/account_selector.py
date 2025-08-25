"""
账号选择器组件
支持单个账号和批量账号选择的通用组件
"""
from typing import Dict, Any, List, Optional, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QComboBox, QCheckBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QScrollArea, QButtonGroup,
    QRadioButton, QFrame
)
from PySide6.QtGui import QFont


class AccountSelector(QWidget):
    """账号选择器组件"""
    
    # 信号定义
    selection_changed = Signal(dict)  # 发射选择变化事件
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.accounts_data = []
        self.selected_accounts = []
        self.operation_mode = "single"  # "single" 或 "batch"
        self.on_selection_changed = None  # 回调函数
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout()
        
        # 操作模式选择
        mode_group = QGroupBox("操作模式")
        mode_layout = QHBoxLayout()
        
        self.mode_button_group = QButtonGroup()
        
        self.single_mode_radio = QRadioButton("单个账号操作")
        self.single_mode_radio.setChecked(True)
        self.single_mode_radio.toggled.connect(self.on_mode_changed)
        self.mode_button_group.addButton(self.single_mode_radio, 0)
        mode_layout.addWidget(self.single_mode_radio)
        
        self.batch_mode_radio = QRadioButton("批量账号操作")
        self.batch_mode_radio.toggled.connect(self.on_mode_changed)
        self.mode_button_group.addButton(self.batch_mode_radio, 1)
        mode_layout.addWidget(self.batch_mode_radio)
        
        mode_layout.addStretch()
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 账号选择区域
        selection_group = QGroupBox("账号选择")
        selection_layout = QVBoxLayout()
        
        # 单个账号选择
        self.single_selection_widget = self.create_single_selection_widget()
        selection_layout.addWidget(self.single_selection_widget)
        
        # 批量账号选择
        self.batch_selection_widget = self.create_batch_selection_widget()
        self.batch_selection_widget.setVisible(False)
        selection_layout.addWidget(self.batch_selection_widget)
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # 选择信息显示
        info_group = QGroupBox("选择信息")
        info_layout = QVBoxLayout()
        
        self.selection_info_label = QLabel("请选择账号")
        self.selection_info_label.setStyleSheet("QLabel { padding: 10px; background-color: #f8f9fa; border-radius: 5px; }")
        info_layout.addWidget(self.selection_info_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        self.setLayout(layout)
        
        # 初始化选择信息
        self.update_selection_info()
    
    def create_single_selection_widget(self) -> QWidget:
        """创建单个账号选择组件"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel("选择账号:"))
        
        self.account_combo = QComboBox()
        self.account_combo.addItem("请先加载账号数据", None)
        self.account_combo.currentIndexChanged.connect(self.on_single_selection_changed)
        layout.addWidget(self.account_combo)
        
        self.refresh_accounts_btn = QPushButton("🔄 刷新账号")
        self.refresh_accounts_btn.clicked.connect(self.refresh_accounts)
        layout.addWidget(self.refresh_accounts_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_batch_selection_widget(self) -> QWidget:
        """创建批量账号选择组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 批量操作控制
        controls_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("✅ 全选")
        self.select_all_btn.clicked.connect(self.select_all_accounts)
        controls_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("❌ 全不选")
        self.select_none_btn.clicked.connect(self.select_no_accounts)
        controls_layout.addWidget(self.select_none_btn)
        
        self.invert_selection_btn = QPushButton("🔄 反选")
        self.invert_selection_btn.clicked.connect(self.invert_selection)
        controls_layout.addWidget(self.invert_selection_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # 账号列表表格
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(4)
        self.accounts_table.setHorizontalHeaderLabels(["选择", "用户名", "餐厅", "状态"])
        
        # 设置表格属性
        header = self.accounts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 选择列固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 用户名列拉伸
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 餐厅列拉伸
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)   # 状态列固定宽度
        
        self.accounts_table.setColumnWidth(0, 60)
        self.accounts_table.setColumnWidth(3, 80)
        self.accounts_table.setAlternatingRowColors(True)
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.accounts_table)
        
        widget.setLayout(layout)
        return widget
    
    def on_mode_changed(self):
        """操作模式变化处理"""
        if self.single_mode_radio.isChecked():
            self.operation_mode = "single"
            self.single_selection_widget.setVisible(True)
            self.batch_selection_widget.setVisible(False)
        else:
            self.operation_mode = "batch"
            self.single_selection_widget.setVisible(False)
            self.batch_selection_widget.setVisible(True)
        
        self.update_selection_info()
        self.emit_selection_changed()
    
    def set_accounts_data(self, accounts: List[Dict[str, Any]]):
        """设置账号数据"""
        self.accounts_data = accounts
        self.refresh_account_combo()
        self.refresh_accounts_table()
        self.update_selection_info()
    
    def refresh_account_combo(self):
        """刷新单个账号选择下拉框"""
        self.account_combo.clear()
        
        if not self.accounts_data:
            self.account_combo.addItem("无可用账号", None)
            return
        
        self.account_combo.addItem("请选择账号", None)
        
        for i, account in enumerate(self.accounts_data):
            username = account.get("username", f"账户{i+1}")
            restaurant = account.get("restaurant_name", "未知餐厅")
            display_text = f"{username} ({restaurant})"
            self.account_combo.addItem(display_text, account)
    
    def refresh_accounts_table(self):
        """刷新批量账号选择表格"""
        self.accounts_table.setRowCount(len(self.accounts_data))
        
        for i, account in enumerate(self.accounts_data):
            # 选择复选框
            checkbox = QCheckBox()
            checkbox.toggled.connect(self.on_batch_selection_changed)
            self.accounts_table.setCellWidget(i, 0, checkbox)
            
            # 用户名
            username = account.get("username", f"账户{i+1}")
            username_item = QTableWidgetItem(username)
            username_item.setFlags(username_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.accounts_table.setItem(i, 1, username_item)
            
            # 餐厅
            restaurant = account.get("restaurant_name", "未知餐厅")
            restaurant_item = QTableWidgetItem(restaurant)
            restaurant_item.setFlags(restaurant_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.accounts_table.setItem(i, 2, restaurant_item)
            
            # 状态
            status = "在线" if account.get("key") and account.get("cookie") else "离线"
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # 设置状态颜色
            if status == "在线":
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            
            self.accounts_table.setItem(i, 3, status_item)
    
    def on_single_selection_changed(self):
        """单个账号选择变化"""
        self.update_selection_info()
        self.emit_selection_changed()
    
    def on_batch_selection_changed(self):
        """批量账号选择变化"""
        self.update_selection_info()
        self.emit_selection_changed()
    
    def select_all_accounts(self):
        """全选账号"""
        for i in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def select_no_accounts(self):
        """全不选账号"""
        for i in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def invert_selection(self):
        """反选账号"""
        for i in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(not checkbox.isChecked())
    
    def get_selected_accounts(self) -> List[Dict[str, Any]]:
        """获取选中的账号"""
        if self.operation_mode == "single":
            current_account = self.account_combo.currentData()
            return [current_account] if current_account else []
        else:
            selected = []
            for i in range(self.accounts_table.rowCount()):
                checkbox = self.accounts_table.cellWidget(i, 0)
                if checkbox and checkbox.isChecked() and i < len(self.accounts_data):
                    selected.append(self.accounts_data[i])
            return selected
    
    def get_operation_mode(self) -> str:
        """获取操作模式"""
        return self.operation_mode
    
    def update_selection_info(self):
        """更新选择信息显示"""
        selected_accounts = self.get_selected_accounts()
        
        if self.operation_mode == "single":
            if selected_accounts:
                account = selected_accounts[0]
                username = account.get("username", "未知用户")
                restaurant = account.get("restaurant_name", "未知餐厅")
                info_text = f"🎯 单个账号操作模式\n已选择账号: {username} ({restaurant})"
            else:
                info_text = "🎯 单个账号操作模式\n请选择一个账号"
        else:
            count = len(selected_accounts)
            if count > 0:
                usernames = [acc.get("username", "未知") for acc in selected_accounts[:3]]
                if count > 3:
                    usernames.append(f"等{count}个账号")
                info_text = f"📦 批量账号操作模式\n已选择 {count} 个账号: {', '.join(usernames)}"
            else:
                info_text = "📦 批量账号操作模式\n未选择任何账号"
        
        self.selection_info_label.setText(info_text)
    
    def emit_selection_changed(self):
        """发射选择变化信号"""
        selection_data = {
            "mode": self.operation_mode,
            "accounts": self.get_selected_accounts(),
            "count": len(self.get_selected_accounts())
        }
        
        # 发射信号
        self.selection_changed.emit(selection_data)
        
        # 调用回调函数
        if self.on_selection_changed:
            self.on_selection_changed(selection_data)
    
    def set_selection_changed_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置选择变化回调函数"""
        self.on_selection_changed = callback
    
    def refresh_accounts(self):
        """刷新账号数据（由外部实现）"""
        # 这个方法应该由使用者重写或连接到实际的刷新逻辑
        pass
    
    def is_valid_selection(self) -> bool:
        """检查是否有有效选择"""
        return len(self.get_selected_accounts()) > 0
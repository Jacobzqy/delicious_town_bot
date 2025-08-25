"""
重新设计的日常任务管理界面
采用现代产品设计理念：顶部工具栏 + 内容优先的布局
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import time

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QCheckBox, QProgressBar, QTextEdit, QMessageBox, QFrame,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QSpacerItem, QSizePolicy
)

from src.delicious_town_bot.utils.account_manager import AccountManager


class ModernDailyTasksPage(QWidget):
    """现代化的日常任务管理界面"""

    def __init__(self, account_manager: AccountManager, log_widget: QTextEdit):
        super().__init__()
        self.account_manager = account_manager
        self.log_widget = log_widget
        
        # 初始化工作线程
        self.signin_worker = None
        self.signin_thread = None
        
        self.setupUI()
        self.load_accounts()

    def setupUI(self):
        """设置现代化UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部工具栏 - 浅色背景，包含所有操作
        toolbar = self.create_modern_toolbar()
        layout.addWidget(toolbar)
        
        # 主内容区域 - 专注于数据展示
        main_content = self.create_main_content()
        layout.addWidget(main_content)
        
        # 底部状态栏 - 简洁明了
        status_bar = self.create_status_bar()
        layout.addWidget(status_bar)

    def create_modern_toolbar(self) -> QWidget:
        """创建现代化顶部工具栏"""
        toolbar = QFrame()
        toolbar.setObjectName("ModernToolbar")
        toolbar.setStyleSheet("""
            QFrame#ModernToolbar {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                min-height: 120px;
                max-height: 120px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                color: white;
                font-weight: 500;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.1);
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        layout = QVBoxLayout(toolbar)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # 标题行
        title_layout = QHBoxLayout()
        title_label = QLabel("🎮 日常任务管理")
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: white;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 全局控制按钮
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.cancel_btn = QPushButton("❌ 停止")
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_operations)
        
        title_layout.addWidget(self.pause_btn)
        title_layout.addWidget(self.cancel_btn)
        layout.addLayout(title_layout)
        
        # 快速操作区域 - 扁平化设计
        quick_actions = QHBoxLayout()
        quick_actions.setSpacing(12)
        
        # 核心操作组 - 最重要的功能
        core_group = self.create_action_group("核心操作", [
            ("🔄", "刷新", self.refresh_task_data),
            ("✅", "签到", self.start_batch_signin),
            ("⛽", "添油", self.start_batch_cycle_oil),
            ("🛒", "特价菜", self.start_batch_special_food_buy)
        ])
        quick_actions.addWidget(core_group)
        
        # 游戏任务组
        game_group = self.create_action_group("游戏任务", [
            ("✂️", "猜拳", self.start_batch_rock_paper_scissors),
            ("🍷", "猜杯", self.start_batch_guess_cup),
            ("👥", "好友", self.start_batch_friend_requests),
            ("🛡️", "守卫", self.start_batch_shrine_guard)
        ])
        quick_actions.addWidget(game_group)
        
        # 高级功能组
        advanced_group = self.create_action_group("高级功能", [
            ("🪳", "蟑螂", self.start_batch_roach_cycle),
            ("🍽️", "吃白食", self.start_batch_eat_cycle),
            ("🏪", "餐厅", self.start_update_restaurant_ids),
            ("💾", "缓存", self.start_refresh_friends_cache)
        ])
        quick_actions.addWidget(advanced_group)
        
        # 选择控制组
        select_group = self.create_action_group("账号选择", [
            ("☑️", "全选", self.select_all_accounts),
            ("☐", "清空", self.select_none_accounts),
            ("🔑", "有Key", self.select_accounts_with_key),
            ("⏳", "待购", self.select_pending_accounts)
        ])
        quick_actions.addWidget(select_group)
        
        quick_actions.addStretch()
        layout.addLayout(quick_actions)
        
        return toolbar

    def create_action_group(self, title: str, actions: List[tuple]) -> QWidget:
        """创建操作组"""
        group = QFrame()
        group.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # 组标题
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.8); margin-bottom: 4px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 按钮网格
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(4)
        
        for i, (icon, text, handler) in enumerate(actions):
            btn = QPushButton(f"{icon}")
            btn.setToolTip(text)  # 使用tooltip显示完整文字
            btn.setFixedSize(36, 36)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    border-radius: 18px;
                    padding: 0;
                    min-width: 36px;
                    max-width: 36px;
                    min-height: 36px;
                    max-height: 36px;
                }
            """)
            btn.clicked.connect(handler)
            
            # 存储按钮引用
            self.store_button_reference(text, btn)
            
            row, col = divmod(i, 2)
            buttons_layout.addWidget(btn, row, col)
        
        layout.addLayout(buttons_layout)
        return group

    def store_button_reference(self, text: str, btn: QPushButton):
        """存储按钮引用以便后续使用"""
        if "刷新" in text:
            self.refresh_btn = btn
        elif "签到" in text:
            self.batch_signin_btn = btn
        elif "添油" in text:
            self.batch_oil_btn = btn
        elif "特价菜" in text:
            self.special_food_btn = btn
        elif "猜拳" in text:
            self.rock_paper_scissors_btn = btn
        elif "猜杯" in text:
            self.guess_cup_btn = btn
        elif "好友" in text:
            self.batch_friend_btn = btn
        elif "守卫" in text:
            self.shrine_guard_btn = btn
        elif "蟑螂" in text:
            self.batch_roach_btn = btn
        elif "吃白食" in text:
            self.batch_eat_btn = btn
        elif "餐厅" in text:
            self.update_restaurant_id_btn = btn
        elif "缓存" in text:
            self.refresh_friends_btn = btn
        elif "全选" in text:
            self.select_all_btn = btn
        elif "清空" in text:
            self.select_none_btn = btn
        elif "有Key" in text:
            self.select_with_key_btn = btn
        elif "待购" in text:
            self.select_pending_btn = btn

    def create_main_content(self) -> QWidget:
        """创建主内容区域 - 专注于数据展示"""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(16)
        
        # 账号概览卡片 - 现代卡片设计
        overview_card = self.create_overview_card()
        layout.addWidget(overview_card)
        
        # 详细信息区域 - 可折叠
        details_card = self.create_details_card()
        layout.addWidget(details_card)
        
        return main_widget

    def create_overview_card(self) -> QWidget:
        """创建现代化的账号概览卡片"""
        card = QFrame()
        card.setObjectName("OverviewCard")
        card.setStyleSheet("""
            QFrame#OverviewCard {
                background: white;
                border: 1px solid #e1e5e9;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 卡片标题
        header_layout = QHBoxLayout()
        title_label = QLabel("📊 账号状态概览")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.addStretch()
        
        # 创建状态统计
        self.total_accounts_label = QLabel("总账号: 0")
        self.active_accounts_label = QLabel("有Key: 0") 
        self.completed_tasks_label = QLabel("已完成: 0")
        
        for label in [self.total_accounts_label, self.active_accounts_label, self.completed_tasks_label]:
            label.setStyleSheet("""
                padding: 4px 12px;
                background: #f8f9fa;
                border-radius: 16px;
                font-size: 12px;
                font-weight: 500;
                color: #6c757d;
            """)
            stats_layout.addWidget(label)
        
        header_layout.addLayout(stats_layout)
        layout.addLayout(header_layout)
        
        # 数据表格 - 现代化样式
        self.overview_table = QTableWidget()
        self.overview_table.setObjectName("ModernTable")
        self.overview_table.setStyleSheet("""
            QTableWidget#ModernTable {
                background: white;
                border: none;
                border-radius: 8px;
                gridline-color: #f1f3f4;
                selection-background-color: #e3f2fd;
            }
            QHeaderView::section {
                background: #f8f9fa;
                border: none;
                border-bottom: 2px solid #e9ecef;
                padding: 12px 8px;
                font-weight: 600;
                color: #495057;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f3f4;
            }
            QTableWidget::item:selected {
                background: #e3f2fd;
                color: #1976d2;
            }
        """)
        
        self.overview_table.setColumnCount(9)
        self.overview_table.setHorizontalHeaderLabels([
            "选择", "账号", "每日完成", "每日活跃", "每周完成", "每周活跃", "特价菜", "Key状态", "更新时间"
        ])
        
        # 表格属性设置
        self.overview_table.verticalHeader().setVisible(False)
        self.overview_table.setAlternatingRowColors(False)  # 使用自定义样式
        self.overview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.overview_table.horizontalHeader().setStretchLastSection(True)
        self.overview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.overview_table)
        return card

    def create_details_card(self) -> QWidget:
        """创建详细信息卡片"""
        card = QFrame()
        card.setObjectName("DetailsCard")
        card.setStyleSheet("""
            QFrame#DetailsCard {
                background: white;
                border: 1px solid #e1e5e9;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 详情标题
        title_label = QLabel("📋 任务详细信息")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # 账号选择
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("查看账号:"))
        
        self.detail_account_combo = QComboBox()
        self.detail_account_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                min-width: 200px;
            }
            QComboBox:focus {
                border-color: #80bdff;
            }
        """)
        account_layout.addWidget(self.detail_account_combo)
        account_layout.addStretch()
        
        layout.addLayout(account_layout)
        
        # 详细信息文本区域
        self.detail_text = QTextEdit()
        self.detail_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e9ecef;
                border-radius: 6px;
                background: #f8f9fa;
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        self.detail_text.setMaximumHeight(200)
        self.detail_text.setReadOnly(True)
        layout.addWidget(self.detail_text)
        
        return card

    def create_status_bar(self) -> QWidget:
        """创建现代化状态栏"""
        status_bar = QFrame()
        status_bar.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border-top: 1px solid #e9ecef;
                padding: 8px 16px;
                min-height: 32px;
                max-height: 32px;
            }
        """)
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 3px;
                background: white;
                height: 16px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #007bff;
                border-radius: 2px;
            }
        """)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        return status_bar

    # 以下是占位符方法，需要实现具体逻辑
    def load_accounts(self):
        """加载账号数据"""
        pass
    
    def refresh_task_data(self):
        """刷新任务数据"""
        pass
    
    def start_batch_signin(self):
        """开始批量签到"""
        pass
    
    def start_batch_cycle_oil(self):
        """开始循环添油"""
        pass
    
    def start_batch_special_food_buy(self):
        """开始特价菜购买"""
        pass
    
    def start_batch_rock_paper_scissors(self):
        """开始猜拳任务"""
        pass
    
    def start_batch_guess_cup(self):
        """开始猜杯任务"""
        pass
    
    def start_batch_friend_requests(self):
        """开始好友申请"""
        pass
    
    def start_batch_shrine_guard(self):
        """开始神殿守卫"""
        pass
    
    def start_batch_roach_cycle(self):
        """开始蟑螂任务"""
        pass
    
    def start_batch_eat_cycle(self):
        """开始吃白食"""
        pass
    
    def start_update_restaurant_ids(self):
        """更新餐厅ID"""
        pass
    
    def start_refresh_friends_cache(self):
        """刷新好友缓存"""
        pass
    
    def select_all_accounts(self):
        """全选账号"""
        pass
    
    def select_none_accounts(self):
        """清空选择"""
        pass
    
    def select_accounts_with_key(self):
        """选择有Key的账号"""
        pass
    
    def select_pending_accounts(self):
        """选择待购买的账号"""
        pass
    
    def cancel_operations(self):
        """取消操作"""
        pass
"""
特色菜管理页面
包括材料查询、残卷统计、神秘食谱鉴定等功能
"""
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QCheckBox, QProgressBar, QTextEdit, QMessageBox, QFrame,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QSizePolicy, QInputDialog, QDialog, QSpinBox, QButtonGroup,
    QRadioButton, QTabWidget, QTextBrowser, QFormLayout
)
from PySide6.QtGui import QFont, QPixmap, QPalette, QColor

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.depot import DepotAction
from src.delicious_town_bot.actions.specialty_food import SpecialtyFoodAction
from src.delicious_town_bot.actions.friend import FriendActions
from src.delicious_town_bot.actions.shop import ShopAction
from src.delicious_town_bot.data.specialty_food_packs import (
    get_all_recipe_names, get_pack_by_recipe_name, SPECIALTY_FOOD_PACKS
)


class DataLoadWorker(QObject):
    """数据加载工作线程"""
    
    # 信号定义
    materials_loaded = Signal(dict)  # 材料数据加载完成
    fragments_loaded = Signal(dict)  # 残卷数据加载完成
    loading_finished = Signal()     # 所有数据加载完成
    error_occurred = Signal(str)    # 错误发生
    
    def __init__(self, account_key: str, cookie: Dict[str, str]):
        super().__init__()
        self.account_key = account_key
        self.cookie = cookie
    
    @Slot()
    def load_data(self):
        """加载所有数据"""
        try:
            # 创建action实例
            depot_action = DepotAction(self.account_key, self.cookie)
            specialty_action = SpecialtyFoodAction(self.account_key, self.cookie)
            
            # 加载材料数据
            materials_count = specialty_action.get_appraisal_materials_count(depot_action)
            self.materials_loaded.emit(materials_count)
            
            # 加载残卷数据
            fragments_stats = specialty_action.get_fragments_count(depot_action)
            self.fragments_loaded.emit(fragments_stats)
            
            self.loading_finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"数据加载失败: {str(e)}")


class AppraisalWorker(QObject):
    """鉴定工作线程"""
    
    # 信号定义
    appraisal_completed = Signal(dict)  # 鉴定完成
    error_occurred = Signal(str)        # 错误发生
    
    def __init__(self, account_key: str, cookie: Dict[str, str], goods_code: str, num: int):
        super().__init__()
        self.account_key = account_key
        self.cookie = cookie
        self.goods_code = goods_code
        self.num = num
    
    @Slot()
    def do_appraisal(self):
        """执行鉴定"""
        try:
            specialty_action = SpecialtyFoodAction(self.account_key, self.cookie)
            result = specialty_action.appraise_cookbook(self.goods_code, self.num)
            self.appraisal_completed.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"鉴定失败: {str(e)}")


class FragmentOperationWorker(QObject):
    """残卷操作工作线程"""
    
    # 信号定义
    operation_completed = Signal(dict)  # 操作完成
    error_occurred = Signal(str)        # 错误发生
    
    def __init__(self, account_key: str, cookie: Dict[str, str], fragment_code: str, operation: str):
        super().__init__()
        self.account_key = account_key
        self.cookie = cookie
        self.fragment_code = fragment_code
        self.operation = operation  # 'learn' 或 'resolve'
    
    @Slot()
    def do_operation(self):
        """执行残卷操作"""
        try:
            specialty_action = SpecialtyFoodAction(self.account_key, self.cookie)
            
            if self.operation == 'learn':
                result = specialty_action.learn_fragment(self.fragment_code)
            elif self.operation == 'resolve':
                result = specialty_action.resolve_fragment(self.fragment_code)
            else:
                raise ValueError(f"未知操作: {self.operation}")
            
            self.operation_completed.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"残卷操作失败: {str(e)}")


class RecipeDataWorker(QObject):
    """已学特色菜数据加载工作线程"""
    
    # 信号定义
    recipes_loaded = Signal(dict)       # 特色菜列表加载完成
    recipe_info_loaded = Signal(dict)   # 特色菜详情加载完成
    error_occurred = Signal(str)        # 错误发生
    
    def __init__(self, account_key: str, cookie: Dict[str, str]):
        super().__init__()
        self.account_key = account_key
        self.cookie = cookie
    
    @Slot()
    def load_recipes(self):
        """加载已学特色菜列表"""
        try:
            specialty_action = SpecialtyFoodAction(self.account_key, self.cookie)
            result = specialty_action.get_learned_recipes(page=1)
            self.recipes_loaded.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"加载已学特色菜失败: {str(e)}")
    
    @Slot(str)
    def load_recipe_info(self, recipe_id: str):
        """加载特色菜详细信息"""
        try:
            specialty_action = SpecialtyFoodAction(self.account_key, self.cookie)
            result = specialty_action.get_recipe_info(recipe_id)
            self.recipe_info_loaded.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"加载特色菜详情失败: {str(e)}")


class RecipeCookingWorker(QObject):
    """特色菜烹饪工作线程"""
    
    # 信号定义
    cooking_completed = Signal(dict)    # 烹饪完成
    error_occurred = Signal(str)        # 错误发生
    
    def __init__(self, account_key: str, cookie: Dict[str, str], recipe_id: str, times: int):
        super().__init__()
        self.account_key = account_key
        self.cookie = cookie
        self.recipe_id = recipe_id
        self.times = times
    
    @Slot()
    def do_cooking(self):
        """执行特色菜烹饪"""
        try:
            specialty_action = SpecialtyFoodAction(self.account_key, self.cookie)
            result = specialty_action.cook_recipe(self.recipe_id, self.times)
            self.cooking_completed.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"特色菜烹饪失败: {str(e)}")


class SpecialtyFoodPage(QWidget):
    """特色菜管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.account_manager = AccountManager()
        self.current_account = None
        self.current_key = None
        self.current_cookie = None
        
        # 数据缓存
        self.materials_data = {}
        self.fragments_data = {}
        self.recipes_data = {}
        
        # 工作线程
        self.data_worker = None
        self.data_thread = None
        self.appraisal_worker = None
        self.appraisal_thread = None
        self.fragment_worker = None
        self.fragment_thread = None
        self.recipe_worker = None
        self.recipe_thread = None
        self.cooking_worker = None
        self.cooking_thread = None
        self.detail_worker = None
        self.detail_thread = None
        
        self.setupUI()
        self.refresh_accounts()
    
    def setupUI(self):
        """设置UI界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("🍽️ 特色菜管理")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 账户选择区域
        account_group = self.create_account_group()
        layout.addWidget(account_group)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 材料管理标签页
        materials_tab = self.create_materials_tab()
        self.tab_widget.addTab(materials_tab, "📦 材料管理")
        
        # 已学特色菜标签页
        recipes_tab = self.create_recipes_tab()
        self.tab_widget.addTab(recipes_tab, "🍽️ 已学特色菜")
        
        # 购买管理标签页
        purchase_tab = self.create_purchase_tab()
        self.tab_widget.addTab(purchase_tab, "🛒 购买管理")
        
        layout.addWidget(self.tab_widget)
        
        self.setLayout(layout)
        self.setWindowTitle("特色菜管理")
        self.resize(1000, 700)
    
    def create_account_group(self) -> QGroupBox:
        """创建账户选择组"""
        group = QGroupBox("账户选择")
        layout = QHBoxLayout()
        
        # 账户下拉框
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        self.account_combo.currentTextChanged.connect(self.on_account_changed)
        layout.addWidget(QLabel("选择账户:"))
        layout.addWidget(self.account_combo)
        
        # 刷新账户按钮
        refresh_btn = QPushButton("🔄 刷新账户")
        refresh_btn.clicked.connect(self.refresh_accounts)
        layout.addWidget(refresh_btn)
        
        # 加载材料数据按钮
        self.load_data_btn = QPushButton("📊 加载材料")
        self.load_data_btn.clicked.connect(self.load_data)
        self.load_data_btn.setEnabled(False)
        layout.addWidget(self.load_data_btn)
        
        # 加载特色菜按钮
        self.load_recipes_btn = QPushButton("🍽️ 加载特色菜")
        self.load_recipes_btn.clicked.connect(self.load_recipes)
        self.load_recipes_btn.setEnabled(False)
        layout.addWidget(self.load_recipes_btn)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def create_materials_tab(self) -> QWidget:
        """创建材料管理标签页"""
        widget = QWidget()
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：材料和残卷统计
        left_widget = self.create_statistics_widget()
        main_splitter.addWidget(left_widget)
        
        # 右侧：鉴定功能和日志
        right_widget = self.create_appraisal_widget()
        main_splitter.addWidget(right_widget)
        
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        
        layout = QVBoxLayout()
        layout.addWidget(main_splitter)
        widget.setLayout(layout)
        return widget
    
    def create_statistics_widget(self) -> QWidget:
        """创建统计信息区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 材料统计
        materials_group = QGroupBox("鉴定材料统计")
        materials_layout = QGridLayout()
        
        # 材料数量标签
        self.mysterious_recipe_label = QLabel("神秘食谱: 0")
        self.fairy_book_label = QLabel("小仙鉴定书: 0")
        self.chef_seal_label = QLabel("厨神玉玺: 0")
        
        materials_layout.addWidget(QLabel("📜"), 0, 0)
        materials_layout.addWidget(self.mysterious_recipe_label, 0, 1)
        materials_layout.addWidget(QLabel("📖"), 1, 0)
        materials_layout.addWidget(self.fairy_book_label, 1, 1)
        materials_layout.addWidget(QLabel("🎖️"), 2, 0)
        materials_layout.addWidget(self.chef_seal_label, 2, 1)
        
        materials_group.setLayout(materials_layout)
        layout.addWidget(materials_group)
        
        # 残卷统计
        fragments_group = QGroupBox("残卷统计")
        fragments_layout = QVBoxLayout()
        
        # 总数统计
        self.fragments_total_label = QLabel("总数: 0 种, 0 个")
        fragments_layout.addWidget(self.fragments_total_label)
        
        # 残卷详细列表
        self.fragments_table = QTableWidget()
        self.fragments_table.setColumnCount(4)
        self.fragments_table.setHorizontalHeaderLabels(["残卷名称", "数量", "学习", "分解"])
        self.fragments_table.horizontalHeader().setStretchLastSection(False)
        # 设置列宽
        self.fragments_table.setColumnWidth(0, 200)  # 残卷名称
        self.fragments_table.setColumnWidth(1, 60)   # 数量
        self.fragments_table.setColumnWidth(2, 60)   # 学习按钮
        self.fragments_table.setColumnWidth(3, 60)   # 分解按钮
        self.fragments_table.setAlternatingRowColors(True)
        self.fragments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        fragments_layout.addWidget(self.fragments_table)
        
        fragments_group.setLayout(fragments_layout)
        layout.addWidget(fragments_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_recipes_tab(self) -> QWidget:
        """创建已学特色菜标签页"""
        widget = QWidget()
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：特色菜列表
        left_widget = self.create_recipes_list_widget()
        main_splitter.addWidget(left_widget)
        
        # 右侧：特色菜详情和烹饪
        right_widget = self.create_recipe_details_widget()
        main_splitter.addWidget(right_widget)
        
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        
        layout = QVBoxLayout()
        layout.addWidget(main_splitter)
        widget.setLayout(layout)
        return widget
    
    def create_recipes_list_widget(self) -> QWidget:
        """创建特色菜列表组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 特色菜列表
        recipes_group = QGroupBox("已学特色菜列表")
        recipes_layout = QVBoxLayout()
        
        # 统计信息
        self.recipes_count_label = QLabel("已学特色菜: 0 道")
        recipes_layout.addWidget(self.recipes_count_label)
        
        # 特色菜表格
        self.recipes_table = QTableWidget()
        self.recipes_table.setColumnCount(5)
        self.recipes_table.setHorizontalHeaderLabels(["特色菜名称", "菜品等级", "熟练度", "经验值", "烹饪"])
        self.recipes_table.horizontalHeader().setStretchLastSection(False)
        # 设置列宽
        self.recipes_table.setColumnWidth(0, 180)  # 名称
        self.recipes_table.setColumnWidth(1, 70)   # 菜品等级
        self.recipes_table.setColumnWidth(2, 80)   # 熟练度
        self.recipes_table.setColumnWidth(3, 120)  # 经验值
        self.recipes_table.setColumnWidth(4, 60)   # 烹饪按钮
        self.recipes_table.setAlternatingRowColors(True)
        self.recipes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recipes_table.itemSelectionChanged.connect(self.on_recipe_selection_changed)
        recipes_layout.addWidget(self.recipes_table)
        
        recipes_group.setLayout(recipes_layout)
        layout.addWidget(recipes_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_recipe_details_widget(self) -> QWidget:
        """创建特色菜详情组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 特色菜详情
        details_group = QGroupBox("特色菜详情")
        details_layout = QVBoxLayout()
        
        # 基本信息
        info_layout = QFormLayout()
        self.recipe_name_label = QLabel("未选择")
        self.recipe_level_label = QLabel("未知")
        self.recipe_proficiency_label = QLabel("未知")
        self.recipe_exp_label = QLabel("0/0")
        self.recipe_description_label = QLabel("无描述")
        
        info_layout.addRow("特色菜名称:", self.recipe_name_label)
        info_layout.addRow("菜品等级:", self.recipe_level_label)
        info_layout.addRow("熟练度:", self.recipe_proficiency_label)
        info_layout.addRow("熟练度经验:", self.recipe_exp_label)
        info_layout.addRow("详情:", self.recipe_description_label)
        
        details_layout.addLayout(info_layout)
        
        # 食材需求
        ingredients_label = QLabel("所需食材:")
        details_layout.addWidget(ingredients_label)
        
        self.ingredients_text = QTextBrowser()
        self.ingredients_text.setMaximumHeight(150)
        details_layout.addWidget(self.ingredients_text)
        
        # 烹饪功能
        cooking_layout = QHBoxLayout()
        cooking_layout.addWidget(QLabel("烹饪倍数:"))
        
        self.cooking_times_combo = QComboBox()
        self.cooking_times_combo.addItems(["3", "5", "10", "50", "100"])
        self.cooking_times_combo.setCurrentText("3")
        cooking_layout.addWidget(self.cooking_times_combo)
        
        # 一键兑换按钮
        self.exchange_btn = QPushButton("🔄 一键兑换")
        self.exchange_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px 16px; }")
        self.exchange_btn.clicked.connect(self.start_exchange)
        self.exchange_btn.setEnabled(False)
        cooking_layout.addWidget(self.exchange_btn)
        
        self.cook_btn = QPushButton("🍳 开始烹饪")
        self.cook_btn.setStyleSheet("QPushButton { background-color: #ff6b35; color: white; font-weight: bold; padding: 8px 16px; }")
        self.cook_btn.clicked.connect(self.start_cooking)
        self.cook_btn.setEnabled(False)
        cooking_layout.addWidget(self.cook_btn)
        
        cooking_layout.addStretch()
        details_layout.addLayout(cooking_layout)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # 操作日志
        log_group = QGroupBox("烹饪日志")
        log_layout = QVBoxLayout()
        
        self.recipes_log_text = QTextEdit()
        self.recipes_log_text.setReadOnly(True)
        self.recipes_log_text.setMaximumHeight(200)
        log_layout.addWidget(self.recipes_log_text)
        
        # 清除日志按钮
        clear_log_btn = QPushButton("🗑️ 清除日志")
        clear_log_btn.clicked.connect(self.recipes_log_text.clear)
        log_layout.addWidget(clear_log_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_appraisal_widget(self) -> QWidget:
        """创建鉴定功能区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 鉴定功能
        appraisal_group = QGroupBox("神秘食谱鉴定")
        appraisal_layout = QVBoxLayout()
        
        # 道具选择
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("选择鉴定道具:"))
        
        # 道具选择按钮组
        self.tool_button_group = QButtonGroup()
        
        self.chef_seal_radio = QRadioButton("厨神玉玺 (1个)")
        self.chef_seal_radio.setChecked(True)
        self.tool_button_group.addButton(self.chef_seal_radio, 0)
        tool_layout.addWidget(self.chef_seal_radio)
        
        self.fairy_book_radio = QRadioButton("小仙鉴定书")
        self.tool_button_group.addButton(self.fairy_book_radio, 1)
        tool_layout.addWidget(self.fairy_book_radio)
        
        # 小仙鉴定书数量选择
        self.fairy_book_spinbox = QSpinBox()
        self.fairy_book_spinbox.setMinimum(1)
        self.fairy_book_spinbox.setMaximum(99)
        self.fairy_book_spinbox.setValue(1)
        self.fairy_book_spinbox.setEnabled(False)
        tool_layout.addWidget(self.fairy_book_spinbox)
        tool_layout.addWidget(QLabel("个"))
        
        # 连接信号
        self.fairy_book_radio.toggled.connect(self.on_tool_selection_changed)
        
        tool_layout.addStretch()
        appraisal_layout.addLayout(tool_layout)
        
        # 鉴定按钮
        appraisal_btn_layout = QHBoxLayout()
        self.appraisal_btn = QPushButton("🔮 开始鉴定")
        self.appraisal_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; padding: 8px 16px; }")
        self.appraisal_btn.clicked.connect(self.start_appraisal)
        self.appraisal_btn.setEnabled(False)
        appraisal_btn_layout.addWidget(self.appraisal_btn)
        appraisal_btn_layout.addStretch()
        appraisal_layout.addLayout(appraisal_btn_layout)
        
        appraisal_group.setLayout(appraisal_layout)
        layout.addWidget(appraisal_group)
        
        # 操作日志
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(300)
        log_layout.addWidget(self.log_text)
        
        # 清除日志按钮
        clear_btn = QPushButton("🗑️ 清除日志")
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        widget.setLayout(layout)
        return widget
    
    def refresh_accounts(self):
        """刷新账户列表"""
        try:
            accounts = self.account_manager.list_accounts()
            self.account_combo.clear()
            
            if not accounts:
                self.log_message("❌ 未找到任何账户")
                return
            
            for account in accounts:
                display_name = f"{account.username} ({account.restaurant or '未设置'})"
                self.account_combo.addItem(display_name, account)
            
            self.log_message(f"✅ 已加载 {len(accounts)} 个账户")
            
        except Exception as e:
            self.log_message(f"❌ 刷新账户失败: {str(e)}")
    
    def on_account_changed(self):
        """账户切换事件"""
        current_data = self.account_combo.currentData()
        if current_data:
            self.current_account = current_data
            self.current_key = current_data.key
            self.current_cookie = {"PHPSESSID": current_data.cookie} if current_data.cookie else {}
            self.load_data_btn.setEnabled(True)
            self.load_recipes_btn.setEnabled(True)
            self.log_message(f"✅ 已选择账户: {current_data.username}")
        else:
            self.load_data_btn.setEnabled(False)
            self.load_recipes_btn.setEnabled(False)
            self.appraisal_btn.setEnabled(False)
            if hasattr(self, 'cook_btn'):
                self.cook_btn.setEnabled(False)
            
            # 清理详情线程
            if hasattr(self, 'detail_thread') and self.detail_thread and self.detail_thread.isRunning():
                self.detail_thread.quit()
                self.detail_thread.wait()
                self.detail_thread = None
                self.detail_worker = None
    
    def load_data(self):
        """加载数据"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        # 禁用按钮
        self.load_data_btn.setEnabled(False)
        self.load_data_btn.setText("📊 加载中...")
        self.appraisal_btn.setEnabled(False)
        
        # 创建工作线程
        self.data_thread = QThread()
        self.data_worker = DataLoadWorker(self.current_key, self.current_cookie)
        self.data_worker.moveToThread(self.data_thread)
        
        # 连接信号
        self.data_thread.started.connect(self.data_worker.load_data)
        self.data_worker.materials_loaded.connect(self.update_materials_display)
        self.data_worker.fragments_loaded.connect(self.update_fragments_display)
        self.data_worker.loading_finished.connect(self.on_data_loading_finished)
        self.data_worker.error_occurred.connect(self.on_data_loading_error)
        
        # 启动线程
        self.data_thread.start()
        self.log_message("📊 开始加载数据...")
    
    @Slot(dict)
    def update_materials_display(self, materials_data: Dict[str, int]):
        """更新材料显示"""
        self.materials_data = materials_data
        
        self.mysterious_recipe_label.setText(f"神秘食谱: {materials_data.get('神秘食谱', 0)}")
        self.fairy_book_label.setText(f"小仙鉴定书: {materials_data.get('小仙鉴定书', 0)}")
        self.chef_seal_label.setText(f"厨神玉玺: {materials_data.get('厨神玉玺', 0)}")
        
        self.log_message(f"✅ 材料数据加载完成: {materials_data}")
    
    @Slot(dict)
    def update_fragments_display(self, fragments_data: Dict[str, Any]):
        """更新残卷显示"""
        self.fragments_data = fragments_data
        
        total_count = fragments_data.get("total_count", 0)
        total_num = fragments_data.get("total_num", 0)
        self.fragments_total_label.setText(f"总数: {total_count} 种, {total_num} 个")
        
        # 更新残卷表格
        fragments_list = fragments_data.get("fragments_list", [])
        self.fragments_table.setRowCount(len(fragments_list))
        
        for row, fragment in enumerate(fragments_list):
            fragment_name = fragment.get("name", "未知残卷")
            fragment_num = fragment.get("num", 0)
            fragment_code = fragment.get("raw_data", {}).get("goods_code", "")
            fragment_level = fragment.get("raw_data", {}).get("goods_level", "")
            
            # 在名称中添加等级信息
            if fragment_level:
                display_name = f"{fragment_name} ({fragment_level}级)"
            else:
                display_name = fragment_name
            
            # 名称和数量
            name_item = QTableWidgetItem(display_name)
            count_item = QTableWidgetItem(str(fragment_num))
            
            self.fragments_table.setItem(row, 0, name_item)
            self.fragments_table.setItem(row, 1, count_item)
            
            # 学习按钮
            learn_btn = QPushButton("学习")
            learn_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; padding: 4px 8px; }")
            learn_btn.clicked.connect(lambda checked, code=fragment_code, name=fragment_name: self.learn_fragment(code, name))
            self.fragments_table.setCellWidget(row, 2, learn_btn)
            
            # 分解按钮
            resolve_btn = QPushButton("分解")
            resolve_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; padding: 4px 8px; }")
            resolve_btn.clicked.connect(lambda checked, code=fragment_code, name=fragment_name: self.resolve_fragment(code, name))
            self.fragments_table.setCellWidget(row, 3, resolve_btn)
        
        self.log_message(f"✅ 残卷数据加载完成: {total_count} 种, {total_num} 个")
    
    @Slot()
    def on_data_loading_finished(self):
        """数据加载完成"""
        self.load_data_btn.setEnabled(True)
        self.load_data_btn.setText("📊 加载数据")
        
        # 检查是否有神秘食谱可以鉴定
        mysterious_count = self.materials_data.get("神秘食谱", 0)
        if mysterious_count > 0:
            self.appraisal_btn.setEnabled(True)
            self.log_message(f"✅ 数据加载完成，发现 {mysterious_count} 个神秘食谱可以鉴定")
        else:
            self.appraisal_btn.setEnabled(False)
            self.log_message("⚠️ 数据加载完成，但没有神秘食谱可以鉴定")
        
        # 清理线程
        if self.data_thread:
            self.data_thread.quit()
            self.data_thread.wait()
            self.data_thread = None
            self.data_worker = None
    
    @Slot(str)
    def on_data_loading_error(self, error_msg: str):
        """数据加载错误"""
        self.load_data_btn.setEnabled(True)
        self.load_data_btn.setText("📊 加载数据")
        self.log_message(f"❌ {error_msg}")
        
        # 清理线程
        if self.data_thread:
            self.data_thread.quit()
            self.data_thread.wait()
            self.data_thread = None
            self.data_worker = None
    
    def on_tool_selection_changed(self, checked: bool):
        """道具选择变更"""
        if checked:  # 小仙鉴定书被选中
            self.fairy_book_spinbox.setEnabled(True)
        else:  # 厨神玉玺被选中
            self.fairy_book_spinbox.setEnabled(False)
    
    def start_appraisal(self):
        """开始鉴定"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户并加载数据")
            return
        
        # 检查神秘食谱数量
        mysterious_count = self.materials_data.get("神秘食谱", 0)
        if mysterious_count <= 0:
            QMessageBox.warning(self, "提示", "没有神秘食谱可以鉴定")
            return
        
        # 获取选择的道具和数量
        if self.chef_seal_radio.isChecked():
            # 使用厨神玉玺
            goods_code = "20903"
            num = 1
            tool_name = "厨神玉玺"
            
            # 检查厨神玉玺数量
            chef_seal_count = self.materials_data.get("厨神玉玺", 0)
            if chef_seal_count <= 0:
                QMessageBox.warning(self, "提示", "没有厨神玉玺可以使用")
                return
        else:
            # 使用小仙鉴定书
            # 这里需要获取小仙鉴定书的goods_code，暂时使用占位符
            goods_code = "20902"  # 假设的小仙鉴定书代码，需要确认实际值
            num = self.fairy_book_spinbox.value()
            tool_name = f"小仙鉴定书 x{num}"
            
            # 检查小仙鉴定书数量
            fairy_book_count = self.materials_data.get("小仙鉴定书", 0)
            if fairy_book_count < num:
                QMessageBox.warning(self, "提示", f"小仙鉴定书数量不足，需要 {num} 个，现有 {fairy_book_count} 个")
                return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认鉴定",
            f"确定要使用 {tool_name} 鉴定神秘食谱吗？\\n\\n"
            f"📜 神秘食谱: {mysterious_count} 个\\n"
            f"🔮 鉴定道具: {tool_name}\\n\\n"
            f"⚠️ 注意：鉴定会消耗道具，请确认操作",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮
        self.appraisal_btn.setEnabled(False)
        self.appraisal_btn.setText("🔮 鉴定中...")
        
        # 创建鉴定工作线程
        self.appraisal_thread = QThread()
        self.appraisal_worker = AppraisalWorker(self.current_key, self.current_cookie, goods_code, num)
        self.appraisal_worker.moveToThread(self.appraisal_thread)
        
        # 连接信号
        self.appraisal_thread.started.connect(self.appraisal_worker.do_appraisal)
        self.appraisal_worker.appraisal_completed.connect(self.on_appraisal_completed)
        self.appraisal_worker.error_occurred.connect(self.on_appraisal_error)
        
        # 启动线程
        self.appraisal_thread.start()
        self.log_message(f"🔮 开始鉴定，使用 {tool_name}")
    
    @Slot(dict)
    def on_appraisal_completed(self, result: Dict[str, Any]):
        """鉴定完成"""
        self.appraisal_btn.setEnabled(True)
        self.appraisal_btn.setText("🔮 开始鉴定")
        
        success = result.get("success", False)
        message = result.get("message", "")
        data = result.get("data", [])
        
        if success:
            self.log_message(f"✅ 鉴定成功: {message}")
            if data:
                self.log_message(f"📝 鉴定结果: {data}")
        else:
            self.log_message(f"❌ 鉴定失败: {message}")
        
        # 清理线程
        if self.appraisal_thread:
            self.appraisal_thread.quit()
            self.appraisal_thread.wait()
            self.appraisal_thread = None
            self.appraisal_worker = None
        
        # 重新加载数据以更新数量
        QTimer.singleShot(1000, self.load_data)
    
    def load_recipes(self):
        """加载已学特色菜"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        # 禁用按钮
        self.load_recipes_btn.setEnabled(False)
        self.load_recipes_btn.setText("🍽️ 加载中...")
        
        # 创建工作线程
        self.recipe_thread = QThread()
        self.recipe_worker = RecipeDataWorker(self.current_key, self.current_cookie)
        self.recipe_worker.moveToThread(self.recipe_thread)
        
        # 连接信号
        self.recipe_thread.started.connect(self.recipe_worker.load_recipes)
        self.recipe_worker.recipes_loaded.connect(self.update_recipes_display)
        self.recipe_worker.error_occurred.connect(self.on_recipes_loading_error)
        
        # 启动线程
        self.recipe_thread.start()
        self.log_message("🍽️ 开始加载已学特色菜...")
    
    @Slot(dict)
    def update_recipes_display(self, recipes_data: Dict[str, Any]):
        """更新特色菜显示"""
        self.recipes_data = recipes_data
        
        success = recipes_data.get("success", False)
        if not success:
            self.log_message(f"❌ 加载特色菜失败: {recipes_data.get('message', '未知错误')}")
            self.load_recipes_btn.setEnabled(True)
            self.load_recipes_btn.setText("🍽️ 加载特色菜")
            return
        
        recipes_list = recipes_data.get("recipes", [])
        self.recipes_count_label.setText(f"已学特色菜: {len(recipes_list)} 道")
        
        # 更新特色菜表格
        self.recipes_table.setRowCount(len(recipes_list))
        
        # 获取熟练度等级配置
        level_exp_config = recipes_data.get("level_exp_config", [])
        level_name_config = recipes_data.get("level_name_config", [])
        
        for row, recipe in enumerate(recipes_list):
            # 根据实际API数据结构解析字段
            recipe_name = recipe.get("name", "未知特色菜")
            recipe_level = recipe.get("level", "未知")  # 特色菜等级
            recipe_exp = int(recipe.get("exp", 0)) if recipe.get("exp") else 0  # 熟练度经验
            proficiency_level = int(recipe.get("proficiency_level", 1)) if recipe.get("proficiency_level") else 1  # 当前熟练度等级
            # 使用cookbooks_id作为烹饪API的ID参数
            recipe_id = recipe.get("cookbooks_id", "") or recipe.get("id", "")
            
            # 根据熟练度等级获取所需经验值
            if level_exp_config and proficiency_level < len(level_exp_config):
                # 熟练度从0级开始，直接使用proficiency_level作为索引
                recipe_max_exp = level_exp_config[proficiency_level]
            else:
                recipe_max_exp = 10000  # 默认值
            
            # 获取熟练度等级名称
            proficiency_name = ""
            if level_name_config and proficiency_level < len(level_name_config):
                # 熟练度从0级开始，直接使用proficiency_level作为索引
                proficiency_name = level_name_config[proficiency_level]
            
            # 填充表格数据
            name_item = QTableWidgetItem(recipe_name)
            recipe_level_item = QTableWidgetItem(f"{recipe_level}级")
            proficiency_item = QTableWidgetItem(proficiency_name)
            exp_item = QTableWidgetItem(f"{recipe_exp}/{recipe_max_exp}")
            
            self.recipes_table.setItem(row, 0, name_item)
            self.recipes_table.setItem(row, 1, recipe_level_item)
            self.recipes_table.setItem(row, 2, proficiency_item)
            self.recipes_table.setItem(row, 3, exp_item)
            
            # 烹饪按钮
            cook_btn = QPushButton("烹饪")
            cook_btn.setStyleSheet("QPushButton { background-color: #ff6b35; color: white; padding: 4px 8px; }")
            cook_btn.clicked.connect(lambda checked, rid=recipe_id, name=recipe_name: self.quick_cook_recipe(rid, name))
            self.recipes_table.setCellWidget(row, 4, cook_btn)
        
        self.log_message(f"✅ 特色菜加载完成: {len(recipes_list)} 道")
        
        # 恢复按钮状态
        self.load_recipes_btn.setEnabled(True)
        self.load_recipes_btn.setText("🍽️ 加载特色菜")
        
        # 清理线程
        if self.recipe_thread:
            self.recipe_thread.quit()
            self.recipe_thread.wait()
            self.recipe_thread = None
            self.recipe_worker = None
    
    @Slot(str)
    def on_recipes_loading_error(self, error_msg: str):
        """特色菜加载错误"""
        self.load_recipes_btn.setEnabled(True)
        self.load_recipes_btn.setText("🍽️ 加载特色菜")
        self.log_message(f"❌ {error_msg}")
        
        # 清理线程
        if self.recipe_thread:
            self.recipe_thread.quit()
            self.recipe_thread.wait()
            self.recipe_thread = None
            self.recipe_worker = None
    
    def on_recipe_selection_changed(self):
        """特色菜选择变更"""
        current_row = self.recipes_table.currentRow()
        if current_row < 0:
            self.cook_btn.setEnabled(False)
            return
        
        # 获取选中的特色菜信息
        if self.recipes_data and self.recipes_data.get("recipes"):
            recipes_list = self.recipes_data["recipes"]
            if current_row < len(recipes_list):
                recipe = recipes_list[current_row]
                # 使用cookbooks_id作为详情查询的ID，而不是id
                recipe_id = recipe.get("cookbooks_id", "") or recipe.get("id", "")
                
                self.log_message(f"🔍 选中特色菜 - ID: {recipe.get('id')}, CookbooksID: {recipe.get('cookbooks_id')}, 使用ID: {recipe_id}")
                
                # 更新详情显示
                self.update_recipe_details(recipe)
                
                # 启用烹饪和兑换按钮
                self.cook_btn.setEnabled(True)
                self.exchange_btn.setEnabled(True)
                
                # 加载详细信息
                self.load_recipe_details(recipe_id)
    
    def update_recipe_details(self, recipe: Dict[str, Any]):
        """更新特色菜详情显示"""
        recipe_name = recipe.get("name", "未知特色菜")
        recipe_level = recipe.get("level", "未知")
        recipe_exp = int(recipe.get("exp", 0)) if recipe.get("exp") else 0
        proficiency_level = int(recipe.get("proficiency_level", 1)) if recipe.get("proficiency_level") else 1
        
        # 从缓存的配置获取熟练度信息
        level_exp_config = self.recipes_data.get("level_exp_config", [])
        level_name_config = self.recipes_data.get("level_name_config", [])
        
        # 获取熟练度等级所需经验值
        if level_exp_config and proficiency_level < len(level_exp_config):
            # 熟练度从0级开始，直接使用proficiency_level作为索引
            recipe_max_exp = level_exp_config[proficiency_level]
        else:
            recipe_max_exp = 10000
            
        # 获取熟练度等级名称
        proficiency_name = ""
        if level_name_config and proficiency_level < len(level_name_config):
            # 熟练度从0级开始，直接使用proficiency_level作为索引
            proficiency_name = level_name_config[proficiency_level]
        
        # 构造详情描述
        add_time = recipe.get("add_time", "")
        recipe_description = f"学习时间: {add_time}"
        
        self.recipe_name_label.setText(recipe_name)
        self.recipe_level_label.setText(f"{recipe_level}级")
        self.recipe_proficiency_label.setText(proficiency_name)
        self.recipe_exp_label.setText(f"{recipe_exp}/{recipe_max_exp}")
        self.recipe_description_label.setText(recipe_description)
        
        # 清空食材显示
        self.ingredients_text.clear()
        self.ingredients_text.append("正在加载详细信息...")
    
    def load_recipe_details(self, recipe_id: str):
        """加载特色菜详细信息"""
        if not self.current_key or not self.current_cookie or not recipe_id:
            return
        
        # 清理之前的线程
        if self.detail_thread and self.detail_thread.isRunning():
            self.detail_thread.quit()
            self.detail_thread.wait()
            self.detail_thread = None
            self.detail_worker = None
        
        # 创建工作线程获取详细信息
        self.detail_thread = QThread()
        self.detail_worker = RecipeDataWorker(self.current_key, self.current_cookie)
        self.detail_worker.moveToThread(self.detail_thread)
        
        # 连接信号
        self.detail_thread.started.connect(lambda: self.detail_worker.load_recipe_info(recipe_id))
        self.detail_worker.recipe_info_loaded.connect(self.update_recipe_ingredients)
        self.detail_worker.error_occurred.connect(self.on_detail_loading_error)
        
        # 启动线程
        self.detail_thread.start()
    
    @Slot(dict)
    def update_recipe_ingredients(self, recipe_info: Dict[str, Any]):
        """更新食材需求显示"""
        # 先调试输出完整的API响应
        import json
        self.log_message(f"🔍 食材详情API响应: {json.dumps(recipe_info, ensure_ascii=False)}")
        
        success = recipe_info.get("success", False)
        if not success:
            self.ingredients_text.setText(f"加载失败: {recipe_info.get('message', '未知错误')}")
            return
        
        # 从API响应中获取食材信息，尝试多种可能的路径
        food_list = recipe_info.get("ingredients", [])
        if not food_list:
            # 尝试从data字段获取
            data = recipe_info.get("data", {})
            food_list = data.get("food", [])
        if not food_list:
            self.ingredients_text.setText("无食材需求信息")
            return
        
        # 缓存食材信息供兑换功能使用
        self.current_recipe_foods = food_list
        
        # 格式化食材信息HTML
        ingredients_html = "<h4>所需食材:</h4>"
        ingredients_html += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
        ingredients_html += "<tr style='background-color: #f0f0f0;'>"
        ingredients_html += "<th>食材名称</th><th>等级</th><th>拥有数量</th></tr>"
        
        for food in food_list:
            name = food.get("name", "未知食材")
            owned_num = int(food.get("num", 0))
            food_level = food.get("food_level", "未知")
            
            # 根据拥有数量设置颜色（基于3倍需求）
            if owned_num >= 10:
                row_color = "#d4edda"  # 绿色 - 充足
            elif owned_num >= 3:
                row_color = "#fff3cd"  # 黄色 - 部分满足  
            else:
                row_color = "#f8d7da"  # 红色 - 不足
            
            ingredients_html += f"<tr style='background-color: {row_color};'>"
            ingredients_html += f"<td><strong>{name}</strong></td>"
            ingredients_html += f"<td>{food_level}级</td>"
            ingredients_html += f"<td><strong>{owned_num}</strong></td>"
            ingredients_html += "</tr>"
        
        ingredients_html += "</table>"
        ingredients_html += "<p style='margin-top: 10px; font-size: 12px; color: #666;'>"
        ingredients_html += "🟢 充足 (≥10个) | 🟡 部分满足 (≥3个) | 🔴 不足 (<3个)"
        ingredients_html += "</p>"
        
        self.ingredients_text.setHtml(ingredients_html)
        
        # 清理详情线程
        if self.detail_thread:
            self.detail_thread.quit()
            self.detail_thread.wait()
            self.detail_thread = None
            self.detail_worker = None
    
    def on_detail_loading_error(self, error_msg: str):
        """详情加载错误"""
        self.ingredients_text.setText(f"加载失败: {error_msg}")
        
        # 清理详情线程
        if self.detail_thread:
            self.detail_thread.quit()
            self.detail_thread.wait()
            self.detail_thread = None
            self.detail_worker = None
    
    def quick_cook_recipe(self, recipe_id: str, recipe_name: str):
        """快速烹饪特色菜（使用默认倍数）"""
        if not recipe_id:
            return
        
        # 使用默认倍数3进行烹饪
        self.start_cooking_with_params(recipe_id, recipe_name, 3)
    
    def start_cooking(self):
        """开始烹饪（从详情面板）"""
        current_row = self.recipes_table.currentRow()
        if current_row < 0 or not self.recipes_data or not self.recipes_data.get("recipes"):
            QMessageBox.warning(self, "提示", "请先选择要烹饪的特色菜")
            return
        
        recipes_list = self.recipes_data["recipes"]
        if current_row >= len(recipes_list):
            return
        
        recipe = recipes_list[current_row]
        recipe_id = recipe.get("id", "")
        recipe_name = recipe.get("name", "未知特色菜")
        times = int(self.cooking_times_combo.currentText())
        
        self.start_cooking_with_params(recipe_id, recipe_name, times)
    
    def start_cooking_with_params(self, recipe_id: str, recipe_name: str, times: int):
        """使用指定参数开始烹饪"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认烹饪",
            f"确定要烹饪特色菜'{recipe_name}' x{times} 倍吗？\n\n"
            f"🍽️ 特色菜: {recipe_name}\n"
            f"📊 烹饪倍数: {times}\n\n"
            f"⚠️ 注意：烹饪会消耗相应的食材",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用烹饪按钮
        self.cook_btn.setEnabled(False)
        self.cook_btn.setText("🍳 烹饪中...")
        
        # 创建烹饪工作线程
        self.cooking_thread = QThread()
        self.cooking_worker = RecipeCookingWorker(self.current_key, self.current_cookie, recipe_id, times)
        self.cooking_worker.moveToThread(self.cooking_thread)
        
        # 连接信号
        self.cooking_thread.started.connect(self.cooking_worker.do_cooking)
        self.cooking_worker.cooking_completed.connect(self.on_cooking_completed)
        self.cooking_worker.error_occurred.connect(self.on_cooking_error)
        
        # 启动线程
        self.cooking_thread.start()
        self.recipes_log_message(f"🍳 开始烹饪: {recipe_name} x{times}")
    
    @Slot(dict)
    def on_cooking_completed(self, result: Dict[str, Any]):
        """烹饪完成"""
        self.cook_btn.setEnabled(True)
        self.cook_btn.setText("🍳 开始烹饪")
        
        success = result.get("success", False)
        message = result.get("message", "")
        data = result.get("data", [])
        
        if success:
            self.recipes_log_message(f"✅ 烹饪成功: {message}")
            if data:
                self.recipes_log_message(f"📝 烹饪结果: {data}")
        else:
            self.recipes_log_message(f"❌ 烹饪失败: {message}")
        
        # 清理线程
        if self.cooking_thread:
            self.cooking_thread.quit()
            self.cooking_thread.wait()
            self.cooking_thread = None
            self.cooking_worker = None
    
    @Slot(str)
    def on_cooking_error(self, error_msg: str):
        """烹饪错误"""
        self.cook_btn.setEnabled(True)
        self.cook_btn.setText("🍳 开始烹饪")
        self.recipes_log_message(f"❌ {error_msg}")
        
        # 清理线程
        if self.cooking_thread:
            self.cooking_thread.quit()
            self.cooking_thread.wait()
            self.cooking_thread = None
            self.cooking_worker = None
    
    def start_exchange(self):
        """开始一键兑换食材"""
        if not self.current_recipe_foods:
            QMessageBox.warning(self, "提示", "请先选择特色菜并加载食材需求信息")
            return
        
        # 获取选择的烹饪倍数
        times = int(self.cooking_times_combo.currentText())
        
        # 计算需要兑换的食材
        exchange_items = []
        insufficient_items = []
        
        for food in self.current_recipe_foods:
            name = food.get("name", "未知食材")
            owned_num = int(food.get("num", 0))
            required_num = times  # 每种食材需要倍数个
            
            if owned_num < required_num:
                shortage = required_num - owned_num
                exchange_items.append({
                    "name": name,
                    "food_code": food.get("food_code", ""),
                    "food_level": food.get("food_level", ""),
                    "owned": owned_num,
                    "required": required_num,
                    "shortage": shortage
                })
        
        if not exchange_items:
            QMessageBox.information(
                self, "兑换检查", 
                f"🎉 恭喜！您已有足够的食材进行 {times} 倍烹饪，无需兑换。"
            )
            return
        
        # 显示兑换确认对话框
        exchange_info = "以下食材不足，需要兑换：\n\n"
        for item in exchange_items:
            exchange_info += f"• {item['name']} ({item['food_level']}级): 拥有 {item['owned']} 个，需要 {item['required']} 个，缺少 {item['shortage']} 个\n"
        
        exchange_info += f"\n⚠️ 注意：这是前端预览功能，后端兑换功能尚未实现"
        
        reply = QMessageBox.question(
            self, "确认兑换食材",
            exchange_info,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 这里是前端实现，显示兑换模拟
            self.simulate_exchange(exchange_items, times)
    
    def simulate_exchange(self, exchange_items: list, times: int):
        """模拟兑换过程（前端实现）"""
        self.exchange_btn.setEnabled(False)
        self.exchange_btn.setText("🔄 兑换中...")
        
        # 模拟兑换日志
        self.recipes_log_message(f"🔄 开始一键兑换食材 (烹饪倍数: {times})")
        
        for item in exchange_items:
            self.recipes_log_message(f"📦 兑换 {item['name']} x{item['shortage']} (等级: {item['food_level']})")
        
        # 模拟完成
        import time
        from PySide6.QtCore import QTimer
        
        def finish_exchange():
            self.exchange_btn.setEnabled(True)
            self.exchange_btn.setText("🔄 一键兑换")
            self.recipes_log_message(f"✅ 兑换完成！已获得所需食材，可以进行 {times} 倍烹饪")
            self.recipes_log_message(f"⚠️ 注意：这是前端模拟，实际兑换需要后端API实现")
        
        # 延迟1.5秒模拟网络请求
        QTimer.singleShot(1500, finish_exchange)
    
    def recipes_log_message(self, message: str):
        """添加烹饪日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.recipes_log_text.append(formatted_message)
        
        # 自动滚动到底部
        from PySide6.QtGui import QTextCursor
        cursor = self.recipes_log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.recipes_log_text.setTextCursor(cursor)
    
    @Slot(str)
    def on_appraisal_error(self, error_msg: str):
        """鉴定错误"""
        self.appraisal_btn.setEnabled(True)
        self.appraisal_btn.setText("🔮 开始鉴定")
        self.log_message(f"❌ {error_msg}")
        
        # 清理线程
        if self.appraisal_thread:
            self.appraisal_thread.quit()
            self.appraisal_thread.wait()
            self.appraisal_thread = None
            self.appraisal_worker = None
    
    def log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        
        # 自动滚动到底部
        from PySide6.QtGui import QTextCursor
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def learn_fragment(self, fragment_code: str, fragment_name: str):
        """学习残卷"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户并加载数据")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认学习残卷",
            f"确定要学习残卷'{fragment_name}'吗？\n\n"
            f"⚠️ 注意：\n"
            f"• 学习后残卷将被消耗\n"
            f"• 需要相应的餐厅星级才能学习\n"
            f"• 学习失败时残卷仍会被消耗",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 创建残卷操作工作线程
        self.fragment_thread = QThread()
        self.fragment_worker = FragmentOperationWorker(self.current_key, self.current_cookie, fragment_code, 'learn')
        self.fragment_worker.moveToThread(self.fragment_thread)
        
        # 连接信号
        self.fragment_thread.started.connect(self.fragment_worker.do_operation)
        self.fragment_worker.operation_completed.connect(self.on_fragment_operation_completed)
        self.fragment_worker.error_occurred.connect(self.on_fragment_operation_error)
        
        # 启动线程
        self.fragment_thread.start()
        self.log_message(f"📚 开始学习残卷: {fragment_name}")
    
    def resolve_fragment(self, fragment_code: str, fragment_name: str):
        """分解残卷"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户并加载数据")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认分解残卷",
            f"确定要分解残卷'{fragment_name}'吗？\n\n"
            f"⚠️ 注意：\n"
            f"• 分解后残卷将被消耗\n"
            f"• 可能获得其他材料奖励\n"
            f"• 分解操作不可撤销",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 创建残卷操作工作线程
        self.fragment_thread = QThread()
        self.fragment_worker = FragmentOperationWorker(self.current_key, self.current_cookie, fragment_code, 'resolve')
        self.fragment_worker.moveToThread(self.fragment_thread)
        
        # 连接信号
        self.fragment_thread.started.connect(self.fragment_worker.do_operation)
        self.fragment_worker.operation_completed.connect(self.on_fragment_operation_completed)
        self.fragment_worker.error_occurred.connect(self.on_fragment_operation_error)
        
        # 启动线程
        self.fragment_thread.start()
        self.log_message(f"🔧 开始分解残卷: {fragment_name}")
    
    @Slot(dict)
    def on_fragment_operation_completed(self, result: Dict[str, Any]):
        """残卷操作完成"""
        success = result.get("success", False)
        message = result.get("message", "")
        data = result.get("data", [])
        
        if success:
            self.log_message(f"✅ 残卷操作成功: {message}")
            if data:
                self.log_message(f"📝 操作结果: {data}")
        else:
            self.log_message(f"❌ 残卷操作失败: {message}")
        
        # 清理线程
        if self.fragment_thread:
            self.fragment_thread.quit()
            self.fragment_thread.wait()
            self.fragment_thread = None
            self.fragment_worker = None
        
        # 重新加载数据以更新残卷列表
        QTimer.singleShot(1000, self.load_data)
    
    @Slot(str)
    def on_fragment_operation_error(self, error_msg: str):
        """残卷操作错误"""
        self.log_message(f"❌ {error_msg}")
        
        # 清理线程
        if self.fragment_thread:
            self.fragment_thread.quit()
            self.fragment_thread.wait()
            self.fragment_thread = None
            self.fragment_worker = None
    
    def _create_friend_exchange_panel(self) -> QWidget:
        """创建好友兑换面板"""
        friend_exchange_group = QGroupBox("好友食材兑换")
        main_layout = QVBoxLayout(friend_exchange_group)
        
        # 第一行：目标食材选择
        target_layout = QHBoxLayout()
        
        target_layout.addWidget(QLabel("想要获得:"))
        
        # 食材等级选择
        self.friend_target_level_combo = QComboBox()
        self.friend_target_level_combo.addItem("1级食材", 1)
        self.friend_target_level_combo.addItem("2级食材", 2)
        self.friend_target_level_combo.addItem("3级食材", 3)
        self.friend_target_level_combo.addItem("4级食材", 4)
        self.friend_target_level_combo.addItem("5级食材", 5)
        self.friend_target_level_combo.currentTextChanged.connect(self._update_target_food_list)
        self.friend_target_level_combo.currentTextChanged.connect(self._update_offer_food_by_level)
        target_layout.addWidget(self.friend_target_level_combo)
        
        # 具体食材选择
        self.friend_target_food_combo = QComboBox()
        self.friend_target_food_combo.setMinimumWidth(120)
        target_layout.addWidget(self.friend_target_food_combo)
        
        # 兑换数量
        target_layout.addWidget(QLabel("数量:"))
        self.friend_exchange_quantity = QSpinBox()
        self.friend_exchange_quantity.setMinimum(1)
        self.friend_exchange_quantity.setMaximum(50)
        self.friend_exchange_quantity.setValue(5)
        target_layout.addWidget(self.friend_exchange_quantity)
        
        target_layout.addStretch()
        main_layout.addLayout(target_layout)
        
        # 第二行：给出食材选择
        offer_layout = QHBoxLayout()
        
        offer_layout.addWidget(QLabel("愿意给出:"))
        
        # 手动选择给出食材
        self.friend_offer_food_combo = QComboBox()
        self.friend_offer_food_combo.setMinimumWidth(120)
        offer_layout.addWidget(self.friend_offer_food_combo)
        
        offer_layout.addWidget(QLabel("好友范围:"))
        self.friend_range_combo = QComboBox()
        self.friend_range_combo.addItem("所有好友", "all")
        self.friend_range_combo.addItem("优选好友", "preferred")
        offer_layout.addWidget(self.friend_range_combo)
        
        offer_layout.addStretch()
        main_layout.addLayout(offer_layout)
        
        # 第三行：控制按钮
        control_layout = QHBoxLayout()
        
        # 查找好友按钮
        self.find_friends_btn = QPushButton("🔍 查找好友")
        self.find_friends_btn.clicked.connect(self._find_friends_with_target_food)
        control_layout.addWidget(self.find_friends_btn)
        
        # 好友数量显示
        self.friends_count_label = QLabel("好友: 未选择")
        control_layout.addWidget(self.friends_count_label)
        
        # 开始兑换按钮
        self.friend_exchange_btn = QPushButton("开始好友兑换")
        self.friend_exchange_btn.clicked.connect(self._start_friend_exchange)
        self.friend_exchange_btn.setEnabled(False)
        control_layout.addWidget(self.friend_exchange_btn)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        return friend_exchange_group
    
    def _create_specialty_pack_panel(self) -> QWidget:
        """创建特色菜食材礼包购买面板"""
        pack_group = QGroupBox("特色菜食材礼包购买")
        main_layout = QVBoxLayout(pack_group)
        
        # 说明文本
        info_text = QLabel("一键购买并打开特色菜食材礼包（每种食材3个）")
        info_text.setStyleSheet("QLabel { color: #666666; font-style: italic; }")
        main_layout.addWidget(info_text)
        
        # 礼包选择和购买
        pack_layout = QHBoxLayout()
        
        # 特色菜选择
        pack_layout.addWidget(QLabel("特色菜:"))
        self.specialty_pack_combo = QComboBox()
        self.specialty_pack_combo.setMinimumWidth(150)
        self.specialty_pack_combo.currentTextChanged.connect(self._update_pack_info)
        pack_layout.addWidget(self.specialty_pack_combo)
        
        # 礼包信息显示
        self.pack_info_label = QLabel("请选择特色菜")
        self.pack_info_label.setMinimumWidth(200)
        self.pack_info_label.setStyleSheet("QLabel { color: #0066cc; }")
        pack_layout.addWidget(self.pack_info_label)
        
        # 购买按钮
        self.buy_pack_btn = QPushButton("💰 购买并打开")
        self.buy_pack_btn.clicked.connect(self._buy_specialty_pack)
        self.buy_pack_btn.setEnabled(False)
        pack_layout.addWidget(self.buy_pack_btn)
        
        # 批量购买按钮
        self.buy_all_packs_btn = QPushButton("🛒 购买全部礼包")
        self.buy_all_packs_btn.clicked.connect(self._buy_all_specialty_packs)
        pack_layout.addWidget(self.buy_all_packs_btn)
        
        pack_layout.addStretch()
        main_layout.addLayout(pack_layout)
        
        # 批量账号操作区域
        batch_account_layout = QVBoxLayout()
        batch_account_layout.addWidget(QLabel("批量账号操作:"))
        
        batch_buttons_layout = QHBoxLayout()
        
        # 批量账号购买按钮
        self.batch_account_buy_btn = QPushButton("🏢 批量账号购买礼包")
        self.batch_account_buy_btn.clicked.connect(self._batch_account_buy_packs)
        batch_buttons_layout.addWidget(self.batch_account_buy_btn)
        
        # 批量账号烹饪按钮  
        self.batch_account_cook_btn = QPushButton("👨‍🍳 批量账号烹饪特色菜")
        self.batch_account_cook_btn.clicked.connect(self._batch_account_cook_specialty)
        batch_buttons_layout.addWidget(self.batch_account_cook_btn)
        
        batch_buttons_layout.addStretch()
        batch_account_layout.addLayout(batch_buttons_layout)
        
        # 批量操作说明
        batch_info_label = QLabel("批量操作将对所有已登录账号执行相同操作")
        batch_info_label.setStyleSheet("QLabel { color: #666666; font-style: italic; }")
        batch_account_layout.addWidget(batch_info_label)
        
        main_layout.addLayout(batch_account_layout)
        
        return pack_group
    
    def create_purchase_tab(self) -> QWidget:
        """创建购买管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 好友食材兑换面板
        friend_exchange_panel = self._create_friend_exchange_panel()
        layout.addWidget(friend_exchange_panel)
        
        # 特色菜礼包购买面板
        specialty_pack_panel = self._create_specialty_pack_panel()
        layout.addWidget(specialty_pack_panel)
        
        # 操作日志
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.purchase_log_text = QTextEdit()
        self.purchase_log_text.setReadOnly(True)
        self.purchase_log_text.setMaximumHeight(150)
        self.purchase_log_text.setStyleSheet("QTextEdit { background-color: #f8f9fa; }")
        log_layout.addWidget(self.purchase_log_text)
        
        layout.addWidget(log_group)
        
        # 初始化食材选择器
        self._initialize_food_selectors()
        
        return widget
    
    def _initialize_food_selectors(self):
        """初始化食材选择器"""
        try:
            self._update_target_food_list()
            self._update_offer_food_by_level()
            self._populate_specialty_packs()
        except Exception as e:
            print(f"[Error] 初始化食材选择器失败: {e}")
    
    def _get_foods_by_level(self, target_level: int) -> Dict[str, str]:
        """获取指定等级的食材列表"""
        import json
        import os
        
        try:
            # 读取foods.json文件
            foods_path = os.path.join(os.path.dirname(__file__), "../../assets/foods.json")
            with open(foods_path, 'r', encoding='utf-8') as f:
                foods_json = json.load(f)
            
            # 获取foods数据
            foods_data = foods_json.get("RECORDS", []) if isinstance(foods_json, dict) else foods_json
            
            # 过滤指定等级的食材
            level_foods = {}
            for food in foods_data:
                try:
                    food_level = int(food.get('level', 0))
                    if food_level == target_level:
                        food_code = food.get('code', '')
                        food_name = food.get('name', food_code)
                        if food_code and food_name:
                            level_foods[food_code] = food_name
                except (ValueError, TypeError):
                    continue
            
            return level_foods
        except Exception as e:
            print(f"[Error] 读取食材数据失败: {e}")
            return {}
    
    def _update_target_food_list(self):
        """更新目标食材列表"""
        level = self.friend_target_level_combo.currentData()
        if not level:
            return
        
        self.friend_target_food_combo.clear()
        
        try:
            foods_by_level = self._get_foods_by_level(level)
            
            for food_code, food_name in foods_by_level.items():
                self.friend_target_food_combo.addItem(food_name, food_code)
        except Exception as e:
            print(f"[Error] 更新目标食材列表失败: {e}")
    
    def _update_offer_food_by_level(self):
        """更新给出食材列表"""
        level = self.friend_target_level_combo.currentData()
        if not level:
            return
        
        self.friend_offer_food_combo.clear()
        
        try:
            foods_by_level = self._get_foods_by_level(level)
            
            for food_code, food_name in foods_by_level.items():
                self.friend_offer_food_combo.addItem(food_name, food_code)
        except Exception as e:
            print(f"[Error] 更新给出食材列表失败: {e}")
    
    def _populate_specialty_packs(self):
        """填充特色菜礼包选择"""
        self.specialty_pack_combo.clear()
        self.specialty_pack_combo.addItem("请选择特色菜", None)
        
        try:
            recipe_names = get_all_recipe_names()
            for recipe_name in recipe_names:
                pack = get_pack_by_recipe_name(recipe_name)
                if pack:
                    display_text = f"{pack.icon} {recipe_name} ({pack.price}金币)"
                    self.specialty_pack_combo.addItem(display_text, recipe_name)
        except Exception as e:
            print(f"[Error] 加载特色菜礼包失败: {e}")
            self.specialty_pack_combo.addItem("加载失败", None)
    
    def _update_pack_info(self):
        """更新礼包信息显示"""
        recipe_name = self.specialty_pack_combo.currentData()
        if not recipe_name:
            self.pack_info_label.setText("请选择特色菜")
            self.buy_pack_btn.setEnabled(False)
            return
        
        try:
            pack = get_pack_by_recipe_name(recipe_name)
            if pack:
                ingredients_text = "、".join(pack.ingredients)
                info_text = f"包含: {ingredients_text} (各3个)"
                self.pack_info_label.setText(info_text)
                self.buy_pack_btn.setEnabled(True)
            else:
                self.pack_info_label.setText("礼包信息获取失败")
                self.buy_pack_btn.setEnabled(False)
        except Exception as e:
            print(f"[Error] 更新礼包信息失败: {e}")
            self.pack_info_label.setText("信息获取失败")
            self.buy_pack_btn.setEnabled(False)
    
    def _find_friends_with_target_food(self):
        """查找拥有目标食材的好友"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        target_food_code = self.friend_target_food_combo.currentData()
        target_food_name = self.friend_target_food_combo.currentText()
        target_level = self.friend_target_level_combo.currentData()
        
        if not target_food_code:
            QMessageBox.warning(self, "提示", "请选择目标食材")
            return
        
        try:
            friend_actions = FriendActions(self.current_key, self.current_cookie)
            friends_info = friend_actions.find_friends_with_food(target_food_code, str(target_level))
            
            if friends_info.get("success"):
                friends_list = friends_info.get("friends", [])
                if friends_list:
                    self.friends_count_label.setText(f"好友: 找到 {len(friends_list)} 个拥有{target_food_name}的好友")
                    self.friend_exchange_btn.setEnabled(True)
                    self.found_friends = friends_list
                    
                    # 在日志中显示好友信息
                    self.purchase_log_text.append(f"✅ 找到 {len(friends_list)} 个拥有{target_food_name}的好友:")
                    for friend in friends_list[:5]:  # 只显示前5个
                        friend_name = friend.get("name", "未知")
                        food_count = friend.get("food_count", 0)
                        self.purchase_log_text.append(f"   • {friend_name}: {food_count}个")
                    if len(friends_list) > 5:
                        self.purchase_log_text.append(f"   ... 还有{len(friends_list)-5}个好友")
                else:
                    self.friends_count_label.setText("好友: 未找到")
                    self.friend_exchange_btn.setEnabled(False)
                    self.found_friends = []
                    self.purchase_log_text.append(f"❌ 未找到拥有{target_food_name}的好友")
            else:
                error_msg = friends_info.get("message", "查找失败")
                self.purchase_log_text.append(f"❌ 查找好友失败: {error_msg}")
                self.friends_count_label.setText("好友: 查找失败")
                self.friend_exchange_btn.setEnabled(False)
        except Exception as e:
            self.purchase_log_text.append(f"❌ 查找好友出错: {e}")
            self.friends_count_label.setText("好友: 查找出错")
            self.friend_exchange_btn.setEnabled(False)
    
    def _start_friend_exchange(self):
        """开始好友兑换"""
        if not hasattr(self, 'found_friends') or not self.found_friends:
            QMessageBox.warning(self, "提示", "请先查找好友")
            return
        
        target_food_code = self.friend_target_food_combo.currentData()
        target_food_name = self.friend_target_food_combo.currentText()
        offer_food_code = self.friend_offer_food_combo.currentData()
        offer_food_name = self.friend_offer_food_combo.currentText()
        exchange_quantity = self.friend_exchange_quantity.value()
        
        if not offer_food_code:
            QMessageBox.warning(self, "提示", "请选择给出的食材")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认兑换",
            f"确认进行好友兑换？\n\n"
            f"目标: 获得 {exchange_quantity} 个 {target_food_name}\n"
            f"代价: 给出 {exchange_quantity*2} 个 {offer_food_name}\n"
            f"好友: {len(self.found_friends)} 个可用好友",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始兑换
        self.friend_exchange_btn.setEnabled(False)
        self.purchase_log_text.append(f"🔄 开始兑换: {target_food_name} x{exchange_quantity}")
        
        try:
            friend_actions = FriendActions(self.current_key, self.current_cookie)
            success_count = 0
            
            for i in range(min(exchange_quantity, len(self.found_friends))):
                friend_info = self.found_friends[i]
                friend_id = friend_info.get("friend_id")
                friend_name = friend_info.get("name", "未知")
                
                try:
                    result = friend_actions.direct_friend_exchange(
                        friend_id, target_food_code, offer_food_code
                    )
                    
                    if result.get("success"):
                        success_count += 1
                        self.purchase_log_text.append(f"   ✅ 与{friend_name}兑换成功")
                    else:
                        error_msg = result.get("message", "兑换失败")
                        self.purchase_log_text.append(f"   ❌ 与{friend_name}兑换失败: {error_msg}")
                    
                    # 间隔避免请求过快
                    import time
                    time.sleep(1)
                    
                except Exception as e:
                    self.purchase_log_text.append(f"   ❌ 与{friend_name}兑换出错: {e}")
            
            self.purchase_log_text.append(f"🎉 兑换完成! 成功 {success_count}/{exchange_quantity} 次")
            
        except Exception as e:
            self.purchase_log_text.append(f"❌ 兑换过程出错: {e}")
        finally:
            self.friend_exchange_btn.setEnabled(True)
    
    def _buy_specialty_pack(self):
        """购买单个特色菜食材礼包"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        recipe_name = self.specialty_pack_combo.currentData()
        if not recipe_name:
            return
        
        # 确认对话框
        pack = get_pack_by_recipe_name(recipe_name)
        if not pack:
            return
        
        reply = QMessageBox.question(
            self, "确认购买",
            f"确认购买 {pack.icon} {recipe_name} 食材礼包？\n\n"
            f"价格: {pack.price} 金币\n"
            f"包含: {', '.join(pack.ingredients)} (各3个)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始购买
        self.buy_pack_btn.setEnabled(False)
        self.purchase_log_text.append(f"🛒 开始购买 {recipe_name} 食材礼包...")
        
        try:
            shop_action = ShopAction(self.current_key, self.current_cookie)
            result = shop_action.buy_and_open_specialty_pack(recipe_name)
            
            if result.get("success"):
                ingredients = result.get("total_ingredients", [])
                ingredients_text = ", ".join([f"{ing['name']}x{ing['count']}" for ing in ingredients])
                self.purchase_log_text.append(f"✅ {recipe_name}: 购买成功")
                if ingredients_text:
                    self.purchase_log_text.append(f"   获得: {ingredients_text}")
            else:
                error_msg = result.get("message", "购买失败")
                self.purchase_log_text.append(f"❌ {recipe_name}: {error_msg}")
        except Exception as e:
            self.purchase_log_text.append(f"❌ 购买出错: {e}")
        finally:
            self.buy_pack_btn.setEnabled(True)
    
    def _buy_all_specialty_packs(self):
        """购买全部特色菜食材礼包"""
        if not self.current_key or not self.current_cookie:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        recipe_names = get_all_recipe_names()
        if not recipe_names:
            QMessageBox.warning(self, "提示", "没有可用的特色菜礼包")
            return
        
        # 计算总价格
        total_cost = 0
        pack_details = []
        for recipe_name in recipe_names:
            pack = get_pack_by_recipe_name(recipe_name)
            if pack:
                total_cost += pack.price
                pack_details.append(f"{pack.icon} {recipe_name}({pack.price}金币)")
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量购买",
            f"确认购买全部特色菜食材礼包？\n\n"
            f"礼包数量: {len(recipe_names)} 个\n"
            f"总价格: {total_cost:,} 金币\n"
            f"礼包详情:\n  " + "\n  ".join(pack_details),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始批量购买
        self.buy_all_packs_btn.setEnabled(False)
        self.purchase_log_text.append(f"🛒 开始批量购买 {len(recipe_names)} 个食材礼包...")
        
        try:
            shop_action = ShopAction(self.current_key, self.current_cookie)
            result = shop_action.batch_buy_specialty_packs(recipe_names)
            
            if result.get("success"):
                success_count = result.get("success_count", 0)
                all_ingredients = result.get("all_ingredients", [])
                self.purchase_log_text.append(f"✅ 批量购买完成: 成功 {success_count}/{len(recipe_names)} 个")
                
                if all_ingredients:
                    ingredient_counts = {}
                    for ing in all_ingredients:
                        name = ing.get("name", "")
                        count = ing.get("count", 0)
                        ingredient_counts[name] = ingredient_counts.get(name, 0) + count
                    
                    ingredients_text = ", ".join([f"{name}x{count}" for name, count in ingredient_counts.items()])
                    self.purchase_log_text.append(f"   总计获得: {ingredients_text}")
            else:
                error_msg = result.get("message", "批量购买失败")
                self.purchase_log_text.append(f"❌ 批量购买失败: {error_msg}")
        except Exception as e:
            self.purchase_log_text.append(f"❌ 批量购买出错: {e}")
        finally:
            self.buy_all_packs_btn.setEnabled(True)
    
    def _batch_account_buy_packs(self):
        """批量账号购买特色菜食材礼包"""
        # 获取所有账号
        accounts = self.account_manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key and acc.cookie]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号")
            return
        
        # 选择要购买的特色菜
        recipe_name = self.specialty_pack_combo.currentData()
        if not recipe_name:
            QMessageBox.warning(self, "提示", "请先选择特色菜")
            return
        
        pack = get_pack_by_recipe_name(recipe_name)
        if not pack:
            QMessageBox.warning(self, "提示", "未找到礼包信息")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量购买",
            f"确认对 {len(valid_accounts)} 个账号批量购买 {pack.icon} {recipe_name} 礼包？\n\n"
            f"单价: {pack.price:,} 金币\n"
            f"总计: {len(valid_accounts)} × {pack.price:,} = {len(valid_accounts) * pack.price:,} 金币\n"
            f"包含: {', '.join(pack.ingredients)} (各3个)\n\n"
            f"账号列表: {', '.join([acc.username for acc in valid_accounts[:5]])}{'...' if len(valid_accounts) > 5 else ''}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始批量操作
        self.batch_account_buy_btn.setEnabled(False)
        self.purchase_log_text.append(f"🏢 开始批量账号购买: {recipe_name} × {len(valid_accounts)}个账号")
        
        success_count = 0
        failed_count = 0
        
        for i, account in enumerate(valid_accounts):
            try:
                self.purchase_log_text.append(f"  [{i+1}/{len(valid_accounts)}] {account.username}: 购买中...")
                
                cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
                shop_action = ShopAction(account.key, cookie_dict)
                
                result = shop_action.buy_and_open_specialty_pack(recipe_name)
                
                if result.get("success"):
                    success_count += 1
                    ingredients = result.get("total_ingredients", [])
                    ingredients_text = ", ".join([f"{ing['name']}x{ing['count']}" for ing in ingredients])
                    self.purchase_log_text.append(f"    ✅ 成功: {ingredients_text}")
                else:
                    failed_count += 1
                    error_msg = result.get("message", "购买失败")
                    self.purchase_log_text.append(f"    ❌ 失败: {error_msg}")
                
                # 账号间间隔2秒
                if i < len(valid_accounts) - 1:
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                failed_count += 1
                self.purchase_log_text.append(f"    ❌ 错误: {e}")
        
        # 总结
        self.purchase_log_text.append(f"🎉 批量购买完成! 成功: {success_count}个账号, 失败: {failed_count}个账号")
        self.batch_account_buy_btn.setEnabled(True)
    
    def _get_recipe_id_by_name(self, recipe_name: str, specialty_action) -> Optional[str]:
        """根据特色菜名称获取recipe_id"""
        try:
            # 获取已学特色菜列表
            result = specialty_action.get_learned_recipes()
            if not result.get("success"):
                return None
                
            recipes = result.get("recipes", [])
            for recipe in recipes:
                if recipe.get("name") == recipe_name:
                    return recipe.get("id")
            return None
        except Exception as e:
            logging.error(f"获取recipe_id失败: {e}")
            return None

    def _batch_account_cook_specialty(self):
        """批量账号烹饪特色菜"""
        # 获取所有账号
        accounts = self.account_manager.list_accounts()
        valid_accounts = [acc for acc in accounts if acc.key and acc.cookie]
        
        if not valid_accounts:
            QMessageBox.warning(self, "提示", "没有可用的账号")
            return
        
        # 选择要烹饪的特色菜
        recipe_name = self.specialty_pack_combo.currentData()
        if not recipe_name:
            QMessageBox.warning(self, "提示", "请先选择特色菜")
            return
        
        # 烹饪倍数选择
        multipliers = ["3", "5", "10", "50", "100"]
        multiplier, ok = QInputDialog.getItem(
            self, "设置烹饪倍数",
            f"请选择每次烹饪 {recipe_name} 的倍数:",
            multipliers, 0, False
        )
        
        if not ok:
            return
        
        multiplier = int(multiplier)
        
        # 烹饪次数输入
        cook_times, ok = QInputDialog.getInt(
            self, "设置烹饪次数",
            f"请设置每个账号烹饪次数（每次 {multiplier} 倍）:",
            1, 1, 10, 1
        )
        
        if not ok:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量烹饪",
            f"确认对 {len(valid_accounts)} 个账号批量烹饪 {recipe_name}？\n\n"
            f"烹饪倍数: {multiplier} 倍\n"
            f"烹饪次数: 每个账号 {cook_times} 次\n"
            f"实际产出: 每个账号 {multiplier * cook_times} 个 {recipe_name}\n"
            f"总计: {len(valid_accounts)} × {multiplier * cook_times} = {len(valid_accounts) * multiplier * cook_times} 个\n\n"
            f"账号列表: {', '.join([acc.username for acc in valid_accounts[:5]])}{'...' if len(valid_accounts) > 5 else ''}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始批量烹饪
        self.batch_account_cook_btn.setEnabled(False)
        self.purchase_log_text.append(f"👨‍🍳 开始批量账号烹饪: {recipe_name} × {len(valid_accounts)}个账号")
        self.purchase_log_text.append(f"    参数: {multiplier}倍 × {cook_times}次 = 每账号产出{multiplier * cook_times}个")
        
        success_count = 0
        failed_count = 0
        total_cooked = 0
        
        for i, account in enumerate(valid_accounts):
            try:
                self.purchase_log_text.append(f"  [{i+1}/{len(valid_accounts)}] {account.username}: 烹饪中...")
                
                cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else None
                specialty_action = SpecialtyFoodAction(account.key, cookie_dict)
                
                # 获取recipe_id
                recipe_id = self._get_recipe_id_by_name(recipe_name, specialty_action)
                if not recipe_id:
                    self.purchase_log_text.append(f"    ❌ 找不到特色菜 {recipe_name} 的ID，可能未学会此菜谱")
                    failed_count += 1
                    continue
                
                # 执行烹饪
                account_success = 0
                account_produced = 0
                for j in range(cook_times):
                    try:
                        cook_result = specialty_action.cook_recipe(recipe_id, multiplier)
                        if cook_result.get("success"):
                            account_success += 1
                            account_produced += multiplier
                            self.purchase_log_text.append(f"    🍳 第{j+1}次烹饪成功 (+{multiplier}个)")
                        else:
                            error_msg = cook_result.get("message", "未知错误")
                            self.purchase_log_text.append(f"    ❌ 第{j+1}次烹饪失败: {error_msg}")
                        
                        # 烹饪间隔
                        import time
                        time.sleep(1)
                        
                    except Exception as cook_error:
                        self.purchase_log_text.append(f"    ❌ 第{j+1}次烹饪异常: {cook_error}")
                
                if account_success > 0:
                    success_count += 1
                    total_cooked += account_produced
                    self.purchase_log_text.append(f"    ✅ 成功烹饪 {account_success}/{cook_times} 次，产出 {account_produced} 个")
                else:
                    failed_count += 1
                    self.purchase_log_text.append(f"    ❌ 所有烹饪均失败")
                
                # 账号间间隔2秒
                if i < len(valid_accounts) - 1:
                    import time
                    time.sleep(2)
                    
            except Exception as e:
                failed_count += 1
                self.purchase_log_text.append(f"    ❌ 错误: {e}")
        
        # 总结
        self.purchase_log_text.append(f"🎉 批量烹饪完成! 成功: {success_count}个账号, 总烹饪: {total_cooked}次")
        self.batch_account_cook_btn.setEnabled(True)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 清理线程
        if self.data_thread and self.data_thread.isRunning():
            self.data_thread.quit()
            self.data_thread.wait()
        
        if self.appraisal_thread and self.appraisal_thread.isRunning():
            self.appraisal_thread.quit()
            self.appraisal_thread.wait()
        
        if self.fragment_thread and self.fragment_thread.isRunning():
            self.fragment_thread.quit()
            self.fragment_thread.wait()
        
        if self.recipe_thread and self.recipe_thread.isRunning():
            self.recipe_thread.quit()
            self.recipe_thread.wait()
        
        if self.cooking_thread and self.cooking_thread.isRunning():
            self.cooking_thread.quit()
            self.cooking_thread.wait()
        
        if self.detail_thread and self.detail_thread.isRunning():
            self.detail_thread.quit()
            self.detail_thread.wait()
        
        event.accept()
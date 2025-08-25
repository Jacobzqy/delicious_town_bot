"""
赛厨排行榜页面 - 显示不同区域的排行榜数据
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QComboBox, QLabel,
    QMessageBox, QHeaderView, QFrame, QTextEdit,
    QAbstractItemView, QSplitter, QLineEdit, QSpinBox,
    QGroupBox, QDialog, QScrollArea, QGridLayout,
    QCheckBox, QProgressBar
)
from PySide6.QtGui import QFont

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.constants import MatchRankingType
from src.delicious_town_bot.actions.match import MatchAction


class MatchDataWorker(QObject):
    """排行榜数据获取工作器"""
    data_loaded = Signal(str, list)  # 区域名称, 排行榜数据
    error_occurred = Signal(str)     # 错误消息
    power_data_loaded = Signal(dict) # 厨力数据
    my_power_data_loaded = Signal(dict) # 我的厨力数据
    challenge_completed = Signal(dict)   # 挑战完成信号
    
    def __init__(self, account_manager: AccountManager):
        super().__init__()
        self.account_manager = account_manager
        self.is_cancelled = False
    
    def fetch_ranking_data(self, ranking_type: MatchRankingType):
        """获取排行榜数据"""
        try:
            # 获取第一个有效账号
            accounts = self.account_manager.list_accounts()
            if not accounts:
                self.error_occurred.emit("没有可用的账号")
                return
                
            account = None
            for acc in accounts:
                if acc.key and acc.cookie:
                    account = acc
                    break
            
            if not account:
                self.error_occurred.emit("没有有效的账号（需要key和cookie）")
                return
            
            # 创建MatchAction实例并获取数据
            match_action = MatchAction(account.key, {"PHPSESSID": account.cookie})
            all_rankings = match_action.get_all_rankings_with_empty(ranking_type)
            region_name = match_action.get_ranking_type_name(ranking_type)
            
            self.data_loaded.emit(region_name, all_rankings)
            
        except Exception as e:
            self.error_occurred.emit(f"获取排行榜数据失败: {str(e)}")
    
    def fetch_power_data(self, res_id: str):
        """获取餐厅厨力数据"""
        try:
            # 获取第一个有效账号
            accounts = self.account_manager.list_accounts()
            if not accounts:
                self.error_occurred.emit("没有可用的账号")
                return
                
            account = None
            for acc in accounts:
                if acc.key and acc.cookie:
                    account = acc
                    break
            
            if not account:
                self.error_occurred.emit("没有有效的账号（需要key和cookie）")
                return
            
            # 创建MatchAction实例并获取厨力数据
            match_action = MatchAction(account.key, {"PHPSESSID": account.cookie})
            power_data = match_action.get_restaurant_power_data(res_id)
            
            if power_data:
                self.power_data_loaded.emit(power_data)
            else:
                self.error_occurred.emit("获取厨力数据失败")
                
        except Exception as e:
            self.error_occurred.emit(f"获取厨力数据失败: {str(e)}")
    
    def fetch_my_power_data(self, account_id: int):
        """获取我的厨力数据"""
        try:
            # 获取指定账号
            account = None
            for acc in self.account_manager.list_accounts():
                if acc.id == account_id:
                    account = acc
                    break
            
            if not account or not account.key or not account.cookie:
                self.error_occurred.emit("选择的账号无效或缺少key/cookie")
                return
            
            # 创建MatchAction实例并获取自己的厨力数据
            match_action = MatchAction(account.key, {"PHPSESSID": account.cookie})
            power_data = match_action.get_restaurant_power_data("")  # 空字符串表示获取自己的数据
            
            if power_data:
                self.my_power_data_loaded.emit(power_data)
            else:
                self.error_occurred.emit("获取自己的厨力数据失败")
                
        except Exception as e:
            self.error_occurred.emit(f"获取自己的厨力数据失败: {str(e)}")
    
    def challenge_restaurant(self, account_id: int, ranking_type: MatchRankingType, ranking_num: int):
        """挑战指定排名的餐厅"""
        try:
            # 获取指定账号
            account = None
            for acc in self.account_manager.list_accounts():
                if acc.id == account_id:
                    account = acc
                    break
            
            if not account or not account.key or not account.cookie:
                self.error_occurred.emit("选择的账号无效或缺少key/cookie")
                return
            
            # 创建MatchAction实例并执行挑战
            match_action = MatchAction(account.key, {"PHPSESSID": account.cookie})
            challenge_result = match_action.challenge_match(ranking_type, ranking_num)
            
            # 解析挑战结果
            if challenge_result.get("success"):
                parsed_result = match_action.parse_challenge_result(challenge_result)
                self.challenge_completed.emit(parsed_result)
            else:
                self.challenge_completed.emit(challenge_result)
                
        except Exception as e:
            error_result = {
                "success": False,
                "message": f"挑战请求失败: {str(e)}"
            }
            self.challenge_completed.emit(error_result)
    
    def occupy_empty_slot(self, account_id: int, ranking_type: MatchRankingType, ranking_num: int):
        """占领空位排名"""
        try:
            # 获取指定账号
            account = None
            for acc in self.account_manager.list_accounts():
                if acc.id == account_id:
                    account = acc
                    break
            
            if not account or not account.key or not account.cookie:
                self.error_occurred.emit("选择的账号无效或缺少key/cookie")
                return
            
            # 创建MatchAction实例并执行占领
            match_action = MatchAction(account.key, {"PHPSESSID": account.cookie})
            occupy_result = match_action.occupy_empty_slot(ranking_type, ranking_num)
            
            # 解析占领结果
            if occupy_result.get("success"):
                parsed_result = match_action.parse_challenge_result(occupy_result)
                self.challenge_completed.emit(parsed_result)
            else:
                self.challenge_completed.emit(occupy_result)
                
        except Exception as e:
            error_result = {
                "success": False,
                "message": f"占领请求失败: {str(e)}",
                "action_type": "occupy"
            }
            self.challenge_completed.emit(error_result)


class MatchRankingPage(QWidget):
    """赛厨排行榜页面"""
    
    def __init__(self, log_widget: QTextEdit, account_manager: AccountManager):
        super().__init__()
        self.log_widget = log_widget
        self.account_manager = account_manager
        self.current_data: List[Dict[str, Any]] = []
        self.setup_worker()  # 先设置worker
        self.setup_ui()      # 再设置UI
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题
        title_label = QLabel("赛厨排行榜")
        title_label.setProperty("role", "Title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 主要内容区域 - 使用水平分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：厨力信息面板
        left_panel = self.create_power_panel()
        left_panel.setMaximumWidth(320)  # 限制厨力面板宽度
        main_splitter.addWidget(left_panel)
        
        # 右侧：排行榜区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 控制面板
        control_panel = self.create_control_panel()
        right_layout.addWidget(control_panel)
        
        # 排行榜表格
        self.setup_ranking_table()
        right_layout.addWidget(self.ranking_table)
        
        # 连接表格双击事件
        self.ranking_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        # 统计信息
        self.stats_label = QLabel("请选择账号和区域，点击刷新获取数据")
        self.stats_label.setProperty("role", "Note")
        right_layout.addWidget(self.stats_label)
        
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([320, 800])  # 设置初始比例
        
        layout.addWidget(main_splitter)
    
    def create_power_panel(self) -> QWidget:
        """创建厨力信息面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 账号选择
        account_group = QGroupBox("选择账号")
        account_layout = QVBoxLayout(account_group)
        
        self.account_combo = QComboBox()
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        account_layout.addWidget(self.account_combo)
        
        refresh_power_btn = QPushButton("刷新厨力")
        refresh_power_btn.clicked.connect(self.refresh_my_power)
        account_layout.addWidget(refresh_power_btn)
        
        layout.addWidget(account_group)
        
        # 厨力信息显示
        power_group = QGroupBox("我的厨力")
        power_layout = QVBoxLayout(power_group)
        
        # 总厨力显示
        self.total_power_frame = QFrame()
        total_layout = QVBoxLayout(self.total_power_frame)
        
        self.total_label = QLabel("总厨力")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.total_label.setFont(font)
        
        self.total_value = QLabel("0")
        self.total_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(18)
        value_font.setBold(True)
        self.total_value.setFont(value_font)
        
        self.equipment_bonus = QLabel("装备加成: +0")
        self.equipment_bonus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.real_power_label = QLabel("真实厨力: 0")
        self.real_power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        real_font = QFont()
        real_font.setBold(True)
        self.real_power_label.setFont(real_font)
        self.real_power_label.setStyleSheet("color: #d32f2f;")
        
        total_layout.addWidget(self.total_label)
        total_layout.addWidget(self.total_value)
        total_layout.addWidget(self.equipment_bonus)
        total_layout.addWidget(self.real_power_label)
        
        power_layout.addWidget(self.total_power_frame)
        
        # 属性详情
        attributes_frame = QFrame()
        attributes_layout = QGridLayout(attributes_frame)
        attributes_layout.setSpacing(4)
        
        # 创建属性标签
        self.attribute_widgets = {}
        attributes = [
            ("fire", "火候", "#ff6b6b"),
            ("cooking", "厨艺", "#4ecdc4"), 
            ("sword", "刀工", "#45b7d1"),
            ("season", "调味", "#96ceb4"),
            ("originality", "创意", "#feca57"),
            ("luck", "运气", "#ff9ff3")
        ]
        
        for i, (attr_key, attr_name, color) in enumerate(attributes):
            row = i // 2
            col = (i % 2) * 2
            
            # 属性名
            name_label = QLabel(attr_name)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_font = QFont()
            name_font.setPointSize(9)
            name_font.setBold(True)
            name_label.setFont(name_font)
            
            # 总值（含装备）
            total_label = QLabel("0")
            total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            total_font = QFont()
            total_font.setPointSize(9)
            total_font.setBold(True)
            total_label.setFont(total_font)
            total_label.setStyleSheet(f"color: {color};")
            
            attributes_layout.addWidget(name_label, row, col)
            attributes_layout.addWidget(total_label, row, col + 1)
            
            self.attribute_widgets[attr_key] = {
                "name": name_label,
                "total": total_label
            }
        
        power_layout.addWidget(attributes_frame)
        
        # 餐厅信息
        self.restaurant_info_label = QLabel("餐厅: 未知\n等级: --\n街道: --")
        self.restaurant_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.restaurant_info_label.setStyleSheet("color: #666; font-size: 10px;")
        power_layout.addWidget(self.restaurant_info_label)
        
        layout.addWidget(power_group)
        
        # 加载账号列表
        self.load_accounts()
        
        layout.addStretch()  # 添加弹性空间
        
        return panel
        
    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QGroupBox("排行榜控制")
        layout = QHBoxLayout(panel)
        
        # 区域选择
        layout.addWidget(QLabel("区域:"))
        self.region_combo = QComboBox()
        self.region_combo.addItems([
            "低级区", "初级区", "中级区", 
            "高级区", "顶级区", "巅峰区"
        ])
        self.region_combo.setCurrentIndex(1)  # 默认选择初级区
        layout.addWidget(self.region_combo)
        
        layout.addStretch()
        
        # 操作按钮
        self.refresh_btn = QPushButton("🔄 刷新排行榜")
        self.refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("📤 导出")
        self.export_btn.clicked.connect(self.export_data)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)
        
        # 搜索框
        layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("餐厅名称...")
        self.search_edit.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_edit)
        
        # 显示空位选项
        self.show_empty_checkbox = QCheckBox("显示空位")
        self.show_empty_checkbox.setChecked(True)
        self.show_empty_checkbox.stateChanged.connect(self.filter_table)
        layout.addWidget(self.show_empty_checkbox)
        
        return panel
    
    def setup_ranking_table(self):
        """设置排行榜表格"""
        self.ranking_table = QTableWidget()
        self.ranking_table.setColumnCount(6)
        self.ranking_table.setHorizontalHeaderLabels(["排名", "餐厅名称", "等级", "餐厅ID", "状态", "操作"])
        
        # 表格样式设置
        self.ranking_table.verticalHeader().setVisible(False)
        self.ranking_table.setAlternatingRowColors(True)
        self.ranking_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ranking_table.setShowGrid(False)
        self.ranking_table.setSortingEnabled(True)
        
        # 列宽设置
        header = self.ranking_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        self.ranking_table.setColumnWidth(0, 60)   # 排名
        self.ranking_table.setColumnWidth(2, 60)   # 等级
        self.ranking_table.setColumnWidth(3, 80)   # 餐厅ID
        self.ranking_table.setColumnWidth(4, 60)   # 状态
        self.ranking_table.setColumnWidth(5, 80)   # 操作
        
        # 设置表格最大高度以适配小屏幕
        self.ranking_table.setMaximumHeight(350)  # 显著降低表格高度
        
    def setup_worker(self):
        """设置数据获取工作器"""
        self.data_thread = QThread()
        self.data_worker = MatchDataWorker(self.account_manager)
        self.data_worker.moveToThread(self.data_thread)
        
        # 连接信号
        self.data_worker.data_loaded.connect(self.on_data_loaded)
        self.data_worker.error_occurred.connect(self.on_error_occurred)
        self.data_worker.power_data_loaded.connect(self.on_power_data_loaded)
        self.data_worker.my_power_data_loaded.connect(self.on_my_power_data_loaded)
        self.data_worker.challenge_completed.connect(self.on_challenge_completed)
        
        self.data_thread.start()
    
    def load_accounts(self):
        """加载账号列表"""
        self.account_combo.clear()
        accounts = self.account_manager.list_accounts()
        
        if not accounts:
            self.account_combo.addItem("无可用账号", userData=None)
            return
        
        for account in accounts:
            display_name = f"{account.username}"
            if account.restaurant:
                display_name += f" ({account.restaurant})"
            if not account.key or not account.cookie:
                display_name += " [缺少认证]"
            
            self.account_combo.addItem(display_name, userData=account.id)
    
    @Slot()
    def on_account_changed(self):
        """账号选择改变"""
        account_id = self.account_combo.currentData()
        if account_id and hasattr(self, 'data_worker'):
            self.refresh_my_power()
    
    @Slot()
    def refresh_my_power(self):
        """刷新当前账号的厨力数据"""
        account_id = self.account_combo.currentData()
        if not account_id:
            self.log_message("请先选择一个有效的账号")
            return
        
        self.log_message("正在获取账号厨力数据...")
        self.data_worker.fetch_my_power_data(account_id)
    
    @Slot(dict)
    def on_my_power_data_loaded(self, power_data: Dict[str, Any]):
        """我的厨力数据加载完成"""
        self.update_power_display(power_data)
        restaurant_name = power_data.get("restaurant_name", "未知餐厅")
        self.log_message(f"成功获取厨力数据: {restaurant_name}")
    
    def update_power_display(self, power_data: Dict[str, Any]):
        """更新厨力显示"""
        if not power_data:
            return
        
        # 更新总厨力
        total_power = power_data.get("total_power", 0)
        base_power = power_data.get("base_power", 0)
        equipment_bonus = power_data.get("equipment_bonus", 0)
        real_power = power_data.get("real_power", 0)
        
        self.total_value.setText(f"{total_power:,}")
        self.equipment_bonus.setText(f"装备加成: +{equipment_bonus:,}")
        self.real_power_label.setText(f"真实厨力: {real_power:,}")
        
        # 更新各属性
        attributes = power_data.get("attributes", {})
        for attr_key, widgets in self.attribute_widgets.items():
            value = attributes.get(attr_key, 0)
            widgets["total"].setText(f"{value:,}")
        
        # 更新餐厅信息
        restaurant_name = power_data.get("restaurant_name", "未知餐厅")
        restaurant_level = power_data.get("restaurant_level", 0)
        restaurant_star = power_data.get("restaurant_star", 0)
        street_name = power_data.get("street_name", "未知街道")
        cook_type = power_data.get("cook_type", "未知菜系")
        speciality_name = power_data.get("speciality", {}).get("name", "无招牌菜")
        
        info_text = f"""餐厅: {restaurant_name}
等级: {restaurant_level}级 {restaurant_star}星
街道: {street_name} ({cook_type})
特色菜: {speciality_name}"""
        
        self.restaurant_info_label.setText(info_text)
    
    def get_selected_ranking_type(self) -> MatchRankingType:
        """获取当前选择的排行榜类型"""
        index = self.region_combo.currentIndex()
        types = [
            MatchRankingType.NOVICE, MatchRankingType.BEGINNER, 
            MatchRankingType.INTERMEDIATE, MatchRankingType.ADVANCED,
            MatchRankingType.EXPERT, MatchRankingType.PEAK
        ]
        return types[index]
    
    @Slot()
    def refresh_data(self):
        """刷新排行榜数据"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请先选择一个有效的账号")
            return
        
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("🔄 获取中...")
        self.stats_label.setText("正在获取排行榜数据...")
        
        ranking_type = self.get_selected_ranking_type()
        
        # 在工作线程中获取数据
        self.data_worker.fetch_ranking_data(ranking_type)
        
    @Slot(str, list)
    def on_data_loaded(self, region_name: str, restaurants: List[Dict[str, Any]]):
        """数据加载完成"""
        self.current_data = restaurants
        self.populate_table(restaurants)
        
        # 更新统计信息
        total_restaurants = len(restaurants)
        active_restaurants = len([r for r in restaurants if not r.get("is_empty", False)])
        empty_slots = total_restaurants - active_restaurants
        
        if active_restaurants > 0:
            active_only = [r for r in restaurants if not r.get("is_empty", False)]
            avg_level = sum(r["level"] for r in active_only) / active_restaurants
            self.stats_label.setText(f"{region_name} - 活跃餐厅: {active_restaurants} 家，空位: {empty_slots} 个，平均等级: {avg_level:.1f}")
        else:
            self.stats_label.setText(f"{region_name} - 暂无活跃餐厅，空位: {empty_slots} 个")
            
        self.export_btn.setEnabled(active_restaurants > 0)
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新数据")
        
        self.log_message(f"成功获取{region_name}排行榜数据，共{active_restaurants}家活跃餐厅，{empty_slots}个空位")
    
    @Slot(str)
    def on_error_occurred(self, error_message: str):
        """处理错误"""
        QMessageBox.warning(self, "错误", error_message)
        self.stats_label.setText(f"获取数据失败: {error_message}")
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新数据")
        self.log_message(f"获取排行榜数据失败: {error_message}")
    
    def populate_table(self, restaurants: List[Dict[str, Any]]):
        """填充表格数据"""
        self.ranking_table.setRowCount(len(restaurants))
        
        for row, restaurant in enumerate(restaurants):
            is_empty = restaurant.get("is_empty", False)
            
            # 排名
            ranking_item = QTableWidgetItem(str(restaurant["ranking_num"]))
            ranking_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ranking_item.setFlags(ranking_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ranking_table.setItem(row, 0, ranking_item)
            
            # 餐厅名称
            name_item = QTableWidgetItem(restaurant["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_empty:
                name_item.setForeground(Qt.GlobalColor.gray)
            self.ranking_table.setItem(row, 1, name_item)
            
            # 等级
            level_text = str(restaurant["level"]) if restaurant["level"] is not None else "-"
            level_item = QTableWidgetItem(level_text)
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            level_item.setFlags(level_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_empty:
                level_item.setForeground(Qt.GlobalColor.gray)
            self.ranking_table.setItem(row, 2, level_item)
            
            # 餐厅ID
            id_item = QTableWidgetItem(str(restaurant["res_id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_empty:
                id_item.setForeground(Qt.GlobalColor.gray)
            self.ranking_table.setItem(row, 3, id_item)
            
            # 状态
            status_text = "空位" if is_empty else "活跃"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_empty:
                status_item.setForeground(Qt.GlobalColor.gray)
            else:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            self.ranking_table.setItem(row, 4, status_item)
            
            # 操作按钮 - 活跃餐厅显示"挑战"，空位显示"占领"
            if not is_empty:
                challenge_btn = QPushButton("挑战")
                challenge_btn.setMaximumSize(70, 25)
                challenge_btn.clicked.connect(lambda checked, r=restaurant: self.challenge_restaurant(r))
                self.ranking_table.setCellWidget(row, 5, challenge_btn)
            else:
                occupy_btn = QPushButton("占领")
                occupy_btn.setMaximumSize(70, 25)
                occupy_btn.setStyleSheet("QPushButton { background-color: #4caf50; color: white; font-weight: bold; }")
                occupy_btn.clicked.connect(lambda checked, r=restaurant: self.occupy_empty_slot(r))
                self.ranking_table.setCellWidget(row, 5, occupy_btn)
            
            # 存储餐厅数据到第一列用于后续使用
            ranking_item.setData(Qt.ItemDataRole.UserRole, restaurant)
    
    @Slot()
    def filter_table(self):
        """根据搜索框内容和空位选项过滤表格"""
        search_text = self.search_edit.text().lower()
        show_empty = self.show_empty_checkbox.isChecked()
        
        for row in range(self.ranking_table.rowCount()):
            ranking_item = self.ranking_table.item(row, 0)
            name_item = self.ranking_table.item(row, 1)
            
            if ranking_item and name_item:
                restaurant_data = ranking_item.data(Qt.ItemDataRole.UserRole)
                is_empty = restaurant_data.get("is_empty", False) if restaurant_data else False
                
                # 检查搜索文本
                text_match = search_text in name_item.text().lower()
                
                # 检查是否显示空位
                empty_filter = show_empty or not is_empty
                
                should_show = text_match and empty_filter
                self.ranking_table.setRowHidden(row, not should_show)
    
    @Slot()
    def export_data(self):
        """导出数据到文件"""
        if not self.current_data:
            QMessageBox.information(self, "提示", "没有数据可以导出")
            return
        
        try:
            region_name = self.region_combo.currentText()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"赛厨排行榜_{region_name}_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"赛厨排行榜 - {region_name}\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"{'排名':<8} {'餐厅名称':<20} {'等级':<8} {'餐厅ID':<10}\n")
                f.write("-" * 50 + "\n")
                
                for restaurant in self.current_data:
                    f.write(f"{restaurant['ranking_num']:<8} {restaurant['name']:<20} "
                           f"{restaurant['level']:<8} {restaurant['res_id']:<10}\n")
            
            QMessageBox.information(self, "成功", f"数据已导出到文件: {filename}")
            self.log_message(f"数据已导出到文件: {filename}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")
            self.log_message(f"数据导出失败: {str(e)}")
    
    def log_message(self, message: str):
        """向日志窗口添加消息"""
        if self.log_widget:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_widget.append(f"[{timestamp}] [赛厨排行榜] {message}")
    
    @Slot(int, int)
    def on_cell_double_clicked(self, row: int, column: int):
        """处理表格双击事件，显示餐厅详细信息"""
        ranking_item = self.ranking_table.item(row, 0)
        if not ranking_item:
            return
            
        restaurant_data = ranking_item.data(Qt.ItemDataRole.UserRole)
        if not restaurant_data or restaurant_data.get("is_empty", False):
            QMessageBox.information(self, "提示", "空位无法查看详细信息")
            return
            
        res_id = restaurant_data.get("res_id")
        if not res_id or res_id == "0":
            QMessageBox.information(self, "提示", "无效的餐厅ID")
            return
            
        # 在工作线程中获取厨力数据
        self.log_message(f"正在获取餐厅 {restaurant_data.get('name')} 的厨力数据...")
        self.data_worker.fetch_power_data(res_id)
    
    @Slot(dict)
    def on_power_data_loaded(self, power_data: Dict[str, Any]):
        """厨力数据加载完成"""
        dialog = RestaurantPowerDialog(power_data, self)
        dialog.exec()
        
        restaurant_name = power_data.get("restaurant_name", "未知餐厅")
        self.log_message(f"成功获取餐厅 {restaurant_name} 的厨力数据")
    
    def challenge_restaurant(self, restaurant_data: Dict[str, Any]):
        """挑战指定餐厅"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请先选择一个有效的账号")
            return
        
        restaurant_name = restaurant_data.get("name", "未知餐厅")
        ranking_num = restaurant_data.get("ranking_num", 0)
        ranking_type = self.get_selected_ranking_type()
        
        # 确认挑战
        reply = QMessageBox.question(
            self, 
            "确认挑战", 
            f"确定要挑战第{ranking_num}名的餐厅「{restaurant_name}」吗？\n\n注意：挑战会消耗体力！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_message(f"开始挑战第{ranking_num}名餐厅: {restaurant_name}")
        
        # 在工作线程中执行挑战
        self.data_worker.challenge_restaurant(account_id, ranking_type, ranking_num)
    
    def occupy_empty_slot(self, restaurant_data: Dict[str, Any]):
        """占领空位"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请先选择一个有效的账号")
            return
        
        ranking_num = restaurant_data.get("ranking_num", 0)
        ranking_type = self.get_selected_ranking_type()
        
        # 确认占领
        reply = QMessageBox.question(
            self, 
            "确认占领", 
            f"确定要占领第{ranking_num}名的空位吗？\n\n注意：占领会消耗体力！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log_message(f"开始占领第{ranking_num}名空位")
        
        # 在工作线程中执行占领
        self.data_worker.occupy_empty_slot(account_id, ranking_type, ranking_num)
    
    @Slot(dict)
    def on_challenge_completed(self, result: Dict[str, Any]):
        """挑战/占领完成处理"""
        if result.get("success"):
            action_type = result.get("action_type", "challenge")
            vitality_cost = result.get("vitality_cost", 0)
            
            if action_type == "occupy":
                # 占领空位结果处理
                occupied_ranking = result.get("occupied_ranking", 0)
                victory = result.get("victory", True)  # 占领通常都成功
                
                # 显示占领结果对话框
                dialog = OccupyResultDialog(result, self)
                dialog.exec()
                
                # 记录日志
                status = "成功占领" if victory else "占领失败"
                self.log_message(f"占领结果: {status} | 排名: 第{occupied_ranking}名 | 体力-{vitality_cost}")
                
            else:
                # 挑战其他餐厅结果处理
                opponent_name = result.get("opponent_name", "未知对手")
                victory = result.get("victory", False)
                prestige_change = result.get("prestige_change", 0)
                total_score = result.get("total_score", {"my": 0, "opponent": 0})
                
                # 显示挑战结果对话框
                dialog = ChallengeResultDialog(result, self)
                dialog.exec()
                
                # 记录日志
                status = "胜利" if victory else "失败"
                prestige_text = f"声望{prestige_change:+d}" if prestige_change != 0 else "声望无变化"
                self.log_message(
                    f"挑战结果: {status} | 对手: {opponent_name} | "
                    f"比分: {total_score['my']:.1f}:{total_score['opponent']:.1f} | "
                    f"体力-{vitality_cost} | {prestige_text}"
                )
            
            # 自动刷新排行榜数据
            QTimer.singleShot(2000, self.refresh_data)  # 2秒后刷新
            
        else:
            # 失败的操作
            action_type = result.get("action_type", "challenge")
            action_name = "占领" if action_type == "occupy" else "挑战"
            error_msg = result.get("message", f"{action_name}失败")
            QMessageBox.warning(self, f"{action_name}失败", error_msg)
            self.log_message(f"{action_name}失败: {error_msg}")
    
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        if hasattr(self, 'data_thread'):
            self.data_thread.quit()
            self.data_thread.wait()
        event.accept()


class RestaurantPowerDialog(QDialog):
    """餐厅厨力数据对话框"""
    
    def __init__(self, power_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.power_data = power_data
        self.setWindowTitle(f"厨力数据 - {power_data.get('restaurant_name', '未知餐厅')}")
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 餐厅基本信息
        basic_group = QGroupBox("餐厅基本信息")
        basic_layout = QGridLayout(basic_group)
        
        basic_info = [
            ("餐厅名称", self.power_data.get("restaurant_name", "未知餐厅")),
            ("餐厅等级", f"{self.power_data.get('restaurant_level', 0)}级"),
            ("星级", f"{self.power_data.get('restaurant_star', 0)}星"),
            ("街道", f"{self.power_data.get('street_name', '未知街道')} ({self.power_data.get('cook_type', '未知菜系')})"),
            ("VIP等级", f"VIP{self.power_data.get('vip_level', 0)}"),
            ("声望", f"{self.power_data.get('prestige', 0):,}"),
            ("金币", f"{self.power_data.get('gold', 0):,}"),
            ("经验", f"{self.power_data.get('exp', 0):,}")
        ]
        
        for i, (label, value) in enumerate(basic_info):
            row = i // 4  # 每行显示4个信息项
            col = (i % 4) * 2
            basic_layout.addWidget(QLabel(f"{label}:"), row, col)
            basic_layout.addWidget(QLabel(str(value)), row, col + 1)
        
        scroll_layout.addWidget(basic_group)
        
        # 厨力信息
        power_group = QGroupBox("厨力信息")
        power_layout = QGridLayout(power_group)
        
        power_info = [
            ("总厨力", f"{self.power_data.get('total_power', 0):,}"),
            ("基础厨力", f"{self.power_data.get('base_power', 0):,}"),
            ("装备加成", f"+{self.power_data.get('equipment_bonus', 0):,}"),
            ("真实厨力", f"{self.power_data.get('real_power', 0):,}")
        ]
        
        for i, (label, value) in enumerate(power_info):
            power_layout.addWidget(QLabel(f"{label}:"), i // 2, (i % 2) * 2)
            value_label = QLabel(str(value))
            if label == "真实厨力":
                value_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
            power_layout.addWidget(value_label, i // 2, (i % 2) * 2 + 1)
        
        scroll_layout.addWidget(power_group)
        
        # 属性详情
        attr_group = QGroupBox("属性详情")
        attr_layout = QGridLayout(attr_group)
        
        attributes = self.power_data.get("attributes", {})
        attr_names = {
            "fire": "火候", "cooking": "厨艺", "sword": "刀工",
            "season": "调味", "originality": "创意", "luck": "运气"
        }
        
        for i, (attr_key, attr_name) in enumerate(attr_names.items()):
            value = attributes.get(attr_key, 0)
            attr_layout.addWidget(QLabel(f"{attr_name}:"), i // 3, (i % 3) * 2)
            attr_layout.addWidget(QLabel(f"{value:,}"), i // 3, (i % 3) * 2 + 1)
        
        scroll_layout.addWidget(attr_group)
        
        # 特色菜信息
        speciality_group = QGroupBox("特色菜信息")
        speciality_layout = QGridLayout(speciality_group)
        
        speciality = self.power_data.get("speciality", {})
        speciality_info = [
            ("特色菜名称", speciality.get("name", "无招牌菜")),
            ("营养值", f"{speciality.get('nutritive', 0)}"),
            ("品质", f"{speciality.get('quality', 0)}星")
        ]
        
        for i, (label, value) in enumerate(speciality_info):
            speciality_layout.addWidget(QLabel(f"{label}:"), i // 2, (i % 2) * 2)
            speciality_layout.addWidget(QLabel(str(value)), i // 2, (i % 2) * 2 + 1)
        
        scroll_layout.addWidget(speciality_group)
        
        # 装备信息
        equipment_group = QGroupBox("装备信息")
        equipment_layout = QVBoxLayout(equipment_group)
        equipment_count = self.power_data.get("equipment_count", 0)
        equipment_layout.addWidget(QLabel(f"装备数量: {equipment_count} 件"))
        scroll_layout.addWidget(equipment_group)
        
        # 真实厨力说明
        formula_group = QGroupBox("真实厨力计算公式")
        formula_layout = QVBoxLayout(formula_group)
        formula_text = QLabel("真实厨力 = 厨艺×1.44 + 刀工×1.41 + 调味×1.5 + 火候×1.71 + 创意×2.25 + 特色菜营养值×1.8")
        formula_text.setWordWrap(True)
        formula_text.setStyleSheet("color: #666; font-style: italic;")
        formula_layout.addWidget(formula_text)
        scroll_layout.addWidget(formula_group)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ChallengeResultDialog(QDialog):
    """挑战结果对话框"""
    
    def __init__(self, challenge_result: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.challenge_result = challenge_result
        self.setWindowTitle("挑战结果")
        self.setMinimumSize(580, 420)  # 小屏友好的最小尺寸
        self.resize(600, 480)  # 合理的默认窗口大小，适配小屏幕
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)  # 减少边距
        layout.setSpacing(8)  # 减少组件间距
        
        # 挑战结果状态 - 固定在顶部
        result_frame = QFrame()
        result_frame.setObjectName("StatsPanel")
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(8, 8, 8, 8)
        
        # 胜负显示
        victory = self.challenge_result.get("victory", False)
        victory_text = "🎉 挑战胜利！" if victory else "😞 挑战失败"
        victory_color = "#4caf50" if victory else "#f44336"
        
        victory_label = QLabel(victory_text)
        victory_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        victory_font = QFont()
        victory_font.setPointSize(14)  # 稍微减少字体大小
        victory_font.setBold(True)
        victory_label.setFont(victory_font)
        victory_label.setStyleSheet(f"color: {victory_color}; margin: 4px;")  # 减少边距
        result_layout.addWidget(victory_label)
        
        layout.addWidget(result_frame)
        
        # 基本信息 - 紧凑布局
        info_frame = QFrame()
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 4, 8, 4)
        
        # 对手信息
        opponent_name = self.challenge_result.get("opponent_name", "未知对手")
        opponent_level = self.challenge_result.get("opponent_level", 0)
        vitality_cost = self.challenge_result.get("vitality_cost", 0)
        prestige_change = self.challenge_result.get("prestige_change", 0)
        
        # 水平排列基本信息
        opponent_label = QLabel(f"对手: {opponent_name} ({opponent_level}级)")
        vitality_label = QLabel(f"体力: -{vitality_cost}")
        prestige_label = QLabel(f"声望: {prestige_change:+d}" if prestige_change != 0 else "声望: 无变化")
        
        if prestige_change > 0:
            prestige_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        elif prestige_change < 0:
            prestige_label.setStyleSheet("color: #f44336; font-weight: bold;")
        
        info_layout.addWidget(opponent_label)
        info_layout.addWidget(vitality_label)
        info_layout.addWidget(prestige_label)
        info_layout.addStretch()
        
        layout.addWidget(info_frame)
        
        # 总比分显示 - 紧凑布局
        total_score = self.challenge_result.get("total_score", {"my": 0, "opponent": 0})
        my_score = total_score.get("my", 0)
        opponent_score = total_score.get("opponent", 0)
        
        score_frame = QFrame()
        score_layout = QHBoxLayout(score_frame)
        score_layout.setContentsMargins(8, 4, 8, 4)
        
        score_text = QLabel(f"比分: {my_score:.1f} : {opponent_score:.1f}")
        score_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_font = QFont()
        score_font.setPointSize(12)
        score_font.setBold(True)
        score_text.setFont(score_font)
        score_text.setStyleSheet("color: #1976d2; padding: 4px;")
        
        score_layout.addStretch()
        score_layout.addWidget(score_text)
        score_layout.addStretch()
        
        layout.addWidget(score_frame)
        
        # 详细内容滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(6)
        
        # 详细评价
        evaluations = self.challenge_result.get("evaluations", [])
        if evaluations:
            eval_table = QTableWidget()
            eval_table.setColumnCount(5)
            eval_table.setHorizontalHeaderLabels(["评委", "项目", "我方", "对方", "评价"])
            eval_table.setRowCount(len(evaluations))
            eval_table.verticalHeader().setVisible(False)
            
            # 根据评价数量动态调整表格高度
            row_height = 25  # 估算每行高度
            header_height = 30  # 表头高度
            max_height = min(300, header_height + len(evaluations) * row_height + 10)  # 最大300像素
            eval_table.setMaximumHeight(max_height)
            
            for row, evaluation in enumerate(evaluations):
                items = [
                    evaluation.get("judge", ""),
                    evaluation.get("category", ""),
                    f"{evaluation.get('my_score', 0):.1f}",
                    f"{evaluation.get('opponent_score', 0):.1f}",
                    evaluation.get("evaluation", "")
                ]
                
                for col, text in enumerate(items):
                    item = QTableWidgetItem(str(text))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    eval_table.setItem(row, col, item)
            
            eval_table.resizeColumnsToContents()
            scroll_layout.addWidget(eval_table)
        
        # 将滚动区域添加到主布局
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # 原始消息（可选）
        raw_message = self.challenge_result.get("raw_message", "")
        if raw_message and len(raw_message) > 50:  # 只有较长消息才显示
            msg_group = QGroupBox("详细消息")
            msg_layout = QVBoxLayout(msg_group)
            
            msg_text = QTextEdit()
            msg_text.setPlainText(raw_message)
            msg_text.setReadOnly(True)
            # 根据消息长度动态调整高度
            estimated_lines = max(3, min(8, len(raw_message) // 80))  # 估算行数，最少3行，最多8行
            msg_text.setMaximumHeight(20 + estimated_lines * 18)  # 每行约18像素 + 边距
            msg_layout.addWidget(msg_text)
            
            layout.addWidget(msg_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("确定")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(80)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)


class OccupyResultDialog(QDialog):
    """占领结果对话框"""
    
    def __init__(self, occupy_result: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.occupy_result = occupy_result
        self.setWindowTitle("占领结果")
        self.setMinimumSize(400, 250)
        self.resize(450, 280)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 占领结果状态
        result_frame = QFrame()
        result_frame.setObjectName("StatsPanel")
        result_layout = QVBoxLayout(result_frame)
        
        # 成功显示
        victory = self.occupy_result.get("victory", True)
        victory_text = "🎉 成功占领空位！" if victory else "😞 占领失败"
        victory_color = "#4caf50" if victory else "#f44336"
        
        victory_label = QLabel(victory_text)
        victory_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        victory_font = QFont()
        victory_font.setPointSize(16)
        victory_font.setBold(True)
        victory_label.setFont(victory_font)
        victory_label.setStyleSheet(f"color: {victory_color}; margin: 10px;")
        result_layout.addWidget(victory_label)
        
        layout.addWidget(result_frame)
        
        # 占领信息
        info_group = QGroupBox("占领信息")
        info_layout = QGridLayout(info_group)
        
        occupied_ranking = self.occupy_result.get("occupied_ranking", 0)
        vitality_cost = self.occupy_result.get("vitality_cost", 0)
        
        basic_info = [
            ("占领排名", f"第{occupied_ranking}名" if occupied_ranking > 0 else "未知"),
            ("体力消耗", f"-{vitality_cost}"),
            ("占领状态", "成功" if victory else "失败"),
        ]
        
        for i, (label, value) in enumerate(basic_info):
            info_layout.addWidget(QLabel(f"{label}:"), i, 0)
            value_label = QLabel(str(value))
            if label == "占领状态":
                if victory:
                    value_label.setStyleSheet("color: #4caf50; font-weight: bold;")
                else:
                    value_label.setStyleSheet("color: #f44336; font-weight: bold;")
            info_layout.addWidget(value_label, i, 1)
        
        layout.addWidget(info_group)
        
        # 提示信息
        if victory:
            tip_group = QGroupBox("提示")
            tip_layout = QVBoxLayout(tip_group)
            
            tip_text = QLabel("🎯 恭喜您成功占领空位排名！\n📈 您的餐厅现在已进入排行榜\n🔄 排行榜将在2秒后自动刷新")
            tip_text.setWordWrap(True)
            tip_text.setStyleSheet("color: #2e7d32; padding: 8px;")
            tip_layout.addWidget(tip_text)
            
            layout.addWidget(tip_group)
        
        # 原始消息（可选）
        raw_message = self.occupy_result.get("raw_message", "")
        if raw_message and len(raw_message) > 20:
            msg_group = QGroupBox("详细消息")
            msg_layout = QVBoxLayout(msg_group)
            
            msg_text = QTextEdit()
            msg_text.setPlainText(raw_message)
            msg_text.setReadOnly(True)
            msg_text.setMaximumHeight(100)  # 增加消息框高度
            msg_layout.addWidget(msg_text)
            
            layout.addWidget(msg_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("确定")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(80)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
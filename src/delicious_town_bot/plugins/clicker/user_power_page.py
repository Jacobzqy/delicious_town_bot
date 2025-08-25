"""
用户厨力展示页面
显示用户餐厅信息、厨力属性、装备信息等
"""
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QCheckBox, QProgressBar, QTextEdit, QMessageBox, QFrame,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QSizePolicy, QInputDialog, QDialog
)
from PySide6.QtGui import QFont, QPixmap, QPalette, QColor

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.user_card import UserCardAction
from src.delicious_town_bot.plugins.clicker.equipment_inventory_dialog import EquipmentInventoryDialog


class PowerAttributeWidget(QWidget):
    """厨力属性展示组件"""
    
    def __init__(self):
        super().__init__()
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 总厨力显示
        self.total_power_frame = QFrame()
        self.total_power_frame.setObjectName("PowerFrame")
        total_layout = QVBoxLayout(self.total_power_frame)
        
        self.total_label = QLabel("总厨力")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.total_label.setFont(font)
        
        self.total_value = QLabel("0")
        self.total_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setBold(True)
        self.total_value.setFont(value_font)
        
        self.equipment_bonus = QLabel("装备加成: +0")
        self.equipment_bonus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        total_layout.addWidget(self.total_label)
        total_layout.addWidget(self.total_value)
        total_layout.addWidget(self.equipment_bonus)
        
        layout.addWidget(self.total_power_frame)
        
        # 属性详情
        self.attributes_group = QGroupBox("属性详情")
        self.attributes_layout = QGridLayout(self.attributes_group)
        
        # 创建属性标签
        self.attribute_widgets = {}
        attributes = [
            ("fire", "火候", "#ff6b6b"),
            ("cooking", "厨艺", "#4ecdc4"), 
            ("sword", "刀工", "#45b7d1"),
            ("season", "调味", "#96ceb4"),
            ("originality", "创意", "#feca57"),
            ("luck", "幸运", "#ff9ff3")
        ]
        
        for i, (attr_key, attr_name, color) in enumerate(attributes):
            row = i // 2
            col = (i % 2) * 3
            
            # 属性名
            name_label = QLabel(attr_name)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_font = QFont()
            name_font.setBold(True)
            name_label.setFont(name_font)
            
            # 基础值
            base_label = QLabel("0")
            base_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 总值（含装备）
            total_label = QLabel("0")
            total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            total_font = QFont()
            total_font.setBold(True)
            total_label.setFont(total_font)
            total_label.setStyleSheet(f"color: {color};")
            
            self.attributes_layout.addWidget(name_label, row * 2, col)
            self.attributes_layout.addWidget(QLabel("基础:"), row * 2 + 1, col)
            self.attributes_layout.addWidget(base_label, row * 2 + 1, col + 1)
            self.attributes_layout.addWidget(total_label, row * 2, col + 1)
            
            self.attribute_widgets[attr_key] = {
                "name": name_label,
                "base": base_label,
                "total": total_label
            }
        
        layout.addWidget(self.attributes_group)
    
    def update_power_data(self, power_data: Dict[str, Any]):
        """更新厨力数据显示"""
        if not power_data:
            return
        
        # 更新总厨力
        total_base = power_data.get("total_base", 0)
        total_with_equip = power_data.get("total_with_equip", 0)
        equipment_bonus = power_data.get("equipment_bonus", 0)
        
        self.total_value.setText(str(total_with_equip))
        self.equipment_bonus.setText(f"装备加成: +{equipment_bonus}")
        
        # 更新各属性
        attributes = power_data.get("attributes", {})
        for attr_key, widgets in self.attribute_widgets.items():
            attr_data = attributes.get(attr_key, {})
            base_value = attr_data.get("base", 0)
            total_value = attr_data.get("total", 0)
            
            widgets["base"].setText(str(base_value))
            widgets["total"].setText(str(total_value))


class RestaurantInfoWidget(QWidget):
    """餐厅信息展示组件"""
    
    def __init__(self):
        super().__init__()
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 餐厅基本信息
        info_group = QGroupBox("餐厅信息")
        info_layout = QGridLayout(info_group)
        
        # 创建信息标签
        self.info_labels = {}
        info_items = [
            ("name", "餐厅名称"),
            ("level", "餐厅等级"),
            ("star", "星级"),
            ("street_name", "所在街道"),
            ("cook_type", "菜系"),
            ("exp", "经验值"),
            ("gold", "金币"),
            ("prestige", "声望"),
            ("vip_level", "VIP等级"),
            ("seat_num", "座位数"),
            ("floor_num", "楼层数")
        ]
        
        for i, (key, label) in enumerate(info_items):
            row = i // 2
            col = (i % 2) * 2
            
            name_label = QLabel(f"{label}:")
            value_label = QLabel("--")
            
            info_layout.addWidget(name_label, row, col)
            info_layout.addWidget(value_label, row, col + 1)
            
            self.info_labels[key] = value_label
        
        layout.addWidget(info_group)
        
        # 收入信息
        income_group = QGroupBox("收入信息")
        income_layout = QGridLayout(income_group)
        
        self.income_labels = {}
        income_items = [
            ("gold_num", "上次收入(金币)"),
            ("exp_num", "上次收入(经验)"),
            ("last_time", "上次收获时间"),
            ("seat_num", "接待客人数"),
            ("nitpick_success_num", "成功挑剔数")
        ]
        
        for i, (key, label) in enumerate(income_items):
            name_label = QLabel(f"{label}:")
            value_label = QLabel("--")
            
            income_layout.addWidget(name_label, i, 0)
            income_layout.addWidget(value_label, i, 1)
            
            self.income_labels[key] = value_label
        
        layout.addWidget(income_group)
    
    def update_restaurant_data(self, restaurant_data: Dict[str, Any], income_data: Dict[str, Any] = None):
        """更新餐厅信息显示"""
        # 更新基本信息
        for key, label in self.info_labels.items():
            value = restaurant_data.get(key, "--")
            if key in ["exp", "gold", "prestige"] and isinstance(value, int):
                # 格式化大数字
                label.setText(f"{value:,}")
            else:
                label.setText(str(value))
        
        # 更新收入信息
        if income_data:
            for key, label in self.income_labels.items():
                value = income_data.get(key, "--")
                if key in ["gold_num", "exp_num"] and isinstance(value, int):
                    label.setText(f"{value:,}")
                else:
                    label.setText(str(value))


class TowerRecommendationWidget(QWidget):
    """厨塔推荐展示组件"""
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent_page = parent
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 厨塔推荐信息
        tower_group = QGroupBox("厨塔推荐")
        tower_layout = QVBoxLayout(tower_group)
        
        # 真实厨力显示
        self.real_power_frame = QFrame()
        self.real_power_frame.setObjectName("PowerFrame")
        real_power_layout = QHBoxLayout(self.real_power_frame)
        
        self.real_power_label = QLabel("真实厨力:")
        self.real_power_value = QLabel("未计算")
        self.real_power_value.setStyleSheet("font-weight: bold; color: #e67e22;")
        
        real_power_layout.addWidget(self.real_power_label)
        real_power_layout.addWidget(self.real_power_value)
        real_power_layout.addStretch()
        
        tower_layout.addWidget(self.real_power_frame)
        
        # 推荐层级显示
        self.recommendation_frame = QFrame()
        recommendation_layout = QVBoxLayout(self.recommendation_frame)
        
        self.best_floor_label = QLabel("推荐层级: 未分析")
        self.best_floor_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        
        self.max_safe_floor_label = QLabel("最高安全层级: 未分析")
        self.max_safe_floor_label.setStyleSheet("color: #3498db;")
        
        recommendation_layout.addWidget(self.best_floor_label)
        recommendation_layout.addWidget(self.max_safe_floor_label)
        
        tower_layout.addWidget(self.recommendation_frame)
        
        # 层级详情表格
        self.tower_table = QTableWidget()
        self.tower_table.setColumnCount(5)
        self.tower_table.setHorizontalHeaderLabels([
            "层级", "名称", "层级厨力", "厨力比值", "难度"
        ])
        self.tower_table.setMaximumHeight(150)
        self.tower_table.verticalHeader().setVisible(False)
        self.tower_table.setAlternatingRowColors(True)
        self.tower_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tower_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tower_table.horizontalHeader().setStretchLastSection(True)
        
        tower_layout.addWidget(self.tower_table)
        
        # 刷新按钮
        button_layout = QHBoxLayout()
        self.refresh_tower_btn = QPushButton("分析厨塔")
        self.refresh_tower_btn.setStyleSheet("QPushButton { background-color: #8e44ad; color: white; font-weight: bold; padding: 8px; }")
        self.refresh_tower_btn.clicked.connect(self.refresh_tower_recommendations)
        
        button_layout.addWidget(self.refresh_tower_btn)
        button_layout.addStretch()
        
        tower_layout.addLayout(button_layout)
        layout.addWidget(tower_group)
    
    def refresh_tower_recommendations(self):
        """刷新厨塔推荐"""
        if not self.parent_page:
            return
        
        account_id = self.parent_page.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请选择一个有效的账号！")
            return
        
        self.refresh_tower_btn.setEnabled(False)
        self.refresh_tower_btn.setText("分析中...")
        
        try:
            account = self.parent_page.manager.get_account(account_id)
            if not account or not account.key:
                raise Exception("账号无效或缺少Key")
            
            cookie_value = account.cookie if account.cookie else "123"
            cookie_dict = {"PHPSESSID": cookie_value}
            user_card_action = UserCardAction(key=account.key, cookie=cookie_dict)
            
            # 获取厨塔推荐
            result = user_card_action.get_tower_recommendations()
            
            if result.get("success"):
                self.update_tower_display(result)
                
                # 记录到日志
                if self.parent_page.log_widget:
                    user_power = result["user_power_analysis"]["total_real_power"]
                    best_floor = result["tower_recommendations"].get("best_floor")
                    floor_info = f"{best_floor['level']}层" if best_floor else "无推荐"
                    self.parent_page.log_widget.append(f"🏗️ 厨塔分析: {account.username} - 真实厨力 {user_power}，推荐 {floor_info}")
            else:
                error_msg = result.get("message", "分析失败")
                QMessageBox.critical(self, "分析失败", error_msg)
        
        except Exception as e:
            error_msg = f"厨塔分析失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
        
        finally:
            self.refresh_tower_btn.setEnabled(True)
            self.refresh_tower_btn.setText("分析厨塔")
    
    def update_tower_display(self, tower_data: Dict[str, Any]):
        """更新厨塔推荐显示"""
        power_analysis = tower_data.get("user_power_analysis", {})
        recommendations = tower_data.get("tower_recommendations", {})
        
        # 更新真实厨力
        real_power = power_analysis.get("total_real_power", 0)
        self.real_power_value.setText(f"{real_power}")
        
        # 更新推荐信息
        best_floor = recommendations.get("best_floor")
        max_safe_floor = recommendations.get("max_safe_floor")
        
        if best_floor:
            self.best_floor_label.setText(f"推荐层级: {best_floor['level']}层 - {best_floor['name']}")
        else:
            self.best_floor_label.setText("推荐层级: 暂无合适层级")
        
        if max_safe_floor:
            self.max_safe_floor_label.setText(f"最高安全层级: {max_safe_floor['level']}层 - {max_safe_floor['name']}")
        else:
            self.max_safe_floor_label.setText("最高安全层级: 无")
        
        # 更新层级表格
        self.update_tower_table(recommendations)
    
    def update_tower_table(self, recommendations: Dict[str, Any]):
        """更新厨塔层级表格"""
        self.tower_table.setRowCount(0)
        
        # 合并所有层级
        all_floors = []
        all_floors.extend(recommendations.get("safe_floors", []))
        all_floors.extend(recommendations.get("challenge_floors", []))
        all_floors.extend(recommendations.get("impossible_floors", []))
        
        # 按层级排序
        all_floors.sort(key=lambda x: x["level"])
        
        for floor in all_floors:
            row = self.tower_table.rowCount()
            self.tower_table.insertRow(row)
            
            # 层级
            level_item = QTableWidgetItem(str(floor["level"]))
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tower_table.setItem(row, 0, level_item)
            
            # 名称
            name_item = QTableWidgetItem(floor["name"])
            self.tower_table.setItem(row, 1, name_item)
            
            # 层级厨力
            power_item = QTableWidgetItem(str(floor["floor_power"]))
            power_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tower_table.setItem(row, 2, power_item)
            
            # 厨力比值
            ratio_item = QTableWidgetItem(f"{floor['power_ratio']:.2f}")
            ratio_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tower_table.setItem(row, 3, ratio_item)
            
            # 难度
            difficulty = self.get_difficulty_text(floor, recommendations)
            difficulty_item = QTableWidgetItem(difficulty)
            difficulty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 设置颜色
            if "✅" in difficulty:
                difficulty_item.setBackground(QColor(200, 255, 200))  # 淡绿色
            elif "⚡" in difficulty:
                difficulty_item.setBackground(QColor(255, 255, 200))  # 淡黄色
            elif "❌" in difficulty:
                difficulty_item.setBackground(QColor(255, 200, 200))  # 淡红色
            
            self.tower_table.setItem(row, 4, difficulty_item)
    
    def get_difficulty_text(self, floor: Dict[str, Any], recommendations: Dict[str, Any]) -> str:
        """获取难度文本"""
        if floor in recommendations.get("safe_floors", []):
            return "✅ 安全"
        elif floor in recommendations.get("challenge_floors", []):
            return "⚡ 挑战"
        elif floor in recommendations.get("impossible_floors", []):
            return "❌ 困难"
        else:
            return "❓ 未知"


class EquipmentWidget(QWidget):
    """装备信息展示组件"""
    
    def __init__(self, parent=None):
        super().__init__()
        self.parent_page = parent
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 装备列表
        equipment_group = QGroupBox("装备信息")
        equipment_layout = QVBoxLayout(equipment_group)
        
        self.equipment_table = QTableWidget()
        self.equipment_table.setColumnCount(9)
        self.equipment_table.setHorizontalHeaderLabels([
            "部位", "装备名称", "强化", "火候", "厨艺", "刀工", "调味", "创意", "幸运"
        ])
        
        # 设置表格属性
        self.equipment_table.verticalHeader().setVisible(False)
        self.equipment_table.setAlternatingRowColors(True)
        self.equipment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.equipment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.equipment_table.horizontalHeader().setStretchLastSection(True)
        
        equipment_layout.addWidget(self.equipment_table)
        layout.addWidget(equipment_group)
        
        # 装备属性汇总
        summary_group = QGroupBox("装备属性汇总")
        summary_layout = QGridLayout(summary_group)
        
        self.summary_labels = {}
        attributes = ["fire", "cooking", "sword", "season", "originality", "luck"]
        attr_names = ["火候", "厨艺", "刀工", "调味", "创意", "幸运"]
        
        for i, (attr, name) in enumerate(zip(attributes, attr_names)):
            row = i // 3
            col = (i % 3) * 2
            
            name_label = QLabel(f"{name}:")
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            summary_layout.addWidget(name_label, row, col)
            summary_layout.addWidget(value_label, row, col + 1)
            
            self.summary_labels[attr] = value_label
        
        layout.addWidget(summary_group)
        
        # 宝石信息组
        gems_group = QGroupBox("宝石信息")
        gems_layout = QVBoxLayout(gems_group)
        
        # 宝石统计
        gems_stats_layout = QHBoxLayout()
        self.inventory_gems_label = QLabel("仓库宝石: 0")
        self.equipped_gems_label = QLabel("已镶嵌: 0")
        self.total_gems_label = QLabel("总计: 0")
        
        gems_stats_layout.addWidget(self.inventory_gems_label)
        gems_stats_layout.addWidget(self.equipped_gems_label)
        gems_stats_layout.addWidget(self.total_gems_label)
        gems_stats_layout.addStretch()
        
        gems_layout.addLayout(gems_stats_layout)
        
        # 宝石管理按钮
        gems_btn_layout = QHBoxLayout()
        self.view_gems_btn = QPushButton("查看宝石库存")
        self.view_gems_btn.setStyleSheet("QPushButton { background-color: #7952b3; color: white; font-weight: bold; padding: 6px; }")
        self.view_gems_btn.clicked.connect(self.view_gems_inventory)
        
        self.manage_gems_btn = QPushButton("宝石管理")
        self.manage_gems_btn.setStyleSheet("QPushButton { background-color: #fd7e14; color: white; font-weight: bold; padding: 6px; }")
        self.manage_gems_btn.clicked.connect(self.manage_gems)
        
        gems_btn_layout.addWidget(self.view_gems_btn)
        gems_btn_layout.addWidget(self.manage_gems_btn)
        gems_btn_layout.addStretch()
        
        gems_layout.addLayout(gems_btn_layout)
        layout.addWidget(gems_group)
        
        # 厨具管理按钮组
        management_group = QGroupBox("厨具管理")
        management_layout = QHBoxLayout(management_group)
        
        self.buy_novice_btn = QPushButton("购买见习装备")
        self.buy_novice_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px; }")
        
        self.view_equipment_btn = QPushButton("查看厨具库存")
        self.view_equipment_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; padding: 8px; }")
        
        self.buy_intermediate_btn = QPushButton("购买中厨装备")
        self.buy_intermediate_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-weight: bold; padding: 8px; }")
        
        self.auto_process_btn = QPushButton("自动处理见习装备")
        self.auto_process_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 8px; }")
        
        # 按钮连接将在父类中设置
        
        self.novice_count_label = QLabel("见习装备: 未统计")
        
        # 操作反馈标签
        self.operation_feedback_label = QLabel("准备就绪")
        self.operation_feedback_label.setStyleSheet("color: #666; font-size: 12px;")
        self.operation_feedback_label.setWordWrap(True)
        
        # 第一行按钮
        first_row_layout = QHBoxLayout()
        first_row_layout.addWidget(self.buy_novice_btn)
        first_row_layout.addWidget(self.buy_intermediate_btn)
        first_row_layout.addWidget(self.view_equipment_btn)
        
        # 第二行按钮
        second_row_layout = QHBoxLayout()
        second_row_layout.addWidget(self.auto_process_btn)
        second_row_layout.addWidget(self.novice_count_label)
        second_row_layout.addStretch()
        
        management_layout.addLayout(first_row_layout)
        management_layout.addLayout(second_row_layout)
        
        layout.addWidget(management_group)
        
        # 一键强化功能组
        enhance_group = QGroupBox("一键强化")
        enhance_layout = QVBoxLayout(enhance_group)
        
        # 材料信息显示
        material_info_layout = QHBoxLayout()
        self.enhance_stone_label = QLabel("强化石: 0")
        self.equipment_essence_label = QLabel("厨具精华: 0") 
        self.refresh_materials_btn = QPushButton("刷新材料")
        self.refresh_materials_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; padding: 4px 8px; }")
        self.refresh_materials_btn.clicked.connect(self.refresh_enhance_materials)
        
        material_info_layout.addWidget(self.enhance_stone_label)
        material_info_layout.addWidget(self.equipment_essence_label)
        material_info_layout.addWidget(self.refresh_materials_btn)
        material_info_layout.addStretch()
        enhance_layout.addLayout(material_info_layout)
        
        # 强化控制区域
        enhance_control_layout = QHBoxLayout()
        enhance_control_layout.addWidget(QLabel("目标强化等级:"))
        
        self.target_level_combo = QComboBox()
        self.target_level_combo.addItems(["+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8", "+9", "+10"])
        self.target_level_combo.setCurrentText("+5")
        enhance_control_layout.addWidget(self.target_level_combo)
        
        self.batch_enhance_btn = QPushButton("一键强化所有装备")
        self.batch_enhance_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; }")
        self.batch_enhance_btn.clicked.connect(self.start_batch_enhance)
        enhance_control_layout.addWidget(self.batch_enhance_btn)
        
        enhance_control_layout.addStretch()
        enhance_layout.addLayout(enhance_control_layout)
        
        # 强化进度显示
        self.enhance_progress_label = QLabel("准备强化")
        self.enhance_progress_label.setStyleSheet("color: #666; font-size: 12px;")
        self.enhance_progress_label.setWordWrap(True)
        enhance_layout.addWidget(self.enhance_progress_label)
        
        layout.addWidget(enhance_group)
        
        # 操作反馈区域
        feedback_layout = QVBoxLayout()
        feedback_layout.addWidget(QLabel("最近操作:"))
        feedback_layout.addWidget(self.operation_feedback_label)
        layout.addLayout(feedback_layout)
    
    def update_equipment_data(self, equipment_data: List[Dict[str, Any]], summary_data: Dict[str, Any] = None):
        """更新装备信息显示"""
        # 清空表格
        self.equipment_table.setRowCount(0)
        
        # 填充装备信息
        for equipment in equipment_data:
            row = self.equipment_table.rowCount()
            self.equipment_table.insertRow(row)
            
            # 部位名称
            part_name = equipment.get("part_name", "")
            part_item = QTableWidgetItem(part_name)
            part_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.equipment_table.setItem(row, 0, part_item)
            
            # 装备名称
            name = equipment.get("name", "")
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(name)  # 鼠标悬停显示完整名称
            self.equipment_table.setItem(row, 1, name_item)
            
            # 强化等级
            strengthen = equipment.get("strengthen_level", 0)
            strengthen_name = equipment.get("strengthen_name", "")
            strengthen_text = f"+{strengthen} {strengthen_name}" if strengthen > 0 else "--"
            strengthen_item = QTableWidgetItem(strengthen_text)
            strengthen_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.equipment_table.setItem(row, 2, strengthen_item)
            
            # 属性值
            total_attrs = equipment.get("total_attributes", {})
            attributes = ["fire", "cooking", "sword", "season", "originality", "luck"]
            for i, attr in enumerate(attributes):
                value = total_attrs.get(attr, 0)
                attr_item = QTableWidgetItem(str(value))
                attr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.equipment_table.setItem(row, i + 3, attr_item)
        
        # 更新属性汇总
        if summary_data:
            total_attrs = summary_data.get("total_attributes", {})
            for attr, label in self.summary_labels.items():
                value = total_attrs.get(attr, 0)
                label.setText(str(value))

    def update_gems_data(self, gems_data: Dict[str, Any]):
        """更新宝石信息显示"""
        if gems_data.get("success"):
            summary = gems_data.get("summary", {})
            inventory_count = summary.get("total_inventory_gems", 0)
            equipped_count = summary.get("total_equipped_gems", 0)
            total_count = inventory_count + equipped_count
            
            self.inventory_gems_label.setText(f"仓库宝石: {inventory_count}")
            self.equipped_gems_label.setText(f"已镶嵌: {equipped_count}")
            self.total_gems_label.setText(f"总计: {total_count}")
        else:
            self.inventory_gems_label.setText("仓库宝石: 获取失败")
            self.equipped_gems_label.setText("已镶嵌: 获取失败")
            self.total_gems_label.setText("总计: 获取失败")

    def view_gems_inventory(self):
        """查看宝石库存"""
        if not self.parent_page:
            return
            
        current_account = self.parent_page.get_current_account()
        if not current_account:
            QMessageBox.warning(self, "提示", "请先选择账号")
            return
        
        try:
            from src.delicious_town_bot.actions.depot import DepotAction
            
            cookie_dict = {"PHPSESSID": current_account.cookie} if current_account.cookie else {}
            depot_action = DepotAction(key=current_account.key, cookie=cookie_dict)
            
            # 获取宝石信息
            gems_result = depot_action.get_all_gems()
            
            if gems_result.get("success"):
                inventory_gems = gems_result.get("inventory_gems", [])
                
                # 创建宝石库存对话框
                dialog = GemsInventoryDialog(inventory_gems, self)
                dialog.exec()
            else:
                QMessageBox.warning(self, "错误", f"获取宝石信息失败: {gems_result.get('message', '未知错误')}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看宝石库存失败: {str(e)}")

    def manage_gems(self):
        """宝石管理功能"""
        if not self.parent_page:
            return
            
        current_account = self.parent_page.get_current_account()
        if not current_account:
            QMessageBox.warning(self, "提示", "请先选择账号")
            return
        
        try:
            # 创建宝石管理对话框
            dialog = GemsManagementDialog(current_account, self)
            dialog.exec()
            
            # 刷新宝石数据
            self.parent_page.refresh_gems_data()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开宝石管理失败: {str(e)}")

    def refresh_enhance_materials(self):
        """刷新强化材料数量"""
        if not self.parent_page:
            return
            
        current_account = self.parent_page.get_current_account()
        if not current_account:
            self.enhance_stone_label.setText("强化石: 未选择账号")
            self.equipment_essence_label.setText("厨具精华: 未选择账号")
            return
        
        self.refresh_materials_btn.setEnabled(False)
        self.refresh_materials_btn.setText("查询中...")
        
        try:
            from src.delicious_town_bot.actions.depot import DepotAction
            from src.delicious_town_bot.constants import ItemType
            
            cookie_dict = {"PHPSESSID": current_account.cookie} if current_account.cookie else {}
            depot_action = DepotAction(key=current_account.key, cookie=cookie_dict)
            
            # 获取材料类物品
            materials = depot_action.get_all_items(ItemType.MATERIALS)
            
            enhance_stone_count = 0
            equipment_essence_count = 0
            
            # 遍历材料物品，统计强化相关材料
            for item in materials:
                item_name = item.get("goods_name", "")
                item_num = int(item.get("num", 0))
                
                if "强化石" in item_name:
                    enhance_stone_count += item_num
                elif "厨具精华" in item_name:
                    equipment_essence_count += item_num
            
            # 更新显示
            self.enhance_stone_label.setText(f"强化石: {enhance_stone_count}")
            self.equipment_essence_label.setText(f"厨具精华: {equipment_essence_count}")
            
        except Exception as e:
            self.enhance_stone_label.setText("强化石: 查询失败")
            self.equipment_essence_label.setText("厨具精华: 查询失败")
            print(f"[Warning] 获取强化材料失败: {e}")
        
        finally:
            self.refresh_materials_btn.setEnabled(True)
            self.refresh_materials_btn.setText("刷新材料")

    def start_batch_enhance(self):
        """开始批量强化"""
        if not self.parent_page:
            return
            
        current_account = self.parent_page.get_current_account()
        if not current_account:
            QMessageBox.warning(self, "提示", "请先选择账号")
            return
        
        target_level = int(self.target_level_combo.currentText().replace("+", ""))
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认批量强化",
            f"确定要将所有已装备厨具强化到 +{target_level} 级吗？\n\n"
            "⚠️ 注意事项：\n"
            "• 强化可能失败，失败会消耗材料但不提升等级\n"
            "• 会自动跳过已达到或超过目标等级的装备\n"
            "• 材料不足时会停止强化\n"
            "• 此过程可能需要较长时间\n\n"
            "建议先刷新材料数量确认充足！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始批量强化
        self.batch_enhance_btn.setEnabled(False)
        self.batch_enhance_btn.setText("强化中...")
        self.enhance_progress_label.setText("正在获取装备信息...")
        
        try:
            # 执行批量强化
            result = self.execute_batch_enhance(current_account, target_level)
            
            # 显示结果
            self.show_batch_enhance_result(result)
            
        except Exception as e:
            error_msg = f"批量强化失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.enhance_progress_label.setText(f"强化失败: {error_msg}")
        
        finally:
            self.batch_enhance_btn.setEnabled(True)
            self.batch_enhance_btn.setText("一键强化所有装备")

    def execute_batch_enhance(self, account, target_level: int) -> Dict[str, Any]:
        """执行批量强化"""
        from src.delicious_town_bot.actions.user_card import UserCardAction
        import time
        
        cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else {}
        user_card_action = UserCardAction(key=account.key, cookie=cookie_dict)
        
        # 获取当前装备信息
        equipment_result = user_card_action.get_equipment_summary()
        if not equipment_result.get("success"):
            raise Exception("获取装备信息失败")
        
        equipment_list = equipment_result.get("equipment_list", [])
        
        # 调试：打印所有装备信息
        print(f"[Debug] 获取到 {len(equipment_list)} 件装备:")
        for i, equip in enumerate(equipment_list):
            print(f"[Debug]   {i+1}. {equip.get('name', '未知')} (ID:{equip.get('id', 'N/A')})")
            print(f"[Debug]      部位: {equip.get('part_name', '未知')}")
            print(f"[Debug]      强化等级: +{equip.get('strengthen_num', 0)}")
            print(f"[Debug]      是否装备: {equip.get('is_use', False)}")
        
        # 筛选需要强化的装备（只强化已装备的）
        equipment_to_enhance = []
        for equip in equipment_list:
            is_equipped = equip.get("is_use", False)
            current_level = equip.get("strengthen_num", 0)
            
            print(f"[Debug] 检查装备 {equip.get('name', '未知')}:")
            print(f"[Debug]   is_use: {is_equipped}")
            print(f"[Debug]   strengthen_num: {current_level}")
            print(f"[Debug]   目标等级: {target_level}")
            
            if is_equipped:  # 只处理已装备的
                print(f"[Debug]   ✅ 已装备")
                if current_level < target_level:
                    print(f"[Debug]   ✅ 需要强化: +{current_level} → +{target_level}")
                    equipment_to_enhance.append({
                        "id": equip.get("id"),
                        "name": equip.get("name", "未知装备"),
                        "part_name": equip.get("part_name", ""),
                        "current_level": current_level,
                        "need_enhance": target_level - current_level
                    })
                else:
                    print(f"[Debug]   ⏭️ 已达到目标等级，跳过")
            else:
                print(f"[Debug]   📦 仓库中装备，跳过")
        
        print(f"[Debug] 筛选结果: {len(equipment_to_enhance)} 件装备需要强化")
        
        if not equipment_to_enhance:
            return {
                "success": True,
                "message": "所有已装备厨具都已达到或超过目标强化等级",
                "total_equipment": 0,
                "enhanced_equipment": [],
                "failed_equipment": [],
                "skipped_equipment": []
            }
        
        result = {
            "success": False,
            "message": "",
            "total_equipment": len(equipment_to_enhance),
            "enhanced_equipment": [],
            "failed_equipment": [],
            "skipped_equipment": [],
            "total_attempts": 0,
            "successful_attempts": 0
        }
        
        self.enhance_progress_label.setText(f"找到 {len(equipment_to_enhance)} 件装备需要强化")
        
        # 逐个装备进行强化
        for i, equip in enumerate(equipment_to_enhance):
            equip_name = f"{equip['part_name']}{equip['name']}"
            self.enhance_progress_label.setText(
                f"强化进度: {i+1}/{len(equipment_to_enhance)} - {equip_name}"
            )
            
            enhanced_levels = 0
            failed_attempts = 0
            current_level = equip["current_level"]
            
            # 强化到目标等级
            while current_level < target_level:
                result["total_attempts"] += 1
                
                # 执行单次强化
                enhance_result = user_card_action.intensify_equipment(equip["id"])
                
                if enhance_result.get("success"):
                    current_level += 1
                    enhanced_levels += 1
                    result["successful_attempts"] += 1
                    self.enhance_progress_label.setText(
                        f"强化进度: {i+1}/{len(equipment_to_enhance)} - {equip_name} +{current_level}"
                    )
                else:
                    failed_attempts += 1
                    # 连续失败5次就跳过这个装备
                    if failed_attempts >= 5:
                        result["failed_equipment"].append({
                            "name": equip_name,
                            "reason": "连续失败5次",
                            "final_level": current_level,
                            "failed_attempts": failed_attempts
                        })
                        break
                
                # 强化间隔，避免请求过快
                time.sleep(0.5)
            
            # 记录装备强化结果
            if current_level >= target_level:
                result["enhanced_equipment"].append({
                    "name": equip_name,
                    "initial_level": equip["current_level"],
                    "final_level": current_level,
                    "enhanced_levels": enhanced_levels,
                    "failed_attempts": failed_attempts
                })
            elif failed_attempts < 5:
                result["skipped_equipment"].append({
                    "name": equip_name,
                    "reason": "其他原因",
                    "final_level": current_level
                })
        
        # 生成结果消息
        successful_count = len(result["enhanced_equipment"])
        failed_count = len(result["failed_equipment"])
        
        if failed_count == 0 and successful_count > 0:
            result["success"] = True
            result["message"] = f"✅ 批量强化完成！成功强化 {successful_count} 件装备到 +{target_level}"
        elif successful_count > 0:
            result["success"] = True
            result["message"] = f"⚠️ 批量强化部分完成：成功 {successful_count} 件，失败 {failed_count} 件"
        else:
            result["message"] = f"❌ 批量强化失败：{failed_count} 件装备强化失败"
        
        self.enhance_progress_label.setText("强化完成")
        return result

    def show_batch_enhance_result(self, result: Dict[str, Any]):
        """显示批量强化结果"""
        enhanced = result.get("enhanced_equipment", [])
        failed = result.get("failed_equipment", [])
        total_attempts = result.get("total_attempts", 0)
        successful_attempts = result.get("successful_attempts", 0)
        
        # 构建详细结果文本
        details = [result.get("message", "")]
        details.append("")
        details.append(f"📊 强化统计:")
        details.append(f"   • 总强化次数: {total_attempts}")
        details.append(f"   • 成功次数: {successful_attempts}")
        details.append(f"   • 成功率: {(successful_attempts/max(total_attempts, 1)*100):.1f}%")
        details.append("")
        
        if enhanced:
            details.append(f"✅ 成功强化装备 ({len(enhanced)} 件):")
            for equip in enhanced:
                details.append(
                    f"   • {equip['name']}: +{equip['initial_level']} → +{equip['final_level']} "
                    f"(强化{equip['enhanced_levels']}次，失败{equip['failed_attempts']}次)"
                )
        
        if failed:
            details.append("")
            details.append(f"❌ 强化失败装备 ({len(failed)} 件):")
            for equip in failed:
                details.append(f"   • {equip['name']}: 最终等级 +{equip['final_level']} ({equip['reason']})")
        
        message_text = "\n".join(details)
        
        # 显示结果对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("批量强化结果")
        msg_box.setText(result.get("message", ""))
        msg_box.setDetailedText(message_text)
        
        if result.get("success"):
            msg_box.setIcon(QMessageBox.Icon.Information)
        else:
            msg_box.setIcon(QMessageBox.Icon.Warning)
        
        msg_box.exec()
        
        # 更新进度显示
        if result.get("success"):
            self.enhance_progress_label.setText(f"✅ 强化完成: {len(enhanced)} 件成功")
        else:
            self.enhance_progress_label.setText(f"⚠️ 强化结束: {len(enhanced)} 件成功, {len(failed)} 件失败")


class GemsInventoryDialog(QMessageBox):
    """宝石库存查看对话框"""
    
    def __init__(self, gems_data: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("宝石库存")
        self.setIcon(QMessageBox.Icon.Information)
        
        # 构建宝石信息文本
        if not gems_data:
            text = "暂无宝石"
        else:
            text_parts = ["宝石库存详情:\n"]
            for gem in gems_data:
                name = gem.get("goods_name", "未知宝石")
                num = gem.get("num", 1)
                desc = gem.get("goods_description", "无描述")
                text_parts.append(f"• {name} x{num}")
                if desc and desc != "无描述":
                    text_parts.append(f"  {desc}")
                text_parts.append("")
            
            text = "\n".join(text_parts)
        
        self.setText(text)
        self.setStandardButtons(QMessageBox.StandardButton.Ok)


class GemsManagementDialog(QDialog):
    """完整的宝石管理对话框"""
    
    def __init__(self, account, parent=None):
        super().__init__(parent)
        self.account = account
        self.parent_page = parent
        
        # 初始化数据存储
        self.equipment_list = []
        self.gems_list = []
        self.current_equipment = None
        
        self.setWindowTitle("宝石管理")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.resize(1000, 700)
        
        self.setupUI()
        self.load_data()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("宝石管理")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.load_data)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(refresh_btn)
        layout.addLayout(title_layout)
        
        # 主内容区域 - 分为四列
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：装备列表
        self.setup_equipment_panel(main_splitter)
        
        # 中间：装备详情和孔位
        self.setup_equipment_detail_panel(main_splitter)
        
        # 右侧上：宝石库存
        self.setup_gems_panel(main_splitter)
        
        # 右侧下：精炼和精华材料
        self.setup_refining_panel(main_splitter)
        
        # 设置分割比例
        main_splitter.setStretchFactor(0, 1)  # 装备列表
        main_splitter.setStretchFactor(1, 2)  # 装备详情
        main_splitter.setStretchFactor(2, 1)  # 宝石库存
        main_splitter.setStretchFactor(3, 1)  # 精炼面板
        
        layout.addWidget(main_splitter)
        
        # 底部操作区域
        self.setup_bottom_panel(layout)
        
    def setup_equipment_panel(self, parent_splitter):
        """设置装备列表面板"""
        equipment_widget = QWidget()
        equipment_layout = QVBoxLayout(equipment_widget)
        
        equipment_group = QGroupBox("我的装备")
        group_layout = QVBoxLayout(equipment_group)
        
        # 装备列表
        self.equipment_table = QTableWidget()
        self.equipment_table.setColumnCount(3)
        self.equipment_table.setHorizontalHeaderLabels(["部位", "装备名称", "孔位状态"])
        self.equipment_table.verticalHeader().setVisible(False)
        self.equipment_table.setAlternatingRowColors(True)
        self.equipment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.equipment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.equipment_table.horizontalHeader().setStretchLastSection(True)
        self.equipment_table.itemSelectionChanged.connect(self.on_equipment_selected)
        
        group_layout.addWidget(self.equipment_table)
        equipment_layout.addWidget(equipment_group)
        
        parent_splitter.addWidget(equipment_widget)
        
    def setup_equipment_detail_panel(self, parent_splitter):
        """设置装备详情面板"""
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        
        # 装备信息
        info_group = QGroupBox("装备信息")
        info_layout = QGridLayout(info_group)
        
        self.equip_name_label = QLabel("请选择装备")
        self.equip_name_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.equip_strengthen_label = QLabel("")
        self.equip_properties_label = QLabel("")
        
        info_layout.addWidget(QLabel("装备名称:"), 0, 0)
        info_layout.addWidget(self.equip_name_label, 0, 1)
        info_layout.addWidget(QLabel("强化等级:"), 1, 0)
        info_layout.addWidget(self.equip_strengthen_label, 1, 1)
        info_layout.addWidget(QLabel("基础属性:"), 2, 0)
        info_layout.addWidget(self.equip_properties_label, 2, 1)
        
        detail_layout.addWidget(info_group)
        
        # 孔位管理
        holes_group = QGroupBox("孔位管理")
        holes_layout = QVBoxLayout(holes_group)
        
        # 孔位状态显示
        holes_status_layout = QHBoxLayout()
        self.holes_status_label = QLabel("孔位状态: 0/0")
        self.add_hole_btn = QPushButton("购买并打孔")
        self.add_hole_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; padding: 6px; }")
        self.add_hole_btn.clicked.connect(self.add_hole_to_equipment)
        
        holes_status_layout.addWidget(self.holes_status_label)
        holes_status_layout.addStretch()
        holes_status_layout.addWidget(self.add_hole_btn)
        holes_layout.addLayout(holes_status_layout)
        
        # 孔位详情表格
        self.holes_table = QTableWidget()
        self.holes_table.setColumnCount(4)
        self.holes_table.setHorizontalHeaderLabels(["孔位", "宝石", "属性加成", "操作"])
        self.holes_table.verticalHeader().setVisible(False)
        self.holes_table.setAlternatingRowColors(True)
        self.holes_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.holes_table.horizontalHeader().setStretchLastSection(True)
        
        holes_layout.addWidget(self.holes_table)
        detail_layout.addWidget(holes_group)
        
        parent_splitter.addWidget(detail_widget)
        
    def setup_gems_panel(self, parent_splitter):
        """设置宝石库存面板"""
        gems_widget = QWidget()
        gems_layout = QVBoxLayout(gems_widget)
        
        gems_group = QGroupBox("宝石库存")
        group_layout = QVBoxLayout(gems_group)
        
        # 宝石统计
        stats_layout = QHBoxLayout()
        self.gems_count_label = QLabel("总计: 0 个宝石")
        stats_layout.addWidget(self.gems_count_label)
        stats_layout.addStretch()
        group_layout.addLayout(stats_layout)
        
        # 宝石列表
        self.gems_table = QTableWidget()
        self.gems_table.setColumnCount(3)
        self.gems_table.setHorizontalHeaderLabels(["宝石名称", "数量", "属性"])
        self.gems_table.verticalHeader().setVisible(False)
        self.gems_table.setAlternatingRowColors(True)
        self.gems_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.gems_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.gems_table.horizontalHeader().setStretchLastSection(True)
        
        group_layout.addWidget(self.gems_table)
        gems_layout.addWidget(gems_group)
        
        parent_splitter.addWidget(gems_widget)
        
    def setup_refining_panel(self, parent_splitter):
        """设置精炼和精华材料面板"""
        refining_widget = QWidget()
        refining_layout = QVBoxLayout(refining_widget)
        
        # 精华材料组
        essences_group = QGroupBox("精华材料库存")
        essences_layout = QVBoxLayout(essences_group)
        
        # 精华材料显示
        self.essences_labels = {}
        essences_data = [
            ("原石精华", "原石精华"),
            ("魔石精华", "魔石精华"),
            ("灵石精华", "灵石精华"),
            ("神石精华", "神石精华"),
            ("原玉精华", "原玉精华"),
            ("魔玉精华", "魔玉精华"),
            ("灵玉精华", "灵玉精华"),
            ("神玉精华", "神玉精华")
        ]
        
        for essence_key, essence_name in essences_data:
            essence_layout = QHBoxLayout()
            name_label = QLabel(f"{essence_name}:")
            name_label.setMinimumWidth(80)
            
            count_label = QLabel("0")
            count_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            count_label.setMinimumWidth(40)
            
            # 购买按钮
            buy_btn = QPushButton("购买")
            buy_btn.setMaximumWidth(50)
            buy_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-size: 11px; padding: 2px; }")
            buy_btn.clicked.connect(lambda checked, key=essence_key: self.buy_essence_material(key))
            
            essence_layout.addWidget(name_label)
            essence_layout.addWidget(count_label)
            essence_layout.addWidget(buy_btn)
            essence_layout.addStretch()
            
            essences_layout.addLayout(essence_layout)
            self.essences_labels[essence_key] = count_label
        
        refining_layout.addWidget(essences_group)
        
        # 宝石精炼组
        refining_group = QGroupBox("宝石精炼")
        refining_group_layout = QVBoxLayout(refining_group)
        
        # 精炼选择
        refining_select_layout = QHBoxLayout()
        refining_select_layout.addWidget(QLabel("选择宝石:"))
        
        self.refining_gem_combo = QComboBox()
        self.refining_gem_combo.setMinimumWidth(150)
        refining_select_layout.addWidget(self.refining_gem_combo)
        refining_select_layout.addStretch()
        
        refining_group_layout.addLayout(refining_select_layout)
        
        # 精炼按钮区域
        refining_buttons_layout = QHBoxLayout()
        
        self.normal_refining_btn = QPushButton("普通精炼")
        self.normal_refining_btn.setStyleSheet("QPushButton { background-color: #f39c12; color: white; font-weight: bold; padding: 6px; }")
        self.normal_refining_btn.clicked.connect(lambda: self.refine_gem(is_fixed=False))
        
        self.fixed_refining_btn = QPushButton("固定精炼")
        self.fixed_refining_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; font-weight: bold; padding: 6px; }")
        self.fixed_refining_btn.clicked.connect(lambda: self.refine_gem(is_fixed=True))
        
        refining_buttons_layout.addWidget(self.normal_refining_btn)
        refining_buttons_layout.addWidget(self.fixed_refining_btn)
        
        refining_group_layout.addLayout(refining_buttons_layout)
        
        # 精炼结果显示
        self.refining_result_label = QLabel("选择宝石进行精炼")
        self.refining_result_label.setStyleSheet("color: #666; padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        self.refining_result_label.setWordWrap(True)
        refining_group_layout.addWidget(self.refining_result_label)
        
        refining_layout.addWidget(refining_group)
        
        parent_splitter.addWidget(refining_widget)
        
    def setup_bottom_panel(self, parent_layout):
        """设置底部操作面板"""
        bottom_layout = QHBoxLayout()
        
        # 镶嵌按钮
        self.install_gem_btn = QPushButton("镶嵌选中宝石")
        self.install_gem_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px; }")
        self.install_gem_btn.clicked.connect(self.install_selected_gem)
        
        # 状态标签
        self.status_label = QLabel("请选择装备和宝石进行操作")
        self.status_label.setStyleSheet("color: #666; padding: 8px;")
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; padding: 8px; }")
        close_btn.clicked.connect(self.close)
        
        bottom_layout.addWidget(self.install_gem_btn)
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        
        parent_layout.addLayout(bottom_layout)

    def load_data(self):
        """加载装备和宝石数据"""
        self.status_label.setText("正在加载数据...")
        
        try:
            # 获取账号信息
            cookie_dict = {"PHPSESSID": self.account.cookie} if self.account.cookie else {}
            
            # 加载装备数据 - 改用get_equipment_list获取装备库存
            from src.delicious_town_bot.actions.user_card import UserCardAction
            user_card_action = UserCardAction(key=self.account.key, cookie=cookie_dict)
            
            self.equipment_list = []
            print("[Debug] 宝石管理 - 开始获取装备库存数据")
            
            # 获取所有部位的装备 (1-5: 铲子、刀具、锅具、调料瓶、厨师帽)
            for part_type in range(1, 6):
                part_names = {1: "铲子", 2: "刀具", 3: "锅具", 4: "调料瓶", 5: "厨师帽"}
                part_name = part_names[part_type]
                
                print(f"[Debug] 获取{part_name}装备...")
                equipment_result = user_card_action.get_equipment_list(part_type=part_type, page=1)
                
                if equipment_result.get("success"):
                    equipment_list = equipment_result.get("equipment_list", [])
                    print(f"[Debug] {part_name}装备数量: {len(equipment_list)}")
                    
                    for i, equip in enumerate(equipment_list):
                        equip_name = equip.get("name", "未知装备")
                        hole_raw = equip.get("hole")
                        hole_count = int(hole_raw) if hole_raw is not None else 0
                        equip_id = equip.get("id")
                        is_use = equip.get("is_use", False)
                        
                        # 调试每个装备的信息
                        print(f"[Debug]   装备 {i+1}: {equip_name}")
                        print(f"[Debug]     ID: {equip_id}")
                        print(f"[Debug]     孔位: {hole_raw} -> {hole_count}")
                        print(f"[Debug]     是否装备: {is_use}")
                        
                        if hole_count > 0:  # 只显示有孔位的装备
                            # 添加必要的字段以保持兼容性
                            equip_data = equip.copy()
                            equip_data["goods_name"] = equip.get("name", "未知装备")
                            self.equipment_list.append(equip_data)
                            print(f"[Debug]     ✅ 添加到装备列表")
                        else:
                            print(f"[Debug]     ❌ 跳过（无孔位）")
                else:
                    print(f"[Debug] {part_name}装备获取失败: {equipment_result.get('message')}")
            
            print(f"[Debug] 总筛选后装备数量: {len(self.equipment_list)}")
            self.update_equipment_table()
            
            # 加载宝石数据 - 使用正确的宝石获取方法
            from src.delicious_town_bot.actions.gem_refining import GemRefiningAction
            gem_refining_action = GemRefiningAction(key=self.account.key, cookie=cookie_dict)
            gems_result = gem_refining_action.get_gem_list()
            
            if gems_result.get("success"):
                self.gems_list = gems_result.get("gems", [])
                print(f"[Debug] 成功加载 {len(self.gems_list)} 个宝石")
                self.update_gems_table()
            else:
                print(f"[Debug] 宝石获取失败: {gems_result.get('message')}")
                self.gems_list = []
                self.update_gems_table()
            
            # 加载精华材料数据
            from src.delicious_town_bot.actions.depot import DepotAction
            depot_action = DepotAction(key=self.account.key, cookie=cookie_dict)
            self.load_essence_materials(depot_action)
            
            # 加载可精炼宝石到下拉框
            self.update_refining_gems_combo()
            
            self.status_label.setText("数据加载完成")
            
        except Exception as e:
            self.status_label.setText(f"加载数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")

    def update_equipment_table(self):
        """更新装备列表表格"""
        self.equipment_table.setRowCount(len(self.equipment_list))
        
        for row, equipment in enumerate(self.equipment_list):
            # 部位
            part_names = {
                1: "铲子", 2: "刀具", 3: "锅具", 4: "调料瓶", 5: "厨师帽"
            }
            part_type = equipment.get("part_type", 0)
            part_name = part_names.get(part_type, f"部位{part_type}")
            self.equipment_table.setItem(row, 0, QTableWidgetItem(part_name))
            
            # 装备名称
            equipment_name = equipment.get("goods_name", equipment.get("name", "未知装备"))
            self.equipment_table.setItem(row, 1, QTableWidgetItem(equipment_name))
            
            # 孔位状态
            hole_count = equipment.get("hole", 0)
            self.equipment_table.setItem(row, 2, QTableWidgetItem(f"{hole_count} 个孔位"))
            
            # 存储装备ID到行数据
            self.equipment_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, equipment.get("id"))

    def update_gems_table(self):
        """更新宝石列表表格"""
        self.gems_table.setRowCount(len(self.gems_list))
        self.gems_count_label.setText(f"总计: {len(self.gems_list)} 个宝石")
        
        for row, gem in enumerate(self.gems_list):
            # 宝石名称
            gem_name = gem.get("goods_name", "未知宝石")
            self.gems_table.setItem(row, 0, QTableWidgetItem(gem_name))
            
            # 数量
            num = gem.get("num", 1)
            self.gems_table.setItem(row, 1, QTableWidgetItem(str(num)))
            
            # 属性描述
            desc = gem.get("goods_description", "无描述")
            # 提取属性信息
            attr_text = self.extract_gem_attributes(desc)
            self.gems_table.setItem(row, 2, QTableWidgetItem(attr_text))
            
            # 存储宝石代码到行数据
            self.gems_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, gem.get("goods_code"))

    def extract_gem_attributes(self, description):
        """从描述中提取宝石属性"""
        if not description or description == "无描述":
            return "无属性"
        
        # 尝试提取属性信息，如 "创意+16", "厨艺+18" 等
        import re
        matches = re.findall(r'([^+,，]+)\+(\d+)', description)
        if matches:
            attrs = [f"{attr}+{value}" for attr, value in matches]
            return ", ".join(attrs)
        
        return description.replace("可镶嵌在厨具上,", "").replace(".", "").strip()

    def on_equipment_selected(self):
        """装备被选中时的处理"""
        current_row = self.equipment_table.currentRow()
        if current_row < 0 or current_row >= len(self.equipment_list):
            return
        
        selected_equipment = self.equipment_list[current_row]
        self.current_equipment = selected_equipment
        
        # 更新装备信息显示
        self.update_equipment_info(selected_equipment)
        
        # 加载装备详情（包括孔位信息）
        self.load_equipment_detail(selected_equipment.get("id"))

    def update_equipment_info(self, equipment):
        """更新装备信息显示"""
        name = equipment.get("goods_name", "未知装备")
        level = equipment.get("level", 0)
        strengthen = equipment.get("strengthen_num", 0)
        
        self.equip_name_label.setText(name)
        self.equip_strengthen_label.setText(f"等级 {level} | 强化 +{strengthen}")
        
        # 基础属性
        properties = []
        if equipment.get("fire", 0) > 0:
            properties.append(f"火候+{equipment['fire']}")
        if equipment.get("cooking", 0) > 0:
            properties.append(f"厨艺+{equipment['cooking']}")
        if equipment.get("sword", 0) > 0:
            properties.append(f"刀工+{equipment['sword']}")
        if equipment.get("season", 0) > 0:
            properties.append(f"调味+{equipment['season']}")
        if equipment.get("originality", 0) > 0:
            properties.append(f"创意+{equipment['originality']}")
        if equipment.get("luck", 0) > 0:
            properties.append(f"幸运+{equipment['luck']}")
        
        self.equip_properties_label.setText(", ".join(properties) if properties else "无基础属性")

    def load_equipment_detail(self, equipment_id):
        """加载装备详情（包括孔位信息）"""
        if not equipment_id:
            return
        
        try:
            from src.delicious_town_bot.actions.equip import EquipAction
            cookie_dict = {"PHPSESSID": self.account.cookie} if self.account.cookie else {}
            equip_action = EquipAction(key=self.account.key, cookie=cookie_dict)
            
            detail_result = equip_action.get_equipment_detail(str(equipment_id))
            
            if detail_result.get("success"):
                equipment_detail = detail_result.get("equipment", {})
                gems = detail_result.get("gems", {})
                holes = detail_result.get("holes", {})
                
                # 更新孔位状态
                total_holes = holes.get("total", 0)
                used_holes = holes.get("used", 0)
                self.holes_status_label.setText(f"孔位状态: {used_holes}/{total_holes}")
                
                # 更新孔位表格
                self.update_holes_table(total_holes, gems, equipment_detail)
                
            else:
                QMessageBox.warning(self, "警告", f"获取装备详情失败: {detail_result.get('message')}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载装备详情失败: {str(e)}")

    def update_holes_table(self, total_holes, gems, equipment_detail):
        """更新孔位表格"""
        # 调试信息
        equipment_name = equipment_detail.get("name", "未知装备")
        print(f"[Debug] 更新孔位表格: {equipment_name} (总孔位:{total_holes}, 已镶嵌:{len(gems)})")
        
        # 设置表格行数为总孔位数
        self.holes_table.setRowCount(total_holes)
        
        for hole_position in range(1, total_holes + 1):
            row = hole_position - 1
            
            # 孔位编号
            self.holes_table.setItem(row, 0, QTableWidgetItem(f"孔位 {hole_position}"))
            
            # 查找该孔位的宝石
            gem_info = None
            for hole_id, gem_data in gems.items():
                if gem_data.get("position", 0) == hole_position:
                    gem_info = gem_data
                    break
            
            if gem_info:
                # 有宝石
                gem_name = gem_info.get("gem_name", "未知宝石")
                print(f"[Debug]   孔位{hole_position}: {gem_name} -> 卸下按钮")
                self.holes_table.setItem(row, 1, QTableWidgetItem(gem_name))
                
                # 属性加成
                properties = gem_info.get("properties", {})
                attr_parts = []
                for attr, value in properties.items():
                    if value > 0:
                        attr_names = {
                            "fire": "火候", "cooking": "厨艺", "sword": "刀工",
                            "season": "调味", "originality": "创意", "luck": "幸运"
                        }
                        attr_parts.append(f"{attr_names.get(attr, attr)}+{value}")
                
                self.holes_table.setItem(row, 2, QTableWidgetItem(", ".join(attr_parts)))
                
                # 卸下按钮
                remove_btn = QPushButton("卸下")
                remove_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; padding: 4px; }")
                remove_btn.clicked.connect(lambda checked, hid=gem_info.get("hole_id"): self.remove_gem(hid))
                self.holes_table.setCellWidget(row, 3, remove_btn)
                
            else:
                # 空孔位
                print(f"[Debug]   孔位{hole_position}: 空 -> 镶嵌按钮")
                self.holes_table.setItem(row, 1, QTableWidgetItem("空"))
                self.holes_table.setItem(row, 2, QTableWidgetItem("-"))
                
                # 镶嵌按钮
                install_btn = QPushButton("镶嵌")
                install_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; padding: 4px; }")
                install_btn.clicked.connect(lambda checked, pos=hole_position: self.install_gem_to_hole(pos))
                self.holes_table.setCellWidget(row, 3, install_btn)

    def install_selected_gem(self):
        """镶嵌选中的宝石"""
        if not self.current_equipment:
            QMessageBox.warning(self, "提示", "请先选择装备")
            return
        
        current_gem_row = self.gems_table.currentRow()
        if current_gem_row < 0:
            QMessageBox.warning(self, "提示", "请选择要镶嵌的宝石")
            return
        
        # 查找空的孔位
        empty_hole = self.find_empty_hole()
        if not empty_hole:
            QMessageBox.warning(self, "提示", "该装备没有空闲孔位，请先打孔或卸下其他宝石")
            return
        
        self.install_gem_to_hole(empty_hole)

    def find_empty_hole(self):
        """查找空的孔位"""
        for row in range(self.holes_table.rowCount()):
            gem_item = self.holes_table.item(row, 1)
            if gem_item and gem_item.text() == "空":
                return row + 1  # 孔位从1开始
        return None

    def install_gem_to_hole(self, hole_position):
        """将选中的宝石镶嵌到指定孔位"""
        if not self.current_equipment:
            QMessageBox.warning(self, "提示", "请先选择装备")
            return
        
        current_gem_row = self.gems_table.currentRow()
        if current_gem_row < 0:
            QMessageBox.warning(self, "提示", "请选择要镶嵌的宝石")
            return
        
        gem_code = self.gems_table.item(current_gem_row, 0).data(Qt.ItemDataRole.UserRole)
        gem_name = self.gems_table.item(current_gem_row, 0).text()
        equipment_id = self.current_equipment.get("id")
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认镶嵌",
            f"确定要将 {gem_name} 镶嵌到 {self.current_equipment.get('goods_name', '装备')} 的孔位 {hole_position} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from src.delicious_town_bot.actions.equip import EquipAction
            cookie_dict = {"PHPSESSID": self.account.cookie} if self.account.cookie else {}
            equip_action = EquipAction(key=self.account.key, cookie=cookie_dict)
            
            # 先获取装备详情以获取正确的hole_id
            detail_result = equip_action.get_equipment_detail(str(equipment_id))
            if not detail_result.get("success"):
                QMessageBox.warning(self, "失败", f"获取装备详情失败: {detail_result.get('message')}")
                return
            
            gems = detail_result.get("gems", {})
            print(f"[Debug] 镶嵌参数: equip_id={equipment_id}, hole_position={hole_position}, gem_code={gem_code}")
            
            # 从装备详情的原始数据中获取hole_id
            equipment_data = detail_result.get("raw_response", {}).get("data", {})
            hole_list = equipment_data.get("hole_list", {})
            
            actual_hole_id = None
            for hole_key, hole_data in hole_list.items():
                if hole_data.get("num") == str(hole_position) and not hole_data.get("goods_name"):
                    actual_hole_id = hole_data.get("id")
                    break
            
            if not actual_hole_id:
                QMessageBox.warning(self, "失败", f"找不到孔位 {hole_position} 的ID")
                return
            
            print(f"[Debug] 找到实际hole_id: {actual_hole_id} (position: {hole_position})")
            
            # 使用实际的hole_id进行镶嵌
            result = equip_action.install_gem(
                equip_id=str(equipment_id),
                hole_id=str(actual_hole_id),
                stone_code=gem_code
            )
            
            if result.get("success"):
                QMessageBox.information(self, "成功", f"宝石镶嵌成功: {result.get('message')}")
                # 刷新数据
                self.load_equipment_detail(equipment_id)
                self.load_data()
            else:
                QMessageBox.warning(self, "失败", f"宝石镶嵌失败: {result.get('message')}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"镶嵌宝石时发生错误: {str(e)}")

    def remove_gem(self, hole_id):
        """卸下宝石"""
        if not self.current_equipment or not hole_id:
            return
        
        equipment_id = self.current_equipment.get("id")
        equipment_name = self.current_equipment.get("goods_name", "装备")
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认卸下",
            f"确定要从 {equipment_name} 上卸下这个宝石吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from src.delicious_town_bot.actions.equip import EquipAction
            cookie_dict = {"PHPSESSID": self.account.cookie} if self.account.cookie else {}
            equip_action = EquipAction(key=self.account.key, cookie=cookie_dict)
            
            result = equip_action.remove_gem(
                equip_id=str(equipment_id),
                hole_id=str(hole_id)
            )
            
            if result.get("success"):
                QMessageBox.information(self, "成功", f"宝石卸下成功: {result.get('message')}")
                # 刷新数据
                self.load_equipment_detail(equipment_id)
                self.load_data()
            else:
                QMessageBox.warning(self, "失败", f"宝石卸下失败: {result.get('message')}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"卸下宝石时发生错误: {str(e)}")

    def add_hole_to_equipment(self):
        """为装备添加孔位"""
        if not self.current_equipment:
            QMessageBox.warning(self, "提示", "请先选择装备")
            return
        
        equipment_name = self.current_equipment.get("goods_name", "装备")
        
        # 询问打孔数量
        num, ok = QInputDialog.getInt(
            self, "装备打孔",
            f"为 {equipment_name} 打孔\n\n每个孔位需要1个打孔石\n请输入要打的孔位数量:",
            1, 1, 10, 1
        )
        
        if not ok:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认打孔",
            f"确定要为 {equipment_name} 打 {num} 个孔吗？\n\n这将消耗 {num} 个打孔石\n如果打孔石不足会自动购买",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from src.delicious_town_bot.actions.equip import EquipAction
            cookie_dict = {"PHPSESSID": self.account.cookie} if self.account.cookie else {}
            equip_action = EquipAction(key=self.account.key, cookie=cookie_dict)
            
            equipment_id = self.current_equipment.get("id")
            
            # 先尝试购买打孔石
            buy_result = equip_action.buy_drill_stone(num)
            if not buy_result.get("success"):
                QMessageBox.warning(self, "购买失败", f"购买打孔石失败: {buy_result.get('message')}")
                return
            
            # 执行打孔
            result = equip_action.add_hole(str(equipment_id), num)
            
            if result.get("success"):
                QMessageBox.information(self, "成功", f"装备打孔成功: {result.get('message')}")
                # 刷新装备详情
                self.load_equipment_detail(equipment_id)
            else:
                QMessageBox.warning(self, "失败", f"装备打孔失败: {result.get('message')}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"装备打孔时发生错误: {str(e)}")

    def load_essence_materials(self, depot_action):
        """加载精华材料数量"""
        print("[Debug] 正在加载精华材料数量...")
        
        try:
            # 获取材料分类数据 (type=2为材料)
            from src.delicious_town_bot.constants import ItemType
            materials_result = depot_action.get_all_items(ItemType.MATERIALS)
            
            print(f"[Debug] 获取到 {len(materials_result)} 个材料")
            
            # 调试：打印前几个材料的完整信息
            print("[Debug] 材料数据结构示例:")
            for i, material in enumerate(materials_result[:3]):
                print(f"[Debug] 材料 {i+1}: {material}")
            
            # 精华材料名称映射（包含物品代码）
            essence_mapping = {
                "原石精华": ["原石精华", "21101"],
                "魔石精华": ["魔石精华", "21102"], 
                "灵石精华": ["灵石精华", "21103"],
                "神石精华": ["神石精华", "21104"],
                "原玉精华": ["原玉精华", "21105"],
                "魔玉精华": ["魔玉精华", "21106"],
                "灵玉精华": ["灵玉精华", "21107"],  # 推测的代码
                "神玉精华": ["神玉精华", "21108"]   # 推测的代码
            }
            
            # 初始化所有精华数量为0
            essence_counts = {key: 0 for key in essence_mapping}
            
            # 查找匹配的精华材料
            print("[Debug] 搜索精华材料...")
            for material in materials_result:
                material_name = material.get("goods_name", "")
                material_code = material.get("goods_code", "")
                
                # 尝试多个可能的数量字段
                material_num = 0
                for num_field in ["goods_num", "num", "count"]:
                    if material.get(num_field):
                        try:
                            material_num = int(material.get(num_field, 0))
                            break
                        except:
                            continue
                
                print(f"[Debug] 检查材料: {material_name} (code: {material_code}) x{material_num}")
                
                # 检查是否匹配精华材料
                for essence_key, (essence_name, essence_code) in essence_mapping.items():
                    # 按名称匹配或代码匹配
                    if (essence_name in material_name or 
                        essence_key in material_name or
                        (essence_code and essence_code == material_code)):
                        essence_counts[essence_key] = material_num
                        print(f"[Debug] ✅ 找到 {essence_name}: {material_num} 个 (匹配: {material_name})")
                        break
            
            # 更新界面显示
            for essence_key, count in essence_counts.items():
                if essence_key in self.essences_labels:
                    self.essences_labels[essence_key].setText(str(count))
            
            print(f"[Debug] 精华材料加载完成")
            
            # 统计找到的精华种类
            found_essences = sum(1 for count in essence_counts.values() if count > 0)
            print(f"[Debug] 找到 {found_essences}/8 种精华材料")
            
            # 显示最终结果
            print("[Debug] 精华材料统计:")
            for essence_key, count in essence_counts.items():
                status = "✅" if count > 0 else "❌"
                print(f"[Debug]   {status} {essence_key}: {count}")
            
        except Exception as e:
            print(f"[Error] 加载精华材料失败: {e}")
            import traceback
            traceback.print_exc()
            # 设置默认值
            for essence_key in self.essences_labels:
                self.essences_labels[essence_key].setText("0")

    def update_refining_gems_combo(self):
        """更新精炼宝石下拉框"""
        self.refining_gem_combo.clear()
        
        if not self.gems_list:
            self.refining_gem_combo.addItem("暂无可精炼宝石")
            return
        
        print("[Debug] 正在更新精炼宝石下拉框...")
        
        # 添加可精炼的宝石到下拉框
        refining_gems = []
        for gem in self.gems_list:
            gem_name = gem.get("goods_name", "未知宝石")
            gem_code = gem.get("goods_code", "")
            gem_count = int(gem.get("num", 0))
            
            print(f"[Debug] 检查宝石: {gem_name}, 代码: {gem_code}, 数量: {gem_count}")
            
            # 只添加有数量的宝石
            if gem_count > 0:
                display_text = f"{gem_name} (x{gem_count})"
                self.refining_gem_combo.addItem(display_text, gem_code)
                refining_gems.append(gem_name)
                print(f"[Debug] ✅ 添加到精炼列表: {display_text}")
        
        if not refining_gems:
            self.refining_gem_combo.addItem("暂无可精炼宝石")
            print("[Debug] ❌ 无可精炼宝石")
        
        print(f"[Debug] 已添加 {len(refining_gems)} 种宝石到精炼列表")

    def buy_essence_material(self, essence_key):
        """购买精华材料"""
        # 弹出购买数量输入对话框
        quantity, ok = QInputDialog.getInt(
            self, 
            f"购买{essence_key}", 
            f"请输入要购买的{essence_key}数量:", 
            1, 1, 100, 1
        )
        
        if not ok:
            return
        
        # 确认购买对话框
        reply = QMessageBox.question(
            self, "确认购买",
            f"确定要购买 {quantity} 个 {essence_key} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # 调用购买接口
            from src.delicious_town_bot.actions.shop import ShopAction
            cookie_dict = {"PHPSESSID": self.account.cookie} if self.account.cookie else {}
            shop_action = ShopAction(key=self.account.key, cookie=cookie_dict)
            
            self.status_label.setText(f"正在购买 {essence_key} x{quantity}...")
            
            # 执行购买
            result = shop_action.buy_essence_material(essence_key, quantity)
            
            if result.get("success"):
                success_message = result.get("message", "购买成功")
                QMessageBox.information(self, "购买成功", f"{essence_key} x{quantity} 购买成功！\n\n{success_message}")
                
                # 刷新精华材料数据
                from src.delicious_town_bot.actions.depot import DepotAction
                depot_action = DepotAction(key=self.account.key, cookie=cookie_dict)
                self.load_essence_materials(depot_action)
                
                self.status_label.setText("购买完成，数据已刷新")
            else:
                error_message = result.get("message", "购买失败")
                QMessageBox.warning(self, "购买失败", f"购买 {essence_key} 失败：\n\n{error_message}")
                self.status_label.setText(f"购买失败: {error_message}")
                
        except Exception as e:
            error_msg = f"购买异常: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.status_label.setText(error_msg)

    def refine_gem(self, is_fixed=False):
        """精炼宝石"""
        current_index = self.refining_gem_combo.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, "提示", "请选择要精炼的宝石")
            return
        
        gem_code = self.refining_gem_combo.itemData(current_index)
        if not gem_code:
            QMessageBox.warning(self, "提示", "该宝石无法精炼")
            return
        
        gem_name = self.refining_gem_combo.currentText().split(" (x")[0]
        refining_type = "固定精炼" if is_fixed else "普通精炼"
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认精炼",
            f"确定要进行 {refining_type} 吗？\n\n宝石: {gem_name}\n类型: {refining_type}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            self.refining_result_label.setText(f"正在精炼 {gem_name}...")
            
            # 调用精炼接口
            from src.delicious_town_bot.actions.gem_refining import GemRefiningAction
            cookie_dict = {"PHPSESSID": self.account.cookie} if self.account.cookie else {}
            refining_action = GemRefiningAction(key=self.account.key, cookie=cookie_dict)
            
            result = refining_action.refine_gem(stone_code=gem_code, is_fixed=1 if is_fixed else 0)
            
            if result.get("success"):
                result_message = result.get("message", "精炼成功")
                result_gem = result.get("result_gem", "")
                
                self.refining_result_label.setText(f"✅ 精炼成功！\n\n{result_message}\n{result_gem}")
                
                # 刷新数据
                self.load_data()
                
                QMessageBox.information(self, "成功", f"宝石精炼成功！\n\n{result_message}")
            else:
                error_message = result.get("message", "精炼失败")
                self.refining_result_label.setText(f"❌ 精炼失败\n\n{error_message}")
                QMessageBox.warning(self, "失败", f"宝石精炼失败: {error_message}")
                
        except Exception as e:
            error_msg = f"精炼异常: {str(e)}"
            self.refining_result_label.setText(f"❌ {error_msg}")
            QMessageBox.critical(self, "错误", error_msg)

    def show(self):
        """显示对话框"""
        super().show()
        # 确保对话框在最前面
        self.raise_()
        self.activateWindow()


class UserPowerPage(QWidget):
    """用户厨力主页面"""
    
    def __init__(self, manager: AccountManager, log_widget=None):
        super().__init__()
        self.manager = manager
        self.log_widget = log_widget
        self.setupUI()
        self.load_accounts()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)  # 减少组件间距，使界面更紧凑
        layout.setContentsMargins(8, 8, 8, 8)  # 减少边距
        
        # 标题和控制区域
        header_layout = QHBoxLayout()
        
        title_label = QLabel("厨力面板")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # 账号选择
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("选择账号:"))
        
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        account_layout.addWidget(self.account_combo)
        
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_user_data)
        account_layout.addWidget(self.refresh_btn)
        
        account_layout.addStretch()
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addLayout(account_layout)
        
        layout.addLayout(header_layout)
        
        # 主内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：餐厅信息和厨力属性
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 餐厅信息
        self.restaurant_widget = RestaurantInfoWidget()
        left_layout.addWidget(self.restaurant_widget)
        
        # 厨力属性
        self.power_widget = PowerAttributeWidget()
        left_layout.addWidget(self.power_widget)
        
        # 厨塔推荐
        self.tower_widget = TowerRecommendationWidget(parent=self)
        left_layout.addWidget(self.tower_widget)
        
        left_layout.addStretch()
        content_splitter.addWidget(left_widget)
        
        # 右侧：装备信息
        self.equipment_widget = EquipmentWidget(parent=self)
        content_splitter.addWidget(self.equipment_widget)
        
        # 连接装备管理按钮事件
        self.equipment_widget.buy_novice_btn.clicked.connect(self.buy_novice_equipment)
        self.equipment_widget.buy_intermediate_btn.clicked.connect(self.buy_intermediate_equipment)
        self.equipment_widget.view_equipment_btn.clicked.connect(self.view_equipment_inventory)
        self.equipment_widget.auto_process_btn.clicked.connect(self.auto_process_novice_equipment)
        
        # 设置分割比例
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(content_splitter)
        
        # 状态栏
        self.status_label = QLabel("请选择账号并点击刷新数据")
        layout.addWidget(self.status_label)
    
    def load_accounts(self):
        """加载账号列表"""
        self.account_combo.clear()
        accounts = self.manager.list_accounts()
        
        for account in accounts:
            if account.key:  # 只显示有Key的账号
                display_text = f"{account.username} ({account.restaurant or '未知餐厅'})"
                self.account_combo.addItem(display_text, account.id)
        
        if self.account_combo.count() == 0:
            self.account_combo.addItem("没有可用账号", None)
            self.refresh_btn.setEnabled(False)
        else:
            self.refresh_btn.setEnabled(True)
    
    def refresh_user_data(self):
        """刷新用户数据"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请选择一个有效的账号！")
            return
        
        self.status_label.setText("正在获取数据...")
        self.refresh_btn.setEnabled(False)
        
        try:
            # 获取账号信息
            account = self.manager.get_account(account_id)
            if not account or not account.key:
                raise Exception("账号无效或缺少Key")
            
            # 创建UserCardAction
            cookie_value = account.cookie if account.cookie else "123"
            cookie_dict = {"PHPSESSID": cookie_value}
            user_card_action = UserCardAction(key=account.key, cookie=cookie_dict)
            
            # 获取用户卡片信息
            card_result = user_card_action.get_user_card()
            if not card_result.get("success"):
                raise Exception(card_result.get("message", "获取用户信息失败"))
            
            # 获取厨力摘要
            power_result = user_card_action.get_cooking_power_summary()
            if not power_result.get("success"):
                raise Exception(power_result.get("message", "获取厨力信息失败"))
            
            # 获取装备摘要  
            equipment_result = user_card_action.get_equipment_summary()
            if not equipment_result.get("success"):
                raise Exception(equipment_result.get("message", "获取装备信息失败"))
            
            # 更新UI显示
            self.restaurant_widget.update_restaurant_data(
                card_result["restaurant_info"],
                card_result.get("income_info", {})
            )
            
            self.power_widget.update_power_data(power_result)
            
            self.equipment_widget.update_equipment_data(
                equipment_result["equipment_list"],
                equipment_result
            )
            
            # 更新见习装备数量显示
            self.update_novice_equipment_count(user_card_action)
            
            # 获取并更新宝石信息
            try:
                from src.delicious_town_bot.actions.depot import DepotAction
                depot_action = DepotAction(key=account.key, cookie=cookie_dict)
                gems_result = depot_action.get_all_gems()
                self.equipment_widget.update_gems_data(gems_result)
            except Exception as e:
                print(f"[Warning] 获取宝石信息失败: {e}")
                # 宝石信息获取失败不影响整体流程，只是显示失败信息
                self.equipment_widget.update_gems_data({"success": False, "message": str(e)})
            
            # 自动刷新强化材料信息
            try:
                self.equipment_widget.refresh_enhance_materials()
            except Exception as e:
                print(f"[Warning] 刷新强化材料失败: {e}")
            
            # 记录到日志
            if self.log_widget:
                restaurant_name = card_result["restaurant_info"].get("name", "未知")
                total_power = power_result.get("total_with_equip", 0)
                self.log_widget.append(f"🏠 厨力面板: {restaurant_name} - 总厨力 {total_power}")
            
            self.status_label.setText(f"数据更新成功 - {datetime.now().strftime('%H:%M:%S')}")
            
            # 自动刷新厨塔推荐（在后台进行，不影响主要数据加载）
            QTimer.singleShot(500, self.tower_widget.refresh_tower_recommendations)
            
        except Exception as e:
            error_msg = f"获取数据失败: {str(e)}"
            self.status_label.setText(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            
            if self.log_widget:
                self.log_widget.append(f"❌ 厨力面板获取失败: {error_msg}")
        
        finally:
            self.refresh_btn.setEnabled(True)
    
    def buy_novice_equipment(self):
        """购买见习装备"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请选择一个有效的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认购买", 
            "确定要购买见习装备吗？\n将购买见习之铲、刀、锅各4件（每件1个，共12次购买）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.equipment_widget.buy_novice_btn.setEnabled(False)
        self.status_label.setText("正在购买见习装备...")
        
        try:
            # 获取账号信息
            account = self.manager.get_account(account_id)
            if not account or not account.key:
                raise Exception("账号无效或缺少Key")
            
            # 创建ShopAction
            from src.delicious_town_bot.actions.shop import ShopAction
            cookie_value = account.cookie if account.cookie else "123"
            cookie_dict = {"PHPSESSID": cookie_value}
            shop_action = ShopAction(key=account.key, cookie=cookie_dict)
            
            # 执行购买
            result = shop_action.buy_novice_equipment_daily()
            
            if result.get("success"):
                total_purchased = result.get("total_purchased", 0)
                equipment_results = result.get("equipment_results", [])
                
                # 构建详细结果
                detail_parts = []
                for eq_result in equipment_results:
                    name = eq_result.get("name", "")
                    success_count = eq_result.get("success_count", 0)
                    detail_parts.append(f"{name}: {success_count}/4")
                
                message = f"购买完成！总计成功 {total_purchased}/12 件\n" + "\n".join(detail_parts)
                QMessageBox.information(self, "购买结果", message)
                
                # 记录到日志
                if self.log_widget:
                    restaurant_name = account.username
                    self.log_widget.append(f"🛒 见习装备购买: {restaurant_name} - 成功购买 {total_purchased}/12 件")
                
                # 更新见习装备数量显示
                cookie_value = account.cookie if account.cookie else "123"
                cookie_dict = {"PHPSESSID": cookie_value}
                user_card_action = UserCardAction(key=account.key, cookie=cookie_dict)
                self.update_novice_equipment_count(user_card_action)
                
            else:
                error_msg = result.get("message", "购买失败")
                QMessageBox.critical(self, "购买失败", error_msg)
                
                if self.log_widget:
                    self.log_widget.append(f"❌ 见习装备购买失败: {error_msg}")
        
        except Exception as e:
            error_msg = f"购买见习装备失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            
            if self.log_widget:
                self.log_widget.append(f"❌ 见习装备购买异常: {error_msg}")
        
        finally:
            self.equipment_widget.buy_novice_btn.setEnabled(True)
            if not self.status_label.text().startswith("数据更新成功"):
                self.status_label.setText("购买操作完成")
    
    def view_equipment_inventory(self):
        """查看厨具库存"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请选择一个有效的账号！")
            return
        
        self.equipment_widget.view_equipment_btn.setEnabled(False)
        
        try:
            # 获取账号信息
            account = self.manager.get_account(account_id)
            if not account or not account.key:
                raise Exception("账号无效或缺少Key")
            
            # 创建UserCardAction
            cookie_value = account.cookie if account.cookie else "123"
            cookie_dict = {"PHPSESSID": cookie_value}
            user_card_action = UserCardAction(key=account.key, cookie=cookie_dict)
            
            # 创建厨具库存对话框
            dialog = EquipmentInventoryDialog(user_card_action, account.username, self)
            dialog.operation_result.connect(self.on_equipment_operation_result)
            dialog.exec()
            
        except Exception as e:
            error_msg = f"查看厨具库存失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
        
        finally:
            self.equipment_widget.view_equipment_btn.setEnabled(True)
    
    def update_novice_equipment_count(self, user_card_action):
        """更新见习装备数量显示"""
        try:
            novice_result = user_card_action.get_novice_equipment_count()
            if novice_result.get("success"):
                total_count = novice_result.get("total_count", 0)
                novice_equipment = novice_result.get("novice_equipment", {})
                
                # 构建显示文本
                count_parts = []
                for name, data in novice_equipment.items():
                    count = data.get("count", 0)
                    count_parts.append(f"{name[-1:]}: {count}")  # 只显示最后一个字（铲/刀/锅）
                
                if count_parts:
                    count_text = f"见习装备: {' | '.join(count_parts)} (共{total_count}件)"
                else:
                    count_text = "见习装备: 无"
                
                self.equipment_widget.novice_count_label.setText(count_text)
            else:
                self.equipment_widget.novice_count_label.setText("见习装备: 统计失败")
        except:
            self.equipment_widget.novice_count_label.setText("见习装备: 未统计")
    
    def on_equipment_operation_result(self, operation_type: str, message: str):
        """处理装备操作结果"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        feedback_message = f"[{timestamp}] {operation_type}: {message}"
        
        # 更新反馈标签
        self.equipment_widget.operation_feedback_label.setText(feedback_message)
        
        # 更新状态栏
        self.status_label.setText(f"装备{operation_type}完成 - {timestamp}")
        
        # 记录到日志
        if self.log_widget:
            account_id = self.account_combo.currentData()
            account = self.manager.get_account(account_id) if account_id else None
            username = account.username if account else "未知用户"
            self.log_widget.append(f"🔧 装备操作: {username} - {message}")
        
        # 如果是成功操作，刷新装备数据
        if "✅" in message:
            # 延迟1秒后刷新数据以确保服务器状态更新
            QTimer.singleShot(1000, self.refresh_equipment_data)
    
    def refresh_equipment_data(self):
        """仅刷新装备相关数据"""
        account_id = self.account_combo.currentData()
        if not account_id:
            return
        
        try:
            account = self.manager.get_account(account_id)
            if not account or not account.key:
                return
            
            cookie_value = account.cookie if account.cookie else "123"
            cookie_dict = {"PHPSESSID": cookie_value}
            user_card_action = UserCardAction(key=account.key, cookie=cookie_dict)
            
            # 仅更新装备相关信息
            equipment_result = user_card_action.get_equipment_summary()
            if equipment_result.get("success"):
                self.equipment_widget.update_equipment_data(
                    equipment_result["equipment_list"],
                    equipment_result
                )
                
                # 更新见习装备数量
                self.update_novice_equipment_count(user_card_action)
                
                # 刷新厨塔推荐（因为装备变化影响厨力）
                QTimer.singleShot(1000, self.tower_widget.refresh_tower_recommendations)
                
        except Exception as e:
            print(f"刷新装备数据失败: {e}")
    
    def buy_intermediate_equipment(self):
        """购买中厨装备"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请选择一个有效的账号！")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认购买", 
            "确定要购买中厨装备吗？\\n将购买中厨之铲、锅、刀各1件",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.equipment_widget.buy_intermediate_btn.setEnabled(False)
        self.status_label.setText("正在购买中厨装备...")
        
        try:
            # 获取账号信息
            account = self.manager.get_account(account_id)
            if not account or not account.key:
                raise Exception("账号无效或缺少Key")
            
            # 创建ShopAction
            from src.delicious_town_bot.actions.shop import ShopAction
            cookie_value = account.cookie if account.cookie else "123"
            cookie_dict = {"PHPSESSID": cookie_value}
            shop_action = ShopAction(key=account.key, cookie=cookie_dict)
            
            # 执行购买
            result = shop_action.buy_intermediate_equipment()
            
            if result.get("success"):
                total_purchased = result.get("total_purchased", 0)
                equipment_results = result.get("equipment_results", [])
                
                # 构建详细结果
                detail_parts = []
                for eq_result in equipment_results:
                    name = eq_result.get("name", "")
                    success = "✅" if eq_result.get("success") else "❌"
                    detail_parts.append(f"{name}: {success}")
                
                message = f"购买完成！总计成功 {total_purchased}/3 件\\n" + "\\n".join(detail_parts)
                QMessageBox.information(self, "购买结果", message)
                
                # 记录到日志
                if self.log_widget:
                    restaurant_name = account.username
                    self.log_widget.append(f"🛒 中厨装备购买: {restaurant_name} - 成功购买 {total_purchased}/3 件")
                
                # 更新装备数据
                QTimer.singleShot(1000, self.refresh_equipment_data)
                
            else:
                error_msg = result.get("message", "购买失败")
                QMessageBox.critical(self, "购买失败", error_msg)
                
                if self.log_widget:
                    self.log_widget.append(f"❌ 中厨装备购买失败: {error_msg}")
        
        except Exception as e:
            error_msg = f"购买中厨装备失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            
            if self.log_widget:
                self.log_widget.append(f"❌ 中厨装备购买异常: {error_msg}")
        
        finally:
            self.equipment_widget.buy_intermediate_btn.setEnabled(True)
            if not self.status_label.text().startswith("数据更新成功"):
                self.status_label.setText("购买操作完成")
    
    def auto_process_novice_equipment(self):
        """自动处理见习装备"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "提示", "请选择一个有效的账号！")
            return
        
        # 详细确认对话框
        reply = QMessageBox.question(
            self, "确认自动处理", 
            "确定要自动处理见习装备吗？\\n\\n"
            "⚠️ 操作内容：\\n"
            "1. 强化一件见习装备（完成每日任务）\\n"
            "2. 分解所有其他见习装备（获得材料）\\n\\n"
            "注意：此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.equipment_widget.auto_process_btn.setEnabled(False)
        self.status_label.setText("正在自动处理见习装备...")
        
        try:
            # 获取账号信息
            account = self.manager.get_account(account_id)
            if not account or not account.key:
                raise Exception("账号无效或缺少Key")
            
            # 创建UserCardAction
            cookie_value = account.cookie if account.cookie else "123"
            cookie_dict = {"PHPSESSID": cookie_value}
            user_card_action = UserCardAction(key=account.key, cookie=cookie_dict)
            
            # 执行自动处理
            result = user_card_action.auto_process_novice_equipment()
            
            if result.get("success"):
                total_processed = result.get("total_processed", 0)
                enhanced_equipment = result.get("enhanced_equipment")
                resolved_equipment = result.get("resolved_equipment", [])
                failed_operations = result.get("failed_operations", [])
                
                # 构建详细结果
                details = []
                if enhanced_equipment:
                    details.append(f"✅ 强化: {enhanced_equipment['name']}")
                
                if resolved_equipment:
                    details.append(f"⚡ 分解: {len(resolved_equipment)} 件装备")
                
                if failed_operations:
                    details.append(f"❌ 失败: {len(failed_operations)} 个操作")
                
                message = f"自动处理完成！总计处理 {total_processed} 件装备\\n\\n" + "\\n".join(details)
                if failed_operations:
                    message += "\\n\\n失败详情：\\n"
                    for fail in failed_operations[:3]:  # 只显示前3个失败
                        message += f"- {fail['operation']} {fail['equipment']}: {fail['error']}\\n"
                
                QMessageBox.information(self, "处理结果", message)
                
                # 记录到日志
                if self.log_widget:
                    restaurant_name = account.username
                    self.log_widget.append(f"🔧 见习装备自动处理: {restaurant_name} - 处理 {total_processed} 件装备")
                
                # 刷新装备数据
                QTimer.singleShot(2000, self.refresh_equipment_data)
                
            else:
                error_msg = result.get("message", "处理失败")
                QMessageBox.critical(self, "处理失败", error_msg)
                
                if self.log_widget:
                    self.log_widget.append(f"❌ 见习装备自动处理失败: {error_msg}")
        
        except Exception as e:
            error_msg = f"自动处理见习装备失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            
            if self.log_widget:
                self.log_widget.append(f"❌ 见习装备自动处理异常: {error_msg}")
        
        finally:
            self.equipment_widget.auto_process_btn.setEnabled(True)
            if not self.status_label.text().startswith("数据更新成功"):
                self.status_label.setText("处理操作完成")

    def get_current_account(self):
        """获取当前选中的账号"""
        account_id = self.account_combo.currentData()
        if account_id:
            return self.manager.get_account(account_id)
        return None

    def refresh_gems_data(self):
        """刷新宝石数据"""
        account = self.get_current_account()
        if not account or not account.key:
            return
        
        try:
            from src.delicious_town_bot.actions.depot import DepotAction
            cookie_dict = {"PHPSESSID": account.cookie} if account.cookie else {}
            depot_action = DepotAction(key=account.key, cookie=cookie_dict)
            gems_result = depot_action.get_all_gems()
            self.equipment_widget.update_gems_data(gems_result)
        except Exception as e:
            print(f"[Warning] 刷新宝石数据失败: {e}")
            self.equipment_widget.update_gems_data({"success": False, "message": str(e)})


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试用的AccountManager
    try:
        from src.delicious_town_bot.utils.account_manager import AccountManager
        manager = AccountManager()
        
        window = UserPowerPage(manager)
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"测试运行失败: {e}")
        print("请确保数据库已正确配置")
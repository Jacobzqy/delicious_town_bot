"""
厨具库存查看对话框
用于显示详细的厨具库存信息
"""
from typing import Dict, Any, List
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, 
    QTableWidgetItem, QLabel, QPushButton, QComboBox, QGroupBox,
    QHeaderView, QAbstractItemView, QProgressBar, QMessageBox,
    QFrame, QSizePolicy, QMenu, QTextEdit
)
from PySide6.QtGui import QFont, QAction, QCursor

from src.delicious_town_bot.actions.user_card import UserCardAction


class EquipmentLoadWorker(QThread):
    """装备数据加载工作线程"""
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, user_card_action: UserCardAction):
        super().__init__()
        self.user_card_action = user_card_action
        
    def run(self):
        """加载所有装备数据"""
        try:
            self.progress.emit("正在加载装备数据...")
            
            # 装备部位类型映射
            part_types = {
                1: "铲子",
                2: "刀具", 
                3: "锅具",
                4: "调料瓶",
                5: "厨师帽"
            }
            
            all_equipment = {}
            total_count = 0
            
            # 获取每个部位的装备
            for part_type, part_name in part_types.items():
                self.progress.emit(f"正在加载{part_name}...")
                
                equipment_result = self.user_card_action.get_equipment_list(part_type=part_type)
                if equipment_result.get("success"):
                    equipment_list = equipment_result.get("equipment_list", [])
                    all_equipment[part_type] = {
                        "name": part_name,
                        "equipment_list": equipment_list,
                        "count": len(equipment_list)
                    }
                    total_count += len(equipment_list)
                else:
                    all_equipment[part_type] = {
                        "name": part_name,
                        "equipment_list": [],
                        "count": 0
                    }
            
            # 获取见习装备统计
            self.progress.emit("正在统计见习装备...")
            novice_result = self.user_card_action.get_novice_equipment_count()
            
            result = {
                "success": True,
                "all_equipment": all_equipment,
                "total_count": total_count,
                "novice_equipment": novice_result.get("novice_equipment", {}),
                "novice_total": novice_result.get("total_count", 0)
            }
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(f"加载装备数据失败: {str(e)}")


class EquipmentInventoryDialog(QDialog):
    """厨具库存查看对话框"""
    
    # 操作结果信号
    operation_result = Signal(str, str)  # operation_type, message
    
    def __init__(self, user_card_action: UserCardAction, username: str, parent=None):
        super().__init__(parent)
        self.user_card_action = user_card_action
        self.username = username
        self.equipment_data = {}
        self.parent_page = parent
        
        self.setWindowTitle(f"厨具库存 - {username}")
        self.setModal(True)
        self.resize(900, 600)
        
        self.setupUI()
        self.load_equipment_data()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        title_label = QLabel(f"厨具库存 - {self.username}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.load_equipment_data)
        
        self.auto_equip_btn = QPushButton("🎯 一键装备最优厨具")
        self.auto_equip_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px 12px; }")
        self.auto_equip_btn.clicked.connect(self.start_auto_equip)
        self.auto_equip_btn.setEnabled(False)  # 初始禁用，数据加载完成后启用
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.auto_equip_btn)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # 统计信息
        self.stats_group = QGroupBox("库存统计")
        stats_layout = QHBoxLayout(self.stats_group)
        
        self.total_label = QLabel("总装备: 0 件")
        self.novice_label = QLabel("见习装备: 0 件")
        self.using_label = QLabel("使用中: 0 件")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.novice_label)
        stats_layout.addWidget(self.using_label)
        stats_layout.addStretch()
        
        layout.addWidget(self.stats_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("正在加载数据...")
        layout.addWidget(self.status_label)
        
        # 装备分类标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各部位标签页
        self.part_tabs = {}
        part_types = {
            1: "铲子",
            2: "刀具", 
            3: "锅具",
            4: "调料瓶",
            5: "厨师帽"
        }
        
        for part_type, part_name in part_types.items():
            tab_widget = self.create_equipment_tab(part_type, part_name)
            self.tab_widget.addTab(tab_widget, part_name)
            self.part_tabs[part_type] = tab_widget
        
        # 见习装备专用标签页
        novice_tab = self.create_novice_equipment_tab()
        self.tab_widget.addTab(novice_tab, "见习装备")
        
        # 操作反馈区域
        feedback_group = QGroupBox("操作反馈")
        feedback_layout = QVBoxLayout(feedback_group)
        
        self.feedback_text = QTextEdit()
        self.feedback_text.setMaximumHeight(100)
        self.feedback_text.setReadOnly(True)
        self.feedback_text.setPlaceholderText("装备操作结果将在此显示...")
        feedback_layout.addWidget(self.feedback_text)
        
        layout.addWidget(feedback_group)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def create_equipment_tab(self, part_type: int, part_name: str):
        """创建装备部位标签页"""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        # 部位信息
        info_layout = QHBoxLayout()
        count_label = QLabel(f"{part_name}: 0 件")
        count_label.setObjectName(f"count_label_{part_type}")
        
        info_layout.addWidget(count_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # 装备列表表格
        table = QTableWidget()
        table.setObjectName(f"table_{part_type}")
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels([
            "装备名称", "等级", "强化", "使用状态", "火候", "厨艺", "刀工", "调味", "创意", "幸运"
        ])
        
        # 设置表格属性
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        
        # 添加右键菜单
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda pos: self.show_equipment_context_menu(table, pos))
        
        layout.addWidget(table)
        
        return widget
    
    def create_novice_equipment_tab(self):
        """创建见习装备专用标签页"""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        # 见习装备统计
        stats_group = QGroupBox("见习装备统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.novice_stats_labels = {}
        novice_names = ["见习之铲", "见习之刀", "见习之锅"]
        
        for name in novice_names:
            label = QLabel(f"{name}: 0 件")
            stats_layout.addWidget(label)
            self.novice_stats_labels[name] = label
        
        layout.addWidget(stats_group)
        
        # 见习装备详细列表
        self.novice_table = QTableWidget()
        self.novice_table.setColumnCount(6)
        self.novice_table.setHorizontalHeaderLabels([
            "装备名称", "强化等级", "强化名称", "使用状态", "总属性", "备注"
        ])
        
        self.novice_table.verticalHeader().setVisible(False)
        self.novice_table.setAlternatingRowColors(True)
        self.novice_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.novice_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.novice_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.novice_table)
        
        return widget
    
    def load_equipment_data(self):
        """加载装备数据"""
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度
        self.status_label.setText("正在加载装备数据...")
        
        # 启动加载线程
        self.load_worker = EquipmentLoadWorker(self.user_card_action)
        self.load_worker.finished.connect(self.on_equipment_loaded)
        self.load_worker.error.connect(self.on_load_error)
        self.load_worker.progress.connect(self.on_load_progress)
        self.load_worker.start()
    
    def on_load_progress(self, message: str):
        """加载进度更新"""
        self.status_label.setText(message)
    
    def on_equipment_loaded(self, data: Dict[str, Any]):
        """装备数据加载完成"""
        self.equipment_data = data
        self.update_equipment_display()
        
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.auto_equip_btn.setEnabled(True)  # 数据加载完成后启用一键装备按钮
        self.status_label.setText(f"加载完成 - 总计 {data.get('total_count', 0)} 件装备")
    
    def on_load_error(self, error_msg: str):
        """加载错误处理"""
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.status_label.setText(f"加载失败: {error_msg}")
        QMessageBox.critical(self, "加载失败", error_msg)
    
    def update_equipment_display(self):
        """更新装备显示"""
        if not self.equipment_data:
            return
        
        all_equipment = self.equipment_data.get("all_equipment", {})
        total_count = self.equipment_data.get("total_count", 0)
        novice_equipment = self.equipment_data.get("novice_equipment", {})
        novice_total = self.equipment_data.get("novice_total", 0)
        
        # 更新统计信息
        using_count = 0
        for part_data in all_equipment.values():
            for equipment in part_data.get("equipment_list", []):
                if equipment.get("is_use", False):
                    using_count += 1
        
        self.total_label.setText(f"总装备: {total_count} 件")
        self.novice_label.setText(f"见习装备: {novice_total} 件")
        self.using_label.setText(f"使用中: {using_count} 件")
        
        # 更新各部位装备表格
        for part_type, part_data in all_equipment.items():
            self.update_part_equipment_table(part_type, part_data)
        
        # 更新见习装备统计
        for name, data in novice_equipment.items():
            count = data.get("count", 0)
            if name in self.novice_stats_labels:
                self.novice_stats_labels[name].setText(f"{name}: {count} 件")
        
        # 更新见习装备详细表格
        self.update_novice_equipment_table(novice_equipment)
    
    def update_part_equipment_table(self, part_type: int, part_data: Dict[str, Any]):
        """更新部位装备表格"""
        part_name = part_data.get("name", "")
        equipment_list = part_data.get("equipment_list", [])
        count = part_data.get("count", 0)
        
        # 更新数量标签
        count_label = self.part_tabs[part_type].findChild(QLabel, f"count_label_{part_type}")
        if count_label:
            count_label.setText(f"{part_name}: {count} 件")
        
        # 更新表格
        table = self.part_tabs[part_type].findChild(QTableWidget, f"table_{part_type}")
        if not table:
            return
        
        table.setRowCount(0)
        
        for equipment in equipment_list:
            row = table.rowCount()
            table.insertRow(row)
            
            # 装备名称
            name_item = QTableWidgetItem(equipment.get("name", ""))
            # 将装备信息存储到表格项中
            name_item.setData(Qt.ItemDataRole.UserRole, {
                "id": equipment.get("id"),
                "name": equipment.get("name"),
                "part_name": equipment.get("part_name"),
                "strengthen_num": equipment.get("strengthen_num", 0),
                "strengthen_name": equipment.get("strengthen_name", ""),
                "is_use": equipment.get("is_use", False)
            })
            table.setItem(row, 0, name_item)
            
            # 等级
            level_item = QTableWidgetItem(str(equipment.get("level", 0)))
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 1, level_item)
            
            # 强化
            strengthen = equipment.get("strengthen_num", 0)
            strengthen_name = equipment.get("strengthen_name", "")
            strengthen_text = f"+{strengthen} {strengthen_name}" if strengthen > 0 else "--"
            strengthen_item = QTableWidgetItem(strengthen_text)
            strengthen_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, strengthen_item)
            
            # 使用状态
            is_use = equipment.get("is_use", False)
            use_text = "✅ 使用中" if is_use else "🔄 仓库中"
            use_item = QTableWidgetItem(use_text)
            use_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 3, use_item)
            
            # 属性值
            total_attrs = equipment.get("total_attributes", {})
            attributes = ["fire", "cooking", "sword", "season", "originality", "luck"]
            for i, attr in enumerate(attributes):
                value = total_attrs.get(attr, 0)
                attr_item = QTableWidgetItem(str(value))
                attr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, i + 4, attr_item)
    
    def update_novice_equipment_table(self, novice_equipment: Dict[str, Any]):
        """更新见习装备详细表格"""
        self.novice_table.setRowCount(0)
        
        for name, data in novice_equipment.items():
            items = data.get("items", [])
            
            for item in items:
                row = self.novice_table.rowCount()
                self.novice_table.insertRow(row)
                
                # 装备名称
                name_item = QTableWidgetItem(name)
                self.novice_table.setItem(row, 0, name_item)
                
                # 强化等级
                strengthen_num = item.get("strengthen_num", 0)
                strengthen_item = QTableWidgetItem(f"+{strengthen_num}")
                strengthen_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.novice_table.setItem(row, 1, strengthen_item)
                
                # 强化名称
                strengthen_name = item.get("strengthen_name", "")
                strengthen_name_item = QTableWidgetItem(strengthen_name or "--")
                self.novice_table.setItem(row, 2, strengthen_name_item)
                
                # 使用状态
                is_use = item.get("is_use", False)
                use_text = "✅ 使用中" if is_use else "🔄 仓库中"
                use_item = QTableWidgetItem(use_text)
                use_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.novice_table.setItem(row, 3, use_item)
                
                # 总属性 (见习装备属性较低，显示总和)
                total_attrs = 6 * strengthen_num  # 见习装备每强化等级增加6点属性
                total_item = QTableWidgetItem(str(total_attrs))
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.novice_table.setItem(row, 4, total_item)
                
                # 备注
                remark = "基础装备" if strengthen_num == 0 else f"强化{strengthen_num}级"
                remark_item = QTableWidgetItem(remark)
                self.novice_table.setItem(row, 5, remark_item)
    
    def show_equipment_context_menu(self, table: QTableWidget, position):
        """显示装备右键菜单"""
        if table.itemAt(position) is None:
            return
        
        current_row = table.currentRow()
        if current_row < 0:
            return
        
        # 获取装备信息
        equipment_info = self.get_equipment_info_from_table(table, current_row)
        if not equipment_info:
            return
        
        # 创建右键菜单
        menu = QMenu(self)
        
        # 强化动作
        enhance_action = QAction("🔧 强化装备", self)
        enhance_action.triggered.connect(lambda: self.enhance_equipment(equipment_info))
        menu.addAction(enhance_action)
        
        # 分解动作
        resolve_action = QAction("⚡ 分解装备", self)
        resolve_action.triggered.connect(lambda: self.resolve_equipment(equipment_info))
        menu.addAction(resolve_action)
        
        # 装备动作 (所有厨具都显示装备选项，后端自动处理替换)
        menu.addSeparator()
        equip_action = QAction("🛡️ 装备厨具", self)
        equip_action.triggered.connect(lambda: self.equip_equipment(equipment_info))
        menu.addAction(equip_action)
        
        # 显示菜单
        menu.exec(table.mapToGlobal(position))
    
    def get_equipment_info_from_table(self, table: QTableWidget, row: int) -> Dict[str, Any]:
        """从表格行获取装备信息"""
        if row < 0 or row >= table.rowCount():
            return {}
        
        # 直接从表格项的UserRole中获取装备信息
        name_item = table.item(row, 0)
        if name_item:
            equipment_info = name_item.data(Qt.ItemDataRole.UserRole)
            if isinstance(equipment_info, dict):
                return equipment_info
        
        return {}
    
    def enhance_equipment(self, equipment_info: Dict[str, Any]):
        """强化装备"""
        equipment_id = equipment_info.get("id")
        equipment_name = equipment_info.get("name")
        is_use = equipment_info.get("is_use", False)
        
        if not equipment_id:
            QMessageBox.warning(self, "错误", "无法获取装备ID")
            return
        
        # 检查是否正在使用
        if is_use:
            reply = QMessageBox.question(
                self, "确认强化", 
                f"装备 '{equipment_name}' 正在使用中，确定要强化吗？\\n\\n"
                "注意：强化可能会消耗材料且有失败风险",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        else:
            reply = QMessageBox.question(
                self, "确认强化", 
                f"确定要强化装备 '{equipment_name}' 吗？\\n\\n"
                "注意：强化可能会消耗材料且有失败风险",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 执行强化
        self.feedback_text.append(f"🔧 正在强化装备: {equipment_name}...")
        
        try:
            result = self.user_card_action.intensify_equipment(equipment_id)
            
            if result.get("success"):
                message = result.get("message", "强化成功")
                enhance_result = result.get("enhance_result", {})
                
                feedback = f"✅ 强化成功: {equipment_name}\\n"
                feedback += f"   结果: {message}\\n"
                
                # 显示属性提升
                attributes = enhance_result.get("attributes", [])
                if attributes:
                    feedback += "   属性提升: "
                    attr_texts = [f"{attr['name']}+{attr['increase']}" for attr in attributes]
                    feedback += ", ".join(attr_texts)
                
                self.feedback_text.append(feedback)
                
                # 通知父窗口
                self.operation_result.emit("强化", f"✅ {equipment_name} 强化成功")
                
                # 刷新装备数据
                self.load_equipment_data()
                
            else:
                error_msg = result.get("message", "强化失败")
                self.feedback_text.append(f"❌ 强化失败: {equipment_name}\\n   错误: {error_msg}")
        
        except Exception as e:
            self.feedback_text.append(f"❌ 强化异常: {equipment_name}\\n   错误: {str(e)}")
    
    def resolve_equipment(self, equipment_info: Dict[str, Any]):
        """分解装备"""
        equipment_id = equipment_info.get("id")
        equipment_name = equipment_info.get("name")
        is_use = equipment_info.get("is_use", False)
        
        if not equipment_id:
            QMessageBox.warning(self, "错误", "无法获取装备ID")
            return
        
        # 检查是否正在使用
        if is_use:
            QMessageBox.warning(
                self, "无法分解", 
                f"装备 '{equipment_name}' 正在使用中，无法分解！\\n\\n"
                "请先卸下装备再进行分解操作。"
            )
            return
        
        # 确认分解
        reply = QMessageBox.question(
            self, "确认分解", 
            f"确定要分解装备 '{equipment_name}' 吗？\\n\\n"
            "⚠️ 警告：分解后装备将永久消失，此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 执行分解
        self.feedback_text.append(f"⚡ 正在分解装备: {equipment_name}...")
        
        try:
            result = self.user_card_action.resolve_equipment(equipment_id)
            
            if result.get("success"):
                message = result.get("message", "分解成功")
                resolve_result = result.get("resolve_result", {})
                
                feedback = f"✅ 分解成功: {equipment_name}\\n"
                feedback += f"   结果: {message}\\n"
                
                # 显示获得的物品
                items = resolve_result.get("items", [])
                if items:
                    feedback += "   获得物品: "
                    item_texts = [f"{item['name']}+{item['quantity']}" for item in items]
                    feedback += ", ".join(item_texts)
                
                self.feedback_text.append(feedback)
                
                # 通知父窗口
                self.operation_result.emit("分解", f"✅ {equipment_name} 分解成功")
                
                # 刷新装备数据
                self.load_equipment_data()
                
            else:
                error_msg = result.get("message", "分解失败")
                self.feedback_text.append(f"❌ 分解失败: {equipment_name}\\n   错误: {error_msg}")
        
        except Exception as e:
            self.feedback_text.append(f"❌ 分解异常: {equipment_name}\\n   错误: {str(e)}")
    
    def equip_equipment(self, equipment_info: Dict[str, Any]):
        """装备厨具"""
        equipment_id = equipment_info.get("id")
        equipment_name = equipment_info.get("name")
        is_use = equipment_info.get("is_use", False)
        
        if not equipment_id:
            QMessageBox.warning(self, "错误", "无法获取装备ID")
            return
        
        # 调试信息
        print(f"[Debug] 装备厨具: ID={equipment_id}, Name={equipment_name}, is_use={is_use}")
        
        # 确认装备
        reply = QMessageBox.question(
            self, "确认装备", 
            f"确定要装备 '{equipment_name}' (ID: {equipment_id}) 吗？\\n\\n"
            "如果已有同类型装备将自动替换。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 执行装备
        self.feedback_text.append(f"🛡️ 正在装备厨具: {equipment_name} (ID: {equipment_id})...")
        
        try:
            result = self.user_card_action.equip_equipment(equipment_id)
            
            if result.get("success"):
                message = result.get("message", "装备成功")
                
                feedback = f"✅ 装备成功: {equipment_name}\\n"
                feedback += f"   结果: {message}"
                
                self.feedback_text.append(feedback)
                
                # 通知父窗口
                self.operation_result.emit("装备", f"✅ {equipment_name} 装备成功")
                
                # 刷新装备数据
                self.load_equipment_data()
                
            else:
                error_msg = result.get("message", "装备失败")
                self.feedback_text.append(f"❌ 装备失败: {equipment_name}\\n   错误: {error_msg}")
        
        except Exception as e:
            self.feedback_text.append(f"❌ 装备异常: {equipment_name}\\n   错误: {str(e)}")

    def calculate_equipment_real_power(self, equipment_data: Dict[str, Any]) -> float:
        """计算单件厨具的真实厨力"""
        # 真实厨力权重
        weights = {
            "cooking": 1.44,    # 厨艺
            "sword": 1.41,      # 刀工  
            "season": 1.5,      # 调味
            "fire": 1.71,       # 火候
            "originality": 2.25, # 创意
            "luck": 0.0         # 幸运不计入真实厨力
        }
        
        total_power = 0.0
        
        # 调试输出：显示原始装备数据
        equipment_name = equipment_data.get("name", "未知装备")
        print(f"[Debug] 计算 {equipment_name} 的真实厨力")
        print(f"[Debug] 原始数据: {equipment_data}")
        
        # 适配多种可能的数据结构
        # 结构1: total_attributes (总属性值)
        total_attributes = equipment_data.get("total_attributes", {})
        
        # 结构2: base_ + strengthen_ + hole_ 分别字段  
        base_attributes = {}
        strengthen_adds = {}
        hole_adds = equipment_data.get("hole_adds", {})
        
        # 尝试多种基础属性字段名组合
        for attr in weights.keys():
            # 基础属性可能的字段名
            base_key_options = [f"base_{attr}", attr]
            for base_key in base_key_options:
                if base_key in equipment_data:
                    base_attributes[attr] = equipment_data[base_key]
                    break
            
            # 强化属性可能的字段名
            enhance_key_options = [f"strengthen_{attr}", f"{attr}_add"]
            for enhance_key in enhance_key_options:
                if enhance_key in equipment_data:
                    strengthen_adds[f"{attr}_add"] = equipment_data[enhance_key]
                    break
        
        # 结构3: attributes + attribute_adds 格式
        if not base_attributes:
            base_attributes = equipment_data.get("base_attributes", equipment_data.get("attributes", {}))
        if not strengthen_adds:
            strengthen_adds = equipment_data.get("strengthen_adds", equipment_data.get("attribute_adds", {}))
        
        print(f"[Debug] 解析结果:")
        print(f"[Debug]   total_attributes: {total_attributes}")
        print(f"[Debug]   base_attributes: {base_attributes}")
        print(f"[Debug]   strengthen_adds: {strengthen_adds}")
        print(f"[Debug]   hole_adds: {hole_adds}")
        
        # 计算真实厨力
        for attr, weight in weights.items():
            attr_total = 0
            calculation_method = ""
            
            if total_attributes and attr in total_attributes:
                # 方法1: 直接使用总属性值
                raw_value = total_attributes.get(attr, 0)
                try:
                    attr_total = int(raw_value) if raw_value else 0
                    calculation_method = f"total[{attr}] = {raw_value} → {attr_total}"
                except (ValueError, TypeError):
                    attr_total = 0
                    calculation_method = f"total[{attr}] = {raw_value} (转换失败) → 0"
            else:
                # 方法2: 分别计算
                base_value = base_attributes.get(attr, 0)
                enhance_add = strengthen_adds.get(f"{attr}_add", 0)
                hole_add = hole_adds.get(f"{attr}_hole_add", 0)
                
                # 确保数值类型
                try:
                    base_value = int(base_value) if base_value else 0
                    enhance_add = int(enhance_add) if enhance_add else 0
                    hole_add = int(hole_add) if hole_add else 0
                except (ValueError, TypeError):
                    base_value = enhance_add = hole_add = 0
                
                attr_total = base_value + enhance_add + hole_add
                calculation_method = f"{base_value}+{enhance_add}+{hole_add} = {attr_total}"
            
            attr_power = attr_total * weight
            total_power += attr_power
            
            if attr != 'luck':  # 幸运权重为0，不显示详细计算
                print(f"[Debug]   {attr}: {calculation_method} × {weight} = {attr_power:.2f}")
        
        print(f"[Debug] {equipment_name} 真实厨力总计: {total_power:.2f}")
        print()
        
        return round(total_power, 2)

    def start_auto_equip(self):
        """开始一键装备最优厨具"""
        if not self.equipment_data or not self.equipment_data.get("success"):
            QMessageBox.warning(self, "提示", "装备数据未加载或加载失败")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认一键装备",
            "确定要根据真实厨力自动装备最优厨具吗？\n\n"
            "⚠️ 注意事项：\n"
            "• 系统会计算每件厨具的真实厨力\n"
            "• 每个部位选择真实厨力最高的装备\n"
            "• 当前装备会被自动替换\n"
            "• 此操作不可撤销\n\n"
            "真实厨力计算公式：\n"
            "厨艺×1.44 + 刀工×1.41 + 调味×1.5 + 火候×1.71 + 创意×2.25",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用按钮，防止重复点击
        self.auto_equip_btn.setEnabled(False)
        self.auto_equip_btn.setText("正在装备...")
        
        try:
            # 执行一键装备
            result = self.execute_auto_equip()
            
            # 显示结果
            self.show_auto_equip_result(result)
            
            # 刷新装备数据显示
            self.load_equipment_data()
            
        except Exception as e:
            error_msg = f"一键装备失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.feedback_text.append(f"❌ {error_msg}")
        
        finally:
            self.auto_equip_btn.setEnabled(True)
            self.auto_equip_btn.setText("🎯 一键装备最优厨具")

    def execute_auto_equip(self) -> Dict[str, Any]:
        """执行一键装备逻辑"""
        import time
        
        all_equipment = self.equipment_data.get("all_equipment", {})
        
        result = {
            "success": False,
            "message": "",
            "equipped_items": [],
            "skipped_items": [],
            "total_power_change": 0.0
        }
        
        # 记录装备前的真实厨力
        original_power_result = self.user_card_action.get_user_card()
        original_total_power = 0.0
        if original_power_result.get("success"):
            cooking_power = original_power_result.get("cooking_power", {})
            # 使用当前装备计算真实厨力
            original_total_power = self.calculate_current_total_real_power()
        
        # 为每个部位选择最优装备
        for part_type, part_data in all_equipment.items():
            part_name = part_data.get("name", f"部位{part_type}")
            equipment_list = part_data.get("equipment_list", [])
            
            if not equipment_list:
                result["skipped_items"].append({
                    "part_name": part_name,
                    "reason": "无可用装备"
                })
                continue
            
            self.feedback_text.append(f"🔍 分析{part_name}装备...")
            
            # 计算每件装备的真实厨力并找出最优的
            best_equipment = None
            best_power = -1.0
            
            self.feedback_text.append(f"📊 {part_name}装备真实厨力分析:")
            
            current_equipped = None  # 记录当前已装备的装备
            
            for equipment in equipment_list:
                equipment_name = equipment.get("name", "未知装备")
                is_equipped = equipment.get("is_use", False)
                
                # 记录当前已装备的装备
                if is_equipped:
                    current_equipped = equipment
                
                # 计算这件装备的真实厨力
                power = self.calculate_equipment_real_power(equipment)
                
                # 调试输出：显示装备的属性数据
                total_attrs = equipment.get("total_attributes", {})
                if total_attrs:
                    attr_str = f"厨艺{total_attrs.get('cooking', 0)} 刀工{total_attrs.get('sword', 0)} 调味{total_attrs.get('season', 0)} 火候{total_attrs.get('fire', 0)} 创意{total_attrs.get('originality', 0)}"
                    status_icon = "⚡" if is_equipped else "🔍"
                    status_text = "(当前装备)" if is_equipped else ""
                    self.feedback_text.append(f"   {status_icon} {equipment_name}: {attr_str} → 真实厨力 {power} {status_text}")
                else:
                    status_icon = "⚡" if is_equipped else "⚠️"
                    status_text = "(当前装备)" if is_equipped else ""
                    self.feedback_text.append(f"   {status_icon} {equipment_name}: 无属性数据 → 真实厨力 {power} {status_text}")
                
                # 更新最优装备（包括已装备的）
                if power > best_power:
                    best_power = power
                    best_equipment = equipment
            
            if not best_equipment:
                result["skipped_items"].append({
                    "part_name": part_name,
                    "reason": "无可用装备"
                })
                continue
            
            # 获取最优装备信息
            equipment_id = best_equipment.get("id")
            equipment_name = best_equipment.get("name", "未知装备")
            is_best_equipped = best_equipment.get("is_use", False)
            
            self.feedback_text.append(
                f"🎯 {part_name}最优装备: {equipment_name} (真实厨力: {best_power})"
            )
            
            # 判断是否需要装备
            if is_best_equipped:
                # 最优装备已经是当前装备，无需更换
                result["skipped_items"].append({
                    "part_name": part_name,
                    "equipment_name": equipment_name,
                    "reason": "当前装备已是最优"
                })
                
                self.feedback_text.append(f"⏭️ {part_name}: {equipment_name} 已是最优装备，无需更换")
                continue
            
            # 装备最优装备
            try:
                equip_result = self.user_card_action.equip_equipment(equipment_id)
                
                if equip_result.get("success"):
                    result["equipped_items"].append({
                        "part_name": part_name,
                        "equipment_name": equipment_name,
                        "equipment_id": equipment_id,
                        "real_power": best_power,
                        "current_equipped": current_equipped.get("name", "未知") if current_equipped else "无",
                        "message": equip_result.get("message", "装备成功")
                    })
                    
                    current_name = current_equipped.get("name", "未知装备") if current_equipped else "无装备"
                    self.feedback_text.append(f"✅ {part_name}: {current_name} → {equipment_name} 装备成功")
                    
                else:
                    result["skipped_items"].append({
                        "part_name": part_name,
                        "equipment_name": equipment_name,
                        "reason": equip_result.get("message", "装备失败")
                    })
                    
                    self.feedback_text.append(f"❌ {part_name}: {equipment_name} 装备失败 - {equip_result.get('message', '未知错误')}")
                
                # 装备间隔，避免请求过快
                time.sleep(0.3)
                
            except Exception as e:
                result["skipped_items"].append({
                    "part_name": part_name,
                    "equipment_name": equipment_name,
                    "reason": f"装备异常: {str(e)}"
                })
        
        # 计算装备后的真实厨力变化
        try:
            new_power_result = self.user_card_action.get_user_card()
            if new_power_result.get("success"):
                new_total_power = self.calculate_current_total_real_power()
                result["total_power_change"] = new_total_power - original_total_power
        except:
            result["total_power_change"] = 0.0
        
        # 生成结果消息
        equipped_count = len(result["equipped_items"])
        skipped_count = len(result["skipped_items"])
        
        if equipped_count > 0:
            result["success"] = True
            result["message"] = f"✅ 一键装备完成！成功装备 {equipped_count} 件装备"
            if result["total_power_change"] > 0:
                result["message"] += f"，真实厨力提升 {result['total_power_change']:.2f}"
        else:
            result["message"] = f"ℹ️ 一键装备完成，没有需要更换的装备"
        
        return result

    def calculate_current_total_real_power(self) -> float:
        """计算当前装备的总真实厨力"""
        try:
            user_card = self.user_card_action.get_user_card()
            if not user_card.get("success"):
                return 0.0
            
            cooking_power = user_card.get("cooking_power", {})
            speciality = user_card.get("speciality", {})
            
            # 使用现有的真实厨力计算方法
            power_result = self.user_card_action.calculate_real_cooking_power(
                cooking_power, speciality
            )
            
            return power_result.get("total_real_power", 0.0)
            
        except Exception as e:
            print(f"[Warning] 计算当前真实厨力失败: {e}")
            return 0.0

    def show_auto_equip_result(self, result: Dict[str, Any]):
        """显示一键装备结果"""
        equipped_items = result.get("equipped_items", [])
        skipped_items = result.get("skipped_items", [])
        power_change = result.get("total_power_change", 0.0)
        
        # 构建详细结果文本
        details = [result.get("message", "")]
        details.append("")
        
        if equipped_items:
            details.append(f"✅ 成功装备 ({len(equipped_items)} 件):")
            for item in equipped_items:
                details.append(
                    f"   • {item['part_name']}: {item['equipment_name']} "
                    f"(真实厨力: {item['real_power']})"
                )
        
        if skipped_items:
            details.append("")
            details.append(f"⏭️ 跳过装备 ({len(skipped_items)} 件):")
            for item in skipped_items:
                equipment_name = item.get('equipment_name', '')
                name_part = f" {equipment_name}" if equipment_name else ""
                details.append(f"   • {item['part_name']}{name_part}: {item['reason']}")
        
        if power_change != 0:
            details.append("")
            if power_change > 0:
                details.append(f"📈 真实厨力提升: +{power_change:.2f}")
            else:
                details.append(f"📉 真实厨力变化: {power_change:.2f}")
        
        message_text = "\\n".join(details)
        
        # 显示结果对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("一键装备结果")
        msg_box.setText(result.get("message", ""))
        msg_box.setDetailedText(message_text)
        
        if result.get("success") and equipped_items:
            msg_box.setIcon(QMessageBox.Icon.Information)
        else:
            msg_box.setIcon(QMessageBox.Icon.Information)
        
        msg_box.exec()
        
        # 通知父窗口刷新数据
        if hasattr(self, 'operation_result'):
            self.operation_result.emit("一键装备", result.get("message", ""))
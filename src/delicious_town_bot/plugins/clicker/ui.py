import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QLineEdit, QApplication, QFrame, QGridLayout, QListWidget, QListWidgetItem,
    QMainWindow, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout,
    QWidget, QLabel, QPushButton, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QInputDialog, QMessageBox, QComboBox, QHeaderView
)

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.utils.depot_manager import DepotManager
from src.delicious_town_bot.constants import ItemType, Street
from src.delicious_town_bot.plugins.clicker.game_operations_page import GameOperationsPage
from src.delicious_town_bot.plugins.clicker.cookbook_page import CookbookPage
from src.delicious_town_bot.plugins.clicker.tower_challenge_page import TowerChallengePage
from src.delicious_town_bot.plugins.clicker.user_power_page import UserPowerPage
from src.delicious_town_bot.plugins.clicker.daily_tasks_page import DailyTasksPage
from src.delicious_town_bot.plugins.clicker.match_ranking_page import MatchRankingPage
from src.delicious_town_bot.plugins.clicker.specialty_food_page import SpecialtyFoodPage
from src.delicious_town_bot.plugins.clicker.vip_page import VipPage


# Card, make_simple_page, AccountsPage 类保持不变...
class Card(QFrame):
    def __init__(self, title: str, note: str = ""):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)  # 减少卡片内边距
        layout.setSpacing(6)  # 减少组件间距
        lbl_title = QLabel(title)
        lbl_title.setProperty("role", "Title")
        layout.addWidget(lbl_title)
        if note:
            lbl_note = QLabel(note)
            lbl_note.setProperty("role", "Note")
            layout.addWidget(lbl_note)
        layout.addStretch()


def make_simple_page(cards: List[Tuple[str, str]]) -> QWidget:
    page = QWidget()
    grid = QGridLayout(page)
    grid.setContentsMargins(16, 16, 16, 16)  # 减少页面边距
    grid.setHorizontalSpacing(12)  # 减少水平间距
    grid.setVerticalSpacing(12)  # 减少垂直间距
    for idx, (t, n) in enumerate(cards):
        card = Card(t, n)
        row, col = divmod(idx, 2)
        grid.addWidget(card, row, col)
    return page


class AccountsPage(QWidget):
    def __init__(self, log_widget: QTextEdit, manager: AccountManager, depot_manager: DepotManager):
        super().__init__()
        self.log_widget = log_widget
        self.manager = manager
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        btn_add = QPushButton("新增账号")
        btn_del = QPushButton("删除账号")
        btn_refresh = QPushButton("刷新 Key")
        btn_reload = QPushButton("刷新列表")
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_del)
        toolbar.addWidget(btn_refresh)
        toolbar.addWidget(btn_reload)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "用户名", "餐厅", "Key?", "最后登录"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.setMaximumHeight(400)  # 限制账号表格高度，避免界面过高
        layout.addWidget(self.table)
        self.load_accounts()
        btn_add.clicked.connect(self.add_account)
        btn_del.clicked.connect(self.delete_account)
        btn_refresh.clicked.connect(self.refresh_selected)
        btn_reload.clicked.connect(self.reload_table)
        self.table.itemDoubleClicked.connect(self.refresh_single)

    def load_accounts(self):
        self.table.setRowCount(0)
        accounts = self.manager.list_accounts()
        for acc in accounts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            cells = [str(acc.id), acc.username, acc.restaurant or "-", "Y" if acc.key else "N",
                     acc.last_login.strftime("%Y-%m-%d %H:%M") if acc.last_login else "-"]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

    def add_account(self):
        username, ok1 = QInputDialog.getText(self, "新增账号", "用户名:")
        if not ok1 or not username: return
        password, ok2 = QInputDialog.getText(self, "新增账号", "密码:", echo=QLineEdit.EchoMode.Password)
        if not ok2 or not password: return
        try:
            acc = self.manager.add_account(username, password)
            self.log_widget.append(f"✅ 添加账号 ID={acc.id} 用户名={acc.username}")
            self.load_accounts()
        except Exception as e:
            QMessageBox.warning(self, "添加失败", str(e))

    def delete_account(self):
        selected = self.table.selectedItems()
        if not selected: QMessageBox.information(self, "提示", "请先选择一行"); return
        row = selected[0].row()
        acc_id = int(self.table.item(row, 0).text())
        confirm = QMessageBox.question(self, "删除确认", f"确定要删除 ID={acc_id} 吗？")
        if confirm != QMessageBox.StandardButton.Yes: return
        try:
            self.manager.delete_account(acc_id)
            self.log_widget.append(f"✅ 删除账号 ID={acc_id}")
            self.load_accounts()
        except Exception as e:
            QMessageBox.warning(self, "删除失败", str(e))

    def reload_table(self):
        self.load_accounts(); self.log_widget.append("🔄 已刷新账号列表")

    def _ids_from_selection(self):
        return [int(self.table.item(r.row(), 0).text()) for r in self.table.selectionModel().selectedRows()]

    def refresh_single(self, item):
        self._refresh_ids([int(self.table.item(item.row(), 0).text())])

    def _refresh_ids(self, ids: List[int]):
        for aid in ids:
            self.log_widget.append(f"🔄 刷新 ID={aid} …")
            new_key = self.manager.refresh_key(aid)
            if new_key:
                self.log_widget.append(f"    ✅ 新 key={new_key}")
            else:
                self.log_widget.append(f"    ⚠️ 刷新失败")
        self.load_accounts()

    def refresh_selected(self):
        ids = self._ids_from_selection()
        if not ids:
            ok = QMessageBox.question(self, "全部刷新？", "未选中任何行，是否刷新所有账号？",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes: return
            ids = [int(self.table.item(r, 0).text()) for r in range(self.table.rowCount())]
        self._refresh_ids(ids)


class WarehousePage(QWidget):
    def __init__(self, log_widget: QTextEdit, account_manager: AccountManager, depot_manager: DepotManager):
        super().__init__()
        self.log_widget = log_widget
        self.account_manager = account_manager
        self.depot_manager = depot_manager

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("选择账号:"))
        self.account_combo = QComboBox()
        self.account_combo.setMaxVisibleItems(15)
        self.account_combo.setMinimumWidth(150)  # [优化] 设置最小宽度
        toolbar.addWidget(self.account_combo)

        toolbar.addWidget(QLabel("物品分类:"))
        self.item_type_combo = QComboBox()
        self.item_type_combo.setMinimumWidth(120)  # [优化] 设置最小宽度
        toolbar.addWidget(self.item_type_combo)

        btn_query = QPushButton("查询物品")
        toolbar.addWidget(btn_query)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.items_table = QTableWidget()
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["物品名称", "数量", "操作"])
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.items_table.setColumnWidth(2, 180)
        self.items_table.setShowGrid(False)
        self.items_table.setMaximumHeight(400)  # 限制物品表格高度，避免界面过高
        layout.addWidget(self.items_table)

        self._populate_accounts()
        self._populate_item_types()
        btn_query.clicked.connect(self._fetch_and_display_items)

    def _populate_accounts(self):
        self.account_combo.clear()
        accounts = self.account_manager.list_accounts()
        for acc in accounts:
            self.account_combo.addItem(acc.username, userData=acc.id)

    def _populate_item_types(self):
        self.item_type_combo.clear()
        type_map = {"PROPS": "道具", "MATERIALS": "材料", "FACILITIES": "设施", "FRAGMENTS": "残卷"}
        for item_type in ItemType:
            self.item_type_combo.addItem(type_map.get(item_type.name, item_type.name), userData=item_type)

    @Slot()
    def _fetch_and_display_items(self):
        account_id = self.account_combo.currentData()
        item_type = self.item_type_combo.currentData()
        if account_id is None or item_type is None:
            QMessageBox.warning(self, "提示", "请先选择一个账号和物品分类")
            return

        username = self.account_combo.currentText()
        type_name = self.item_type_combo.currentText()
        self.log_widget.append(f"📦 正在查询 '{username}' 的仓库物品 (分类: {type_name})...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        items = self.depot_manager.get_items_for_account(account_id, item_type)
        self.items_table.setRowCount(0)
        for idx, item_data in enumerate(items, start=1):
            row, item_name, item_num, item_code = self.items_table.rowCount(), item_data.get('goods_name',
                                                                                             '未知物品'), item_data.get(
                'num', '?'), item_data.get('goods_code') or item_data.get('code')
            self.items_table.insertRow(row)
            display_name = f"{idx}. {item_name}"
            name_item = QTableWidgetItem(display_name)
            quantity_item = QTableWidgetItem(str(item_num))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            name_item.setData(Qt.ItemDataRole.UserRole, item_code)
            quantity_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_table.setItem(row, 0, name_item)
            self.items_table.setItem(row, 1, quantity_item)
            self._add_action_buttons(row, item_type)
        QApplication.restoreOverrideCursor()
        self.log_widget.append(f"✅ 查询完成，共找到 {len(items)} 种物品。")

    def _add_action_buttons(self, row: int, item_type: ItemType):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        btn_action = QPushButton("分解" if item_type == ItemType.FRAGMENTS else "使用")
        if item_type == ItemType.FRAGMENTS:
            btn_action.clicked.connect(lambda: self._decompose_item(row))
        else:
            btn_action.clicked.connect(lambda: self._use_item(row))
        layout.addWidget(btn_action)
        layout.addStretch()
        self.items_table.setCellWidget(row, 2, widget)

    def _use_item(self, row: int):
        account_id = self.account_combo.currentData()
        item_widget = self.items_table.item(row, 0)
        if not item_widget: return

        item_display_name = item_widget.text()
        item_name = ". ".join(item_display_name.split(". ")[1:])
        item_code = item_widget.data(Qt.ItemDataRole.UserRole)
        username = self.account_combo.currentText()
        step_2_data = None  # 默认为 None，即一步操作

        # [核心修改] 根据物品名称判断是否需要额外数据
        if "改名卡" in item_name:
            new_name, ok = QInputDialog.getText(self, "输入新名称", "请输入新的餐厅名称:")
            if not ok or not new_name.strip(): return  # 用户取消或输入为空
            step_2_data = new_name
        elif "搬家卡" in item_name:
            # 从 Street 枚举创建街道选项
            street_map = {s.name.capitalize(): s.value for s in Street if s.value > 0}  # 排除 CURRENT 和 HOMESTYLE
            street_name, ok = QInputDialog.getItem(self, "选择新街道", "请选择要搬往的街道:", street_map.keys(), 0,
                                                   False)
            if not ok: return  # 用户取消
            step_2_data = street_map[street_name]

        self.log_widget.append(f"🔧 用户 '{username}' 正在使用物品: {item_name} (code: {item_code})")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        success = self.depot_manager.use_item_for_account(account_id, item_code, step_2_data)

        QApplication.restoreOverrideCursor()
        if success:
            self.log_widget.append(f"    ✅ 物品 '{item_name}' 使用成功！")
            self._fetch_and_display_items()
        else:
            self.log_widget.append(f"    ❌ 物品 '{item_name}' 使用失败，请查看日志或游戏内提示。")

    def _decompose_item(self, row: int):
        # ... 此方法无需修改 ...
        account_id = self.account_combo.currentData()
        item_widget = self.items_table.item(row, 0)
        if not item_widget: return
        item_display_name, item_code, username = item_widget.text(), item_widget.data(
            Qt.ItemDataRole.UserRole), self.account_combo.currentText()
        item_name = ". ".join(item_display_name.split(". ")[1:])
        self.log_widget.append(f"🗑️ 用户 '{username}' 正在分解残卷: {item_name} (code: {item_code})")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        success = self.depot_manager.resolve_fragment_for_account(account_id, item_code)
        QApplication.restoreOverrideCursor()
        if success:
            self.log_widget.append(f"    ✅ 残卷 '{item_name}' 分解成功！")
            self._fetch_and_display_items()
        else:
            self.log_widget.append(f"    ❌ 残卷 '{item_name}' 分解失败。")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delicious Town Bot")
        self.resize(1200, 600)  # 小屏友好：降低高度，保持合理宽度
        self.account_manager, self.depot_manager = AccountManager(), DepotManager()
        self._init_ui()

    def _init_ui(self):
        sidebar, self.log = QListWidget(), QTextEdit()
        sidebar.setObjectName("SideBar")
        self.log.setObjectName("LogArea")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(80)  # 进一步减少日志区域高度
        nav_list = [
            ("账号管理", AccountsPage), 
            ("游戏操作", lambda log, acc_mgr, dep_mgr: GameOperationsPage(log, acc_mgr)),
            ("日常任务", lambda log, acc_mgr, dep_mgr: DailyTasksPage(acc_mgr, log)),
            ("食谱管理", lambda log, acc_mgr, dep_mgr: CookbookPage(log, acc_mgr)),
            ("厨塔挑战", lambda log, acc_mgr, dep_mgr: TowerChallengePage(acc_mgr, log)),
            ("厨力面板", lambda log, acc_mgr, dep_mgr: UserPowerPage(acc_mgr, log)),
            ("特色菜管理", lambda log, acc_mgr, dep_mgr: SpecialtyFoodPage()),
            ("VIP管理", lambda log, acc_mgr, dep_mgr: self._create_vip_page(acc_mgr, dep_mgr, log)),
            ("赛厨排行榜", lambda log, acc_mgr, dep_mgr: MatchRankingPage(log, acc_mgr)),
            ("仓库管理", WarehousePage),
            ("数据统计", lambda log, acc_mgr, dep_mgr: make_simple_page([("统计面板", "账号数据分析"), ("操作日志", "历史操作记录")]))
        ]
        stack = QStackedWidget()
        for title, page_factory in nav_list:
            item = QListWidgetItem(title)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            sidebar.addItem(item)
            widget = page_factory(self.log, self.account_manager, self.depot_manager)
            stack.addWidget(widget)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(stack)
        splitter.addWidget(self.log)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        root= QWidget()
        layout = QGridLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(sidebar, 0, 0)
        layout.addWidget(splitter, 0, 1)
        layout.setColumnStretch(1, 1)
        self.setCentralWidget(root)
        sidebar.currentRowChanged.connect(stack.setCurrentIndex)
        sidebar.setCurrentRow(0)
        sidebar.setFixedWidth(160)
        self.apply_qss()

    def _create_vip_page(self, account_manager: AccountManager, depot_manager: DepotManager, log_widget: QTextEdit) -> VipPage:
        """创建VIP管理页面并设置账号数据"""
        vip_page = VipPage()
        
        # 设置DepotManager到VIP页面
        vip_page.set_depot_manager(depot_manager)
        
        # 获取账号数据并转换格式
        accounts = account_manager.list_accounts()
        accounts_data = []
        
        for acc in accounts:
            account_data = {
                "username": acc.username,
                "key": acc.key,
                "cookie": {"PHPSESSID": acc.cookie} if acc.cookie else {},
                "restaurant_name": acc.restaurant or "未知餐厅",
                "id": acc.id
            }
            accounts_data.append(account_data)
        
        # 设置账号数据到VIP页面
        vip_page.set_accounts_data(accounts_data)
        
        # 连接账号选择器的刷新功能
        def refresh_accounts():
            updated_accounts = account_manager.list_accounts()
            updated_data = []
            for acc in updated_accounts:
                account_data = {
                    "username": acc.username,
                    "key": acc.key,
                    "cookie": {"PHPSESSID": acc.cookie} if acc.cookie else {},
                    "restaurant_name": acc.restaurant or "未知餐厅",
                    "id": acc.id
                }
                updated_data.append(account_data)
            vip_page.set_accounts_data(updated_data)
            log_widget.append("🔄 VIP页面账号数据已刷新")
        
        vip_page.account_selector.refresh_accounts = refresh_accounts
        
        return vip_page

    def closeEvent(self, event): self.account_manager.close(); self.depot_manager.close(); super().closeEvent(event)

    def apply_qss(self):
        self.setStyleSheet("""
        *{font-size:14px;}
        QListWidget#SideBar{background:#fafafa;border-right:1px solid #eee;}
        QListWidget::item{padding:10px 14px;}
        QListWidget::item:selected{background:#ff95651f;color:#ff6e3f;}
        QFrame#Card{background:white;border-radius:16px;border:1px solid #f0f0f0;}
        [role="Title"]{font-size:16px;font-weight:600;color:#333;}
        [role="Note"]{font-size:12px;color:#666;}
        QTextEdit#LogArea{background:#fafafa;color:#333;border:none;padding:8px;font-family:Monaco,Courier,monospace;font-size:13px;}
        QPushButton {padding: 5px 10px; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;}
        QPushButton:hover {background-color: #e0e0e0;} QPushButton:pressed {background-color: #d0d0d0;}
        QComboBox { padding: 4px; border: 1px solid #ccc; border-radius: 4px; combobox-popup: 0; }
        QTableWidget { border: none; gridline-color: transparent; }
        QTableWidget::item:alternate { background: #f7f7f7; }
        QHeaderView::section { background-color: #f2f2f2; padding: 6px; border: none; font-weight: 600; }
        QFrame#StatsPanel { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px; }
        QFrame#StatsPanel [role="Title"] { font-size: 16px; font-weight: 600; color: #2c3e50; margin-bottom: 8px; }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
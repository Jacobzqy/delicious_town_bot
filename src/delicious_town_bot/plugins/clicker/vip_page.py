"""
VIP管理页面
包括VIP购买、CDK兑换等功能的GUI界面
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QGroupBox, QLabel, QPushButton, QLineEdit, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QSpinBox, QTextBrowser, QProgressBar, QFrame
)
from PySide6.QtGui import QFont, QColor

from src.delicious_town_bot.actions.vip import VipAction
from src.delicious_town_bot.plugins.clicker.account_selector import AccountSelector
from src.delicious_town_bot.data.vip_shop_items import (
    VIP_SHOP_ITEMS, VIP_SHOP_CATEGORIES, VIP_SHOP_RARITY,
    RARITY_COLORS, get_item_by_id, validate_purchase
)


class CdkExchangeWorker(QObject):
    """CDK兑换工作线程"""
    exchange_completed = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, key: str, cookie: Dict[str, str], cdk_code: str):
        super().__init__()
        self.key = key
        self.cookie = cookie
        self.cdk_code = cdk_code
    
    def do_exchange(self):
        """执行CDK兑换"""
        try:
            vip_action = VipAction(self.key, self.cookie)
            result = vip_action.exchange_cdk(self.cdk_code)
            self.exchange_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"CDK兑换异常: {e}")


class VipInfoWorker(QObject):
    """VIP信息获取工作线程"""
    info_loaded = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, key: str, cookie: Dict[str, str]):
        super().__init__()
        self.key = key
        self.cookie = cookie
    
    def do_load_info(self):
        """加载VIP信息"""
        try:
            vip_action = VipAction(self.key, self.cookie)
            result = vip_action.get_vip_info()
            self.info_loaded.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"获取VIP信息异常: {e}")


class VipPurchaseWorker(QObject):
    """VIP购买工作线程（120钻石）"""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, key: str, cookie: Dict[str, str], cost_diamonds: int = 120):
        super().__init__()
        self.key = key
        self.cookie = cookie
        self.cost_diamonds = cost_diamonds
    
    def run(self):
        """执行VIP购买"""
        try:
            vip_action = VipAction(self.key, self.cookie)
            result = vip_action.purchase_vip(self.cost_diamonds)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"VIP购买异常: {e}")


class BatchCdkExchangeWorker(QObject):
    """批量CDK兑换工作线程"""
    exchange_completed = Signal(dict)
    progress_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, accounts: list, cdk_code: str):
        super().__init__()
        self.accounts = accounts
        self.cdk_code = cdk_code
    
    def do_batch_exchange(self):
        """执行批量CDK兑换"""
        try:
            # 使用第一个账号的VipAction实例进行批量操作
            if not self.accounts:
                self.error_occurred.emit("没有选择任何账号")
                return
            
            first_account = self.accounts[0]
            vip_action = VipAction(first_account.get("key", ""), first_account.get("cookie", {}))
            result = vip_action.batch_exchange_cdk(self.accounts, self.cdk_code)
            
            self.exchange_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"批量CDK兑换异常: {e}")


class BatchVipPurchaseWorker(QObject):
    """批量VIP购买工作线程（120钻石）"""
    finished = Signal(dict)
    progress_updated = Signal(dict)
    error = Signal(str)
    
    def __init__(self, accounts: list, cost_diamonds: int = 120):
        super().__init__()
        self.accounts = accounts
        self.cost_diamonds = cost_diamonds
    
    def run(self):
        """执行批量VIP购买"""
        try:
            # 使用第一个账号的VipAction实例进行批量操作
            if not self.accounts:
                self.error.emit("没有选择任何账号")
                return
            
            first_account = self.accounts[0]
            vip_action = VipAction(first_account.get("key", ""), first_account.get("cookie", {}))
            result = vip_action.batch_purchase_vip(self.accounts, self.cost_diamonds)
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"批量VIP购买异常: {e}")


class BatchVipInfoWorker(QObject):
    """批量VIP信息获取工作线程"""
    info_loaded = Signal(dict)
    progress_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, accounts: list):
        super().__init__()
        self.accounts = accounts
    
    def do_batch_load_info(self):
        """执行批量VIP信息获取"""
        try:
            # 使用第一个账号的VipAction实例进行批量操作
            if not self.accounts:
                self.error_occurred.emit("没有选择任何账号")
                return
            
            first_account = self.accounts[0]
            vip_action = VipAction(first_account.get("key", ""), first_account.get("cookie", {}))
            result = vip_action.batch_get_vip_info(self.accounts)
            
            self.info_loaded.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"批量VIP信息获取异常: {e}")


class GiftPackageWorker(QObject):
    """礼包打开工作线程"""
    package_opened = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, key: str, cookie: Dict[str, str], package_code: str):
        super().__init__()
        self.key = key
        self.cookie = cookie
        self.package_code = package_code
    
    def do_open_package(self):
        """打开礼包"""
        try:
            vip_action = VipAction(self.key, self.cookie)
            result = vip_action.open_gift_package(self.package_code)
            self.package_opened.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"礼包打开异常: {e}")


class VipVoucherWorker(QObject):
    """VIP礼券数量获取工作线程"""
    voucher_loaded = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, key: str, cookie: Dict[str, str]):
        super().__init__()
        self.key = key
        self.cookie = cookie
    
    def do_load_vouchers(self):
        """加载VIP礼券数量"""
        try:
            vip_action = VipAction(self.key, self.cookie)
            result = vip_action.get_vip_voucher_count()
            self.voucher_loaded.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"获取VIP礼券数量异常: {e}")


class VipShopPurchaseWorker(QObject):
    """VIP商店购买工作线程"""
    purchase_completed = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, key: str, cookie: Dict[str, str], goods_id: int, quantity: int):
        super().__init__()
        self.key = key
        self.cookie = cookie
        self.goods_id = goods_id
        self.quantity = quantity
    
    def do_purchase(self):
        """执行VIP商店购买"""
        try:
            vip_action = VipAction(self.key, self.cookie)
            result = vip_action.vip_shop_purchase(self.goods_id, self.quantity)
            self.purchase_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"VIP商店购买异常: {e}")


class BatchVipShopPurchaseWorker(QObject):
    """批量VIP商店购买工作线程"""
    purchase_completed = Signal(dict)
    progress_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, accounts: list, goods_id: int, quantity: int):
        super().__init__()
        self.accounts = accounts
        self.goods_id = goods_id
        self.quantity = quantity
    
    def do_batch_purchase(self):
        """执行批量VIP商店购买"""
        try:
            if not self.accounts:
                self.error_occurred.emit("没有选择任何账号")
                return
            
            first_account = self.accounts[0]
            vip_action = VipAction(first_account.get("key", ""), first_account.get("cookie", {}))
            result = vip_action.batch_vip_shop_purchase(self.accounts, self.goods_id, self.quantity)
            self.purchase_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"批量VIP商店购买异常: {e}")


class BatchGiftPackageWorker(QObject):
    """批量礼包打开工作线程"""
    packages_opened = Signal(dict)
    progress_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, accounts: list, package_codes: list):
        super().__init__()
        self.accounts = accounts
        self.package_codes = package_codes
    
    def do_batch_open_packages(self):
        """执行批量礼包打开"""
        try:
            if not self.accounts:
                self.error_occurred.emit("没有选择任何账号")
                return
            
            if not self.package_codes:
                self.error_occurred.emit("没有输入任何礼包代码")
                return
            
            first_account = self.accounts[0]
            vip_action = VipAction(first_account.get("key", ""), first_account.get("cookie", {}))
            result = vip_action.batch_open_gift_packages(self.accounts, self.package_codes)
            
            self.packages_opened.emit(result)
        except Exception as e:
            self.error_occurred.emit(f"批量礼包打开异常: {e}")


class VipPage(QWidget):
    """VIP管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_key = None
        self.current_cookie = None
        self.accounts_data = []
        self.depot_manager = None
        
        # 工作线程相关
        self.cdk_thread = None
        self.cdk_worker = None
        self.vip_info_thread = None
        self.vip_info_worker = None
        self.purchase_thread = None
        self.purchase_worker = None
        
        # 批量操作线程
        self.batch_cdk_thread = None
        self.batch_cdk_worker = None
        self.batch_purchase_thread = None
        self.batch_purchase_worker = None
        self.batch_info_thread = None
        self.batch_info_worker = None
        
        # 礼包操作线程
        self.gift_package_thread = None
        self.gift_package_worker = None
        self.batch_gift_package_thread = None
        self.batch_gift_package_worker = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("💎 VIP管理中心")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 账号选择器
        self.account_selector = AccountSelector()
        self.account_selector.set_selection_changed_callback(self.on_account_selection_changed)
        layout.addWidget(self.account_selector)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # VIP信息标签页
        self.tab_widget.addTab(self.create_vip_info_widget(), "📊 VIP信息")
        
        # CDK兑换标签页
        self.tab_widget.addTab(self.create_cdk_widget(), "🎁 CDK兑换")
        
        # VIP购买标签页
        self.tab_widget.addTab(self.create_purchase_widget(), "💳 VIP购买")
        
        # 礼包管理标签页
        self.tab_widget.addTab(self.create_gift_package_widget(), "🎁 礼包管理")
        
        # VIP商店标签页
        self.tab_widget.addTab(self.create_vip_shop_widget(), "🛒 VIP商店")
        
        layout.addWidget(self.tab_widget)
        
        self.setLayout(layout)
    
    def on_account_selection_changed(self, selection_data: Dict[str, Any]):
        """账号选择变化处理"""
        mode = selection_data.get("mode", "single")
        accounts = selection_data.get("accounts", [])
        count = selection_data.get("count", 0)
        
        if mode == "single" and count > 0:
            # 单个账号模式
            account = accounts[0]
            self.current_key = account.get("key", "")
            self.current_cookie = account.get("cookie", {})
            self.vip_log_message(f"📱 选择单个账号: {account.get('username', '未知')}")
        elif mode == "batch" and count > 0:
            # 批量账号模式
            self.current_key = None
            self.current_cookie = None
            usernames = [acc.get("username", "未知") for acc in accounts[:3]]
            if count > 3:
                usernames.append(f"等{count}个")
            self.vip_log_message(f"📦 选择批量账号: {count} 个账号 ({', '.join(usernames)})")
        else:
            # 没有选择
            self.current_key = None
            self.current_cookie = None
            self.vip_log_message("❌ 未选择任何账号")
    
    def set_accounts_data(self, accounts: List[Dict[str, Any]]):
        """设置账户数据"""
        self.accounts_data = accounts
        self.account_selector.set_accounts_data(accounts)
        self.vip_log_message(f"📋 已加载 {len(accounts)} 个账户")
    
    def set_depot_manager(self, depot_manager):
        """设置仓库管理器"""
        self.depot_manager = depot_manager
    
    def create_vip_info_widget(self) -> QWidget:
        """创建VIP信息区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # VIP状态信息
        status_group = QGroupBox("VIP状态")
        status_layout = QVBoxLayout()
        
        # 刷新按钮
        refresh_layout = QHBoxLayout()
        self.refresh_vip_btn = QPushButton("🔄 刷新VIP信息")
        self.refresh_vip_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; padding: 8px 16px; }")
        self.refresh_vip_btn.clicked.connect(self.refresh_vip_info)
        refresh_layout.addWidget(self.refresh_vip_btn)
        refresh_layout.addStretch()
        status_layout.addLayout(refresh_layout)
        
        # VIP信息显示
        self.vip_info_text = QTextBrowser()
        self.vip_info_text.setMaximumHeight(300)
        self.vip_info_text.setHtml(self.get_default_vip_info_html())
        status_layout.addWidget(self.vip_info_text)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 操作日志
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout()
        
        self.vip_log_text = QTextEdit()
        self.vip_log_text.setReadOnly(True)
        self.vip_log_text.setMaximumHeight(200)
        log_layout.addWidget(self.vip_log_text)
        
        # 清除日志按钮
        clear_log_btn = QPushButton("🗑️ 清除日志")
        clear_log_btn.clicked.connect(self.vip_log_text.clear)
        log_layout.addWidget(clear_log_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_cdk_widget(self) -> QWidget:
        """创建CDK兑换区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # CDK兑换功能
        cdk_group = QGroupBox("CDK兑换")
        cdk_layout = QVBoxLayout()
        
        # CDK输入
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("CDK兑换码:"))
        
        self.cdk_input = QLineEdit()
        self.cdk_input.setPlaceholderText("请输入CDK兑换码")
        self.cdk_input.setStyleSheet("QLineEdit { padding: 8px; font-size: 14px; }")
        input_layout.addWidget(self.cdk_input)
        
        self.cdk_exchange_btn = QPushButton("🎁 立即兑换")
        self.cdk_exchange_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px 16px; }")
        self.cdk_exchange_btn.clicked.connect(self.exchange_cdk)
        input_layout.addWidget(self.cdk_exchange_btn)
        
        cdk_layout.addLayout(input_layout)
        
        # CDK兑换说明
        info_label = QLabel(
            "💡 <b>兑换说明：</b><br>"
            "• 请输入有效的CDK兑换码<br>"
            "• 每个CDK码只能使用一次<br>"
            "• 兑换成功后奖励将直接发放到账户<br>"
            "• 请确保CDK码输入正确，避免浪费"
        )
        info_label.setStyleSheet("QLabel { background-color: #e7f3ff; padding: 10px; border-radius: 5px; }")
        cdk_layout.addWidget(info_label)
        
        cdk_group.setLayout(cdk_layout)
        layout.addWidget(cdk_group)
        
        # CDK兑换历史
        history_group = QGroupBox("兑换记录")
        history_layout = QVBoxLayout()
        
        self.cdk_history_text = QTextEdit()
        self.cdk_history_text.setReadOnly(True)
        self.cdk_history_text.setMaximumHeight(200)
        self.cdk_history_text.setPlaceholderText("CDK兑换记录将显示在这里...")
        history_layout.addWidget(self.cdk_history_text)
        
        # 清除历史按钮
        clear_history_btn = QPushButton("🗑️ 清除记录")
        clear_history_btn.clicked.connect(self.cdk_history_text.clear)
        history_layout.addWidget(clear_history_btn)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_purchase_widget(self) -> QWidget:
        """创建VIP购买区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # VIP购买选择
        package_group = QGroupBox("💎 VIP购买（钻石）")
        package_layout = QVBoxLayout()
        
        # 购买信息
        info_layout = QVBoxLayout()
        
        vip_info_label = QLabel(
            "🌟 <b>VIP会员特权</b><br>"
            "💎 <b>费用：120钻石</b><br>"
            "⏰ 有效期：根据游戏设定<br>"
            "✨ 享受VIP专属特权和功能"
        )
        vip_info_label.setStyleSheet("QLabel { background-color: #e7f3ff; padding: 15px; border-radius: 8px; color: #0056b3; }")
        info_layout.addWidget(vip_info_label)
        
        package_layout.addLayout(info_layout)
        
        # 钻石费用显示
        cost_layout = QHBoxLayout()
        cost_layout.addWidget(QLabel("购买费用:"))
        
        self.diamond_cost_label = QLabel("💎 120 钻石")
        self.diamond_cost_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #ff6b35; }")
        cost_layout.addWidget(self.diamond_cost_label)
        cost_layout.addStretch()
        
        package_layout.addLayout(cost_layout)
        
        # 购买按钮
        purchase_layout = QHBoxLayout()
        self.purchase_btn = QPushButton("💎 立即购买VIP（120钻石）")
        self.purchase_btn.setStyleSheet("QPushButton { background-color: #ff6b35; color: white; font-weight: bold; padding: 12px 24px; font-size: 16px; }")
        self.purchase_btn.clicked.connect(self.purchase_vip)
        purchase_layout.addWidget(self.purchase_btn)
        purchase_layout.addStretch()
        
        package_layout.addLayout(purchase_layout)
        
        package_group.setLayout(package_layout)
        layout.addWidget(package_group)
        
        # VIP特权说明
        privileges_group = QGroupBox("VIP特权")
        privileges_layout = QVBoxLayout()
        
        privileges_info = QTextBrowser()
        privileges_info.setMaximumHeight(250)
        privileges_info.setHtml(self.get_vip_privileges_html())
        privileges_layout.addWidget(privileges_info)
        
        privileges_group.setLayout(privileges_layout)
        layout.addWidget(privileges_group)
        
        # 购买说明
        notice_label = QLabel(
            "⚠️ <b>购买须知：</b><br>"
            "• VIP购买使用游戏内钻石，费用：120钻石<br>"
            "• 购买前请确保账户有足够的钻石余额<br>"
            "• VIP购买成功后立即生效<br>"
            "• VIP特权包括但不限于上述列表内容<br>"
            "• 如有问题请联系客服"
        )
        notice_label.setStyleSheet("QLabel { background-color: #fff3cd; padding: 10px; border-radius: 5px; color: #856404; }")
        layout.addWidget(notice_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_gift_package_widget(self) -> QWidget:
        """创建礼包管理区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 礼包打开功能
        open_group = QGroupBox("礼包打开")
        open_layout = QVBoxLayout()
        
        # 礼包代码输入
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("礼包代码:"))
        
        self.package_code_input = QLineEdit()
        self.package_code_input.setPlaceholderText("请输入礼包代码，多个代码用逗号分隔")
        self.package_code_input.setStyleSheet("QLineEdit { padding: 8px; font-size: 14px; }")
        input_layout.addWidget(self.package_code_input)
        
        self.open_package_btn = QPushButton("🎁 打开礼包")
        self.open_package_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px 16px; }")
        self.open_package_btn.clicked.connect(self.open_gift_packages)
        input_layout.addWidget(self.open_package_btn)
        
        open_layout.addLayout(input_layout)
        
        # 快速输入按钮
        quick_input_layout = QHBoxLayout()
        quick_input_layout.addWidget(QLabel("快速输入:"))
        
        # 预设的常见礼包代码
        common_codes = ["10660", "10661", "10662", "10663"]
        for code in common_codes:
            btn = QPushButton(f"礼包{code}")
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked, c=code: self.add_package_code(c))
            quick_input_layout.addWidget(btn)
        
        quick_input_layout.addStretch()
        open_layout.addLayout(quick_input_layout)
        
        # 礼包打开说明
        gift_info_label = QLabel(
            "💡 <b>礼包说明：</b><br>"
            "• 请输入有效的礼包代码<br>"
            "• 多个礼包代码请用逗号分隔<br>"
            "• CDK兑换后获得的礼包会自动显示代码<br>"
            "• 支持单个账号和批量账号操作"
        )
        gift_info_label.setStyleSheet("QLabel { background-color: #e7f3ff; padding: 10px; border-radius: 5px; }")
        open_layout.addWidget(gift_info_label)
        
        open_group.setLayout(open_layout)
        layout.addWidget(open_group)
        
        # 礼包管理结果
        result_group = QGroupBox("操作结果")
        result_layout = QVBoxLayout()
        
        self.gift_package_result_text = QTextEdit()
        self.gift_package_result_text.setReadOnly(True)
        self.gift_package_result_text.setMaximumHeight(250)
        self.gift_package_result_text.setPlaceholderText("礼包打开结果将显示在这里...")
        result_layout.addWidget(self.gift_package_result_text)
        
        # 结果操作按钮
        result_btn_layout = QHBoxLayout()
        
        clear_result_btn = QPushButton("🗑️ 清除结果")
        clear_result_btn.clicked.connect(self.gift_package_result_text.clear)
        result_btn_layout.addWidget(clear_result_btn)
        
        refresh_depot_btn = QPushButton("📦 检查仓库礼包")
        refresh_depot_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; padding: 6px 12px; }")
        refresh_depot_btn.clicked.connect(self.check_depot_gift_packages)
        result_btn_layout.addWidget(refresh_depot_btn)
        
        result_btn_layout.addStretch()
        result_layout.addLayout(result_btn_layout)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 使用说明
        usage_group = QGroupBox("使用指南")
        usage_layout = QVBoxLayout()
        
        usage_info = QTextBrowser()
        usage_info.setMaximumHeight(150)
        usage_info.setHtml(self.get_gift_package_usage_html())
        usage_layout.addWidget(usage_info)
        
        usage_group.setLayout(usage_layout)
        layout.addWidget(usage_group)
        
        widget.setLayout(layout)
        return widget
    
    def get_gift_package_usage_html(self) -> str:
        """获取礼包使用指南HTML"""
        return """
        <div style='padding: 10px;'>
            <h4>🎁 礼包管理使用指南</h4>
            <ol style='line-height: 1.6;'>
                <li><strong>选择账号：</strong> 使用上方账号选择器选择要操作的账号（支持单个/批量）</li>
                <li><strong>输入礼包代码：</strong> 在输入框中输入礼包代码，多个代码用逗号分隔</li>
                <li><strong>打开礼包：</strong> 点击"打开礼包"按钮执行操作</li>
                <li><strong>查看结果：</strong> 在操作结果区域查看礼包打开的详细信息</li>
                <li><strong>仓库检查：</strong> 使用"检查仓库礼包"功能自动发现可用礼包</li>
            </ol>
            <div style='margin-top: 15px; padding: 8px; background-color: #fff3cd; border-radius: 5px;'>
                <p style='margin: 0; color: #856404; font-size: 12px;'>
                    <strong>💡 提示：</strong> CDK兑换成功后通常会获得礼包，可以使用此功能批量打开获得的礼包奖励。
                </p>
            </div>
        </div>
        """
    
    def create_vip_shop_widget(self) -> QWidget:
        """创建VIP商店区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 礼券余额显示
        voucher_group = QGroupBox("💳 礼券余额")
        voucher_layout = QHBoxLayout()
        
        self.voucher_count_label = QLabel("VIP礼券: 查询中...")
        self.voucher_count_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #28a745; }")
        voucher_layout.addWidget(self.voucher_count_label)
        
        refresh_voucher_btn = QPushButton("🔄 刷新余额")
        refresh_voucher_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; padding: 6px 12px; }")
        refresh_voucher_btn.clicked.connect(self.refresh_voucher_count)
        voucher_layout.addWidget(refresh_voucher_btn)
        
        voucher_layout.addStretch()
        voucher_group.setLayout(voucher_layout)
        layout.addWidget(voucher_group)
        
        # 商品分类选择
        category_group = QGroupBox("🛍️ 商品分类")
        category_layout = QHBoxLayout()
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部商品", "道具", "升级道具", "金币", "食谱"])
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        category_layout.addWidget(QLabel("分类:"))
        category_layout.addWidget(self.category_combo)
        
        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(["全部稀有度", "普通", "高级", "稀有", "史诗", "传说"])
        self.rarity_combo.currentTextChanged.connect(self.on_rarity_changed)
        category_layout.addWidget(QLabel("稀有度:"))
        category_layout.addWidget(self.rarity_combo)
        
        category_layout.addStretch()
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # 商品列表
        shop_group = QGroupBox("🛒 商品列表")
        shop_layout = QVBoxLayout()
        
        # 创建商品表格
        self.shop_table = QTableWidget()
        self.shop_table.setColumnCount(6)
        self.shop_table.setHorizontalHeaderLabels(["商品", "名称", "描述", "礼券", "数量", "操作"])
        
        # 设置表格样式
        header = self.shop_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 商品图标
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 名称
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 描述
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # 礼券
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # 数量
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 操作
        
        self.shop_table.setColumnWidth(0, 60)  # 图标列
        self.shop_table.setColumnWidth(3, 80)  # 礼券列
        self.shop_table.setColumnWidth(4, 80)  # 数量列
        self.shop_table.setColumnWidth(5, 100)  # 操作列
        
        self.shop_table.setAlternatingRowColors(True)
        self.shop_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        shop_layout.addWidget(self.shop_table)
        
        # 购买操作
        purchase_layout = QHBoxLayout()
        
        self.batch_purchase_btn = QPushButton("🛍️ 批量购买选中商品")
        self.batch_purchase_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px 16px; }")
        self.batch_purchase_btn.clicked.connect(self.batch_purchase_selected_items)
        purchase_layout.addWidget(self.batch_purchase_btn)
        
        purchase_layout.addStretch()
        shop_layout.addLayout(purchase_layout)
        
        shop_group.setLayout(shop_layout)
        layout.addWidget(shop_group)
        
        # 购买结果
        result_group = QGroupBox("📋 购买结果")
        result_layout = QVBoxLayout()
        
        self.shop_result_text = QTextEdit()
        self.shop_result_text.setReadOnly(True)
        self.shop_result_text.setMaximumHeight(200)
        self.shop_result_text.setPlaceholderText("购买结果将显示在这里...")
        result_layout.addWidget(self.shop_result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 初始化商品列表
        self.load_shop_items()
        
        widget.setLayout(layout)
        return widget
    
    def add_package_code(self, code: str):
        """添加礼包代码到输入框"""
        current_text = self.package_code_input.text().strip()
        if current_text:
            # 检查是否已存在该代码
            codes = [c.strip() for c in current_text.split(',')]
            if code not in codes:
                self.package_code_input.setText(f"{current_text}, {code}")
        else:
            self.package_code_input.setText(code)
    
    def check_depot_gift_packages(self):
        """检查仓库中的礼包"""
        selected_accounts = self.account_selector.get_selected_accounts()
        operation_mode = self.account_selector.get_operation_mode()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        if not self.depot_manager:
            QMessageBox.warning(self, "错误", "仓库管理器未初始化")
            return
        
        self.vip_log_message("📦 开始检查仓库礼包...")
        
        try:
            if operation_mode == "single":
                # 单个账号模式
                account = selected_accounts[0]
                account_id = account.get("id")
                username = account.get("username", "未知")
                
                self.vip_log_message(f"🔍 检查账号 {username} 的仓库礼包...")
                
                # 使用VipAction的礼包检查功能
                vip_action = VipAction(account.get("key", ""), account.get("cookie", {}))
                
                # 创建DepotAction实例来获取仓库数据
                from src.delicious_town_bot.actions.depot import DepotAction
                depot_action = DepotAction(account.get("key", ""), account.get("cookie", {}))
                
                # 获取礼包列表
                gift_result = vip_action.get_gift_packages_in_depot(depot_action)
                
                if gift_result.get("success", False):
                    gift_packages = gift_result.get("gift_packages", [])
                    self.display_gift_packages_result([account], [gift_packages])
                else:
                    error_msg = gift_result.get("message", "未知错误")
                    self.vip_log_message(f"❌ 获取礼包失败: {error_msg}")
                    self.gift_package_result_text.append(f"❌ 账号 {username} 礼包检查失败: {error_msg}\n\n")
            else:
                # 批量账号模式
                self.vip_log_message(f"🔍 批量检查 {len(selected_accounts)} 个账号的仓库礼包...")
                
                all_results = []
                for i, account in enumerate(selected_accounts, 1):
                    account_id = account.get("id")
                    username = account.get("username", "未知")
                    
                    self.vip_log_message(f"  [{i}/{len(selected_accounts)}] 检查账号 {username}...")
                    
                    try:
                        # 使用VipAction的礼包检查功能
                        vip_action = VipAction(account.get("key", ""), account.get("cookie", {}))
                        
                        # 创建DepotAction实例
                        from src.delicious_town_bot.actions.depot import DepotAction
                        depot_action = DepotAction(account.get("key", ""), account.get("cookie", {}))
                        
                        # 获取礼包列表
                        gift_result = vip_action.get_gift_packages_in_depot(depot_action)
                        
                        if gift_result.get("success", False):
                            gift_packages = gift_result.get("gift_packages", [])
                            all_results.append((account, gift_packages))
                            self.vip_log_message(f"    ✅ {username}: 发现 {len(gift_packages)} 种礼包")
                        else:
                            error_msg = gift_result.get("message", "未知错误")
                            all_results.append((account, []))
                            self.vip_log_message(f"    ❌ {username}: {error_msg}")
                    except Exception as e:
                        all_results.append((account, []))
                        self.vip_log_message(f"    ❌ {username}: 检查异常 - {e}")
                
                # 显示批量结果
                self.display_batch_gift_packages_result(all_results)
                
        except Exception as e:
            self.vip_log_message(f"❌ 礼包检查异常: {e}")
            self.gift_package_result_text.append(f"❌ 礼包检查异常: {e}\n\n")
    
    def display_gift_packages_result(self, accounts, gift_packages_list):
        """显示单个账号礼包检查结果"""
        account = accounts[0]
        gift_packages = gift_packages_list[0] if gift_packages_list else []
        username = account.get("username", "未知")
        
        result_text = f"📦 账号 {username} 仓库礼包检查结果:\n\n"
        package_codes = []
        
        if gift_packages:
            for pkg in gift_packages:
                pkg_name = pkg.get("name", "未知礼包")
                pkg_code = pkg.get("code", "")
                pkg_num = pkg.get("num", 0)
                result_text += f"• {pkg_name} (代码: {pkg_code}) x{pkg_num}\n"
                if pkg_code and pkg_num > 0:
                    package_codes.append(pkg_code)
            
            if package_codes:
                result_text += f"\n🎯 发现 {len(package_codes)} 种可用礼包，代码: {', '.join(package_codes)}\n"
                result_text += "💡 代码已自动填入上方输入框，可直接打开\n"
                
                # 自动填入礼包代码
                self.package_code_input.setText(", ".join(package_codes))
                
                self.vip_log_message(f"✅ 找到 {len(package_codes)} 种可用礼包: {', '.join(package_codes)}")
            else:
                result_text += "\n💡 虽然有礼包但无可用代码或数量为0\n"
                self.vip_log_message("⚠️ 礼包存在但无可用代码")
        else:
            result_text += "❌ 未发现任何礼包\n"
            self.vip_log_message("❌ 未发现礼包")
        
        result_text += f"\n⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        self.gift_package_result_text.append(result_text)
    
    def display_batch_gift_packages_result(self, all_results):
        """显示批量账号礼包检查结果"""
        result_text = f"📦 批量仓库礼包检查结果 ({len(all_results)} 个账号):\n\n"
        
        all_package_codes = set()
        success_count = 0
        
        for account, gift_packages in all_results:
            username = account.get("username", "未知")
            
            if gift_packages:
                success_count += 1
                result_text += f"✅ {username}: 发现 {len(gift_packages)} 种礼包\n"
                
                for pkg in gift_packages:
                    pkg_name = pkg.get("name", "未知礼包")
                    pkg_code = pkg.get("code", "")
                    pkg_num = pkg.get("num", 0)
                    result_text += f"  • {pkg_name} (代码: {pkg_code}) x{pkg_num}\n"
                    if pkg_code and pkg_num > 0:
                        all_package_codes.add(pkg_code)
            else:
                result_text += f"❌ {username}: 未发现礼包\n"
            
            result_text += "\n"
        
        # 汇总信息
        result_text += f"📊 汇总统计:\n"
        result_text += f"  • 成功检查: {success_count}/{len(all_results)} 个账号\n"
        result_text += f"  • 发现礼包代码: {len(all_package_codes)} 种\n"
        
        if all_package_codes:
            package_codes_list = list(all_package_codes)
            result_text += f"  • 所有代码: {', '.join(package_codes_list)}\n"
            result_text += "💡 所有代码已自动填入上方输入框\n"
            
            # 自动填入所有礼包代码
            self.package_code_input.setText(", ".join(package_codes_list))
            
            self.vip_log_message(f"✅ 批量检查完成: {len(all_package_codes)} 种礼包代码")
        else:
            result_text += "  • 未发现任何可用礼包代码\n"
            self.vip_log_message("❌ 批量检查完成但未发现礼包")
        
        result_text += f"\n⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        self.gift_package_result_text.append(result_text)
    
    def open_gift_packages(self):
        """打开礼包"""
        selected_accounts = self.account_selector.get_selected_accounts()
        operation_mode = self.account_selector.get_operation_mode()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        package_codes_text = self.package_code_input.text().strip()
        if not package_codes_text:
            QMessageBox.warning(self, "提示", "请输入礼包代码")
            return
        
        # 解析礼包代码
        package_codes = [code.strip() for code in package_codes_text.split(',') if code.strip()]
        if not package_codes:
            QMessageBox.warning(self, "提示", "请输入有效的礼包代码")
            return
        
        # 确认对话框
        account_count = len(selected_accounts)
        total_operations = account_count * len(package_codes)
        
        mode_text = "单个账号" if operation_mode == "single" else f"{account_count}个账号批量"
        reply = QMessageBox.question(
            self, "确认打开礼包",
            f"确定要{mode_text}打开以下礼包吗？\n\n"
            f"📦 礼包代码: {', '.join(package_codes)}\n"
            f"👥 账号数量: {account_count}\n"
            f"🎯 总操作数: {total_operations}\n\n"
            f"⚠️ 注意：\n"
            f"• 每个礼包只能打开一次\n"
            f"• 打开后无法撤销\n"
            f"• 请确保礼包代码正确",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮
        self.open_package_btn.setEnabled(False)
        self.open_package_btn.setText("🎁 打开中...")
        
        if operation_mode == "single":
            # 单个账号模式
            account = selected_accounts[0]
            self.open_single_account_packages(account, package_codes)
        else:
            # 批量账号模式
            self.open_batch_account_packages(selected_accounts, package_codes)
    
    def open_single_account_packages(self, account: Dict[str, Any], package_codes: List[str]):
        """单个账号打开礼包"""
        # 如果只有一个礼包代码，使用单个操作
        if len(package_codes) == 1:
            self.gift_package_thread = QThread()
            self.gift_package_worker = GiftPackageWorker(
                account.get("key", ""), 
                account.get("cookie", {}), 
                package_codes[0]
            )
            self.gift_package_worker.moveToThread(self.gift_package_thread)
            
            # 连接信号
            self.gift_package_thread.started.connect(self.gift_package_worker.do_open_package)
            self.gift_package_worker.package_opened.connect(self.on_single_package_opened)
            self.gift_package_worker.error_occurred.connect(self.on_gift_package_error)
            
            # 启动线程
            self.gift_package_thread.start()
            self.vip_log_message(f"🎁 开始打开礼包: {package_codes[0]} ({account.get('username', '未知')})")
        else:
            # 多个礼包代码，使用批量操作
            self.open_batch_account_packages([account], package_codes)
    
    def open_batch_account_packages(self, accounts: List[Dict[str, Any]], package_codes: List[str]):
        """批量账号打开礼包"""
        self.batch_gift_package_thread = QThread()
        self.batch_gift_package_worker = BatchGiftPackageWorker(accounts, package_codes)
        self.batch_gift_package_worker.moveToThread(self.batch_gift_package_thread)
        
        # 连接信号
        self.batch_gift_package_thread.started.connect(self.batch_gift_package_worker.do_batch_open_packages)
        self.batch_gift_package_worker.packages_opened.connect(self.on_batch_packages_opened)
        self.batch_gift_package_worker.error_occurred.connect(self.on_batch_gift_package_error)
        
        # 启动线程
        self.batch_gift_package_thread.start()
        account_count = len(accounts)
        package_count = len(package_codes)
        self.vip_log_message(f"🎁 开始批量打开礼包: {package_count} 种礼包 x {account_count} 个账号")
    
    @Slot(dict)
    def on_single_package_opened(self, result: Dict[str, Any]):
        """单个礼包打开完成"""
        self.open_package_btn.setEnabled(True)
        self.open_package_btn.setText("🎁 打开礼包")
        
        success = result.get("success", False)
        message = result.get("message", "")
        data = result.get("data", [])
        
        if success:
            self.vip_log_message(f"✅ 礼包打开成功: {message}")
            result_text = f"🎁 礼包打开成功\n\n"
            result_text += f"📝 消息: {message}\n"
            if data:
                result_text += f"🎯 奖励内容: {data}\n"
            result_text += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            self.gift_package_result_text.append(result_text)
        else:
            self.vip_log_message(f"❌ 礼包打开失败: {message}")
            result_text = f"❌ 礼包打开失败\n\n"
            result_text += f"📝 错误: {message}\n"
            result_text += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            self.gift_package_result_text.append(result_text)
        
        # 清理线程
        if self.gift_package_thread:
            self.gift_package_thread.quit()
            self.gift_package_thread.wait()
            self.gift_package_thread = None
            self.gift_package_worker = None
    
    @Slot(str)
    def on_gift_package_error(self, error_msg: str):
        """礼包打开错误"""
        self.open_package_btn.setEnabled(True)
        self.open_package_btn.setText("🎁 打开礼包")
        self.vip_log_message(f"❌ {error_msg}")
        
        result_text = f"❌ 礼包打开异常\n\n"
        result_text += f"📝 错误: {error_msg}\n"
        result_text += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        self.gift_package_result_text.append(result_text)
        
        # 清理线程
        if self.gift_package_thread:
            self.gift_package_thread.quit()
            self.gift_package_thread.wait()
            self.gift_package_thread = None
            self.gift_package_worker = None
    
    @Slot(dict)
    def on_batch_packages_opened(self, result: Dict[str, Any]):
        """批量礼包打开完成"""
        self.open_package_btn.setEnabled(True)
        self.open_package_btn.setText("🎁 打开礼包")
        
        success = result.get("success", False)
        message = result.get("message", "")
        results = result.get("results", [])
        success_count = result.get("success_count", 0)
        failure_count = result.get("failure_count", 0)
        total_operations = result.get("total_operations", 0)
        
        if success:
            self.vip_log_message(f"✅ 批量礼包打开完成: 成功 {success_count}/{total_operations} 个操作")
            
            # 显示批量结果
            result_text = f"🎁 批量礼包打开结果\n\n"
            result_text += f"📊 总体统计:\n"
            result_text += f"  • 总操作数: {total_operations}\n"
            result_text += f"  • 成功数量: {success_count}\n"
            result_text += f"  • 失败数量: {failure_count}\n\n"
            
            # 显示每个账号的详细结果
            for account_result in results:
                account = account_result.get("account", {})
                username = account.get("username", "未知")
                account_success = account_result.get("success_count", 0)
                account_total = account_result.get("total_packages", 0)
                
                result_text += f"👤 {username}: {account_success}/{account_total} 成功\n"
                
                # 显示礼包详情
                package_results = account_result.get("package_results", [])
                for pkg_result in package_results:
                    pkg_code = pkg_result.get("package_code", "未知")
                    pkg_success = pkg_result.get("success", False)
                    pkg_message = pkg_result.get("message", "")
                    status = "✅" if pkg_success else "❌"
                    result_text += f"  {status} 礼包{pkg_code}: {pkg_message}\n"
                
                result_text += "\n"
            
            result_text += f"⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            self.gift_package_result_text.append(result_text)
        else:
            self.vip_log_message(f"❌ 批量礼包打开失败: {message}")
            result_text = f"❌ 批量礼包打开失败\n\n"
            result_text += f"📝 错误: {message}\n"
            result_text += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            self.gift_package_result_text.append(result_text)
        
        # 清理线程
        if self.batch_gift_package_thread:
            self.batch_gift_package_thread.quit()
            self.batch_gift_package_thread.wait()
            self.batch_gift_package_thread = None
            self.batch_gift_package_worker = None
    
    @Slot(str)
    def on_batch_gift_package_error(self, error_msg: str):
        """批量礼包打开错误"""
        self.open_package_btn.setEnabled(True)
        self.open_package_btn.setText("🎁 打开礼包")
        self.vip_log_message(f"❌ {error_msg}")
        
        result_text = f"❌ 批量礼包打开异常\n\n"
        result_text += f"📝 错误: {error_msg}\n"
        result_text += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        self.gift_package_result_text.append(result_text)
        
        # 清理线程
        if self.batch_gift_package_thread:
            self.batch_gift_package_thread.quit()
            self.batch_gift_package_thread.wait()
            self.batch_gift_package_thread = None
            self.batch_gift_package_worker = None
    
    def get_default_vip_info_html(self) -> str:
        """获取默认VIP信息HTML"""
        return """
        <div style='text-align: center; padding: 20px;'>
            <h3>💎 VIP信息</h3>
            <p style='color: #666;'>请先选择账户并刷新VIP信息</p>
            <hr>
            <div style='margin-top: 20px;'>
                <p><strong>VIP等级：</strong> <span style='color: #999;'>未知</span></p>
                <p><strong>到期时间：</strong> <span style='color: #999;'>未知</span></p>
                <p><strong>剩余天数：</strong> <span style='color: #999;'>未知</span></p>
                <p><strong>特权状态：</strong> <span style='color: #999;'>未知</span></p>
            </div>
        </div>
        """
    
    def get_vip_privileges_html(self) -> str:
        """获取VIP特权说明HTML"""
        return """
        <div style='padding: 10px;'>
            <h4>💎 VIP专属特权</h4>
            <ul style='line-height: 1.8;'>
                <li>🎯 <strong>挂机加速：</strong> 挂机收益提升50%</li>
                <li>⚡ <strong>操作优先：</strong> 所有操作享受优先处理</li>
                <li>🎁 <strong>每日礼包：</strong> 每日登录获得VIP专属礼包</li>
                <li>🏪 <strong>商店折扣：</strong> 所有商店物品享受9折优惠</li>
                <li>🔄 <strong>无限刷新：</strong> 各种刷新次数无限制</li>
                <li>📈 <strong>经验加成：</strong> 所有经验获得提升30%</li>
                <li>💰 <strong>金币加成：</strong> 金币获得提升40%</li>
                <li>🎨 <strong>专属标识：</strong> 游戏内显示VIP专属标识</li>
                <li>🛡️ <strong>优先客服：</strong> 享受VIP专属客服支持</li>
                <li>🎪 <strong>活动优先：</strong> 优先参与各种特殊活动</li>
            </ul>
            <div style='margin-top: 15px; padding: 10px; background-color: #e7f3ff; border-radius: 5px;'>
                <p style='margin: 0; text-align: center; color: #0066cc;'>
                    <strong>🌟 成为VIP，享受游戏最佳体验！</strong>
                </p>
            </div>
        </div>
        """
    
    def set_account_info(self, key: str, cookie: Dict[str, str]):
        """设置账户信息"""
        self.current_key = key
        self.current_cookie = cookie
        self.vip_log_message("📱 账户信息已更新，可以使用VIP功能")
    
    def refresh_vip_info(self):
        """刷新VIP信息"""
        selected_accounts = self.account_selector.get_selected_accounts()
        operation_mode = self.account_selector.get_operation_mode()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        # 禁用按钮
        self.refresh_vip_btn.setEnabled(False)
        self.refresh_vip_btn.setText("🔄 加载中...")
        
        if operation_mode == "single":
            # 单个账号模式
            account = selected_accounts[0]
            # 创建VIP信息获取工作线程
            self.vip_info_thread = QThread()
            self.vip_info_worker = VipInfoWorker(account.get("key", ""), account.get("cookie", {}))
            self.vip_info_worker.moveToThread(self.vip_info_thread)
            
            # 连接信号
            self.vip_info_thread.started.connect(self.vip_info_worker.do_load_info)
            self.vip_info_worker.info_loaded.connect(self.on_vip_info_loaded)
            self.vip_info_worker.error_occurred.connect(self.on_vip_info_error)
            
            # 启动线程
            self.vip_info_thread.start()
            self.vip_log_message(f"🔄 开始获取VIP信息: {account.get('username', '未知')}")
        else:
            # 批量账号模式
            self.batch_info_thread = QThread()
            self.batch_info_worker = BatchVipInfoWorker(selected_accounts)
            self.batch_info_worker.moveToThread(self.batch_info_thread)
            
            # 连接信号
            self.batch_info_thread.started.connect(self.batch_info_worker.do_batch_load_info)
            self.batch_info_worker.info_loaded.connect(self.on_batch_vip_info_loaded)
            self.batch_info_worker.error_occurred.connect(self.on_batch_vip_info_error)
            
            # 启动线程
            self.batch_info_thread.start()
            self.vip_log_message(f"🔄 开始批量获取VIP信息: {len(selected_accounts)} 个账号")
    
    @Slot(dict)
    def on_vip_info_loaded(self, result: Dict[str, Any]):
        """VIP信息加载完成"""
        self.refresh_vip_btn.setEnabled(True)
        self.refresh_vip_btn.setText("🔄 刷新VIP信息")
        
        success = result.get("success", False)
        message = result.get("message", "")
        vip_info = result.get("vip_info", {})
        
        if success:
            self.update_vip_info_display(vip_info)
            self.vip_log_message(f"✅ VIP信息获取成功")
        else:
            self.vip_log_message(f"❌ VIP信息获取失败: {message}")
            # 显示模拟数据
            self.show_mock_vip_info()
        
        # 清理线程
        if self.vip_info_thread:
            self.vip_info_thread.quit()
            self.vip_info_thread.wait()
            self.vip_info_thread = None
            self.vip_info_worker = None
    
    @Slot(str)
    def on_vip_info_error(self, error_msg: str):
        """VIP信息获取错误"""
        self.refresh_vip_btn.setEnabled(True)
        self.refresh_vip_btn.setText("🔄 刷新VIP信息")
        self.vip_log_message(f"❌ {error_msg}")
        
        # 显示模拟数据
        self.show_mock_vip_info()
        
        # 清理线程
        if self.vip_info_thread:
            self.vip_info_thread.quit()
            self.vip_info_thread.wait()
            self.vip_info_thread = None
            self.vip_info_worker = None
    
    @Slot(dict)
    def on_batch_vip_info_loaded(self, result: Dict[str, Any]):
        """批量VIP信息加载完成"""
        self.refresh_vip_btn.setEnabled(True)
        self.refresh_vip_btn.setText("🔄 刷新VIP信息")
        
        success = result.get("success", False)
        message = result.get("message", "")
        results = result.get("results", [])
        success_count = result.get("success_count", 0)
        failure_count = result.get("failure_count", 0)
        
        if success:
            self.vip_log_message(f"✅ 批量VIP信息获取完成: 成功 {success_count} 个, 失败 {failure_count} 个")
            
            # 显示批量结果摘要
            batch_info_html = self.create_batch_vip_info_html(results)
            self.vip_info_text.setHtml(batch_info_html)
            
            # 记录详细结果
            for result_item in results:
                account = result_item.get("account", {})
                username = account.get("username", "未知")
                if result_item.get("success", False):
                    self.vip_log_message(f"  ✅ {username}: VIP信息获取成功")
                else:
                    self.vip_log_message(f"  ❌ {username}: {result_item.get('message', '未知错误')}")
        else:
            self.vip_log_message(f"❌ 批量VIP信息获取失败: {message}")
            self.show_mock_vip_info()
        
        # 清理线程
        if self.batch_info_thread:
            self.batch_info_thread.quit()
            self.batch_info_thread.wait()
            self.batch_info_thread = None
            self.batch_info_worker = None
    
    @Slot(str)
    def on_batch_vip_info_error(self, error_msg: str):
        """批量VIP信息获取错误"""
        self.refresh_vip_btn.setEnabled(True)
        self.refresh_vip_btn.setText("🔄 刷新VIP信息")
        self.vip_log_message(f"❌ {error_msg}")
        
        # 显示模拟数据
        self.show_mock_vip_info()
        
        # 清理线程
        if self.batch_info_thread:
            self.batch_info_thread.quit()
            self.batch_info_thread.wait()
            self.batch_info_thread = None
            self.batch_info_worker = None
    
    def create_batch_vip_info_html(self, results: List[Dict[str, Any]]) -> str:
        """创建批量VIP信息HTML"""
        html_content = """
        <div style='text-align: center; padding: 20px;'>
            <h3>💎 批量VIP信息</h3>
            <hr>
            <table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>
                <tr style='background-color: #f0f0f0;'>
                    <th>账号</th>
                    <th>VIP等级</th>
                    <th>到期时间</th>
                    <th>状态</th>
                </tr>
        """
        
        for result_item in results:
            account = result_item.get("account", {})
            username = account.get("username", "未知")
            
            if result_item.get("success", False):
                vip_info = result_item.get("vip_info", {})
                vip_level = vip_info.get("vip_level", "普通用户")
                expire_time = vip_info.get("expire_time", "未开通")
                status = "✅ 成功"
                status_color = "#d4edda"
            else:
                vip_level = "获取失败"
                expire_time = "获取失败"
                status = "❌ 失败"
                status_color = "#f8d7da"
            
            html_content += f"""
                <tr style='background-color: {status_color};'>
                    <td><strong>{username}</strong></td>
                    <td>{vip_level}</td>
                    <td>{expire_time}</td>
                    <td>{status}</td>
                </tr>
            """
        
        html_content += """
            </table>
            <div style='margin-top: 20px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;'>
                <p style='margin: 0; color: #6c757d; font-size: 12px;'>
                    最后更新: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
                </p>
            </div>
        </div>
        """
        
        return html_content
    
    def show_mock_vip_info(self):
        """显示模拟VIP信息"""
        mock_info = {
            "vip_level": "普通用户",
            "expire_time": "未开通",
            "remaining_days": 0,
            "privileges": "无VIP特权"
        }
        self.update_vip_info_display(mock_info)
    
    def update_vip_info_display(self, vip_info: Dict[str, Any]):
        """更新VIP信息显示"""
        # 从真实API返回的数据中提取信息
        vip_level = vip_info.get("vip_level", "0")
        vip_time = vip_info.get("vip_time", "")
        restaurant_name = vip_info.get("restaurant_name", "未知餐厅")
        level = vip_info.get("level", "0")
        gold_raw = vip_info.get("gold", "0")
        vip_privileges = vip_info.get("vip_privileges", [])
        
        # 安全地转换金币为整数以支持千分位格式化
        try:
            gold = int(gold_raw) if gold_raw else 0
        except (ValueError, TypeError):
            gold = 0
        
        # 计算VIP状态
        vip_level_int = int(vip_level) if vip_level.isdigit() else 0
        if vip_level_int > 0:
            vip_status = f"VIP{vip_level_int}"
            level_color = "#ff6b35" if vip_level_int == 1 else "#9c27b0"  # VIP1橙色，VIP2紫色
            status_color = "#28a745"
            expire_time = vip_time if vip_time else "永久"
        else:
            vip_status = "普通用户"
            level_color = "#6c757d"
            status_color = "#6c757d"
            expire_time = "未开通"
        
        # 计算剩余天数
        remaining_days = "永久"
        if vip_time and vip_time != "永久":
            try:
                from datetime import datetime
                expire_dt = datetime.strptime(vip_time, "%Y-%m-%d %H:%M:%S")
                now_dt = datetime.now()
                if expire_dt > now_dt:
                    delta = expire_dt - now_dt
                    remaining_days = f"{delta.days} 天"
                else:
                    remaining_days = "已过期"
                    status_color = "#dc3545"
            except:
                remaining_days = "解析失败"
        
        # 构建特权列表HTML
        privileges_html = ""
        if vip_privileges:
            privileges_html = "<div style='margin-top: 15px;'><h4>🌟 VIP特权对比</h4><table style='width: 100%; border-collapse: collapse;'>"
            privileges_html += "<tr style='background-color: #f8f9fa;'><th style='padding: 8px; border: 1px solid #ddd;'>VIP1特权</th><th style='padding: 8px; border: 1px solid #ddd;'>SVIP特权</th></tr>"
            
            for privilege in vip_privileges:
                vip1_feature = privilege.get("1", "")
                svip_feature = privilege.get("2", "")
                if vip1_feature or svip_feature:
                    privileges_html += f"<tr><td style='padding: 6px; border: 1px solid #ddd; font-size: 12px;'>{vip1_feature}</td><td style='padding: 6px; border: 1px solid #ddd; font-size: 12px;'>{svip_feature}</td></tr>"
            
            privileges_html += "</table></div>"
        
        html_content = f"""
        <div style='padding: 15px;'>
            <h3 style='text-align: center; color: {level_color}; margin-bottom: 20px;'>💎 VIP信息面板</h3>
            
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;'>
                <h4 style='margin-top: 0; color: #333;'>🏪 餐厅信息</h4>
                <p><strong>餐厅名称：</strong> <span style='color: #007bff; font-weight: bold;'>{restaurant_name}</span></p>
                <p><strong>餐厅等级：</strong> <span style='color: #28a745;'>Lv.{level}</span></p>
                <p><strong>金币余额：</strong> <span style='color: #ffc107; font-weight: bold;'>{gold:,}💰</span></p>
            </div>
            
            <div style='background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid {level_color}; margin-bottom: 15px;'>
                <h4 style='margin-top: 0; color: #333;'>👑 VIP状态</h4>
                <p><strong>VIP等级：</strong> <span style='color: {level_color}; font-weight: bold; font-size: 16px;'>{vip_status}</span></p>
                <p><strong>到期时间：</strong> <span style='color: {status_color}; font-weight: bold;'>{expire_time}</span></p>
                <p><strong>剩余时间：</strong> <span style='color: {status_color}; font-weight: bold;'>{remaining_days}</span></p>
            </div>
            
            {privileges_html}
            
            <div style='text-align: center; margin-top: 20px; padding: 10px; background-color: #e9ecef; border-radius: 5px;'>
                <p style='margin: 0; color: #6c757d; font-size: 12px;'>
                    📅 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </div>
        """
        
        self.vip_info_text.setHtml(html_content)
    
    def exchange_cdk(self):
        """兑换CDK"""
        selected_accounts = self.account_selector.get_selected_accounts()
        operation_mode = self.account_selector.get_operation_mode()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        cdk_code = self.cdk_input.text().strip()
        if not cdk_code:
            QMessageBox.warning(self, "提示", "请输入CDK兑换码")
            return
        
        # 根据操作模式显示不同的确认对话框
        if operation_mode == "single":
            account = selected_accounts[0]
            username = account.get("username", "未知")
            reply = QMessageBox.question(
                self, "确认兑换",
                f"确定要为账号 {username} 兑换CDK码: {cdk_code} 吗？\n\n"
                f"⚠️ 注意：\n"
                f"• 每个CDK码只能使用一次\n"
                f"• 兑换后无法撤销\n"
                f"• 请确保CDK码输入正确",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            account_count = len(selected_accounts)
            usernames = [acc.get("username", "未知") for acc in selected_accounts[:3]]
            if account_count > 3:
                usernames.append(f"等{account_count}个")
            
            reply = QMessageBox.question(
                self, "确认批量兑换",
                f"确定要为 {account_count} 个账号批量兑换CDK码: {cdk_code} 吗？\n\n"
                f"🎯 账号列表: {', '.join(usernames)}\n\n"
                f"⚠️ 注意：\n"
                f"• 每个CDK码只能使用一次\n"
                f"• 批量兑换后无法撤销\n"
                f"• 请确保CDK码输入正确\n"
                f"• 总操作数: {account_count} 个账号",
                QMessageBox.Yes | QMessageBox.No
            )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮
        self.cdk_exchange_btn.setEnabled(False)
        self.cdk_exchange_btn.setText("🎁 兑换中...")
        
        if operation_mode == "single":
            # 单个账号兑换
            account = selected_accounts[0]
            self.cdk_thread = QThread()
            self.cdk_worker = CdkExchangeWorker(
                account.get("key", ""), 
                account.get("cookie", {}), 
                cdk_code
            )
            self.cdk_worker.moveToThread(self.cdk_thread)
            
            # 连接信号
            self.cdk_thread.started.connect(self.cdk_worker.do_exchange)
            self.cdk_worker.exchange_completed.connect(self.on_cdk_exchange_completed)
            self.cdk_worker.error_occurred.connect(self.on_cdk_exchange_error)
            
            # 启动线程
            self.cdk_thread.start()
            self.vip_log_message(f"🎁 开始单个兑换CDK: {cdk_code} ({account.get('username', '未知')})")
        else:
            # 批量账号兑换
            self.batch_cdk_thread = QThread()
            self.batch_cdk_worker = BatchCdkExchangeWorker(selected_accounts, cdk_code)
            self.batch_cdk_worker.moveToThread(self.batch_cdk_thread)
            
            # 连接信号
            self.batch_cdk_thread.started.connect(self.batch_cdk_worker.do_batch_exchange)
            self.batch_cdk_worker.exchange_completed.connect(self.on_batch_cdk_exchange_completed)
            self.batch_cdk_worker.error_occurred.connect(self.on_batch_cdk_exchange_error)
            
            # 启动线程
            self.batch_cdk_thread.start()
            self.vip_log_message(f"🎁 开始批量兑换CDK: {cdk_code} ({len(selected_accounts)} 个账号)")
    
    @Slot(dict)
    def on_cdk_exchange_completed(self, result: Dict[str, Any]):
        """CDK兑换完成"""
        self.cdk_exchange_btn.setEnabled(True)
        self.cdk_exchange_btn.setText("🎁 立即兑换")
        
        success = result.get("success", False)
        message = result.get("message", "")
        data = result.get("data", {})
        
        if success:
            self.vip_log_message(f"✅ CDK兑换成功: {message}")
            # 记录兑换历史
            self.add_cdk_history(self.cdk_input.text().strip(), True, message)
            # 清空输入框
            self.cdk_input.clear()
            if data:
                self.vip_log_message(f"🎁 兑换奖励: {data}")
        else:
            self.vip_log_message(f"❌ CDK兑换失败: {message}")
            # 记录兑换历史
            self.add_cdk_history(self.cdk_input.text().strip(), False, message)
        
        # 清理线程
        if self.cdk_thread:
            self.cdk_thread.quit()
            self.cdk_thread.wait()
            self.cdk_thread = None
            self.cdk_worker = None
    
    @Slot(str)
    def on_cdk_exchange_error(self, error_msg: str):
        """CDK兑换错误"""
        self.cdk_exchange_btn.setEnabled(True)
        self.cdk_exchange_btn.setText("🎁 立即兑换")
        self.vip_log_message(f"❌ {error_msg}")
        
        # 记录兑换历史
        self.add_cdk_history(self.cdk_input.text().strip(), False, error_msg)
        
        # 清理线程
        if self.cdk_thread:
            self.cdk_thread.quit()
            self.cdk_thread.wait()
            self.cdk_thread = None
            self.cdk_worker = None
    
    def add_cdk_history(self, cdk_code: str, success: bool, message: str):
        """添加CDK兑换历史"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "✅ 成功" if success else "❌ 失败"
        history_entry = f"[{timestamp}] CDK: {cdk_code} - {status} - {message}\n"
        self.cdk_history_text.append(history_entry)
    
    def purchase_vip(self):
        """购买VIP（120钻石）"""
        selected_accounts = self.account_selector.get_selected_accounts()
        operation_mode = self.account_selector.get_operation_mode()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        cost_diamonds = 120
        
        # 根据操作模式显示不同的确认对话框
        if operation_mode == "single":
            account = selected_accounts[0]
            username = account.get("username", "未知")
            reply = QMessageBox.question(
                self, "确认购买",
                f"确定要为账号 {username} 购买VIP会员吗？\n\n"
                f"💎 费用: {cost_diamonds} 钻石\n"
                f"✨ 获得VIP专属特权\n\n"
                f"⚠️ 请确保账户有足够的钻石余额",
                QMessageBox.Yes | QMessageBox.No
            )
        else:
            account_count = len(selected_accounts)
            usernames = [acc.get("username", "未知") for acc in selected_accounts[:3]]
            if account_count > 3:
                usernames.append(f"等{account_count}个")
            
            total_cost = cost_diamonds * account_count
            reply = QMessageBox.question(
                self, "确认批量购买",
                f"确定要为 {account_count} 个账号批量购买VIP会员吗？\n\n"
                f"🎯 账号列表: {', '.join(usernames)}\n"
                f"💎 单价: {cost_diamonds} 钻石/账号\n"
                f"💰 总计: {total_cost} 钻石\n\n"
                f"⚠️ 请确保每个账户都有足够的钻石余额\n"
                f"• 总操作数: {account_count} 个账号",
                QMessageBox.Yes | QMessageBox.No
            )
        
        if reply != QMessageBox.Yes:
            return
        
        # 执行购买过程
        if operation_mode == "single":
            self.execute_vip_purchase(selected_accounts[0], cost_diamonds)
        else:
            self.execute_batch_vip_purchase(selected_accounts, cost_diamonds)
    
    def execute_vip_purchase(self, account: Dict[str, Any], cost_diamonds: int):
        """执行单个账号VIP购买"""
        if not account:
            return
            
        self.purchase_btn.setEnabled(False)
        self.purchase_btn.setText("💎 购买中...")
        
        username = account.get("username", "未知")
        key = account.get("key", "")
        cookie = account.get("cookie", {})
        
        # 记录购买开始
        self.vip_log_message(f"💎 为账号 {username} 开始购买VIP")
        self.vip_log_message(f"💰 费用: {cost_diamonds} 钻石")
        
        # 创建工作线程
        self.vip_thread = QThread()
        self.vip_worker = VipPurchaseWorker(key, cookie, cost_diamonds)
        self.vip_worker.moveToThread(self.vip_thread)
        
        # 连接信号
        self.vip_thread.started.connect(self.vip_worker.run)
        self.vip_worker.finished.connect(self.on_vip_purchase_completed)
        self.vip_worker.error.connect(self.on_vip_purchase_error)
        
        # 线程清理由信号处理函数负责，不自动删除
        self.vip_worker.finished.connect(self.vip_worker.deleteLater)
        # 移除自动删除线程的连接，由手动清理
        
        # 启动线程
        self.vip_thread.start()
    
    def execute_batch_vip_purchase(self, accounts: List[Dict[str, Any]], cost_diamonds: int):
        """执行批量VIP购买"""
        if not accounts:
            return
            
        self.purchase_btn.setEnabled(False)
        self.purchase_btn.setText("💎 批量购买中...")
        
        account_count = len(accounts)
        
        # 记录批量购买开始
        self.vip_log_message(f"💎 开始批量购买VIP")
        self.vip_log_message(f"💰 费用: {cost_diamonds} 钻石/账号")
        self.vip_log_message(f"📊 账号数量: {account_count}")
        
        # 创建批量工作线程
        self.batch_vip_thread = QThread()
        self.batch_vip_worker = BatchVipPurchaseWorker(accounts, cost_diamonds)
        self.batch_vip_worker.moveToThread(self.batch_vip_thread)
        
        # 连接信号
        self.batch_vip_thread.started.connect(self.batch_vip_worker.run)
        self.batch_vip_worker.finished.connect(self.on_batch_vip_purchase_completed)
        self.batch_vip_worker.error.connect(self.on_batch_vip_purchase_error)
        
        # 线程清理由信号处理函数负责，不自动删除
        self.batch_vip_worker.finished.connect(self.batch_vip_worker.deleteLater)
        # 移除自动删除线程的连接，由手动清理
        
        # 启动线程
        self.batch_vip_thread.start()
    
    def vip_log_message(self, message: str):
        """添加VIP日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.vip_log_text.append(formatted_message)
        
        # 自动滚动到底部
        from PySide6.QtGui import QTextCursor
        cursor = self.vip_log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.vip_log_text.setTextCursor(cursor)
    
    # VIP商店相关方法
    def load_shop_items(self):
        """加载商品列表到表格"""
        try:
            # 获取当前筛选条件
            selected_category = self.category_combo.currentText()
            selected_rarity = self.rarity_combo.currentText()
            
            # 过滤商品
            items = VIP_SHOP_ITEMS.copy()
            
            if selected_category != "全部商品":
                items = [item for item in items if item.category == selected_category]
            
            if selected_rarity != "全部稀有度":
                items = [item for item in items if item.rarity == selected_rarity]
            
            # 更新表格
            self.shop_table.setRowCount(len(items))
            
            for row, item in enumerate(items):
                # 商品图标
                icon_label = QLabel(item.icon)
                icon_label.setAlignment(Qt.AlignCenter)
                icon_label.setStyleSheet("font-size: 24px;")
                self.shop_table.setCellWidget(row, 0, icon_label)
                
                # 商品名称
                name_item = QTableWidgetItem(item.name)
                rarity_color = RARITY_COLORS.get(item.rarity, "#000000")
                name_item.setForeground(QColor(rarity_color))
                self.shop_table.setItem(row, 1, name_item)
                
                # 商品描述
                desc_item = QTableWidgetItem(item.description)
                self.shop_table.setItem(row, 2, desc_item)
                
                # 礼券价格
                price_item = QTableWidgetItem(f"{item.voucher_cost} 🎫")
                price_item.setTextAlignment(Qt.AlignCenter)
                self.shop_table.setItem(row, 3, price_item)
                
                # 数量选择
                quantity_spin = QSpinBox()
                quantity_spin.setMinimum(1)
                quantity_spin.setMaximum(item.max_quantity if item.max_quantity > 0 else 999)
                quantity_spin.setValue(1)
                quantity_spin.setAlignment(Qt.AlignCenter)
                self.shop_table.setCellWidget(row, 4, quantity_spin)
                
                # 购买按钮
                purchase_btn = QPushButton("💳 购买")
                purchase_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; }")
                purchase_btn.clicked.connect(lambda checked, goods_id=item.goods_id, r=row: self.purchase_single_item(goods_id, r))
                self.shop_table.setCellWidget(row, 5, purchase_btn)
                
                # 存储商品ID到行数据
                name_item.setData(Qt.UserRole, item.goods_id)
            
            self.vip_log_message(f"📦 商品列表更新: 显示 {len(items)} 种商品")
            
        except Exception as e:
            self.vip_log_message(f"❌ 加载商品列表失败: {e}")
    
    def refresh_voucher_count(self):
        """刷新VIP礼券数量"""
        selected_accounts = self.account_selector.get_selected_accounts()
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        account = selected_accounts[0]  # 使用第一个账户查询
        
        # 禁用按钮
        self.voucher_count_label.setText("VIP礼券: 查询中...")
        
        # 创建工作线程
        self.voucher_thread = QThread()
        self.voucher_worker = VipVoucherWorker(
            account.get("key", ""),
            account.get("cookie", {})
        )
        self.voucher_worker.moveToThread(self.voucher_thread)
        
        # 连接信号
        self.voucher_thread.started.connect(self.voucher_worker.do_load_vouchers)
        self.voucher_worker.voucher_loaded.connect(self.on_voucher_loaded)
        self.voucher_worker.error_occurred.connect(self.on_voucher_error)
        
        # 启动线程
        self.voucher_thread.start()
        self.vip_log_message(f"🔍 开始查询VIP礼券数量 ({account.get('username', '未知')})")
    
    @Slot(dict)
    def on_voucher_loaded(self, result: Dict[str, Any]):
        """礼券数量加载完成"""
        try:
            if result.get("success", False):
                voucher_count = result.get("voucher_count", 0)
                self.voucher_count_label.setText(f"VIP礼券: {voucher_count} 🎫")
                self.vip_log_message(f"✅ 礼券查询成功: {voucher_count} 张")
                
                # 保存礼券数量供购买时使用
                self.current_voucher_count = voucher_count
            else:
                message = result.get("message", "未知错误")
                self.voucher_count_label.setText("VIP礼券: 查询失败")
                self.vip_log_message(f"❌ 礼券查询失败: {message}")
                self.current_voucher_count = 0
        except Exception as e:
            self.vip_log_message(f"❌ 处理礼券查询结果异常: {e}")
        finally:
            # 清理线程
            self.cleanup_voucher_thread()
    
    @Slot(str)
    def on_voucher_error(self, error: str):
        """礼券查询错误"""
        self.voucher_count_label.setText("VIP礼券: 查询失败")
        self.vip_log_message(f"❌ 礼券查询错误: {error}")
        self.current_voucher_count = 0
        self.cleanup_voucher_thread()
    
    def cleanup_voucher_thread(self):
        """清理礼券查询线程"""
        if hasattr(self, 'voucher_thread') and self.voucher_thread is not None:
            try:
                if not self.voucher_thread.isFinished():
                    self.voucher_thread.quit()
                    self.voucher_thread.wait()
            except RuntimeError:
                pass
            finally:
                self.voucher_thread = None
                self.voucher_worker = None
    
    def on_category_changed(self, category: str):
        """分类筛选变化"""
        self.load_shop_items()
        self.vip_log_message(f"🔍 切换分类过滤: {category}")
    
    def on_rarity_changed(self, rarity: str):
        """稀有度筛选变化"""
        self.load_shop_items()
        self.vip_log_message(f"🔍 切换稀有度过滤: {rarity}")
    
    def purchase_single_item(self, goods_id: int, row: int):
        """购买单个商品"""
        selected_accounts = self.account_selector.get_selected_accounts()
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        # 获取商品信息
        item = get_item_by_id(goods_id)
        if not item:
            QMessageBox.warning(self, "错误", "商品不存在")
            return
        
        # 获取购买数量
        quantity_spin = self.shop_table.cellWidget(row, 4)
        quantity = quantity_spin.value()
        
        # 验证购买
        current_vouchers = getattr(self, 'current_voucher_count', 0)
        validation = validate_purchase(goods_id, quantity, current_vouchers)
        
        if not validation["valid"]:
            QMessageBox.warning(self, "购买失败", validation["error"])
            return
        
        # 确认购买
        total_cost = validation["total_cost"]
        remaining = validation["remaining_vouchers"]
        
        reply = QMessageBox.question(
            self, "确认购买",
            f"确定要购买以下商品吗？\n\n"
            f"🛍️ 商品: {item.icon} {item.name}\n"
            f"📦 数量: {quantity}\n"
            f"💰 单价: {item.voucher_cost} 礼券\n"
            f"💸 总价: {total_cost} 礼券\n"
            f"💳 剩余: {remaining} 礼券\n\n"
            f"⚠️ 注意：购买后无法撤销！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 执行购买
        operation_mode = self.account_selector.get_operation_mode()
        
        if operation_mode == "single":
            # 单个账号购买
            account = selected_accounts[0]
            self.execute_single_purchase(account, goods_id, quantity, item.name)
        else:
            # 批量账号购买
            self.execute_batch_purchase(selected_accounts, goods_id, quantity, item.name)
    
    def execute_single_purchase(self, account: Dict[str, Any], goods_id: int, quantity: int, item_name: str):
        """执行单个账号购买"""
        # 创建工作线程
        self.shop_thread = QThread()
        self.shop_worker = VipShopPurchaseWorker(
            account.get("key", ""),
            account.get("cookie", {}),
            goods_id,
            quantity
        )
        self.shop_worker.moveToThread(self.shop_thread)
        
        # 连接信号
        self.shop_thread.started.connect(self.shop_worker.do_purchase)
        self.shop_worker.purchase_completed.connect(self.on_shop_purchase_completed)
        self.shop_worker.error_occurred.connect(self.on_shop_purchase_error)
        
        # 启动线程
        self.shop_thread.start()
        username = account.get("username", "未知")
        self.vip_log_message(f"🛒 开始购买: {item_name} x{quantity} ({username})")
    
    def execute_batch_purchase(self, accounts: List[Dict[str, Any]], goods_id: int, quantity: int, item_name: str):
        """执行批量账号购买"""
        # 创建工作线程
        self.batch_shop_thread = QThread()
        self.batch_shop_worker = BatchVipShopPurchaseWorker(accounts, goods_id, quantity)
        self.batch_shop_worker.moveToThread(self.batch_shop_thread)
        
        # 连接信号
        self.batch_shop_thread.started.connect(self.batch_shop_worker.do_batch_purchase)
        self.batch_shop_worker.purchase_completed.connect(self.on_batch_shop_purchase_completed)
        self.batch_shop_worker.error_occurred.connect(self.on_batch_shop_purchase_error)
        
        # 启动线程
        self.batch_shop_thread.start()
        self.vip_log_message(f"🛒 开始批量购买: {item_name} x{quantity} ({len(accounts)} 个账号)")
    
    @Slot(dict)
    def on_shop_purchase_completed(self, result: Dict[str, Any]):
        """单个购买完成"""
        try:
            if result.get("success", False):
                goods_id = result.get("goods_id", 0)
                quantity = result.get("quantity", 0)
                item = get_item_by_id(goods_id)
                item_name = item.name if item else f"商品{goods_id}"
                
                self.vip_log_message(f"✅ 购买成功: {item_name} x{quantity}")
                self.shop_result_text.append(f"✅ {item_name} x{quantity} 购买成功")
                
                # 刷新礼券余额
                self.refresh_voucher_count()
            else:
                message = result.get("message", "购买失败")
                self.vip_log_message(f"❌ 购买失败: {message}")
                self.shop_result_text.append(f"❌ 购买失败: {message}")
        except Exception as e:
            self.vip_log_message(f"❌ 处理购买结果异常: {e}")
        finally:
            self.cleanup_shop_thread()
    
    @Slot(str)
    def on_shop_purchase_error(self, error: str):
        """单个购买错误"""
        self.vip_log_message(f"❌ 购买错误: {error}")
        self.shop_result_text.append(f"❌ 购买错误: {error}")
        self.cleanup_shop_thread()
    
    @Slot(dict)
    def on_batch_shop_purchase_completed(self, result: Dict[str, Any]):
        """批量购买完成"""
        try:
            total_accounts = result.get("total_accounts", 0)
            success_count = result.get("success_count", 0)
            failure_count = result.get("failure_count", 0)
            goods_id = result.get("goods_id", 0)
            quantity = result.get("quantity", 0)
            
            item = get_item_by_id(goods_id)
            item_name = item.name if item else f"商品{goods_id}"
            
            self.vip_log_message(f"📊 批量购买完成: {item_name} x{quantity}")
            self.vip_log_message(f"📈 成功: {success_count}/{total_accounts} 个账号")
            
            result_text = f"📊 批量购买结果: {item_name} x{quantity}\n"
            result_text += f"✅ 成功: {success_count} 个账号\n"
            result_text += f"❌ 失败: {failure_count} 个账号\n"
            
            # 显示详细结果
            results = result.get("results", [])
            for account_result in results:
                account_info = account_result.get("account", {})
                username = account_info.get("username", "未知")
                success = account_result.get("success", False)
                message = account_result.get("message", "")
                
                status = "✅" if success else "❌"
                result_text += f"  {status} {username}: {message}\n"
            
            self.shop_result_text.append(result_text)
            
            # 刷新礼券余额
            if success_count > 0:
                self.refresh_voucher_count()
                
        except Exception as e:
            self.vip_log_message(f"❌ 处理批量购买结果异常: {e}")
        finally:
            self.cleanup_batch_shop_thread()
    
    @Slot(str)
    def on_batch_shop_purchase_error(self, error: str):
        """批量购买错误"""
        self.vip_log_message(f"❌ 批量购买错误: {error}")
        self.shop_result_text.append(f"❌ 批量购买错误: {error}")
        self.cleanup_batch_shop_thread()
    
    def cleanup_shop_thread(self):
        """清理单个购买线程"""
        if hasattr(self, 'shop_thread') and self.shop_thread is not None:
            try:
                if not self.shop_thread.isFinished():
                    self.shop_thread.quit()
                    self.shop_thread.wait()
            except RuntimeError:
                pass
            finally:
                self.shop_thread = None
                self.shop_worker = None
    
    def cleanup_batch_shop_thread(self):
        """清理批量购买线程"""
        if hasattr(self, 'batch_shop_thread') and self.batch_shop_thread is not None:
            try:
                if not self.batch_shop_thread.isFinished():
                    self.batch_shop_thread.quit()
                    self.batch_shop_thread.wait()
            except RuntimeError:
                pass
            finally:
                self.batch_shop_thread = None
                self.batch_shop_worker = None
    
    def batch_purchase_selected_items(self):
        """批量购买选中的商品"""
        selected_accounts = self.account_selector.get_selected_accounts()
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先选择账户")
            return
        
        # 获取选中的行
        selected_rows = set()
        for item in self.shop_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要购买的商品（点击表格行）")
            return
        
        # 收集购买信息
        purchase_items = []
        total_cost = 0
        current_vouchers = getattr(self, 'current_voucher_count', 0)
        
        for row in selected_rows:
            # 获取商品ID
            name_item = self.shop_table.item(row, 1)
            if not name_item:
                continue
                
            goods_id = name_item.data(Qt.UserRole)
            item = get_item_by_id(goods_id)
            if not item:
                continue
            
            # 获取数量
            quantity_spin = self.shop_table.cellWidget(row, 4)
            quantity = quantity_spin.value()
            
            # 验证购买
            validation = validate_purchase(goods_id, quantity, current_vouchers - total_cost)
            if not validation["valid"]:
                QMessageBox.warning(
                    self, "购买失败", 
                    f"商品 {item.name} 验证失败：{validation['error']}"
                )
                return
            
            purchase_items.append({
                "goods_id": goods_id,
                "item": item,
                "quantity": quantity,
                "cost": item.voucher_cost * quantity
            })
            total_cost += item.voucher_cost * quantity
        
        if not purchase_items:
            QMessageBox.warning(self, "提示", "没有有效的购买商品")
            return
        
        # 构建确认信息
        confirm_text = f"确定要批量购买以下商品吗？\n\n"
        confirm_text += f"👥 账号数量: {len(selected_accounts)}\n"
        confirm_text += f"🛍️ 商品列表:\n"
        
        for item_info in purchase_items:
            item = item_info["item"]
            quantity = item_info["quantity"]
            cost = item_info["cost"]
            confirm_text += f"  • {item.icon} {item.name} x{quantity} = {cost} 礼券\n"
        
        confirm_text += f"\n💸 单账号总费用: {total_cost} 礼券\n"
        confirm_text += f"💳 当前余额: {current_vouchers} 礼券\n"
        confirm_text += f"💰 购买后余额: {current_vouchers - total_cost} 礼券\n"
        confirm_text += f"\n⚠️ 注意：每个账号都会购买上述所有商品！"
        
        reply = QMessageBox.question(
            self, "确认批量购买",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 执行批量购买
        self.execute_multi_item_batch_purchase(selected_accounts, purchase_items)
    
    def execute_multi_item_batch_purchase(self, accounts: List[Dict[str, Any]], purchase_items: List[Dict[str, Any]]):
        """执行多商品批量购买"""
        self.vip_log_message(f"🛒 开始多商品批量购买: {len(purchase_items)} 种商品 x {len(accounts)} 个账号")
        
        # 显示购买进度
        total_operations = len(accounts) * len(purchase_items)
        completed_operations = 0
        
        # 记录所有结果
        all_results = []
        
        for i, account in enumerate(accounts, 1):
            username = account.get("username", f"账户{i}")
            self.vip_log_message(f"[{i}/{len(accounts)}] 开始为账户 {username} 购买商品")
            
            account_results = []
            account_success = 0
            account_failure = 0
            
            for j, item_info in enumerate(purchase_items, 1):
                goods_id = item_info["goods_id"]
                item = item_info["item"]
                quantity = item_info["quantity"]
                
                self.vip_log_message(f"  [{j}/{len(purchase_items)}] 购买 {item.name} x{quantity}")
                
                # 创建VIP操作实例
                vip_action = VipAction(account.get("key", ""), account.get("cookie", {}))
                result = vip_action.vip_shop_purchase(goods_id, quantity)
                
                # 记录结果
                result["account"] = {
                    "username": username,
                    "key": account.get("key", ""),
                    "index": i
                }
                result["item_info"] = item_info
                
                account_results.append(result)
                completed_operations += 1
                
                if result.get("success", False):
                    account_success += 1
                    self.vip_log_message(f"    ✅ {item.name} x{quantity} 购买成功")
                else:
                    account_failure += 1
                    message = result.get("message", "未知错误")
                    self.vip_log_message(f"    ❌ {item.name} x{quantity} 购买失败: {message}")
            
            # 账户购买汇总
            all_results.extend(account_results)
            self.vip_log_message(f"账户 {username} 购买完成: 成功 {account_success}/{len(purchase_items)} 个商品")
        
        # 生成汇总报告
        self.generate_batch_purchase_report(all_results, accounts, purchase_items)
        
        # 刷新礼券余额
        self.refresh_voucher_count()
    
    def generate_batch_purchase_report(self, all_results: List[Dict[str, Any]], accounts: List[Dict[str, Any]], purchase_items: List[Dict[str, Any]]):
        """生成批量购买报告"""
        total_operations = len(accounts) * len(purchase_items)
        success_count = sum(1 for r in all_results if r.get("success", False))
        failure_count = total_operations - success_count
        
        self.vip_log_message(f"📊 批量购买完成: 成功 {success_count}/{total_operations} 个操作")
        
        # 生成详细报告
        report_text = f"📊 多商品批量购买报告\n"
        report_text += f"{'=' * 50}\n"
        report_text += f"👥 账号数量: {len(accounts)}\n"
        report_text += f"🛍️ 商品种类: {len(purchase_items)}\n"
        report_text += f"🎯 总操作数: {total_operations}\n"
        report_text += f"✅ 成功操作: {success_count}\n"
        report_text += f"❌ 失败操作: {failure_count}\n"
        report_text += f"📈 成功率: {success_count/total_operations*100:.1f}%\n\n"
        
        # 按账号分组显示结果
        report_text += f"📋 详细结果:\n"
        for i, account in enumerate(accounts, 1):
            username = account.get("username", f"账户{i}")
            account_results = [r for r in all_results if r.get("account", {}).get("username") == username]
            
            account_success = sum(1 for r in account_results if r.get("success", False))
            account_total = len(account_results)
            
            report_text += f"\n👤 {username} ({account_success}/{account_total}):\n"
            
            for result in account_results:
                item_info = result.get("item_info", {})
                item = item_info.get("item")
                quantity = item_info.get("quantity", 0)
                
                if item:
                    status = "✅" if result.get("success", False) else "❌"
                    message = result.get("message", "")
                    report_text += f"  {status} {item.name} x{quantity}: {message}\n"
        
        self.shop_result_text.append(report_text)
        
        # 显示成功率统计
        if success_count > 0:
            self.vip_log_message(f"🎉 批量购买成功，建议刷新礼券余额查看最新状态")
    
    @Slot(dict)
    def on_batch_cdk_exchange_completed(self, result: Dict[str, Any]):
        """批量CDK兑换完成"""
        self.cdk_exchange_btn.setEnabled(True)
        self.cdk_exchange_btn.setText("🎁 立即兑换")
        
        success = result.get("success", False)
        message = result.get("message", "")
        results = result.get("results", [])
        success_count = result.get("success_count", 0)
        failure_count = result.get("failure_count", 0)
        total_accounts = result.get("total_accounts", 0)
        cdk_code = result.get("cdk_code", "")
        
        if success:
            self.vip_log_message(f"✅ 批量CDK兑换完成: 成功 {success_count}/{total_accounts} 个账号")
            
            # 记录批量兑换历史
            self.add_cdk_history(cdk_code, True, f"批量兑换: 成功 {success_count}/{total_accounts}")
            
            # 显示详细结果
            for result_item in results:
                account = result_item.get("account", {})
                username = account.get("username", "未知")
                if result_item.get("success", False):
                    item_message = result_item.get("message", "")
                    self.vip_log_message(f"  ✅ {username}: {item_message}")
                else:
                    item_message = result_item.get("message", "未知错误")
                    self.vip_log_message(f"  ❌ {username}: {item_message}")
            
            # 清空输入框
            self.cdk_input.clear()
            
            # 显示批量结果对话框
            QMessageBox.information(
                self, "批量兑换完成",
                f"🎉 批量CDK兑换完成！\n\n"
                f"📊 兑换统计:\n"
                f"• 总账号数: {total_accounts}\n"
                f"• 成功数量: {success_count}\n"
                f"• 失败数量: {failure_count}\n"
                f"• CDK代码: {cdk_code}\n\n"
                f"✨ 详细结果请查看操作日志"
            )
        else:
            self.vip_log_message(f"❌ 批量CDK兑换失败: {message}")
            # 记录兑换历史
            self.add_cdk_history(cdk_code, False, f"批量兑换失败: {message}")
        
        # 清理线程
        if self.batch_cdk_thread:
            self.batch_cdk_thread.quit()
            self.batch_cdk_thread.wait()
            self.batch_cdk_thread = None
            self.batch_cdk_worker = None
    
    @Slot(str)
    def on_batch_cdk_exchange_error(self, error_msg: str):
        """批量CDK兑换错误"""
        self.cdk_exchange_btn.setEnabled(True)
        self.cdk_exchange_btn.setText("🎁 立即兑换")
        self.vip_log_message(f"❌ {error_msg}")
        
        # 记录兑换历史
        cdk_code = self.cdk_input.text().strip()
        self.add_cdk_history(cdk_code, False, f"批量兑换异常: {error_msg}")
        
        # 清理线程
        if self.batch_cdk_thread:
            self.batch_cdk_thread.quit()
            self.batch_cdk_thread.wait()
            self.batch_cdk_thread = None
            self.batch_cdk_worker = None
    
    @Slot(dict)
    def on_vip_purchase_completed(self, result: Dict[str, Any]):
        """VIP购买完成"""
        self.purchase_btn.setEnabled(True)
        self.purchase_btn.setText("💎 立即购买VIP（120钻石）")
        
        success = result.get("success", False)
        message = result.get("message", "")
        cost_diamonds = result.get("cost_diamonds", 120)
        
        if success:
            self.vip_log_message(f"✅ VIP购买成功: {message}")
            self.vip_log_message(f"💎 消耗钻石: {cost_diamonds}")
            
            # 显示成功对话框
            QMessageBox.information(
                self, "购买成功",
                f"🎉 恭喜！VIP购买成功\n\n"
                f"💎 费用: {cost_diamonds} 钻石\n"
                f"✨ VIP特权已激活\n\n"
                f"📝 详细信息: {message}"
            )
        else:
            self.vip_log_message(f"❌ VIP购买失败: {message}")
            QMessageBox.warning(
                self, "购买失败",
                f"❌ VIP购买失败\n\n"
                f"📝 错误信息: {message}\n"
                f"💡 请检查账户钻石余额是否充足"
            )
        
        # 清理线程（安全方式）
        if hasattr(self, 'vip_thread') and self.vip_thread is not None:
            try:
                if not self.vip_thread.isFinished():
                    self.vip_thread.quit()
                    self.vip_thread.wait()
            except RuntimeError:
                pass  # 线程已被删除
            finally:
                self.vip_thread = None
                self.vip_worker = None
    
    @Slot(str)
    def on_vip_purchase_error(self, error_msg: str):
        """VIP购买错误"""
        self.purchase_btn.setEnabled(True)
        self.purchase_btn.setText("💎 立即购买VIP（120钻石）")
        self.vip_log_message(f"❌ {error_msg}")
        
        QMessageBox.critical(
            self, "购买异常",
            f"❌ VIP购买过程中发生异常\n\n"
            f"📝 错误信息: {error_msg}\n"
            f"💡 请稍后重试或联系客服"
        )
        
        # 清理线程（安全方式）
        if hasattr(self, 'vip_thread') and self.vip_thread is not None:
            try:
                if not self.vip_thread.isFinished():
                    self.vip_thread.quit()
                    self.vip_thread.wait()
            except RuntimeError:
                pass  # 线程已被删除
            finally:
                self.vip_thread = None
                self.vip_worker = None
    
    @Slot(dict)
    def on_batch_vip_purchase_completed(self, result: Dict[str, Any]):
        """批量VIP购买完成"""
        self.purchase_btn.setEnabled(True)
        self.purchase_btn.setText("💎 立即购买VIP（120钻石）")
        
        success = result.get("success", False)
        message = result.get("message", "")
        results = result.get("results", [])
        success_count = result.get("success_count", 0)
        failure_count = result.get("failure_count", 0)
        total_accounts = result.get("total_accounts", 0)
        cost_diamonds = result.get("cost_diamonds", 120)
        
        if success:
            self.vip_log_message(f"✅ 批量VIP购买完成: 成功 {success_count}/{total_accounts} 个账号")
            self.vip_log_message(f"💎 总消耗钻石: {cost_diamonds * success_count}")
            
            # 显示详细结果
            QMessageBox.information(
                self, "批量购买完成",
                f"🎉 批量VIP购买已完成！\n\n"
                f"📊 购买统计:\n"
                f"• 总账号数: {total_accounts}\n"
                f"• 成功数量: {success_count}\n"
                f"• 失败数量: {failure_count}\n"
                f"• 单价: {cost_diamonds} 钻石\n"
                f"• 总消耗: {cost_diamonds * success_count} 钻石\n\n"
                f"✨ 详细结果请查看操作日志"
            )
        else:
            self.vip_log_message(f"❌ 批量VIP购买失败: {message}")
        
        # 清理线程（安全方式）
        if hasattr(self, 'batch_vip_thread') and self.batch_vip_thread is not None:
            try:
                if not self.batch_vip_thread.isFinished():
                    self.batch_vip_thread.quit()
                    self.batch_vip_thread.wait()
            except RuntimeError:
                pass  # 线程已被删除
            finally:
                self.batch_vip_thread = None
                self.batch_vip_worker = None
    
    @Slot(str)
    def on_batch_vip_purchase_error(self, error_msg: str):
        """批量VIP购买错误"""
        self.purchase_btn.setEnabled(True)
        self.purchase_btn.setText("💎 立即购买VIP（120钻石）")
        self.vip_log_message(f"❌ {error_msg}")
        
        QMessageBox.critical(
            self, "批量购买异常",
            f"❌ 批量VIP购买过程中发生异常\n\n"
            f"📝 错误信息: {error_msg}\n"
            f"💡 请稍后重试或联系客服"
        )
        
        # 清理线程（安全方式）
        if hasattr(self, 'batch_vip_thread') and self.batch_vip_thread is not None:
            try:
                if not self.batch_vip_thread.isFinished():
                    self.batch_vip_thread.quit()
                    self.batch_vip_thread.wait()
            except RuntimeError:
                pass  # 线程已被删除
            finally:
                self.batch_vip_thread = None
                self.batch_vip_worker = None
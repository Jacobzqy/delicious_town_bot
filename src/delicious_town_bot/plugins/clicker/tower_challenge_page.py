"""
厨塔挑战页面 - 支持批量挑战厨塔
支持设置层数、选择账号、批量执行并展示挑战结果和奖励
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from PySide6.QtCore import Qt, QObject, QThread, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QProgressBar, QTextEdit, QComboBox, QMessageBox,
    QHeaderView, QAbstractItemView, QSplitter, QFrame, QScrollArea
)
from PySide6.QtGui import QFont, QColor

from src.delicious_town_bot.utils.account_manager import AccountManager
from src.delicious_town_bot.actions.challenge import ChallengeAction
from src.delicious_town_bot.actions.user_card import UserCardAction


class ChallengeStatus(Enum):
    """挑战状态枚举"""
    PENDING = ("等待中", "#6c757d")
    RUNNING = ("挑战中", "#007bff")
    SUCCESS = ("成功", "#28a745")
    FAILED = ("失败", "#dc3545")
    SKIPPED = ("跳过", "#ffc107")


class TowerChallengeWorker(QObject):
    """厨塔挑战工作线程"""
    progress_updated = Signal(int, int, str, str)  # 当前进度, 总数, 当前账号, 状态
    challenge_finished = Signal(int, str, bool, str, dict)  # 账号ID, 账号名, 是否成功, 消息, 奖励
    batch_finished = Signal(bool, str, dict)    # 是否全部成功, 总结消息, 统计数据
    
    def __init__(self, level: int, account_list: List[Dict], 
                 interval_seconds: int = 2, manager: AccountManager = None, 
                 use_auto_layer: bool = False, continuous_mode: bool = False):
        super().__init__()
        self.level = level
        self.account_list = account_list  # [{"id": 1, "username": "xxx", "key": "xxx", "recommended_level": N}, ...]
        self.interval_seconds = interval_seconds
        self.manager = manager
        self.use_auto_layer = use_auto_layer  # 是否使用智能层级模式
        self.continuous_mode = continuous_mode  # 是否连续挑战模式
        self.is_cancelled = False
        self.is_paused = False
        self.stats = {"success": 0, "failed": 0, "skipped": 0, "total_rewards": {}, "total_challenges": 0}
        
    def run(self):
        """批量执行厨塔挑战"""
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
            
            # 确定挑战层级
            if self.use_auto_layer and "recommended_level" in account_info:
                challenge_level = account_info["recommended_level"]
                layer_info = f"智能推荐第{challenge_level}层"
            else:
                challenge_level = self.level
                layer_info = f"第{challenge_level}层"
            
            # 发送进度信号
            self.progress_updated.emit(
                i + 1, total_count, username, 
                f"正在挑战{layer_info}厨塔"
            )
            
            # 检查Key是否有效
            if not key:
                self.challenge_finished.emit(account_id, username, False, "账号无Key，跳过", {})
                self.stats["skipped"] += 1
                continue
            
            # 执行厨塔挑战（支持连续挑战模式）
            try:
                print(f"[Tower] 开始挑战 - 账号: {username}, 层数: {challenge_level}")
                
                # 获取cookie信息
                cookie_value = account_info.get("cookie", "123")
                cookie_dict = {"PHPSESSID": cookie_value}
                print(f"[Tower] 使用key: {key[:10]}..., cookie: {cookie_dict}")
                
                challenge_action = ChallengeAction(key=key, cookie=cookie_dict)
                
                # 连续挑战逻辑
                if self.continuous_mode:
                    self._continuous_challenge(challenge_action, challenge_level, account_id, username, i + 1, total_count)
                else:
                    # 单次挑战
                    self._single_challenge(challenge_action, challenge_level, account_id, username)
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                error_msg = f"挑战异常: {type(e).__name__}: {str(e)}"
                print(f"[Tower] 挑战异常 - 账号: {username}")
                print(f"[Tower] 异常详情: {error_detail}")
                self.challenge_finished.emit(account_id, username, False, error_msg, {})
                self.stats["failed"] += 1
            
            # 间隔等待（除了最后一个）
            if i < total_count - 1 and not self.is_cancelled:
                time.sleep(self.interval_seconds)
        
        # 发送批次完成信号
        if not self.is_cancelled:
            total_challenges = self.stats["total_challenges"]
            success_count = self.stats["success"]
            failed_count = self.stats["failed"]
            skipped_count = self.stats["skipped"]
            
            if total_challenges > 0:
                success_rate = (success_count / total_challenges) * 100
                if self.continuous_mode:
                    summary = f"连续挑战完成：总计{total_challenges}次挑战，成功{success_count}次，失败{failed_count}次，跳过{skipped_count}个账号，成功率{success_rate:.1f}%"
                else:
                    summary = f"批量挑战完成：成功{success_count}个，失败{failed_count}个，跳过{skipped_count}个，成功率{success_rate:.1f}%"
            else:
                summary = f"挑战完成：跳过{skipped_count}个账号"
            
            self.batch_finished.emit(True, summary, self.stats)
    
    def _single_challenge(self, challenge_action, challenge_level: int, account_id: int, username: str):
        """执行单次挑战"""
        result = challenge_action.attack_tower(level=challenge_level)
        
        success = result.get("success", False)
        message = result.get("message", "未知结果")
        rewards = result.get("rewards", {})
        
        print(f"[Tower] 挑战结果 - 账号: {username}, 成功: {success}, 消息: {message}")
        print(f"[Tower] 奖励详情 - {rewards}")
        
        # 更新统计
        self.stats["total_challenges"] += 1
        if success:
            self.stats["success"] += 1
            self._accumulate_rewards(rewards)
        else:
            self.stats["failed"] += 1
        
        # 发送结果信号
        self.challenge_finished.emit(account_id, username, success, message, rewards)
    
    def _continuous_challenge(self, challenge_action, challenge_level: int, account_id: int, username: str, current_account: int, total_accounts: int):
        """执行连续挑战直到体力不足或次数用尽"""
        challenge_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 3  # 连续失败3次就停止
        
        while not self.is_cancelled and not self.is_paused:
            challenge_count += 1
            
            # 更新进度显示
            self.progress_updated.emit(
                current_account, total_accounts, username,
                f"连续挑战第{challenge_count}次 {challenge_level}层"
            )
            
            result = challenge_action.attack_tower(level=challenge_level)
            
            success = result.get("success", False)
            message = result.get("message", "未知结果")
            rewards = result.get("rewards", {})
            
            print(f"[Tower] 连续挑战第{challenge_count}次 - 账号: {username}, 成功: {success}, 消息: {message}")
            print(f"[Tower] 奖励详情 - {rewards}")
            
            # 更新统计
            self.stats["total_challenges"] += 1
            if success:
                self.stats["success"] += 1
                self._accumulate_rewards(rewards)
                consecutive_failures = 0  # 重置连续失败计数
            else:
                self.stats["failed"] += 1
                consecutive_failures += 1
            
            # 发送结果信号
            self.challenge_finished.emit(account_id, username, success, message, rewards)
            
            # 检查是否应该停止挑战
            should_stop, stop_reason = self._should_stop_challenge(message, consecutive_failures, max_consecutive_failures)
            if should_stop:
                print(f"[Tower] 停止连续挑战 - 账号: {username}, 原因: {stop_reason}")
                # 发送停止原因通知
                self.challenge_finished.emit(account_id, username, False, f"连续挑战结束: {stop_reason}", {})
                break
            
            # 短暂间隔
            if not self.is_cancelled:
                time.sleep(0.5)  # 连续挑战间隔较短
    
    def _should_stop_challenge(self, message: str, consecutive_failures: int, max_consecutive_failures: int) -> Tuple[bool, str]:
        """判断是否应该停止挑战"""
        # 检查体力不足
        if "体力不足" in message or "体力值不足" in message:
            return True, "体力不足"
        
        # 检查挑战次数用尽
        if "挑战次数" in message and ("不足" in message or "用完" in message or "已用尽" in message):
            return True, "挑战次数已用尽"
        
        # 检查其他可能的停止条件
        stop_keywords = [
            "今日挑战次数已满", "挑战次数已达上限", "无法继续挑战",
            "等级不足", "权限不足", "服务器维护"
        ]
        for keyword in stop_keywords:
            if keyword in message:
                return True, f"系统限制: {keyword}"
        
        # 检查连续失败次数
        if consecutive_failures >= max_consecutive_failures:
            return True, f"连续失败{consecutive_failures}次"
        
        return False, ""
    
    def _accumulate_rewards(self, rewards: Dict[str, Any]):
        """累积奖励统计"""
        for reward_type, value in rewards.items():
            if reward_type == "items" and isinstance(value, dict):
                # 处理物品奖励
                if "items" not in self.stats["total_rewards"]:
                    self.stats["total_rewards"]["items"] = {}
                for item_name, item_count in value.items():
                    current = self.stats["total_rewards"]["items"].get(item_name, 0)
                    self.stats["total_rewards"]["items"][item_name] = current + item_count
            elif reward_type in ["score", "penalty"]:
                # 跳过比分信息和处罚信息，这些不需要累积
                continue
            elif isinstance(value, (int, float)):
                # 处理数值奖励（声望、金币、经验）
                current = self.stats["total_rewards"].get(reward_type, 0)
                self.stats["total_rewards"][reward_type] = current + value
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True
    
    def pause(self):
        """暂停执行"""
        self.is_paused = True
    
    def resume(self):
        """恢复执行"""
        self.is_paused = False


class TowerChallengeResultWidget(QWidget):
    """挑战结果展示组件"""
    
    def __init__(self):
        super().__init__()
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 结果表格
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "账号", "状态", "消息", "比分", "声望", "金币", "经验", "物品"
        ])
        
        # 设置表格属性
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # 设置列宽
        header = self.results_table.horizontalHeader()
        header.resizeSection(0, 100)  # 账号列
        header.resizeSection(1, 80)   # 状态列
        header.resizeSection(2, 180)  # 消息列
        header.resizeSection(3, 80)   # 比分列
        header.resizeSection(4, 60)   # 声望列
        header.resizeSection(5, 60)   # 金币列
        header.resizeSection(6, 60)   # 经验列
        header.resizeSection(7, 120)  # 物品列
        
        layout.addWidget(QLabel("挑战结果"))
        layout.addWidget(self.results_table)
        
        # 奖励统计
        self.rewards_display = QTextEdit()
        self.rewards_display.setMaximumHeight(150)
        self.rewards_display.setPlaceholderText("奖励统计将在挑战完成后显示...")
        
        layout.addWidget(QLabel("奖励统计"))
        layout.addWidget(self.rewards_display)
    
    def add_result(self, account_id: int, username: str, success: bool, 
                   message: str, rewards: Dict[str, Any]):
        """添加挑战结果"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # 状态显示
        status = "✅ 成功" if success else "❌ 失败"
        status_color = "#28a745" if success else "#dc3545"
        
        # 提取比分信息
        score_info = rewards.get("score", {})
        if score_info:
            user_power = score_info.get("user_power", 0)
            opponent_power = score_info.get("opponent_power", 0)
            # 格式化显示，如果是整数则显示为整数，否则保留1位小数
            if isinstance(user_power, float) and user_power.is_integer():
                user_power = int(user_power)
            elif isinstance(user_power, float):
                user_power = round(user_power, 1)
            
            if isinstance(opponent_power, float) and opponent_power.is_integer():
                opponent_power = int(opponent_power)
            elif isinstance(opponent_power, float):
                opponent_power = round(opponent_power, 1)
                
            score_text = f"{user_power} : {opponent_power}"
        else:
            score_text = "-"
        
        # 提取奖励/处罚数据
        reputation = rewards.get("reputation", 0)
        gold = rewards.get("gold", 0)
        experience = rewards.get("experience", 0)
        
        # 处理物品奖励
        items_reward = rewards.get("items", {})
        if items_reward:
            item_texts = [f"{name}x{count}" for name, count in items_reward.items()]
            items_display = ", ".join(item_texts[:3])  # 最多显示3个物品
            if len(items_reward) > 3:
                items_display += f" 等{len(items_reward)}种"
        else:
            items_display = "-"
        
        # 处理消息显示 - 限制长度防止显示异常
        display_message = message
        if len(message) > 40:
            display_message = message[:37] + "..."
        
        # 设置表格项
        items = [
            username,
            status,
            display_message,
            score_text,
            str(reputation) if reputation != 0 else "-",
            str(gold) if gold else "-",
            str(experience) if experience else "-",
            items_display
        ]
        
        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 设置状态列颜色
            if col == 1:  # 状态列
                item.setForeground(Qt.GlobalColor.white)
                item.setBackground(Qt.GlobalColor.green if success else Qt.GlobalColor.red)
            
            # 为消息列设置工具提示，显示完整消息
            if col == 2:  # 消息列
                item.setToolTip(message)  # 鼠标悬停显示完整消息
            
            # 设置声望列颜色（失败时为红色表示处罚）
            if col == 4 and reputation != 0:  # 声望列
                if not success and reputation < 0:
                    item.setForeground(QColor("#dc3545"))  # 红色表示处罚
                    item.setText(f"{reputation} (处罚)")
                elif success and reputation > 0:
                    item.setForeground(QColor("#28a745"))  # 绿色表示奖励
            
            # 为物品列设置工具提示，显示完整物品列表
            if col == 7 and items_reward:  # 物品列
                full_items = ", ".join([f"{name}x{count}" for name, count in items_reward.items()])
                item.setToolTip(full_items)
            
            self.results_table.setItem(row, col, item)
        
        # 自动滚动到最新结果
        self.results_table.scrollToBottom()
    
    def display_final_rewards(self, total_rewards: Dict[str, Any]):
        """显示最终奖励统计"""
        if not total_rewards:
            self.rewards_display.setText("本次挑战未获得任何奖励。")
            return
        
        reward_text = "🏆 **本次批量挑战总结**\n\n"
        
        # 基础奖励/处罚
        basic_rewards = []
        if "reputation" in total_rewards:
            reputation_total = total_rewards['reputation']
            if reputation_total > 0:
                basic_rewards.append(f"声望: +{reputation_total}")
            elif reputation_total < 0:
                basic_rewards.append(f"声望: {reputation_total} (净处罚)")
            else:
                basic_rewards.append(f"声望: 0 (收支平衡)")
        if "gold" in total_rewards:
            basic_rewards.append(f"金币: +{total_rewards['gold']}")
        if "experience" in total_rewards:
            basic_rewards.append(f"经验: +{total_rewards['experience']}")
        
        if basic_rewards:
            reward_text += "💰 **资源变化**\n" + "  |  ".join(basic_rewards) + "\n\n"
        
        # 物品奖励
        items = total_rewards.get("items", {})
        if items:
            reward_text += "🎁 **物品奖励**\n"
            for item_name, count in items.items():
                reward_text += f"• {item_name} x{count}\n"
        
        if not basic_rewards and not items:
            reward_text += "本次挑战未获得奖励。"
        
        self.rewards_display.setText(reward_text)
    
    def clear_results(self):
        """清空结果"""
        self.results_table.setRowCount(0)
        self.rewards_display.clear()


class TowerChallengePage(QWidget):
    """厨塔挑战主页面"""
    
    def __init__(self, manager: AccountManager, log_widget=None):
        super().__init__()
        self.manager = manager
        self.log_widget = log_widget  # 添加日志组件引用
        self.worker = None
        self.worker_thread = None
        self.setupUI()
        self.load_accounts()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("厨塔挑战")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # 右侧：结果展示
        self.result_widget = TowerChallengeResultWidget()
        splitter.addWidget(self.result_widget)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 1)  # 控制面板
        splitter.setStretchFactor(1, 2)  # 结果展示
        
        layout.addWidget(splitter)
        
        # 底部状态栏
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("准备就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.status_layout.addWidget(self.status_label)
        self.status_layout.addWidget(self.progress_bar)
        self.status_layout.addStretch()
        
        layout.addLayout(self.status_layout)
    
    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(350)
        layout = QVBoxLayout(panel)
        
        # 层数选择
        level_group = QGroupBox("挑战设置")
        level_layout = QGridLayout(level_group)
        
        level_layout.addWidget(QLabel("厨塔层数:"), 0, 0)
        self.level_spinbox = QSpinBox()
        self.level_spinbox.setRange(1, 9)
        self.level_spinbox.setValue(1)
        self.level_spinbox.setSuffix("层")
        level_layout.addWidget(self.level_spinbox, 0, 1)
        
        level_layout.addWidget(QLabel("间隔时间:"), 1, 0)
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 10)
        self.interval_spinbox.setValue(2)
        self.interval_spinbox.setSuffix("秒")
        level_layout.addWidget(self.interval_spinbox, 1, 1)
        
        # 自动层级模式
        self.auto_layer_checkbox = QCheckBox("智能层级模式")
        self.auto_layer_checkbox.setToolTip("启用后，每个账号将挑战根据其厨力推荐的最佳层级")
        level_layout.addWidget(self.auto_layer_checkbox, 2, 0, 1, 2)
        
        # 获取推荐按钮
        self.get_recommendations_btn = QPushButton("分析推荐层级")
        self.get_recommendations_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; }")
        level_layout.addWidget(self.get_recommendations_btn, 3, 0, 1, 2)
        
        # 连续挑战模式
        self.continuous_mode_checkbox = QCheckBox("连续挑战模式")
        self.continuous_mode_checkbox.setToolTip("启用后，每个账号将持续挑战直到体力不足或次数用尽")
        level_layout.addWidget(self.continuous_mode_checkbox, 4, 0, 1, 2)
        
        layout.addWidget(level_group)
        
        # 账号选择
        accounts_group = QGroupBox("账号选择")
        accounts_layout = QVBoxLayout(accounts_group)
        
        # 批量操作按钮
        batch_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_none_btn = QPushButton("全不选")
        self.select_valid_btn = QPushButton("选择有Key账号")
        
        batch_layout.addWidget(self.select_all_btn)
        batch_layout.addWidget(self.select_none_btn)
        batch_layout.addWidget(self.select_valid_btn)
        accounts_layout.addLayout(batch_layout)
        
        # 账号列表
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(6)
        self.accounts_table.setHorizontalHeaderLabels(["选择", "用户名", "餐厅", "Key状态", "推荐层级", "真实厨力"])
        self.accounts_table.verticalHeader().setVisible(False)
        self.accounts_table.setAlternatingRowColors(True)
        self.accounts_table.horizontalHeader().setStretchLastSection(True)
        self.accounts_table.setMaximumHeight(280)
        
        accounts_layout.addWidget(self.accounts_table)
        layout.addWidget(accounts_group)
        
        # 控制按钮
        control_group = QGroupBox("操作控制")
        control_layout = QVBoxLayout(control_group)
        
        self.start_btn = QPushButton("开始挑战")
        self.start_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 8px; }")
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("清空结果")
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.cancel_btn)
        control_layout.addWidget(self.clear_btn)
        
        layout.addWidget(control_group)
        layout.addStretch()
        
        # 连接信号
        self.select_all_btn.clicked.connect(self.select_all_accounts)
        self.select_none_btn.clicked.connect(self.select_no_accounts)
        self.select_valid_btn.clicked.connect(self.select_valid_accounts)
        self.get_recommendations_btn.clicked.connect(self.analyze_tower_recommendations)
        
        self.start_btn.clicked.connect(self.start_challenge)
        self.pause_btn.clicked.connect(self.pause_challenge)
        self.cancel_btn.clicked.connect(self.cancel_challenge)
        self.clear_btn.clicked.connect(self.clear_results)
        
        return panel
    
    def load_accounts(self):
        """加载账号列表"""
        self.accounts_table.setRowCount(0)
        accounts = self.manager.list_accounts()
        
        for account in accounts:
            row = self.accounts_table.rowCount()
            self.accounts_table.insertRow(row)
            
            # 选择框
            checkbox = QCheckBox()
            if account.key:  # 默认选择有Key的账号
                checkbox.setChecked(True)
            self.accounts_table.setCellWidget(row, 0, checkbox)
            
            # 用户名
            username_item = QTableWidgetItem(account.username)
            username_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            username_item.setFlags(username_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            username_item.setData(Qt.ItemDataRole.UserRole, account.id)  # 存储账号ID
            self.accounts_table.setItem(row, 1, username_item)
            
            # 餐厅
            restaurant_item = QTableWidgetItem(account.restaurant or "-")
            restaurant_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            restaurant_item.setFlags(restaurant_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.accounts_table.setItem(row, 2, restaurant_item)
            
            # Key状态
            key_status = "有Key" if account.key else "无Key"
            key_item = QTableWidgetItem(key_status)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if account.key:
                key_item.setForeground(Qt.GlobalColor.green)
            else:
                key_item.setForeground(Qt.GlobalColor.red)
            self.accounts_table.setItem(row, 3, key_item)
            
            # 推荐层级
            recommend_item = QTableWidgetItem("未分析")
            recommend_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            recommend_item.setFlags(recommend_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.accounts_table.setItem(row, 4, recommend_item)
            
            # 真实厨力
            power_item = QTableWidgetItem("未计算")
            power_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            power_item.setFlags(power_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.accounts_table.setItem(row, 5, power_item)
            
            # 存储完整账号信息
            username_item.setData(Qt.ItemDataRole.UserRole + 1, {
                "id": account.id,
                "username": account.username,
                "key": account.key,
                "cookie": account.cookie or "123"  # 确保有默认cookie
            })
    
    def analyze_tower_recommendations(self):
        """分析厨塔推荐层级"""
        self.get_recommendations_btn.setEnabled(False)
        self.get_recommendations_btn.setText("分析中...")
        self.status_label.setText("正在分析厨塔推荐...")
        
        analyzed_count = 0
        total_accounts = 0
        
        for row in range(self.accounts_table.rowCount()):
            username_item = self.accounts_table.item(row, 1)
            key_item = self.accounts_table.item(row, 3)
            recommend_item = self.accounts_table.item(row, 4)
            power_item = self.accounts_table.item(row, 5)
            
            if not username_item or not key_item:
                continue
                
            # 只分析有Key的账号
            if key_item.text() != "有Key":
                recommend_item.setText("无Key")
                power_item.setText("无Key")
                continue
            
            total_accounts += 1
            account_data = username_item.data(Qt.ItemDataRole.UserRole + 1)
            if not account_data:
                continue
            
            username = account_data["username"]
            key = account_data["key"]
            cookie_value = account_data["cookie"]
            
            try:
                self.status_label.setText(f"正在分析 {username} 的厨塔推荐...")
                
                # 创建UserCardAction并获取推荐
                cookie_dict = {"PHPSESSID": cookie_value}
                user_card_action = UserCardAction(key=key, cookie=cookie_dict)
                result = user_card_action.get_tower_recommendations()
                
                if result.get("success"):
                    # 提取真实厨力和推荐层级
                    power_analysis = result.get("user_power_analysis", {})
                    recommendations = result.get("tower_recommendations", {})
                    
                    real_power = power_analysis.get("total_real_power", 0)
                    best_floor = recommendations.get("best_floor")
                    
                    # 更新显示
                    power_item.setText(str(int(real_power)))
                    power_item.setForeground(QColor("#e67e22"))
                    
                    if best_floor:
                        recommend_level = best_floor.get("level", 1)
                        recommend_item.setText(f"{recommend_level}层")
                        recommend_item.setForeground(QColor("#27ae60"))
                        
                        # 存储推荐层级到数据中
                        account_data["recommended_level"] = recommend_level
                        account_data["real_power"] = real_power
                        username_item.setData(Qt.ItemDataRole.UserRole + 1, account_data)
                        
                        analyzed_count += 1
                    else:
                        recommend_item.setText("无推荐")
                        recommend_item.setForeground(QColor("#f39c12"))
                else:
                    error_msg = result.get("message", "分析失败")
                    recommend_item.setText("分析失败")
                    recommend_item.setToolTip(error_msg)
                    recommend_item.setForeground(QColor("#e74c3c"))
                    power_item.setText("分析失败")
                    power_item.setForeground(QColor("#e74c3c"))
                    
                    if self.log_widget:
                        self.log_widget.append(f"❌ 厨塔分析失败 - {username}: {error_msg}")
                
            except Exception as e:
                error_msg = str(e)
                recommend_item.setText("异常")
                recommend_item.setToolTip(error_msg)
                recommend_item.setForeground(QColor("#e74c3c"))
                power_item.setText("异常")
                power_item.setForeground(QColor("#e74c3c"))
                
                if self.log_widget:
                    self.log_widget.append(f"❌ 厨塔分析异常 - {username}: {error_msg}")
            
            # 短暂延迟避免请求过快
            import time
            time.sleep(0.5)
        
        # 完成分析
        self.get_recommendations_btn.setEnabled(True)
        self.get_recommendations_btn.setText("分析推荐层级")
        
        if total_accounts > 0:
            success_rate = (analyzed_count / total_accounts) * 100
            summary = f"厨塔分析完成：成功分析 {analyzed_count}/{total_accounts} 个账号 ({success_rate:.1f}%)"
            self.status_label.setText(summary)
            
            if self.log_widget:
                self.log_widget.append(f"🏗️ {summary}")
        else:
            self.status_label.setText("没有可分析的账号（需要有Key的账号）")
    
    def select_all_accounts(self):
        """全选账号"""
        for row in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def select_no_accounts(self):
        """取消选择所有账号"""
        for row in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def select_valid_accounts(self):
        """选择有Key的账号"""
        for row in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(row, 0)
            key_item = self.accounts_table.item(row, 3)
            if checkbox and key_item:
                has_key = key_item.text() == "有Key"
                checkbox.setChecked(has_key)
    
    def get_selected_accounts(self) -> List[Dict]:
        """获取选中的账号列表"""
        selected_accounts = []
        for row in range(self.accounts_table.rowCount()):
            checkbox = self.accounts_table.cellWidget(row, 0)
            username_item = self.accounts_table.item(row, 1)
            
            if checkbox and checkbox.isChecked() and username_item:
                account_data = username_item.data(Qt.ItemDataRole.UserRole + 1)
                if account_data:
                    selected_accounts.append(account_data)
        
        return selected_accounts
    
    def start_challenge(self):
        """开始挑战"""
        selected_accounts = self.get_selected_accounts()
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请至少选择一个账号进行挑战！")
            return
        
        level = self.level_spinbox.value()
        interval = self.interval_spinbox.value()
        use_auto_layer = self.auto_layer_checkbox.isChecked()
        continuous_mode = self.continuous_mode_checkbox.isChecked()
        
        # 验证智能层级模式
        if use_auto_layer:
            accounts_with_recommendations = [acc for acc in selected_accounts if "recommended_level" in acc]
            if not accounts_with_recommendations:
                QMessageBox.warning(
                    self, "智能层级模式", 
                    "启用智能层级模式需要先点击'分析推荐层级'按钮分析账号的推荐层级！"
                )
                return
            elif len(accounts_with_recommendations) < len(selected_accounts):
                missing_count = len(selected_accounts) - len(accounts_with_recommendations)
                reply = QMessageBox.question(
                    self, "智能层级模式", 
                    f"有 {missing_count} 个账号没有推荐层级数据，这些账号将使用固定层级 {level}。\n\n继续挑战吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        
        # 确认对话框
        if use_auto_layer:
            layer_info = "智能推荐层级"
        else:
            layer_info = f"第 {level} 层"
        
        challenge_mode = "连续挑战" if continuous_mode else "单次挑战"
        
        confirmation_text = f"确定要让 {len(selected_accounts)} 个账号{challenge_mode}{layer_info}厨塔吗？"
        if continuous_mode:
            confirmation_text += "\n\n⚠️ 连续挑战模式：每个账号将持续挑战直到体力不足或次数用尽"
            
        reply = QMessageBox.question(
            self, "确认挑战", 
            confirmation_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 清空之前的结果
        self.result_widget.clear_results()
        
        # 创建工作线程
        self.worker = TowerChallengeWorker(level, selected_accounts, interval, self.manager, use_auto_layer, continuous_mode)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        # 连接信号
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.challenge_finished.connect(self.result_widget.add_result)
        self.worker.challenge_finished.connect(self.log_challenge_result)
        self.worker.batch_finished.connect(self.on_batch_finished)
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_accounts))
        self.progress_bar.setValue(0)
        
        # 启动线程
        self.worker_thread.start()
    
    def pause_challenge(self):
        """暂停/恢复挑战"""
        if self.worker:
            if self.worker.is_paused:
                self.worker.resume()
                self.pause_btn.setText("暂停")
                self.status_label.setText("挑战恢复...")
            else:
                self.worker.pause()
                self.pause_btn.setText("恢复")
                self.status_label.setText("挑战已暂停")
    
    def cancel_challenge(self):
        """取消挑战"""
        if self.worker:
            self.worker.cancel()
        self.reset_ui_state()
    
    def clear_results(self):
        """清空结果"""
        self.result_widget.clear_results()
        self.status_label.setText("结果已清空")
    
    @Slot(int, int, str, str)
    def update_progress(self, current: int, total: int, username: str, status: str):
        """更新进度"""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"({current}/{total}) {username}: {status}")
    
    @Slot(int, str, bool, str, dict)
    def log_challenge_result(self, account_id: int, username: str, success: bool, message: str, rewards: dict):
        """记录挑战结果到日志"""
        if self.log_widget:
            status_icon = "✅" if success else "❌"
            
            # 构建比分信息
            score_info = ""
            if "score" in rewards:
                score_data = rewards["score"]
                user_power = score_data.get("user_power", 0)
                opponent_power = score_data.get("opponent_power", 0)
                
                # 格式化比分显示
                if isinstance(user_power, float) and user_power.is_integer():
                    user_power = int(user_power)
                elif isinstance(user_power, float):
                    user_power = round(user_power, 1)
                
                if isinstance(opponent_power, float) and opponent_power.is_integer():
                    opponent_power = int(opponent_power)
                elif isinstance(opponent_power, float):
                    opponent_power = round(opponent_power, 1)
                    
                score_info = f" ({user_power}:{opponent_power})"
            
            # 构建奖励/处罚信息
            reward_summary = ""
            if rewards:
                reward_parts = []
                if "reputation" in rewards:
                    reputation = rewards['reputation']
                    if success:
                        reward_parts.append(f"声望+{reputation}")
                    else:
                        reward_parts.append(f"声望{reputation}(处罚)")
                if "gold" in rewards:
                    reward_parts.append(f"金币+{rewards['gold']}")
                if "experience" in rewards:
                    reward_parts.append(f"经验+{rewards['experience']}")
                if "items" in rewards:
                    items = rewards["items"]
                    item_count = len(items)
                    if item_count <= 2:
                        for item_name, count in items.items():
                            reward_parts.append(f"{item_name}x{count}")
                    else:
                        reward_parts.append(f"物品{item_count}种")
                if reward_parts:
                    reward_summary = f" | {', '.join(reward_parts)}"
            
            log_message = f"🏗️ 厨塔挑战 {status_icon} {username}{score_info}: {message}{reward_summary}"
            self.log_widget.append(log_message)
    
    @Slot(bool, str, dict)
    def on_batch_finished(self, success: bool, summary: str, stats: dict):
        """批次完成处理"""
        self.status_label.setText(summary)
        self.result_widget.display_final_rewards(stats.get("total_rewards", {}))
        
        # 记录总结到日志
        if self.log_widget:
            self.log_widget.append(f"🏗️ 厨塔挑战批次完成: {summary}")
            total_rewards = stats.get("total_rewards", {})
            if total_rewards:
                reward_summary = []
                for reward_type, value in total_rewards.items():
                    if reward_type == "items" and isinstance(value, dict):
                        item_count = sum(value.values())
                        reward_summary.append(f"物品{item_count}个")
                    else:
                        reward_summary.append(f"{reward_type}+{value}")
                if reward_summary:
                    self.log_widget.append(f"🏆 总奖励: {', '.join(reward_summary)}")
        
        self.reset_ui_state()
        
        # 显示完成通知
        QMessageBox.information(self, "挑战完成", summary)
    
    def reset_ui_state(self):
        """重置UI状态"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # 清理线程
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.worker = None
        self.worker_thread = None


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试用的AccountManager（需要数据库）
    try:
        from src.delicious_town_bot.utils.account_manager import AccountManager
        manager = AccountManager()
        
        window = TowerChallengePage(manager)
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"测试运行失败: {e}")
        print("请确保数据库已正确配置")
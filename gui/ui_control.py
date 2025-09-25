"""
手動控制界面模組

提供手動控制發球機的功能，包括：
- 單發模式：點擊位置按鈕直接發球
- 連發模式：設定球數和間隔，連續發球
- 25宮格發球區域控制
"""

import asyncio
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, 
                             QGroupBox, QTabWidget, QProgressBar, QDialog, QGridLayout, QHBoxLayout, 
                             QScrollArea, QSpinBox, QDoubleSpinBox, QCheckBox, QSlider, QButtonGroup, QRadioButton)
from PyQt5.QtCore import Qt, QTimer
from commands import read_data_from_json
import time
from qasync import asyncSlot
from .ui_utils import create_area_buttons as utils_create_area_buttons
from core.services.device_service import DeviceService

def create_manual_tab(self):
    """創建手動控制標籤頁（含單機/雙機子頁）"""
    manual_tabs = QTabWidget()
    single_tab = _create_single_manual_tab(self)
    dual_tab = _create_dual_manual_tab(self)
    manual_tabs.addTab(single_tab, "🔧 單發球機")
    manual_tabs.addTab(dual_tab, "🤖 雙發球機")
    self.tab_widget.addTab(manual_tabs, "手動控制")


def _create_single_manual_tab(self) -> QWidget:
    """建立單發球機手動控制子頁"""
    manual_widget = QWidget()
    layout = QVBoxLayout(manual_widget)

    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)

    # 單發/連發模式
    burst_group = QGroupBox("🚀 BURST MODE • 單機連發系統")
    burst_layout = QVBoxLayout(burst_group)

    mode_selection_layout = QHBoxLayout()
    mode_selection_layout.addWidget(QLabel("🎯 發球模式:"))

    self.single_shot_mode_group = QButtonGroup()
    self.single_single_mode_radio = QRadioButton("單發模式")
    self.single_burst_mode_radio = QRadioButton("連發模式")
    self.single_single_mode_radio.setChecked(True)
    self.single_shot_mode_group.addButton(self.single_single_mode_radio, 0)
    self.single_shot_mode_group.addButton(self.single_burst_mode_radio, 1)

    mode_selection_layout.addWidget(self.single_single_mode_radio)
    mode_selection_layout.addWidget(self.single_burst_mode_radio)
    mode_selection_layout.addStretch()
    burst_layout.addLayout(mode_selection_layout)

    # 連發設定（單機）
    burst_settings_layout = QHBoxLayout()

    # 球數
    single_ball_count_layout = QVBoxLayout()
    single_ball_count_layout.addWidget(QLabel("發球數量:"))
    self.single_ball_count_spinbox = QSpinBox()
    self.single_ball_count_spinbox.setRange(1, 50)
    self.single_ball_count_spinbox.setValue(5)
    single_ball_count_layout.addWidget(self.single_ball_count_spinbox)
    burst_settings_layout.addLayout(single_ball_count_layout)

    # 間隔
    single_interval_layout = QVBoxLayout()
    single_interval_layout.addWidget(QLabel("發球間隔 (秒):"))
    self.single_interval_spinbox = QSpinBox()
    self.single_interval_spinbox.setRange(1, 10)
    self.single_interval_spinbox.setValue(2)
    self.single_interval_spinbox.setSuffix(" 秒")
    single_interval_layout.addWidget(self.single_interval_spinbox)
    burst_settings_layout.addLayout(single_interval_layout)

    burst_layout.addLayout(burst_settings_layout)

    # 狀態
    self.single_burst_status_label = QLabel("💤 等待連發指令...")
    burst_layout.addWidget(self.single_burst_status_label)

    # 控制按鈕（用 lambda 傳 self）
    single_burst_control_layout = QHBoxLayout()
    self.single_start_burst_btn = QPushButton("🚀 開始連發")
    self.single_start_burst_btn.clicked.connect(lambda: start_burst_mode_single(self))
    self.single_stop_burst_btn = QPushButton("⏹️ 停止連發")
    self.single_stop_burst_btn.clicked.connect(lambda: stop_burst_mode_single(self))
    self.single_stop_burst_btn.setEnabled(False)
    single_burst_control_layout.addWidget(self.single_start_burst_btn)
    single_burst_control_layout.addWidget(self.single_stop_burst_btn)
    single_burst_control_layout.addStretch()
    burst_layout.addLayout(single_burst_control_layout)

    # 提示
    burst_info = QLabel("💡 單機連發：選擇位置後設定球數和間隔，點擊開始")
    burst_info.setStyleSheet("color: #ffcc00; font-size: 11px;")
    burst_info.setWordWrap(True)
    burst_layout.addWidget(burst_info)

    scroll_layout.addWidget(burst_group)

    # 區域按鈕（以 handler lambda 傳 self）
    front_group = QGroupBox("🎯 FRONT ZONE • 前場精準區域 (sec1-sec5)")
    front_layout = QGridLayout(front_group)
    utils_create_area_buttons(self, front_layout, 1, 5, handler=lambda s: handle_shot_button_click_single(self, s))
    scroll_layout.addWidget(front_group)

    middle_group = QGroupBox("⚡ MID ZONE • 中場戰術區域 (sec6-sec15)")
    middle_layout = QGridLayout(middle_group)
    utils_create_area_buttons(self, middle_layout, 6, 15, handler=lambda s: handle_shot_button_click_single(self, s))
    scroll_layout.addWidget(middle_group)

    back_group = QGroupBox("🔥 BACK ZONE • 後場威力區域 (sec16-sec25)")
    back_layout = QGridLayout(back_group)
    utils_create_area_buttons(self, back_layout, 16, 25, handler=lambda s: handle_shot_button_click_single(self, s))
    scroll_layout.addWidget(back_group)

    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    layout.addWidget(scroll_area)

    # 變數
    self.single_burst_mode_active = False
    self.single_burst_task = None
    self.single_current_burst_section = None

    return manual_widget


def _create_dual_manual_tab(self) -> QWidget:
    """建立雙發球機手動控制子頁（沿用現有雙機與協調控制）"""
    manual_widget = QWidget()
    layout = QVBoxLayout(manual_widget)

    # 以下內容取自原先 create_manual_tab（含雙機控制）
    # 創建滾動區域
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)

    # 連發模式控制組 - AI風格（移到最上面）
    burst_group = QGroupBox("🚀 BURST MODE • 智能連發系統")
    burst_layout = QVBoxLayout(burst_group)

    # 模式選擇 + 雙機控制（沿用之前代碼，保留 dual_* 控件）
    mode_selection_layout = QHBoxLayout()
    mode_selection_layout.addWidget(QLabel("🎯 發球模式:"))

    self.shot_mode_group = QButtonGroup()
    self.single_mode_radio = QRadioButton("單發模式")
    self.burst_mode_radio = QRadioButton("連發模式")
    self.single_mode_radio.setChecked(True)
    self.shot_mode_group.addButton(self.single_mode_radio, 0)
    self.shot_mode_group.addButton(self.burst_mode_radio, 1)

    mode_selection_layout.addWidget(self.single_mode_radio)
    mode_selection_layout.addWidget(self.burst_mode_radio)

    # 雙機控制塊（已於先前新增）
    mode_selection_layout.addSpacing(20)
    mode_selection_layout.addWidget(QLabel("🧭 目標:"))
    self.dual_target_combo = QComboBox()
    self.dual_target_combo.addItems(["左發球機", "右發球機", "協調(雙機)"])
    mode_selection_layout.addWidget(self.dual_target_combo)

    mode_selection_layout.addStretch()
    burst_layout.addLayout(mode_selection_layout)

    # === 協調設定容器（放模式/間隔/次數） ===
    self.dual_coord_settings_container = QWidget()
    coord_container_layout = QVBoxLayout(self.dual_coord_settings_container)
    coord_container_layout.setContentsMargins(0, 0, 0, 0)
    coord_container_layout.setSpacing(8)

    # 第一行：模式選擇
    mode_row = QHBoxLayout()
    mode_row.addWidget(QLabel("🎯 協調模式:"))
    self.coordination_mode_combo = QComboBox()
    self.coordination_mode_combo.addItems(["alternate(交替)", "simultaneous(同時)"])
    self.coordination_mode_combo.setEnabled(False)
    self.coordination_mode_combo.setMinimumWidth(150)
    mode_row.addWidget(self.coordination_mode_combo)
    mode_row.addStretch()
    coord_container_layout.addLayout(mode_row)

    # 第二行：間隔和球數設定
    settings_row = QHBoxLayout()
    
    # 間隔設定
    interval_group = QHBoxLayout()
    interval_group.addWidget(QLabel("⏱️ 間隔:"))
    self.coordination_interval_spin = QDoubleSpinBox()
    self.coordination_interval_spin.setRange(0.0, 10.0)  # 0-10秒
    self.coordination_interval_spin.setValue(2.0)        # 預設2秒
    self.coordination_interval_spin.setSingleStep(0.1)   # 每次調整0.1秒
    self.coordination_interval_spin.setDecimals(1)       # 顯示1位小數
    self.coordination_interval_spin.setSuffix(" 秒")
    self.coordination_interval_spin.setEnabled(False)
    self.coordination_interval_spin.setMinimumWidth(100)
    interval_group.addWidget(self.coordination_interval_spin)
    settings_row.addLayout(interval_group)
    
    settings_row.addSpacing(20)
    
    # 球數設定
    count_group = QHBoxLayout()
    count_group.addWidget(QLabel("⚽ 球數:"))
    self.coordination_count_spin = QSpinBox()
    self.coordination_count_spin.setRange(1, 100)
    self.coordination_count_spin.setValue(5)
    self.coordination_count_spin.setEnabled(False)
    self.coordination_count_spin.setMinimumWidth(80)
    count_group.addWidget(self.coordination_count_spin)
    settings_row.addLayout(count_group)
    
    settings_row.addStretch()
    coord_container_layout.addLayout(settings_row)

    burst_layout.addWidget(self.dual_coord_settings_container)

    # 連發設定區域（沿用現有，作為單機左/右用）
    self.dual_standard_settings_container = QWidget()
    burst_settings_layout = QHBoxLayout(self.dual_standard_settings_container)
    burst_settings_layout.setContentsMargins(0, 0, 0, 0)

    ball_count_layout = QVBoxLayout()
    ball_count_layout.addWidget(QLabel("發球數量:"))
    self.ball_count_spinbox = QSpinBox()
    self.ball_count_spinbox.setRange(1, 50)
    self.ball_count_spinbox.setValue(5)
    ball_count_layout.addWidget(self.ball_count_spinbox)
    burst_settings_layout.addLayout(ball_count_layout)

    interval_layout = QVBoxLayout()
    interval_layout.addWidget(QLabel("發球間隔 (秒):"))
    self.interval_spinbox = QSpinBox()
    self.interval_spinbox.setRange(1, 10)
    self.interval_spinbox.setValue(2)
    self.interval_spinbox.setSuffix(" 秒")
    interval_layout.addWidget(self.interval_spinbox)
    burst_settings_layout.addLayout(interval_layout)

    burst_layout.addWidget(self.dual_standard_settings_container)

    def on_dual_target_changed():
        is_coord = self.dual_target_combo.currentIndex() == 2
        # 協調選項顯示，標準連發隱藏
        self.dual_coord_settings_container.setVisible(is_coord)
        self.coordination_mode_combo.setEnabled(is_coord)
        self.coordination_interval_spin.setEnabled(is_coord)
        self.coordination_count_spin.setEnabled(is_coord)
        
        # 顯示/隱藏協調模式說明
        if hasattr(self, 'coord_info_label'):
            self.coord_info_label.setVisible(is_coord)

        self.dual_standard_settings_container.setVisible(not is_coord)
    self.dual_target_combo.currentIndexChanged.connect(on_dual_target_changed)
    on_dual_target_changed()

    # 連發狀態顯示
    self.burst_status_label = QLabel("💤 等待連發指令...")
    burst_layout.addWidget(self.burst_status_label)

    # 連發控制按鈕
    burst_control_layout = QHBoxLayout()
    self.start_burst_btn = QPushButton("🚀 開始連發")
    self.start_burst_btn.clicked.connect(self.start_burst_mode)
    self.stop_burst_btn = QPushButton("⏹️ 停止連發")
    self.stop_burst_btn.clicked.connect(self.stop_burst_mode)
    self.stop_burst_btn.setEnabled(False)
    burst_control_layout.addWidget(self.start_burst_btn)
    burst_control_layout.addWidget(self.stop_burst_btn)
    burst_control_layout.addStretch()
    burst_layout.addLayout(burst_control_layout)

    # 協調模式說明
    coord_info = QLabel("💡 協調模式說明：交替=總球數，同時=每台發球數")
    coord_info.setStyleSheet("color: #4ecdc4; font-size: 11px; font-weight: bold;")
    coord_info.setWordWrap(True)
    coord_info.setVisible(False)  # 預設隱藏，只在協調模式時顯示
    self.coord_info_label = coord_info
    burst_layout.addWidget(coord_info)
    
    burst_info = QLabel("💡 雙機連發：可選左/右/協調與模式參數")
    burst_info.setStyleSheet("color: #ffcc00; font-size: 11px;")
    burst_info.setWordWrap(True)
    burst_layout.addWidget(burst_info)

    scroll_layout.addWidget(burst_group)

    # 區域按鈕（沿用現有，使用雙機處理器）
    front_group = QGroupBox("🎯 FRONT ZONE • 前場精準區域 (sec1-sec5)")
    front_layout = QGridLayout(front_group)
    utils_create_area_buttons(self, front_layout, 1, 5, handler=lambda s: handle_shot_button_click(self, s))
    scroll_layout.addWidget(front_group)

    middle_group = QGroupBox("⚡ MID ZONE • 中場戰術區域 (sec6-sec15)")
    middle_layout = QGridLayout(middle_group)
    utils_create_area_buttons(self, middle_layout, 6, 15, handler=lambda s: handle_shot_button_click(self, s))
    scroll_layout.addWidget(middle_group)

    back_group = QGroupBox("🔥 BACK ZONE • 後場威力區域 (sec16-sec25)")
    back_layout = QGridLayout(back_group)
    utils_create_area_buttons(self, back_layout, 16, 25, handler=lambda s: handle_shot_button_click(self, s))
    scroll_layout.addWidget(back_group)

    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    layout.addWidget(scroll_area)

    # 初始化連發模式相關變數
    self.burst_mode_active = False
    self.burst_task = None
    self.current_burst_section = None

    return manual_widget


def handle_shot_button_click(self, section):
    """處理發球按鈕點擊事件，根據模式決定單發或連發（修復版本）"""
    self.log_message(f"🔍 雙發球機手動控制 - 按鈕點擊: {section}")
    
    if hasattr(self, 'burst_mode_radio') and self.burst_mode_radio.isChecked():
        # 連發模式：設定目標位置並準備連發
        self.current_burst_section = section
        self.update_burst_status(f"🎯 已選擇位置: {section}，準備連發")
        self.log_message(f"連發模式：已選擇位置 {section}，請設定球數和間隔後開始連發")
    else:
        # 單發模式：直接發球
        self.log_message(f"🔍 雙發球機手動控制 - 單發模式，準備發送: {section}")
        try:
            self.log_message(f"🔍 準備調用 send_single_shot: {section}")
            # 創建異步任務來調用 send_single_shot
            self.create_async_task(send_single_shot(self, section))
            self.log_message(f"🔍 send_single_shot 調用完成: {section}")
        except Exception as e:
            self.log_message(f"❌ send_single_shot 調用失敗: {e}")
            import traceback
            traceback.print_exc()


def start_burst_mode(self):
    """開始連發模式（修復版本）"""
    if not self.current_burst_section:
        self.log_message("請先選擇發球位置")
        return
    
    # 檢查連接狀態（支持雙發球機）
    is_connected = False
    
    # 檢查雙發球機連接狀態
    if hasattr(self, 'dual_bluetooth_manager') and self.dual_bluetooth_manager:
        dual_connected = self.dual_bluetooth_manager.is_dual_connected()
        self.log_message(f"🔍 雙發球機連接狀態: {dual_connected}")
        if dual_connected:
            is_connected = True
        else:
            # 檢查個別機器狀態
            left_status = "未設置"
            right_status = "未設置"
            if hasattr(self.dual_bluetooth_manager, 'left_machine') and self.dual_bluetooth_manager.left_machine:
                left_status = f"已連接: {self.dual_bluetooth_manager.left_machine.is_connected}"
            if hasattr(self.dual_bluetooth_manager, 'right_machine') and self.dual_bluetooth_manager.right_machine:
                right_status = f"已連接: {self.dual_bluetooth_manager.right_machine.is_connected}"
            self.log_message(f"🔍 左發球機狀態: {left_status}")
            self.log_message(f"🔍 右發球機狀態: {right_status}")
    
    # 檢查單發球機連接狀態
    if not is_connected:
        if hasattr(self, 'device_service'):
            if not self.device_service:
                self.device_service = DeviceService(self, simulate=False)
            single_connected = self.device_service.is_connected()
            self.log_message(f"🔍 單發球機連接狀態: {single_connected}")
            is_connected = single_connected
        else:
            self.device_service = DeviceService(self, simulate=False)
            single_connected = self.device_service.is_connected()
            self.log_message(f"🔍 單發球機連接狀態: {single_connected}")
            is_connected = single_connected
    
    if not is_connected:
        self.log_message("請先連接發球機")
        return
    
    ball_count = self.ball_count_spinbox.value()
    interval = self.interval_spinbox.value()
    
    self.burst_mode_active = True
    self.start_burst_btn.setEnabled(False)
    self.stop_burst_btn.setEnabled(True)
    
    self.update_burst_status(f"🚀 連發中：{self.current_burst_section} ({ball_count}球，間隔{interval}秒)")
    self.log_message(f"開始連發：{self.current_burst_section}，{ball_count}球，間隔{interval}秒")
    
    # 創建連發任務
    self.burst_task = self.create_async_task(self.execute_burst_sequence())


def stop_burst_mode(self):
    """停止連發模式"""
    self.burst_mode_active = False
    
    if self.burst_task and not self.burst_task.done():
        self.burst_task.cancel()
    
    self.start_burst_btn.setEnabled(True)
    self.stop_burst_btn.setEnabled(False)
    
    self.update_burst_status("⏹️ 連發已停止")
    self.log_message("連發模式已停止")


async def execute_burst_sequence(self):
    """執行連發序列"""
    try:
        ball_count = self.ball_count_spinbox.value()
        interval = self.interval_spinbox.value()
        section = self.current_burst_section
        
        # 根據目標決定發送策略
        target_idx = self.dual_target_combo.currentIndex() if hasattr(self, 'dual_target_combo') else 0
        is_coord = target_idx == 2
        
        if is_coord and hasattr(self, 'dual_bluetooth_manager') and self.dual_bluetooth_manager:
            # 使用協調器處理連發，使用協調設定的球數和間隔
            mode_map = {0: "alternate", 1: "simultaneous"}
            coord_mode = mode_map.get(self.coordination_mode_combo.currentIndex() if hasattr(self, 'coordination_mode_combo') else 0, "alternate")
            coord_interval = float(self.coordination_interval_spin.value()) if hasattr(self, 'coordination_interval_spin') else float(interval)
            coord_count = int(self.coordination_count_spin.value()) if hasattr(self, 'coordination_count_spin') else ball_count
            # 左右同一區域；若未來需要左右不同，可延伸 UI
            success = await self.dual_bluetooth_manager.send_coordinated_shot(
                section, section, coordination_mode=coord_mode, interval=coord_interval, count=coord_count
            )
            if not success:
                self.log_message("協調連發失敗")
            else:
                self.log_message(f"協調連發完成：{coord_mode} x{coord_count}")
        else:
            # 單機（左或右或單機模式）逐球送出
            for i in range(ball_count):
                if not self.burst_mode_active:
                    break
                
                # 發送單球（路由）
                await _send_single_routed(self, section)
                
                # 更新狀態
                remaining = ball_count - i - 1
                self.update_burst_status(f"🚀 連發中：{section} ({i+1}/{ball_count}，剩餘{remaining}球)")
                self.log_message(f"連發進度：{section} 第{i+1}球")
                
                # 如果不是最後一球，等待間隔時間
                if i < ball_count - 1 and self.burst_mode_active:
                    await asyncio.sleep(interval)
        
        if self.burst_mode_active:
            self.update_burst_status("✅ 連發完成")
            self.log_message(f"連發完成：{section}，共發送{ball_count}球")
        
    except asyncio.CancelledError:
        self.log_message("連發被取消")
    except Exception as e:
        self.log_message(f"連發過程中發生錯誤：{e}")
    finally:
        # 重置狀態
        self.burst_mode_active = False
        self.start_burst_btn.setEnabled(True)
        self.stop_burst_btn.setEnabled(False)
        if not self.burst_mode_active:
            self.update_burst_status("💤 等待連發指令...")


def update_burst_status(self, status):
    """更新連發狀態顯示"""
    if hasattr(self, 'burst_status_label'):
        self.burst_status_label.setText(status)
        
        # 根據狀態更新顏色
        if "連發中" in status:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #ff3366;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(255, 51, 102, 0.1);
                    border: 1px solid #ff3366;
                    border-radius: 5px;
                }
            """)
        elif "完成" in status:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #51cf66;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(81, 207, 102, 0.1);
                    border: 1px solid #51cf66;
                    border-radius: 5px;
                }
            """)
        elif "停止" in status:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(255, 107, 107, 0.1);
                    border: 1px solid #ff6b6b;
                    border-radius: 5px;
                }
            """)
        else:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #4ecdc4;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(78, 205, 196, 0.1);
                    border: 1px solid #4ecdc4;
                    border-radius: 5px;
                }
            """)


def log_message(self, message):
    """記錄訊息到日誌"""
    if hasattr(self, 'log_message'):
        self.log_message(message)
    else:
        print(f"[手動控制] {message}")

async def send_single_shot(self, section):
    """發送單球（修復版本）"""
    self.log_message(f"🔍 send_single_shot 被調用: {section}")
    # 若為協調模式則使用協調發送，否則根據目標路由到左/右或單機
    try:
        await _send_single_routed(self, section)
    except Exception as e:
        self.log_message(f"發送失敗：{e}")
        import traceback
        traceback.print_exc()


async def _send_single_routed(self, section: str):
    """根據目標（左/右/協調）路由單球發送（修復版本）"""
    self.log_message(f"🔍 _send_single_routed 被調用: {section}")
    # 目標索引：0 左，1 右，2 協調
    target_idx = self.dual_target_combo.currentIndex() if hasattr(self, 'dual_target_combo') else 0
    self.log_message(f"🔍 目標索引: {target_idx}")
    
    # 協調模式
    if target_idx == 2:
        if not hasattr(self, 'dual_bluetooth_manager') or not self.dual_bluetooth_manager:
            self.log_message("請先連接雙發球機")
            return
        if not self.dual_bluetooth_manager.is_dual_connected():
            self.log_message("雙發球機未完全連接")
            return
        mode_map = {0: "alternate", 1: "simultaneous"}
        coord_mode = mode_map.get(self.coordination_mode_combo.currentIndex() if hasattr(self, 'coordination_mode_combo') else 0, "alternate")
        coord_interval = float(self.coordination_interval_spin.value()) if hasattr(self, 'coordination_interval_spin') else 0.0
        await self.dual_bluetooth_manager.send_coordinated_shot(section, section, coordination_mode=coord_mode, interval=coord_interval, count=1)
        return
    
    # 左/右模式：檢查目標發球機連接狀態
    if target_idx in [0, 1]:  # 左發球機或右發球機
        if not hasattr(self, 'dual_bluetooth_manager') or not self.dual_bluetooth_manager:
            self.log_message("請先連接雙發球機")
            return
        
        # 檢查目標發球機是否連接
        machine_type = "left" if target_idx == 0 else "right"
        thread = self.dual_bluetooth_manager.get_machine_thread(machine_type)
        
        if not thread:
            self.log_message(f"{machine_type}發球機線程未找到")
            return
            
        if not thread.is_connected:
            self.log_message(f"{machine_type}發球機未連接")
            return
        
        # 發送單球到目標發球機
        self.log_message(f"🎯 發送單球到{machine_type}發球機: {section}")
        await thread.send_shot(section)
        return
    
    # 單機模式 → 使用 DeviceService
    if not hasattr(self, 'device_service'):
        self.device_service = DeviceService(self, simulate=False)
    if not self.device_service.is_connected():
        self.log_message("請先連接發球機")
        return
    await self.device_service.send_shot(section)
        
def handle_shot_button_click_single(self, section):
    """單機子頁：處理發球按鈕點擊事件"""
    if hasattr(self, 'single_burst_mode_radio') and self.single_burst_mode_radio.isChecked():
        self.single_current_burst_section = section
        update_burst_status_single(self, f"🎯 已選擇位置: {section}，準備連發")
        self.log_message(f"單機連發：已選擇位置 {section}，請設定球數和間隔後開始連發")
    else:
        send_single_shot_single(self, section)


@asyncSlot()
async def send_single_shot_single(self, section):
    """單機子頁：發送單球（使用單機 bluetooth_thread）"""
    if not hasattr(self, 'device_service'):
        self.device_service = DeviceService(self, simulate=False)
    if not self.device_service.is_connected():
        self.log_message("請先連接發球機")
        return
    await self.device_service.send_shot(section)


def start_burst_mode_single(self):
    """單機子頁：開始連發"""
    if not self.single_current_burst_section:
        self.log_message("請先選擇發球位置")
        return
    if not hasattr(self, 'device_service'):
        self.device_service = DeviceService(self, simulate=False)
    if not self.device_service.is_connected():
        self.log_message("請先連接發球機")
        return

    ball_count = self.single_ball_count_spinbox.value()
    interval = self.single_interval_spinbox.value()

    self.single_burst_mode_active = True
    self.single_start_burst_btn.setEnabled(False)
    self.single_stop_burst_btn.setEnabled(True)

    update_burst_status_single(self, f"🚀 連發中：{self.single_current_burst_section} ({ball_count}球，間隔{interval}秒)")
    self.log_message(f"單機開始連發：{self.single_current_burst_section}，{ball_count}球，間隔{interval}秒")

    self.single_burst_task = self.create_async_task(execute_burst_sequence_single(self))


def stop_burst_mode_single(self):
    """單機子頁：停止連發"""
    self.single_burst_mode_active = False
    if self.single_burst_task and not self.single_burst_task.done():
        self.single_burst_task.cancel()
    self.single_start_burst_btn.setEnabled(True)
    self.single_stop_burst_btn.setEnabled(False)
    update_burst_status_single(self, "⏹️ 連發已停止")
    self.log_message("單機連發模式已停止")


async def execute_burst_sequence_single(self):
    """單機子頁：執行連發序列"""
    try:
        ball_count = self.single_ball_count_spinbox.value()
        interval = self.single_interval_spinbox.value()
        section = self.single_current_burst_section

        for i in range(ball_count):
            if not self.single_burst_mode_active:
                break
            await self.bluetooth_thread.send_shot(section)
            remaining = ball_count - i - 1
            update_burst_status_single(self, f"🚀 連發中：{section} ({i+1}/{ball_count}，剩餘{remaining}球)")
            self.log_message(f"單機連發進度：{section} 第{i+1}球")
            if i < ball_count - 1 and self.single_burst_mode_active:
                await asyncio.sleep(interval)
        if self.single_burst_mode_active:
            update_burst_status_single(self, "✅ 連發完成")
            self.log_message(f"單機連發完成：{section}，共發送{ball_count}球")
    except asyncio.CancelledError:
        self.log_message("單機連發被取消")
    except Exception as e:
        self.log_message(f"單機連發過程中發生錯誤：{e}")
    finally:
        self.single_burst_mode_active = False
        self.single_start_burst_btn.setEnabled(True)
        self.single_stop_burst_btn.setEnabled(False)
        if not self.single_burst_mode_active:
            update_burst_status_single(self, "💤 等待連發指令...")


def update_burst_status_single(self, status: str):
    if hasattr(self, 'single_burst_status_label'):
        self.single_burst_status_label.setText(status)
        
        # 根據狀態更新顏色
        if "連發中" in status:
            self.single_burst_status_label.setStyleSheet("""
                QLabel {
                    color: #ff3366;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(255, 51, 102, 0.1);
                    border: 1px solid #ff3366;
                    border-radius: 5px;
                }
            """)
        elif "完成" in status:
            self.single_burst_status_label.setStyleSheet("""
                QLabel {
                    color: #51cf66;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(81, 207, 102, 0.1);
                    border: 1px solid #51cf66;
                    border-radius: 5px;
                }
            """)
        elif "停止" in status:
            self.single_burst_status_label.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(255, 107, 107, 0.1);
                    border: 1px solid #ff6b6b;
                    border-radius: 5px;
                }
            """)
        else:
            self.single_burst_status_label.setStyleSheet("""
                QLabel {
                    color: #4ecdc4;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(78, 205, 196, 0.1);
                    border: 1px solid #4ecdc4;
                    border-radius: 5px;
                }
            """)
        
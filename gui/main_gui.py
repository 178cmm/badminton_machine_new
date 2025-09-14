import sys
import asyncio
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QPushButton, QComboBox, QGroupBox, QTabWidget)
from PyQt5.QtCore import Qt
import qasync
from qasync import QEventLoop

import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bluetooth import BluetoothThread
from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params
from voice_control import VoiceControl

# bring UI functions and attach to class after definition
from . import ui_connection as _ui_connection
from . import ui_training as _ui_training
from . import ui_text_input as _ui_text_input
from . import ui_log as _ui_log
from . import ui_utils as _ui_utils
from . import ui_course as _ui_course
from . import ui_control as _ui_control
from . import ui_warmup as _ui_warmup
from . import ui_advanced_training as _ui_adv
from . import ui_voice as _ui_voice
from . import ui_simulation as _ui_simulation

class BadmintonLauncherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化藍牙執行緒和事件循環
        self.bluetooth_thread = None
        self.loop = None
        # 語音控制
        self.voice_control = None
        # 訓練任務和停止旗標
        self.training_task = None  # 用於停止訓練
        self.stop_flag = False  # 用於停止發球
        # 初始化使用者介面
        self.init_ui()
        # 載入訓練程式
        self.load_programs()

    def init_ui(self):
        """初始化使用者介面"""
        # 設定視窗標題和大小
        self.setWindowTitle("🤖 AI 羽毛球發球機控制系統 v2.0")
        # 設定最小尺寸並使用螢幕尺寸的80%作為初始大小
        from PyQt5.QtWidgets import QDesktopWidget
        from PyQt5.QtCore import Qt
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        width = int(screen_rect.width() * 0.8)
        height = int(screen_rect.height() * 0.8)
        self.setGeometry(100, 100, min(1200, width), min(800, height))
        self.setMinimumSize(800, 600)  # 設定最小尺寸
        
        # 設定視窗圖示和屬性
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 設定柔和AI科技感主題樣式
        self.setStyleSheet("""
            /* 主視窗背景 - 柔和深藍漸層 */
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1d2e, stop:0.3 #2a2d3e, stop:0.7 #3a3d4e, stop:1 #2a2d3e);
                color: #d0d6e5;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            
            /* 通用Widget樣式 */
            QWidget {
                background-color: transparent;
                color: #c0c6d5;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            
            /* GroupBox - 柔和科技感邊框 */
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                border: 1px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a7c8a, stop:0.5 #5a8c9a, stop:1 #4a7c8a);
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 16px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(74, 124, 138, 0.08), stop:1 rgba(90, 140, 154, 0.04));
                color: #e0e6f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 4px 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a8c9a, stop:1 #4a7c8a);
                color: #ffffff;
                border-radius: 6px;
                font-weight: bold;
            }
            
            /* 按鈕 - 柔和科技效果 */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a8c9a, stop:0.5 #4a7c8a, stop:1 #3a6c7a);
                color: #ffffff;
                border: 1px solid #5a8c9a;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                min-height: 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a9caa, stop:0.5 #5a8c9a, stop:1 #4a7c8a);
                border: 1px solid #6a9caa;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a6c7a, stop:0.5 #2a5c6a, stop:1 #1a4c5a);
                border: 1px solid #4a7c8a;
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #555555, stop:1 #333333);
                color: #777777;
                border: 1px solid #555555;
            }
            
            /* 下拉選單 - 柔和設計 */
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #5a8c9a;
                border-radius: 6px;
                font-size: 13px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(90, 140, 154, 0.1), stop:1 rgba(74, 124, 138, 0.05));
                color: #ffffff;
                min-height: 18px;
            }
            QComboBox:hover {
                border: 1px solid #6a9caa;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #5a8c9a;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2d3e, stop:1 #1a1d2e);
                color: #ffffff;
                border: 1px solid #5a8c9a;
                border-radius: 6px;
                selection-background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a8c9a, stop:1 #4a7c8a);
                selection-color: #ffffff;
                padding: 4px;
            }
            
            /* 文字編輯區 - 柔和終端機風格 */
            QTextEdit {
                border: 1px solid #5a8c9a;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 0, 0, 0.6), stop:1 rgba(90, 140, 154, 0.05));
                color: #7fb069;
                selection-background-color: #5a8c9a;
                selection-color: #ffffff;
            }
            QTextEdit:focus {
                border: 1px solid #6a9caa;
            }
            
            /* 輸入框 */
            QLineEdit {
                border: 1px solid #5a8c9a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(90, 140, 154, 0.1), stop:1 rgba(74, 124, 138, 0.05));
                color: #ffffff;
                min-height: 18px;
            }
            QLineEdit:focus {
                border: 1px solid #6a9caa;
            }
            
            /* 標籤 */
            QLabel {
                color: #c0c6d5;
                font-weight: 500;
            }
            
            /* 標籤頁 - 柔和標籤 */
            QTabWidget::pane {
                border: 1px solid #5a8c9a;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(90, 140, 154, 0.05), stop:1 rgba(74, 124, 138, 0.02));
                margin-top: 6px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(90, 140, 154, 0.15), stop:1 rgba(74, 124, 138, 0.08));
                color: #c0c6d5;
                padding: 6px 8px;
                margin-right: 1px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #5a8c9a;
                border-bottom: none;
                font-weight: 500;
                max-width: 80px;
                min-width: 50px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a8c9a, stop:1 #4a7c8a);
                color: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(90, 140, 154, 0.25), stop:1 rgba(74, 124, 138, 0.15));
            }
            
            /* 進度條 - 柔和能量條效果 */
            QProgressBar {
                border: 1px solid #5a8c9a;
                border-radius: 6px;
                text-align: center;
                background: rgba(0, 0, 0, 0.3);
                color: #ffffff;
                font-weight: bold;
                min-height: 18px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7fb069, stop:0.5 #5a8c9a, stop:1 #4a7c8a);
                border-radius: 4px;
                margin: 1px;
            }
            
            /* 滾動條 - 柔和滾動條 */
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.2);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a8c9a, stop:1 #4a7c8a);
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a9caa, stop:1 #5a8c9a);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            /* 核取方塊 */
            QCheckBox {
                color: #c0c6d5;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #5a8c9a;
                border-radius: 3px;
                background: rgba(90, 140, 154, 0.1);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5a8c9a, stop:1 #4a7c8a);
            }
            QCheckBox::indicator:checked:after {
                content: "✓";
                color: #ffffff;
                font-weight: bold;
            }
            
            /* 數值選擇器 */
            QSpinBox {
                border: 1px solid #5a8c9a;
                border-radius: 6px;
                padding: 6px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(90, 140, 154, 0.1), stop:1 rgba(74, 124, 138, 0.05));
                color: #ffffff;
                font-size: 13px;
            }
            QSpinBox:hover {
                border: 1px solid #6a9caa;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a8c9a, stop:1 #4a7c8a);
                border: none;
                border-radius: 3px;
                width: 18px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a9caa, stop:1 #5a8c9a);
            }
        """)

        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 創建主佈局
        main_layout = QVBoxLayout(central_widget)

        # 創建柔和AI科技感標題
        title_label = QLabel("🤖 AI BADMINTON LAUNCHER CONTROL SYSTEM v2.0")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            margin: 12px;
            padding: 16px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(90, 140, 154, 0.2), stop:0.5 rgba(74, 124, 138, 0.15), stop:1 rgba(90, 140, 154, 0.2));
            border-radius: 12px;
            border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #5a8c9a, stop:0.5 #4a7c8a, stop:1 #5a8c9a);
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            letter-spacing: 1px;
        """)
        main_layout.addWidget(title_label)

        # 創建標籤頁
        self.tab_widget = QTabWidget()
        # 設定標籤頁為可滾動，防止溢出
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(False)
        self.tab_widget.setUsesScrollButtons(True)  # 當標籤過多時顯示滾動按鈕
        main_layout.addWidget(self.tab_widget)

        # 創建各個標籤頁（調整順序）
        # 由左至右：連線設定 熱身 基礎訓練 進階訓練 模擬對打 手動控制 課程訓練 文本輸入控制 系統日誌
        self.create_connection_tab()
        self.create_warmup_tab()
        self.create_basic_training_tab()
        self.create_advanced_training_tab()
        self.create_simulation_tab()  # 模擬對打模式
        self.create_manual_tab()
        self.create_training_tab()
        self.create_text_input_tab()  # 文本輸入控制
        self.create_voice_tab()  # 語音控制
        self.create_log_tab()

        # 創建柔和AI風格狀態欄
        self.status_label = QLabel("🔴 SYSTEM STATUS: DISCONNECTED")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            padding: 10px 16px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(180, 80, 80, 0.6), stop:0.5 rgba(150, 60, 60, 0.4), stop:1 rgba(180, 80, 80, 0.6));
            color: #ffffff;
            border-radius: 8px;
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #b45050;
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            letter-spacing: 1px;
        """)
        main_layout.addWidget(self.status_label)

    def on_shot_sent(self, message):
        """發球發送回調"""
        # 記錄發球訊息
        self.log_message(message)

    def on_error(self, message):
        """錯誤處理"""
        # 記錄錯誤訊息
        self.log_message(f"錯誤: {message}")
    
    def update_connection_status(self, is_connected, message=""):
        """更新柔和AI風格連接狀態"""
        if is_connected:
            self.status_label.setText("🟢 SYSTEM STATUS: CONNECTED & READY")
            self.status_label.setStyleSheet("""
                padding: 10px 16px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(120, 180, 120, 0.6), stop:0.5 rgba(100, 150, 100, 0.4), stop:1 rgba(120, 180, 120, 0.6));
                color: #ffffff;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #78b478;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                letter-spacing: 1px;
            """)
        else:
            self.status_label.setText("🔴 SYSTEM STATUS: DISCONNECTED")
            self.status_label.setStyleSheet("""
                padding: 10px 16px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(180, 80, 80, 0.6), stop:0.5 rgba(150, 60, 60, 0.4), stop:1 rgba(180, 80, 80, 0.6));
                color: #ffffff;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #b45050;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                letter-spacing: 1px;
            """)
        
        if message:
            self.log_message(message)

    def closeEvent(self, event):
        """視窗關閉事件"""
        # 取消未完成的訓練任務
        if self.training_task and not self.training_task.done():
            self.training_task.cancel()

        # 如果藍牙已連接，則斷開連接
        if self.bluetooth_thread and self.bluetooth_thread.is_connected:
            asyncio.create_task(self.bluetooth_thread.disconnect())

        # 停止語音控制
        try:
            if hasattr(self, 'stop_voice_control'):
                asyncio.create_task(self.stop_voice_control())
        except Exception:
            pass

        event.accept()

    async def start_voice_control(self, model_path: str = "models/vosk-model-small-cn-0.22"):
        """啟動語音控制（非阻塞）。"""
        if self.voice_control is None:
            import os
            # 支援環境變數覆蓋
            env_path = os.getenv("VOSK_MODEL_PATH")
            final_path = env_path or model_path or "models/vosk-model-small-cn-0.22"
            self.voice_control = VoiceControl(self, model_path=final_path)
        await self.voice_control.start()

    async def stop_voice_control(self):
        """停止語音控制並釋放資源。"""
        if self.voice_control is not None:
            await self.voice_control.stop()

# 將 UI 函數從其他模組附加到 BadmintonLauncherGUI 類別
BadmintonLauncherGUI.create_connection_tab = getattr(_ui_connection, 'create_connection_tab')
BadmintonLauncherGUI.scan_devices = getattr(_ui_connection, 'scan_devices')
BadmintonLauncherGUI.on_device_found = getattr(_ui_connection, 'on_device_found')
BadmintonLauncherGUI.connect_device = getattr(_ui_connection, 'connect_device')
BadmintonLauncherGUI.on_connection_status = getattr(_ui_connection, 'on_connection_status')
BadmintonLauncherGUI.disconnect_device = getattr(_ui_connection, 'disconnect_device')
BadmintonLauncherGUI.create_training_tab = getattr(_ui_course, 'create_training_tab')
BadmintonLauncherGUI.create_basic_training_tab = getattr(_ui_training, 'create_basic_training_tab')
BadmintonLauncherGUI.select_basic_training = getattr(_ui_training, 'select_basic_training')
BadmintonLauncherGUI.start_selected_training = getattr(_ui_training, 'start_selected_training')
BadmintonLauncherGUI.create_manual_tab = getattr(_ui_control, 'create_manual_tab')
BadmintonLauncherGUI.execute_training_command = getattr(_ui_course, 'execute_training_command')
BadmintonLauncherGUI.practice_specific_shot = getattr(_ui_training, 'practice_specific_shot')
BadmintonLauncherGUI.practice_level_programs = getattr(_ui_training, 'practice_level_programs')
BadmintonLauncherGUI.get_section_by_shot_name = getattr(_ui_training, 'get_section_by_shot_name')
BadmintonLauncherGUI.send_shot_command = getattr(_ui_training, 'send_shot_command')
BadmintonLauncherGUI.create_area_buttons = getattr(_ui_training, 'create_area_buttons')
BadmintonLauncherGUI.create_shot_buttons = getattr(_ui_training, 'create_shot_buttons')
BadmintonLauncherGUI.send_single_shot = getattr(_ui_training, 'send_single_shot')
BadmintonLauncherGUI.start_training = getattr(_ui_training, 'start_training')
BadmintonLauncherGUI.execute_training = getattr(_ui_training, 'execute_training')
BadmintonLauncherGUI.stop_training = getattr(_ui_training, 'stop_training')
BadmintonLauncherGUI.create_text_input_tab = getattr(_ui_text_input, 'create_text_input_tab')
BadmintonLauncherGUI.create_voice_tab = getattr(_ui_voice, 'create_voice_tab')
BadmintonLauncherGUI.execute_text_command = getattr(_ui_text_input, 'execute_text_command')
BadmintonLauncherGUI.create_log_tab = getattr(_ui_log, 'create_log_tab')
BadmintonLauncherGUI.log_message = getattr(_ui_log, 'log_message')
BadmintonLauncherGUI.load_programs = getattr(_ui_utils, 'load_programs')
BadmintonLauncherGUI.update_program_list = getattr(_ui_utils, 'update_program_list')
BadmintonLauncherGUI.update_program_description = getattr(_ui_utils, 'update_program_description')
BadmintonLauncherGUI.on_scan_button_clicked = getattr(_ui_connection, 'on_scan_button_clicked')
BadmintonLauncherGUI.on_connect_button_clicked = getattr(_ui_connection, 'on_connect_button_clicked')
BadmintonLauncherGUI.on_disconnect_button_clicked = getattr(_ui_connection, 'on_disconnect_button_clicked')
BadmintonLauncherGUI.on_start_training_button_clicked = getattr(_ui_training, 'on_start_training_button_clicked')
BadmintonLauncherGUI.create_warmup_tab = getattr(_ui_warmup, 'create_warmup_tab')
BadmintonLauncherGUI.start_warmup = getattr(_ui_warmup, 'start_warmup')
BadmintonLauncherGUI.update_warmup_description = getattr(_ui_warmup, 'update_warmup_description')
BadmintonLauncherGUI.create_advanced_training_tab = getattr(_ui_adv, 'create_advanced_training_tab')
BadmintonLauncherGUI.start_advanced_training = getattr(_ui_adv, 'start_advanced_training')
BadmintonLauncherGUI.create_simulation_tab = getattr(_ui_simulation, 'create_simulation_tab')
BadmintonLauncherGUI.start_simulation_training = getattr(_ui_simulation, 'start_simulation_training')
BadmintonLauncherGUI.stop_simulation_training = getattr(_ui_simulation, 'stop_simulation_training')
BadmintonLauncherGUI.connect_simulation_events = getattr(_ui_simulation, 'connect_simulation_events')

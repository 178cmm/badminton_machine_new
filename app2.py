import sys
import asyncio
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QPushButton, QComboBox, QGroupBox, QTabWidget)
from PyQt5.QtCore import Qt
import qasync
from qasync import QEventLoop

from bluetooth import BluetoothThread
from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params
from voice_control import VoiceControl

# bring UI functions and attach to class after definition
import ui_connection as _ui_connection
import ui_training as _ui_training
import ui_text_input as _ui_text_input
import ui_log as _ui_log
import ui_utils as _ui_utils
import ui_course as _ui_course
import ui_control as _ui_control
import ui_warmup as _ui_warmup
import ui_advanced_training as _ui_adv
import ui_voice as _ui_voice

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
        self.setWindowTitle("羽毛球發球機控制系統")
        self.setGeometry(100, 100, 1000, 700)

        # 設定深色主題樣式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #555555;
                border-radius: 3px;
                font-size: 14px;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                selection-background-color: #4CAF50;
            }
            QTextEdit {
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
                font-family: 'Courier New';
                font-size: 12px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #555555;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 創建主佈局
        main_layout = QVBoxLayout(central_widget)

        # 創建標題
        title_label = QLabel("🏸 羽毛球發球機控制系統")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
            margin: 10px;
            padding: 10px;
            background-color: #3c3c3c;
            border-radius: 8px;
            border: 2px solid #4CAF50;
        """)
        main_layout.addWidget(title_label)

        # 創建標籤頁
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 創建各個標籤頁（調整順序）
        # 由左至右：連線設定 熱身 基礎訓練 進階訓練 手動控制 課程訓練 文本輸入控制 系統日誌
        self.create_connection_tab()
        self.create_warmup_tab()
        self.create_basic_training_tab()
        self.create_advanced_training_tab()
        self.create_manual_tab()
        self.create_training_tab()
        self.create_text_input_tab()  # 文本輸入控制
        self.create_voice_tab()  # 語音控制
        self.create_log_tab()

        # 創建狀態欄
        self.status_label = QLabel("未連接")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background-color: #ff4444;
            color: white;
            border-radius: 5px;
            font-weight: bold;
            border: 1px solid #cc0000;
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
BadmintonLauncherGUI.parse_command = getattr(_ui_text_input, 'parse_command')
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
BadmintonLauncherGUI._execute_warmup = getattr(_ui_warmup, '_execute_warmup')
BadmintonLauncherGUI.update_warmup_description = getattr(_ui_warmup, 'update_warmup_description')
BadmintonLauncherGUI.create_advanced_training_tab = getattr(_ui_adv, 'create_advanced_training_tab')
BadmintonLauncherGUI.start_advanced_training = getattr(_ui_adv, 'start_advanced_training')

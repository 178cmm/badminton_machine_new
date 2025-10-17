import sys
import asyncio
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QPushButton, QComboBox, QGroupBox, QTabWidget, QShortcut)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
import qasync
from qasync import QEventLoop

import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bluetooth import BluetoothThread
from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params, get_area_params
# 舊版語音控制已移除，僅使用 TTS 版本
VoiceControl = None
# 新的 TTS 語音控制系統
try:
    from scripts.voice_control_tts import VoiceControlTTS
    TTS_VOICE_AVAILABLE = True
except ImportError:
    TTS_VOICE_AVAILABLE = False

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
from . import ui_simulate_panel as _ui_simulate_panel
from . import ui_ai_coach as _ui_ai_coach
from . import ui_three_machine_simple as _ui_three_machine
from . import ui_custom_shot_control as _ui_custom_shot

class BadmintonLauncherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化藍牙執行緒和事件循環
        self.bluetooth_thread = None
        self.loop = None
        # 語音控制
        self.voice_control = None
        self.voice_control_tts = None  # 新的 TTS 語音控制
        # 訓練任務和停止旗標
        self.training_task = None  # 用於停止訓練
        self.stop_flag = False  # 用於停止發球
        # 初始化使用者介面
        self.init_ui()
        # 載入訓練程式
        self.load_programs()
        # 初始化系統服務
        self.init_system_service()
        # 設置事件循環引用
        import asyncio
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            # 如果沒有運行的事件循環，嘗試獲取當前事件循環
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = None
    
    def create_async_task(self, coro):
        """安全地創建異步任務"""
        import asyncio
        try:
            # 嘗試獲取當前運行的事件循環
            loop = asyncio.get_running_loop()
            return loop.create_task(coro)
        except RuntimeError:
            # 如果沒有運行的事件循環，嘗試使用主循環
            if hasattr(self, 'loop') and self.loop:
                try:
                    return self.loop.create_task(coro)
                except Exception as e:
                    self.log_message(f"❌ 創建異步任務失敗: {e}")
                    return None
            else:
                # 嘗試獲取當前事件循環
                try:
                    loop = asyncio.get_event_loop()
                    if loop and not loop.is_closed():
                        return loop.create_task(coro)
                except Exception:
                    pass
                
                # 嘗試創建新的事件循環（在線程中）
                try:
                    import threading
                    import queue
                    
                    result_queue = queue.Queue()
                    
                    def run_in_thread():
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result = new_loop.run_until_complete(coro)
                            result_queue.put(('success', result))
                        except Exception as e:
                            result_queue.put(('error', e))
                        finally:
                            new_loop.close()
                    
                    thread = threading.Thread(target=run_in_thread, daemon=True)
                    thread.start()
                    
                    # 返回一個假的任務對象，表示已開始執行
                    class FakeTask:
                        def __init__(self):
                            self.done = False
                            self.result = None
                            self.exception = None
                        
                        def add_done_callback(self, callback):
                            # 在後台檢查結果
                            def check_result():
                                if not result_queue.empty():
                                    status, result = result_queue.get()
                                    if status == 'success':
                                        self.result = result
                                    else:
                                        self.exception = result
                                    self.done = True
                                    callback(self)
                                else:
                                    # 繼續檢查
                                    threading.Timer(0.1, check_result).start()
                            check_result()
                    
                    return FakeTask()
                    
                except Exception as e:
                    self.log_message(f"⚠️ 創建後備異步任務失敗: {e}")
                    return None

    def init_ui(self):
        """初始化使用者介面"""
        from PyQt5.QtWidgets import QDesktopWidget
        from PyQt5.QtCore import Qt
        
        # 設定視窗標題和大小
        self.setWindowTitle("🤖 AI 羽毛球發球機控制系統 v2.0")
        
        # 設定視窗屬性以避免重繪問題
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        
        # 設定最小尺寸並使用螢幕尺寸的80%作為初始大小
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        width = int(screen_rect.width() * 0.8)
        height = int(screen_rect.height() * 0.8)
        self.setGeometry(100, 100, min(1200, width), min(800, height))
        self.setMinimumSize(800, 600)  # 設定最小尺寸
        
        # 設定視窗圖示和屬性
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 使用簡化的樣式表以避免分段錯誤
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1f2230;
                color: #c7cbd6;
            }
            QWidget {
                background-color: transparent;
                color: #b8becb;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #3d5560;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: rgba(45, 70, 80, 0.08);
                color: #d6dbe6;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 4px 12px;
                background-color: #3d5560;
                color: #ffffff;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3d5560;
                color: #ffffff;
                border: 1px solid #3d5560;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #466273;
                border: 1px solid #466273;
            }
            QPushButton:pressed {
                background-color: #2b3e49;
                border: 1px solid #36515c;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #777777;
                border: 1px solid #555555;
            }
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #3d5560;
                border-radius: 6px;
                font-size: 13px;
                background-color: rgba(45, 70, 80, 0.1);
                color: #ffffff;
                min-height: 18px;
            }
            QComboBox:hover {
                border: 1px solid #466273;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #3d5560;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #1f2230;
                color: #ffffff;
                border: 1px solid #3d5560;
                border-radius: 6px;
                selection-background-color: #3d5560;
                selection-color: #ffffff;
                padding: 4px;
            }
            QTextEdit {
                border: 1px solid #3d5560;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: rgba(0, 0, 0, 0.7);
                color: #d3d9e8;
                selection-background-color: #3d5560;
                selection-color: #ffffff;
            }
            QTextEdit:focus {
                border: 1px solid #466273;
            }
            QLineEdit {
                border: 1px solid #3d5560;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                background-color: rgba(45, 70, 80, 0.1);
                color: #ffffff;
                min-height: 18px;
            }
            QLineEdit:focus {
                border: 1px solid #466273;
            }
            QLabel {
                color: #b8becb;
                font-weight: 500;
            }
            QTabWidget::pane {
                border: 1px solid #3d5560;
                border-radius: 8px;
                background-color: rgba(45, 70, 80, 0.05);
                margin-top: 6px;
            }
            QTabBar::tab {
                background-color: rgba(45, 70, 80, 0.15);
                color: #b8becb;
                padding: 6px 8px;
                margin-right: 1px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #3d5560;
                border-bottom: none;
                font-weight: 500;
                max-width: 120px;
                min-width: 75px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #3d5560;
                color: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: rgba(45, 70, 80, 0.25);
            }
            QProgressBar {
                border: 1px solid #3d5560;
                border-radius: 6px;
                text-align: center;
                background-color: rgba(0, 0, 0, 0.3);
                color: #ffffff;
                font-weight: bold;
                min-height: 18px;
            }
            QProgressBar::chunk {
                background-color: #466273;
                border-radius: 4px;
                margin: 1px;
            }
            QScrollBar:vertical {
                background-color: rgba(0, 0, 0, 0.2);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d5560;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #466273;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QCheckBox {
                color: #b8becb;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3d5560;
                border-radius: 3px;
                background-color: rgba(45, 70, 80, 0.1);
            }
            QCheckBox::indicator:checked {
                background-color: #3d5560;
            }
            QSpinBox {
                border: 1px solid #3d5560;
                border-radius: 6px;
                padding: 6px;
                background-color: rgba(45, 70, 80, 0.1);
                color: #ffffff;
                font-size: 13px;
            }
            QSpinBox:hover {
                border: 1px solid #466273;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3d5560;
                border: none;
                border-radius: 3px;
                width: 18px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #466273;
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
            background-color: rgba(45, 70, 80, 0.12);
            border-radius: 12px;
            border: 2px solid #3d5560;
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
        # 由左至右：連線設定 熱身 基礎訓練 進階訓練 模擬對打 手動控制 課程訓練 三發球機 文本輸入控制 系統日誌
        self.create_connection_tab()
        self.create_warmup_tab()
        self.create_basic_training_tab()
        self.create_advanced_training_tab()
        self.create_simulation_tab()  # 模擬對打模式
        self.create_manual_tab()
        self.create_training_tab()
        self.create_three_machine_tab()  # 三發球機簡易控制
        self.create_custom_shot_tab()  # 自定義發球控制
        self.create_text_input_tab()  # 文本輸入控制
        self.create_voice_tab()  # 語音控制
        self.create_ai_coach_tab()  # AI 教練（文字對話）
        self.create_log_tab()
        
        # 在 simulate 模式下添加解析面板
        simulate_panel = self.create_simulate_panel()
        if simulate_panel:
            self.tab_widget.addTab(simulate_panel, "🔍 Simulate")

        # 創建柔和AI風格狀態欄
        self.status_label = QLabel("🔴 SYSTEM STATUS: DISCONNECTED")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            padding: 10px 16px;
            background-color: rgba(120, 60, 60, 0.5);
            color: #ffffff;
            border-radius: 8px;
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #7a3a3a;
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            letter-spacing: 1px;
        """)
        main_layout.addWidget(self.status_label)
        
        # 新增狀態燈（簡報筆遙控狀態顯示）- 已移除以節省空間
        # self.create_status_light(main_layout)
        
        # 初始化快捷鍵
        self.init_shortcuts()

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
                background-color: rgba(70, 120, 80, 0.55);
                color: #ffffff;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #4f7e55;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                letter-spacing: 1px;
            """)
        else:
            self.status_label.setText("🔴 SYSTEM STATUS: DISCONNECTED")
            self.status_label.setStyleSheet("""
                padding: 10px 16px;
                background-color: rgba(120, 60, 60, 0.5);
                color: #ffffff;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #7a3a3a;
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

        # 如果藍牙已連接，則斷開連接（簡化處理避免事件循環問題）
        if self.bluetooth_thread and self.bluetooth_thread.is_connected:
            try:
                # 直接設置為未連接狀態，避免複雜的異步處理
                self.bluetooth_thread.is_connected = False
                print("藍牙連接已標記為斷開")
            except Exception as e:
                print(f"藍牙斷開連接處理錯誤：{e}")

        # 停止語音控制（簡化版）
        try:
            # 停止 TTS 語音控制
            if hasattr(self, 'voice_control_tts') and self.voice_control_tts is not None:
                self.voice_control_tts._running = False
                self.voice_control_tts._starting = False
                self.voice_control_tts._listen_task = None
                self.voice_control_tts._capture_task = None
                self.voice_control_tts._audio_stream = None
                print("語音控制已停止")
            
            # 停止舊版語音控制
            if hasattr(self, 'voice_control') and self.voice_control is not None:
                self.voice_control._running = False
                self.voice_control._starting = False
                self.voice_control._listen_task = None
                self.voice_control._capture_task = None
                self.voice_control._audio_stream = None
                print("舊版語音控制已停止")
        except Exception as e:
            print(f"停止語音控制時發生錯誤：{e}")

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
        if self.voice_control_tts is not None:
            await self.voice_control_tts.stop()

    def init_system_service(self):
        """初始化系統服務"""
        from core.services.system_service import SystemService
        self.system_service = SystemService(self)
    
    def create_status_light(self, parent_layout):
        """創建狀態燈顯示"""
        self.status_light = QLabel("💤 待機")
        self.status_light.setAlignment(Qt.AlignCenter)
        self.status_light.setMinimumHeight(60)
        self.status_light.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 10px;
                border: 2px solid #3d5560;
                background-color: rgba(255, 193, 7, 0.2);
                color: #000000;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
        """)
        parent_layout.addWidget(self.status_light)
    
    def init_shortcuts(self):
        """初始化快捷鍵綁定"""
        # 空白鍵：開始/暫停切換
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.space_shortcut.activated.connect(self.toggle_start_pause)
        
        # Esc 鍵：急停
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.esc_shortcut.activated.connect(self.emergency_stop)
    
    def toggle_start_pause(self, source="keyboard"):
        """統一開始/暫停切換入口（智能版本）"""
        if not hasattr(self, 'system_service'):
            self.init_system_service()
        
        current_state = self.system_service.get_state()
        
        # 如果當前是 IDLE 狀態，先檢查是否有訓練目標
        if current_state.value == "IDLE":
            if not self._has_available_training_target():
                self.log_message("💡 請先選擇訓練目標：")
                self.log_message("   - 課程訓練：選擇套餐")
                self.log_message("   - 手動控制：選擇發球位置")
                self.log_message("   - 基礎訓練：選擇球路")
                return  # 不執行狀態切換
        
        # 執行狀態切換
        success = self.system_service.toggle()
        if success:
            new_state = self.system_service.get_state()
            self.update_status_light(new_state)
            self.log_event("TOGGLE_START_PAUSE", new_state.value, {"source": source})
            
            # 根據狀態執行相應的業務邏輯
            if new_state.value == "RUNNING":
                self._handle_start_training()
            elif new_state.value == "IDLE":
                self._handle_pause_training()
    
    def emergency_stop(self, source="keyboard"):
        """急停入口"""
        if not hasattr(self, 'system_service'):
            self.init_system_service()
        
        success = self.system_service.stop()
        if success:
            new_state = self.system_service.get_state()
            self.update_status_light(new_state)
            self.log_event("EMERGENCY_STOP", new_state.value, {"source": source})
            self._handle_emergency_stop()
    
    def update_status_light(self, state):
        """更新狀態燈顯示 - 已移除以節省空間"""
        # 狀態燈已被移除，此方法保留以保持向後相容性
        pass
    
    def log_event(self, event_type: str, state: str, extra: dict = None):
        """記錄事件到審計日誌"""
        import json
        import os
        from datetime import datetime
        
        # 確保 logs 目錄存在
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # 建立事件記錄
        event_data = {
            "event": event_type,
            "state": state,
            "timestamp": int(datetime.now().timestamp()),
            "source": extra.get("source", "unknown") if extra else "unknown",
            "extra": extra or {}
        }
        
        # 寫入 JSON Lines 格式
        log_file = os.path.join(logs_dir, "commands.jsonl")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_data, ensure_ascii=False) + "\n")
        except Exception as e:
            # 寫檔失敗不致命，記錄警告
            if hasattr(self, 'log_message'):
                self.log_message(f"⚠️ 事件記錄失敗: {e}")
            else:
                print(f"⚠️ 事件記錄失敗: {e}")
    
    def _handle_start_training(self):
        """處理開始訓練的業務邏輯（智能版本）"""
        current_tab = self.tab_widget.currentWidget()
        training_started = False
        
        # 1. 課程訓練
        if hasattr(current_tab, 'start_training'):
            try:
                current_tab.start_training()
                training_started = True
                self.log_message("🚀 開始課程訓練（簡報筆遙控）")
            except Exception as e:
                self.log_message(f"⚠️ 課程訓練啟動失敗: {e}")
        
        # 2. 手動控制連發（雙機）
        elif hasattr(current_tab, 'start_burst_mode') and hasattr(self, 'current_burst_section') and self.current_burst_section:
            try:
                current_tab.start_burst_mode()
                training_started = True
                self.log_message(f"🚀 開始連發訓練：{self.current_burst_section}（簡報筆遙控）")
            except Exception as e:
                self.log_message(f"⚠️ 連發訓練啟動失敗: {e}")
        
        # 3. 手動控制連發（單機）
        elif hasattr(current_tab, 'start_burst_mode_single') and hasattr(self, 'single_current_burst_section') and self.single_current_burst_section:
            try:
                current_tab.start_burst_mode_single()
                training_started = True
                self.log_message(f"🚀 開始單機連發訓練：{self.single_current_burst_section}（簡報筆遙控）")
            except Exception as e:
                self.log_message(f"⚠️ 單機連發訓練啟動失敗: {e}")
        
        # 4. 基礎訓練
        elif hasattr(current_tab, 'start_selected_training'):
            try:
                current_tab.start_selected_training()
                training_started = True
                self.log_message("🚀 開始基礎訓練（簡報筆遙控）")
            except Exception as e:
                self.log_message(f"⚠️ 基礎訓練啟動失敗: {e}")
        
        # 5. 進階訓練
        elif hasattr(current_tab, 'start_advanced_training'):
            try:
                current_tab.start_advanced_training()
                training_started = True
                self.log_message("🚀 開始進階訓練（簡報筆遙控）")
            except Exception as e:
                self.log_message(f"⚠️ 進階訓練啟動失敗: {e}")
        
        # 6. 模擬對打
        elif hasattr(current_tab, 'start_simulation_training'):
            try:
                current_tab.start_simulation_training()
                training_started = True
                self.log_message("🚀 開始模擬對打（簡報筆遙控）")
            except Exception as e:
                self.log_message(f"⚠️ 模擬對打啟動失敗: {e}")
        
        # 7. 熱身訓練
        elif hasattr(current_tab, 'start_warmup'):
            try:
                current_tab.start_warmup()
                training_started = True
                self.log_message("🚀 開始熱身訓練（簡報筆遙控）")
            except Exception as e:
                self.log_message(f"⚠️ 熱身訓練啟動失敗: {e}")
        
        if not training_started:
            self.log_message("⚠️ 無法啟動訓練：請檢查訓練設定")
            # 如果無法啟動訓練，將狀態重置為 IDLE
            self.system_service.reset()
            self.update_status_light(self.system_service.get_state())
    
    def _handle_pause_training(self):
        """處理暫停訓練的業務邏輯"""
        # 暫停當前運行的訓練
        if hasattr(self, 'training_task') and self.training_task and not self.training_task.done():
            self.training_task.cancel()
        
        # 停止連發模式
        if hasattr(self, 'burst_mode_active') and self.burst_mode_active:
            if hasattr(self, 'stop_burst_mode'):
                self.stop_burst_mode()
        
        self.log_message("⏸️ 暫停訓練（簡報筆遙控）")
    
    def _has_available_training_target(self):
        """檢查是否有可用的訓練目標"""
        current_tab = self.tab_widget.currentWidget()
        
        # 1. 檢查課程訓練標籤頁
        if hasattr(current_tab, 'program_combo') and current_tab.program_combo.currentIndex() >= 0:
            return True
        
        # 2. 檢查手動控制標籤頁（雙機）
        if hasattr(current_tab, 'current_burst_section') and current_tab.current_burst_section:
            return True
        
        # 3. 檢查手動控制標籤頁（單機）
        if hasattr(current_tab, 'single_current_burst_section') and current_tab.single_current_burst_section:
            return True
        
        # 4. 檢查基礎訓練標籤頁
        if hasattr(current_tab, 'selected_training') and current_tab.selected_training:
            return True
        
        # 5. 檢查進階訓練標籤頁
        if hasattr(current_tab, 'selected_advanced_training') and current_tab.selected_advanced_training:
            return True
        
        # 6. 檢查模擬對打標籤頁
        if hasattr(current_tab, 'simulation_level') and current_tab.simulation_level:
            return True
        
        # 7. 檢查熱身標籤頁
        if hasattr(current_tab, 'selected_warmup') and current_tab.selected_warmup:
            return True
        
        return False
    
    def _handle_emergency_stop(self):
        """處理急停的業務邏輯"""
        # 停止所有訓練任務
        if hasattr(self, 'training_task') and self.training_task and not self.training_task.done():
            self.training_task.cancel()
        
        # 停止連發模式
        if hasattr(self, 'burst_mode_active') and self.burst_mode_active:
            if hasattr(self, 'stop_burst_mode'):
                self.stop_burst_mode()
        
        # 停止單機連發
        if hasattr(self, 'single_burst_mode_active') and self.single_burst_mode_active:
            if hasattr(self, 'stop_burst_mode_single'):
                self.stop_burst_mode_single()
        
        self.log_message("🛑 急停執行（簡報筆遙控）")

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
BadmintonLauncherGUI.handle_shot_button_click = getattr(_ui_control, 'handle_shot_button_click')
BadmintonLauncherGUI.start_burst_mode = getattr(_ui_control, 'start_burst_mode')
BadmintonLauncherGUI.stop_burst_mode = getattr(_ui_control, 'stop_burst_mode')
BadmintonLauncherGUI.execute_burst_sequence = getattr(_ui_control, 'execute_burst_sequence')
BadmintonLauncherGUI.update_burst_status = getattr(_ui_control, 'update_burst_status')
BadmintonLauncherGUI.start_training = getattr(_ui_training, 'start_training')
BadmintonLauncherGUI.execute_training = getattr(_ui_training, 'execute_training')
BadmintonLauncherGUI.stop_training = getattr(_ui_training, 'stop_training')
BadmintonLauncherGUI.create_text_input_tab = getattr(_ui_text_input, 'create_text_input_tab')
BadmintonLauncherGUI.create_voice_tab = getattr(_ui_voice, 'create_voice_tab')
BadmintonLauncherGUI.create_ai_coach_tab = getattr(_ui_ai_coach, 'create_ai_coach_tab')
BadmintonLauncherGUI.send_coach_message = getattr(_ui_ai_coach, 'send_coach_message')
BadmintonLauncherGUI._append_ai_coach_chat = getattr(_ui_ai_coach, '_append_ai_coach_chat')
BadmintonLauncherGUI.init_ai_coach_system = getattr(_ui_ai_coach, 'init_ai_coach_system')
BadmintonLauncherGUI.update_ai_coach_user_info = getattr(_ui_ai_coach, 'update_ai_coach_user_info')
BadmintonLauncherGUI.clear_ai_coach_chat = getattr(_ui_ai_coach, 'clear_ai_coach_chat')
BadmintonLauncherGUI.send_ai_coach_message = getattr(_ui_ai_coach, 'send_ai_coach_message')
# 移除不存在的方法綁定：'_build_coach_system_prompt', '_should_use_cache', '_generate_coach_reply'
BadmintonLauncherGUI.update_voice_status = getattr(_ui_voice, 'update_voice_status')
BadmintonLauncherGUI.add_voice_chat_message = getattr(_ui_voice, 'add_voice_chat_message')
BadmintonLauncherGUI.execute_text_command = getattr(_ui_text_input, 'execute_text_command')
BadmintonLauncherGUI.create_log_tab = getattr(_ui_log, 'create_log_tab')
BadmintonLauncherGUI.log_message = getattr(_ui_log, 'log_message')
BadmintonLauncherGUI.load_programs = getattr(_ui_utils, 'load_programs')
BadmintonLauncherGUI.update_program_list = getattr(_ui_utils, 'update_program_list')
BadmintonLauncherGUI.update_program_description = getattr(_ui_utils, 'update_program_description')
BadmintonLauncherGUI.on_scan_button_clicked = getattr(_ui_connection, 'on_scan_button_clicked')
BadmintonLauncherGUI.on_connect_button_clicked = getattr(_ui_connection, 'on_connect_button_clicked')
BadmintonLauncherGUI.on_disconnect_button_clicked = getattr(_ui_connection, 'on_disconnect_button_clicked')
BadmintonLauncherGUI.on_position_changed = getattr(_ui_connection, 'on_position_changed')
# 雙發球機相關函數
BadmintonLauncherGUI._create_single_machine_tab = getattr(_ui_connection, '_create_single_machine_tab')
BadmintonLauncherGUI._create_dual_machine_tab = getattr(_ui_connection, '_create_dual_machine_tab')
BadmintonLauncherGUI.on_dual_scan_button_clicked = getattr(_ui_connection, 'on_dual_scan_button_clicked')
BadmintonLauncherGUI.on_connect_dual_button_clicked = getattr(_ui_connection, 'on_connect_dual_button_clicked')
BadmintonLauncherGUI.on_disconnect_dual_button_clicked = getattr(_ui_connection, 'on_disconnect_dual_button_clicked')
BadmintonLauncherGUI.update_dual_connection_status = getattr(_ui_connection, 'update_dual_connection_status')
BadmintonLauncherGUI.update_connection_status = getattr(_ui_connection, 'update_connection_status')
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
# 三發球機相關函數
BadmintonLauncherGUI.create_three_machine_tab = getattr(_ui_three_machine, 'create_three_machine_tab')
# 自定義發球控制相關函數
BadmintonLauncherGUI.create_custom_shot_tab = getattr(_ui_custom_shot, 'create_custom_shot_control_tab')
# Simulate 面板
BadmintonLauncherGUI.create_simulate_panel = getattr(_ui_simulate_panel, 'create_simulate_panel')
BadmintonLauncherGUI._refresh_simulate_panel = getattr(_ui_simulate_panel, '_refresh_simulate_panel')
BadmintonLauncherGUI._clear_simulate_logs = getattr(_ui_simulate_panel, '_clear_simulate_logs')

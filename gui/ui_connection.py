from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, 
                             QGroupBox, QHBoxLayout, QTabWidget, QFrame, QGridLayout)
from PyQt5.QtCore import Qt
import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.managers import create_bluetooth_manager, create_dual_bluetooth_manager
from core.services.device_service import DeviceService

def create_connection_tab(self):
    """創建連接標籤頁"""
    connection_widget = QWidget()
    layout = QVBoxLayout(connection_widget)
    
    # 創建連接模式選擇標籤頁
    connection_tabs = QTabWidget()
    
    # 單發球機連接標籤頁
    single_tab = self._create_single_machine_tab()
    connection_tabs.addTab(single_tab, "🔧 單發球機")
    
    # 雙發球機連接標籤頁
    dual_tab = self._create_dual_machine_tab()
    connection_tabs.addTab(dual_tab, "🤖 雙發球機")
    
    layout.addWidget(connection_tabs)
    layout.addStretch()
    
    # 建立裝置服務（統一路徑）
    self.device_service = DeviceService(self, simulate=False)
    # 仍保留舊管理器以相容（將於 M5 移除）
    self.bluetooth_manager = create_bluetooth_manager(self)
    self.dual_bluetooth_manager = create_dual_bluetooth_manager(self)
    
    # 初始化雙發球機模式標誌
    self.dual_machine_mode = False
    self.left_bluetooth_thread = None
    self.right_bluetooth_thread = None
    
    self.tab_widget.addTab(connection_widget, "連接設定")


def _create_single_machine_tab(self):
    """創建單發球機連接標籤頁"""
    single_widget = QWidget()
    layout = QVBoxLayout(single_widget)
    
    # 單發球機連接控制組
    single_group = QGroupBox("🔧 單發球機連接")
    single_group.setStyleSheet("""
        QGroupBox::title {
            color: #4CAF50;
            font-weight: bold;
            font-size: 14px;
        }
    """)
    single_layout = QVBoxLayout(single_group)
    
    # 掃描按鈕
    self.scan_button = QPushButton("🔍 掃描發球機")
    self.scan_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4CAF50, stop:1 #45a049);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #45a049, stop:1 #3d8b40);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3d8b40, stop:1 #357a38);
        }
    """)
    self.scan_button.clicked.connect(self.on_scan_button_clicked)
    single_layout.addWidget(self.scan_button)
    
    # 設備列表
    single_layout.addWidget(QLabel("📱 選擇設備:"))
    self.device_combo = QComboBox()
    self.device_combo.addItem("請先掃描設備")
    self.device_combo.setStyleSheet("""
        QComboBox {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #4CAF50;
            margin-right: 10px;
        }
    """)
    single_layout.addWidget(self.device_combo)
    
    # 發球機位置選擇
    single_layout.addWidget(QLabel("📍 發球機位置:"))
    self.position_combo = QComboBox()
    self.position_combo.addItem("🏠 中央位置 (預設)", "center")
    self.position_combo.addItem("⬅️ 左側位置", "left")
    self.position_combo.addItem("➡️ 右側位置", "right")
    self.position_combo.setStyleSheet("""
        QComboBox {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid #ff9800;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #ff9800;
            margin-right: 10px;
        }
    """)
    self.position_combo.currentTextChanged.connect(self.on_position_changed)
    single_layout.addWidget(self.position_combo)
    
    # 連接控制按鈕
    connect_control_layout = QHBoxLayout()
    
    self.connect_button = QPushButton("🔗 連接")
    self.connect_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2196F3, stop:1 #1976D2);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1976D2, stop:1 #1565C0);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1565C0, stop:1 #0D47A1);
        }
    """)
    self.connect_button.clicked.connect(self.on_connect_button_clicked)
    self.connect_button.setEnabled(False)
    connect_control_layout.addWidget(self.connect_button)
    
    self.disconnect_button = QPushButton("❌ 斷開")
    self.disconnect_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f44336, stop:1 #d32f2f);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #d32f2f, stop:1 #c62828);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #c62828, stop:1 #b71c1c);
        }
    """)
    self.disconnect_button.clicked.connect(self.on_disconnect_button_clicked)
    self.disconnect_button.setEnabled(False)
    connect_control_layout.addWidget(self.disconnect_button)
    
    single_layout.addLayout(connect_control_layout)
    
    # 連接狀態顯示
    self.connection_status_label = QLabel("💤 未連接")
    self.connection_status_label.setStyleSheet("""
        QLabel {
            color: #ffcc00;
            font-weight: bold;
            font-size: 12px;
            padding: 8px;
            background-color: rgba(255, 204, 0, 0.1);
            border: 1px solid #ffcc00;
            border-radius: 5px;
        }
    """)
    single_layout.addWidget(self.connection_status_label)
    
    layout.addWidget(single_group)
    layout.addStretch()
    
    return single_widget


def _create_dual_machine_tab(self):
    """創建雙發球機連接標籤頁"""
    dual_widget = QWidget()
    layout = QVBoxLayout(dual_widget)
    
    # 雙發球機連接控制組
    dual_group = QGroupBox("🤖 雙發球機連接")
    dual_group.setStyleSheet("""
        QGroupBox::title {
            color: #ff9800;
            font-weight: bold;
            font-size: 14px;
        }
    """)
    dual_layout = QVBoxLayout(dual_group)
    
    # 掃描按鈕
    self.dual_scan_button = QPushButton("🔍 掃描雙發球機")
    self.dual_scan_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ff9800, stop:1 #f57c00);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f57c00, stop:1 #ef6c00);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ef6c00, stop:1 #e65100);
        }
    """)
    self.dual_scan_button.clicked.connect(self.on_dual_scan_button_clicked)
    dual_layout.addWidget(self.dual_scan_button)
    
    # 設備選擇區域
    device_selection_layout = QGridLayout()
    
    # 左發球機選擇
    device_selection_layout.addWidget(QLabel("🔵 左發球機:"), 0, 0)
    self.left_device_combo = QComboBox()
    self.left_device_combo.addItem("請先掃描設備")
    self.left_device_combo.setStyleSheet("""
        QComboBox {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid #2196F3;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #2196F3;
            margin-right: 10px;
        }
    """)
    device_selection_layout.addWidget(self.left_device_combo, 0, 1)
    
    # 右發球機選擇
    device_selection_layout.addWidget(QLabel("🔴 右發球機:"), 1, 0)
    self.right_device_combo = QComboBox()
    self.right_device_combo.addItem("請先掃描設備")
    self.right_device_combo.setStyleSheet("""
        QComboBox {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid #f44336;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #f44336;
            margin-right: 10px;
        }
    """)
    device_selection_layout.addWidget(self.right_device_combo, 1, 1)
    
    dual_layout.addLayout(device_selection_layout)
    
    # 連接控制按鈕
    dual_connect_control_layout = QHBoxLayout()
    
    self.connect_dual_button = QPushButton("🔗 連接雙發球機")
    self.connect_dual_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9c27b0, stop:1 #7b1fa2);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7b1fa2, stop:1 #6a1b9a);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6a1b9a, stop:1 #4a148c);
        }
    """)
    self.connect_dual_button.clicked.connect(self.on_connect_dual_button_clicked)
    self.connect_dual_button.setEnabled(False)
    dual_connect_control_layout.addWidget(self.connect_dual_button)
    
    self.disconnect_dual_button = QPushButton("❌ 斷開雙發球機")
    self.disconnect_dual_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f44336, stop:1 #d32f2f);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #d32f2f, stop:1 #c62828);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #c62828, stop:1 #b71c1c);
        }
    """)
    self.disconnect_dual_button.clicked.connect(self.on_disconnect_dual_button_clicked)
    self.disconnect_dual_button.setEnabled(False)
    dual_connect_control_layout.addWidget(self.disconnect_dual_button)
    
    dual_layout.addLayout(dual_connect_control_layout)
    
    # 雙發球機狀態顯示
    dual_status_layout = QVBoxLayout()
    
    self.left_machine_status = QLabel("🔵 左發球機: 💤 未連接")
    self.left_machine_status.setStyleSheet("""
        QLabel {
            color: #2196F3;
            font-weight: bold;
            font-size: 12px;
            padding: 8px;
            background-color: rgba(33, 150, 243, 0.1);
            border: 1px solid #2196F3;
            border-radius: 5px;
        }
    """)
    dual_status_layout.addWidget(self.left_machine_status)
    
    self.right_machine_status = QLabel("🔴 右發球機: 💤 未連接")
    self.right_machine_status.setStyleSheet("""
        QLabel {
            color: #f44336;
            font-weight: bold;
            font-size: 12px;
            padding: 8px;
            background-color: rgba(244, 67, 54, 0.1);
            border: 1px solid #f44336;
            border-radius: 5px;
        }
    """)
    dual_status_layout.addWidget(self.right_machine_status)
    
    self.dual_connection_status = QLabel("🤖 雙發球機模式: 💤 未啟用")
    self.dual_connection_status.setStyleSheet("""
        QLabel {
            color: #ff9800;
            font-weight: bold;
            font-size: 12px;
            padding: 8px;
            background-color: rgba(255, 152, 0, 0.1);
            border: 1px solid #ff9800;
            border-radius: 5px;
        }
    """)
    dual_status_layout.addWidget(self.dual_connection_status)
    
    dual_layout.addLayout(dual_status_layout)
    
    # 雙發球機說明
    dual_info = QLabel("💡 雙發球機模式：掃描並連接兩台發球機，支援協調發球和智能訓練")
    dual_info.setStyleSheet("color: #ffcc00; font-size: 11px;")
    dual_info.setWordWrap(True)
    dual_layout.addWidget(dual_info)
    
    layout.addWidget(dual_group)
    layout.addStretch()
    
    return dual_widget


def on_position_changed(self):
    """發球機位置變更事件"""
    try:
        position = self.position_combo.currentData()
        position_name = self.position_combo.currentText()
        
        self.log_message(f"📍 發球機位置已變更為: {position_name}")
        
        # 如果已連接，通知藍牙管理器更新參數映射
        if hasattr(self, 'bluetooth_manager') and self.bluetooth_manager.bluetooth_thread and self.bluetooth_manager.bluetooth_thread.is_connected:
            self.bluetooth_manager.set_machine_position(position)
            self.log_message(f"✅ 已更新發球機參數映射為: {position}")
        
    except Exception as e:
        self.log_message(f"❌ 位置變更處理失敗: {e}")

def on_scan_button_clicked(self):
    """掃描按鈕點擊事件（UI 層面的處理）"""
    # 使用統一 Service
    self.create_async_task(self.device_service.scan())

def on_connect_button_clicked(self):
    """連接按鈕點擊事件（UI 層面的處理）"""
    address = self.device_combo.currentData()
    # Service 內部會處理地址為空的情況
    self.create_async_task(self.device_service.connect(address))

def on_disconnect_button_clicked(self):
    """斷開按鈕點擊事件（UI 層面的處理）"""
    # 使用統一 Service
    self.create_async_task(self.device_service.disconnect())

# 雙發球機事件處理函數
def on_dual_scan_button_clicked(self):
    """雙發球機掃描按鈕點擊事件"""
    self.create_async_task(self.dual_bluetooth_manager.scan_dual_devices())

def on_connect_dual_button_clicked(self):
    """雙發球機連接按鈕點擊事件"""
    try:
        self.log_message("🖱️ 雙發球機連接按鈕被點擊")
        
        # 檢查雙發球機管理器是否存在
        if not hasattr(self, 'dual_bluetooth_manager') or self.dual_bluetooth_manager is None:
            self.log_message("❌ 雙發球機管理器未初始化")
            return
        
        # 檢查是否有可用的設備
        if not hasattr(self, 'left_device_combo') or not hasattr(self, 'right_device_combo'):
            self.log_message("❌ 設備選擇組件未初始化")
            return
        
        left_address = self.left_device_combo.currentData()
        right_address = self.right_device_combo.currentData()
        
        if not left_address or not right_address:
            self.log_message("❌ 請先選擇左右發球機設備")
            return
        
        self.log_message(f"🔗 準備連接: 左發球機({left_address}), 右發球機({right_address})")
        
        # 創建並執行連接任務
        task = self.create_async_task(self.dual_bluetooth_manager.connect_dual_machines())
        self.log_message(f"📋 已創建連接任務: {task}")
        
    except Exception as e:
        self.log_message(f"❌ 創建連接任務失敗: {e}")
        import traceback
        traceback.print_exc()

def on_disconnect_dual_button_clicked(self):
    """雙發球機斷開按鈕點擊事件"""
    self.create_async_task(self.dual_bluetooth_manager.disconnect_dual_machines())

def update_dual_connection_status(self, machine_name: str, connected: bool, message: str):
    """更新雙發球機連接狀態顯示"""
    try:
        if machine_name == "左發球機":
            if connected:
                self.left_machine_status.setText("🔵 左發球機: ✅ 已連接")
                self.left_machine_status.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 8px;
                        background-color: rgba(76, 175, 80, 0.1);
                        border: 1px solid #4CAF50;
                        border-radius: 5px;
                    }
                """)
            else:
                self.left_machine_status.setText("🔵 左發球機: ❌ 未連接")
                self.left_machine_status.setStyleSheet("""
                    QLabel {
                        color: #f44336;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 8px;
                        background-color: rgba(244, 67, 54, 0.1);
                        border: 1px solid #f44336;
                        border-radius: 5px;
                    }
                """)
        
        elif machine_name == "右發球機":
            if connected:
                self.right_machine_status.setText("🔴 右發球機: ✅ 已連接")
                self.right_machine_status.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 8px;
                        background-color: rgba(76, 175, 80, 0.1);
                        border: 1px solid #4CAF50;
                        border-radius: 5px;
                    }
                """)
            else:
                self.right_machine_status.setText("🔴 右發球機: ❌ 未連接")
                self.right_machine_status.setStyleSheet("""
                    QLabel {
                        color: #f44336;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 8px;
                        background-color: rgba(244, 67, 54, 0.1);
                        border: 1px solid #f44336;
                        border-radius: 5px;
                    }
                """)
        
        # 更新雙發球機模式狀態
        if hasattr(self, 'dual_bluetooth_manager') and self.dual_bluetooth_manager.is_dual_connected():
            self.dual_connection_status.setText("🤖 雙發球機模式: ✅ 已啟用")
            self.dual_connection_status.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(76, 175, 80, 0.1);
                    border: 1px solid #4CAF50;
                    border-radius: 5px;
                }
            """)
            
            # 啟用雙發球機控制按鈕
            if hasattr(self, 'disconnect_dual_button'):
                self.disconnect_dual_button.setEnabled(True)
            if hasattr(self, 'connect_dual_button'):
                self.connect_dual_button.setEnabled(False)
            
            # 更新總狀態欄為雙發球機已連接
            if hasattr(self, 'status_label'):
                self.status_label.setText("🟢 SYSTEM STATUS: DUAL MACHINE CONNECTED & READY")
                self.status_label.setStyleSheet("""
                    padding: 10px 16px;
                    background-color: rgba(120, 180, 120, 0.6);
                    color: #ffffff;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    border: 1px solid #78b478;
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    letter-spacing: 1px;
                """)
        else:
            self.dual_connection_status.setText("🤖 雙發球機模式: 💤 未啟用")
            self.dual_connection_status.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(255, 152, 0, 0.1);
                    border: 1px solid #ff9800;
                    border-radius: 5px;
                }
            """)
            
            # 禁用雙發球機控制按鈕
            if hasattr(self, 'disconnect_dual_button'):
                self.disconnect_dual_button.setEnabled(False)
            if hasattr(self, 'connect_dual_button'):
                self.connect_dual_button.setEnabled(True)
            
            # 如果雙發球機未連接，檢查單發球機狀態
            if hasattr(self, 'bluetooth_manager') and self.bluetooth_manager.is_connected():
                # 單發球機已連接，保持單發球機狀態
                if hasattr(self, 'status_label'):
                    self.status_label.setText("🟢 SYSTEM STATUS: CONNECTED & READY")
                    self.status_label.setStyleSheet("""
                        padding: 10px 16px;
                        background-color: rgba(120, 180, 120, 0.6);
                        color: #ffffff;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 13px;
                        border: 1px solid #78b478;
                        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                        letter-spacing: 1px;
                    """)
            else:
                # 都沒有連接，顯示未連接狀態
                if hasattr(self, 'status_label'):
                    self.status_label.setText("🔴 SYSTEM STATUS: DISCONNECTED")
                    self.status_label.setStyleSheet("""
                        padding: 10px 16px;
                        background-color: rgba(180, 80, 80, 0.6);
                        color: #ffffff;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 13px;
                        border: 1px solid #b45050;
                        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                        letter-spacing: 1px;
                    """)
                
    except Exception as e:
        self.log_message(f"❌ 更新雙發球機連接狀態失敗: {e}")

def update_connection_status(self, connected: bool, message: str):
    """更新單發球機連接狀態顯示"""
    try:
        if connected:
            self.connection_status_label.setText("✅ 已連接")
            self.connection_status_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(76, 175, 80, 0.1);
                    border: 1px solid #4CAF50;
                    border-radius: 5px;
                }
            """)
            # 啟用控制按鈕
            if hasattr(self, 'disconnect_button'):
                self.disconnect_button.setEnabled(True)
            if hasattr(self, 'connect_button'):
                self.connect_button.setEnabled(False)
            
            # 更新總狀態欄為已連接
            if hasattr(self, 'status_label'):
                self.status_label.setText("🟢 SYSTEM STATUS: CONNECTED & READY")
                self.status_label.setStyleSheet("""
                    padding: 10px 16px;
                    background-color: rgba(120, 180, 120, 0.6);
                    color: #ffffff;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    border: 1px solid #78b478;
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    letter-spacing: 1px;
                """)
        else:
            self.connection_status_label.setText("❌ 未連接")
            self.connection_status_label.setStyleSheet("""
                QLabel {
                    color: #f44336;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(244, 67, 54, 0.1);
                    border: 1px solid #f44336;
                    border-radius: 5px;
                }
            """)
            # 禁用控制按鈕
            if hasattr(self, 'disconnect_button'):
                self.disconnect_button.setEnabled(False)
            if hasattr(self, 'connect_button'):
                self.connect_button.setEnabled(True)
            
            # 更新總狀態欄為未連接
            if hasattr(self, 'status_label'):
                self.status_label.setText("🔴 SYSTEM STATUS: DISCONNECTED")
                self.status_label.setStyleSheet("""
                    padding: 10px 16px;
                    background-color: rgba(180, 80, 80, 0.6);
                    color: #ffffff;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    border: 1px solid #b45050;
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    letter-spacing: 1px;
                """)
                
    except Exception as e:
        self.log_message(f"❌ 更新連接狀態失敗: {e}")

# 為了向後相容，保留這些函數名稱
async def scan_devices(self, checked=False):
    """掃描設備（向後相容）"""
    await self.bluetooth_manager.scan_devices()

async def connect_device(self, checked=False):
    """連接設備（向後相容）"""
    address = self.device_combo.currentData()
    if address:
        await self.bluetooth_manager.connect_device(address)

async def disconnect_device(self, checked=False):
    """斷開連接（向後相容）"""
    await self.bluetooth_manager.disconnect_device()

def on_device_found(self, address):
    """設備找到回調（向後相容）"""
    # 這個回調現在由 bluetooth_manager 處理
    pass

def on_shot_sent(self, message):
    """發球發送回調（向後相容）"""
    # 這個回調現在由 bluetooth_manager 處理
    pass

def on_connection_status(self, connected, message):
    """連接狀態回調（向後相容）"""
    # 這個回調現在由 bluetooth_manager 處理
    pass
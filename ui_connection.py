import asyncio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox
from PyQt5.QtCore import pyqtSignal
from bluetooth import BluetoothThread
from qasync import asyncSlot
target_name_prefix = "YX-BE241"

def create_connection_tab(self):
    """創建連接標籤頁"""
    connection_widget = QWidget()
    layout = QVBoxLayout(connection_widget)
    
    # 連接控制組
    connection_group = QGroupBox("藍牙連接")
    connection_layout = QVBoxLayout(connection_group)
    
    # 掃描按鈕
    self.scan_button = QPushButton("🔍 掃描發球機")
    # 使用 lambda 直接呼叫 asyncSlot 包裝的方法（其本身會建立任務）
    self.scan_button.clicked.connect(lambda checked=False: self.scan_devices())
    connection_layout.addWidget(self.scan_button)
    
    # 設備列表
    self.device_combo = QComboBox()
    self.device_combo.addItem("請先掃描設備")
    connection_layout.addWidget(QLabel("選擇設備:"))
    connection_layout.addWidget(self.device_combo)
    
    # 連接按鈕
    self.connect_button = QPushButton("🔗 連接")
    self.connect_button.clicked.connect(lambda checked=False: self.connect_device())
    self.connect_button.setEnabled(False)
    connection_layout.addWidget(self.connect_button)
    
    # 斷開按鈕
    self.disconnect_button = QPushButton("❌ 斷開")
    self.disconnect_button.clicked.connect(lambda checked=False: self.disconnect_device())
    self.disconnect_button.setEnabled(False)
    connection_layout.addWidget(self.disconnect_button)
    
    layout.addWidget(connection_group)
    layout.addStretch()
    
    self.tab_widget.addTab(connection_widget, "連接設定")


@asyncSlot(bool)
async def scan_devices(self, checked=False):
    """掃描設備"""
    self.log_message("開始掃描發球機...")
    self.scan_button.setEnabled(False)
    self.scan_button.setText("掃描中...")

    try:
        # 創建藍牙線程
        self.bluetooth_thread = BluetoothThread()
        self.bluetooth_thread.device_found.connect(self.on_device_found)
        self.bluetooth_thread.connection_status.connect(self.on_connection_status)
        self.bluetooth_thread.shot_sent.connect(self.on_shot_sent)
        self.bluetooth_thread.error_occurred.connect(self.on_error)

        # 開始掃描
        await self.bluetooth_thread.find_device()

    except Exception as e:
        self.log_message(f"掃描失敗: {e}")
    finally:
        self.scan_button.setEnabled(True)
        self.scan_button.setText("🔍 掃描發球機")

def on_scan_button_clicked(self):
    asyncio.create_task(self.scan_devices())

def on_device_found(self, address):
    """設備找到回調"""
    self.device_combo.clear()
    self.device_combo.addItem(f"{target_name_prefix}-{address[-8:]} ({address})", address)
    self.connect_button.setEnabled(True)
    self.log_message(f"找到設備: {address}")

def on_shot_sent(self, message):
    """發球發送回調"""
    self.log_message(message)

@asyncSlot(bool)
async def connect_device(self, checked=False):
    """連接設備"""
    address = self.device_combo.currentData()
    if not address:
        return

    if not self.bluetooth_thread:
        self.log_message("請先掃描設備")
        return

    self.log_message(f"正在連接到 {address}...")
    self.connect_button.setEnabled(False)

    try:
        await self.bluetooth_thread.connect_device(address)
    except Exception as e:
        self.log_message(f"連接失敗: {e}")
        self.connect_button.setEnabled(True)

def on_connection_status(self, connected, message):
    """連接狀態回調"""
    if connected:
        self.status_label.setText("已連接")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background-color: #44ff44;
            color: white;
            border-radius: 5px;
            font-weight: bold;
            border: 1px solid #00cc00;
        """)
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.start_training_button.setEnabled(True)
    else:
        self.status_label.setText("未連接")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background-color: #ff4444;
            color: white;
            border-radius: 5px;
            font-weight: bold;
            border: 1px solid #cc0000;
        """)
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.start_training_button.setEnabled(False)

    self.log_message(message)

@asyncSlot(bool)
async def disconnect_device(self, checked=False):
    """斷開連接"""
    if not self.bluetooth_thread:
        self.log_message("沒有連接的設備")
        return

    await self.bluetooth_thread.disconnect()

def on_connect_button_clicked(self):
    asyncio.create_task(self.connect_device())

def on_disconnect_button_clicked(self):
    asyncio.create_task(self.disconnect_device())
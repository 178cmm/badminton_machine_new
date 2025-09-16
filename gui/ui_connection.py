from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox
import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.managers import create_bluetooth_manager

def create_connection_tab(self):
    """創建連接標籤頁"""
    connection_widget = QWidget()
    layout = QVBoxLayout(connection_widget)
    
    # 連接控制組
    connection_group = QGroupBox("藍牙連接")
    connection_layout = QVBoxLayout(connection_group)
    
    # 掃描按鈕
    self.scan_button = QPushButton("🔍 掃描發球機")
    self.scan_button.clicked.connect(self.on_scan_button_clicked)
    connection_layout.addWidget(self.scan_button)
    
    # 設備列表
    self.device_combo = QComboBox()
    self.device_combo.addItem("請先掃描設備")
    connection_layout.addWidget(QLabel("選擇設備:"))
    connection_layout.addWidget(self.device_combo)
    
    # 連接按鈕
    self.connect_button = QPushButton("🔗 連接")
    self.connect_button.clicked.connect(self.on_connect_button_clicked)
    self.connect_button.setEnabled(False)
    connection_layout.addWidget(self.connect_button)
    
    # 斷開按鈕
    self.disconnect_button = QPushButton("❌ 斷開")
    self.disconnect_button.clicked.connect(self.on_disconnect_button_clicked)
    self.disconnect_button.setEnabled(False)
    connection_layout.addWidget(self.disconnect_button)
    
    # 建立藍牙管理器
    self.bluetooth_manager = create_bluetooth_manager(self)
    
    layout.addWidget(connection_group)
    layout.addStretch()
    
    self.tab_widget.addTab(connection_widget, "連接設定")


def on_scan_button_clicked(self):
    """掃描按鈕點擊事件（UI 層面的處理）"""
    # 使用安全的方法創建異步任務
    self.create_async_task(self.bluetooth_manager.scan_devices())

def on_connect_button_clicked(self):
    """連接按鈕點擊事件（UI 層面的處理）"""
    address = self.device_combo.currentData()
    if address:
        # 使用安全的方法創建異步任務
        self.create_async_task(self.bluetooth_manager.connect_device(address))

def on_disconnect_button_clicked(self):
    """斷開按鈕點擊事件（UI 層面的處理）"""
    # 使用安全的方法創建異步任務
    self.create_async_task(self.bluetooth_manager.disconnect_device())

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
"""
藍牙連接管理器

這個模組負責管理藍牙連接的邏輯，包括掃描、連接、斷開等操作。
"""

import asyncio
from typing import Optional, Callable, Any
from bluetooth import BluetoothThread


class BluetoothManager:
    """藍牙連接管理器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化藍牙管理器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
        self.bluetooth_thread: Optional[BluetoothThread] = None
        self.target_name_prefix = "YX-BE241"
    
    async def scan_devices(self) -> bool:
        """
        掃描藍牙設備
        
        Returns:
            是否成功開始掃描
        """
        try:
            self.gui.log_message("開始掃描發球機...")
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'scan_button'):
                self.gui.scan_button.setEnabled(False)
                self.gui.scan_button.setText("掃描中...")
            
            # 創建藍牙線程
            self.bluetooth_thread = BluetoothThread()
            self.bluetooth_thread.device_found.connect(self._on_device_found)
            self.bluetooth_thread.connection_status.connect(self._on_connection_status)
            self.bluetooth_thread.shot_sent.connect(self._on_shot_sent)
            self.bluetooth_thread.error_occurred.connect(self._on_error)
            
            # 開始掃描
            await self.bluetooth_thread.find_device()
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"掃描失敗: {e}")
            return False
        finally:
            # 恢復 UI 狀態
            if hasattr(self.gui, 'scan_button'):
                self.gui.scan_button.setEnabled(True)
                self.gui.scan_button.setText("🔍 掃描發球機")
    
    async def connect_device(self, address: str) -> bool:
        """
        連接到指定的藍牙設備
        
        Args:
            address: 設備地址
            
        Returns:
            是否成功連接
        """
        try:
            if not self.bluetooth_thread:
                self.gui.log_message("請先掃描設備")
                return False
            
            self.gui.log_message(f"正在連接到 {address}...")
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(False)
            
            # 執行連接
            await self.bluetooth_thread.connect_device(address)
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"連接失敗: {e}")
            # 恢復 UI 狀態
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(True)
            return False
    
    async def disconnect_device(self) -> bool:
        """
        斷開藍牙連接
        
        Returns:
            是否成功斷開
        """
        try:
            if not self.bluetooth_thread:
                self.gui.log_message("沒有連接的設備")
                return False
            
            await self.bluetooth_thread.disconnect()
            return True
            
        except Exception as e:
            self.gui.log_message(f"斷開連接失敗: {e}")
            return False
    
    def is_connected(self) -> bool:
        """
        檢查是否已連接
        
        Returns:
            是否已連接
        """
        return self.bluetooth_thread is not None and self.bluetooth_thread.is_connected
    
    def get_bluetooth_thread(self) -> Optional[BluetoothThread]:
        """
        取得藍牙線程實例
        
        Returns:
            藍牙線程實例
        """
        return self.bluetooth_thread
    
    def _on_device_found(self, address: str):
        """設備找到回調"""
        try:
            # 更新設備列表
            if hasattr(self.gui, 'device_combo'):
                self.gui.device_combo.clear()
                device_name = f"{self.target_name_prefix}-{address[-8:]} ({address})"
                self.gui.device_combo.addItem(device_name, address)
            
            # 啟用連接按鈕
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(True)
            
            self.gui.log_message(f"找到設備: {address}")
            
        except Exception as e:
            self.gui.log_message(f"處理設備找到事件時發生錯誤: {e}")
    
    def _on_connection_status(self, connected: bool, message: str):
        """連接狀態回調"""
        try:
            if connected:
                self._update_ui_connected()
            else:
                self._update_ui_disconnected()
            
            self.gui.log_message(message)
            
        except Exception as e:
            self.gui.log_message(f"處理連接狀態事件時發生錯誤: {e}")
    
    def _on_shot_sent(self, message: str):
        """發球發送回調"""
        try:
            self.gui.log_message(message)
        except Exception as e:
            print(f"處理發球事件時發生錯誤: {e}")
    
    def _on_error(self, message: str):
        """錯誤回調"""
        try:
            self.gui.log_message(f"錯誤: {message}")
        except Exception as e:
            print(f"處理錯誤事件時發生錯誤: {e}")
    
    def _update_ui_connected(self):
        """更新 UI 為已連接狀態"""
        try:
            # 更新狀態標籤
            if hasattr(self.gui, 'status_label'):
                self.gui.status_label.setText("已連接")
                self.gui.status_label.setStyleSheet("""
                    padding: 8px;
                    background-color: #44ff44;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                    border: 1px solid #00cc00;
                """)
            
            # 更新按鈕狀態
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(False)
            if hasattr(self.gui, 'disconnect_button'):
                self.gui.disconnect_button.setEnabled(True)
            if hasattr(self.gui, 'start_training_button'):
                self.gui.start_training_button.setEnabled(True)
                
        except Exception as e:
            print(f"更新連接 UI 時發生錯誤: {e}")
    
    def _update_ui_disconnected(self):
        """更新 UI 為未連接狀態"""
        try:
            # 更新狀態標籤
            if hasattr(self.gui, 'status_label'):
                self.gui.status_label.setText("未連接")
                self.gui.status_label.setStyleSheet("""
                    padding: 8px;
                    background-color: #ff4444;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                    border: 1px solid #cc0000;
                """)
            
            # 更新按鈕狀態
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(True)
            if hasattr(self.gui, 'disconnect_button'):
                self.gui.disconnect_button.setEnabled(False)
            if hasattr(self.gui, 'start_training_button'):
                self.gui.start_training_button.setEnabled(False)
                
        except Exception as e:
            print(f"更新斷開 UI 時發生錯誤: {e}")


def create_bluetooth_manager(gui_instance) -> BluetoothManager:
    """
    建立藍牙管理器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        BluetoothManager 實例
    """
    return BluetoothManager(gui_instance)

"""
藍牙連接管理器

這個模組負責管理藍牙連接的邏輯，包括掃描、連接、斷開等操作。
"""

import asyncio
import threading
import queue
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
        self.machine_position = "center"  # 預設為中央位置
    
    def set_machine_position(self, position: str):
        """
        設定發球機位置
        
        Args:
            position: 發球機位置 ("center", "left", "right")
        """
        if position in ["center", "left", "right"]:
            self.machine_position = position
            self.gui.log_message(f"📍 發球機位置已設定為: {position}")
            
            # 如果藍牙線程已連接，更新其位置設定
            if self.bluetooth_thread and hasattr(self.bluetooth_thread, 'set_machine_position'):
                self.bluetooth_thread.set_machine_position(position)
        else:
            self.gui.log_message(f"❌ 無效的發球機位置: {position}")
    
    def get_machine_position(self) -> str:
        """
        獲取當前發球機位置
        
        Returns:
            當前發球機位置
        """
        return self.machine_position
    
    async def scan_devices(self) -> bool:
        """
        掃描藍牙設備（修復版本，防止閃退）
        
        Returns:
            是否成功開始掃描
        """
        try:
            self.gui.log_message("開始掃描發球機...")
            
            # 清理舊的藍牙線程
            if self.bluetooth_thread is not None:
                try:
                    # 斷開信號連接
                    if hasattr(self.bluetooth_thread, 'device_found'):
                        self.bluetooth_thread.device_found.disconnect()
                    if hasattr(self.bluetooth_thread, 'connection_status'):
                        self.bluetooth_thread.connection_status.disconnect()
                    if hasattr(self.bluetooth_thread, 'shot_sent'):
                        self.bluetooth_thread.shot_sent.disconnect()
                    if hasattr(self.bluetooth_thread, 'error_occurred'):
                        self.bluetooth_thread.error_occurred.disconnect()
                    
                    # 如果線程正在運行，停止它
                    if hasattr(self.bluetooth_thread, 'isRunning') and self.bluetooth_thread.isRunning():
                        self.bluetooth_thread.quit()
                        self.bluetooth_thread.wait(1000)  # 等待1秒
                    
                except Exception as e:
                    self.gui.log_message(f"清理舊線程時發生錯誤: {e}")
                
                self.bluetooth_thread = None
            
            # 清空之前的設備列表
            if hasattr(self.gui, 'device_combo'):
                self.gui.device_combo.clear()
                self.gui.device_combo.addItem("請先掃描設備")
            
            # 禁用連接按鈕
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(False)
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'scan_button'):
                self.gui.scan_button.setEnabled(False)
                self.gui.scan_button.setText("掃描中...")
            
            # 創建新的藍牙線程
            self.bluetooth_thread = BluetoothThread()
            self.bluetooth_thread.device_found.connect(self._on_device_found)
            self.bluetooth_thread.connection_status.connect(self._on_connection_status)
            self.bluetooth_thread.shot_sent.connect(self._on_shot_sent)
            self.bluetooth_thread.error_occurred.connect(self._on_error)
            
            # 將藍牙線程設置到主 GUI 類別中
            self.gui.bluetooth_thread = self.bluetooth_thread
            
            # 開始掃描 - 在線程中運行異步掃描
            try:
                import threading
                import queue
                
                result_queue = queue.Queue()
                
                def run_scan_in_thread():
                    try:
                        # 創建新的事件循環
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        
                        # 運行掃描
                        result = new_loop.run_until_complete(self.bluetooth_thread.find_device())
                        result_queue.put(('success', result))
                    except Exception as e:
                        result_queue.put(('error', e))
                    finally:
                        new_loop.close()
                
                # 在後台線程中運行掃描
                scan_thread = threading.Thread(target=run_scan_in_thread, daemon=True)
                scan_thread.start()
                
                # 等待結果（最多等待15秒）
                try:
                    status, result = result_queue.get(timeout=15)
                    if status == 'error':
                        self.gui.log_message(f"❌ 掃描設備失敗: {result}")
                        result = None
                except queue.Empty:
                    self.gui.log_message("❌ 掃描超時，請檢查設備是否開機")
                    result = None
                    
            except Exception as e:
                self.gui.log_message(f"❌ 掃描設備失敗: {e}")
                result = None
            
            # 更新掃描狀態指示器
            if hasattr(self.gui, 'scan_status_label'):
                if result:
                    self.gui.scan_status_label.setText("✅ 掃描完成")
                    self.gui.scan_status_label.setStyleSheet("""
                        QLabel {
                            color: #4CAF50;
                            font-weight: bold;
                            font-size: 11px;
                            padding: 4px;
                            background-color: rgba(76, 175, 80, 0.1);
                            border: 1px solid #4CAF50;
                            border-radius: 3px;
                        }
                    """)
                else:
                    self.gui.scan_status_label.setText("❌ 未找到設備")
                    self.gui.scan_status_label.setStyleSheet("""
                        QLabel {
                            color: #f44336;
                            font-weight: bold;
                            font-size: 11px;
                            padding: 4px;
                            background-color: rgba(244, 67, 54, 0.1);
                            border: 1px solid #f44336;
                            border-radius: 3px;
                        }
                    """)
            
            return bool(result)
            
        except Exception as e:
            self.gui.log_message(f"掃描失敗: {e}")
            # 更新掃描狀態指示器為錯誤狀態
            if hasattr(self.gui, 'scan_status_label'):
                self.gui.scan_status_label.setText("❌ 掃描失敗")
                self.gui.scan_status_label.setStyleSheet("""
                    QLabel {
                        color: #f44336;
                        font-weight: bold;
                        font-size: 11px;
                        padding: 4px;
                        background-color: rgba(244, 67, 54, 0.1);
                        border: 1px solid #f44336;
                        border-radius: 3px;
                    }
                """)
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
                self.gui.log_message("❌ 請先掃描設備")
                return False
            
            self.gui.log_message(f"🔗 正在連接到 {address}...")
            
            # 設定發球機位置
            if hasattr(self.bluetooth_thread, 'set_machine_position'):
                self.bluetooth_thread.set_machine_position(self.machine_position)
                self.gui.log_message(f"📍 使用發球機位置: {self.machine_position}")
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(False)
            
            # 執行連接 - 在線程中運行異步連接
            result_queue = queue.Queue()
            
            def run_connect_in_thread():
                try:
                    # 創建新的事件循環
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # 運行連接
                    result = new_loop.run_until_complete(self.bluetooth_thread.connect_device(address))
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    new_loop.close()
            
            # 在後台線程中運行連接
            connect_thread = threading.Thread(target=run_connect_in_thread, daemon=True)
            connect_thread.start()
            
            # 等待結果（最多等待10秒）
            try:
                status, result = result_queue.get(timeout=10)
                if status == 'error':
                    self.gui.log_message(f"❌ 連接失敗: {result}")
                    # 恢復 UI 狀態
                    if hasattr(self.gui, 'connect_button'):
                        self.gui.connect_button.setEnabled(True)
                    return False
            except queue.Empty:
                self.gui.log_message("❌ 連接超時，請檢查設備是否可達")
                # 恢復 UI 狀態
                if hasattr(self.gui, 'connect_button'):
                    self.gui.connect_button.setEnabled(True)
                return False
            
            # 等待一下讓連接狀態信號有時間處理
            import time
            time.sleep(0.5)
            
            # 檢查連接狀態
            if self.bluetooth_thread.is_connected:
                self.gui.log_message(f"✅ 成功連接到 {address}")
                return True
            else:
                self.gui.log_message(f"❌ 連接失敗：無法連接到 {address}")
                # 恢復 UI 狀態
                if hasattr(self.gui, 'connect_button'):
                    self.gui.connect_button.setEnabled(True)
                return False
            
        except Exception as e:
            self.gui.log_message(f"❌ 連接失敗: {e}")
            import traceback
            traceback.print_exc()
            # 恢復 UI 狀態
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(True)
            return False
    
    async def disconnect_device(self) -> bool:
        """
        斷開藍牙連接（修復版本，處理事件循環問題）
        
        Returns:
            是否成功斷開
        """
        try:
            if not self.bluetooth_thread:
                self.gui.log_message("沒有連接的設備")
                return False
            
            # 在線程中運行斷開連接
            result_queue = queue.Queue()
            
            def run_disconnect_in_thread():
                try:
                    # 創建新的事件循環
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # 運行斷開連接
                    result = new_loop.run_until_complete(self.bluetooth_thread.disconnect())
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    new_loop.close()
            
            # 在後台線程中運行斷開連接
            disconnect_thread = threading.Thread(target=run_disconnect_in_thread, daemon=True)
            disconnect_thread.start()
            
            # 等待結果（最多等待5秒）
            try:
                status, result = result_queue.get(timeout=5)
                if status == 'error':
                    self.gui.log_message(f"❌ 斷開連接失敗: {result}")
                    return False
                return True
            except queue.Empty:
                self.gui.log_message("❌ 斷開連接超時")
                return False
            
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
        """設備找到回調（修復版本，支持多設備）"""
        try:
            # 更新設備列表
            if hasattr(self.gui, 'device_combo'):
                # 檢查是否已經存在該設備
                device_exists = False
                for i in range(self.gui.device_combo.count()):
                    if self.gui.device_combo.itemData(i) == address:
                        device_exists = True
                        break
                
                # 如果設備不存在，添加到列表中
                if not device_exists:
                    device_name = f"{self.target_name_prefix}-{address[-8:]} ({address})"
                    self.gui.device_combo.addItem(device_name, address)
                    
                    # 如果是第一個設備，清空"請先掃描設備"選項
                    if self.gui.device_combo.count() == 2 and self.gui.device_combo.itemText(0) == "請先掃描設備":
                        self.gui.device_combo.removeItem(0)
            
            # 啟用連接按鈕
            if hasattr(self.gui, 'connect_button'):
                self.gui.connect_button.setEnabled(True)
            
            self.gui.log_message(f"找到設備: {address}")
            
        except Exception as e:
            self.gui.log_message(f"處理設備找到事件時發生錯誤: {e}")
    
    def _on_connection_status(self, connected: bool, message: str):
        """連接狀態回調（修復版本）"""
        try:
            # 調用連線頁面的狀態更新方法
            if hasattr(self.gui, 'update_connection_status'):
                self.gui.update_connection_status(connected, message)
            
            # 直接更新主GUI的狀態橫幅
            if hasattr(self.gui, 'status_label'):
                if connected:
                    self.gui.status_label.setText("🟢 SYSTEM STATUS: CONNECTED & READY")
                    self.gui.status_label.setStyleSheet("""
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
                    self.gui.status_label.setText("🔴 SYSTEM STATUS: DISCONNECTED")
                    self.gui.status_label.setStyleSheet("""
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
            
            # 記錄日誌
            self.gui.log_message(message)
            
        except Exception as e:
            self.gui.log_message(f"處理連接狀態事件時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
    
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

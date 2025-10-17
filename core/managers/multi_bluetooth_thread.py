"""
四台發球機藍牙線程

這個模組擴展了 DualBluetoothThread 功能，支援：
- 四台設備並行管理
- 設備識別和分類
- 獨立發球控制
- 連接狀態監控
"""

import asyncio
import time
from typing import Optional, Dict, List, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from bleak import BleakScanner, BleakClient
from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params, get_area_params
from .dual_bluetooth_thread import DualBluetoothThread


class MultiBluetoothThread(DualBluetoothThread):
    """四台發球機藍牙線程類別"""
    
    # 信號定義（繼承父類並添加新的）
    device_found = pyqtSignal(str, str)  # address, machine_id
    connection_status = pyqtSignal(str, bool, str)  # machine_id, connected, message
    shot_sent = pyqtSignal(str, str)  # machine_id, message
    error_occurred = pyqtSignal(str, str)  # machine_id, message
    multi_connection_status = pyqtSignal(bool, str)  # all_connected, message
    
    def __init__(self, machine_id: str = "unknown"):
        """
        初始化四台發球機藍牙線程
        
        Args:
            machine_id: 發球機ID ("machine_1", "machine_2", "machine_3", "machine_4")
        """
        # 將 machine_id 轉換為 machine_type 以兼容父類
        machine_type = self._convert_machine_id_to_type(machine_id)
        super().__init__(machine_type)
        
        self.machine_id = machine_id
        self.machine_type = machine_type  # 保持兼容性
        
        # 四台發球機特定設定
        self.max_retry_attempts = 3
        self.retry_delay = 2.0  # 重試延遲（秒）
        self.connection_timeout = 10.0  # 連接超時（秒）
        
        # 連接統計
        self.connection_attempts = 0
        self.last_connection_time = None
        self.last_error = None
        
        # 發球統計
        self.total_shots_sent = 0
        self.successful_shots = 0
        self.failed_shots = 0
    
    def _convert_machine_id_to_type(self, machine_id: str) -> str:
        """
        將機器ID轉換為機器類型（用於兼容父類）
        
        Args:
            machine_id: 機器ID
            
        Returns:
            機器類型
        """
        if machine_id in ["machine_1", "machine_2"]:
            return "left"  # 使用left類型
        elif machine_id in ["machine_3", "machine_4"]:
            return "right"  # 使用right類型
        else:
            return "unknown"
    
    async def connect_device(self, address: str, timeout: float = None) -> bool:
        """
        連接發球機設備（擴展版本）
        
        Args:
            address: 設備地址
            timeout: 連接超時時間
            
        Returns:
            是否成功連接
        """
        if timeout is None:
            timeout = self.connection_timeout
        
        self.connection_attempts += 1
        self.last_connection_time = time.time()
        
        try:
            # 檢查是否已經連接
            if self.is_connected and self.device_address == address:
                self.connection_status.emit(
                    self.machine_id, 
                    True, 
                    f"已連接到 {self.device_name} ({address})"
                )
                return True
            
            # 如果連接到不同設備，先斷開
            if self.is_connected:
                await self.disconnect()
            
            # 實際藍牙連接
            self.client = BleakClient(address)
            
            # 使用超時連接
            await asyncio.wait_for(self.client.connect(), timeout=timeout)
            self.is_connected = self.client.is_connected
            
            if self.is_connected:
                # 獲取設備名稱
                try:
                    device_name_bytes = await self.client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                    self.device_name = device_name_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    self.device_name = f"{self.target_name_prefix}-{address[-8:]}"
                
                self.device_address = address
                self.last_error = None
                
                self.connection_status.emit(
                    self.machine_id, 
                    True, 
                    f"已連接到 {self.device_name} ({address})"
                )
                return True
            else:
                error_msg = "連接失敗"
                self.last_error = error_msg
                self.connection_status.emit(self.machine_id, False, error_msg)
                return False
                
        except asyncio.TimeoutError:
            error_msg = f"連接超時 ({timeout}秒)"
            self.last_error = error_msg
            self.connection_status.emit(self.machine_id, False, error_msg)
            return False
        except Exception as e:
            error_msg = f"連接錯誤: {e}"
            self.last_error = error_msg
            self.connection_status.emit(self.machine_id, False, error_msg)
            return False
    
    async def disconnect(self) -> bool:
        """
        斷開發球機連接（擴展版本）
        
        Returns:
            是否成功斷開
        """
        try:
            if self.client and self.is_connected:
                await self.client.disconnect()
            
            self.is_connected = False
            self.client = None
            self.device_address = None
            self.device_name = None
            
            self.connection_status.emit(
                self.machine_id, 
                False, 
                "已斷開連接"
            )
            return True
            
        except Exception as e:
            self.connection_status.emit(
                self.machine_id, 
                False, 
                f"斷開連接錯誤: {e}"
            )
            return False
    
    async def send_shot(self, area_section: str, machine_specific: bool = False) -> bool:
        """
        發送發球指令（擴展版本）
        
        Args:
            area_section: 發球區域代碼 (如 "sec1_1", "sec1_2")
            machine_specific: 是否使用機器特定參數
            
        Returns:
            是否成功發送
        """
        try:
            # 檢查發球冷卻時間
            current_time = time.time()
            if current_time - self.last_shot_time < self.shot_cooldown:
                try:
                    await asyncio.sleep(self.shot_cooldown - (current_time - self.last_shot_time))
                except RuntimeError as e:
                    if "no running event loop" in str(e):
                        time.sleep(self.shot_cooldown - (current_time - self.last_shot_time))
                    else:
                        raise
            
            # 選擇參數來源
            if machine_specific and self.machine_id in ["machine_1", "machine_2", "machine_3", "machine_4"]:
                # 使用機器特定參數
                machine_type_key = f"{self.machine_id}_machine"
                params = get_area_params(area_section, machine_type_key, self.area_file_path)
            else:
                # 使用通用參數
                params = get_area_params(area_section, "section", self.area_file_path)
            
            if not params:
                self.error_occurred.emit(self.machine_id, f"❌ 找不到區域 {area_section} 的參數")
                self.failed_shots += 1
                return False
            
            # 檢查連接狀態
            if not self.client or not self.is_connected:
                self.error_occurred.emit(self.machine_id, f"❌ 設備未連接")
                self.failed_shots += 1
                return False
            
            # 創建發球指令
            command = create_shot_command(
                params['speed'],
                params['horizontal_angle'],
                params['vertical_angle'],
                params['height']
            )
            
            # 發送指令
            try:
                await self.client.write_gatt_char(self.write_char_uuid, command)
                
                # 更新統計
                self.total_shots_sent += 1
                self.successful_shots += 1
                self.last_shot_time = time.time()
                
                self.shot_sent.emit(
                    self.machine_id, 
                    f"發球成功: {area_section} (速度:{params['speed']}, 水平:{params['horizontal_angle']}, 垂直:{params['vertical_angle']}, 高度:{params['height']})"
                )
                return True
                
            except Exception as e:
                self.failed_shots += 1
                self.error_occurred.emit(self.machine_id, f"❌ 發送發球指令失敗: {e}")
                return False
                
        except Exception as e:
            self.failed_shots += 1
            self.error_occurred.emit(self.machine_id, f"❌ 發球過程錯誤: {e}")
            return False
    
    async def send_continuous_shots(self, area_sections: List[str], interval: float, 
                                  count: int = -1, machine_specific: bool = False) -> bool:
        """
        發送連續發球指令
        
        Args:
            area_sections: 發球區域代碼列表
            interval: 發球間隔（秒）
            count: 發球次數（-1表示無限）
            machine_specific: 是否使用機器特定參數
            
        Returns:
            是否成功開始連續發球
        """
        try:
            if not self.is_connected:
                self.error_occurred.emit(self.machine_id, "❌ 設備未連接，無法開始連續發球")
                return False
            
            if not area_sections:
                self.error_occurred.emit(self.machine_id, "❌ 沒有指定發球區域")
                return False
            
            self.shot_sent.emit(
                self.machine_id, 
                f"開始連續發球: {len(area_sections)} 個區域, 間隔 {interval}s, 次數 {count if count > 0 else '無限'}"
            )
            
            sent_count = 0
            while count == -1 or sent_count < count:
                for area_section in area_sections:
                    if count > 0 and sent_count >= count:
                        break
                    
                    success = await self.send_shot(area_section, machine_specific)
                    if not success:
                        self.error_occurred.emit(self.machine_id, f"❌ 連續發球中斷: {area_section}")
                        return False
                    
                    sent_count += 1
                    
                    # 等待間隔時間
                    if interval > 0:
                        await asyncio.sleep(interval)
            
            self.shot_sent.emit(self.machine_id, f"連續發球完成: 共發送 {sent_count} 球")
            return True
            
        except Exception as e:
            self.error_occurred.emit(self.machine_id, f"❌ 連續發球錯誤: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, any]:
        """
        獲取連接信息
        
        Returns:
            連接信息字典
        """
        return {
            "machine_id": self.machine_id,
            "machine_type": self.machine_type,
            "is_connected": self.is_connected,
            "device_address": self.device_address,
            "device_name": self.device_name,
            "connection_attempts": self.connection_attempts,
            "last_connection_time": self.last_connection_time,
            "last_error": self.last_error,
            "total_shots_sent": self.total_shots_sent,
            "successful_shots": self.successful_shots,
            "failed_shots": self.failed_shots,
            "success_rate": (self.successful_shots / max(1, self.total_shots_sent)) * 100
        }
    
    def reset_statistics(self):
        """重置統計信息"""
        self.connection_attempts = 0
        self.last_connection_time = None
        self.last_error = None
        self.total_shots_sent = 0
        self.successful_shots = 0
        self.failed_shots = 0
    
    def set_shot_cooldown(self, cooldown: float):
        """
        設定發球冷卻時間
        
        Args:
            cooldown: 冷卻時間（秒）
        """
        self.shot_cooldown = max(0.1, cooldown)  # 最小0.1秒
    
    def set_connection_timeout(self, timeout: float):
        """
        設定連接超時時間
        
        Args:
            timeout: 超時時間（秒）
        """
        self.connection_timeout = max(1.0, timeout)  # 最小1秒
    
    def is_healthy(self) -> bool:
        """
        檢查設備健康狀態
        
        Returns:
            是否健康
        """
        if not self.is_connected:
            return False
        
        # 檢查成功率
        if self.total_shots_sent > 10:  # 至少發送10球後才檢查成功率
            success_rate = (self.successful_shots / self.total_shots_sent) * 100
            if success_rate < 80:  # 成功率低於80%認為不健康
                return False
        
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        status = "已連接" if self.is_connected else "未連接"
        return f"MultiBluetoothThread({self.machine_id}, {status})"
    
    def __repr__(self) -> str:
        """詳細字符串表示"""
        return (f"MultiBluetoothThread(machine_id='{self.machine_id}', "
                f"is_connected={self.is_connected}, "
                f"device_address='{self.device_address}', "
                f"total_shots={self.total_shots_sent})")

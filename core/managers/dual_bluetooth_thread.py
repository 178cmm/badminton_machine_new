"""
雙發球機藍牙線程

這個模組擴展了基本的 BluetoothThread 功能，支援：
- 多設備並行管理
- 設備識別和分類
- 協調發球控制
- 連接狀態監控
"""

import asyncio
import time
from typing import Optional, Dict, List, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from bleak import BleakScanner, BleakClient
from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params, get_area_params


class DualBluetoothThread(QThread):
    """雙發球機藍牙線程類別"""
    
    # 信號定義
    device_found = pyqtSignal(str, str)  # address, machine_type
    connection_status = pyqtSignal(str, bool, str)  # machine_type, connected, message
    shot_sent = pyqtSignal(str, str)  # machine_type, message
    error_occurred = pyqtSignal(str, str)  # machine_type, message
    dual_connection_status = pyqtSignal(bool, str)  # both_connected, message
    
    def __init__(self, machine_type: str = "unknown"):
        """
        初始化雙發球機藍牙線程
        
        Args:
            machine_type: 發球機類型 ("left", "right", "unknown")
        """
        super().__init__()
        self.machine_type = machine_type
        self.client: Optional[BleakClient] = None
        self.is_connected = False
        self._scanning = False
        
        # 藍牙通信設定
        self.target_name_prefix = "YX-BE241"
        self.write_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"
        self.area_file_path = "area.json"
        
        # 設備信息
        self.device_address: Optional[str] = None
        self.device_name: Optional[str] = None
        
        # 發球狀態
        self.last_shot_time = 0
        self.shot_cooldown = 0.5  # 發球冷卻時間（秒）
    
    async def find_device(self, timeout: float = 5.0) -> Optional[str]:
        """
        尋找發球機設備（優化版本）
        
        Args:
            timeout: 掃描超時時間（減少到5秒）
            
        Returns:
            找到的設備地址，如果未找到則返回 None
        """
        if self._scanning:
            self.error_occurred.emit(self.machine_type, "掃描已在進行中")
            return None
        
        self._scanning = True
        try:
            # 優化：減少掃描超時時間
            devices = await BleakScanner.discover(timeout=timeout)
            
            for device in devices or []:
                try:
                    name = getattr(device, 'name', None)
                    if name and name.startswith(self.target_name_prefix):
                        # 識別設備類型
                        detected_type = self._identify_machine_type(name, device.address)
                        
                        # 如果指定了機器類型，只返回匹配的設備
                        if self.machine_type == "unknown" or detected_type == self.machine_type:
                            self.device_found.emit(device.address, detected_type)
                            return device.address
                            
                except Exception:
                    continue
            
            self.error_occurred.emit(self.machine_type, "未找到匹配的發球機設備")
            return None
            
        except Exception as e:
            self.error_occurred.emit(self.machine_type, f"掃描設備失敗: {e}")
            return None
        finally:
            self._scanning = False
    
    def _identify_machine_type(self, name: str, address: str) -> str:
        """
        識別發球機類型
        
        Args:
            name: 設備名稱
            address: 設備地址
            
        Returns:
            發球機類型 ("left", "right")
        """
        # 方案1: 通過設備名稱識別
        name_upper = name.upper()
        if 'L' in name_upper or 'LEFT' in name_upper:
            return "left"
        elif 'R' in name_upper or 'RIGHT' in name_upper:
            return "right"
        
        # 方案2: 通過 MAC 地址識別
        try:
            last_char = address[-1]
            if last_char.isdigit():
                return "left" if int(last_char) % 2 == 0 else "right"
            else:
                return "left" if ord(last_char) % 2 == 0 else "right"
        except Exception:
            return "left"  # 預設為左發球機
    
    async def connect_device(self, address: str) -> bool:
        """
        連接到指定的藍牙設備
        
        Args:
            address: 設備地址
            
        Returns:
            是否成功連接
        """
        try:
            self.device_address = address
            
            # 檢查是否為模擬地址（用於測試）
            if address.startswith("AA:BB:CC:DD:EE:"):
                # 模擬連接成功
                self.is_connected = True
                self.device_name = f"{self.target_name_prefix}-{address[-8:]}"
                
                self.connection_status.emit(
                    self.machine_type, 
                    True, 
                    f"已連接到 {self.device_name} ({address}) [模擬模式]"
                )
                return True
            
            # 實際藍牙連接
            self.client = BleakClient(address)
            
            await self.client.connect()
            self.is_connected = self.client.is_connected
            
            if self.is_connected:
                # 獲取設備名稱
                try:
                    self.device_name = await self.client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                    self.device_name = self.device_name.decode('utf-8', errors='ignore')
                except Exception:
                    self.device_name = f"{self.target_name_prefix}-{address[-8:]}"
                
                self.connection_status.emit(
                    self.machine_type, 
                    True, 
                    f"已連接到 {self.device_name} ({address})"
                )
                return True
            else:
                self.connection_status.emit(self.machine_type, False, "連接失敗")
                return False
                
        except Exception as e:
            self.is_connected = False
            self.connection_status.emit(self.machine_type, False, f"連接錯誤: {e}")
            return False
    
    async def send_shot(self, area_section: str, machine_specific: bool = False) -> bool:
        """
        發送發球指令
        
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
                await asyncio.sleep(self.shot_cooldown - (current_time - self.last_shot_time))
            
            # 選擇參數來源
            if machine_specific and self.machine_type in ["left", "right"]:
                # 使用機器特定參數
                machine_type_key = f"{self.machine_type}_machine"
                params = get_area_params(area_section, machine_type_key, self.area_file_path)
            else:
                # 使用通用參數
                params = get_area_params(area_section, "section", self.area_file_path)
            
            if not params:
                self.error_occurred.emit(self.machine_type, f"找不到區域 {area_section} 的參數")
                return False
            
            # 檢查連接狀態
            if not self.client or not self.is_connected:
                self.error_occurred.emit(self.machine_type, "設備未連接")
                return False
            
            # 創建發球指令
            command = create_shot_command(
                params['speed'],
                params['horizontal_angle'],
                params['vertical_angle'],
                params['height']
            )
            
            # 發送指令
            await self.client.write_gatt_char(self.write_char_uuid, command)
            
            # 更新發球時間
            self.last_shot_time = time.time()
            
            # 發送成功信號
            self.shot_sent.emit(self.machine_type, f"已發送 {area_section}")
            return True
            
        except Exception as e:
            self.error_occurred.emit(self.machine_type, f"發送指令失敗: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """
        斷開連接
        
        Returns:
            是否成功斷開
        """
        try:
            if self.client and self.is_connected:
                await self.client.disconnect()
                self.is_connected = False
                self.connection_status.emit(self.machine_type, False, "已斷開連接")
                return True
            else:
                self.connection_status.emit(self.machine_type, False, "沒有連接的設備")
                return False
                
        except Exception as e:
            self.error_occurred.emit(self.machine_type, f"斷開連接失敗: {e}")
            return False
    
    def get_device_info(self) -> Dict[str, str]:
        """
        獲取設備信息
        
        Returns:
            設備信息字典
        """
        return {
            'machine_type': self.machine_type,
            'address': self.device_address or "未知",
            'name': self.device_name or "未知",
            'connected': str(self.is_connected)
        }
    
    async def wait_for_shot_completion(self, timeout: float = 5.0) -> bool:
        """
        等待發球完成
        
        Args:
            timeout: 超時時間
            
        Returns:
            是否在超時前完成
        """
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if not self.is_connected:
                    return False
                await asyncio.sleep(0.1)
            return True
        except Exception:
            return False


class DualMachineCoordinator:
    """雙發球機協調器"""
    
    def __init__(self, left_thread: DualBluetoothThread, right_thread: DualBluetoothThread):
        """
        初始化雙發球機協調器
        
        Args:
            left_thread: 左發球機線程
            right_thread: 右發球機線程
        """
        self.left_thread = left_thread
        self.right_thread = right_thread
        self.sync_tolerance = 0.1  # 同步容差（秒）
    
    async def send_coordinated_shot(self, left_area: str, right_area: str, 
                                  coordination_mode: str = "alternate", interval: float = 0.5, count: int = 1) -> bool:
        """
        發送協調發球指令
        
        Args:
            left_area: 左發球機發球區域
            right_area: 右發球機發球區域
            coordination_mode: 協調模式 ("alternate", "simultaneous")
            interval: 模式相關的間隔時間（秒）。對 alternate 生效
            count: 發球數（球），alternate為總球數，simultaneous為每台發球數
            
        Returns:
            是否成功發送
        """
        try:
            if not self.left_thread.is_connected or not self.right_thread.is_connected:
                return False
            
            if coordination_mode == "alternate":
                return await self._alternate_shots(left_area, right_area, interval=interval, count=count)
                
            elif coordination_mode == "simultaneous":
                return await self._simultaneous_shots(left_area, right_area, count=count)
            
            return False
            
        except Exception as e:
            print(f"❌ 協調發球失敗: {e}")
            return False
    
    async def _alternate_shots(self, left_area: str, right_area: str, interval: float, count: int) -> bool:
        """交替發球：左-右交替，總共發 count 球，發送命令後立即等待間隔時間"""
        try:
            total_shots = max(1, count)
            for i in range(total_shots):
                if i % 2 == 0:  # 偶數次發左球
                    result = await self.left_thread.send_shot(left_area)
                    machine_name = "左發球機"
                else:  # 奇數次發右球
                    result = await self.right_thread.send_shot(right_area)
                    machine_name = "右發球機"
                
                if not result:
                    print(f"❌ {machine_name} 發球失敗")
                    return False
                
                print(f"✅ {machine_name} 發球命令已發送 ({i+1}/{total_shots})")
                
                # 如果不是最後一球，發送命令後立即等待間隔時間（不等待球實際發出）
                if i < total_shots - 1:
                    print(f"⏱️ 等待間隔時間: {interval}秒")
                    await asyncio.sleep(max(0.0, interval))
            return True
        except Exception as e:
            print(f"❌ 交替發球失敗: {e}")
            return False
    
    async def _simultaneous_shots(self, left_area: str, right_area: str, count: int) -> bool:
        """同時發球：左右發球機同時各發 count 球，總共發 count*2 球"""
        try:
            total_shots = max(1, count)
            for shot_num in range(total_shots):
                print(f"🎯 同時發球第 {shot_num + 1} 組")
                start_time = time.time()
                
                # 同時發送命令給兩台發球機
                print(f"🔍 準備同時發送: 左發球機({left_area}) + 右發球機({right_area})")
                print(f"🔍 左發球機線程: {self.left_thread.machine_type}, 地址: {self.left_thread.device_address}")
                print(f"🔍 右發球機線程: {self.right_thread.machine_type}, 地址: {self.right_thread.device_address}")
                
                left_task = self.left_thread.send_shot(left_area)
                right_task = self.right_thread.send_shot(right_area)
                left_result, right_result = await asyncio.gather(left_task, right_task)
                
                sync_time = time.time() - start_time
                print(f"⚡ 同步發送時間: {sync_time:.3f}s")
                
                if sync_time > self.sync_tolerance:
                    print(f"⚠️ 同步時間超過容差: {sync_time:.3f}s > {self.sync_tolerance}s")
                
                if not (left_result and right_result):
                    print(f"❌ 同時發球失敗: 左={left_result}, 右={right_result}")
                    return False
                
                print(f"✅ 同時發球成功: 左({left_area}) + 右({right_area})")
            return True
        except Exception as e:
            print(f"❌ 同時發球失敗: {e}")
            return False
    
    
    def is_both_connected(self) -> bool:
        """檢查兩台發球機是否都已連接"""
        return self.left_thread.is_connected and self.right_thread.is_connected
    
    def get_connection_status(self) -> Dict[str, bool]:
        """獲取連接狀態"""
        return {
            'left_connected': self.left_thread.is_connected,
            'right_connected': self.right_thread.is_connected,
            'both_connected': self.is_both_connected()
        }


def create_dual_bluetooth_thread(machine_type: str) -> DualBluetoothThread:
    """
    創建雙發球機藍牙線程的工廠函數
    
    Args:
        machine_type: 發球機類型 ("left", "right")
        
    Returns:
        DualBluetoothThread 實例
    """
    return DualBluetoothThread(machine_type)


def create_dual_machine_coordinator(left_thread: DualBluetoothThread, 
                                  right_thread: DualBluetoothThread) -> DualMachineCoordinator:
    """
    創建雙發球機協調器的工廠函數
    
    Args:
        left_thread: 左發球機線程
        right_thread: 右發球機線程
        
    Returns:
        DualMachineCoordinator 實例
    """
    return DualMachineCoordinator(left_thread, right_thread)


import asyncio
from bleak import BleakScanner, BleakClient
from PyQt5.QtCore import QThread, pyqtSignal
from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params

# 藍牙通信設定
# 設定目標設備名稱前綴和寫入特徵UUID
# 定義區域和訓練計畫的檔案路徑

target_name_prefix = "YX-BE241"
write_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"
AREA_FILE_PATH = "area.json"
PROGRAMS_FILE_PATH = "training_programs.json"

class BluetoothThread(QThread):
    """藍牙通信線程"""
    device_found = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)
    shot_sent = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.is_connected = False
        self._scanning = False
        self.machine_position = "center"  # 預設為中央位置
    
    def set_machine_position(self, position: str):
        """
        設定發球機位置
        
        Args:
            position: 發球機位置 ("center", "left", "right")
        """
        if position in ["center", "left", "right"]:
            self.machine_position = position
        else:
            self.error_occurred.emit(f"無效的發球機位置: {position}")
    
    def get_machine_position(self) -> str:
        """
        獲取當前發球機位置
        
        Returns:
            當前發球機位置
        """
        return self.machine_position
        
    async def find_device(self):
        """尋找發球機設備（加入超時及重試，避免事件迴圈衝突）"""
        if self._scanning:
            self.error_occurred.emit("掃描已在進行中")
            return None
        self._scanning = True
        try:
            max_scans = 3
            for _ in range(max_scans):
                try:
                    devices = await BleakScanner.discover(timeout=5.0)
                except TypeError:
                    # 某些平台/版本不支援 timeout 參數
                    devices = await BleakScanner.discover()

                for device in devices or []:
                    try:
                        name = getattr(device, 'name', None)
                        if name and name.startswith(target_name_prefix):
                            self.device_found.emit(device.address)
                            return device.address
                    except Exception:
                        # 忽略單一設備屬性解析錯誤
                        continue

                await asyncio.sleep(1.5)

            # 後備方案：使用掃描器持續監聽回呼（對 macOS 較穩定）
            try:
                found_address = None
                def detection_callback(d):
                    nonlocal found_address
                    try:
                        if d and getattr(d, 'name', None) and d.name.startswith(target_name_prefix):
                            found_address = d.address
                    except Exception:
                        pass

                scanner = BleakScanner(detection_callback)
                await scanner.start()
                # 監聽 6 秒
                for _ in range(6):
                    if found_address:
                        break
                    await asyncio.sleep(1.0)
                await scanner.stop()
                if found_address:
                    self.device_found.emit(found_address)
                    return found_address
            except Exception:
                # 後備掃描也失敗則忽略，交由下方錯誤輸出
                pass

            self.error_occurred.emit("未找到發球機設備，請確認設備已開機並靠近電腦")
            return None
        except Exception as e:
            self.error_occurred.emit(f"掃描設備失敗: {e}")
            return None
        finally:
            self._scanning = False
    
    async def connect_device(self, address):
        """連接設備"""
        try:
            self.client = BleakClient(address)
            await self.client.connect()
            self.is_connected = self.client.is_connected
            if self.is_connected:
                self.connection_status.emit(True, f"已連接到 {address}")
            else:
                self.is_connected = False
                self.connection_status.emit(False, "連接失敗")
        except Exception as e:
            self.is_connected = False
            self.connection_status.emit(False, f"連接錯誤: {e}")
    
    async def send_shot(self, area_section):
        """發送發球指令"""
        try:
            area_data = read_data_from_json(AREA_FILE_PATH)
            if not area_data:
                self.error_occurred.emit("無法載入發球區域數據")
                return False
            
            # 根據發球機位置選擇參數來源
            position_key = f"{self.machine_position}_machine"
            if position_key in area_data and area_section in area_data[position_key]:
                params_str = area_data[position_key][area_section]
            elif area_section in area_data.get("section", {}):
                # 回退到通用參數
                params_str = area_data["section"][area_section]
            else:
                self.error_occurred.emit(f"找不到區域 {area_section} 的參數")
                return False
            
            params = parse_area_params(params_str)
            
            if params and self.client and self.is_connected:
                command = create_shot_command(
                    params['speed'],
                    params['horizontal_angle'],
                    params['vertical_angle'],
                    params['height']
                )
                
                await self.client.write_gatt_char(write_char_uuid, command)
                self.shot_sent.emit(f"已發送 {area_section} (位置: {self.machine_position})")
                return True
            else:
                self.error_occurred.emit(f"無法發送 {area_section}")
                return False
        except Exception as e:
            self.error_occurred.emit(f"發送指令失敗: {e}")
            return False
    
    async def disconnect(self):
        """斷開連接"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            self.connection_status.emit(False, "已斷開連接")

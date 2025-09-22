"""
雙發球機藍牙連接管理器

這個模組負責管理雙發球機的藍牙連接邏輯，包括：
- 掃描和識別雙發球機設備
- 管理左右發球機的連接狀態
- 提供雙發球機協調控制功能
"""

import asyncio
import time
from typing import Optional, Dict, List, Tuple
from bluetooth import BluetoothThread
from .dual_bluetooth_thread import DualBluetoothThread, DualMachineCoordinator


class DualBluetoothManager:
    """雙發球機藍牙連接管理器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化雙發球機藍牙管理器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
        self.target_name_prefix = "YX-BE241"
        
        # 雙發球機連接管理
        self.left_machine: Optional[DualBluetoothThread] = None
        self.right_machine: Optional[DualBluetoothThread] = None
        self.machine_threads: Dict[str, DualBluetoothThread] = {}
        self.coordinator: Optional[DualMachineCoordinator] = None
        
        # 設備識別
        self.found_devices: List[Dict] = []
        self.device_identification_strategy = "mac_based"  # "name_based" 或 "mac_based"
        
        # 連接狀態監控
        self.connection_monitor_task = None
        self.monitor_interval = 5  # 監控間隔（秒）
        
        # 同步發球設定
        self.sync_tolerance = 0.1  # 同步容差（秒）
    
    async def scan_dual_devices(self) -> bool:
        """
        掃描雙發球機設備
        
        Returns:
            是否成功開始掃描
        """
        try:
            self.gui.log_message("🔍 開始掃描雙發球機...")
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'dual_scan_button'):
                self.gui.dual_scan_button.setEnabled(False)
                self.gui.dual_scan_button.setText("掃描中...")
            
            # 清空之前的設備列表
            self.found_devices.clear()
            
            # 開始掃描
            devices = await self._discover_devices()
            
            if devices:
                self.gui.log_message(f"✅ 找到 {len(devices)} 個發球機設備")
                await self._identify_machines(devices)
                return True
            else:
                self.gui.log_message("❌ 未找到發球機設備")
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ 掃描雙發球機失敗: {e}")
            return False
        finally:
            # 恢復 UI 狀態
            if hasattr(self.gui, 'dual_scan_button'):
                self.gui.dual_scan_button.setEnabled(True)
                self.gui.dual_scan_button.setText("🔍 掃描雙發球機")
    
    async def _discover_devices(self) -> List[Dict]:
        """
        發現發球機設備
        
        Returns:
            發現的設備列表
        """
        from bleak import BleakScanner
        
        devices = []
        try:
            # 掃描設備
            discovered = await BleakScanner.discover(timeout=10.0)
            
            for device in discovered or []:
                try:
                    name = getattr(device, 'name', None)
                    if name and name.startswith(self.target_name_prefix):
                        device_info = {
                            'name': name,
                            'address': device.address,
                            'rssi': getattr(device, 'rssi', 0)
                        }
                        devices.append(device_info)
                        self.gui.log_message(f"📱 發現設備: {name} ({device.address})")
                except Exception:
                    continue
                    
        except Exception as e:
            self.gui.log_message(f"❌ 設備發現失敗: {e}")
        
        return devices
    
    async def _identify_machines(self, devices: List[Dict]):
        """
        識別左右發球機
        
        Args:
            devices: 發現的設備列表
        """
        try:
            if len(devices) == 0:
                self.gui.log_message("❌ 沒有找到任何發球機設備")
                self.found_devices = []
                return
            elif len(devices) == 1:
                self.gui.log_message("⚠️ 只找到一台發球機")
                # 對於單一設備，提供選擇選項
                device = devices[0]
                device['machine_type'] = 'left'  # 預設為左發球機
                self.found_devices = devices
                self.gui.log_message("💡 提示：可以手動將設備設為左發球機或右發球機")
            else:
                # 多台設備，使用智能分配策略
                await self._smart_assign_devices(devices)
                
                # 檢查識別結果
                left_count = sum(1 for d in self.found_devices if d.get('machine_type') == 'left')
                right_count = sum(1 for d in self.found_devices if d.get('machine_type') == 'right')
                
                self.gui.log_message(f"📊 識別結果: 左發球機 {left_count} 台, 右發球機 {right_count} 台")
                
                # 如果識別結果不理想，提供重新分配選項
                if left_count == 0 or right_count == 0:
                    self.gui.log_message("⚠️ 識別結果不理想，建議手動調整設備分配")
            
            # 更新 UI 顯示
            self._update_device_ui()
            
        except Exception as e:
            self.gui.log_message(f"❌ 設備識別失敗: {e}")
            import traceback
            traceback.print_exc()
    
    async def _smart_assign_devices(self, devices: List[Dict]):
        """
        智能分配設備到左右發球機
        
        Args:
            devices: 發現的設備列表
        """
        try:
            # 首先嘗試通過名稱識別
            name_identified = []
            for device in devices:
                name = device['name'].upper()
                if 'L' in name or 'LEFT' in name:
                    device['machine_type'] = 'left'
                    name_identified.append(device)
                elif 'R' in name or 'RIGHT' in name:
                    device['machine_type'] = 'right'
                    name_identified.append(device)
            
            # 對於未通過名稱識別的設備，使用智能分配
            unidentified = [d for d in devices if d not in name_identified]
            
            if len(unidentified) >= 2:
                # 如果有兩台或以上未識別的設備，交替分配
                for i, device in enumerate(unidentified):
                    device['machine_type'] = 'left' if i % 2 == 0 else 'right'
                    self.gui.log_message(f"🤖 智能分配: {device['name']} -> {'左發球機' if i % 2 == 0 else '右發球機'}")
            elif len(unidentified) == 1:
                # 如果只有一台未識別的設備，檢查現有分配
                left_count = sum(1 for d in devices if d.get('machine_type') == 'left')
                right_count = sum(1 for d in devices if d.get('machine_type') == 'right')
                
                # 分配到數量較少的一邊
                if left_count <= right_count:
                    unidentified[0]['machine_type'] = 'left'
                    self.gui.log_message(f"🤖 智能分配: {unidentified[0]['name']} -> 左發球機")
                else:
                    unidentified[0]['machine_type'] = 'right'
                    self.gui.log_message(f"🤖 智能分配: {unidentified[0]['name']} -> 右發球機")
            
            self.found_devices = devices
            self.gui.log_message("✅ 智能設備分配完成")
            
        except Exception as e:
            self.gui.log_message(f"❌ 智能分配失敗: {e}")
            # 後備方案：簡單交替分配
            for i, device in enumerate(devices):
                device['machine_type'] = 'left' if i % 2 == 0 else 'right'
            self.found_devices = devices

    async def _identify_by_name(self, devices: List[Dict]):
        """通過設備名稱識別左右發球機"""
        for device in devices:
            name = device['name'].upper()
            if 'L' in name or 'LEFT' in name:
                device['machine_type'] = 'left'
            elif 'R' in name or 'RIGHT' in name:
                device['machine_type'] = 'right'
            else:
                # 如果名稱中沒有明確標識，使用 MAC 地址
                device['machine_type'] = self._identify_by_mac_address(device['address'])
        
        self.found_devices = devices
    
    async def _identify_by_mac(self, devices: List[Dict]):
        """通過 MAC 地址識別左右發球機"""
        for device in devices:
            device['machine_type'] = self._identify_by_mac_address(device['address'])
        
        self.found_devices = devices
    
    def _identify_by_mac_address(self, address: str) -> str:
        """
        通過 MAC 地址識別發球機類型
        
        Args:
            address: MAC 地址
            
        Returns:
            'left' 或 'right'
        """
        try:
            # 使用 MAC 地址的最後一位數字來區分
            last_char = address[-1]
            if last_char.isdigit():
                return 'left' if int(last_char) % 2 == 0 else 'right'
            else:
                # 如果是字母，使用 ASCII 值
                return 'left' if ord(last_char) % 2 == 0 else 'right'
        except Exception:
            # 預設為左發球機
            return 'left'
    
    def _update_device_ui(self):
        """更新設備選擇 UI"""
        try:
            # 檢查 UI 組件是否存在且不為 None
            if (not hasattr(self.gui, 'left_device_combo') or self.gui.left_device_combo is None or
                not hasattr(self.gui, 'right_device_combo') or self.gui.right_device_combo is None):
                self.gui.log_message("⚠️ UI 組件未初始化，跳過 UI 更新")
                return
            
            # 清空現有選項
            self.gui.left_device_combo.clear()
            self.gui.right_device_combo.clear()
            
            # 統計左右發球機數量
            left_devices = []
            right_devices = []
            
            for device in self.found_devices:
                device_name = f"{device['name']} ({device['address']})"
                machine_type = device.get('machine_type', 'unknown')
                
                if machine_type == 'left':
                    left_devices.append((device_name, device['address']))
                elif machine_type == 'right':
                    right_devices.append((device_name, device['address']))
            
            # 添加設備到對應的下拉選單
            for device_name, address in left_devices:
                self.gui.left_device_combo.addItem(device_name, address)
            
            for device_name, address in right_devices:
                self.gui.right_device_combo.addItem(device_name, address)
            
            # 如果沒有找到對應類型的設備，添加提示信息和可用設備
            if not left_devices:
                self.gui.left_device_combo.addItem("未找到左發球機", None)
                # 添加其他可用設備作為選項
                for device in self.found_devices:
                    if device.get('machine_type') != 'left':
                        device_name = f"{device['name']} ({device['address']}) - 可設為左發球機"
                        self.gui.left_device_combo.addItem(device_name, device['address'])
            
            if not right_devices:
                self.gui.right_device_combo.addItem("未找到右發球機", None)
                # 添加其他可用設備作為選項
                for device in self.found_devices:
                    if device.get('machine_type') != 'right':
                        device_name = f"{device['name']} ({device['address']}) - 可設為右發球機"
                        self.gui.right_device_combo.addItem(device_name, device['address'])
            
            # 記錄統計信息
            self.gui.log_message(f"📊 設備統計: 左發球機 {len(left_devices)} 台, 右發球機 {len(right_devices)} 台")
            
            # 啟用連接按鈕（需要至少一台左發球機和一台右發球機）
            if hasattr(self.gui, 'connect_dual_button'):
                can_connect = len(left_devices) > 0 and len(right_devices) > 0
                self.gui.connect_dual_button.setEnabled(can_connect)
                
                if can_connect:
                    self.gui.log_message("✅ 雙發球機準備就緒，可以連接")
                else:
                    self.gui.log_message("⚠️ 需要至少一台左發球機和一台右發球機才能連接")
                
        except Exception as e:
            self.gui.log_message(f"❌ 更新設備 UI 失敗: {e}")
            import traceback
            traceback.print_exc()
    
    async def connect_dual_machines(self) -> bool:
        """
        連接雙發球機
        
        Returns:
            是否成功連接
        """
        try:
            self.gui.log_message("🔗 開始連接雙發球機...")
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'connect_dual_button'):
                self.gui.connect_dual_button.setEnabled(False)
                self.gui.connect_dual_button.setText("連接中...")
            
            # 獲取用戶選擇的設備
            left_address = None
            right_address = None
            
            if hasattr(self.gui, 'left_device_combo'):
                left_address = self.gui.left_device_combo.currentData()
            if hasattr(self.gui, 'right_device_combo'):
                right_address = self.gui.right_device_combo.currentData()
            
            if not left_address or not right_address:
                self.gui.log_message("❌ 請選擇左右發球機設備")
                return False
            
            # 檢查是否為同一設備（不允許左右發球機使用同一設備）
            if left_address == right_address:
                self.gui.log_message("❌ 左右發球機不能使用同一設備")
                return False
            
            # 找到對應的設備信息，如果找不到則創建新的設備信息
            left_device = next((d for d in self.found_devices if d['address'] == left_address), None)
            right_device = next((d for d in self.found_devices if d['address'] == right_address), None)
            
            # 如果找不到設備信息，創建新的設備信息
            if not left_device:
                left_device = {
                    'name': f"YX-BE241-{left_address[-8:]}",
                    'address': left_address,
                    'machine_type': 'left'
                }
                self.found_devices.append(left_device)
                self.gui.log_message(f"📱 創建左發球機設備信息: {left_device['name']}")
            
            if not right_device:
                right_device = {
                    'name': f"YX-BE241-{right_address[-8:]}",
                    'address': right_address,
                    'machine_type': 'right'
                }
                self.found_devices.append(right_device)
                self.gui.log_message(f"📱 創建右發球機設備信息: {right_device['name']}")
            
            # 更新設備類型（根據用戶選擇）
            left_device['machine_type'] = 'left'
            right_device['machine_type'] = 'right'
            
            # 創建藍牙線程
            self.left_machine = DualBluetoothThread("left")
            self.right_machine = DualBluetoothThread("right")
            
            # 設置信號連接
            self._setup_machine_signals(self.left_machine, "左發球機")
            self._setup_machine_signals(self.right_machine, "右發球機")
            
            # 並行連接
            left_task = self.left_machine.connect_device(left_device['address'])
            right_task = self.right_machine.connect_device(right_device['address'])
            
            left_result, right_result = await asyncio.gather(
                left_task, right_task, return_exceptions=True
            )
            
            # 檢查連接結果
            left_connected = not isinstance(left_result, Exception) and self.left_machine.is_connected
            right_connected = not isinstance(right_result, Exception) and self.right_machine.is_connected
            
            if left_connected and right_connected:
                self.gui.log_message("✅ 雙發球機連接成功！")
                
                # 存儲機器線程
                self.machine_threads = {
                    'left': self.left_machine,
                    'right': self.right_machine
                }
                
                # 創建協調器
                self.coordinator = DualMachineCoordinator(self.left_machine, self.right_machine)
                
                # 設置到主 GUI
                self.gui.left_bluetooth_thread = self.left_machine
                self.gui.right_bluetooth_thread = self.right_machine
                self.gui.dual_machine_mode = True
                
                # 開始連接監控
                self._start_connection_monitoring()
                
                return True
            else:
                self.gui.log_message("❌ 雙發球機連接失敗")
                if not left_connected:
                    self.gui.log_message(f"❌ 左發球機連接失敗: {left_result}")
                if not right_connected:
                    self.gui.log_message(f"❌ 右發球機連接失敗: {right_result}")
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ 連接雙發球機失敗: {e}")
            return False
        finally:
            # 恢復 UI 狀態
            if hasattr(self.gui, 'connect_dual_button'):
                self.gui.connect_dual_button.setEnabled(True)
                self.gui.connect_dual_button.setText("🔗 連接雙發球機")
    
    def _setup_machine_signals(self, machine_thread: DualBluetoothThread, machine_name: str):
        """設置發球機信號連接"""
        try:
            machine_thread.connection_status.connect(
                lambda connected, msg: self._on_machine_connection_status(machine_name, connected, msg)
            )
            machine_thread.shot_sent.connect(
                lambda msg: self._on_machine_shot_sent(machine_name, msg)
            )
            machine_thread.error_occurred.connect(
                lambda msg: self._on_machine_error(machine_name, msg)
            )
        except Exception as e:
            self.gui.log_message(f"❌ 設置 {machine_name} 信號失敗: {e}")
    
    def _on_machine_connection_status(self, machine_name: str, connected: bool, message: str):
        """發球機連接狀態回調"""
        try:
            status_icon = "✅" if connected else "❌"
            self.gui.log_message(f"{status_icon} {machine_name}: {message}")
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'update_dual_connection_status'):
                self.gui.update_dual_connection_status(machine_name, connected, message)
                
        except Exception as e:
            self.gui.log_message(f"❌ 處理 {machine_name} 連接狀態失敗: {e}")
    
    def _on_machine_shot_sent(self, machine_name: str, message: str):
        """發球機發球回調"""
        try:
            self.gui.log_message(f"🎯 {machine_name}: {message}")
        except Exception as e:
            print(f"處理 {machine_name} 發球事件時發生錯誤: {e}")
    
    def _on_machine_error(self, machine_name: str, message: str):
        """發球機錯誤回調"""
        try:
            self.gui.log_message(f"❌ {machine_name} 錯誤: {message}")
        except Exception as e:
            print(f"處理 {machine_name} 錯誤事件時發生錯誤: {e}")
    
    async def disconnect_dual_machines(self) -> bool:
        """
        斷開雙發球機連接
        
        Returns:
            是否成功斷開
        """
        try:
            self.gui.log_message("🔌 斷開雙發球機連接...")
            
            # 停止連接監控
            self._stop_connection_monitoring()
            
            # 並行斷開連接
            tasks = []
            if self.left_machine and self.left_machine.is_connected:
                tasks.append(self.left_machine.disconnect())
            if self.right_machine and self.right_machine.is_connected:
                tasks.append(self.right_machine.disconnect())
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # 清理資源
            self.left_machine = None
            self.right_machine = None
            self.machine_threads.clear()
            
            # 更新主 GUI
            self.gui.left_bluetooth_thread = None
            self.gui.right_bluetooth_thread = None
            self.gui.dual_machine_mode = False
            
            self.gui.log_message("✅ 雙發球機已斷開連接")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 斷開雙發球機失敗: {e}")
            return False
    
    def _start_connection_monitoring(self):
        """開始連接監控"""
        try:
            if self.connection_monitor_task and not self.connection_monitor_task.done():
                self.connection_monitor_task.cancel()
            
            self.connection_monitor_task = asyncio.create_task(self._monitor_connections())
            self.gui.log_message("🔍 開始監控雙發球機連接狀態")
            
        except Exception as e:
            self.gui.log_message(f"❌ 啟動連接監控失敗: {e}")
    
    def _stop_connection_monitoring(self):
        """停止連接監控"""
        try:
            if self.connection_monitor_task and not self.connection_monitor_task.done():
                self.connection_monitor_task.cancel()
            self.connection_monitor_task = None
            self.gui.log_message("⏹️ 停止監控雙發球機連接狀態")
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止連接監控失敗: {e}")
    
    async def _monitor_connections(self):
        """監控連接狀態"""
        try:
            while True:
                await asyncio.sleep(self.monitor_interval)
                
                # 檢查左發球機連接
                if self.left_machine and not self.left_machine.is_connected:
                    self.gui.log_message("⚠️ 左發球機連接丟失，嘗試重連...")
                    await self._reconnect_machine('left')
                
                # 檢查右發球機連接
                if self.right_machine and not self.right_machine.is_connected:
                    self.gui.log_message("⚠️ 右發球機連接丟失，嘗試重連...")
                    await self._reconnect_machine('right')
                    
        except asyncio.CancelledError:
            self.gui.log_message("⏹️ 連接監控已停止")
        except Exception as e:
            self.gui.log_message(f"❌ 連接監控錯誤: {e}")
    
    async def _reconnect_machine(self, machine_type: str):
        """重連發球機"""
        try:
            device = next((d for d in self.found_devices if d.get('machine_type') == machine_type), None)
            if not device:
                self.gui.log_message(f"❌ 找不到 {machine_type} 發球機設備信息")
                return False
            
            machine = self.machine_threads.get(machine_type)
            if not machine:
                self.gui.log_message(f"❌ {machine_type} 發球機線程不存在")
                return False
            
            # 嘗試重連
            await machine.connect_device(device['address'])
            
            if machine.is_connected:
                self.gui.log_message(f"✅ {machine_type} 發球機重連成功")
                return True
            else:
                self.gui.log_message(f"❌ {machine_type} 發球機重連失敗")
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ {machine_type} 發球機重連錯誤: {e}")
            return False
    
    def is_dual_connected(self) -> bool:
        """
        檢查雙發球機是否都已連接
        
        Returns:
            是否都已連接
        """
        left_connected = self.left_machine and self.left_machine.is_connected
        right_connected = self.right_machine and self.right_machine.is_connected
        return left_connected and right_connected
    
    def get_machine_thread(self, machine_type: str) -> Optional[DualBluetoothThread]:
        """
        獲取指定類型的發球機線程
        
        Args:
            machine_type: 'left' 或 'right'
            
        Returns:
            發球機線程實例
        """
        return self.machine_threads.get(machine_type)
    
    async def send_coordinated_shot(self, left_area: str, right_area: str, 
                                  coordination_mode: str = "alternate", interval: float = 0.5, count: int = 1) -> bool:
        """
        發送協調發球指令
        
        Args:
            left_area: 左發球機發球區域
            right_area: 右發球機發球區域
            coordination_mode: 協調模式 ("alternate", "simultaneous", "sequence")
            interval: 模式相關的間隔時間（秒）。對 alternate/sequence 生效
            count: 發球輪數（次）
            
        Returns:
            是否成功發送
        """
        try:
            if not self.is_dual_connected():
                self.gui.log_message("❌ 雙發球機未完全連接")
                return False
            
            if not self.coordinator:
                self.gui.log_message("❌ 雙發球機協調器未初始化")
                return False
            
            # 使用協調器發送協調發球
            result = await self.coordinator.send_coordinated_shot(
                left_area, right_area, coordination_mode, interval=interval, count=count
            )
            
            if result:
                self.gui.log_message(f"🎯 協調發球完成: 左({left_area}) + 右({right_area}) [{coordination_mode}] x{max(1, count)}")
            else:
                self.gui.log_message(f"❌ 協調發球失敗: 左({left_area}) + 右({right_area}) [{coordination_mode}] x{max(1, count)}")
            
            return result
            
        except Exception as e:
            self.gui.log_message(f"❌ 協調發球失敗: {e}")
            return False
    
    def reassign_device(self, device_address: str, new_machine_type: str) -> bool:
        """
        重新分配設備類型
        
        Args:
            device_address: 設備地址
            new_machine_type: 新的機器類型 ('left' 或 'right')
            
        Returns:
            是否成功重新分配
        """
        try:
            # 找到對應的設備
            device = None
            for d in self.found_devices:
                if d['address'] == device_address:
                    device = d
                    break
            
            if not device:
                self.gui.log_message(f"❌ 找不到地址為 {device_address} 的設備")
                return False
            
            old_type = device.get('machine_type', 'unknown')
            device['machine_type'] = new_machine_type
            
            self.gui.log_message(f"🔄 設備 {device['name']} 從 {old_type} 重新分配為 {new_machine_type}")
            
            # 更新 UI
            self._update_device_ui()
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 重新分配設備失敗: {e}")
            return False
    
    def get_available_devices(self) -> List[Dict]:
        """
        獲取所有可用設備
        
        Returns:
            設備列表
        """
        return self.found_devices.copy()


def create_dual_bluetooth_manager(gui_instance) -> DualBluetoothManager:
    """
    建立雙發球機藍牙管理器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        DualBluetoothManager 實例
    """
    return DualBluetoothManager(gui_instance)

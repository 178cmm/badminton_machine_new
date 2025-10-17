"""
四台發球機藍牙連接管理器

這個模組負責管理四台發球機的藍牙連接邏輯，包括：
- 掃描和識別四台發球機設備
- 管理四台發球機的連接狀態
- 提供四台發球機獨立控制功能
- 基於 DualBluetoothManager 擴展，保持向後兼容
"""

import asyncio
import time
from typing import Optional, Dict, List, Tuple, Any, TYPE_CHECKING
from .dual_bluetooth_manager import DualBluetoothManager
from .dual_bluetooth_thread import DualBluetoothThread
from .multi_bluetooth_thread import MultiBluetoothThread

if TYPE_CHECKING:
    from .training_session import TrainingSession


class MultiMachineManager(DualBluetoothManager):
    """四台發球機藍牙連接管理器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化四台發球機藍牙管理器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        # 調用父類初始化
        super().__init__(gui_instance)
        
        # 四台發球機連接管理
        self.machines: Dict[str, MultiBluetoothThread] = {}  # {machine_id: MultiBluetoothThread}
        self.training_sessions: Dict[str, 'TrainingSession'] = {}  # {machine_id: TrainingSession}
        
        # 設備識別策略
        self.max_machines = 4
        self.machine_ids = ['machine_1', 'machine_2', 'machine_3', 'machine_4']
        
        # 連接狀態監控
        self.multi_connection_monitor_task = None
        self.monitor_interval = 5  # 監控間隔（秒）
        
        # 載入可用套餐
        self.available_programs = self._load_available_programs()
        
        # 訓練執行器
        self.training_executor = None
        self.coordinated_training_executor = None
        
        self.gui.log_message("🏸 四台發球機管理器已初始化")
    
    def _load_available_programs(self) -> Dict[str, Dict]:
        """
        載入可用的訓練套餐
        
        Returns:
            套餐配置字典
        """
        return {
            "基礎訓練": {
                "id": "basic_training",
                "type": "basic",
                "shots": [
                    {"section": "sec25_1", "description": "正手高遠球"},
                    {"section": "sec21_1", "description": "反手高遠球"},
                    {"section": "sec25_1", "description": "正手切球"},
                    {"section": "sec21_1", "description": "反手切球"},
                    {"section": "sec25_1", "description": "正手殺球"},
                    {"section": "sec21_1", "description": "反手殺球"},
                    {"section": "sec15_1", "description": "正手平抽球"},
                    {"section": "sec11_1", "description": "反手平抽球"},
                    {"section": "sec5_1", "description": "正手小球"},
                    {"section": "sec1_1", "description": "反手小球"},
                    {"section": "sec5_1", "description": "正手挑球"},
                    {"section": "sec1_1", "description": "反手挑球"},
                    {"section": "sec13_1", "description": "平推球"},
                    {"section": "sec20_1", "description": "正手接殺球"},
                    {"section": "sec16_1", "description": "反手接殺球"},
                    {"section": "sec18_1", "description": "近身接殺"}
                ]
            },
            "近身隨機接殺": {
                "id": "near_body_random_kill",
                "type": "advanced",
                "mode": "random",
                "sections": ["sec17_1", "sec18_1", "sec19_1"]
            },
            "前場隨機": {
                "id": "front_court_random",
                "type": "advanced",
                "mode": "random", 
                "sections": ["sec1_1", "sec2_1", "sec3_1", "sec4_1", "sec5_1"]
            },
            "後場隨機": {
                "id": "back_court_random",
                "type": "advanced",
                "mode": "random",
                "sections": ["sec21_1", "sec22_1", "sec23_1", "sec24_1", "sec25_1"]
            },
            "四角隨機": {
                "id": "four_corner_random",
                "type": "advanced",
                "mode": "random",
                "sections": ["sec1_1", "sec5_1", "sec21_1", "sec25_1"]
            },
            "六角隨機": {
                "id": "six_corner_random", 
                "type": "advanced",
                "mode": "random",
                "sections": ["sec1_1", "sec5_1", "sec11_1", "sec15_1", "sec21_1", "sec25_1"]
            },
            "殺球上網": {
                "id": "kill_and_approach",
                "type": "advanced",
                "mode": "sequence",
                "sections": ["sec25_1", "sec5_1", "sec21_1", "sec1_1"]
            },
            "殺抽壓連貫": {
                "id": "kill_drive_press",
                "type": "advanced",
                "mode": "sequence", 
                "sections": ["sec25_1", "sec15_1", "sec5_1", "sec21_1", "sec11_1", "sec1_1"]
            },
            "單打防守": {
                "id": "singles_defense",
                "type": "advanced",
                "mode": "random",
                "sections": ["sec16_1", "sec17_1", "sec18_1", "sec19_1", "sec20_1"]
            },
            "雙打防守": {
                "id": "doubles_defense",
                "type": "advanced",
                "mode": "random",
                "sections": ["sec11_1", "sec12_1", "sec13_1", "sec14_1", "sec15_1", "sec16_1"]
            }
        }
    
    async def scan_multi_devices(self) -> bool:
        """
        掃描四台發球機設備
        
        Returns:
            是否成功開始掃描
        """
        try:
            self.gui.log_message("🔍 開始掃描四台發球機...")
            
            # 清空之前的設備列表
            self.found_devices.clear()
            
            # 開始掃描
            devices = await self._discover_devices()
            
            if devices:
                self.gui.log_message(f"✅ 找到 {len(devices)} 個發球機設備")
                await self._identify_multi_machines(devices)
                return True
            else:
                self.gui.log_message("❌ 未找到發球機設備")
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ 掃描四台發球機失敗: {e}")
            return False
    
    async def _identify_multi_machines(self, devices: List[Dict]):
        """
        識別四台發球機
        
        Args:
            devices: 發現的設備列表
        """
        try:
            if len(devices) == 0:
                self.gui.log_message("❌ 沒有找到任何發球機設備")
                self.found_devices = []
                return
            
            # 智能分配設備到四台發球機
            await self._smart_assign_multi_devices(devices)
            
            # 檢查識別結果
            machine_counts = {}
            for device in self.found_devices:
                machine_id = device.get('machine_id', 'unknown')
                machine_counts[machine_id] = machine_counts.get(machine_id, 0) + 1
            
            self.gui.log_message(f"📊 識別結果: {dict(machine_counts)}")
            
            # 更新 UI 顯示
            self._update_multi_device_ui()
            
        except Exception as e:
            self.gui.log_message(f"❌ 四台發球機識別失敗: {e}")
            import traceback
            traceback.print_exc()
    
    async def _smart_assign_multi_devices(self, devices: List[Dict]):
        """
        智能分配設備到四台發球機
        
        Args:
            devices: 發現的設備列表
        """
        try:
            # 首先嘗試通過名稱識別
            name_identified = []
            for device in devices:
                name = device['name'].upper()
                # 檢查是否包含數字標識
                for i in range(1, 5):
                    # 更精確的匹配：檢查是否以數字結尾或包含特定模式
                    if (name.endswith(f"-{i}") or 
                        name.endswith(f"_{i}") or 
                        f"MACHINE{i}" in name or
                        (name.endswith(str(i)) and len(name) > 1)):
                        device['machine_id'] = f'machine_{i}'
                        name_identified.append(device)
                        self.gui.log_message(f"🔍 名稱識別: {device['name']} -> machine_{i}")
                        break
            
            # 對於未通過名稱識別的設備，按順序分配
            unidentified = [d for d in devices if d not in name_identified]
            
            # 按順序分配到可用的機器ID
            used_machine_ids = {d.get('machine_id') for d in name_identified}
            available_machine_ids = [mid for mid in self.machine_ids if mid not in used_machine_ids]
            
            for i, device in enumerate(unidentified):
                if i < len(available_machine_ids):
                    device['machine_id'] = available_machine_ids[i]
                    self.gui.log_message(f"🤖 智能分配: {device['name']} -> {available_machine_ids[i]}")
                else:
                    # 如果超過4台設備，分配到已使用的機器ID
                    device['machine_id'] = f'machine_{i % 4 + 1}'
                    self.gui.log_message(f"🤖 智能分配: {device['name']} -> {device['machine_id']} (重複分配)")
            
            self.found_devices = devices
            self.gui.log_message("✅ 四台發球機智能分配完成")
            
        except Exception as e:
            self.gui.log_message(f"❌ 四台發球機智能分配失敗: {e}")
            # 後備方案：簡單順序分配
            for i, device in enumerate(devices):
                device['machine_id'] = f'machine_{i % 4 + 1}'
            self.found_devices = devices
    
    def _update_multi_device_ui(self):
        """更新四台發球機設備選擇 UI"""
        try:
            # 統計各機器ID的設備數量
            machine_devices = {}
            for device in self.found_devices:
                machine_id = device.get('machine_id', 'unknown')
                if machine_id not in machine_devices:
                    machine_devices[machine_id] = []
                machine_devices[machine_id].append(device)
            
            # 記錄統計信息
            for machine_id in self.machine_ids:
                count = len(machine_devices.get(machine_id, []))
                self.gui.log_message(f"📊 {machine_id}: {count} 台設備")
            
            # 如果有UI組件，更新它們
            if hasattr(self.gui, 'update_multi_machine_ui'):
                self.gui.update_multi_machine_ui(machine_devices)
            
            # 啟用連接按鈕（需要至少一台設備）
            if hasattr(self.gui, 'connect_multi_button'):
                can_connect = len(self.found_devices) > 0
                self.gui.connect_multi_button.setEnabled(can_connect)
                
                if can_connect:
                    self.gui.log_message("✅ 四台發球機準備就緒，可以連接")
                else:
                    self.gui.log_message("⚠️ 需要至少一台發球機才能連接")
                
        except Exception as e:
            self.gui.log_message(f"❌ 更新四台發球機設備 UI 失敗: {e}")
            import traceback
            traceback.print_exc()
    
    async def connect_multi_machines(self) -> bool:
        """
        連接四台發球機
        
        Returns:
            是否成功連接
        """
        try:
            self.gui.log_message("🔗 開始連接四台發球機...")
            
            # 獲取要連接的設備
            devices_to_connect = []
            for device in self.found_devices:
                machine_id = device.get('machine_id')
                if machine_id and machine_id in self.machine_ids:
                    devices_to_connect.append((machine_id, device))
            
            if not devices_to_connect:
                self.gui.log_message("❌ 沒有找到可連接的發球機設備")
                return False
            
            # 並行連接所有設備
            connection_tasks = []
            for machine_id, device in devices_to_connect:
                task = self._connect_single_machine(machine_id, device)
                connection_tasks.append(task)
            
            # 等待所有連接完成
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # 檢查連接結果
            successful_connections = 0
            for i, result in enumerate(results):
                machine_id, device = devices_to_connect[i]
                if not isinstance(result, Exception) and result:
                    successful_connections += 1
                    self.gui.log_message(f"✅ {machine_id} 連接成功: {device['name']}")
                else:
                    self.gui.log_message(f"❌ {machine_id} 連接失敗: {device['name']}")
            
            if successful_connections > 0:
                self.gui.log_message(f"✅ 四台發球機連接完成: {successful_connections}/{len(devices_to_connect)} 台成功")
                
                # 開始連接監控
                self._start_multi_connection_monitoring()
                
                return True
            else:
                self.gui.log_message("❌ 四台發球機連接失敗")
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ 連接四台發球機失敗: {e}")
            return False
    
    async def _connect_single_machine(self, machine_id: str, device: Dict) -> bool:
        """
        連接單台發球機
        
        Args:
            machine_id: 機器ID
            device: 設備信息
            
        Returns:
            是否成功連接
        """
        try:
            # 創建藍牙線程
            machine_thread = MultiBluetoothThread(machine_id)
            
            # 設置信號連接
            self._setup_machine_signals(machine_thread, machine_id)
            
            # 連接設備
            success = await machine_thread.connect_device(device['address'])
            
            if success:
                # 存儲機器線程
                self.machines[machine_id] = machine_thread
                
                # 設置到主 GUI
                if hasattr(self.gui, f'{machine_id}_bluetooth_thread'):
                    setattr(self.gui, f'{machine_id}_bluetooth_thread', machine_thread)
                
                return True
            else:
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ 連接 {machine_id} 失敗: {e}")
            return False
    
    def _setup_machine_signals(self, machine_thread: MultiBluetoothThread, machine_id: str):
        """設置發球機信號連接"""
        try:
            machine_thread.connection_status.connect(
                lambda machine_type, connected, msg: self._on_machine_connection_status(machine_id, connected, msg)
            )
            machine_thread.shot_sent.connect(
                lambda machine_type, msg: self._on_machine_shot_sent(machine_id, msg)
            )
            machine_thread.error_occurred.connect(
                lambda machine_type, msg: self._on_machine_error(machine_id, msg)
            )
        except Exception as e:
            self.gui.log_message(f"❌ 設置 {machine_id} 信號失敗: {e}")
    
    def _on_machine_connection_status(self, machine_id: str, connected: bool, message: str):
        """發球機連接狀態回調"""
        try:
            status_icon = "✅" if connected else "❌"
            self.gui.log_message(f"{status_icon} {machine_id}: {message}")
            
            # 更新 UI 狀態
            if hasattr(self.gui, 'update_multi_machine_connection_status'):
                self.gui.update_multi_machine_connection_status(machine_id, connected, message)
                
        except Exception as e:
            self.gui.log_message(f"❌ 處理 {machine_id} 連接狀態失敗: {e}")
    
    def _on_machine_shot_sent(self, machine_id: str, message: str):
        """發球機發球回調"""
        try:
            self.gui.log_message(f"🎯 {machine_id}: {message}")
        except Exception as e:
            print(f"處理 {machine_id} 發球事件時發生錯誤: {e}")
    
    def _on_machine_error(self, machine_id: str, message: str):
        """發球機錯誤回調"""
        try:
            self.gui.log_message(f"❌ {machine_id} 錯誤: {message}")
        except Exception as e:
            print(f"處理 {machine_id} 錯誤事件時發生錯誤: {e}")
    
    async def disconnect_multi_machines(self) -> bool:
        """
        斷開四台發球機連接
        
        Returns:
            是否成功斷開
        """
        try:
            self.gui.log_message("🔌 斷開四台發球機連接...")
            
            # 停止連接監控
            self._stop_multi_connection_monitoring()
            
            # 並行斷開所有連接
            tasks = []
            for machine_id, machine_thread in self.machines.items():
                if machine_thread and machine_thread.is_connected:
                    tasks.append(machine_thread.disconnect())
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # 清理資源
            self.machines.clear()
            
            # 更新主 GUI
            for machine_id in self.machine_ids:
                if hasattr(self.gui, f'{machine_id}_bluetooth_thread'):
                    setattr(self.gui, f'{machine_id}_bluetooth_thread', None)
            
            self.gui.log_message("✅ 四台發球機已斷開連接")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 斷開四台發球機失敗: {e}")
            return False
    
    def _start_multi_connection_monitoring(self):
        """開始四台發球機連接監控"""
        try:
            if self.multi_connection_monitor_task and not self.multi_connection_monitor_task.done():
                self.multi_connection_monitor_task.cancel()
            
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                self.multi_connection_monitor_task = loop.create_task(self._monitor_multi_connections())
            except RuntimeError:
                self.gui.log_message("❌ 無法創建四台發球機連接監控任務")
                return
            self.gui.log_message("🔍 開始監控四台發球機連接狀態")
            
        except Exception as e:
            self.gui.log_message(f"❌ 啟動四台發球機連接監控失敗: {e}")
    
    def _stop_multi_connection_monitoring(self):
        """停止四台發球機連接監控"""
        try:
            if self.multi_connection_monitor_task and not self.multi_connection_monitor_task.done():
                self.multi_connection_monitor_task.cancel()
            self.multi_connection_monitor_task = None
            self.gui.log_message("⏹️ 停止監控四台發球機連接狀態")
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止四台發球機連接監控失敗: {e}")
    
    async def _monitor_multi_connections(self):
        """監控四台發球機連接狀態"""
        try:
            while True:
                await asyncio.sleep(self.monitor_interval)
                
                # 檢查每台發球機連接
                for machine_id, machine_thread in self.machines.items():
                    if machine_thread and not machine_thread.is_connected:
                        self.gui.log_message(f"⚠️ {machine_id} 連接丟失，嘗試重連...")
                        await self._reconnect_multi_machine(machine_id)
                    
        except asyncio.CancelledError:
            self.gui.log_message("⏹️ 四台發球機連接監控已停止")
        except Exception as e:
            self.gui.log_message(f"❌ 四台發球機連接監控錯誤: {e}")
    
    async def _reconnect_multi_machine(self, machine_id: str):
        """重連發球機"""
        try:
            device = next((d for d in self.found_devices if d.get('machine_id') == machine_id), None)
            if not device:
                self.gui.log_message(f"❌ 找不到 {machine_id} 設備信息")
                return False
            
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                self.gui.log_message(f"❌ {machine_id} 線程不存在")
                return False
            
            # 嘗試重連
            await machine_thread.connect_device(device['address'])
            
            if machine_thread.is_connected:
                self.gui.log_message(f"✅ {machine_id} 重連成功")
                return True
            else:
                self.gui.log_message(f"❌ {machine_id} 重連失敗")
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ {machine_id} 重連錯誤: {e}")
            return False
    
    def is_multi_connected(self) -> bool:
        """
        檢查四台發球機是否都已連接
        
        Returns:
            是否都已連接
        """
        if not self.machines:
            return False
        
        for machine_thread in self.machines.values():
            if not machine_thread or not machine_thread.is_connected:
                return False
        
        return True
    
    def get_connected_machines(self) -> List[str]:
        """
        獲取已連接的發球機列表
        
        Returns:
            已連接的發球機ID列表
        """
        connected = []
        for machine_id, machine_thread in self.machines.items():
            if machine_thread and machine_thread.is_connected:
                connected.append(machine_id)
        return connected
    
    def get_machine_thread(self, machine_id: str) -> Optional[MultiBluetoothThread]:
        """
        獲取指定ID的發球機線程
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            發球機線程實例
        """
        return self.machines.get(machine_id)
    
    def get_available_programs(self) -> Dict[str, Dict]:
        """
        獲取可用的訓練套餐
        
        Returns:
            套餐配置字典
        """
        return self.available_programs.copy()
    
    def create_training_session(self, machine_id: str, program_name: str, 
                              interval: float, unlimited: bool = True) -> Optional['TrainingSession']:
        """
        創建訓練會話
        
        Args:
            machine_id: 發球機ID
            program_name: 套餐名稱
            interval: 發球間隔
            unlimited: 是否無限發球
            
        Returns:
            訓練會話實例
        """
        try:
            from .training_session import TrainingSession
            
            # 檢查機器ID是否有效
            if machine_id not in self.machine_ids:
                self.gui.log_message(f"❌ 無效的發球機ID: {machine_id}")
                return None
            
            if program_name not in self.available_programs:
                self.gui.log_message(f"❌ 套餐 {program_name} 不存在")
                return None
            
            # 檢查是否已有會話
            if machine_id in self.training_sessions:
                self.gui.log_message(f"⚠️ {machine_id} 已有訓練會話，將替換")
                self.remove_training_session(machine_id)
            
            session = TrainingSession(machine_id, program_name, interval, unlimited)
            session.program_config = self.available_programs[program_name]
            
            self.training_sessions[machine_id] = session
            
            self.gui.log_message(f"✅ 為 {machine_id} 創建訓練會話: {program_name}")
            return session
            
        except Exception as e:
            self.gui.log_message(f"❌ 創建訓練會話失敗: {e}")
            return None
    
    def get_training_session(self, machine_id: str) -> Optional['TrainingSession']:
        """
        獲取訓練會話
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            訓練會話實例
        """
        return self.training_sessions.get(machine_id)
    
    def remove_training_session(self, machine_id: str) -> bool:
        """
        移除訓練會話
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功移除
        """
        try:
            if machine_id in self.training_sessions:
                session = self.training_sessions[machine_id]
                if session.worker and session.worker.isRunning():
                    session.worker.quit()
                    session.worker.wait()
                
                del self.training_sessions[machine_id]
                self.gui.log_message(f"✅ 移除 {machine_id} 訓練會話")
                return True
            else:
                self.gui.log_message(f"⚠️ {machine_id} 沒有訓練會話")
                return False
                
        except Exception as e:
            self.gui.log_message(f"❌ 移除訓練會話失敗: {e}")
            return False
    
    async def send_shot_to_machine(self, machine_id: str, area_section: str, 
                                 machine_specific: bool = False) -> bool:
        """
        向指定發球機發送發球指令
        
        Args:
            machine_id: 發球機ID
            area_section: 發球區域代碼
            machine_specific: 是否使用機器特定參數
            
        Returns:
            是否成功發送
        """
        try:
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                self.gui.log_message(f"❌ 發球機 {machine_id} 不存在")
                return False
            
            if not machine_thread.is_connected:
                self.gui.log_message(f"❌ 發球機 {machine_id} 未連接")
                return False
            
            success = await machine_thread.send_shot(area_section, machine_specific)
            if success:
                self.gui.log_message(f"🎯 {machine_id} 發球成功: {area_section}")
            else:
                self.gui.log_message(f"❌ {machine_id} 發球失敗: {area_section}")
            
            return success
            
        except Exception as e:
            self.gui.log_message(f"❌ 向 {machine_id} 發送發球指令失敗: {e}")
            return False
    
    async def send_continuous_shots_to_machine(self, machine_id: str, area_sections: List[str], 
                                             interval: float, count: int = -1, 
                                             machine_specific: bool = False) -> bool:
        """
        向指定發球機發送連續發球指令
        
        Args:
            machine_id: 發球機ID
            area_sections: 發球區域代碼列表
            interval: 發球間隔（秒）
            count: 發球次數（-1表示無限）
            machine_specific: 是否使用機器特定參數
            
        Returns:
            是否成功開始連續發球
        """
        try:
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                self.gui.log_message(f"❌ 發球機 {machine_id} 不存在")
                return False
            
            if not machine_thread.is_connected:
                self.gui.log_message(f"❌ 發球機 {machine_id} 未連接")
                return False
            
            success = await machine_thread.send_continuous_shots(
                area_sections, interval, count, machine_specific
            )
            
            if success:
                self.gui.log_message(f"🎯 {machine_id} 開始連續發球")
            else:
                self.gui.log_message(f"❌ {machine_id} 連續發球失敗")
            
            return success
            
        except Exception as e:
            self.gui.log_message(f"❌ 向 {machine_id} 發送連續發球指令失敗: {e}")
            return False
    
    def get_machine_connection_info(self, machine_id: str) -> Optional[Dict[str, any]]:
        """
        獲取發球機連接信息
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            連接信息字典
        """
        try:
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                return None
            
            return machine_thread.get_connection_info()
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取 {machine_id} 連接信息失敗: {e}")
            return None
    
    def get_all_machines_connection_info(self) -> Dict[str, Dict[str, any]]:
        """
        獲取所有發球機的連接信息
        
        Returns:
            所有發球機的連接信息字典
        """
        try:
            info = {}
            for machine_id in self.machine_ids:
                machine_info = self.get_machine_connection_info(machine_id)
                if machine_info:
                    info[machine_id] = machine_info
                else:
                    info[machine_id] = {
                        "machine_id": machine_id,
                        "is_connected": False,
                        "error": "機器不存在或未初始化"
                    }
            
            return info
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取所有發球機連接信息失敗: {e}")
            return {}
    
    def set_machine_shot_cooldown(self, machine_id: str, cooldown: float) -> bool:
        """
        設定發球機的發球冷卻時間
        
        Args:
            machine_id: 發球機ID
            cooldown: 冷卻時間（秒）
            
        Returns:
            是否成功設定
        """
        try:
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                self.gui.log_message(f"❌ 發球機 {machine_id} 不存在")
                return False
            
            machine_thread.set_shot_cooldown(cooldown)
            self.gui.log_message(f"✅ {machine_id} 發球冷卻時間設定為 {cooldown} 秒")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 設定 {machine_id} 發球冷卻時間失敗: {e}")
            return False
    
    def set_machine_connection_timeout(self, machine_id: str, timeout: float) -> bool:
        """
        設定發球機的連接超時時間
        
        Args:
            machine_id: 發球機ID
            timeout: 超時時間（秒）
            
        Returns:
            是否成功設定
        """
        try:
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                self.gui.log_message(f"❌ 發球機 {machine_id} 不存在")
                return False
            
            machine_thread.set_connection_timeout(timeout)
            self.gui.log_message(f"✅ {machine_id} 連接超時時間設定為 {timeout} 秒")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 設定 {machine_id} 連接超時時間失敗: {e}")
            return False
    
    def reset_machine_statistics(self, machine_id: str) -> bool:
        """
        重置發球機統計信息
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功重置
        """
        try:
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                self.gui.log_message(f"❌ 發球機 {machine_id} 不存在")
                return False
            
            machine_thread.reset_statistics()
            self.gui.log_message(f"✅ {machine_id} 統計信息已重置")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 重置 {machine_id} 統計信息失敗: {e}")
            return False
    
    def check_machine_health(self, machine_id: str) -> bool:
        """
        檢查發球機健康狀態
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否健康
        """
        try:
            machine_thread = self.machines.get(machine_id)
            if not machine_thread:
                return False
            
            return machine_thread.is_healthy()
            
        except Exception as e:
            self.gui.log_message(f"❌ 檢查 {machine_id} 健康狀態失敗: {e}")
            return False
    
    def get_healthy_machines(self) -> List[str]:
        """
        獲取健康的發球機列表
        
        Returns:
            健康的發球機ID列表
        """
        try:
            healthy_machines = []
            for machine_id in self.machine_ids:
                if self.check_machine_health(machine_id):
                    healthy_machines.append(machine_id)
            
            return healthy_machines
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取健康發球機列表失敗: {e}")
            return []
    
    def get_training_executor(self):
        """
        獲取訓練執行器
        
        Returns:
            訓練執行器實例
        """
        if self.training_executor is None:
            from ..executors.multi_machine_training_executor import create_multi_machine_training_executor
            self.training_executor = create_multi_machine_training_executor(self.gui, self)
            self.gui.log_message("🏸 四台發球機訓練執行器已初始化")
        
        return self.training_executor
    
    def start_individual_training(self, machine_id: str, program_name: str, 
                                interval: float, unlimited: bool = True) -> bool:
        """
        啟動指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            program_name: 套餐名稱
            interval: 發球間隔
            unlimited: 是否無限發球
            
        Returns:
            是否成功開始訓練
        """
        try:
            executor = self.get_training_executor()
            return executor.start_individual_training(machine_id, program_name, interval, unlimited)
        except Exception as e:
            self.gui.log_message(f"❌ 啟動 {machine_id} 訓練失敗: {e}")
            return False
    
    def pause_individual_training(self, machine_id: str) -> bool:
        """
        暫停指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功暫停
        """
        try:
            executor = self.get_training_executor()
            return executor.pause_individual_training(machine_id)
        except Exception as e:
            self.gui.log_message(f"❌ 暫停 {machine_id} 訓練失敗: {e}")
            return False
    
    def resume_individual_training(self, machine_id: str) -> bool:
        """
        恢復指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功恢復
        """
        try:
            executor = self.get_training_executor()
            return executor.resume_individual_training(machine_id)
        except Exception as e:
            self.gui.log_message(f"❌ 恢復 {machine_id} 訓練失敗: {e}")
            return False
    
    def stop_individual_training(self, machine_id: str) -> bool:
        """
        停止指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功停止
        """
        try:
            executor = self.get_training_executor()
            return executor.stop_individual_training(machine_id)
        except Exception as e:
            self.gui.log_message(f"❌ 停止 {machine_id} 訓練失敗: {e}")
            return False
    
    def pause_all_training(self) -> bool:
        """
        暫停所有發球機的訓練
        
        Returns:
            是否成功暫停
        """
        try:
            executor = self.get_training_executor()
            return executor.pause_all_training()
        except Exception as e:
            self.gui.log_message(f"❌ 暫停全部訓練失敗: {e}")
            return False
    
    def resume_all_training(self) -> bool:
        """
        恢復所有發球機的訓練
        
        Returns:
            是否成功恢復
        """
        try:
            executor = self.get_training_executor()
            return executor.resume_all_training()
        except Exception as e:
            self.gui.log_message(f"❌ 恢復全部訓練失敗: {e}")
            return False
    
    def stop_all_training(self) -> bool:
        """
        停止所有發球機的訓練
        
        Returns:
            是否成功停止
        """
        try:
            executor = self.get_training_executor()
            return executor.stop_all_training()
        except Exception as e:
            self.gui.log_message(f"❌ 停止全部訓練失敗: {e}")
            return False
    
    def get_training_status(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取指定發球機的訓練狀態
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            訓練狀態信息
        """
        try:
            executor = self.get_training_executor()
            return executor.get_training_status(machine_id)
        except Exception as e:
            self.gui.log_message(f"❌ 獲取 {machine_id} 訓練狀態失敗: {e}")
            return None
    
    def get_all_training_status(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取所有發球機的訓練狀態
        
        Returns:
            所有發球機的訓練狀態
        """
        try:
            executor = self.get_training_executor()
            return executor.get_all_training_status()
        except Exception as e:
            self.gui.log_message(f"❌ 獲取全部訓練狀態失敗: {e}")
            return {}
    
    def get_coordinated_training_executor(self):
        """
        獲取協調訓練執行器
        
        Returns:
            協調訓練執行器實例
        """
        if self.coordinated_training_executor is None:
            from ..executors.coordinated_training_executor import create_coordinated_training_executor
            self.coordinated_training_executor = create_coordinated_training_executor(self.gui, self)
            self.gui.log_message("🏸 協調訓練執行器已初始化")
        
        return self.coordinated_training_executor
    
    def start_coordinated_training(self, coordination_config: dict) -> bool:
        """
        開始協調訓練
        
        Args:
            coordination_config: 協調配置
            
        Returns:
            是否成功開始訓練
        """
        try:
            executor = self.get_coordinated_training_executor()
            return executor.start_coordinated_training(coordination_config)
        except Exception as e:
            self.gui.log_message(f"❌ 開始協調訓練失敗: {e}")
            return False
    
    def pause_coordinated_training(self) -> bool:
        """
        暫停協調訓練
        
        Returns:
            是否成功暫停
        """
        try:
            executor = self.get_coordinated_training_executor()
            return executor.pause_coordinated_training()
        except Exception as e:
            self.gui.log_message(f"❌ 暫停協調訓練失敗: {e}")
            return False
    
    def resume_coordinated_training(self) -> bool:
        """
        恢復協調訓練
        
        Returns:
            是否成功恢復
        """
        try:
            executor = self.get_coordinated_training_executor()
            return executor.resume_coordinated_training()
        except Exception as e:
            self.gui.log_message(f"❌ 恢復協調訓練失敗: {e}")
            return False
    
    def stop_coordinated_training(self) -> bool:
        """
        停止協調訓練
        
        Returns:
            是否成功停止
        """
        try:
            executor = self.get_coordinated_training_executor()
            return executor.stop_coordinated_training()
        except Exception as e:
            self.gui.log_message(f"❌ 停止協調訓練失敗: {e}")
            return False
    
    def get_coordination_status(self) -> Optional[Dict[str, Any]]:
        """
        獲取協調訓練狀態
        
        Returns:
            協調訓練狀態信息
        """
        try:
            executor = self.get_coordinated_training_executor()
            return executor.get_coordination_status()
        except Exception as e:
            self.gui.log_message(f"❌ 獲取協調狀態失敗: {e}")
            return None


def create_multi_machine_manager(gui_instance) -> MultiMachineManager:
    """
    建立四台發球機藍牙管理器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        MultiMachineManager 實例
    """
    return MultiMachineManager(gui_instance)

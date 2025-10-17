"""
智能協調管理器

這個模組實現三發球機的智能協調功能，解決BLE信號阻塞問題：
- 智能時機調度
- 獨立操作支持
- 信號衝突檢測
- 自動重試機制
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class MachineState(Enum):
    """發球機狀態"""
    IDLE = "idle"
    READY = "ready"
    SHOOTING = "shooting"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class ShotRequest:
    """發球請求"""
    machine_id: str
    area: str
    timestamp: float
    priority: int = 1  # 1=高優先級, 2=中優先級, 3=低優先級
    retry_count: int = 0
    max_retries: int = 3

class SmartCoordinationManager(QObject):
    """智能協調管理器"""
    
    # 信號定義
    shot_scheduled = pyqtSignal(str, str, float)  # machine_id, area, delay
    shot_completed = pyqtSignal(str, bool, str)  # machine_id, success, message
    coordination_update = pyqtSignal(dict)  # 協調狀態更新
    
    def __init__(self):
        super().__init__()
        
        # 發球機狀態
        self.machine_states: Dict[str, MachineState] = {
            'machine_1': MachineState.IDLE,
            'machine_2': MachineState.IDLE,
            'machine_3': MachineState.IDLE
        }
        
        # 發球請求隊列
        self.shot_queue: List[ShotRequest] = []
        
        # 協調參數
        self.min_shot_interval = 0.15  # 最小發球間隔（秒）
        self.max_shot_interval = 0.5   # 最大發球間隔（秒）
        self.signal_detection_window = 0.1  # 信號檢測窗口（秒）
        
        # 統計信息
        self.shot_statistics = {
            'total_requests': 0,
            'successful_shots': 0,
            'failed_shots': 0,
            'collision_detected': 0,
            'retry_attempts': 0
        }
        
        # 定時器
        self.coordination_timer = QTimer()
        self.coordination_timer.timeout.connect(self._process_shot_queue)
        self.coordination_timer.start(50)  # 每50ms檢查一次
        
        # 發球機線程引用（將由外部設置）
        self.machine_threads: Dict[str, any] = {}
        
    def set_machine_thread(self, machine_id: str, thread):
        """設置發球機線程引用"""
        self.machine_threads[machine_id] = thread
        
    def request_shot(self, machine_id: str, area: str, priority: int = 1) -> bool:
        """
        請求發球
        
        Args:
            machine_id: 發球機ID
            area: 發球區域
            priority: 優先級 (1=高, 2=中, 3=低)
            
        Returns:
            是否成功加入隊列
        """
        if machine_id not in self.machine_states:
            return False
            
        # 檢查發球機狀態
        if self.machine_states[machine_id] in [MachineState.SHOOTING, MachineState.ERROR]:
            return False
            
        # 創建發球請求
        request = ShotRequest(
            machine_id=machine_id,
            area=area,
            timestamp=time.time(),
            priority=priority
        )
        
        # 按優先級插入隊列
        self._insert_request_by_priority(request)
        self.shot_statistics['total_requests'] += 1
        
        return True
        
    def _insert_request_by_priority(self, request: ShotRequest):
        """按優先級插入發球請求"""
        inserted = False
        for i, existing_request in enumerate(self.shot_queue):
            if request.priority < existing_request.priority:
                self.shot_queue.insert(i, request)
                inserted = True
                break
                
        if not inserted:
            self.shot_queue.append(request)
            
    def _process_shot_queue(self):
        """處理發球隊列"""
        if not self.shot_queue:
            return
            
        current_time = time.time()
        
        # 檢查是否有可執行的發球請求
        for request in self.shot_queue[:]:
            if self._can_execute_shot(request, current_time):
                self._execute_shot(request)
                self.shot_queue.remove(request)
                break
                
    def _can_execute_shot(self, request: ShotRequest, current_time: float) -> bool:
        """檢查是否可以執行發球"""
        machine_id = request.machine_id
        
        # 檢查發球機狀態
        if self.machine_states[machine_id] != MachineState.READY:
            return False
            
        # 檢查信號衝突
        if self._detect_signal_collision(machine_id, current_time):
            return False
            
        # 檢查重試次數
        if request.retry_count >= request.max_retries:
            self.shot_statistics['failed_shots'] += 1
            self.shot_completed.emit(machine_id, False, "達到最大重試次數")
            return False
            
        return True
        
    def _detect_signal_collision(self, machine_id: str, current_time: float) -> bool:
        """檢測信號衝突"""
        # 檢查其他發球機是否正在發球
        for other_machine_id, state in self.machine_states.items():
            if other_machine_id != machine_id and state == MachineState.SHOOTING:
                # 檢查時間窗口
                if hasattr(self, f'{other_machine_id}_last_shot_time'):
                    last_shot_time = getattr(self, f'{other_machine_id}_last_shot_time')
                    if current_time - last_shot_time < self.signal_detection_window:
                        self.shot_statistics['collision_detected'] += 1
                        return True
                        
        return False
        
    async def _execute_shot(self, request: ShotRequest):
        """執行發球"""
        machine_id = request.machine_id
        area = request.area
        
        try:
            # 更新狀態
            self.machine_states[machine_id] = MachineState.SHOOTING
            setattr(self, f'{machine_id}_last_shot_time', time.time())
            
            # 獲取發球機線程
            machine_thread = self.machine_threads.get(machine_id)
            if not machine_thread:
                raise Exception("發球機線程未設置")
                
            # 執行發球
            success = await machine_thread.send_shot(area)
            
            if success:
                self.shot_statistics['successful_shots'] += 1
                self.shot_completed.emit(machine_id, True, f"發球成功: {area}")
            else:
                # 發球失敗，增加重試次數
                request.retry_count += 1
                self.shot_statistics['retry_attempts'] += 1
                
                if request.retry_count < request.max_retries:
                    # 重新加入隊列，增加延遲
                    delay = self.min_shot_interval * (request.retry_count + 1)
                    request.timestamp = time.time() + delay
                    self._insert_request_by_priority(request)
                else:
                    self.shot_statistics['failed_shots'] += 1
                    self.shot_completed.emit(machine_id, False, "發球失敗")
                    
        except Exception as e:
            self.shot_statistics['failed_shots'] += 1
            self.shot_completed.emit(machine_id, False, f"發球錯誤: {e}")
            
        finally:
            # 恢復狀態
            self.machine_states[machine_id] = MachineState.READY
            
    def pause_machine(self, machine_id: str) -> bool:
        """暫停指定發球機"""
        if machine_id in self.machine_states:
            if self.machine_states[machine_id] == MachineState.READY:
                self.machine_states[machine_id] = MachineState.PAUSED
                return True
        return False
        
    def resume_machine(self, machine_id: str) -> bool:
        """恢復指定發球機"""
        if machine_id in self.machine_states:
            if self.machine_states[machine_id] == MachineState.PAUSED:
                self.machine_states[machine_id] = MachineState.READY
                return True
        return False
        
    def stop_machine(self, machine_id: str) -> bool:
        """停止指定發球機"""
        if machine_id in self.machine_states:
            self.machine_states[machine_id] = MachineState.IDLE
            # 移除該發球機的待處理請求
            self.shot_queue = [req for req in self.shot_queue if req.machine_id != machine_id]
            return True
        return False
        
    def get_coordination_status(self) -> dict:
        """獲取協調狀態"""
        return {
            'machine_states': {k: v.value for k, v in self.machine_states.items()},
            'queue_length': len(self.shot_queue),
            'statistics': self.shot_statistics.copy()
        }
        
    def clear_queue(self):
        """清空發球隊列"""
        self.shot_queue.clear()
        
    def set_coordination_params(self, min_interval: float = None, max_interval: float = None, 
                              detection_window: float = None):
        """設置協調參數"""
        if min_interval is not None:
            self.min_shot_interval = min_interval
        if max_interval is not None:
            self.max_shot_interval = max_interval
        if detection_window is not None:
            self.signal_detection_window = detection_window

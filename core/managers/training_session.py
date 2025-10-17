"""
訓練會話管理

這個模組負責管理單台發球機的訓練會話，包括：
- 會話狀態管理
- 進度追蹤
- 配置參數管理
"""

import time
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal


class TrainingSession(QObject):
    """單台發球機的訓練會話"""
    
    # 信號定義
    status_changed = pyqtSignal(str, str)  # machine_id, status
    progress_updated = pyqtSignal(str, int, int)  # machine_id, current, total
    session_finished = pyqtSignal(str, str)  # machine_id, final_status
    
    def __init__(self, machine_id: str, program_name: str, interval: float, unlimited: bool = True):
        """
        初始化訓練會話
        
        Args:
            machine_id: 發球機ID
            program_name: 套餐名稱
            interval: 發球間隔（秒）
            unlimited: 是否無限發球
        """
        super().__init__()
        
        self.machine_id = machine_id
        self.program_name = program_name
        self.interval = interval
        self.unlimited = unlimited
        
        # 會話狀態
        self.status = "idle"  # idle, running, paused, stopped, error
        self.current_shot = 0
        self.total_shots = 0
        self.start_time = None
        self.pause_time = None
        self.total_pause_time = 0
        
        # 配置參數
        self.program_config: Optional[Dict[str, Any]] = None
        self.worker: Optional['IndividualTrainingWorker'] = None
        
        # 統計信息
        self.shots_sent = 0
        self.errors_count = 0
        self.last_error = None
        
        self.status_changed.emit(self.machine_id, self.status)
    
    def start_session(self) -> bool:
        """
        開始訓練會話
        
        Returns:
            是否成功開始
        """
        try:
            if self.status == "running":
                return False  # 已經在運行
            
            if not self.program_config:
                return False  # 沒有配置
            
            # 計算總球數
            if self.unlimited:
                self.total_shots = -1  # 無限模式
            else:
                if self.program_config.get("type") == "basic":
                    self.total_shots = len(self.program_config.get("shots", []))
                else:  # advanced
                    # 進階訓練預設100球
                    self.total_shots = 100
            
            # 重置計數器
            self.current_shot = 0
            self.shots_sent = 0
            self.errors_count = 0
            self.start_time = time.time()
            self.total_pause_time = 0
            
            # 更新狀態
            self.status = "running"
            self.status_changed.emit(self.machine_id, self.status)
            
            return True
            
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            self.status_changed.emit(self.machine_id, self.status)
            return False
    
    def pause_session(self) -> bool:
        """
        暫停訓練會話
        
        Returns:
            是否成功暫停
        """
        try:
            if self.status != "running":
                return False  # 不在運行狀態
            
            self.pause_time = time.time()
            self.status = "paused"
            self.status_changed.emit(self.machine_id, self.status)
            
            return True
            
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            self.status_changed.emit(self.machine_id, self.status)
            return False
    
    def resume_session(self) -> bool:
        """
        恢復訓練會話
        
        Returns:
            是否成功恢復
        """
        try:
            if self.status != "paused":
                return False  # 不在暫停狀態
            
            # 計算暫停時間
            if self.pause_time:
                pause_duration = time.time() - self.pause_time
                self.total_pause_time += pause_duration
                self.pause_time = None
            
            self.status = "running"
            self.status_changed.emit(self.machine_id, self.status)
            
            return True
            
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            self.status_changed.emit(self.machine_id, self.status)
            return False
    
    def stop_session(self) -> bool:
        """
        停止訓練會話
        
        Returns:
            是否成功停止
        """
        try:
            if self.status in ["stopped", "idle"]:
                return True  # 已經停止
            
            # 計算暫停時間
            if self.pause_time:
                pause_duration = time.time() - self.pause_time
                self.total_pause_time += pause_duration
                self.pause_time = None
            
            self.status = "stopped"
            self.status_changed.emit(self.machine_id, self.status)
            
            # 發送完成信號
            self.session_finished.emit(self.machine_id, self.status)
            
            return True
            
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            self.status_changed.emit(self.machine_id, self.status)
            return False
    
    def reset_session(self) -> bool:
        """
        重置訓練會話
        
        Returns:
            是否成功重置
        """
        try:
            # 停止會話
            self.stop_session()
            
            # 重置所有狀態
            self.status = "idle"
            self.current_shot = 0
            self.total_shots = 0
            self.start_time = None
            self.pause_time = None
            self.total_pause_time = 0
            self.shots_sent = 0
            self.errors_count = 0
            self.last_error = None
            
            self.status_changed.emit(self.machine_id, self.status)
            
            return True
            
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            self.status_changed.emit(self.machine_id, self.status)
            return False
    
    def update_progress(self, current: int, total: int = None):
        """
        更新進度
        
        Args:
            current: 當前進度
            total: 總進度（可選）
        """
        try:
            self.current_shot = current
            if total is not None:
                self.total_shots = total
            
            self.progress_updated.emit(self.machine_id, current, self.total_shots)
            
        except Exception as e:
            print(f"更新進度失敗: {e}")
    
    def record_shot_sent(self):
        """記錄發球"""
        try:
            self.shots_sent += 1
            if not self.unlimited:
                self.current_shot += 1
                self.progress_updated.emit(self.machine_id, self.current_shot, self.total_shots)
            else:
                # 無限模式下也更新進度顯示
                self.progress_updated.emit(self.machine_id, self.shots_sent, -1)
        except Exception as e:
            print(f"記錄發球失敗: {e}")
    
    def record_error(self, error_message: str):
        """
        記錄錯誤
        
        Args:
            error_message: 錯誤訊息
        """
        try:
            self.errors_count += 1
            self.last_error = error_message
        except Exception as e:
            print(f"記錄錯誤失敗: {e}")
    
    def get_session_duration(self) -> float:
        """
        獲取會話持續時間（秒）
        
        Returns:
            持續時間
        """
        try:
            if not self.start_time:
                return 0.0
            
            current_time = time.time()
            if self.pause_time:
                # 如果正在暫停，使用暫停時間
                current_time = self.pause_time
            
            return current_time - self.start_time - self.total_pause_time
            
        except Exception:
            return 0.0
    
    def get_progress_percentage(self) -> float:
        """
        獲取進度百分比
        
        Returns:
            進度百分比 (0-100)
        """
        try:
            if self.unlimited or self.total_shots <= 0:
                return 0.0
            
            if self.current_shot >= self.total_shots:
                return 100.0
            
            return (self.current_shot / self.total_shots) * 100.0
            
        except Exception:
            return 0.0
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        獲取會話狀態信息
        
        Returns:
            狀態信息字典
        """
        try:
            return {
                "machine_id": self.machine_id,
                "program_name": self.program_name,
                "status": self.status,
                "current_shot": self.current_shot,
                "total_shots": self.total_shots,
                "unlimited": self.unlimited,
                "interval": self.interval,
                "shots_sent": self.shots_sent,
                "errors_count": self.errors_count,
                "last_error": self.last_error,
                "duration": self.get_session_duration(),
                "progress_percentage": self.get_progress_percentage()
            }
        except Exception as e:
            return {
                "machine_id": self.machine_id,
                "error": str(e)
            }
    
    def is_running(self) -> bool:
        """檢查是否正在運行"""
        return self.status == "running"
    
    def is_paused(self) -> bool:
        """檢查是否暫停"""
        return self.status == "paused"
    
    def is_stopped(self) -> bool:
        """檢查是否停止"""
        return self.status in ["stopped", "idle"]
    
    def has_error(self) -> bool:
        """檢查是否有錯誤"""
        return self.status == "error"
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"TrainingSession({self.machine_id}, {self.program_name}, {self.status})"
    
    def __repr__(self) -> str:
        """詳細字符串表示"""
        return (f"TrainingSession(machine_id='{self.machine_id}', "
                f"program_name='{self.program_name}', "
                f"status='{self.status}', "
                f"current_shot={self.current_shot}, "
                f"total_shots={self.total_shots})")

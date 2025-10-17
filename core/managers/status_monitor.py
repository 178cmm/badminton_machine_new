"""
狀態監控管理器

這個模組負責監控四台發球機的狀態，包括：
- 實時狀態監控
- 性能統計和分析
- 系統健康檢查
- 狀態歷史記錄
"""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


@dataclass
class MachineStatus:
    """發球機狀態數據類別"""
    machine_id: str
    is_connected: bool
    is_training: bool
    training_program: str
    current_shot: int
    total_shots: int
    connection_quality: float  # 0.0-1.0
    last_shot_time: float
    total_shots_sent: int
    successful_shots: int
    failed_shots: int
    error_count: int
    uptime: float  # 運行時間（秒）
    timestamp: float


@dataclass
class SystemStatus:
    """系統狀態數據類別"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_usage: float
    active_connections: int
    total_training_sessions: int
    system_uptime: float
    timestamp: float


@dataclass
class PerformanceMetrics:
    """性能指標數據類別"""
    machine_id: str
    shots_per_minute: float
    success_rate: float
    average_response_time: float
    connection_stability: float
    error_rate: float
    timestamp: float


class StatusMonitor(QObject):
    """狀態監控管理器"""
    
    # 信號定義
    sig_machine_status_updated = pyqtSignal(str, dict)  # machine_id, status
    sig_system_status_updated = pyqtSignal(dict)  # system_status
    sig_performance_updated = pyqtSignal(str, dict)  # machine_id, metrics
    sig_health_alert = pyqtSignal(str, str)  # alert_type, message
    
    def __init__(self, gui_instance):
        """
        初始化狀態監控管理器
        
        Args:
            gui_instance: GUI 主類別實例
        """
        super().__init__()
        self.gui = gui_instance
        self.multi_machine_manager = None
        
        # 狀態數據存儲
        self.machine_status_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.system_status_history: deque = deque(maxlen=1000)
        self.performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # 監控配置
        self.monitor_interval = 1.0  # 監控間隔（秒）
        self.performance_interval = 30.0  # 性能統計間隔（秒）
        self.health_check_interval = 10.0  # 健康檢查間隔（秒）
        
        # 監控狀態
        self.is_monitoring = False
        self.monitor_timer = None
        self.performance_timer = None
        self.health_timer = None
        
        # 健康檢查閾值
        self.health_thresholds = {
            "cpu_usage": 80.0,  # CPU使用率閾值
            "memory_usage": 85.0,  # 記憶體使用率閾值
            "connection_quality": 0.7,  # 連接品質閾值
            "error_rate": 0.1,  # 錯誤率閾值
            "response_time": 5.0,  # 響應時間閾值（秒）
        }
        
        # 統計數據
        self.start_time = time.time()
        self.total_alerts = 0
        self.alert_history: deque = deque(maxlen=100)
    
    def set_multi_machine_manager(self, manager):
        """設置四台發球機管理器"""
        self.multi_machine_manager = manager
    
    def start_monitoring(self):
        """開始監控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.start_time = time.time()
        
        # 創建監控定時器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_machines)
        self.monitor_timer.start(int(self.monitor_interval * 1000))
        
        # 創建性能統計定時器
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._calculate_performance_metrics)
        self.performance_timer.start(int(self.performance_interval * 1000))
        
        # 創建健康檢查定時器
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._health_check)
        self.health_timer.start(int(self.health_check_interval * 1000))
        
        self.gui.log_message("🔍 狀態監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        # 停止定時器
        if self.monitor_timer:
            self.monitor_timer.stop()
            self.monitor_timer = None
        
        if self.performance_timer:
            self.performance_timer.stop()
            self.performance_timer = None
        
        if self.health_timer:
            self.health_timer.stop()
            self.health_timer = None
        
        self.gui.log_message("⏹️ 狀態監控已停止")
    
    def _monitor_machines(self):
        """監控發球機狀態"""
        if not self.multi_machine_manager:
            return
        
        try:
            # 監控每台發球機
            for machine_id in self.multi_machine_manager.machine_ids:
                machine_status = self._get_machine_status(machine_id)
                if machine_status:
                    self._update_machine_status(machine_id, machine_status)
            
            # 監控系統狀態
            system_status = self._get_system_status()
            self._update_system_status(system_status)
            
        except Exception as e:
            self.gui.log_message(f"❌ 監控錯誤: {e}")
    
    def _get_machine_status(self, machine_id: str) -> Optional[MachineStatus]:
        """獲取發球機狀態"""
        try:
            if not self.multi_machine_manager:
                return None
            
            # 獲取機器線程
            machine_thread = self.multi_machine_manager.get_machine_thread(machine_id)
            if not machine_thread:
                return None
            
            # 獲取訓練狀態
            training_status = self.multi_machine_manager.get_training_status(machine_id)
            
            # 計算連接品質（基於成功率和響應時間）
            connection_quality = self._calculate_connection_quality(machine_thread)
            
            # 計算運行時間
            uptime = time.time() - self.start_time
            
            status = MachineStatus(
                machine_id=machine_id,
                is_connected=machine_thread.is_connected,
                is_training=training_status.get("is_running", False) if training_status else False,
                training_program=training_status.get("session_info", {}).get("program_name", "") if training_status else "",
                current_shot=training_status.get("current_shot", 0) if training_status else 0,
                total_shots=training_status.get("total_shots", 0) if training_status else 0,
                connection_quality=connection_quality,
                last_shot_time=machine_thread.last_shot_time,
                total_shots_sent=machine_thread.total_shots_sent,
                successful_shots=machine_thread.successful_shots,
                failed_shots=machine_thread.failed_shots,
                error_count=getattr(machine_thread, 'error_count', 0),
                uptime=uptime,
                timestamp=time.time()
            )
            
            return status
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取 {machine_id} 狀態失敗: {e}")
            return None
    
    def _get_system_status(self) -> SystemStatus:
        """獲取系統狀態"""
        try:
            # 獲取系統資源使用情況
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 獲取網路使用情況
            network = psutil.net_io_counters()
            network_usage = (network.bytes_sent + network.bytes_recv) / (1024 * 1024)  # MB
            
            # 計算活躍連接數
            active_connections = len(self.multi_machine_manager.machines) if self.multi_machine_manager else 0
            
            # 計算總訓練會話數
            total_sessions = len(self.multi_machine_manager.training_sessions) if self.multi_machine_manager else 0
            
            # 計算系統運行時間
            system_uptime = time.time() - self.start_time
            
            status = SystemStatus(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_usage=network_usage,
                active_connections=active_connections,
                total_training_sessions=total_sessions,
                system_uptime=system_uptime,
                timestamp=time.time()
            )
            
            return status
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取系統狀態失敗: {e}")
            return None
    
    def _calculate_connection_quality(self, machine_thread) -> float:
        """計算連接品質"""
        try:
            if machine_thread.total_shots_sent == 0:
                return 1.0 if machine_thread.is_connected else 0.0
            
            # 基於成功率和連接狀態計算品質
            success_rate = machine_thread.successful_shots / machine_thread.total_shots_sent
            connection_bonus = 0.2 if machine_thread.is_connected else 0.0
            
            quality = min(1.0, success_rate + connection_bonus)
            return quality
            
        except Exception as e:
            return 0.0
    
    def _update_machine_status(self, machine_id: str, status: MachineStatus):
        """更新發球機狀態"""
        try:
            # 存儲狀態歷史
            self.machine_status_history[machine_id].append(status)
            
            # 發送信號
            self.sig_machine_status_updated.emit(machine_id, asdict(status))
            
        except Exception as e:
            self.gui.log_message(f"❌ 更新 {machine_id} 狀態失敗: {e}")
    
    def _update_system_status(self, status: SystemStatus):
        """更新系統狀態"""
        try:
            # 存儲狀態歷史
            self.system_status_history.append(status)
            
            # 發送信號
            self.sig_system_status_updated.emit(asdict(status))
            
        except Exception as e:
            self.gui.log_message(f"❌ 更新系統狀態失敗: {e}")
    
    def _calculate_performance_metrics(self):
        """計算性能指標"""
        try:
            for machine_id in self.multi_machine_manager.machine_ids:
                metrics = self._get_performance_metrics(machine_id)
                if metrics:
                    self.performance_metrics[machine_id].append(metrics)
                    self.sig_performance_updated.emit(machine_id, asdict(metrics))
            
        except Exception as e:
            self.gui.log_message(f"❌ 計算性能指標失敗: {e}")
    
    def _get_performance_metrics(self, machine_id: str) -> Optional[PerformanceMetrics]:
        """獲取性能指標"""
        try:
            status_history = self.machine_status_history[machine_id]
            if len(status_history) < 2:
                return None
            
            # 獲取最近30秒的數據
            current_time = time.time()
            recent_statuses = [
                status for status in status_history
                if current_time - status.timestamp <= 30.0
            ]
            
            if len(recent_statuses) < 2:
                return None
            
            # 計算發球速度（每分鐘）
            time_span = recent_statuses[-1].timestamp - recent_statuses[0].timestamp
            shots_span = recent_statuses[-1].total_shots_sent - recent_statuses[0].total_shots_sent
            shots_per_minute = (shots_span / time_span * 60) if time_span > 0 else 0.0
            
            # 計算成功率
            total_shots = recent_statuses[-1].total_shots_sent
            successful_shots = recent_statuses[-1].successful_shots
            success_rate = (successful_shots / total_shots) if total_shots > 0 else 0.0
            
            # 計算平均響應時間
            response_times = []
            for i in range(1, len(recent_statuses)):
                if recent_statuses[i].last_shot_time > recent_statuses[i-1].last_shot_time:
                    response_time = recent_statuses[i].timestamp - recent_statuses[i].last_shot_time
                    response_times.append(response_time)
            
            average_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            
            # 計算連接穩定性
            connection_qualities = [status.connection_quality for status in recent_statuses]
            connection_stability = sum(connection_qualities) / len(connection_qualities)
            
            # 計算錯誤率
            total_errors = recent_statuses[-1].error_count
            error_rate = (total_errors / total_shots) if total_shots > 0 else 0.0
            
            metrics = PerformanceMetrics(
                machine_id=machine_id,
                shots_per_minute=shots_per_minute,
                success_rate=success_rate,
                average_response_time=average_response_time,
                connection_stability=connection_stability,
                error_rate=error_rate,
                timestamp=time.time()
            )
            
            return metrics
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取 {machine_id} 性能指標失敗: {e}")
            return None
    
    def _health_check(self):
        """健康檢查"""
        try:
            # 檢查系統資源
            if self.system_status_history:
                latest_system = self.system_status_history[-1]
                
                if latest_system.cpu_usage > self.health_thresholds["cpu_usage"]:
                    self._trigger_alert("cpu_high", f"CPU使用率過高: {latest_system.cpu_usage:.1f}%")
                
                if latest_system.memory_usage > self.health_thresholds["memory_usage"]:
                    self._trigger_alert("memory_high", f"記憶體使用率過高: {latest_system.memory_usage:.1f}%")
            
            # 檢查發球機狀態
            for machine_id in self.multi_machine_manager.machine_ids:
                if machine_id in self.machine_status_history:
                    latest_status = self.machine_status_history[machine_id][-1]
                    
                    if latest_status.connection_quality < self.health_thresholds["connection_quality"]:
                        self._trigger_alert("connection_poor", f"{machine_id} 連接品質差: {latest_status.connection_quality:.2f}")
                    
                    if latest_status.error_count > 0:
                        error_rate = latest_status.error_count / max(1, latest_status.total_shots_sent)
                        if error_rate > self.health_thresholds["error_rate"]:
                            self._trigger_alert("error_rate_high", f"{machine_id} 錯誤率過高: {error_rate:.2%}")
            
            # 檢查性能指標
            for machine_id in self.multi_machine_manager.machine_ids:
                if machine_id in self.performance_metrics and self.performance_metrics[machine_id]:
                    latest_metrics = self.performance_metrics[machine_id][-1]
                    
                    if latest_metrics.average_response_time > self.health_thresholds["response_time"]:
                        self._trigger_alert("response_slow", f"{machine_id} 響應時間過慢: {latest_metrics.average_response_time:.2f}秒")
            
        except Exception as e:
            self.gui.log_message(f"❌ 健康檢查失敗: {e}")
    
    def _trigger_alert(self, alert_type: str, message: str):
        """觸發警報"""
        try:
            self.total_alerts += 1
            alert = {
                "type": alert_type,
                "message": message,
                "timestamp": time.time(),
                "severity": self._get_alert_severity(alert_type)
            }
            
            self.alert_history.append(alert)
            self.sig_health_alert.emit(alert_type, message)
            
            self.gui.log_message(f"⚠️ 健康警報: {message}")
            
        except Exception as e:
            self.gui.log_message(f"❌ 觸發警報失敗: {e}")
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """獲取警報嚴重程度"""
        severity_map = {
            "cpu_high": "warning",
            "memory_high": "warning",
            "connection_poor": "error",
            "error_rate_high": "error",
            "response_slow": "warning"
        }
        return severity_map.get(alert_type, "info")
    
    def get_machine_status_history(self, machine_id: str, duration: float = 300.0) -> List[Dict[str, Any]]:
        """獲取發球機狀態歷史"""
        try:
            current_time = time.time()
            history = []
            
            for status in self.machine_status_history[machine_id]:
                if current_time - status.timestamp <= duration:
                    history.append(asdict(status))
            
            return history
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取 {machine_id} 狀態歷史失敗: {e}")
            return []
    
    def get_system_status_history(self, duration: float = 300.0) -> List[Dict[str, Any]]:
        """獲取系統狀態歷史"""
        try:
            current_time = time.time()
            history = []
            
            for status in self.system_status_history:
                if current_time - status.timestamp <= duration:
                    history.append(asdict(status))
            
            return history
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取系統狀態歷史失敗: {e}")
            return []
    
    def get_performance_metrics(self, machine_id: str, duration: float = 3600.0) -> List[Dict[str, Any]]:
        """獲取性能指標"""
        try:
            current_time = time.time()
            metrics = []
            
            for metric in self.performance_metrics[machine_id]:
                if current_time - metric.timestamp <= duration:
                    metrics.append(asdict(metric))
            
            return metrics
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取 {machine_id} 性能指標失敗: {e}")
            return []
    
    def get_alert_history(self, duration: float = 3600.0) -> List[Dict[str, Any]]:
        """獲取警報歷史"""
        try:
            current_time = time.time()
            alerts = []
            
            for alert in self.alert_history:
                if current_time - alert["timestamp"] <= duration:
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取警報歷史失敗: {e}")
            return []
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """獲取監控摘要"""
        try:
            summary = {
                "is_monitoring": self.is_monitoring,
                "monitor_uptime": time.time() - self.start_time,
                "total_alerts": self.total_alerts,
                "active_machines": len(self.multi_machine_manager.machines) if self.multi_machine_manager else 0,
                "total_training_sessions": len(self.multi_machine_manager.training_sessions) if self.multi_machine_manager else 0,
                "monitor_interval": self.monitor_interval,
                "performance_interval": self.performance_interval,
                "health_check_interval": self.health_check_interval
            }
            
            return summary
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取監控摘要失敗: {e}")
            return {}


def create_status_monitor(gui_instance) -> StatusMonitor:
    """
    建立狀態監控管理器的工廠函數
    
    Args:
        gui_instance: GUI 主類別實例
        
    Returns:
        StatusMonitor 實例
    """
    return StatusMonitor(gui_instance)

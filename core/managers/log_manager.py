"""
日誌記錄管理器

這個模組負責管理系統日誌記錄，包括：
- 多級別日誌記錄
- 日誌文件管理
- 日誌查詢和過濾
- 日誌分析和統計
"""

import os
import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class LogLevel(Enum):
    """日誌級別枚舉"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日誌條目數據類別"""
    timestamp: float
    level: str
    source: str  # 來源模組或組件
    message: str
    machine_id: Optional[str] = None
    session_id: Optional[str] = None
    user_action: Optional[str] = None
    error_code: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class LogManager(QObject):
    """日誌記錄管理器"""
    
    # 信號定義
    sig_log_entry = pyqtSignal(dict)  # log_entry
    sig_log_level_changed = pyqtSignal(str)  # level
    sig_log_file_rotated = pyqtSignal(str)  # new_file_path
    
    def __init__(self, gui_instance, log_dir: str = "logs"):
        """
        初始化日誌記錄管理器
        
        Args:
            gui_instance: GUI 主類別實例
            log_dir: 日誌文件目錄
        """
        super().__init__()
        self.gui = gui_instance
        self.log_dir = log_dir
        
        # 確保日誌目錄存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 日誌配置
        self.log_level = LogLevel.INFO
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_files = 5
        self.enable_console_log = True
        self.enable_file_log = True
        
        # 日誌存儲
        self.log_entries: deque = deque(maxlen=10000)  # 記憶體中保留最近10000條
        self.log_files: List[str] = []
        self.current_log_file = None
        
        # 統計數據
        self.log_stats = {
            "total_logs": 0,
            "level_counts": defaultdict(int),
            "source_counts": defaultdict(int),
            "machine_counts": defaultdict(int),
            "error_counts": defaultdict(int)
        }
        
        # 日誌記錄器
        self.logger = None
        self._setup_logger()
        
        # 日誌輪轉定時器
        self.rotation_timer = None
        self.rotation_interval = 24 * 60 * 60 * 1000  # 24小時（毫秒）
        
        # 線程安全鎖
        self.log_lock = threading.Lock()
    
    def _setup_logger(self):
        """設置日誌記錄器"""
        try:
            # 創建日誌記錄器
            self.logger = logging.getLogger("badminton_system")
            self.logger.setLevel(getattr(logging, self.log_level.value))
            
            # 清除現有處理器
            self.logger.handlers.clear()
            
            # 創建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # 控制台處理器
            if self.enable_console_log:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(getattr(logging, self.log_level.value))
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
            
            # 文件處理器
            if self.enable_file_log:
                self._setup_file_handler()
            
            # 啟動日誌輪轉定時器
            self._start_rotation_timer()
            
        except Exception as e:
            print(f"設置日誌記錄器失敗: {e}")
    
    def _setup_file_handler(self):
        """設置文件處理器"""
        try:
            # 生成日誌文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"badminton_system_{timestamp}.log"
            log_filepath = os.path.join(self.log_dir, log_filename)
            
            # 創建文件處理器
            file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
            file_handler.setLevel(getattr(logging, self.log_level.value))
            
            # 設置格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # 添加到記錄器
            self.logger.addHandler(file_handler)
            
            # 更新當前日誌文件
            self.current_log_file = log_filepath
            self.log_files.append(log_filepath)
            
            # 限制日誌文件數量
            if len(self.log_files) > self.max_files:
                old_file = self.log_files.pop(0)
                try:
                    os.remove(old_file)
                except OSError:
                    pass
            
        except Exception as e:
            print(f"設置文件處理器失敗: {e}")
    
    def _start_rotation_timer(self):
        """啟動日誌輪轉定時器"""
        try:
            if not hasattr(self, 'rotation_interval'):
                self.rotation_interval = 24 * 60 * 60 * 1000  # 24小時（毫秒）
            
            self.rotation_timer = QTimer()
            self.rotation_timer.timeout.connect(self._rotate_log_file)
            self.rotation_timer.start(self.rotation_interval)
            
        except Exception as e:
            print(f"啟動日誌輪轉定時器失敗: {e}")
    
    def _rotate_log_file(self):
        """輪轉日誌文件"""
        try:
            if self.enable_file_log:
                # 重新設置文件處理器
                self._setup_file_handler()
                self.sig_log_file_rotated.emit(self.current_log_file)
                
        except Exception as e:
            print(f"輪轉日誌文件失敗: {e}")
    
    def set_log_level(self, level: LogLevel):
        """設置日誌級別"""
        try:
            self.log_level = level
            self.logger.setLevel(getattr(logging, level.value))
            
            # 更新所有處理器的級別
            for handler in self.logger.handlers:
                handler.setLevel(getattr(logging, level.value))
            
            self.sig_log_level_changed.emit(level.value)
            self.log(LogLevel.INFO, "LogManager", f"日誌級別已更改為: {level.value}")
            
        except Exception as e:
            print(f"設置日誌級別失敗: {e}")
    
    def log(self, level: LogLevel, source: str, message: str, 
            machine_id: Optional[str] = None, session_id: Optional[str] = None,
            user_action: Optional[str] = None, error_code: Optional[str] = None,
            extra_data: Optional[Dict[str, Any]] = None):
        """記錄日誌"""
        try:
            with self.log_lock:
                # 創建日誌條目
                log_entry = LogEntry(
                    timestamp=time.time(),
                    level=level.value,
                    source=source,
                    message=message,
                    machine_id=machine_id,
                    session_id=session_id,
                    user_action=user_action,
                    error_code=error_code,
                    extra_data=extra_data
                )
                
                # 添加到記憶體存儲
                self.log_entries.append(log_entry)
                
                # 更新統計數據
                self._update_stats(log_entry)
                
                # 記錄到標準日誌系統
                log_message = self._format_log_message(log_entry)
                getattr(self.logger, level.value.lower())(log_message)
                
                # 發送信號
                self.sig_log_entry.emit(asdict(log_entry))
                
        except Exception as e:
            print(f"記錄日誌失敗: {e}")
    
    def _format_log_message(self, log_entry: LogEntry) -> str:
        """格式化日誌訊息"""
        try:
            parts = [log_entry.message]
            
            if log_entry.machine_id:
                parts.append(f"[機器: {log_entry.machine_id}]")
            
            if log_entry.session_id:
                parts.append(f"[會話: {log_entry.session_id}]")
            
            if log_entry.user_action:
                parts.append(f"[動作: {log_entry.user_action}]")
            
            if log_entry.error_code:
                parts.append(f"[錯誤碼: {log_entry.error_code}]")
            
            return " ".join(parts)
            
        except Exception as e:
            return log_entry.message
    
    def _update_stats(self, log_entry: LogEntry):
        """更新統計數據"""
        try:
            self.log_stats["total_logs"] += 1
            self.log_stats["level_counts"][log_entry.level] += 1
            self.log_stats["source_counts"][log_entry.source] += 1
            
            if log_entry.machine_id:
                self.log_stats["machine_counts"][log_entry.machine_id] += 1
            
            if log_entry.error_code:
                self.log_stats["error_counts"][log_entry.error_code] += 1
                
        except Exception as e:
            print(f"更新統計數據失敗: {e}")
    
    def debug(self, source: str, message: str, **kwargs):
        """記錄調試日誌"""
        self.log(LogLevel.DEBUG, source, message, **kwargs)
    
    def info(self, source: str, message: str, **kwargs):
        """記錄信息日誌"""
        self.log(LogLevel.INFO, source, message, **kwargs)
    
    def warning(self, source: str, message: str, **kwargs):
        """記錄警告日誌"""
        self.log(LogLevel.WARNING, source, message, **kwargs)
    
    def error(self, source: str, message: str, **kwargs):
        """記錄錯誤日誌"""
        self.log(LogLevel.ERROR, source, message, **kwargs)
    
    def critical(self, source: str, message: str, **kwargs):
        """記錄嚴重錯誤日誌"""
        self.log(LogLevel.CRITICAL, source, message, **kwargs)
    
    def log_machine_event(self, machine_id: str, event_type: str, message: str, **kwargs):
        """記錄發球機事件"""
        self.info("MachineEvent", message, machine_id=machine_id, user_action=event_type, **kwargs)
    
    def log_training_event(self, machine_id: str, session_id: str, event_type: str, message: str, **kwargs):
        """記錄訓練事件"""
        self.info("TrainingEvent", message, machine_id=machine_id, session_id=session_id, user_action=event_type, **kwargs)
    
    def log_system_event(self, event_type: str, message: str, **kwargs):
        """記錄系統事件"""
        self.info("SystemEvent", message, user_action=event_type, **kwargs)
    
    def log_user_action(self, action: str, message: str, **kwargs):
        """記錄用戶操作"""
        self.info("UserAction", message, user_action=action, **kwargs)
    
    def log_error(self, source: str, error: Exception, machine_id: Optional[str] = None, **kwargs):
        """記錄錯誤"""
        error_message = f"{type(error).__name__}: {str(error)}"
        self.error(source, error_message, machine_id=machine_id, error_code=type(error).__name__, **kwargs)
    
    def get_logs(self, level: Optional[LogLevel] = None, source: Optional[str] = None,
                machine_id: Optional[str] = None, start_time: Optional[float] = None,
                end_time: Optional[float] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """獲取日誌條目"""
        try:
            with self.log_lock:
                logs = []
                count = 0
                
                # 從最新的日誌開始遍歷
                for log_entry in reversed(self.log_entries):
                    if count >= limit:
                        break
                    
                    # 應用過濾條件
                    if level and log_entry.level != level.value:
                        continue
                    
                    if source and log_entry.source != source:
                        continue
                    
                    if machine_id and log_entry.machine_id != machine_id:
                        continue
                    
                    if start_time and log_entry.timestamp < start_time:
                        continue
                    
                    if end_time and log_entry.timestamp > end_time:
                        continue
                    
                    logs.append(asdict(log_entry))
                    count += 1
                
                # 按時間順序排列
                logs.reverse()
                return logs
                
        except Exception as e:
            print(f"獲取日誌失敗: {e}")
            return []
    
    def get_log_stats(self) -> Dict[str, Any]:
        """獲取日誌統計"""
        try:
            stats = self.log_stats.copy()
            
            # 添加額外統計信息
            stats["memory_logs"] = len(self.log_entries)
            stats["log_files"] = len(self.log_files)
            stats["current_log_file"] = self.current_log_file
            stats["log_level"] = self.log_level.value
            stats["max_file_size"] = self.max_file_size
            stats["max_files"] = self.max_files
            
            return stats
            
        except Exception as e:
            print(f"獲取日誌統計失敗: {e}")
            return {}
    
    def search_logs(self, query: str, level: Optional[LogLevel] = None,
                   source: Optional[str] = None, machine_id: Optional[str] = None,
                   start_time: Optional[float] = None, end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """搜索日誌"""
        try:
            with self.log_lock:
                results = []
                query_lower = query.lower()
                
                for log_entry in self.log_entries:
                    # 應用過濾條件
                    if level and log_entry.level != level.value:
                        continue
                    
                    if source and log_entry.source != source:
                        continue
                    
                    if machine_id and log_entry.machine_id != machine_id:
                        continue
                    
                    if start_time and log_entry.timestamp < start_time:
                        continue
                    
                    if end_time and log_entry.timestamp > end_time:
                        continue
                    
                    # 搜索匹配
                    if (query_lower in log_entry.message.lower() or
                        query_lower in log_entry.source.lower() or
                        (log_entry.machine_id and query_lower in log_entry.machine_id.lower())):
                        results.append(asdict(log_entry))
                
                return results
                
        except Exception as e:
            print(f"搜索日誌失敗: {e}")
            return []
    
    def export_logs(self, filepath: str, level: Optional[LogLevel] = None,
                   source: Optional[str] = None, machine_id: Optional[str] = None,
                   start_time: Optional[float] = None, end_time: Optional[float] = None) -> bool:
        """導出日誌"""
        try:
            logs = self.get_logs(level, source, machine_id, start_time, end_time)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"導出日誌失敗: {e}")
            return False
    
    def clear_logs(self):
        """清除記憶體中的日誌"""
        try:
            with self.log_lock:
                self.log_entries.clear()
                self.log_stats = {
                    "total_logs": 0,
                    "level_counts": defaultdict(int),
                    "source_counts": defaultdict(int),
                    "machine_counts": defaultdict(int),
                    "error_counts": defaultdict(int)
                }
            
            self.info("LogManager", "記憶體日誌已清除")
            
        except Exception as e:
            print(f"清除日誌失敗: {e}")
    
    def get_recent_logs(self, count: int = 100) -> List[Dict[str, Any]]:
        """獲取最近的日誌"""
        try:
            with self.log_lock:
                recent_logs = []
                for log_entry in list(self.log_entries)[-count:]:
                    recent_logs.append(asdict(log_entry))
                return recent_logs
                
        except Exception as e:
            print(f"獲取最近日誌失敗: {e}")
            return []
    
    def get_log_summary(self, duration: float = 3600.0) -> Dict[str, Any]:
        """獲取日誌摘要"""
        try:
            current_time = time.time()
            start_time = current_time - duration
            
            # 獲取指定時間範圍內的日誌
            logs = self.get_logs(start_time=start_time, end_time=current_time)
            
            # 統計摘要
            summary = {
                "total_logs": len(logs),
                "level_counts": defaultdict(int),
                "source_counts": defaultdict(int),
                "machine_counts": defaultdict(int),
                "error_counts": defaultdict(int),
                "duration": duration,
                "start_time": start_time,
                "end_time": current_time
            }
            
            for log in logs:
                summary["level_counts"][log["level"]] += 1
                summary["source_counts"][log["source"]] += 1
                
                if log["machine_id"]:
                    summary["machine_counts"][log["machine_id"]] += 1
                
                if log["error_code"]:
                    summary["error_counts"][log["error_code"]] += 1
            
            return summary
            
        except Exception as e:
            print(f"獲取日誌摘要失敗: {e}")
            return {}


def create_log_manager(gui_instance, log_dir: str = "logs") -> LogManager:
    """
    建立日誌記錄管理器的工廠函數
    
    Args:
        gui_instance: GUI 主類別實例
        log_dir: 日誌文件目錄
        
    Returns:
        LogManager 實例
    """
    return LogManager(gui_instance, log_dir)

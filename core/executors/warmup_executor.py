"""
熱身執行器

這個模組負責執行熱身訓練，處理熱身的實際執行邏輯。
"""

import asyncio
from typing import List, Dict, Any, Optional
from ..parsers import get_warmup_sequence, get_warmup_title


def map_speed_to_interval(speed_text: str) -> float:
    """
    將速度文字轉換為時間間隔（秒）
    
    Args:
        speed_text: 速度文字（"慢", "正常", "快", "極限快"）
        
    Returns:
        對應的時間間隔（秒）
    """
    speed_mapping = {
        "慢": 4.0,
        "正常": 3.5,
        "快": 2.5,
        "極限快": 1.4
    }
    return speed_mapping.get(speed_text, 3.5)




class WarmupExecutor:
    """熱身執行器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化執行器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
        self.training_task = None
        self.stop_flag = False
    
    def start_warmup(self, warmup_type: str) -> bool:
        """
        開始熱身
        
        Args:
            warmup_type: 熱身類型（"basic", "advanced", "comprehensive"）
            
        Returns:
            是否成功開始熱身
        """
        # 檢查前置條件
        if not self._check_prerequisites():
            return False
        
        # 取得熱身參數
        speed_text = self._get_speed_text()
        interval = map_speed_to_interval(speed_text)
        sequence = get_warmup_sequence(warmup_type)
        title = get_warmup_title(warmup_type)
        
        if not sequence:
            self.gui.log_message("未知的熱身類型")
            return False
        
        # 檢查是否有其他訓練進行中
        if hasattr(self.gui, 'training_task') and self.gui.training_task and not self.gui.training_task.done():
            self.gui.log_message("已有訓練進行中，請先停止後再開始新熱身")
            return False
        
        # 記錄開始訊息
        self.gui.log_message(f"開始 {title} | 速度:{speed_text} | 間隔:{interval}s | 總顆數:{len(sequence)}")
        
        # 設定進度條
        self._setup_progress_bar(len(sequence))
        
        # 更新描述
        self._update_description(warmup_type)
        
        # 開始執行熱身
        self.stop_flag = False
        self.training_task = asyncio.create_task(
            self._execute_warmup(sequence, interval, title)
        )
        
        return True
    
    def stop_warmup(self):
        """停止熱身"""
        if self.training_task and not self.training_task.done():
            self.stop_flag = True
            self.training_task.cancel()
    
    def _check_prerequisites(self) -> bool:
        """檢查熱身前置條件"""
        if not hasattr(self.gui, 'bluetooth_thread') or not self.gui.bluetooth_thread:
            self.gui.log_message("請先掃描設備")
            return False
        
        if not self.gui.bluetooth_thread.is_connected:
            self.gui.log_message("請先連接發球機")
            return False
        
        return True
    
    def _get_speed_text(self) -> str:
        """取得速度設定"""
        if hasattr(self.gui, 'warmup_speed_combo'):
            return self.gui.warmup_speed_combo.currentText()
        return "正常"
    
    def _setup_progress_bar(self, total_shots: int):
        """設定進度條"""
        if hasattr(self.gui, 'warmup_progress_bar'):
            self.gui.warmup_progress_bar.setMaximum(total_shots)
            self.gui.warmup_progress_bar.setValue(0)
            self.gui.warmup_progress_bar.setVisible(True)
    
    def _update_description(self, warmup_type: str):
        """更新描述"""
        if hasattr(self.gui, 'update_warmup_description'):
            self.gui.update_warmup_description(warmup_type)
    
    async def _execute_warmup(self, sequence: List[str], interval: float, title: str):
        """執行熱身的實際邏輯"""
        try:
            sent = 0
            for section in sequence:
                if self.stop_flag:
                    raise asyncio.CancelledError()
                
                # 發送發球命令
                result = await self.gui.bluetooth_thread.send_shot(section)
                if not result:
                    self.gui.log_message("發送失敗，已中止熱身")
                    break
                
                sent += 1
                self.gui.log_message(f"{title}: 已發送 {section} 第 {sent} 顆")
                
                # 更新進度條
                if hasattr(self.gui, 'warmup_progress_bar'):
                    self.gui.warmup_progress_bar.setValue(sent)
                
                await asyncio.sleep(interval)
            
            self.gui.log_message(f"{title} 完成！")
            
        except asyncio.CancelledError:
            self.gui.log_message(f"{title} 已停止")
        except Exception as e:
            self.gui.log_message(f"{title} 執行失敗: {e}")
        finally:
            self._cleanup_warmup()
    
    def _cleanup_warmup(self):
        """清理熱身狀態"""
        # 隱藏進度條
        if hasattr(self.gui, 'warmup_progress_bar'):
            self.gui.warmup_progress_bar.setVisible(False)
        
        # 更新 GUI 的訓練任務狀態
        if hasattr(self.gui, 'training_task'):
            self.gui.training_task = None
        
        self.training_task = None


def create_warmup_executor(gui_instance) -> WarmupExecutor:
    """
    建立熱身執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        WarmupExecutor 實例
    """
    return WarmupExecutor(gui_instance)

"""
進階訓練執行器

這個模組負責執行進階訓練，處理訓練的實際執行邏輯。
"""

import asyncio
import random
from typing import Dict, Any, Optional
from ..parsers import adv_map_speed_to_interval as map_speed_to_interval
from ..parsers import parse_ball_count


class AdvancedTrainingExecutor:
    """進階訓練執行器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化執行器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
        self.training_task = None
        self.stop_flag = False
    
    def start_advanced_training(self, title: str, specs: Dict[str, Any], 
                              speed_text: str, ball_count_text: str) -> bool:
        """
        開始進階訓練
        
        Args:
            title: 訓練標題
            specs: 訓練規格
            speed_text: 速度文字
            ball_count_text: 球數文字
            
        Returns:
            是否成功開始訓練
        """
        # 檢查前置條件
        if not self._check_prerequisites():
            return False
        
        # 解析參數
        interval = map_speed_to_interval(speed_text)
        balls = parse_ball_count(ball_count_text)
        
        # 設定進度條
        self._setup_progress_bar(balls)
        
        # 記錄開始訊息
        mode_label = "隨機" if specs.get('mode') == 'random' else "依序"
        self.gui.log_message(
            f"開始進階訓練: {title} | 模式:{mode_label} | "
            f"速度:{speed_text} | 間隔:{interval}s | 總顆數:{balls}"
        )
        
        # 開始執行訓練
        self.stop_flag = False
        self.training_task = asyncio.create_task(
            self._execute_advanced_training(title, specs, interval, balls)
        )
        
        return True
    
    def stop_advanced_training(self):
        """停止進階訓練"""
        if self.training_task and not self.training_task.done():
            self.stop_flag = True
            self.training_task.cancel()
    
    def _check_prerequisites(self) -> bool:
        """檢查訓練前置條件"""
        if not hasattr(self.gui, '_advanced_specs') or not self.gui._advanced_specs:
            self.gui.log_message("進階訓練內容尚未載入或檔案解析失敗")
            return False
        
        if not self.gui.bluetooth_thread:
            self.gui.log_message("請先掃描設備")
            return False
        
        if not self.gui.bluetooth_thread.is_connected:
            self.gui.log_message("請先連接發球機")
            return False
        
        if hasattr(self.gui, 'training_task') and self.gui.training_task and not self.gui.training_task.done():
            self.gui.log_message("已有訓練進行中，請先停止後再開始")
            return False
        
        return True
    
    def _setup_progress_bar(self, total_balls: int):
        """設定進度條"""
        if hasattr(self.gui, 'advanced_progress_bar'):
            self.gui.advanced_progress_bar.setMaximum(total_balls)
            self.gui.advanced_progress_bar.setValue(0)
            self.gui.advanced_progress_bar.setVisible(True)
    
    async def _execute_advanced_training(self, title: str, spec: Dict[str, Any], 
                                       interval: float, total_balls: int):
        """執行進階訓練的實際邏輯"""
        try:
            sent = 0
            sections = spec.get("sections", [])
            mode = spec.get("mode")
            
            while sent < total_balls:
                if self.stop_flag:
                    raise asyncio.CancelledError()
                
                # 選擇發球點位
                if mode == "sequence":
                    section = sections[sent % len(sections)]
                else:
                    section = random.choice(sections)
                
                # 發送發球命令
                result = await self.gui.bluetooth_thread.send_shot(section)
                if not result:
                    self.gui.log_message("發送失敗，已中止進階訓練")
                    break
                
                sent += 1
                self.gui.log_message(f"{title}: 已發送 {section} 第 {sent} 顆")
                
                # 更新進度條
                if hasattr(self.gui, 'advanced_progress_bar'):
                    self.gui.advanced_progress_bar.setValue(sent)
                
                await asyncio.sleep(interval)
            else:
                self.gui.log_message(f"{title} 完成！")
                
        except asyncio.CancelledError:
            self.gui.log_message(f"{title} 已停止")
        except Exception as e:
            self.gui.log_message(f"{title} 執行失敗: {e}")
        finally:
            self._cleanup_training()
    
    def _cleanup_training(self):
        """清理訓練狀態"""
        if hasattr(self.gui, 'advanced_progress_bar'):
            self.gui.advanced_progress_bar.setVisible(False)
        
        # 更新 GUI 的訓練任務狀態
        if hasattr(self.gui, 'training_task'):
            self.gui.training_task = None
        
        self.training_task = None


def create_advanced_training_executor(gui_instance) -> AdvancedTrainingExecutor:
    """
    建立進階訓練執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        AdvancedTrainingExecutor 實例
    """
    return AdvancedTrainingExecutor(gui_instance)

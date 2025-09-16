"""
基礎訓練執行器

這個模組負責執行基礎訓練，處理訓練的實際執行邏輯。
"""

import asyncio
import time
from typing import Dict, Any, Optional
from ..parsers import (
    basic_map_speed_to_interval as map_speed_to_interval, 
    map_count_to_number, 
    get_section_by_shot_name, 
    get_shot_name_by_section
)


class BasicTrainingExecutor:
    """基礎訓練執行器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化執行器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
        self.training_task = None
        self.stop_flag = False
    
    def start_selected_training(self, section: str, speed_text: str, count_text: str) -> bool:
        """
        開始選定的訓練
        
        Args:
            section: 區域代碼
            speed_text: 速度文字
            count_text: 球數文字
            
        Returns:
            是否成功開始訓練
        """
        # 檢查前置條件
        if not self._check_prerequisites():
            return False
        
        # 解析參數
        interval = map_speed_to_interval(speed_text)
        num_shots = map_count_to_number(count_text)
        
        # 取得球種名稱
        shot_name = get_shot_name_by_section(section)
        display_name = shot_name or section
        
        # 記錄開始訊息
        self.gui.log_message(
            f"開始執行單一球路: {display_name} | "
            f"速度:{speed_text} | 間隔:{interval}s | 球數:{num_shots}"
        )
        
        # 設定進度條
        self._setup_progress_bar(num_shots)
        
        # 開始執行訓練
        self.stop_flag = False
        self.training_task = self.gui.create_async_task(
            self._execute_training(section, interval, num_shots, display_name)
        )
        
        # 同步設置主GUI的訓練任務，保持與舊版本一致
        self.gui.training_task = self.training_task
        
        return True
    
    def practice_specific_shot(self, shot_name: str, count: int, interval: float) -> bool:
        """
        練習特定球種
        
        Args:
            shot_name: 球種名稱
            count: 球數
            interval: 間隔時間
            
        Returns:
            是否成功開始練習
        """
        # 取得對應的區域代碼
        section = get_section_by_shot_name(shot_name)
        if not section:
            self.gui.log_message(f"無法找到擊球項目: {shot_name}")
            return False
        
        # 記錄開始訊息
        self.gui.log_message(f"開始練習 {shot_name}，共 {count} 顆球，間隔 {interval} 秒")
        
        # 執行練習
        for i in range(count):
            if self.stop_flag:
                break
            
            try:
                # 發送發球命令
                if hasattr(self.gui, 'bluetooth_thread') and self.gui.bluetooth_thread:
                    self.gui.create_async_task(self.gui.bluetooth_thread.send_shot(section))
                else:
                    self.gui.log_message("藍牙連接不可用")
                    return False
                
                self.gui.log_message(f"已發送 {shot_name} 第 {i+1} 顆")
                time.sleep(interval)
            except Exception as e:
                self.gui.log_message(f"發球失敗: {e}")
                return False
        
        self.gui.log_message(f"完成 {shot_name} 的練習，共發送 {count} 顆球")
        return True
    
    def practice_level_programs(self, level: int, programs_data: Dict[str, Any]) -> bool:
        """
        練習特定等級的所有訓練套餐
        
        Args:
            level: 等級
            programs_data: 訓練套餐數據
            
        Returns:
            是否成功開始練習
        """
        # 獲取該等級的所有訓練套餐
        level_key = f"level{level}_basic"
        if level_key not in programs_data.get("program_categories", {}):
            self.gui.log_message(f"無法找到等級 {level} 的訓練套餐")
            return False
        
        # 遍歷並練習每個套餐
        for program_id in programs_data["program_categories"][level_key]:
            if program_id in programs_data.get("training_programs", {}):
                program = programs_data["training_programs"][program_id]
                self.gui.log_message(f"開始練習套餐: {program.get('name', program_id)}")
                
                for shot in program.get('shots', []):
                    if self.stop_flag:
                        return False
                    
                    try:
                        # 發送發球命令
                        if hasattr(self.gui, 'bluetooth_thread') and self.gui.bluetooth_thread:
                            self.gui.create_async_task(self.gui.bluetooth_thread.send_shot(shot['section']))
                        else:
                            self.gui.log_message("藍牙連接不可用")
                            return False
                        
                        self.gui.log_message(f"已發送 {shot.get('description', shot['section'])}")
                        time.sleep(shot.get('delay_seconds', 3.5))
                    except Exception as e:
                        self.gui.log_message(f"發球失敗: {e}")
                        return False
        
        return True
    
    def stop_training(self):
        """停止訓練"""
        self.stop_flag = True
        try:
            if self.training_task and not self.training_task.done():
                self.training_task.cancel()
            # 調用主GUI的停止方法以確保UI狀態正確更新
            if hasattr(self.gui, 'stop_training'):
                self.gui.stop_training()
        except Exception:
            pass
    
    def _check_prerequisites(self) -> bool:
        """檢查訓練前置條件"""
        if not hasattr(self.gui, 'bluetooth_thread') or not self.gui.bluetooth_thread:
            self.gui.log_message("請先掃描設備")
            return False
        
        if not self.gui.bluetooth_thread.is_connected:
            self.gui.log_message("請先連接發球機")
            return False
        
        if hasattr(self.gui, 'training_task') and self.gui.training_task and not self.gui.training_task.done():
            self.gui.log_message("已有訓練進行中，請先停止後再開始")
            return False
        
        return True
    
    def _setup_progress_bar(self, total_shots: int):
        """設定進度條"""
        # 使用基礎訓練專用的進度條
        if hasattr(self.gui, 'basic_training_progress_bar'):
            self.gui.basic_training_progress_bar.setMaximum(total_shots)
            self.gui.basic_training_progress_bar.setValue(0)
            self.gui.basic_training_progress_bar.setVisible(True)
        
        # 顯示進度文字標籤
        if hasattr(self.gui, 'basic_training_progress_label'):
            self.gui.basic_training_progress_label.setText(f"準備開始訓練，共 {total_shots} 顆球")
            self.gui.basic_training_progress_label.setVisible(True)
        
        # 更新按鈕狀態
        if hasattr(self.gui, 'start_training_button'):
            self.gui.start_training_button.setEnabled(False)
        if hasattr(self.gui, 'stop_training_button'):
            self.gui.stop_training_button.setEnabled(True)
    
    async def _execute_training(self, section: str, interval: float, num_shots: int, display_name: str):
        """執行訓練的實際邏輯"""
        try:
            sent_count = 0
            
            for _ in range(num_shots):
                if self.stop_flag:
                    self.gui.log_message("訓練已被停止")
                    break
                
                if not self.gui.bluetooth_thread or not self.gui.bluetooth_thread.is_connected:
                    self.gui.log_message("請先連接發球機")
                    break
                
                try:
                    await self.gui.bluetooth_thread.send_shot(section)
                except Exception as e:
                    self.gui.log_message(f"發球失敗: {e}")
                    break
                
                sent_count += 1
                self.gui.log_message(f"已發送 {section} 第 {sent_count} 顆")
                
                # 更新進度條
                if hasattr(self.gui, 'basic_training_progress_bar'):
                    self.gui.basic_training_progress_bar.setValue(sent_count)
                
                # 更新進度文字
                if hasattr(self.gui, 'basic_training_progress_label'):
                    self.gui.basic_training_progress_label.setText(f"已發送 {sent_count}/{num_shots} 顆球")
                
                await asyncio.sleep(interval)
            
            self.gui.log_message(f"完成 {display_name} 的訓練，共發送 {sent_count} 顆球")
            
        except asyncio.CancelledError:
            self.gui.log_message("訓練已被停止")
        except Exception as e:
            self.gui.log_message(f"訓練執行失敗: {e}")
        finally:
            self._cleanup_training()
    
    def _cleanup_training(self):
        """清理訓練狀態"""
        # 更新按鈕狀態
        if hasattr(self.gui, 'start_training_button'):
            self.gui.start_training_button.setEnabled(True)
        if hasattr(self.gui, 'stop_training_button'):
            self.gui.stop_training_button.setEnabled(False)
        
        # 隱藏進度條
        if hasattr(self.gui, 'basic_training_progress_bar'):
            self.gui.basic_training_progress_bar.setVisible(False)
        if hasattr(self.gui, 'basic_training_progress_label'):
            self.gui.basic_training_progress_label.setVisible(False)
        
        # 更新 GUI 的訓練任務狀態
        if hasattr(self.gui, 'training_task'):
            self.gui.training_task = None
        
        self.training_task = None


def create_basic_training_executor(gui_instance) -> BasicTrainingExecutor:
    """
    建立基礎訓練執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        BasicTrainingExecutor 實例
    """
    return BasicTrainingExecutor(gui_instance)

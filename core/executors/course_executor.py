"""
課程執行器

這個模組負責執行各種訓練命令，處理命令的實際執行邏輯。
"""

import asyncio
from typing import Dict, Any, Optional


class CourseExecutor:
    """課程執行器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化執行器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
    
    def execute_training_command(self, command: Dict[str, Any], programs_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        根據用戶的指令，執行相應的訓練操作
        
        Args:
            command: 用戶的指令，包含訓練類型、項目、數量、間隔等信息
            programs_data: 訓練套餐的數據
            
        Returns:
            是否成功執行命令
        """
        try:
            command_type = command.get('type')
            
            if command_type == 'specific_shot':
                return self._execute_specific_shot(command)
            elif command_type == 'stop':
                return self._execute_stop()
            elif command_type == 'scan':
                return self._execute_scan()
            elif command_type == 'connect':
                return self._execute_connect()
            elif command_type == 'disconnect':
                return self._execute_disconnect()
            elif command_type == 'start_warmup':
                return self._execute_start_warmup(command)
            elif command_type == 'start_advanced':
                return self._execute_start_advanced(command)
            elif command_type == 'start_current':
                return self._execute_start_current(command)
            elif command_type == 'level_program':
                return self._execute_level_program(command, programs_data)
            else:
                self.gui.log_message("未知的指令類型")
                return False
                
        except Exception as e:
            self.gui.log_message(f"執行命令時發生錯誤: {str(e)}")
            return False
    
    def _execute_specific_shot(self, command: Dict[str, Any]) -> bool:
        """執行特定球種練習"""
        shot_name = command.get('shot_name')
        count = command.get('count')
        interval = command.get('interval')
        
        if not all([shot_name, count, interval]):
            self.gui.log_message("特定球種練習參數不完整")
            return False
        
        # 使用基礎訓練執行器
        if not hasattr(self.gui, 'basic_training_executor'):
            from .basic_training_executor import create_basic_training_executor
            self.gui.basic_training_executor = create_basic_training_executor(self.gui)
        
        return self.gui.basic_training_executor.practice_specific_shot(shot_name, count, interval)
    
    def _execute_stop(self) -> bool:
        """停止目前訓練"""
        try:
            if hasattr(self.gui, 'stop_training'):
                self.gui.stop_training()
            return True
        except Exception as e:
            self.gui.log_message(f"停止訓練時發生錯誤: {str(e)}")
            return False
    
    def _execute_scan(self) -> bool:
        """掃描發球機"""
        try:
            if hasattr(self.gui, 'scan_devices'):
                asyncio.create_task(self.gui.scan_devices())
            return True
        except Exception as e:
            self.gui.log_message(f"掃描設備時發生錯誤: {str(e)}")
            return False
    
    def _execute_connect(self) -> bool:
        """連接當前選擇的發球機"""
        try:
            if hasattr(self.gui, 'connect_device'):
                asyncio.create_task(self.gui.connect_device())
            return True
        except Exception as e:
            self.gui.log_message(f"連接設備時發生錯誤: {str(e)}")
            return False
    
    def _execute_disconnect(self) -> bool:
        """斷開當前連線"""
        try:
            if hasattr(self.gui, 'disconnect_device'):
                asyncio.create_task(self.gui.disconnect_device())
            return True
        except Exception as e:
            self.gui.log_message(f"斷開連接時發生錯誤: {str(e)}")
            return False
    
    def _execute_start_warmup(self, command: Dict[str, Any]) -> bool:
        """執行熱身"""
        try:
            warmup_type = command.get('warmup_type', 'basic')
            speed = command.get('speed')
            
            # 設定速度選項
            if speed and hasattr(self.gui, 'warmup_speed_combo'):
                if speed in ["慢", "正常", "快", "極限快"]:
                    self.gui.warmup_speed_combo.setCurrentText(speed)
            
            # 開始熱身
            if hasattr(self.gui, 'start_warmup'):
                self.gui.start_warmup(warmup_type)
            
            return True
        except Exception as e:
            self.gui.log_message(f"開始熱身時發生錯誤: {str(e)}")
            return False
    
    def _execute_start_advanced(self, command: Dict[str, Any]) -> bool:
        """執行進階訓練"""
        try:
            title = command.get('title')
            speed = command.get('speed')
            balls = command.get('balls')
            
            # 設定標題選項
            if title and hasattr(self.gui, 'advanced_combo') and self.gui.advanced_combo.count():
                for idx in range(self.gui.advanced_combo.count()):
                    if self.gui.advanced_combo.itemText(idx) == title:
                        self.gui.advanced_combo.setCurrentIndex(idx)
                        break
            
            # 設定速度選項
            if speed and hasattr(self.gui, 'advanced_speed_combo'):
                if speed in ["慢", "正常", "快", "極限快"]:
                    self.gui.advanced_speed_combo.setCurrentText(speed)
            
            # 設定球數選項
            if balls and hasattr(self.gui, 'advanced_ball_count_combo'):
                label = f"{int(balls)}顆" if int(balls) in [10, 20, 30] else None
                if label:
                    self.gui.advanced_ball_count_combo.setCurrentText(label)
            
            # 開始進階訓練
            if hasattr(self.gui, 'start_advanced_training'):
                self.gui.start_advanced_training()
            
            return True
        except Exception as e:
            self.gui.log_message(f"開始進階訓練時發生錯誤: {str(e)}")
            return False
    
    def _execute_start_current(self, command: Dict[str, Any]) -> bool:
        """執行當前選定的訓練"""
        try:
            speed = command.get('speed')
            balls = command.get('balls')
            
            # 設定速度選項
            if speed and hasattr(self.gui, 'speed_combo'):
                if speed in ["慢", "正常", "快", "極限快"]:
                    self.gui.speed_combo.setCurrentText(speed)
            
            # 設定球數選項
            if balls and hasattr(self.gui, 'ball_count_combo'):
                label = f"{int(balls)}顆" if int(balls) in [10, 20, 30] else None
                if label:
                    self.gui.ball_count_combo.setCurrentText(label)
            
            # 開始訓練
            if hasattr(self.gui, 'start_training'):
                self.gui.start_training()
            
            return True
        except Exception as e:
            self.gui.log_message(f"開始當前訓練時發生錯誤: {str(e)}")
            return False
    
    def _execute_level_program(self, command: Dict[str, Any], programs_data: Optional[Dict[str, Any]]) -> bool:
        """執行特定等級的套餐練習"""
        try:
            level = command.get('level')
            if not level or not programs_data:
                self.gui.log_message("等級套餐練習參數不完整")
                return False
            
            # 使用基礎訓練執行器
            if not hasattr(self.gui, 'basic_training_executor'):
                from .basic_training_executor import create_basic_training_executor
                self.gui.basic_training_executor = create_basic_training_executor(self.gui)
            
            return self.gui.basic_training_executor.practice_level_programs(level, programs_data)
            
        except Exception as e:
            self.gui.log_message(f"執行等級套餐時發生錯誤: {str(e)}")
            return False


def create_course_executor(gui_instance) -> CourseExecutor:
    """
    建立課程執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        CourseExecutor 實例
    """
    return CourseExecutor(gui_instance)

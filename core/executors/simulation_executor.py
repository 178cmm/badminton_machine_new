"""
模擬對打模式執行器

這個模組負責執行模擬對打模式的訓練，包括單發球機和雙發球機的對打模擬。
"""

import asyncio
import json
import random
import time
from typing import Dict, Any, Optional, List
from queue import Queue, Empty
import sys
import os

# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params
from core.utils.shot_selector import ShotZoneSelector


class SimulationExecutor:
    """模擬對打模式執行器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化模擬對打執行器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
        self.bluetooth_thread = None
        self.training_task = None
        self.stop_flag = False
        self.pitch_queue = Queue()
        self.previous_sec = None
        self.json_data = None
        self.selector = ShotZoneSelector()
        
        # 載入發球區域數據
        self._load_area_data()
    
    def _load_area_data(self):
        """載入發球區域數據"""
        try:
            # 優先使用 hit_area.json，如果不存在則使用 area.json
            if os.path.exists("hit_area.json"):
                self.json_data = read_data_from_json("hit_area.json")
            else:
                self.json_data = read_data_from_json("area.json")
            
            if not self.json_data:
                self.gui.log_message("❌ 無法載入發球區域數據")
        except Exception as e:
            self.gui.log_message(f"❌ 載入發球區域數據失敗: {e}")
    
    def start_simulation(self, level: int, use_dual_machine: bool = False) -> bool:
        """
        開始模擬對打
        
        Args:
            level: 球員等級 (1-12)
            use_dual_machine: 是否使用雙發球機
            
        Returns:
            是否成功開始模擬
        """
        try:
            if not self.json_data:
                self.gui.log_message("❌ 發球區域數據未載入")
                return False
            
            # 檢查藍牙連接
            if not self._check_bluetooth_connection():
                return False
            
            # 獲取訓練參數
            difficulty, interval, serve_type = self._get_training_params(level)
            
            self.gui.log_message(f"🎯 開始模擬對打 - 等級: {level}, 難度: {difficulty}, 間隔: {interval}s")
            self.gui.log_message(f"📊 球路類型: {self._get_serve_type_label(serve_type)}")
            
            if use_dual_machine:
                # 使用雙發球機模式
                self.gui.log_message("🔄 使用雙發球機模式")
                return self._start_dual_machine_simulation(level, difficulty, interval, serve_type)
            else:
                # 使用單發球機模式
                self.gui.log_message("🔄 使用單發球機模式")
                
                # 重置狀態
                self.stop_flag = False
                self.previous_sec = None
                
                # 開始訓練任務
                self.training_task = asyncio.create_task(
                    self._run_simulation(difficulty, interval, serve_type)
                )
                
                return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 開始模擬對打失敗: {e}")
            return False
    
    def _start_dual_machine_simulation(self, level: int, difficulty: int, interval: float, serve_type: int) -> bool:
        """
        開始雙發球機模擬對打
        
        Args:
            level: 球員等級
            difficulty: 難度等級
            interval: 發球間隔
            serve_type: 球路類型
            
        Returns:
            是否成功開始
        """
        try:
            # 創建雙發球機執行器
            if not hasattr(self.gui, 'dual_machine_executor'):
                from .dual_machine_executor import create_dual_machine_executor
                self.gui.dual_machine_executor = create_dual_machine_executor(self.gui)
            
            # 開始雙發球機模擬對打
            return self.gui.dual_machine_executor.start_dual_simulation(level)
            
        except Exception as e:
            self.gui.log_message(f"❌ 開始雙發球機模擬對打失敗: {e}")
            return False
    
    def stop_simulation(self) -> bool:
        """
        停止模擬對打
        
        Returns:
            是否成功停止
        """
        try:
            self.stop_flag = True
            
            # 停止單發球機模擬
            if self.training_task and not self.training_task.done():
                self.training_task.cancel()
            
            # 停止雙發球機模擬
            if hasattr(self.gui, 'dual_machine_executor'):
                self.gui.dual_machine_executor.stop_dual_simulation()
            
            self.gui.log_message("🛑 模擬對打已停止")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止模擬對打失敗: {e}")
            return False
    
    def _check_bluetooth_connection(self) -> bool:
        """檢查藍牙連接狀態"""
        if not hasattr(self.gui, 'bluetooth_thread') or not self.gui.bluetooth_thread:
            self.gui.log_message("❌ 請先連接發球機")
            return False
        
        if not self.gui.bluetooth_thread.is_connected:
            self.gui.log_message("❌ 發球機未連接")
            return False
        
        self.bluetooth_thread = self.gui.bluetooth_thread
        return True
    
    def _get_training_params(self, level: int) -> tuple:
        """
        根據等級獲取訓練參數
        
        Args:
            level: 球員等級 (1-12)
            
        Returns:
            (difficulty, interval, serve_type)
        """
        # 對應等級 1~12 到難度 0~3 的查表
        difficulty_table = [
            0, 0,  # 1, 2 → 容易（Easy）
            1, 1,  # 3, 4 → 普通（Normal）
            2, 2,  # 5, 6 → 困難（Hard）
            3, 3,  # 7, 8 → 瘋狂（Crazy）
            2, 2,  # 9,10 → 困難（Hard）
            3, 3   # 11,12 → 瘋狂（Crazy）
        ]
        
        interval_table = [
            3, 2.5,    # 1, 2
            2.5, 2,    # 3, 4
            2, 1.5,    # 5, 6
            1.5, 1,    # 7, 8
            2, 1.5,    # 9, 10
            1.5, 1     # 11, 12
        ]
        
        serve_type_table = [
            0,  # level 1 - 全部高球
            0,  # level 2 - 全部高球
            1,  # level 3 - 後高前低
            1,  # level 4 - 後高前低
            1,  # level 5 - 後高前低
            1,  # level 6 - 後高前低
            2,  # level 7 - 後高中殺前低
            2,  # level 8 - 後高中殺前低
            2,  # level 9 - 後高中殺前低
            2,  # level 10 - 後高中殺前低
            2,  # level 11 - 後高中殺前低
            2   # level 12 - 後高中殺前低
        ]
        
        return (
            difficulty_table[level - 1],
            interval_table[level - 1],
            serve_type_table[level - 1]
        )
    
    def _get_serve_type_label(self, serve_type: int) -> str:
        """獲取球路類型標籤"""
        labels = {
            0: "全部高球",
            1: "後高前低",
            2: "後高中殺前低"
        }
        return labels.get(serve_type, "未知")
    
    def _generate_pitch_areas(self, difficulty: int) -> tuple:
        """
        生成發球區域
        
        Args:
            difficulty: 難度等級 (0-3)
            
        Returns:
            (current_sec, next_sec)
        """
        # 根據是否已有前一個發球區域來選擇當前區域
        if self.previous_sec is None:
            # 如果沒有前一個發球區域，隨機分配一個區域
            current_sec = f'sec{random.randint(1, 25)}'
        else:
            # 如果有前一個發球區域，使用它作為當前區域
            current_sec = self.previous_sec
        
        # 根據當前區域和難度，使用 selector 取得可攻擊區域
        first_targets = self.selector.get_available_targets(current_sec, difficulty)
        
        # 從第一步的可攻擊區域中隨機選出下一個發球位置
        next_sec = random.choice(first_targets)
        second_targets = self.selector.get_available_targets(next_sec, difficulty)
        next_start = random.choice(second_targets)
        
        # 記錄本次的發球區域，為下次使用
        self.previous_sec = next_start
        
        return current_sec, next_sec
    
    def _get_params_from_zone(self, zone: str, serve_type: int) -> Optional[bytearray]:
        """
        從區域獲取發球參數
        
        Args:
            zone: 發球區域
            serve_type: 球路類型
            
        Returns:
            發球參數
        """
        try:
            # 使用單發球機的參數
            section_data = self.json_data.get("serve_types_one", {}).get(str(serve_type), {})
            if not section_data:
                section_data = self.json_data.get("section", {})
            
            params_str = section_data.get(zone)
            if not params_str:
                self.gui.log_message(f"❌ 找不到區域 {zone} 的參數")
                return None
            
            # 解析參數
            params = [int(x.strip(), 16) for x in params_str.split(",")]
            if len(params) < 4:
                self.gui.log_message(f"❌ 區域 {zone} 參數格式錯誤")
                return None
            
            # 創建發球指令
            command = create_shot_command(params[0], params[1], params[2], params[3])
            return command
            
        except Exception as e:
            self.gui.log_message(f"❌ 處理區域 {zone} 參數失敗: {e}")
            return None
    
    async def _run_simulation(self, difficulty: int, interval: float, serve_type: int):
        """
        執行模擬對打
        
        Args:
            difficulty: 難度等級
            interval: 發球間隔
            serve_type: 球路類型
        """
        try:
            self.gui.log_message("🚀 模擬對打開始")
            
            while not self.stop_flag:
                # 生成發球區域
                current_sec, next_sec = self._generate_pitch_areas(difficulty)
                
                # 獲取發球參數
                params = self._get_params_from_zone(current_sec, serve_type)
                if not params:
                    await asyncio.sleep(1)
                    continue
                
                # 發送發球指令
                await self._send_shot_command(params)
                self.gui.log_message(f"🎯 發球區域: {current_sec}")
                
                # 等待發球完成
                await self._wait_for_shot_completion()
                
                if self.stop_flag:
                    break
                
                # 等待間隔時間
                await asyncio.sleep(interval)
                
                # 準備下一球
                self.gui.log_message(f"🔄 準備下一球: {next_sec}")
            
            self.gui.log_message("✅ 模擬對打結束")
            
        except asyncio.CancelledError:
            self.gui.log_message("🛑 模擬對打被取消")
        except Exception as e:
            self.gui.log_message(f"❌ 模擬對打執行錯誤: {e}")
    
    async def _send_shot_command(self, params: bytearray):
        """
        發送發球指令
        
        Args:
            params: 發球參數
        """
        try:
            if self.bluetooth_thread and self.bluetooth_thread.is_connected:
                await self.bluetooth_thread.send_shot_command(params)
                self.gui.log_message("✅ 發球指令已發送")
            else:
                self.gui.log_message("❌ 發球機未連接")
        except Exception as e:
            self.gui.log_message(f"❌ 發送發球指令失敗: {e}")
    
    async def _wait_for_shot_completion(self):
        """等待發球完成"""
        try:
            # 等待發球完成通知
            if hasattr(self.bluetooth_thread, 'wait_for_shot_completion'):
                await self.bluetooth_thread.wait_for_shot_completion()
            else:
                # 如果沒有等待機制，等待固定時間
                await asyncio.sleep(2)
        except Exception as e:
            self.gui.log_message(f"❌ 等待發球完成失敗: {e}")


def create_simulation_executor(gui_instance) -> SimulationExecutor:
    """
    建立模擬對打執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        SimulationExecutor 實例
    """
    return SimulationExecutor(gui_instance)

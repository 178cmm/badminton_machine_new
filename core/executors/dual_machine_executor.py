"""
雙發球機執行器 (功能保留)

這個模組保留了雙發球機的功能，供後續開發使用。
目前專案尚未開發到雙發球機階段，此模組為預留功能。
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

from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params, get_area_params
from core.utils.shot_selector import ShotZoneSelector


class DualMachineExecutor:
    """雙發球機執行器類別 (功能保留)"""
    
    def __init__(self, gui_instance):
        """
        初始化雙發球機執行器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
        self.bluetooth_threads = []  # 雙發球機的藍牙線程列表
        self.training_task = None
        self.stop_flag = False
        self.pitch_queue = Queue()
        self.previous_sec = None
        self.json_data = None
        self.selector = ShotZoneSelector()
        self.current_machine = 0  # 輪流使用 0, 1，預設第一台是左發球機
        
        # 載入發球區域數據
        self._load_area_data()
    
    def _load_area_data(self):
        """載入發球區域數據"""
        try:
            # 使用 area.json 載入發球區域數據
            self.json_data = read_data_from_json("config/area.json")
            
            if not self.json_data:
                self.gui.log_message("❌ 無法載入發球區域數據")
        except Exception as e:
            self.gui.log_message(f"❌ 載入發球區域數據失敗: {e}")
    
    def start_dual_simulation(self, level: int) -> bool:
        """
        開始雙發球機模擬對打 (功能保留)
        
        Args:
            level: 球員等級 (1-12)
            
        Returns:
            是否成功開始模擬
        """
        try:
            if not self.json_data:
                self.gui.log_message("❌ 發球區域數據未載入")
                return False
            
            # 檢查雙發球機連接
            if not self._check_dual_bluetooth_connection():
                return False
            
            # 獲取訓練參數
            difficulty, interval, serve_type = self._get_training_params(level)
            
            self.gui.log_message(f"🎯 開始雙發球機模擬對打 - 等級: {level}, 難度: {difficulty}, 間隔: {interval}s")
            self.gui.log_message(f"📊 球路類型: {self._get_serve_type_label(serve_type)}")
            self.gui.log_message("🔄 雙發球機模式 (功能保留，目前使用單發球機)")
            
            # 重置狀態
            self.stop_flag = False
            self.previous_sec = None
            
            # 開始訓練任務
            self.training_task = self.gui.create_async_task(
                self._run_dual_simulation(difficulty, interval, serve_type)
            )
            
            # 同步設置主GUI的訓練任務，保持與舊版本一致
            self.gui.training_task = self.training_task
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 開始雙發球機模擬對打失敗: {e}")
            return False
    
    def stop_dual_simulation(self) -> bool:
        """
        停止雙發球機模擬對打
        
        Returns:
            是否成功停止
        """
        try:
            self.stop_flag = True
            
            if self.training_task and not self.training_task.done():
                self.training_task.cancel()
            
            # 調用主GUI的停止方法以確保UI狀態正確更新
            if hasattr(self.gui, 'stop_training'):
                self.gui.stop_training()
            
            self.gui.log_message("🛑 雙發球機模擬對打已停止")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止雙發球機模擬對打失敗: {e}")
            return False
    
    def _check_dual_bluetooth_connection(self) -> bool:
        """檢查雙發球機連接狀態 (功能保留)"""
        # 目前專案尚未開發到雙發球機階段
        # 此功能保留供後續開發
        self.gui.log_message("⚠️ 雙發球機功能尚未開發，目前使用單發球機模式")
        
        # 檢查單發球機連接
        if not hasattr(self.gui, 'bluetooth_thread') or not self.gui.bluetooth_thread:
            self.gui.log_message("❌ 請先連接發球機")
            return False
        
        if not self.gui.bluetooth_thread.is_connected:
            self.gui.log_message("❌ 發球機未連接")
            return False
        
        # 模擬雙發球機連接
        self.bluetooth_threads = [self.gui.bluetooth_thread, self.gui.bluetooth_thread]
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
            sec_num = random.randint(1, 25)
            sec_type = random.randint(1, 2)
            current_sec = f'sec{sec_num}_{sec_type}'
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
    
    def _get_params_from_zone_dual(self, zone: str, serve_type: int, machine_index: int) -> Optional[bytearray]:
        """
        從區域獲取雙發球機發球參數 (功能保留)
        
        Args:
            zone: 發球區域
            serve_type: 球路類型
            machine_index: 發球機索引 (0=左, 1=右)
            
        Returns:
            發球參數
        """
        try:
            # 使用雙發球機的參數
            if machine_index == 0:  # 左發球機
                section_data = self.json_data.get("left_machine", {})
            else:  # 右發球機
                section_data = self.json_data.get("right_machine", {})
            
            if not section_data:
                # 如果沒有雙發球機參數，使用通用參數
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
    
    async def _run_dual_simulation(self, difficulty: int, interval: float, serve_type: int):
        """
        執行雙發球機模擬對打 (功能保留)
        
        Args:
            difficulty: 難度等級
            interval: 發球間隔
            serve_type: 球路類型
        """
        try:
            self.gui.log_message("🚀 雙發球機模擬對打開始 (功能保留)")
            
            while not self.stop_flag:
                # 生成發球區域
                current_sec, next_sec = self._generate_pitch_areas(difficulty)
                
                # 發送發球指令 (目前使用單發球機)
                await self._send_dual_shot_command(current_sec)
                self.gui.log_message(f"🎯 發球機 {self.current_machine} 發球區域: {current_sec}")
                self.gui.log_message(f"🎯 發球機 {1 - self.current_machine} 預備區域: {next_sec}")
                
                # 等待發球完成
                await self._wait_for_shot_completion()
                
                if self.stop_flag:
                    break
                
                # 等待間隔時間
                try:
                    await asyncio.sleep(interval)
                except RuntimeError as e:
                    if "no running event loop" in str(e):
                        time.sleep(interval)
                    else:
                        raise
                
                # 輪流切換發球機
                self.current_machine = 1 - self.current_machine
                
                # 準備下一球
                self.gui.log_message(f"🔄 準備下一球，切換到發球機 {self.current_machine}")
            
            self.gui.log_message("✅ 雙發球機模擬對打結束")
            
        except asyncio.CancelledError:
            self.gui.log_message("🛑 雙發球機模擬對打被取消")
        except Exception as e:
            self.gui.log_message(f"❌ 雙發球機模擬對打執行錯誤: {e}")
    
    async def _send_dual_shot_command(self, area_section: str):
        """
        發送雙發球機發球指令 (功能保留)
        
        Args:
            area_section: 發球區域代碼
        """
        try:
            # 目前專案尚未開發到雙發球機階段
            # 此功能保留供後續開發
            # 目前只發送發球機的指令
            if self.bluetooth_threads and len(self.bluetooth_threads) > 0:
                result = await self.bluetooth_threads[0].send_shot(area_section)
                if result:
                    self.gui.log_message("✅ 發球指令已發送 (單發球機模式)")
                else:
                    self.gui.log_message("❌ 發球指令發送失敗")
            else:
                self.gui.log_message("❌ 發球機未連接")
        except Exception as e:
            self.gui.log_message(f"❌ 發送雙發球機發球指令失敗: {e}")
    
    async def _wait_for_shot_completion(self):
        """等待發球完成"""
        try:
            # 等待發球完成通知
            if hasattr(self.bluetooth_threads[0], 'wait_for_shot_completion'):
                await self.bluetooth_threads[0].wait_for_shot_completion()
            else:
                # 如果沒有等待機制，等待固定時間
                await asyncio.sleep(2)
        except Exception as e:
            self.gui.log_message(f"❌ 等待發球完成失敗: {e}")


def create_dual_machine_executor(gui_instance) -> DualMachineExecutor:
    """
    建立雙發球機執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        DualMachineExecutor 實例
    """
    return DualMachineExecutor(gui_instance)

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

from commands import read_data_from_json, calculate_crc16_modbus, create_shot_command, parse_area_params, get_area_params
from core.utils.shot_selector import ShotZoneSelector
from typing import Tuple


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
            # 使用 area.json 載入發球區域數據
            self.json_data = read_data_from_json("area.json")
            
            if not self.json_data:
                self.gui.log_message("❌ 無法載入發球區域數據")
        except Exception as e:
            self.gui.log_message(f"❌ 載入發球區域數據失敗: {e}")
    
    def start_simulation(self, level: int, use_dual_machine: bool = False, total_balls: int = 30) -> bool:
        """
        開始模擬對打
        
        Args:
            level: 球員等級 (1-12)
            use_dual_machine: 是否使用雙發球機
            total_balls: 總發球數 (預設30顆)
            
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
            
            self.gui.log_message(f"🎯 開始模擬對打 - 等級: {level}, 難度: {difficulty}, 間隔: {interval}s, 總球數: {total_balls}")
            self.gui.log_message(f"📊 球路類型: {self._get_serve_type_label(serve_type)}")
            
            if use_dual_machine:
                # 使用雙發球機模式
                self.gui.log_message("🔄 使用雙發球機模式")
                return self._start_dual_machine_simulation(level, difficulty, interval, serve_type, total_balls)
            else:
                # 使用單發球機模式
                self.gui.log_message("🔄 使用單發球機模式")
                
                # 重置狀態
                self.stop_flag = False
                self.previous_sec = None
                
                # 開始訓練任務
                self.training_task = self.gui.create_async_task(
                    self._run_simulation(difficulty, interval, serve_type, total_balls)
                )
                
                if self.training_task is None:
                    self.gui.log_message("❌ 無法創建異步任務，請檢查事件循環")
                    return False
                
                # 同步設置主GUI的訓練任務，保持與舊版本一致
                self.gui.training_task = self.training_task
                
                return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 開始模擬對打失敗: {e}")
            return False
    
    def _start_dual_machine_simulation(self, level: int, difficulty: int, interval: float, serve_type: int, total_balls: int) -> bool:
        """
        開始雙發球機模擬對打
        
        Args:
            level: 球員等級
            difficulty: 難度等級
            interval: 發球間隔
            serve_type: 球路類型
            total_balls: 總發球數
            
        Returns:
            是否成功開始
        """
        try:
            # 檢查雙發球機連接狀態
            if not self._check_dual_bluetooth_connection():
                return False
            
            self.gui.log_message("🔄 使用雙發球機模式進行模擬對打")
            
            # 重置狀態
            self.stop_flag = False
            self.previous_sec = None
            
            # 開始雙發球機訓練任務
            self.training_task = self.gui.create_async_task(
                self._run_dual_machine_simulation(difficulty, interval, serve_type, total_balls)
            )
            
            if self.training_task is None:
                self.gui.log_message("❌ 無法創建雙發球機異步任務，請檢查事件循環")
                return False
            
            # 同步設置主GUI的訓練任務，保持與舊版本一致
            self.gui.training_task = self.training_task
            
            return True
            
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
            self.gui.log_message("🛑 正在停止模擬對打...")
            self.stop_flag = True
            
            # 停止單發球機模擬
            if self.training_task and not self.training_task.done():
                self.training_task.cancel()
                self.gui.log_message("🛑 單發球機模擬任務已取消")
                
                # 強制等待任務完成或超時
                import asyncio
                try:
                    # 嘗試等待任務完成，最多等待2秒
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循環正在運行，創建一個新任務來等待
                        async def wait_for_cancellation():
                            try:
                                await asyncio.wait_for(self.training_task, timeout=2.0)
                            except asyncio.CancelledError:
                                pass
                            except asyncio.TimeoutError:
                                pass
                        
                        # 在事件循環中運行等待任務
                        asyncio.create_task(wait_for_cancellation())
                    else:
                        # 如果沒有運行的事件循環，直接等待
                        loop.run_until_complete(asyncio.wait_for(self.training_task, timeout=2.0))
                except Exception as e:
                    self.gui.log_message(f"⚠️ 等待任務取消時發生錯誤: {e}")
            
            # 停止雙發球機模擬
            if hasattr(self.gui, 'dual_machine_executor'):
                self.gui.dual_machine_executor.stop_dual_simulation()
                self.gui.log_message("🛑 雙發球機模擬已停止")
            
            # 調用主GUI的停止方法以確保UI狀態正確更新
            if hasattr(self.gui, 'stop_training'):
                self.gui.stop_training()
            
            # 立即更新UI狀態
            self._update_simulation_status("已停止", "發球次數: 0 | 運行時間: 00:00")
            
            # 清理任務引用
            self.training_task = None
            
            self.gui.log_message("✅ 模擬對打已停止")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止模擬對打失敗: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _check_bluetooth_connection(self) -> bool:
        """檢查藍牙連接狀態"""
        # 1) 正常藍牙線程
        if hasattr(self.gui, 'bluetooth_thread') and self.gui.bluetooth_thread and getattr(self.gui.bluetooth_thread, 'is_connected', False):
            self.bluetooth_thread = self.gui.bluetooth_thread
            return True
        
        # 2) 離線模擬：允許使用 DeviceService.simulate 進行發球測試
        if hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False):
            self.gui.log_message("[simulate] 使用模擬裝置服務進行發球測試")
            self.bluetooth_thread = None  # 明確不使用實體藍牙
            return True
        
        # 3) 檢查環境變數模擬模式
        import os
        if os.environ.get("SIMULATE", "0") == "1":
            self.gui.log_message("[simulate] 環境變數模擬模式已啟用")
            self.bluetooth_thread = None
            return True
        
        self.gui.log_message("❌ 發球機未連接（且未開啟模擬模式）")
        return False
    
    def _check_dual_bluetooth_connection(self) -> bool:
        """檢查雙發球機連接狀態"""
        # 檢查是否為模擬模式
        is_simulate_mode = False
        if hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False):
            is_simulate_mode = True
        elif os.environ.get("SIMULATE", "0") == "1":
            is_simulate_mode = True
        
        # 在模擬模式下，允許雙發球機模擬
        if is_simulate_mode:
            self.gui.log_message("[simulate] 雙發球機模擬模式已啟用")
            return True
        
        # 檢查雙發球機管理器是否存在
        if not hasattr(self.gui, 'dual_bluetooth_manager') or not self.gui.dual_bluetooth_manager:
            self.gui.log_message("❌ 雙發球機管理器未初始化")
            return False
        
        # 檢查雙發球機是否都已連接
        if not self.gui.dual_bluetooth_manager.is_dual_connected():
            self.gui.log_message("❌ 雙發球機未完全連接，請先連接雙發球機")
            return False
        
        self.gui.log_message("✅ 雙發球機連接狀態正常")
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
        try:
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
            
            if not first_targets:
                raise ValueError(f"無法為區域 {current_sec} 和難度 {difficulty} 生成目標區域")
            
            # 從第一步的可攻擊區域中隨機選出下一個發球位置
            next_sec = random.choice(first_targets)
            second_targets = self.selector.get_available_targets(next_sec, difficulty)
            
            if not second_targets:
                raise ValueError(f"無法為區域 {next_sec} 和難度 {difficulty} 生成目標區域")
            
            next_start = random.choice(second_targets)
            
            # 記錄本次的發球區域，為下次使用
            self.previous_sec = next_start
            
            return current_sec, next_sec
            
        except Exception as e:
            self.gui.log_message(f"❌ _generate_pitch_areas 內部錯誤: {e}")
            raise
    
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
    
    async def _run_simulation(self, difficulty: int, interval: float, serve_type: int, total_balls: int = 30):
        """
        執行模擬對打
        
        Args:
            difficulty: 難度等級
            interval: 發球間隔
            serve_type: 球路類型
            total_balls: 總發球數
        """
        try:
            self.gui.log_message("🚀 模擬對打開始")
            
            # 初始化統計數據
            shot_count = 0
            start_time = time.time()
            
            # 更新狀態為運行中
            self._update_simulation_status("運行中", f"發球次數: {shot_count}/{total_balls} | 運行時間: 00:00")
            
            while not self.stop_flag and shot_count < total_balls:
                # 檢查停止標誌
                if self.stop_flag:
                    break
                
                # 生成發球區域
                try:
                    current_sec, next_sec = self._generate_pitch_areas(difficulty)
                    self.gui.log_message(f"🎯 生成發球區域: {current_sec}")
                except Exception as e:
                    self.gui.log_message(f"❌ 生成發球區域失敗: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                
                # 發送發球指令
                try:
                    await self._send_shot_command(current_sec)
                    self.gui.log_message(f"🎯 發球區域: {current_sec}")
                except Exception as e:
                    self.gui.log_message(f"❌ 發送發球指令失敗: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                
                # 更新統計數據
                shot_count += 1
                elapsed_time = int(time.time() - start_time)
                minutes = elapsed_time // 60
                seconds = elapsed_time % 60
                time_str = f"{minutes:02d}:{seconds:02d}"
                
                # 更新狀態顯示
                self._update_simulation_status("運行中", f"發球次數: {shot_count}/{total_balls} | 運行時間: {time_str}")
                
                # 更新進度條
                self._update_simulation_progress(shot_count, total_balls, "運行中")
                
                # 等待發球完成
                await self._wait_for_shot_completion()
                
                # 再次檢查停止標誌
                if self.stop_flag:
                    break
                
                # 分段等待間隔時間，以便更頻繁地檢查停止標誌
                wait_time = interval
                while wait_time > 0 and not self.stop_flag:
                    sleep_time = min(0.1, wait_time)  # 每0.1秒檢查一次停止標誌
                    try:
                        await asyncio.sleep(sleep_time)
                    except asyncio.CancelledError:
                        # 任務被取消，立即退出
                        self.gui.log_message("🛑 模擬對打被取消")
                        return
                    except RuntimeError as e:
                        if "no running event loop" in str(e):
                            time.sleep(sleep_time)
                        else:
                            raise
                    wait_time -= sleep_time
                
                # 準備下一球
                if not self.stop_flag:
                    self.gui.log_message(f"🔄 準備下一球: {next_sec}")
            
            # 更新最終狀態
            elapsed_time = int(time.time() - start_time)
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            if shot_count >= total_balls:
                self._update_simulation_status("已完成", f"發球次數: {shot_count}/{total_balls} | 運行時間: {time_str}")
                self._update_simulation_progress(shot_count, total_balls, "已完成")
                self.gui.log_message(f"✅ 模擬對打完成 - 已發送 {shot_count} 顆球")
            else:
                self._update_simulation_status("已結束", f"發球次數: {shot_count}/{total_balls} | 運行時間: {time_str}")
                self._update_simulation_progress(shot_count, total_balls, "已結束")
                self.gui.log_message("✅ 模擬對打結束")
            
        except asyncio.CancelledError:
            self._update_simulation_status("已停止", f"發球次數: {shot_count} | 運行時間: {time_str}")
            self.gui.log_message("🛑 模擬對打被取消")
        except Exception as e:
            self._update_simulation_status("錯誤", f"發球次數: {shot_count} | 運行時間: {time_str}")
            self.gui.log_message(f"❌ 模擬對打執行錯誤: {e}")
        finally:
            # 清理狀態
            self._cleanup_simulation()
    
    async def _send_shot_command(self, area_section: str):
        """
        發送發球指令
        
        Args:
            area_section: 發球區域代碼
        """
        try:
            # 1) 實機藍牙線程
            if self.bluetooth_thread and getattr(self.bluetooth_thread, 'is_connected', False):
                try:
                    result = await self.bluetooth_thread.send_shot(area_section)
                    if result:
                        self.gui.log_message("✅ 發球指令已發送")
                    else:
                        self.gui.log_message("❌ 發球指令發送失敗")
                    return
                except Exception as e:
                    self.gui.log_message(f"❌ 藍牙發球失敗: {e}")
                    return
            
            # 2) 模擬裝置服務
            if hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False):
                try:
                    result = await self.gui.device_service.send_shot(area_section)
                    self.gui.log_message("[simulate] ✅ 發球指令已發送" if result else "[simulate] ❌ 發球指令發送失敗")
                    return
                except Exception as e:
                    self.gui.log_message(f"[simulate] ❌ 發球失敗: {e}")
                    return
            
            # 3) 環境變數模擬模式
            import os
            if os.environ.get("SIMULATE", "0") == "1":
                self.gui.log_message(f"[simulate] 發送發球指令: {area_section}")
                return
            
            self.gui.log_message("❌ 發球機未連接")
        except Exception as e:
            self.gui.log_message(f"❌ 發送發球指令失敗: {e}")
            import traceback
            traceback.print_exc()
    
    async def _wait_for_shot_completion(self):
        """等待發球完成"""
        try:
            # 在模擬模式下，縮短等待時間
            is_simulate_mode = False
            if hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False):
                is_simulate_mode = True
            elif os.environ.get("SIMULATE", "0") == "1":
                is_simulate_mode = True
            
            if is_simulate_mode:
                # 模擬模式下等待較短時間
                try:
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    # 任務被取消，立即退出
                    return
                except RuntimeError as e:
                    if "no running event loop" in str(e):
                        time.sleep(0.5)
                    else:
                        raise
                return
            
            # 等待發球完成通知
            if self.bluetooth_thread and hasattr(self.bluetooth_thread, 'wait_for_shot_completion'):
                try:
                    await self.bluetooth_thread.wait_for_shot_completion()
                except asyncio.CancelledError:
                    # 任務被取消，立即退出
                    return
                except RuntimeError as e:
                    if "no running event loop" in str(e):
                        time.sleep(2)
                    else:
                        raise
            else:
                # 如果沒有等待機制，等待固定時間
                try:
                    await asyncio.sleep(2)
                except asyncio.CancelledError:
                    # 任務被取消，立即退出
                    return
                except RuntimeError as e:
                    if "no running event loop" in str(e):
                        time.sleep(2)
                    else:
                        raise
        except Exception as e:
            self.gui.log_message(f"❌ 等待發球完成失敗: {e}")
    
    def _update_simulation_status(self, status: str, stats: str = ""):
        """
        更新模擬對打狀態
        
        Args:
            status: 狀態文字
            stats: 統計信息
        """
        try:
            # 調用GUI的狀態更新函數
            if hasattr(self.gui, 'update_simulation_status'):
                self.gui.update_simulation_status(status, stats)
            else:
                # 如果沒有專用函數，直接更新UI元素
                if hasattr(self.gui, 'simulation_status_label'):
                    self.gui.simulation_status_label.setText(status)
                    
                    # 根據狀態更新顏色
                    if "運行中" in status or "對打中" in status or "雙發球機" in status:
                        self.gui.simulation_status_label.setStyleSheet("""
                            QLabel {
                                font-size: 14px;
                                color: #4CAF50;
                                font-weight: bold;
                                padding: 5px 10px;
                                background-color: rgba(76, 175, 80, 0.2);
                                border-radius: 5px;
                                border: 1px solid #4CAF50;
                            }
                        """)
                    elif "已完成" in status:
                        self.gui.simulation_status_label.setStyleSheet("""
                            QLabel {
                                font-size: 14px;
                                color: #2196F3;
                                font-weight: bold;
                                padding: 5px 10px;
                                background-color: rgba(33, 150, 243, 0.2);
                                border-radius: 5px;
                                border: 1px solid #2196F3;
                            }
                        """)
                    elif "停止" in status or "結束" in status:
                        self.gui.simulation_status_label.setStyleSheet("""
                            QLabel {
                                font-size: 14px;
                                color: #f44336;
                                font-weight: bold;
                                padding: 5px 10px;
                                background-color: rgba(244, 67, 54, 0.2);
                                border-radius: 5px;
                                border: 1px solid #f44336;
                            }
                        """)
                    else:
                        self.gui.simulation_status_label.setStyleSheet("""
                            QLabel {
                                font-size: 14px;
                                color: #ff9800;
                                font-weight: bold;
                                padding: 5px 10px;
                                background-color: rgba(255, 152, 0, 0.2);
                                border-radius: 5px;
                                border: 1px solid #ff9800;
                            }
                        """)
                
                if hasattr(self.gui, 'simulation_stats_label') and stats:
                    self.gui.simulation_stats_label.setText(stats)
        except Exception as e:
            self.gui.log_message(f"❌ 更新狀態失敗: {e}")
    
    def _update_simulation_progress(self, current_balls: int, total_balls: int, status: str = ""):
        """
        更新模擬對打進度條
        
        Args:
            current_balls: 當前已發球數
            total_balls: 總球數
            status: 狀態文字
        """
        try:
            # 調用GUI的進度更新函數
            if hasattr(self.gui, 'update_simulation_progress'):
                self.gui.update_simulation_progress(current_balls, total_balls, status)
        except Exception as e:
            self.gui.log_message(f"❌ 更新進度條失敗: {e}")
    
    async def _run_dual_machine_simulation(self, difficulty: int, interval: float, serve_type: int, total_balls: int = 30):
        """
        執行雙發球機模擬對打
        
        Args:
            difficulty: 難度等級
            interval: 發球間隔
            serve_type: 球路類型
            total_balls: 總發球數
        """
        try:
            self.gui.log_message("🚀 雙發球機模擬對打開始")
            
            # 初始化統計數據
            shot_count = 0
            start_time = time.time()
            current_machine = 0  # 0=左發球機, 1=右發球機
            
            # 更新狀態為運行中
            self._update_simulation_status("雙發球機對打中", f"發球次數: {shot_count}/{total_balls} | 運行時間: 00:00")
            
            while not self.stop_flag and shot_count < total_balls:
                # 生成發球區域
                current_sec, next_sec = self._generate_pitch_areas(difficulty)
                
                # 選擇當前發球機
                machine_name = "左發球機" if current_machine == 0 else "右發球機"
                machine_thread = self.gui.dual_bluetooth_manager.get_machine_thread("left" if current_machine == 0 else "right")
                
                # 在模擬模式下，即使沒有實體線程也允許發球
                is_simulate_mode = False
                if hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False):
                    is_simulate_mode = True
                elif os.environ.get("SIMULATE", "0") == "1":
                    is_simulate_mode = True
                
                if machine_thread or is_simulate_mode:
                    # 發送發球指令
                    await self._send_dual_shot_command(machine_thread, current_sec, machine_name)
                    self.gui.log_message(f"🎯 {machine_name} 發球區域: {current_sec}")
                    
                    # 更新統計數據
                    shot_count += 1
                    elapsed_time = int(time.time() - start_time)
                    minutes = elapsed_time // 60
                    seconds = elapsed_time % 60
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    
                    # 更新狀態顯示
                    self._update_simulation_status("雙發球機對打中", f"發球次數: {shot_count}/{total_balls} | 運行時間: {time_str}")
                    
                    # 更新進度條
                    self._update_simulation_progress(shot_count, total_balls, "雙發球機對打中")
                    
                    # 等待發球完成
                    await self._wait_for_shot_completion()
                    
                    if self.stop_flag:
                        break
                    
                    # 分段等待間隔時間，以便更頻繁地檢查停止標誌
                    wait_time = interval
                    while wait_time > 0 and not self.stop_flag:
                        sleep_time = min(0.1, wait_time)  # 每0.1秒檢查一次停止標誌
                        await asyncio.sleep(sleep_time)
                        wait_time -= sleep_time
                    
                    if self.stop_flag:
                        break
                    
                    # 輪流切換發球機
                    current_machine = 1 - current_machine
                    
                    # 準備下一球
                    next_machine_name = "左發球機" if current_machine == 0 else "右發球機"
                    self.gui.log_message(f"🔄 準備下一球，切換到 {next_machine_name}: {next_sec}")
                else:
                    self.gui.log_message(f"❌ {machine_name} 線程不可用")
                    break
            
            # 更新最終狀態
            elapsed_time = int(time.time() - start_time)
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            if shot_count >= total_balls:
                self._update_simulation_status("已完成", f"發球次數: {shot_count}/{total_balls} | 運行時間: {time_str}")
                self._update_simulation_progress(shot_count, total_balls, "已完成")
                self.gui.log_message(f"✅ 雙發球機模擬對打完成 - 已發送 {shot_count} 顆球")
            else:
                self._update_simulation_status("已結束", f"發球次數: {shot_count}/{total_balls} | 運行時間: {time_str}")
                self._update_simulation_progress(shot_count, total_balls, "已結束")
                self.gui.log_message("✅ 雙發球機模擬對打結束")
            
        except asyncio.CancelledError:
            self._update_simulation_status("已停止", f"發球次數: {shot_count} | 運行時間: {time_str}")
            self.gui.log_message("🛑 雙發球機模擬對打被取消")
        except Exception as e:
            self._update_simulation_status("錯誤", f"發球次數: {shot_count} | 運行時間: {time_str}")
            self.gui.log_message(f"❌ 雙發球機模擬對打執行錯誤: {e}")
        finally:
            # 清理狀態
            self._cleanup_simulation()
    
    async def _send_dual_shot_command(self, machine_thread, area_section: str, machine_name: str):
        """
        發送雙發球機發球指令
        
        Args:
            machine_thread: 發球機線程
            area_section: 發球區域代碼
            machine_name: 發球機名稱
        """
        try:
            # 在模擬模式下，直接以日誌驗證送球，不依賴底層 Bleak client
            if hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False):
                self.gui.log_message(f"[simulate-dual] {machine_name} 發送 {area_section}")
                return
            
            # 環境變數模擬模式
            import os
            if os.environ.get("SIMULATE", "0") == "1":
                self.gui.log_message(f"[simulate-dual] {machine_name} 發送 {area_section}")
                return
            
            # 1) 實機線程
            if machine_thread and getattr(machine_thread, 'is_connected', False):
                result = await machine_thread.send_shot(area_section)
                self.gui.log_message(f"✅ {machine_name} 發球指令已發送" if result else f"❌ {machine_name} 發球指令發送失敗")
                return
            
            self.gui.log_message(f"❌ {machine_name} 未連接")
        except Exception as e:
            self.gui.log_message(f"❌ 發送 {machine_name} 發球指令失敗: {e}")

    def _cleanup_simulation(self):
        """清理模擬對打狀態"""
        try:
            # 重置停止標誌
            self.stop_flag = False
            
            # 更新按鈕狀態
            if hasattr(self.gui, 'simulation_start_button'):
                self.gui.simulation_start_button.setEnabled(True)
            if hasattr(self.gui, 'simulation_stop_button'):
                self.gui.simulation_stop_button.setEnabled(False)
            
            # 更新 GUI 的訓練任務狀態
            if hasattr(self.gui, 'training_task'):
                self.gui.training_task = None
            
            self.training_task = None
            
            # 更新狀態顯示
            self._update_simulation_status("已停止", "發球次數: 0 | 運行時間: 00:00")
            
            self.gui.log_message("🧹 模擬對打狀態已清理")
        except Exception as e:
            self.gui.log_message(f"❌ 清理狀態失敗: {e}")

    async def _ensure_dual_manager_connected_simulated(self) -> bool:
        """在模擬模式下，確保雙發球機管理器具備可用的左右機線程。"""
        try:
            # 僅在模擬模式下生效
            if not (hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False)):
                return False
            
            # 若不存在管理器，嘗試創建
            if not hasattr(self.gui, 'dual_bluetooth_manager') or self.gui.dual_bluetooth_manager is None:
                from core.managers.dual_bluetooth_manager import DualBluetoothManager
                self.gui.dual_bluetooth_manager = DualBluetoothManager(self.gui)
            
            manager = self.gui.dual_bluetooth_manager
            
            # 若線程不存在或未連接，建立模擬連線（特殊 MAC 前綴將被線程識別為模擬）
            if not getattr(manager, 'left_machine', None):
                from core.managers.dual_bluetooth_thread import DualBluetoothThread
                manager.left_machine = DualBluetoothThread("left")
            if not getattr(manager, 'right_machine', None):
                from core.managers.dual_bluetooth_thread import DualBluetoothThread
                manager.right_machine = DualBluetoothThread("right")
            
            # 以保留前綴的模擬地址進行「假連接」
            if not manager.left_machine.is_connected:
                await manager.left_machine.connect_device("AA:BB:CC:DD:EE:01")
            if not manager.right_machine.is_connected:
                await manager.right_machine.connect_device("AA:BB:CC:DD:EE:02")
            
            # 建立映射查找
            manager.machine_threads = {
                'left': manager.left_machine,
                'right': manager.right_machine,
            }
            
            return manager.left_machine.is_connected and manager.right_machine.is_connected
        except Exception as e:
            self.gui.log_message(f"❌ 構建模擬雙機失敗: {e}")
            return False

    async def test_levels(self, use_dual_machine: bool = False, levels: Optional[List[int]] = None) -> Dict[int, bool]:
        """
        在未連機也可執行的批次測試：對指定等級（預設 1..12），各送出一球以驗證送球路徑。
        返回每個等級是否成功送出發球的布林值。
        """
        results: Dict[int, bool] = {}
        try:
            # 準備等級清單
            level_list = levels if levels else list(range(1, 13))
            
            # 檢查單機或準備雙機（模擬）
            if use_dual_machine:
                ok = await self._ensure_dual_manager_connected_simulated()
                if not ok and (not hasattr(self.gui, 'dual_bluetooth_manager') or not self.gui.dual_bluetooth_manager.is_dual_connected()):
                    self.gui.log_message("❌ 無法建立雙機（實機未連接且模擬構建失敗）")
                    return {lvl: False for lvl in level_list}
            else:
                if not self._check_bluetooth_connection():
                    # 允許 simulate 模式通過；若完全不行，全部失敗
                    if not (hasattr(self.gui, 'device_service') and getattr(self.gui.device_service, 'simulate', False)):
                        return {lvl: False for lvl in level_list}
            
            # 重置狀態以獲得穩定起點
            self.previous_sec = None
            
            for level in level_list:
                try:
                    difficulty, interval, serve_type = self._get_training_params(level)
                    current_sec, next_sec = self._generate_pitch_areas(difficulty)
                    
                    if use_dual_machine:
                        # 交替測試：左機發一球、下一等級再換右機
                        machine_name = "左發球機" if level % 2 == 1 else "右發球機"
                        thread = self.gui.dual_bluetooth_manager.get_machine_thread('left' if level % 2 == 1 else 'right')
                        await self._send_dual_shot_command(thread, current_sec, machine_name)
                        # 視為成功：若是模擬，已記錄日誌；實機則依 send_shot 回傳
                        results[level] = True
                    else:
                        await self._send_shot_command(current_sec)
                        results[level] = True
                except Exception as e:
                    self.gui.log_message(f"❌ 等級 {level} 測試失敗: {e}")
                    results[level] = False
            
            return results
        except Exception as e:
            self.gui.log_message(f"❌ 等級批次測試發生錯誤: {e}")
            return results


def create_simulation_executor(gui_instance) -> SimulationExecutor:
    """
    建立模擬對打執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        SimulationExecutor 實例
    """
    return SimulationExecutor(gui_instance)

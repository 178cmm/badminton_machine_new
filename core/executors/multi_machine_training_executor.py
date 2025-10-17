"""
四台發球機訓練執行器

這個模組整合了 BasicTrainingExecutor 和 AdvancedTrainingExecutor，
支援四台發球機的獨立和協調訓練。
"""

import asyncio
import random
import time
from typing import Dict, Any, Optional, List
from PyQt5.QtCore import QThread, pyqtSignal
from ..parsers import (
    basic_map_speed_to_interval as basic_map_speed_to_interval,
    adv_map_speed_to_interval as adv_map_speed_to_interval,
    map_count_to_number,
    parse_ball_count,
    get_section_by_shot_name,
    get_shot_name_by_section
)


class IndividualTrainingWorker(QThread):
    """單台發球機的獨立訓練執行器"""
    
    # 信號定義
    sig_progress = pyqtSignal(str, int, int)  # machine_id, current, total
    sig_message = pyqtSignal(str, str)  # machine_id, message
    sig_finished = pyqtSignal(str, str)  # machine_id, status
    
    def __init__(self, machine_id: str, program_config: dict, interval: float, unlimited: bool = True):
        """
        初始化獨立訓練執行器
        
        Args:
            machine_id: 發球機ID
            program_config: 套餐配置
            interval: 發球間隔
            unlimited: 是否無限發球
        """
        super().__init__()
        self.machine_id = machine_id
        self.program_config = program_config
        self.interval = interval
        self.unlimited = unlimited
        self.stop_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # 初始為非暫停狀態
        
        # 訓練狀態
        self.current_shot = 0
        self.total_shots = 0
        self.is_running = False
        
        # 發球機引用（將由管理器設置）
        self.machine_thread = None
    
    def set_machine_thread(self, machine_thread):
        """設置發球機線程引用"""
        self.machine_thread = machine_thread
    
    def pause(self):
        """暫停訓練"""
        self.pause_event.clear()
        self.sig_message.emit(self.machine_id, "訓練已暫停")
    
    def resume(self):
        """恢復訓練"""
        self.pause_event.set()
        self.sig_message.emit(self.machine_id, "訓練已恢復")
    
    def stop(self):
        """停止訓練"""
        self.stop_event.set()
        self.sig_message.emit(self.machine_id, "訓練已停止")
    
    async def run_training(self):
        """運行訓練"""
        try:
            self.is_running = True
            self.sig_message.emit(self.machine_id, f"開始訓練: {self.program_config.get('id', 'unknown')}")
            
            # 計算總球數
            if self.unlimited:
                self.total_shots = -1
            else:
                if self.program_config.get("type") == "basic":
                    self.total_shots = len(self.program_config.get("shots", []))
                else:  # advanced
                    self.total_shots = 100  # 預設100球
            
            # 開始訓練循環
            while not self.stop_event.is_set():
                # 檢查暫停狀態
                await self.pause_event.wait()
                
                if self.stop_event.is_set():
                    break
                
                # 執行發球
                success = await self._execute_shot()
                if not success:
                    self.sig_message.emit(self.machine_id, "發球失敗，停止訓練")
                    break
                
                # 更新進度
                self.current_shot += 1
                if self.total_shots > 0:
                    self.sig_progress.emit(self.machine_id, self.current_shot, self.total_shots)
                    
                    # 檢查是否完成
                    if self.current_shot >= self.total_shots:
                        self.sig_message.emit(self.machine_id, "訓練完成")
                        break
                else:
                    # 無限模式
                    self.sig_progress.emit(self.machine_id, self.current_shot, -1)
                
                # 等待間隔時間
                if self.interval > 0:
                    await asyncio.sleep(self.interval)
            
            self.sig_finished.emit(self.machine_id, "completed")
            
        except Exception as e:
            self.sig_message.emit(self.machine_id, f"訓練錯誤: {e}")
            self.sig_finished.emit(self.machine_id, "error")
        finally:
            self.is_running = False
    
    async def _execute_shot(self) -> bool:
        """執行單次發球"""
        try:
            if not self.machine_thread or not self.machine_thread.is_connected:
                return False
            
            # 根據套餐類型選擇發球區域
            area_section = self._get_next_shot_area()
            if not area_section:
                return False
            
            # 發送發球指令
            success = await self.machine_thread.send_shot(area_section)
            
            if success:
                self.sig_message.emit(self.machine_id, f"發球成功: {area_section}")
            else:
                self.sig_message.emit(self.machine_id, f"發球失敗: {area_section}")
            
            return success
            
        except Exception as e:
            self.sig_message.emit(self.machine_id, f"發球執行錯誤: {e}")
            return False
    
    def _get_next_shot_area(self) -> Optional[str]:
        """獲取下一個發球區域"""
        try:
            program_type = self.program_config.get("type", "basic")
            
            if program_type == "basic":
                # 基礎訓練：依序發球
                shots = self.program_config.get("shots", [])
                if not shots:
                    return None
                
                shot_index = self.current_shot % len(shots)
                shot_config = shots[shot_index]
                return shot_config.get("section")
            
            elif program_type == "advanced":
                # 進階訓練：根據模式發球
                mode = self.program_config.get("mode", "random")
                sections = self.program_config.get("sections", [])
                
                if not sections:
                    return None
                
                if mode == "random":
                    return random.choice(sections)
                elif mode == "sequence":
                    return sections[self.current_shot % len(sections)]
                else:
                    return sections[0] if sections else None
            
            return None
            
        except Exception as e:
            print(f"獲取發球區域錯誤: {e}")
            return None


class MultiMachineTrainingExecutor:
    """四台發球機訓練執行器類別"""
    
    def __init__(self, gui_instance, multi_machine_manager):
        """
        初始化四台發球機訓練執行器
        
        Args:
            gui_instance: GUI 主類別的實例
            multi_machine_manager: 四台發球機管理器
        """
        self.gui = gui_instance
        self.multi_machine_manager = multi_machine_manager
        self.training_workers: Dict[str, IndividualTrainingWorker] = {}
        self.active_sessions: Dict[str, Any] = {}
    
    def start_individual_training(self, machine_id: str, program_name: str, 
                                interval: float, unlimited: bool = True) -> bool:
        """
        啟動指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            program_name: 套餐名稱
            interval: 發球間隔
            unlimited: 是否無限發球
            
        Returns:
            是否成功開始訓練
        """
        try:
            # 檢查發球機是否存在
            machine_thread = self.multi_machine_manager.get_machine_thread(machine_id)
            if not machine_thread:
                self.gui.log_message(f"❌ 發球機 {machine_id} 不存在")
                return False
            
            if not machine_thread.is_connected:
                self.gui.log_message(f"❌ 發球機 {machine_id} 未連接")
                return False
            
            # 獲取套餐配置
            available_programs = self.multi_machine_manager.get_available_programs()
            if program_name not in available_programs:
                self.gui.log_message(f"❌ 套餐 {program_name} 不存在")
                return False
            
            program_config = available_programs[program_name]
            
            # 停止現有訓練（如果有的話）
            if machine_id in self.training_workers:
                self.stop_individual_training(machine_id)
            
            # 創建訓練會話
            session = self.multi_machine_manager.create_training_session(
                machine_id, program_name, interval, unlimited
            )
            if not session:
                self.gui.log_message(f"❌ 創建訓練會話失敗: {machine_id}")
                return False
            
            # 創建訓練執行器
            worker = IndividualTrainingWorker(machine_id, program_config, interval, unlimited)
            worker.set_machine_thread(machine_thread)
            
            # 設置信號連接
            worker.sig_progress.connect(
                lambda machine_id, current, total: self._on_training_progress(machine_id, current, total)
            )
            worker.sig_message.connect(
                lambda machine_id, message: self._on_training_message(machine_id, message)
            )
            worker.sig_finished.connect(
                lambda machine_id, status: self._on_training_finished(machine_id, status)
            )
            
            # 存儲引用
            self.training_workers[machine_id] = worker
            self.active_sessions[machine_id] = session
            
            # 開始訓練會話
            session.start_session()
            
            # 啟動訓練執行器
            worker.start()
            
            self.gui.log_message(f"✅ 開始 {machine_id} 訓練: {program_name}")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 啟動 {machine_id} 訓練失敗: {e}")
            return False
    
    def pause_individual_training(self, machine_id: str) -> bool:
        """
        暫停指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功暫停
        """
        try:
            if machine_id not in self.training_workers:
                self.gui.log_message(f"❌ {machine_id} 沒有運行中的訓練")
                return False
            
            worker = self.training_workers[machine_id]
            worker.pause()
            
            # 更新會話狀態
            session = self.active_sessions.get(machine_id)
            if session:
                session.pause_session()
            
            self.gui.log_message(f"⏸️ {machine_id} 訓練已暫停")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 暫停 {machine_id} 訓練失敗: {e}")
            return False
    
    def resume_individual_training(self, machine_id: str) -> bool:
        """
        恢復指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功恢復
        """
        try:
            if machine_id not in self.training_workers:
                self.gui.log_message(f"❌ {machine_id} 沒有暫停中的訓練")
                return False
            
            worker = self.training_workers[machine_id]
            worker.resume()
            
            # 更新會話狀態
            session = self.active_sessions.get(machine_id)
            if session:
                session.resume_session()
            
            self.gui.log_message(f"▶️ {machine_id} 訓練已恢復")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 恢復 {machine_id} 訓練失敗: {e}")
            return False
    
    def stop_individual_training(self, machine_id: str) -> bool:
        """
        停止指定發球機的訓練
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            是否成功停止
        """
        try:
            if machine_id not in self.training_workers:
                self.gui.log_message(f"❌ {machine_id} 沒有運行中的訓練")
                return False
            
            worker = self.training_workers[machine_id]
            worker.stop()
            
            # 等待線程結束
            if worker.isRunning():
                worker.wait(3000)  # 等待3秒
            
            # 更新會話狀態
            session = self.active_sessions.get(machine_id)
            if session:
                session.stop_session()
            
            # 清理引用
            del self.training_workers[machine_id]
            if machine_id in self.active_sessions:
                del self.active_sessions[machine_id]
            
            self.gui.log_message(f"⏹️ {machine_id} 訓練已停止")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止 {machine_id} 訓練失敗: {e}")
            return False
    
    def pause_all_training(self) -> bool:
        """
        暫停所有發球機的訓練
        
        Returns:
            是否成功暫停
        """
        try:
            paused_count = 0
            for machine_id in list(self.training_workers.keys()):
                if self.pause_individual_training(machine_id):
                    paused_count += 1
            
            self.gui.log_message(f"⏸️ 已暫停 {paused_count} 台發球機的訓練")
            return paused_count > 0
            
        except Exception as e:
            self.gui.log_message(f"❌ 暫停全部訓練失敗: {e}")
            return False
    
    def resume_all_training(self) -> bool:
        """
        恢復所有發球機的訓練
        
        Returns:
            是否成功恢復
        """
        try:
            resumed_count = 0
            for machine_id in list(self.training_workers.keys()):
                if self.resume_individual_training(machine_id):
                    resumed_count += 1
            
            self.gui.log_message(f"▶️ 已恢復 {resumed_count} 台發球機的訓練")
            return resumed_count > 0
            
        except Exception as e:
            self.gui.log_message(f"❌ 恢復全部訓練失敗: {e}")
            return False
    
    def stop_all_training(self) -> bool:
        """
        停止所有發球機的訓練
        
        Returns:
            是否成功停止
        """
        try:
            stopped_count = 0
            for machine_id in list(self.training_workers.keys()):
                if self.stop_individual_training(machine_id):
                    stopped_count += 1
            
            self.gui.log_message(f"⏹️ 已停止 {stopped_count} 台發球機的訓練")
            return stopped_count > 0
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止全部訓練失敗: {e}")
            return False
    
    def get_training_status(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取指定發球機的訓練狀態
        
        Args:
            machine_id: 發球機ID
            
        Returns:
            訓練狀態信息
        """
        try:
            if machine_id not in self.training_workers:
                return None
            
            worker = self.training_workers[machine_id]
            session = self.active_sessions.get(machine_id)
            
            return {
                "machine_id": machine_id,
                "is_running": worker.is_running,
                "current_shot": worker.current_shot,
                "total_shots": worker.total_shots,
                "interval": worker.interval,
                "unlimited": worker.unlimited,
                "session_status": session.status if session else "unknown",
                "session_info": session.get_status_info() if session else None
            }
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取 {machine_id} 訓練狀態失敗: {e}")
            return None
    
    def get_all_training_status(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取所有發球機的訓練狀態
        
        Returns:
            所有發球機的訓練狀態
        """
        try:
            status = {}
            for machine_id in self.multi_machine_manager.machine_ids:
                machine_status = self.get_training_status(machine_id)
                if machine_status:
                    status[machine_id] = machine_status
                else:
                    status[machine_id] = {
                        "machine_id": machine_id,
                        "is_running": False,
                        "status": "idle"
                    }
            
            return status
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取全部訓練狀態失敗: {e}")
            return {}
    
    def _on_training_progress(self, machine_id: str, current: int, total: int):
        """訓練進度回調"""
        try:
            # 更新會話進度
            session = self.active_sessions.get(machine_id)
            if session:
                session.update_progress(current, total)
            
            # 通知GUI更新
            if hasattr(self.gui, 'update_training_progress'):
                self.gui.update_training_progress(machine_id, current, total)
                
        except Exception as e:
            print(f"處理訓練進度回調錯誤: {e}")
    
    def _on_training_message(self, machine_id: str, message: str):
        """訓練訊息回調"""
        try:
            self.gui.log_message(f"[{machine_id}] {message}")
        except Exception as e:
            print(f"處理訓練訊息回調錯誤: {e}")
    
    def _on_training_finished(self, machine_id: str, status: str):
        """訓練完成回調"""
        try:
            # 更新會話狀態
            session = self.active_sessions.get(machine_id)
            if session:
                if status == "completed":
                    session.stop_session()
                else:
                    session.status = "error"
            
            # 清理引用
            if machine_id in self.training_workers:
                del self.training_workers[machine_id]
            if machine_id in self.active_sessions:
                del self.active_sessions[machine_id]
            
            self.gui.log_message(f"🏁 {machine_id} 訓練完成: {status}")
            
            # 通知GUI更新
            if hasattr(self.gui, 'on_training_finished'):
                self.gui.on_training_finished(machine_id, status)
                
        except Exception as e:
            print(f"處理訓練完成回調錯誤: {e}")


def create_multi_machine_training_executor(gui_instance, multi_machine_manager) -> MultiMachineTrainingExecutor:
    """
    建立四台發球機訓練執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        multi_machine_manager: 四台發球機管理器
        
    Returns:
        MultiMachineTrainingExecutor 實例
    """
    return MultiMachineTrainingExecutor(gui_instance, multi_machine_manager)

"""
協調訓練執行器

這個模組實現四台發球機的協調訓練功能，包括：
- 多台發球機協調發球
- 時間同步和序列控制
- 協調訓練模式設計
- 協調狀態監控
"""

import asyncio
import time
import random
from typing import Dict, Any, Optional, List, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from ..managers.multi_machine_manager import MultiMachineManager
from ..managers.training_session import TrainingSession


class CoordinatedTrainingWorker(QThread):
    """協調訓練執行器"""
    
    # 信號定義
    sig_progress = pyqtSignal(str, int, int)  # machine_id, current, total
    sig_message = pyqtSignal(str, str)  # machine_id, message
    sig_coordination_update = pyqtSignal(dict)  # 協調狀態更新
    sig_finished = pyqtSignal(str, str)  # machine_id, status
    
    def __init__(self, coordination_config: dict, multi_machine_manager: MultiMachineManager):
        """
        初始化協調訓練執行器
        
        Args:
            coordination_config: 協調配置
            multi_machine_manager: 四台發球機管理器
        """
        super().__init__()
        self.coordination_config = coordination_config
        self.multi_machine_manager = multi_machine_manager
        
        # 協調狀態
        self.is_running = False
        self.is_paused = False
        self.current_round = 0
        self.total_rounds = 0
        self.start_time = None
        
        # 發球機狀態
        self.machine_states: Dict[str, Dict[str, Any]] = {}
        self.coordination_sequence: List[Dict[str, Any]] = []
        
        # 控制事件
        self.stop_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # 初始為非暫停狀態
    
    def pause(self):
        """暫停協調訓練"""
        self.is_paused = True
        self.pause_event.clear()
        self.sig_message.emit("coordinator", "協調訓練已暫停")
    
    def resume(self):
        """恢復協調訓練"""
        self.is_paused = False
        self.pause_event.set()
        self.sig_message.emit("coordinator", "協調訓練已恢復")
    
    def stop(self):
        """停止協調訓練"""
        self.stop_event.set()
        self.sig_message.emit("coordinator", "協調訓練已停止")
    
    async def run_coordinated_training(self):
        """運行協調訓練"""
        try:
            self.is_running = True
            self.start_time = time.time()
            
            # 初始化協調配置
            await self._initialize_coordination()
            
            # 開始協調訓練循環
            while not self.stop_event.is_set():
                # 檢查暫停狀態
                await self.pause_event.wait()
                
                if self.stop_event.is_set():
                    break
                
                # 執行一輪協調發球
                success = await self._execute_coordination_round()
                if not success:
                    self.sig_message.emit("coordinator", "協調發球失敗，停止訓練")
                    break
                
                # 更新進度
                self.current_round += 1
                self._update_progress()
                
                # 檢查是否完成
                if self.total_rounds > 0 and self.current_round >= self.total_rounds:
                    self.sig_message.emit("coordinator", "協調訓練完成")
                    break
                
                # 等待下一輪間隔
                interval = self.coordination_config.get("round_interval", 1.0)
                if interval > 0:
                    await asyncio.sleep(interval)
            
            self.sig_finished.emit("coordinator", "completed")
            
        except Exception as e:
            self.sig_message.emit("coordinator", f"協調訓練錯誤: {e}")
            self.sig_finished.emit("coordinator", "error")
        finally:
            self.is_running = False
    
    async def _initialize_coordination(self):
        """初始化協調配置"""
        try:
            # 獲取協調模式
            mode = self.coordination_config.get("mode", "sequence")
            
            # 獲取參與的發球機
            participating_machines = self.coordination_config.get("machines", [])
            if not participating_machines:
                participating_machines = ["machine_1", "machine_2", "machine_3", "machine_4"]
            
            # 初始化發球機狀態
            for machine_id in participating_machines:
                self.machine_states[machine_id] = {
                    "is_active": True,
                    "current_shot": 0,
                    "total_shots": 0,
                    "last_shot_time": 0,
                    "program": self.coordination_config.get("program", "基礎訓練")
                }
            
            # 生成協調序列
            self.coordination_sequence = self._generate_coordination_sequence(mode, participating_machines)
            
            # 計算總輪數
            self.total_rounds = self.coordination_config.get("total_rounds", 0)
            if self.total_rounds == 0:
                self.total_rounds = len(self.coordination_sequence)
            
            self.sig_message.emit("coordinator", f"協調訓練初始化完成: {mode} 模式, {len(participating_machines)} 台發球機")
            
        except Exception as e:
            self.sig_message.emit("coordinator", f"協調初始化失敗: {e}")
            raise
    
    def _generate_coordination_sequence(self, mode: str, machines: List[str]) -> List[Dict[str, Any]]:
        """生成協調序列"""
        sequence = []
        
        if mode == "sequence":
            # 序列模式：按順序發球
            for i, machine_id in enumerate(machines):
                sequence.append({
                    "machine_id": machine_id,
                    "area": f"sec{(i % 5) + 1}_1",
                    "delay": i * 0.5,  # 每台機器延遲0.5秒
                    "round": i
                })
        
        elif mode == "simultaneous":
            # 同時模式：所有機器同時發球
            for i, machine_id in enumerate(machines):
                sequence.append({
                    "machine_id": machine_id,
                    "area": f"sec{(i % 5) + 1}_1",
                    "delay": 0,  # 同時發球
                    "round": 0
                })
        
        elif mode == "random":
            # 隨機模式：隨機選擇機器發球
            for i in range(len(machines) * 2):  # 每台機器發2次
                machine_id = random.choice(machines)
                sequence.append({
                    "machine_id": machine_id,
                    "area": f"sec{random.randint(1, 5)}_{random.randint(1, 2)}",
                    "delay": random.uniform(0, 1.0),
                    "round": i
                })
        
        elif mode == "wave":
            # 波浪模式：波浪式發球
            for round_num in range(len(machines)):
                for i, machine_id in enumerate(machines):
                    sequence.append({
                        "machine_id": machine_id,
                        "area": f"sec{(round_num % 5) + 1}_1",
                        "delay": i * 0.2,  # 波浪延遲
                        "round": round_num
                    })
        
        return sequence
    
    async def _execute_coordination_round(self) -> bool:
        """執行一輪協調發球"""
        try:
            # 獲取當前輪次的發球指令
            current_round_instructions = [
                inst for inst in self.coordination_sequence 
                if inst["round"] == self.current_round
            ]
            
            if not current_round_instructions:
                return True  # 沒有指令，跳過這一輪
            
            # 按延遲時間排序
            current_round_instructions.sort(key=lambda x: x["delay"])
            
            # 執行發球指令
            tasks = []
            for instruction in current_round_instructions:
                machine_id = instruction["machine_id"]
                area = instruction["area"]
                delay = instruction["delay"]
                
                # 創建發球任務
                task = self._execute_machine_shot(machine_id, area, delay)
                tasks.append(task)
            
            # 並行執行所有發球任務
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 檢查結果
            success_count = sum(1 for result in results if result is True)
            total_count = len(results)
            
            self.sig_message.emit("coordinator", f"第 {self.current_round + 1} 輪: {success_count}/{total_count} 發球成功")
            
            # 更新協調狀態
            self._update_coordination_status()
            
            return success_count > 0
            
        except Exception as e:
            self.sig_message.emit("coordinator", f"執行協調輪次錯誤: {e}")
            return False
    
    async def _execute_machine_shot(self, machine_id: str, area: str, delay: float) -> bool:
        """執行單台機器發球"""
        try:
            # 等待延遲時間
            if delay > 0:
                await asyncio.sleep(delay)
            
            # 獲取機器線程
            machine_thread = self.multi_machine_manager.get_machine_thread(machine_id)
            if not machine_thread or not machine_thread.is_connected:
                self.sig_message.emit(machine_id, f"機器未連接，跳過發球: {area}")
                return False
            
            # 發送發球指令
            success = await machine_thread.send_shot(area)
            
            if success:
                # 更新機器狀態
                if machine_id in self.machine_states:
                    self.machine_states[machine_id]["current_shot"] += 1
                    self.machine_states[machine_id]["last_shot_time"] = time.time()
                
                self.sig_message.emit(machine_id, f"發球成功: {area}")
            else:
                self.sig_message.emit(machine_id, f"發球失敗: {area}")
            
            return success
            
        except Exception as e:
            self.sig_message.emit(machine_id, f"發球執行錯誤: {e}")
            return False
    
    def _update_progress(self):
        """更新進度"""
        for machine_id, state in self.machine_states.items():
            self.sig_progress.emit(machine_id, state["current_shot"], state["total_shots"])
    
    def _update_coordination_status(self):
        """更新協調狀態"""
        status = {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "machine_states": self.machine_states.copy(),
            "elapsed_time": time.time() - self.start_time if self.start_time else 0
        }
        
        self.sig_coordination_update.emit(status)


class CoordinatedTrainingExecutor:
    """協調訓練執行器類別"""
    
    def __init__(self, gui_instance, multi_machine_manager: MultiMachineManager):
        """
        初始化協調訓練執行器
        
        Args:
            gui_instance: GUI 主類別實例
            multi_machine_manager: 四台發球機管理器
        """
        self.gui = gui_instance
        self.multi_machine_manager = multi_machine_manager
        self.coordination_worker: Optional[CoordinatedTrainingWorker] = None
        self.coordination_session: Optional[TrainingSession] = None
    
    def start_coordinated_training(self, coordination_config: dict) -> bool:
        """
        開始協調訓練
        
        Args:
            coordination_config: 協調配置
            
        Returns:
            是否成功開始訓練
        """
        try:
            # 檢查前置條件
            if not self._check_prerequisites():
                return False
            
            # 停止現有協調訓練
            if self.coordination_worker:
                self.stop_coordinated_training()
            
            # 創建協調訓練會話
            self.coordination_session = TrainingSession(
                "coordinator", 
                coordination_config.get("program", "協調訓練"),
                coordination_config.get("interval", 1.0),
                coordination_config.get("unlimited", False)
            )
            
            # 創建協調訓練執行器
            self.coordination_worker = CoordinatedTrainingWorker(
                coordination_config, 
                self.multi_machine_manager
            )
            
            # 設置信號連接
            self.coordination_worker.sig_progress.connect(self._on_progress_update)
            self.coordination_worker.sig_message.connect(self._on_message_update)
            self.coordination_worker.sig_coordination_update.connect(self._on_coordination_update)
            self.coordination_worker.sig_finished.connect(self._on_training_finished)
            
            # 開始訓練會話
            self.coordination_session.start_session()
            
            # 啟動協調訓練執行器
            self.coordination_worker.start()
            
            self.gui.log_message("✅ 協調訓練已開始")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 開始協調訓練失敗: {e}")
            return False
    
    def pause_coordinated_training(self) -> bool:
        """
        暫停協調訓練
        
        Returns:
            是否成功暫停
        """
        try:
            if not self.coordination_worker:
                self.gui.log_message("❌ 沒有運行中的協調訓練")
                return False
            
            self.coordination_worker.pause()
            
            # 更新會話狀態
            if self.coordination_session:
                self.coordination_session.pause_session()
            
            self.gui.log_message("⏸️ 協調訓練已暫停")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 暫停協調訓練失敗: {e}")
            return False
    
    def resume_coordinated_training(self) -> bool:
        """
        恢復協調訓練
        
        Returns:
            是否成功恢復
        """
        try:
            if not self.coordination_worker:
                self.gui.log_message("❌ 沒有暫停中的協調訓練")
                return False
            
            self.coordination_worker.resume()
            
            # 更新會話狀態
            if self.coordination_session:
                self.coordination_session.resume_session()
            
            self.gui.log_message("▶️ 協調訓練已恢復")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 恢復協調訓練失敗: {e}")
            return False
    
    def stop_coordinated_training(self) -> bool:
        """
        停止協調訓練
        
        Returns:
            是否成功停止
        """
        try:
            if not self.coordination_worker:
                self.gui.log_message("❌ 沒有運行中的協調訓練")
                return False
            
            self.coordination_worker.stop()
            
            # 等待線程結束
            if self.coordination_worker.isRunning():
                self.coordination_worker.wait(3000)  # 等待3秒
            
            # 更新會話狀態
            if self.coordination_session:
                self.coordination_session.stop_session()
            
            # 清理引用
            self.coordination_worker = None
            self.coordination_session = None
            
            self.gui.log_message("⏹️ 協調訓練已停止")
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 停止協調訓練失敗: {e}")
            return False
    
    def get_coordination_status(self) -> Optional[Dict[str, Any]]:
        """
        獲取協調訓練狀態
        
        Returns:
            協調訓練狀態信息
        """
        try:
            if not self.coordination_worker:
                return None
            
            return {
                "is_running": self.coordination_worker.is_running,
                "is_paused": self.coordination_worker.is_paused,
                "current_round": self.coordination_worker.current_round,
                "total_rounds": self.coordination_worker.total_rounds,
                "machine_states": self.coordination_worker.machine_states.copy(),
                "session_status": self.coordination_session.status if self.coordination_session else "unknown"
            }
            
        except Exception as e:
            self.gui.log_message(f"❌ 獲取協調狀態失敗: {e}")
            return None
    
    def _check_prerequisites(self) -> bool:
        """檢查前置條件"""
        try:
            # 檢查是否有連接的發球機
            connected_machines = self.multi_machine_manager.get_connected_machines()
            if not connected_machines:
                self.gui.log_message("❌ 沒有連接的發球機")
                return False
            
            # 檢查是否有運行中的個別訓練
            all_status = self.multi_machine_manager.get_all_training_status()
            running_machines = [
                machine_id for machine_id, status in all_status.items()
                if status.get("is_running", False)
            ]
            
            if running_machines:
                self.gui.log_message(f"❌ 以下發球機正在運行個別訓練: {', '.join(running_machines)}")
                return False
            
            return True
            
        except Exception as e:
            self.gui.log_message(f"❌ 前置條件檢查失敗: {e}")
            return False
    
    def _on_progress_update(self, machine_id: str, current: int, total: int):
        """進度更新回調"""
        try:
            # 更新會話進度
            if self.coordination_session:
                self.coordination_session.update_progress(current, total)
            
            # 通知GUI更新
            if hasattr(self.gui, 'update_coordination_progress'):
                self.gui.update_coordination_progress(machine_id, current, total)
                
        except Exception as e:
            print(f"處理協調進度回調錯誤: {e}")
    
    def _on_message_update(self, machine_id: str, message: str):
        """訊息更新回調"""
        try:
            self.gui.log_message(f"[{machine_id}] {message}")
        except Exception as e:
            print(f"處理協調訊息回調錯誤: {e}")
    
    def _on_coordination_update(self, status: dict):
        """協調狀態更新回調"""
        try:
            # 通知GUI更新協調狀態
            if hasattr(self.gui, 'update_coordination_status'):
                self.gui.update_coordination_status(status)
                
        except Exception as e:
            print(f"處理協調狀態回調錯誤: {e}")
    
    def _on_training_finished(self, machine_id: str, status: str):
        """訓練完成回調"""
        try:
            # 更新會話狀態
            if self.coordination_session:
                if status == "completed":
                    self.coordination_session.stop_session()
                else:
                    self.coordination_session.status = "error"
            
            # 清理引用
            self.coordination_worker = None
            self.coordination_session = None
            
            self.gui.log_message(f"🏁 協調訓練完成: {status}")
            
            # 通知GUI更新
            if hasattr(self.gui, 'on_coordination_finished'):
                self.gui.on_coordination_finished(status)
                
        except Exception as e:
            print(f"處理協調完成回調錯誤: {e}")


def create_coordinated_training_executor(gui_instance, multi_machine_manager: MultiMachineManager) -> CoordinatedTrainingExecutor:
    """
    建立協調訓練執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別實例
        multi_machine_manager: 四台發球機管理器
        
    Returns:
        CoordinatedTrainingExecutor 實例
    """
    return CoordinatedTrainingExecutor(gui_instance, multi_machine_manager)

"""
Training Service

提供依名稱/ID 執行訓練套餐的服務，直接調用現有 GUI 的 execute_training 流程。
"""

from typing import Any, Dict, Optional
from ..registry.program_registry import ProgramRegistry


class TrainingService:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.registry = ProgramRegistry()

    async def run_program(self, program_id: str, balls: float = 10, interval_sec: float = 3.0) -> Dict[str, Any]:
        # 從 ProgramRegistry 獲取程序資料
        program = self.registry.programs.get(program_id)
        if not program:
            return {"ok": False, "error": "program_not_found"}

        # 檢查是否為個別球路程序
        if program.get("category") == "individual_shot":
            return await self._run_individual_shot(program, balls, interval_sec)
        
        # 使用 GUI 的 execute_training 以覆蓋參數
        try:
            # 將 registry 格式轉換為 GUI 期望的格式
            gui_program = {
                "id": program["id"],
                "name": program["name"],
                "description": program.get("description", ""),
                "shots": program.get("shots", []),
                "repeat_times": program.get("repeat_times", 1)
            }
            
            task = self.gui.create_async_task(
                self.gui.execute_training(gui_program, interval_override=interval_sec, balls_override=int(balls))
            )
            return {"ok": True, "task": task}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _run_individual_shot(self, program: Dict[str, Any], balls: float, interval_sec: float) -> Dict[str, Any]:
        """執行個別球路訓練"""
        try:
            shots = program.get("shots", [])
            if not shots:
                return {"ok": False, "error": "no_shots_defined"}
            
            # 只取第一個球路（個別球路程序只有一個球路）
            shot = shots[0]
            section = shot.get("section")
            description = shot.get("description", "")
            
            if not section:
                return {"ok": False, "error": "invalid_shot_section"}
            
            # 使用 DeviceService 發送單一球路
            from .device_service import DeviceService
            import os
            simulate = os.environ.get("SIMULATE", "0") == "1"
            device_service = DeviceService(self.gui, simulate=simulate)
            
            if not device_service.is_connected():
                return {"ok": False, "error": "not_connected"}
            
            # 發送指定數量的球
            sent = 0
            while sent < int(balls):
                result = await device_service.send_shot(section)
                if not result:
                    return {"ok": False, "error": f"shot_failed_at_{sent+1}"}
                
                sent += 1
                self.gui.log_message(f"{description}: 已發送第 {sent} 顆")
                
                if sent < int(balls):  # 最後一顆不需要等待
                    import asyncio
                    await asyncio.sleep(interval_sec)
            
            self.gui.log_message(f"{description} 完成！共發送 {sent} 顆球")
            return {"ok": True, "sent": sent}
            
        except Exception as e:
            return {"ok": False, "error": str(e)}



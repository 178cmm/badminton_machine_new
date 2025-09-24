"""
Command Router（單一入口）

提供狀態機與模板回覆，僅呼叫 Service，不產生文案。
"""

from typing import Any, Dict
from .commands import CommandDTO as Command
from .services.system_service import SystemService
from .services.device_service import DeviceService
from .services.training_service import TrainingService


class StateStore:
    def __init__(self):
        self.state = "IDLE"  # IDLE / DISCOVERING / CONNECTING / CONNECTED / TRAINING / DISCONNECTING

    def set(self, s: str) -> None:
        self.state = s

    def get(self) -> str:
        return self.state


class CommandRouter:
    def __init__(self, gui_instance, reply_templates):
        self.gui = gui_instance
        self.reply = reply_templates
        self.state_store = StateStore()
        # 後續以 DeviceService 取代 SystemService；先並存不改行為
        import os
        simulate = os.environ.get("SIMULATE", "0") == "1"
        self.device_service = DeviceService(gui_instance, simulate=simulate)
        self.training_service = TrainingService(gui_instance)
        # 舊 router 已標記 deprecated，不再委派

    async def handle(self, cmd: Command) -> str:
        intent = cmd.intent

        # WAKE
        if intent == "WAKE":
            return self.reply.WAKE_OK

        # SCAN
        if intent == "SCAN":
            self.state_store.set("DISCOVERING")
            start = self.reply.SCAN_START
            await self.device_service.scan()
            n = 0
            try:
                if hasattr(self.gui, 'device_combo'):
                    n = self.gui.device_combo.count()
            except Exception:
                pass
            self.state_store.set("IDLE")
            return start + "\n" + self.reply.SCAN_DONE(n)

        # CONNECT
        if intent == "CONNECT":
            self.state_store.set("CONNECTING")
            start = self.reply.CONNECT_START
            await self.device_service.connect(None)
            self.state_store.set("CONNECTED")
            return start + "\n" + self.reply.CONNECT_DONE

        # DISCONNECT
        if intent == "DISCONNECT":
            self.state_store.set("DISCONNECTING")
            start = self.reply.DISCONNECT_START
            await self.device_service.disconnect()
            self.state_store.set("IDLE")
            return start + "\n" + self.reply.DISCONNECT_DONE

        # RUN_PROGRAM_BY_NAME
        if intent == "RUN_PROGRAM_BY_NAME":
            if not self.device_service.is_connected():
                return self.reply.NOT_CONNECTED
            slots = cmd.slots or {}
            program_id = slots.get("program_id")
            program_name = slots.get("program_name") or program_id
            balls = slots.get("balls", 10)
            interval = slots.get("interval_sec", 3.0)
            candidates = slots.get("candidates")
            if candidates:
                return self.reply.ASK_DISAMBIGUATION(candidates)
            if not program_id:
                return self.reply.NOT_FOUND
            self.state_store.set("TRAINING")
            try:
                result = await self.training_service.run_program(program_id, balls, interval)
                self.state_store.set("CONNECTED")
                if result.get("ok"):
                    return self.reply.PROGRAM_START(program_name, int(balls), interval)
                else:
                    # 記錄錯誤但不拋出異常
                    from core.audit import write as audit_write
                    audit_write(cmd.meta.get("raw"), cmd.__dict__, None, {"source": cmd.meta.get("source"), "error": result.get("error", "unknown")})
                    return self.reply.NOT_FOUND
            except Exception as e:
                from core.audit import write as audit_write
                audit_write(cmd.meta.get("raw"), cmd.__dict__, None, {"source": cmd.meta.get("source"), "error": str(e)})
                self.state_store.set("CONNECTED")
                return self.reply.NOT_FOUND

        return ""



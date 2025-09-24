"""
Device Service

封裝掃描/連線/斷開（提供真實/模擬注入點）。
暫時直接搬遷自 SystemService，保留相同 API 與行為，不改功能。
"""

from typing import Any, Dict, Optional
import os


class DeviceService:
    def __init__(self, gui_instance, simulate: bool = False):
        self.gui = gui_instance
        # 允許以環境變數覆蓋 simulate 模式
        env_sim = os.environ.get("SIMULATE", "0")
        self.simulate = simulate or (env_sim == "1")

    async def wake(self) -> Dict[str, Any]:
        return {"ok": True}

    async def scan(self) -> Dict[str, Any]:
        if self.simulate:
            # 模擬掃描：更新 UI 並返回假裝找到設備
            try:
                if hasattr(self.gui, 'log_message'):
                    self.gui.log_message("[simulate] 掃描完成，假裝找到 1 台")
            except Exception:
                pass
            return {"ok": True, "count": 1}

        if not hasattr(self.gui, "bluetooth_manager"):
            try:
                from core.managers import create_bluetooth_manager
                self.gui.bluetooth_manager = create_bluetooth_manager(self.gui)
            except Exception:
                return {"ok": False, "error": "bluetooth_manager_not_available"}
        success = await self.gui.bluetooth_manager.scan_devices()
        return {"ok": bool(success)}

    async def connect(self, address: Optional[str] = None) -> Dict[str, Any]:
        if self.simulate:
            try:
                # 給 UI 一個已連線狀態的假線程旗標
                setattr(self.gui, 'bluetooth_manager', type('BM', (), {
                    'is_connected': lambda self=None: True
                })())
            except Exception:
                pass
            return {"ok": True}

        if not hasattr(self.gui, "bluetooth_manager") or self.gui.bluetooth_manager is None:
            try:
                from core.managers import create_bluetooth_manager
                self.gui.bluetooth_manager = create_bluetooth_manager(self.gui)
            except Exception:
                return {"ok": False, "error": "bluetooth_manager_not_available"}

        if address is None and hasattr(self.gui, "device_combo") and self.gui.device_combo.count() > 0:
            address = self.gui.device_combo.currentData()

        if not address:
            try:
                thread = self.gui.bluetooth_manager.get_bluetooth_thread()
                if thread and getattr(thread, "device_address", None):
                    address = thread.device_address
            except Exception:
                pass

        if not address:
            return {"ok": False, "error": "no_device_selected"}

        success = await self.gui.bluetooth_manager.connect_device(address)
        return {"ok": bool(success)}

    async def disconnect(self) -> Dict[str, Any]:
        if self.simulate:
            return {"ok": True}
        if not hasattr(self.gui, "bluetooth_manager") or self.gui.bluetooth_manager is None:
            return {"ok": False, "error": "bluetooth_manager_not_available"}
        success = await self.gui.bluetooth_manager.disconnect_device()
        return {"ok": bool(success)}

    def is_connected(self) -> bool:
        if self.simulate:
            return True
        try:
            if hasattr(self.gui, "bluetooth_manager") and self.gui.bluetooth_manager:
                return bool(self.gui.bluetooth_manager.is_connected())
        except Exception:
            pass
        return False

    async def send_shot(self, section: str) -> bool:
        if self.simulate:
            try:
                if hasattr(self.gui, 'log_message'):
                    self.gui.log_message(f"[simulate] 發送單球：{section}")
            except Exception:
                pass
            return True
        try:
            if hasattr(self.gui, 'bluetooth_manager') and self.gui.bluetooth_manager:
                thread = self.gui.bluetooth_manager.get_bluetooth_thread()
                if thread and getattr(thread, 'is_connected', False):
                    return await thread.send_shot(section)
        except Exception:
            return False
        return False



"""
System Service

封裝系統層指令（WAKE/SCAN/CONNECT/DISCONNECT）的實作，對接 GUI 與 BluetoothManager。
"""

from typing import Any, Dict, Optional


class SystemService:
    def __init__(self, gui_instance):
        self.gui = gui_instance

    async def wake(self) -> Dict[str, Any]:
        # 僅回覆即可
        return {"ok": True}

    async def scan(self) -> Dict[str, Any]:
        if not hasattr(self.gui, "bluetooth_manager"):
            # 若尚未建立，嘗試建立
            try:
                from core.managers import create_bluetooth_manager
                self.gui.bluetooth_manager = create_bluetooth_manager(self.gui)
            except Exception:
                return {"ok": False, "error": "bluetooth_manager_not_available"}

        success = await self.gui.bluetooth_manager.scan_devices()
        # Manager 會自行將找到的裝置更新到 UI
        return {"ok": bool(success)}

    async def connect(self, address: Optional[str] = None) -> Dict[str, Any]:
        if not hasattr(self.gui, "bluetooth_manager") or self.gui.bluetooth_manager is None:
            try:
                from core.managers import create_bluetooth_manager
                self.gui.bluetooth_manager = create_bluetooth_manager(self.gui)
            except Exception:
                return {"ok": False, "error": "bluetooth_manager_not_available"}

        # 若未指定地址，嘗試從 UI 選單讀取
        if address is None and hasattr(self.gui, "device_combo") and self.gui.device_combo.count() > 0:
            address = self.gui.device_combo.currentData()

        if not address:
            # 若尚未選擇，嘗試用 manager 掃描到的 thread 狀態
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
        if not hasattr(self.gui, "bluetooth_manager") or self.gui.bluetooth_manager is None:
            return {"ok": False, "error": "bluetooth_manager_not_available"}
        success = await self.gui.bluetooth_manager.disconnect_device()
        return {"ok": bool(success)}



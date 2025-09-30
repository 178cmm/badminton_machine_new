"""
System Service

封裝系統層指令（WAKE/SCAN/CONNECT/DISCONNECT）的實作，對接 GUI 與 BluetoothManager。
新增狀態機功能：統一管理開始/暫停/停止狀態，支援簡報筆遙控。
"""

import time
import asyncio
from enum import Enum
from typing import Any, Dict, Optional


class State(Enum):
    """系統狀態枚舉"""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class SystemService:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        # 狀態機相關屬性
        self._state = State.IDLE
        self._last_toggle_time = 0.0
        self._debounce_ms = 500  # 防抖時間（毫秒）

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

    # ========== 狀態機相關方法 ==========
    
    def get_state(self) -> State:
        """取得當前狀態"""
        return self._state
    
    def start(self) -> bool:
        """開始訓練/發球"""
        if self._state == State.EMERGENCY_STOP:
            # 急停狀態需要先重置
            self._state = State.IDLE
            return False
        
        if self._state == State.IDLE:
            self._state = State.RUNNING
            return True
        
        return False  # 已在運行中
    
    def pause(self) -> bool:
        """暫停訓練/發球"""
        if self._state == State.RUNNING:
            self._state = State.IDLE
            return True
        
        return False  # 不在運行中
    
    def stop(self) -> bool:
        """急停訓練/發球"""
        if self._state in [State.RUNNING, State.IDLE]:
            self._state = State.EMERGENCY_STOP
            return True
        
        return False  # 已在急停狀態
    
    def toggle(self) -> bool:
        """切換開始/暫停狀態（帶防抖）"""
        current_time = time.time() * 1000  # 轉換為毫秒
        
        # 防抖檢查
        if current_time - self._last_toggle_time < self._debounce_ms:
            return False
        
        self._last_toggle_time = current_time
        
        if self._state == State.RUNNING:
            return self.pause()
        elif self._state == State.IDLE:
            return self.start()
        else:  # EMERGENCY_STOP
            # 急停狀態下，toggle 會重置為 IDLE
            self._state = State.IDLE
            return True
    
    def reset(self) -> bool:
        """重置狀態為 IDLE"""
        if self._state != State.IDLE:
            self._state = State.IDLE
            return True
        return False



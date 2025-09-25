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

        try:
            if not hasattr(self.gui, "bluetooth_manager") or self.gui.bluetooth_manager is None:
                try:
                    from core.managers import create_bluetooth_manager
                    self.gui.bluetooth_manager = create_bluetooth_manager(self.gui)
                except Exception as e:
                    if hasattr(self.gui, 'log_message'):
                        self.gui.log_message(f"❌ 創建藍牙管理器失敗: {e}")
                    return {"ok": False, "error": "bluetooth_manager_not_available"}
            
            if self.gui.bluetooth_manager is None:
                if hasattr(self.gui, 'log_message'):
                    self.gui.log_message("❌ 藍牙管理器未初始化")
                return {"ok": False, "error": "bluetooth_manager_not_initialized"}
            
            success = await self.gui.bluetooth_manager.scan_devices()
            return {"ok": bool(success)}
        except Exception as e:
            if hasattr(self.gui, 'log_message'):
                self.gui.log_message(f"❌ 掃描設備失敗: {e}")
            return {"ok": False, "error": str(e)}
    
    def scan_sync(self) -> Dict[str, Any]:
        """同步掃描方法，用於沒有事件循環時"""
        if self.simulate:
            # 模擬掃描：更新 UI 並返回假裝找到設備
            try:
                if hasattr(self.gui, 'log_message'):
                    self.gui.log_message("[simulate] 掃描完成，假裝找到 1 台")
            except Exception:
                pass
            return {"ok": True, "count": 1}
        
        # 嘗試在線程中運行異步掃描
        try:
            import threading
            import queue
            import asyncio
            
            result_queue = queue.Queue()
            
            def run_scan():
                try:
                    # 創建新的事件循環
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # 運行掃描
                    result = new_loop.run_until_complete(self.scan())
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    new_loop.close()
            
            # 在後台線程中運行掃描
            scan_thread = threading.Thread(target=run_scan, daemon=True)
            scan_thread.start()
            
            # 等待結果（最多等待10秒）
            try:
                status, result = result_queue.get(timeout=10)
                if status == 'success':
                    return result
                else:
                    if hasattr(self.gui, 'log_message'):
                        self.gui.log_message(f"❌ 後備掃描失敗: {result}")
                    return {"ok": False, "error": str(result)}
            except queue.Empty:
                if hasattr(self.gui, 'log_message'):
                    self.gui.log_message("❌ 掃描超時，請檢查設備是否開機")
                return {"ok": False, "error": "scan_timeout"}
                
        except Exception as e:
            if hasattr(self.gui, 'log_message'):
                self.gui.log_message(f"❌ 後備掃描方法失敗: {e}")
            return {"ok": False, "error": str(e)}

    async def connect(self, address: Optional[str] = None) -> Dict[str, Any]:
        try:
            if self.simulate:
                try:
                    # 給 UI 一個已連線狀態的假線程旗標
                    setattr(self.gui, 'bluetooth_manager', type('BM', (), {
                        'is_connected': lambda self=None: True
                    })())
                except Exception as e:
                    self.gui.log_message(f"❌ 模擬模式設置失敗: {e}")
                return {"ok": True}

            if not hasattr(self.gui, "bluetooth_manager") or self.gui.bluetooth_manager is None:
                try:
                    from core.managers import create_bluetooth_manager
                    self.gui.bluetooth_manager = create_bluetooth_manager(self.gui)
                except Exception as e:
                    self.gui.log_message(f"❌ 創建藍牙管理器失敗: {e}")
                    return {"ok": False, "error": "bluetooth_manager_not_available"}

            if address is None and hasattr(self.gui, "device_combo") and self.gui.device_combo.count() > 0:
                address = self.gui.device_combo.currentData()

            if not address:
                try:
                    thread = self.gui.bluetooth_manager.get_bluetooth_thread()
                    if thread and getattr(thread, "device_address", None):
                        address = thread.device_address
                except Exception as e:
                    self.gui.log_message(f"❌ 獲取設備地址失敗: {e}")

            if not address:
                self.gui.log_message("❌ 未選擇設備")
                return {"ok": False, "error": "no_device_selected"}

            success = await self.gui.bluetooth_manager.connect_device(address)
            return {"ok": bool(success)}
            
        except Exception as e:
            self.gui.log_message(f"❌ 連接過程發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return {"ok": False, "error": str(e)}

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



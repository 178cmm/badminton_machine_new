import asyncio
import pathlib
import time
import json
import os
from unittest.mock import Mock


async def main():
    import sys
    import os
    # 將父目錄加入路徑以便匯入上層模組
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    try:
        from ui.io_bridge import IOBridge
    except ImportError:
        print("警告: 無法匯入 IOBridge，跳過原有測試")
        IOBridge = None
    # 構造一個簡易 GUI stub 以便輸出（實際應由主程式提供）
    class StubGUI:
        def __init__(self):
            self.texts = []
            self.device_combo = type('MockCombo', (), {'count': lambda: 0})()
        def add_voice_chat_message(self, text, t):
            self.texts.append(text)
        def log_message(self, text):
            print(f"[GUI LOG] {text}")
        def create_async_task(self, coro):
            return coro
        def execute_training(self, program, interval_override=None, balls_override=None):
            print(f"[GUI EXECUTE] {program['name']} - {balls_override} balls, {interval_override}s interval")
            return True
        def __getattr__(self, name):
            # 提供必要的屬性占位
            raise AttributeError

    if IOBridge:
        gui = StubGUI()
        bridge = IOBridge(gui)

        CASES = [
            "啟動",
            "掃描",
            "連線",
            "基礎訓練",
            "正手平抽",
            "正手高远",
            "平抽",
            "基礎訓練 12顆 間隔2.5秒",
            "斷開",
        ]
        # 未連線保護
        CASES_NOT_CONNECTED = [
            "斷開",
            "基礎訓練",
        ]
        print("== simulate e2e ==")
        for s in CASES:
            print("\n>", s)
            reply = await bridge.handle_text_async(s, source="text")
            print("<", reply)
        print("\n== simulate guard (not connected) ==")
        for s in CASES_NOT_CONNECTED:
            print("\n>", s)
            reply = await bridge.handle_text_async(s, source="text")
            print("<", reply)
        # 多候選後再精確名稱
        print("\n== simulate disambiguation ==")
        reply = await bridge.handle_text_async("平抽", source="text")
        print("<", reply)
        reply = await bridge.handle_text_async("反手平抽球", source="text")
        print("<", reply)
        p = pathlib.Path("logs/commands.jsonl")
        print("\nlog:", str(p.resolve()) if p.exists() else "no log")
    else:
        print("跳過原有 IOBridge 測試")
    
    # 新增：簡報筆遙控測試
    print("\n== 簡報筆遙控測試 ==")
    await test_remote_control()


async def test_remote_control():
    """測試簡報筆遙控功能"""
    from core.services.system_service import SystemService, State
    
    # 創建模擬 GUI 實例
    mock_gui = Mock()
    mock_gui.log_message = lambda msg: print(f"[GUI LOG] {msg}")
    
    # 創建系統服務
    system_service = SystemService(mock_gui)
    
    print("1. 測試狀態機基本功能")
    print(f"   初始狀態: {system_service.get_state()}")
    
    # 測試開始
    success = system_service.start()
    print(f"   開始訓練: {success}, 狀態: {system_service.get_state()}")
    
    # 測試暫停
    success = system_service.pause()
    print(f"   暫停訓練: {success}, 狀態: {system_service.get_state()}")
    
    # 測試急停
    success = system_service.stop()
    print(f"   急停訓練: {success}, 狀態: {system_service.get_state()}")
    
    print("\n2. 測試 toggle 功能")
    system_service.reset()
    print(f"   重置後狀態: {system_service.get_state()}")
    
    # 測試 toggle: IDLE -> RUNNING
    success = system_service.toggle()
    print(f"   Toggle (IDLE->RUNNING): {success}, 狀態: {system_service.get_state()}")
    
    # 測試 toggle: RUNNING -> IDLE (等待防抖時間)
    time.sleep(0.6)  # 等待超過 500ms 防抖時間
    success = system_service.toggle()
    print(f"   Toggle (RUNNING->IDLE): {success}, 狀態: {system_service.get_state()}")
    
    print("\n3. 測試防抖機制")
    # 快速連續觸發
    start_time = time.time()
    results = []
    for i in range(5):
        success = system_service.toggle()
        results.append((i, success, system_service.get_state()))
        time.sleep(0.1)  # 100ms 間隔，小於 500ms 防抖時間
    
    print("   快速連續觸發結果:")
    for i, success, state in results:
        print(f"     第{i+1}次: {success}, 狀態: {state}")
    
    print("\n4. 測試事件記錄")
    # 模擬事件記錄
    test_log_events()
    
    print("\n5. 測試狀態燈更新")
    test_status_light_updates()
    
    print("\n6. 測試智能檢查功能")
    test_smart_check()


def test_log_events():
    """測試事件記錄功能"""
    # 確保 logs 目錄存在
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 模擬事件記錄
    test_events = [
        {"event": "TOGGLE_START_PAUSE", "state": "RUNNING", "source": "keyboard"},
        {"event": "TOGGLE_START_PAUSE", "state": "IDLE", "source": "keyboard"},
        {"event": "EMERGENCY_STOP", "state": "EMERGENCY_STOP", "source": "keyboard"},
    ]
    
    log_file = os.path.join(logs_dir, "commands.jsonl")
    
    # 記錄測試事件
    for event_data in test_events:
        event_data["timestamp"] = int(time.time())
        event_data["extra"] = {"source": event_data["source"]}
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_data, ensure_ascii=False) + "\n")
            print(f"   記錄事件: {event_data['event']} -> {event_data['state']}")
        except Exception as e:
            print(f"   記錄失敗: {e}")
    
    # 驗證記錄
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            print(f"   日誌檔案總行數: {len(lines)}")
            if lines:
                last_line = json.loads(lines[-1])
                print(f"   最後一筆記錄: {last_line['event']} at {last_line['timestamp']}")


def test_status_light_updates():
    """測試狀態燈更新功能"""
    from core.services.system_service import State
    
    # 模擬狀態燈更新
    states = [State.IDLE, State.RUNNING, State.EMERGENCY_STOP]
    state_names = ["待機", "發球中", "急停"]
    colors = ["黃色", "綠色", "紅色"]
    
    print("   狀態燈測試:")
    for state, name, color in zip(states, state_names, colors):
        print(f"     {state.value}: {name} ({color})")


def test_smart_check():
    """測試智能檢查功能"""
    from unittest.mock import Mock
    
    # 創建模擬 GUI 實例
    mock_gui = Mock()
    mock_gui.log_message = lambda msg: print(f"[GUI LOG] {msg}")
    
    # 模擬不同的標籤頁狀態
    test_cases = [
        {
            "name": "課程訓練（有選擇套餐）",
            "tab": Mock(program_combo=Mock(currentIndex=lambda: 0)),
            "expected": True
        },
        {
            "name": "課程訓練（未選擇套餐）",
            "tab": Mock(program_combo=Mock(currentIndex=lambda: -1)),
            "expected": False
        },
        {
            "name": "手動控制（有選擇位置）",
            "tab": Mock(current_burst_section="sec5"),
            "expected": True
        },
        {
            "name": "手動控制（未選擇位置）",
            "tab": Mock(current_burst_section=None),
            "expected": False
        },
        {
            "name": "基礎訓練（有選擇球路）",
            "tab": Mock(selected_training="正手高遠球"),
            "expected": True
        },
        {
            "name": "基礎訓練（未選擇球路）",
            "tab": Mock(selected_training=None),
            "expected": False
        }
    ]
    
    print("   智能檢查測試:")
    for case in test_cases:
        # 模擬 _has_available_training_target 的邏輯
        tab = case["tab"]
        has_target = False
        
        # 檢查課程訓練
        if hasattr(tab, 'program_combo') and hasattr(tab.program_combo, 'currentIndex'):
            try:
                index = tab.program_combo.currentIndex()
                if callable(index):
                    index = index()
                if index >= 0:
                    has_target = True
            except:
                pass
        # 檢查手動控制
        if not has_target and hasattr(tab, 'current_burst_section') and tab.current_burst_section:
            has_target = True
        # 檢查基礎訓練
        if not has_target and hasattr(tab, 'selected_training') and tab.selected_training:
            has_target = True
        
        result = "✅ 通過" if has_target == case["expected"] else "❌ 失敗"
        print(f"     {case['name']}: {result} (預期: {case['expected']}, 實際: {has_target})")


if __name__ == "__main__":
    asyncio.run(main())



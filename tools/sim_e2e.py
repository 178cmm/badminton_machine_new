import asyncio
import pathlib


async def main():
    from ui.io_bridge import IOBridge
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


if __name__ == "__main__":
    asyncio.run(main())



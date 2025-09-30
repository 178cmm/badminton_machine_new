# 語音控制統一路徑方案實施計劃

## 📋 概述

本文檔詳細記錄了將語音控制系統整合到統一路徑架構中的完整實施方案，使語音控制能夠達到與文本控制相同的發球機控制能力。

## 🎯 目標

- 讓語音控制支援所有文本控制的功能
- 統一語音和文本控制的處理邏輯
- 提高代碼復用性和維護性
- 確保系統架構的一致性

## 📊 現狀分析

### 語音控制系統版本
- **舊版語音控制** (`voice_control.py`) - 基於 Vosk 本地模型，功能完整
- **新版語音控制** (`voice_control_tts.py`) - 基於 Whisper API + TTS，功能不完整

### 功能對比表

| 功能 | 文本控制 | 舊版語音控制 | 新版語音控制TTS |
|------|----------|-------------|----------------|
| **直接發球指令** | ✅ 完整支援 | ✅ 完整支援 | ❌ **不完整** |
| **連線控制** | ✅ 完整支援 | ✅ 完整支援 | ✅ 完整支援 |
| **訓練模式** | ✅ 完整支援 | ✅ 完整支援 | ❌ **不完整** |
| **模擬對打** | ✅ 完整支援 | ✅ 完整支援 | ❌ **不完整** |

### 現有架構優勢
- **IOBridge** (`ui/io_bridge.py`) - 統一處理語音和文本輸入
- **UnifiedParser** (`core/parsers/unified_parser.py`) - 統一解析邏輯
- **CommandRouter** (`core/router.py`) - 統一執行邏輯

## 🚀 實施方案

### 📋 階段一：基礎架構擴展（1-2天）

#### 步驟1：擴展UnifiedParser - 添加球種解析
**文件：** `core/parsers/unified_parser.py`

```python
# 在現有parse方法中添加球種解析邏輯
def parse(self, text: str, source: str = "text") -> Optional[CommandDTO]:
    t = (text or "").strip()
    if not t:
        return None

    # ... 現有的WAKE、SCAN、CONNECT、DISCONNECT邏輯 ...

    # 新增：球種解析
    shot_result = self._parse_shot_command(t)
    if shot_result:
        return make_command("RUN_SPECIFIC_SHOT", source, text, slots=shot_result)

    # ... 現有的程式名稱匹配邏輯 ...
    return None

def _parse_shot_command(self, text: str) -> Optional[Dict[str, Any]]:
    """解析球種指令"""
    # 球種模式匹配
    shot_patterns = [
        (r"正手高遠球", "正手高遠球"),
        (r"反手高遠球", "反手高遠球"),
        (r"正手切球", "正手切球"),
        (r"反手切球", "反手切球"),
        (r"正手殺球", "正手殺球"),
        (r"反手殺球", "反手殺球"),
        (r"正手平抽球", "正手平抽球"),
        (r"反手平抽球", "反手平抽球"),
        (r"正手小球", "正手小球"),
        (r"反手小球", "反手小球"),
        (r"正手挑球", "正手挑球"),
        (r"反手挑球", "反手挑球"),
        (r"平推球", "平推球"),
        (r"正手接殺球", "正手接殺球"),
        (r"反手接殺球", "反手接殺球"),
        (r"近身接殺", "近身接殺"),
    ]
    
    shot_name = None
    for pattern, name in shot_patterns:
        if re.search(pattern, text):
            shot_name = name
            break
    
    if not shot_name:
        return None
    
    # 提取數量和間隔
    balls, interval = extract_numbers(text)
    balls = int(balls) if balls is not None else 10
    interval = float(interval) if interval is not None else 3.0
    
    return {
        "shot_name": shot_name,
        "balls": balls,
        "interval_sec": interval,
    }
```

#### 步驟2：擴展CommandRouter - 添加球種執行
**文件：** `core/router/command_router.py`

```python
async def handle(self, cmd: Command) -> str:
    intent = cmd.intent

    # ... 現有的WAKE、SCAN、CONNECT、DISCONNECT、RUN_PROGRAM_BY_NAME邏輯 ...

    # 新增：RUN_SPECIFIC_SHOT
    if intent == "RUN_SPECIFIC_SHOT":
        if not self.device_service.is_connected():
            return self.reply.NOT_CONNECTED
        
        slots = cmd.slots or {}
        shot_name = slots.get("shot_name")
        balls = slots.get("balls", 10)
        interval = slots.get("interval_sec", 3.0)
        
        try:
            result = await self.training_service.run_specific_shot(shot_name, balls, interval)
            if result.get("ok"):
                return self.reply.SHOT_START(shot_name, int(balls), interval)
            else:
                return self.reply.SHOT_NOT_FOUND(shot_name)
        except Exception as e:
            return self.reply.SHOT_ERROR(shot_name, str(e))

    return ""
```

#### 步驟3：擴展TrainingService - 添加球種執行方法
**文件：** `core/services/training_service.py`

```python
async def run_specific_shot(self, shot_name: str, balls: int, interval: float) -> Dict[str, Any]:
    """執行特定球種發球"""
    try:
        # 獲取球種對應的section
        from ..parsers.basic_training_parser import get_section_by_shot_name
        section = get_section_by_shot_name(shot_name)
        
        if not section:
            return {"ok": False, "error": f"找不到球種：{shot_name}"}
        
        # 檢查連接狀態
        if not self.device_service.is_connected():
            return {"ok": False, "error": "發球機未連接"}
        
        # 執行發球
        sent = 0
        for i in range(int(balls)):
            if getattr(self.gui, "stop_flag", False):
                self.gui.log_message("發球被停止")
                break
            
            result = await self.device_service.send_shot(section)
            if not result:
                return {"ok": False, "error": f"第{i+1}顆球發送失敗"}
            
            sent += 1
            self.gui.log_message(f"發送 {shot_name} 第 {sent} 顆")
            
            if sent < int(balls):  # 最後一顆不需要等待
                import asyncio
                await asyncio.sleep(interval)
        
        self.gui.log_message(f"{shot_name} 完成！共發送 {sent}/{balls} 顆球")
        return {"ok": True, "sent": sent}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

#### 步驟4：擴展ReplyTemplates - 添加球種回覆模板
**文件：** `gui/response_templates.py`

```python
class ReplyTemplates:
    # ... 現有模板 ...

    # 新增：球種相關回覆
    @staticmethod
    def SHOT_START(shot_name: str, balls: int, interval: float) -> str:
        return f"開始『{shot_name}』：共 {balls} 顆、每球 {interval} 秒"
    
    @staticmethod
    def SHOT_NOT_FOUND(shot_name: str) -> str:
        return f"抱歉，找不到球種『{shot_name}』，請檢查球種名稱"
    
    @staticmethod
    def SHOT_ERROR(shot_name: str, error: str) -> str:
        return f"執行『{shot_name}』時發生錯誤：{error}"
    
    SHOT_DONE = "球種訓練完成，辛苦了！"
```

### 📋 階段二：語音控制整合優化（1天）

#### 步驟5：優化語音控制TTS的IOBridge整合
**文件：** `gui/ui_voice.py`

```python
# 在_start_voice函數中優化IOBridge整合
async def _patched_process_command(text: str):
    try:
        # 使用IOBridge統一處理
        self._io_bridge.handle_text(text, source="voice")
    except Exception as e:
        # 記錄錯誤但不崩潰
        self._log_ui(f"⚠️ 語音指令處理失敗：{e}")
        # 嘗試原始流程作為備用
        try:
            if original_process:
                await original_process(text)
        except Exception:
            pass
```

#### 步驟6：添加語音控制狀態反饋
**文件：** `gui/ui_voice.py`

```python
def _log_ui(self, message: str):
    """統一的UI日誌記錄"""
    try:
        if hasattr(self, 'voice_chat_log') and self.voice_chat_log is not None:
            self.voice_chat_log.append(message)
            self.voice_chat_log.ensureCursorVisible()
        elif hasattr(self, 'text_chat_log') and self.text_chat_log is not None:
            self.text_chat_log.append(message)
            self.text_chat_log.ensureCursorVisible()
    except Exception:
        pass
```

### 📋 階段三：測試和驗證（1天）

#### 步驟7：創建測試腳本
**文件：** `test_unified_voice_control.py`

```python
#!/usr/bin/env python3
"""
統一路徑語音控制測試腳本
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.parsers.unified_parser import UnifiedParser
from core.router import CommandRouter
from gui.response_templates import ReplyTemplates

class MockGUI:
    def __init__(self):
        self.device_combo = type('obj', (object,), {'count': lambda: 1})()
        self.stop_flag = False
    
    def log_message(self, msg):
        print(f"[GUI] {msg}")
    
    def create_async_task(self, coro):
        return asyncio.create_task(coro)

async def test_shot_commands():
    """測試球種指令解析和執行"""
    parser = UnifiedParser()
    gui = MockGUI()
    router = CommandRouter(gui, ReplyTemplates)
    
    test_commands = [
        "正手高遠球 20 顆 間隔 3 秒",
        "反手切球 15 顆",
        "正手殺球 10 顆 間隔 2 秒",
        "平推球 5 顆",
    ]
    
    for cmd_text in test_commands:
        print(f"\n🧪 測試指令：{cmd_text}")
        
        # 解析指令
        cmd = parser.parse(cmd_text, source="voice")
        if cmd:
            print(f"✅ 解析成功：{cmd.intent} - {cmd.slots}")
            
            # 模擬執行（不實際發球）
            try:
                reply = await router.handle(cmd)
                print(f"📝 回覆：{reply}")
            except Exception as e:
                print(f"❌ 執行失敗：{e}")
        else:
            print("❌ 解析失敗")

if __name__ == "__main__":
    asyncio.run(test_shot_commands())
```

#### 步驟8：創建語音控制測試用例
**文件：** `test_voice_integration.py`

```python
#!/usr/bin/env python3
"""
語音控制整合測試
"""

import asyncio
from voice_control_tts import VoiceControlTTS, VoiceConfig

class MockWindow:
    def __init__(self):
        self.voice_chat_log = []
        self.text_chat_log = []
        self.stop_flag = False
    
    def log_message(self, msg):
        print(f"[MockWindow] {msg}")
    
    def add_voice_chat_message(self, msg, sender):
        self.voice_chat_log.append(f"{sender}: {msg}")
        print(f"[VoiceChat] {sender}: {msg}")

async def test_voice_shot_commands():
    """測試語音球種指令"""
    config = VoiceConfig()
    config.enable_tts = False  # 測試時關閉TTS
    config.enable_rules = True
    
    window = MockWindow()
    voice_control = VoiceControlTTS(window, config)
    
    # 模擬語音指令
    test_commands = [
        "正手高遠球 20 顆",
        "反手切球 15 顆 間隔 3 秒",
        "開始正手殺球練習",
    ]
    
    for cmd in test_commands:
        print(f"\n🎙️ 模擬語音指令：{cmd}")
        await voice_control._process_command(cmd)
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(test_voice_shot_commands())
```

### 📋 階段四：文檔和部署（0.5天）

#### 步驟9：更新文檔
**文件：** `docs/VOICE_CONTROL_INTEGRATION.md`

```markdown
# 語音控制統一路徑整合文檔

## 概述
語音控制系統已整合到統一路徑架構中，現在語音和文本控制使用相同的解析和執行邏輯。

## 支援的語音指令

### 球種發球指令
- "正手高遠球 20 顆 間隔 3 秒"
- "反手切球 15 顆"
- "正手殺球 10 顆 間隔 2 秒"
- "平推球 5 顆"

### 系統控制指令
- "掃描發球機"
- "連線"
- "斷開"
- "停止"

## 架構說明
1. 語音識別 → IOBridge → UnifiedParser → CommandRouter → TrainingService
2. 與文本控制使用完全相同的執行路徑
3. 支援所有現有的球種和訓練模式
```

#### 步驟10：創建部署檢查清單
**文件：** `DEPLOYMENT_CHECKLIST.md`

```markdown
# 語音控制統一路徑部署檢查清單

## 部署前檢查
- [ ] UnifiedParser 已擴展球種解析
- [ ] CommandRouter 已添加球種執行邏輯
- [ ] TrainingService 已實現球種發球方法
- [ ] ReplyTemplates 已添加球種回覆模板
- [ ] 語音控制TTS已整合IOBridge
- [ ] 測試腳本通過所有測試用例

## 部署後驗證
- [ ] 語音控制可以識別球種指令
- [ ] 語音控制可以執行發球機動作
- [ ] 語音和文本控制行為一致
- [ ] 錯誤處理正常
- [ ] UI反饋正常
```

## 📊 實施時間表

| 階段 | 步驟 | 預估時間 | 負責人 | 狀態 |
|------|------|----------|--------|------|
| 階段一 | 1-4 | 1-2天 | 開發者 | ⏳ 待開始 |
| 階段二 | 5-6 | 1天 | 開發者 | ⏳ 待開始 |
| 階段三 | 7-8 | 1天 | 開發者 | ⏳ 待開始 |
| 階段四 | 9-10 | 0.5天 | 開發者 | ⏳ 待開始 |
| **總計** | | **3.5-4.5天** | | |

## 🎯 成功標準

1. **功能完整性**：語音控制支援所有文本控制的功能
2. **行為一致性**：語音和文本控制產生相同的結果
3. **錯誤處理**：妥善處理各種異常情況
4. **用戶體驗**：提供清晰的語音反饋和狀態提示
5. **代碼質量**：遵循現有架構，代碼可維護

## 🚀 部署策略

1. **漸進式部署**：先在測試環境驗證，再部署到生產環境
2. **回滾準備**：保留原有語音控制邏輯作為備用
3. **監控機制**：部署後密切監控語音控制功能
4. **用戶培訓**：提供新的語音指令使用指南

## 📝 支援的球種指令

### 完整球種列表
- 正手高遠球
- 反手高遠球
- 正手切球
- 反手切球
- 正手殺球
- 反手殺球
- 正手平抽球
- 反手平抽球
- 正手小球
- 反手小球
- 正手挑球
- 反手挑球
- 平推球
- 正手接殺球
- 反手接殺球
- 近身接殺

### 指令格式範例
```
[球種名稱] [數量] [間隔時間]

範例：
- "正手高遠球 20 顆 間隔 3 秒"
- "反手切球 15 顆"
- "正手殺球 10 顆 間隔 2 秒"
- "平推球 5 顆"
```

## 🔧 技術架構

### 統一路徑流程
```
語音輸入 → Whisper API → IOBridge → UnifiedParser → CommandRouter → TrainingService → 發球機
文本輸入 → 直接輸入 → IOBridge → UnifiedParser → CommandRouter → TrainingService → 發球機
```

### 關鍵組件
- **IOBridge**: 統一處理語音和文本輸入
- **UnifiedParser**: 統一解析邏輯，支援球種指令
- **CommandRouter**: 統一執行邏輯，路由到對應服務
- **TrainingService**: 執行具體的發球機控制
- **ReplyTemplates**: 統一回覆模板

## 📋 注意事項

1. **向後相容性**：保持現有功能不受影響
2. **錯誤處理**：妥善處理各種異常情況
3. **性能考量**：確保語音識別和執行的響應速度
4. **用戶體驗**：提供清晰的狀態反饋和錯誤提示
5. **測試覆蓋**：確保所有功能都有對應的測試用例

## 🎉 預期效果

實施完成後，語音控制系統將具備與文本控制完全相同的功能：

- ✅ 支援所有球種的直接發球指令
- ✅ 支援連線控制（掃描、連接、斷開）
- ✅ 支援訓練模式控制
- ✅ 支援模擬對打功能
- ✅ 統一的錯誤處理和用戶反饋
- ✅ 與文本控制完全一致的行為

---

**文檔版本**: 1.0  
**創建日期**: 2024年12月  
**最後更新**: 2024年12月  
**狀態**: 待實施

# 貢獻指南

## 提交規範

### 必要檢查
- 若修改 Parser/模板，必須附上對應測試
- 若修改 simulate 行為，需更新 golden log
- 所有提交前必須通過 CI 檢查

### 提交訊息格式
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

類型：
- `feat`: 新功能
- `fix`: 修復
- `docs`: 文檔更新
- `style`: 代碼格式
- `refactor`: 重構
- `test`: 測試
- `chore`: 構建/工具

## 本地驗收流程

### 基本驗收
1. 設定模擬模式：
```bash
export SIMULATE=true
```

2. 執行端到端測試：
```bash
python tools/sim_e2e.py
```

3. 檢查審計日誌：
```bash
tail -f logs/commands.jsonl
```

4. 執行測試套件：
```bash
pytest
```

### 語音控制驗收
1. 設定 OpenAI API Key
2. 啟動語音控制
3. 測試關鍵指令：
   - 「連線發球機」
   - 「前場練習」
   - 「停止訓練」

### 雙發球機驗收
1. 連接左右發球機
2. 測試協調模式（同時/交替/序列）
3. 驗證發球時序和位置

## CI 檢查項

### 自動檢查
- **Deprecated 掃描**：確保無 deprecated 引用
- **Pytest 全綠**：所有測試必須通過
- **代碼格式**：符合專案規範
- **類型檢查**：Python 類型註解檢查

### 手動檢查
- 文檔更新完整性
- 向後相容性
- 效能影響評估

## 開發環境設定

### 必要工具
- Python 3.8+
- PyQt5
- OpenAI API Key（語音功能）

### 可選工具
- ripgrep（用於 CI 檢查）
- pytest（測試框架）

## 測試策略

### 單元測試
- 核心邏輯測試
- Parser 功能測試
- 狀態機測試

### 整合測試
- 端到端流程測試
- 語音控制整合測試
- 雙發球機協調測試

### 模擬測試
- 使用 `SIMULATE=true` 進行無硬體測試
- Golden log 比對
- 效能基準測試

## 故障排除

### 常見問題
1. **藍牙連接失敗**：檢查設備狀態和權限
2. **語音識別不準確**：確認網路和 API Key
3. **測試失敗**：檢查環境變數和依賴

### 除錯工具
- 查看 `logs/commands.jsonl` 審計日誌
- 使用 `SIMULATE=true` 進行隔離測試
- 檢查 GUI 狀態顯示

## 文檔維護

### 更新時機
- 新增功能時更新對應文檔
- 修改 API 時更新使用說明
- 重大變更時更新架構文檔

### 文檔結構
- `docs/` 目錄存放詳細文檔
- `README.md` 提供快速開始指南
- `CONTRIBUTING.md` 本檔案

## 聯絡與支援

如有問題或建議，請：
1. 查看現有文檔和 FAQ
2. 搜尋已知問題
3. 提交 Issue 或 Pull Request

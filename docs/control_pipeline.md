# 控制管線與狀態機概覽

## 系統流程圖

Input（文字/ASR） → NLU（Parser/Matcher） → Command → Router（State） → Services（Device/Training） → Reply（TTS/UI/Log）

### 元件職責（簡述）
- Input: 來源包含 GUI 文字框、語音 ASR（Whisper/Vosk）
- NLU: 
  - Parser：結構化抽取（如「快速」「前場」「球數」等）
  - Matcher：規則與關鍵詞命中（`rules/badminton_rules.yaml`）
- Command: 標準化後的指令物件（type、payload、meta）
- Router（State）：依目前系統狀態決定落地服務與動作（含 simulate）
- Services：
  - Device：掃描、連線、斷線、單/雙機發球（藍牙）
  - Training：基礎/進階/模擬對打執行器
- Reply：回饋到 UI 與語音（TTS），並寫入審計日誌

## 狀態機說明

核心狀態與轉移條件（節錄）：
- Idle → Connecting：收到 `scan/connect` 指令或 GUI 連線動作
- Connecting → Connected：藍牙連線成功（單/雙機）
- Connected → Training：收到訓練指令（start_training、front_court_training…）
- Training → Connected：收到停止訓練指令或訓練自然結束
- 任意 → Error：服務層拋出錯誤（裝置離線等）
- 任意 ↔ Simulate：`simulate=true` 時，路由改向 Fake services（不觸發實機藍牙）

狀態來源與維護：
- GUI 主窗口持有連線狀態、訓練任務與旗標（如 `stop_flag`）
- 語音模組在處理連線/訓練前會檢查狀態（避免不合法轉移）

## Simulate 模式

- 切換方式：設定 `simulate=true`（環境變數或設定檔，實作依專案配置）
- 行為：
  - 所有 Device/Training 呼叫改向 Fake services，不做實機藍牙與真實發球
  - 仍會經過完整 NLU → Router → Services → Reply 流程
  - 可用於端到端腳本（tools/sim_e2e.py）與文件化測試
- 限制：
  - 不生成實際藍牙封包與硬體回應
  - 計時/節奏僅近似模擬，非真機準確時間
  - 部分硬體-only 錯誤情境（斷包、RSSI）無法覆現

## Fake services（作用與限制）

- 作用：
  - 模擬掃描/連線/斷線、發球、訓練流程完成與狀態回報
  - 讓上層 UI/語音/指令管線可在無機器下演練
- 限制：
  - 僅回報預設成功與一般錯誤情境，不能覆蓋所有藍牙實況
  - 不保證時序精準度與併發邏輯的真實性

## 審計：logs/commands.jsonl

每行為一筆 JSON 物件（JSON Lines），建議欄位：
- timestamp：ISO8601 時間
- source：`text` | `asr`
- raw_text：原始輸入（ASR 轉文字或文字框）
- nlu:
  - matcher_rule_id：命中的規則 id（若有）
  - parser_slots：解析出的槽位（speed、area、count…）
- command：標準化後的 `{type, payload}`
- router:
  - state_before / state_after：狀態轉移
  - target_service：`device` | `training` | `simulation`
- result：`ok` | `error`
- error：錯誤訊息（若有）

### 解讀範例
```json
{"timestamp":"2025-09-23T12:34:56Z","source":"asr","raw_text":"連線發球機","nlu":{"matcher_rule_id":"connect_device","parser_slots":{}},"command":{"type":"connect","payload":{}},"router":{"state_before":"Idle","state_after":"Connecting","target_service":"device"},"result":"ok"}
```

以上範例表示：ASR 取得「連線發球機」，命中 `connect_device` 規則，路由到 Device 服務，狀態 Idle→Connecting，執行成功。



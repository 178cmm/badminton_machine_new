# 動態課程與球路匹配（ProgramRegistry）

## 資料來源

- 檔案：`training_programs.json`
- 結構（相容既有）：
  - `training_programs`: 物件，每個 key 為 program id
    - `id`: 由程式載入時補上
    - `name`: 顯示名稱
    - `difficulty`: beginner/intermediate/advanced（或自由字串）
    - `duration_minutes`: 預估時長
    - `shots`: 陣列（每個球路至少含 `description`）
    - `aliases`:（可選）自定別名陣列

另：`discription.txt`（每行一條）會被當作自由詞彙候選，利於命中。

## 比對流程

正規化（簡繁/同義詞/去尾綴/Token） → 完全比對 → Token 包含 → 模糊比對（閾值）

- 正規化：
  - `normalize_query`：大小寫/空白/全形處理（可擴充簡繁）
  - `apply_synonyms`：同義詞替換（如「平抽球」→「平抽」）
  - `strip_suffix`：去尾綴（移除「球」「訓練」「套餐」）
- 完全比對：
  - 正規化查詢在 `name_to_id` 中直接命中
- Token 包含：
  - 先檢查「個別球路程序」（由 `basic_training.shots` 自動展開）
  - 再檢查一般程序（含 `aliases` 與內建補丁）
- 模糊比對：
  - 近似度 `>= 0.85` 直接命中
  - `0.75 ~ 0.85` 回傳前 3 名候選，提示澄清

## 多候選澄清話術

- 「偵測到多個相近的訓練：A、B、C，請再指定一個。」
- 可加序號：「請說 1、2、3 中的其中一個。」

## 參數預設與覆蓋規則

- 預設：取自 program（如 `duration_minutes`、`repeat_times`、`shots`）
- 覆蓋優先序：使用者明確指定 > 程式預設

## 新增/調整球路與別名步驟

1. 編輯 `training_programs.json`
   - 在 `training_programs.<program_id>` 下新增/調整 `shots`、`aliases`
2. 更新 `discription.txt`（可選）
   - 加入常見描述詞，利於自由詞彙命中
3. 更新 `aliases.yaml`（若採用）
   - 補充同義詞對應（例：平抽 ↔ 平抽球，放網 ↔ 網前小球）
4. 重新啟動程式或觸發 `ProgramRegistry` 重新載入

### aliases.yaml 建議結構
```yaml
synonyms:
  平抽球: [平抽, 平抽擊]
  高遠球: [高遠, 後場高遠]
  吊球: [小球, 放網]
```

### 如何調整 aliases.yaml

1. **編輯配置檔案**：
   - 修改 `config/aliases.yaml` 中的 `synonyms` 區塊
   - 格式：`標準詞: [同義詞1, 同義詞2, ...]`

2. **重新載入**：
   - 重啟程式或觸發 `ProgramRegistry` 重新載入
   - 配置會在程式啟動時自動載入

3. **驗證效果**：
   - 使用語音或文字指令測試新同義詞
   - 檢查 `logs/commands.jsonl` 確認匹配結果

4. **fallback 機制**：
   - 若 `config/aliases.yaml` 不存在，會使用內建最小集合
   - 確保系統在無配置檔案時仍能正常運作

> 備註：程式內含最小 alias 補丁（不改檔）；正式別名仍建議寫入 `training_programs.json` 或 `aliases.yaml`。

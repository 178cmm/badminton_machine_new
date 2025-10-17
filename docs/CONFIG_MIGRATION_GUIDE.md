# 配置系統遷移指南

## 概述

本專案已成功將分散的訓練參數配置統一到新的配置管理系統中。新的配置系統提供了更好的可維護性、擴展性和一致性。

## 新的配置結構

```
config/
├── training/                    # 訓練相關配置
│   ├── programs.json           # 基礎訓練和課程配置（向後相容）
│   ├── basic_training.json     # 基礎訓練配置
│   ├── course_training.json    # 課程訓練配置
│   ├── warmup.json             # 熱身訓練配置
│   ├── advanced.json           # 進階訓練配置
│   └── shots/                  # 球路描述
│       └── basic_shots.json    # 基本球路描述
├── nlu/                        # 語音控制相關
│   ├── aliases.yaml           # 同義詞配置
│   └── suffixes.yaml          # 尾綴規則配置
└── system/                     # 系統配置（預留）
```

## 遷移完成的項目

### ✅ 已遷移的配置

1. **基礎訓練和課程配置**
   - 來源：`training_programs.json`
   - 目標：`config/training/programs.json`（向後相容）
   - 分離為：
     - `config/training/basic_training.json` - 基礎訓練配置
     - `config/training/course_training.json` - 課程訓練配置
   - 狀態：已遷移並分離，保持向後相容

2. **熱身訓練配置**
   - 來源：`core/parsers/warmup_parser.py` 中的硬編碼配置
   - 目標：`config/training/warmup.json`
   - 狀態：已遷移，解析器已更新

3. **進階訓練配置**
   - 來源：`adavance_training.txt`
   - 目標：`config/training/advanced.json`
   - 狀態：已遷移，解析器已更新

4. **球路描述配置**
   - 來源：`discription.txt`
   - 目標：`config/training/shots/basic_shots.json`
   - 狀態：已遷移為結構化格式

5. **NLU 配置**
   - 來源：`config/aliases.yaml`, `config/suffixes.yaml`
   - 目標：`config/nlu/aliases.yaml`, `config/nlu/suffixes.yaml`
   - 狀態：已遷移

### ✅ 新增功能

1. **統一配置管理器**
   - 檔案：`core/config/config_manager.py`
   - 功能：統一管理所有配置，支援動態載入和重新載入

2. **向後相容性**
   - 所有現有解析器都已更新，支援新配置格式
   - 如果新配置不可用，會自動回退到舊的硬編碼邏輯

## 使用方式

### 基本使用

```python
from core.config import get_config_manager

# 取得配置管理器
config_manager = get_config_manager()

# 取得基礎訓練配置
basic_configs = config_manager.get_basic_training_configs()
basic_training = config_manager.get_basic_training_config("basic_training")

# 取得課程訓練配置
course_configs = config_manager.get_course_training_configs()
course_levels = config_manager.get_all_course_levels()
level2_course = config_manager.get_course_training_config("level2_basic")

# 取得特定熱身配置
basic_warmup = config_manager.get_warmup_config("basic")

# 取得進階訓練配置
advanced_configs = config_manager.get_advanced_configs()

# 搜尋訓練配置
results = config_manager.search_training_by_name("基礎")

# 向後相容：取得舊格式配置
programs = config_manager.get_programs()
```

### 重新載入配置

```python
from core.config import reload_all_configs

# 重新載入所有配置
reload_all_configs()

# 或重新載入特定類型
config_manager = get_config_manager()
config_manager.reload_config("training")  # 只重新載入訓練配置
```

## 配置格式說明

### 統一配置格式

所有訓練配置都採用統一的 JSON 格式：

```json
{
  "metadata": {
    "version": "1.0",
    "last_updated": "2024-01-01T00:00:00Z",
    "description": "配置檔案描述"
  },
  "categories": {
    "category_id": {
      "name": "顯示名稱",
      "description": "描述",
      "type": "warmup|basic|advanced|course",
      "difficulty": "beginner|intermediate|advanced|expert",
      "duration_minutes": 30,
      "config": {
        "mode": "sequence|random",
        "interval_seconds": 3.5,
        "total_shots": 100,
        "sections": ["sec1_1", "sec2_1"],
        "shots": [
          {
            "section": "sec1_1",
            "description": "球路描述",
            "count": 5
          }
        ]
      },
      "aliases": ["別名1", "別名2"],
      "tags": ["標籤1", "標籤2"]
    }
  }
}
```

## 測試結果

配置系統已通過完整測試：

### 分離前測試結果
- ✅ 基礎訓練配置：載入 7 個套餐
- ✅ 熱身配置：載入 3 個類型
- ✅ 進階訓練配置：載入 10 個類型
- ✅ 球路描述配置：載入 16 個球路
- ✅ NLU 配置：載入 2 個檔案
- ✅ 搜尋功能：正常運作
- ✅ 解析器整合：完全相容

### 分離後測試結果
- ✅ 基礎訓練配置：載入 1 個基礎訓練類型
- ✅ 課程訓練配置：載入 6 個課程等級（第2-7級）
- ✅ 課程等級排序：按等級正確排序
- ✅ 向後相容性：舊格式配置正常載入
- ✅ 搜尋功能：支援新舊格式搜尋
- ✅ 配置結構：所有必要欄位完整
- ✅ 總訓練類型：27 個（包含所有類型）

## 向後相容性

為了確保現有程式碼不受影響，所有解析器都保持向後相容：

1. **熱身解析器**：如果新配置不可用，會回退到硬編碼邏輯
2. **進階訓練解析器**：如果新配置不可用，會回退到檔案解析
3. **基礎訓練解析器**：繼續使用現有的 `training_programs.json`

## 未來擴展

新的配置系統為未來擴展提供了良好的基礎：

1. **新增訓練類型**：只需在對應的配置檔案中新增即可
2. **系統配置**：`config/system/` 目錄預留給系統級配置
3. **動態配置**：支援配置的動態載入和重新載入
4. **配置驗證**：可以輕鬆新增配置格式驗證

## 注意事項

1. **舊檔案保留**：為了向後相容，舊的配置檔案暫時保留
2. **逐步遷移**：建議逐步將依賴舊配置的程式碼遷移到新系統
3. **配置備份**：在修改配置前建議先備份
4. **測試驗證**：修改配置後請執行測試腳本驗證

## 測試腳本

使用 `test_config_system.py` 腳本來測試配置系統：

```bash
python test_config_system.py
```

這個腳本會測試所有配置載入、解析器整合和搜尋功能。

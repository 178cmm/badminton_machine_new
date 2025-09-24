# 🏸 羽毛球發球機控制系統 - 系統架構文檔

## 📋 概述

這是一個功能完整的羽毛球發球機控制系統，採用模組化設計，支援多種控制方式和訓練模式。系統整合了圖形界面、語音控制、藍牙通訊和智能訓練功能。

## 🏗️ 系統架構圖

```
羽毛球發球機控制系統
├── 🎯 用戶界面層 (GUI Layer)
│   ├── main_gui.py              # 主界面控制器
│   ├── ui_*.py                  # 各功能模組界面
│   └── response_templates.py    # 回應模板
│
├── 🧠 核心業務層 (Core Layer)
│   ├── router.py                # 命令路由器
│   ├── commands.py              # 命令定義
│   ├── executors/               # 執行器模組
│   ├── parsers/                 # 解析器模組
│   ├── managers/                # 管理器模組
│   ├── services/                # 服務層
│   ├── nlu/                     # 自然語言理解
│   └── registry/                # 註冊中心
│
├── 🔗 通訊層 (Communication Layer)
│   ├── bluetooth.py             # 藍牙通訊
│   ├── voice_control_tts.py     # 語音控制
│   └── voice_control.py         # 語音控制(舊版)
│
├── 📁 配置與數據層 (Config & Data Layer)
│   ├── area.json                # 發球區域配置
│   ├── training_programs.json   # 訓練課程配置
│   ├── config/                  # 配置文件
│   └── rules/                   # 規則文件
│
└── 🛠️ 工具與日誌層 (Tools & Logging Layer)
    ├── core/audit/              # 審計日誌
    ├── logs/                    # 系統日誌
    └── tools/                   # 工具腳本
```

## 📂 目錄結構詳解

### 🎯 用戶界面層 (GUI Layer)

**位置**: `/gui/`

| 文件 | 功能描述 |
|------|----------|
| `main_gui.py` | 主界面控制器，整合所有UI模組 |
| `ui_connection.py` | 藍牙連接管理界面 |
| `ui_control.py` | 手動控制界面（單發/連發） |
| `ui_voice.py` | 語音控制界面 |
| `ui_training.py` | 基礎訓練界面 |
| `ui_advanced_training.py` | 進階訓練界面 |
| `ui_simulation.py` | 模擬對打界面 |
| `ui_warmup.py` | 熱身模式界面 |
| `ui_text_input.py` | 文字指令輸入界面 |
| `ui_log.py` | 日誌查看界面 |
| `ui_utils.py` | UI工具函數 |
| `response_templates.py` | 語音回應模板 |

### 🧠 核心業務層 (Core Layer)

**位置**: `/core/`

#### 1. 命令路由系統
- **`router.py`**: 統一命令路由器，處理所有用戶指令
- **`commands.py`**: 命令定義和DTO結構
- **`commands/dto.py`**: 數據傳輸對象定義

#### 2. 執行器模組 (`executors/`)
| 執行器 | 功能 |
|--------|------|
| `text_command_executor.py` | 文字命令執行 |
| `basic_training_executor.py` | 基礎訓練執行 |
| `advanced_training_executor.py` | 進階訓練執行 |
| `course_executor.py` | 課程執行 |
| `warmup_executor.py` | 熱身執行 |
| `simulation_executor.py` | 模擬對打執行 |
| `dual_machine_executor.py` | 雙發球機執行 |

#### 3. 解析器模組 (`parsers/`)
| 解析器 | 功能 |
|--------|------|
| `unified_parser.py` | 統一解析器 |
| `text_command_parser.py` | 自然語言命令解析 |
| `basic_training_parser.py` | 基礎訓練配置解析 |
| `advanced_training_parser.py` | 進階訓練配置解析 |
| `warmup_parser.py` | 熱身配置解析 |
| `simulation_parser.py` | 模擬對打配置解析 |

#### 4. 管理器模組 (`managers/`)
| 管理器 | 功能 |
|--------|------|
| `bluetooth_manager.py` | 藍牙連接管理 |
| `dual_bluetooth_manager.py` | 雙發球機藍牙管理 |
| `dual_bluetooth_thread.py` | 雙發球機線程管理 |

#### 5. 服務層 (`services/`)
| 服務 | 功能 |
|------|------|
| `device_service.py` | 設備服務 |
| `system_service.py` | 系統服務 |
| `training_service.py` | 訓練服務 |

#### 6. 自然語言理解 (`nlu/`)
| 模組 | 功能 |
|------|------|
| `matcher.py` | 規則匹配器 |
| `normalizer.py` | 文本正規化 |

#### 7. 註冊中心 (`registry/`)
| 模組 | 功能 |
|------|------|
| `program_registry.py` | 訓練課程註冊 |

#### 8. 工具模組 (`utils/`)
| 工具 | 功能 |
|------|------|
| `shot_selector.py` | 擊球選擇器 |
| `video_config.py` | 視頻配置 |

### 🔗 通訊層 (Communication Layer)

| 模組 | 功能 |
|------|------|
| `bluetooth.py` | 藍牙通訊核心，處理設備連接和數據傳輸 |
| `voice_control_tts.py` | 新版語音控制（Whisper + TTS） |
| `voice_control.py` | 舊版語音控制（Vosk） |

### 📁 配置與數據層

#### 配置文件
| 文件 | 功能 |
|------|------|
| `area.json` | 25個發球區域的參數配置 |
| `training_programs.json` | 訓練課程定義 |
| `config/aliases.yaml` | 命令別名配置 |
| `config/suffixes.yaml` | 後綴配置 |
| `rules/badminton_rules.yaml` | 語音控制規則 |

#### 數據文件
| 文件 | 功能 |
|------|------|
| `cache/reply_cache.json` | 語音回應快取 |
| `logs/commands.jsonl` | 命令執行日誌 |

## 🔄 系統流程

### 1. 啟動流程
```
main.py → BadmintonLauncherGUI → 初始化各UI模組 → 啟動事件循環
```

### 2. 命令處理流程
```
用戶輸入 → UI模組 → CommandRouter → 解析器 → 執行器 → 藍牙通訊 → 發球機
```

### 3. 語音控制流程
```
語音輸入 → Whisper API → 規則匹配 → 命令生成 → CommandRouter → 執行
```

### 4. 訓練執行流程
```
選擇訓練 → 解析配置 → 生成指令序列 → 藍牙發送 → 狀態監控 → 完成回饋
```

## 🎯 核心功能模組

### 1. 手動控制
- **單發模式**: 點擊位置按鈕直接發球
- **連發模式**: 設定球數和間隔，連續發球
- **25宮格控制**: 精準控制發球位置

### 2. 語音控制
- **Whisper API**: 高精度語音識別
- **規則匹配**: 智能指令理解
- **TTS回覆**: 即時語音反饋
- **VAD偵測**: 自動語音活動偵測

### 3. 訓練模式
- **基礎訓練**: 單一球路反覆練習
- **進階訓練**: 多球路組合訓練
- **模擬對打**: 智能對打模擬（12個等級）
- **熱身模式**: 系統化熱身訓練

### 4. 雙發球機支援
- **雙機協調**: 同時控制兩台發球機
- **位置管理**: 左/右/中央位置配置
- **同步發球**: 協調發球時機

## 🔧 技術特色

### 1. 模組化設計
- 清晰的職責分離
- 可擴展的架構
- 統一的接口設計

### 2. 異步處理
- 非阻塞UI設計
- 異步藍牙通訊
- 多線程語音處理

### 3. 智能控制
- 自然語言理解
- 規則匹配系統
- 狀態機管理

### 4. 可配置性
- JSON/YAML配置文件
- 動態規則載入
- 靈活的參數調整

## 📊 數據流

### 1. 配置數據流
```
配置文件 → 解析器 → 註冊中心 → 執行器 → 藍牙指令
```

### 2. 狀態數據流
```
發球機狀態 → 藍牙接收 → 狀態更新 → UI顯示 → 用戶反饋
```

### 3. 日誌數據流
```
操作記錄 → 審計系統 → 日誌文件 → 日誌查看器
```

## 🚀 擴展指南

### 1. 添加新的訓練模式
1. 在 `training_programs.json` 中定義新課程
2. 創建對應的解析器（如需要）
3. 創建對應的執行器
4. 在UI中添加相應界面

### 2. 添加新的語音指令
1. 在 `rules/badminton_rules.yaml` 中添加規則
2. 在 `response_templates.py` 中添加回應模板
3. 在 `CommandRouter` 中添加處理邏輯

### 3. 添加新的設備支援
1. 擴展 `bluetooth_manager.py`
2. 更新設備配置
3. 添加設備特定的指令格式

## 🔍 故障排除

### 常見問題
1. **藍牙連接失敗**: 檢查設備電源和藍牙狀態
2. **語音識別不準確**: 確認網路連接和API Key
3. **發球機無響應**: 檢查藍牙連接和設備狀態
4. **UI卡頓**: 檢查異步處理和線程管理

### 日誌查看
- 系統日誌: `logs/commands.jsonl`
- 審計日誌: `core/audit/`
- 錯誤日誌: 控制台輸出

## 📈 性能優化

### 1. 快取機制
- 語音回應快取
- 配置數據快取
- 藍牙連接快取

### 2. 異步處理
- 非阻塞UI更新
- 異步藍牙通訊
- 多線程語音處理

### 3. 資源管理
- 連接池管理
- 記憶體優化
- 線程生命週期管理

---

*本文檔提供了系統的完整架構概覽，幫助開發者理解系統結構和擴展方式。*

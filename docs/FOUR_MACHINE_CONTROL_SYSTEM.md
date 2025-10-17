# 🏸 四台發球機多套餐控制系統開發文檔

## 📋 項目概述

### 背景
經過實際場域測試與羽球專家建議，教練希望系統能夠同時控制多台發球機，每台發球機運行不同的訓練套餐，並提供靈活的控制方法，讓教練可以隨時暫停、開始任意一台發球機進行講解流程。

### 目標
- **多發球機支援**：同時控制四台發球機
- **套餐多樣化**：每台發球機可選擇不同的基礎訓練或進階訓練套餐
- **獨立控制**：教練可隨時暫停/開始任意一台發球機
- **無限發球**：設定後持續發球直到手動停止
- **教練友好**：提供全局控制功能，方便管理

## 🎯 功能需求

### 核心功能
1. **四台發球機獨立控制**
   - 每台發球機可選擇不同訓練套餐
   - 獨立設定發球間隔（1.5-5秒）
   - 支援無限發球模式
   - 實時顯示每台發球機狀態
   - **設備識別**：自動識別和分配四台發球機（基於MAC地址或設備名稱）

2. **訓練套餐支援**
   - **基礎訓練**：16種基礎球路（正手高遠球、反手高遠球等）
   - **進階訓練**：9種進階套餐
     - 近身隨機接殺
     - 前場隨機
     - 後場隨機
     - 四角隨機
     - 六角隨機
     - 殺球上網
     - 殺抽壓連貫
     - 單打防守
     - 雙打防守
   - **自定義套餐**：教練可創建和保存自定義訓練序列
   - **速度設定**：支援慢(4.0s)、正常(3.5s)、快(2.5s)、極限快(1.4s)四種速度

3. **控制功能**
   - 個別發球機：開始/暫停/停止/重置
   - 全局控制：暫停全部/開始全部/停止全部/重置全部
   - 狀態監控：實時顯示每台發球機運行狀態
   - **緊急停止**：一鍵停止所有發球機（安全功能）
   - **連接管理**：自動重連斷線的發球機

## 🏗️ 技術架構

### 系統架構圖
```
四台發球機控制系統
├── 多發球機管理器 (MultiMachineManager)
│   ├── 藍牙連接管理
│   ├── 訓練會話管理
│   └── 套餐配置管理
├── 訓練會話 (TrainingSession)
│   ├── 會話狀態管理
│   ├── 進度追蹤
│   └── 配置參數
├── 獨立訓練執行器 (IndividualTrainingWorker)
│   ├── 背景執行緒
│   ├── 暫停/恢復控制
│   └── 發球邏輯
└── GUI控制界面 (MultiMachineControlUI)
    ├── 四台發球機控制面板
    ├── 教練控制中心
    └── 狀態顯示
```

### 核心組件設計

#### 1. MultiMachineManager
```python
class MultiMachineManager:
    """四台發球機管理器"""
    
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.machines = {}  # {machine_id: DualBluetoothThread}
        self.training_sessions = {}  # {machine_id: TrainingSession}
        self.available_programs = self._load_available_programs()
        
    def _load_available_programs(self):
        """載入可用的訓練套餐"""
        return {
            "基礎訓練": {
                "id": "basic_training",
                "shots": [
                    {"section": "sec25_1", "description": "正手高遠球"},
                    {"section": "sec21_1", "description": "反手高遠球"},
                    # ... 其他基礎訓練球路
                ]
            },
            "近身隨機接殺": {
                "id": "near_body_random_kill",
                "mode": "random",
                "sections": ["sec17_1", "sec18_1", "sec19_1"]
            },
            # ... 其他進階訓練套餐
        }
```

#### 2. TrainingSession
```python
class TrainingSession:
    """單台發球機的訓練會話"""
    
    def __init__(self, machine_id: str, program_name: str, interval: float, unlimited: bool = True):
        self.machine_id = machine_id
        self.program_name = program_name
        self.interval = interval
        self.unlimited = unlimited
        self.status = "idle"  # idle, running, paused, stopped
        self.current_shot = 0
        self.total_shots = 0
        self.worker = None
        self.program_config = None
```

#### 3. IndividualTrainingWorker
```python
class IndividualTrainingWorker(QThread):
    """單台發球機的獨立訓練執行器"""
    
    sig_progress = pyqtSignal(str, int, int)  # machine_id, current, total
    sig_message = pyqtSignal(str, str)  # machine_id, message
    sig_finished = pyqtSignal(str, str)  # machine_id, status
    
    def __init__(self, machine_id: str, program_config: dict, interval: float, unlimited: bool = True):
        super().__init__()
        self.machine_id = machine_id
        self.program_config = program_config
        self.interval = interval
        self.unlimited = unlimited
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # 初始為非暫停狀態
```

## 🎨 GUI界面設計

### 四台發球機控制面板設計

#### 整體布局
```
┌─────────────────────────────────────────────────────────────┐
│  🏸 四台發球機控制中心                                        │
├─────────────────────────────────────────────────────────────┤
│ 發球機 #1  │ 發球機 #2  │ 發球機 #3  │ 發球機 #4           │
│ ┌─────────┐ │ ┌─────────┐ │ ┌─────────┐ │ ┌─────────┐       │
│ │🟢 運行中│ │ │🟡 暫停中│ │ │🔴 停止  │ │ │⚪ 待機  │       │
│ │基礎訓練 │ │ │進階訓練 │ │ │移動訓練 │ │ │未分配  │       │
│ │進度: 60%│ │ │進度: 30%│ │ │進度: 0% │ │ │進度: 0%│       │
│ │[暫停]   │ │ │[開始]   │ │ │[開始]   │ │ │[分配]  │       │
│ └─────────┘ │ └─────────┘ │ └─────────┘ │ └─────────┘       │
├─────────────────────────────────────────────────────────────┤
│ 🎯 教練控制: [暫停全部] [開始全部] [緊急停止] [重置全部]     │
└─────────────────────────────────────────────────────────────┘
```

#### 單台發球機控制面板
```python
def _create_machine_control_panel(self, machine_name: str):
    """創建單台發球機控制面板"""
    
    group = QGroupBox(machine_name)
    layout = QVBoxLayout(group)
    
    # 狀態顯示
    status_label = QLabel("⚪ 待機")
    status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
    layout.addWidget(status_label)
    
    # 套餐選擇
    program_layout = QHBoxLayout()
    program_layout.addWidget(QLabel("訓練套餐:"))
    program_combo = QComboBox()
    program_combo.addItems([
        "未選擇", "基礎訓練", "近身隨機接殺", "前場隨機", 
        "後場隨機", "四角隨機", "六角隨機", "殺球上網", "殺抽壓連貫"
    ])
    program_layout.addWidget(program_combo)
    layout.addLayout(program_layout)
    
    # 間隔設定
    interval_layout = QHBoxLayout()
    interval_layout.addWidget(QLabel("間隔(秒):"))
    interval_spin = QDoubleSpinBox()
    interval_spin.setRange(0.5, 10.0)
    interval_spin.setValue(3.0)
    interval_spin.setSingleStep(0.5)
    interval_layout.addWidget(interval_spin)
    layout.addLayout(interval_layout)
    
    # 進度條
    progress_bar = QProgressBar()
    progress_bar.setVisible(False)
    layout.addWidget(progress_bar)
    
    # 控制按鈕
    button_layout = QHBoxLayout()
    start_btn = QPushButton("▶️ 開始")
    pause_btn = QPushButton("⏸️ 暫停")
    stop_btn = QPushButton("⏹️ 停止")
    
    return group
```

### 教練控制中心
```python
def create_coach_control_center(self):
    """創建教練控制中心"""
    
    coach_control_group = QGroupBox("🎯 教練控制中心")
    coach_layout = QHBoxLayout(coach_control_group)
    
    # 全局控制按鈕
    self.pause_all_btn = QPushButton("⏸️ 暫停全部")
    self.start_all_btn = QPushButton("▶️ 開始全部")
    self.stop_all_btn = QPushButton("⏹️ 停止全部")
    self.reset_all_btn = QPushButton("🔄 重置全部")
    
    # 連接信號
    self.pause_all_btn.clicked.connect(self.pause_all_machines)
    self.start_all_btn.clicked.connect(self.start_all_machines)
    self.stop_all_btn.clicked.connect(self.stop_all_machines)
    self.reset_all_btn.clicked.connect(self.reset_all_machines)
    
    coach_layout.addWidget(self.pause_all_btn)
    coach_layout.addWidget(self.start_all_btn)
    coach_layout.addWidget(self.stop_all_btn)
    coach_layout.addWidget(self.reset_all_btn)
    
    return coach_control_group
```

## 🔧 核心控制方法

### 個別發球機控制
```python
def start_individual_training(self, machine_id: str):
    """啟動指定發球機的訓練"""
    # 1. 獲取UI設定（套餐、間隔）
    # 2. 檢查發球機連接狀態
    # 3. 創建訓練會話
    # 4. 創建訓練執行器
    # 5. 啟動訓練
    # 6. 更新UI狀態

def pause_individual_training(self, machine_id: str):
    """暫停指定發球機的訓練"""
    # 1. 暫停訓練執行器
    # 2. 更新會話狀態
    # 3. 更新UI狀態

def resume_individual_training(self, machine_id: str):
    """恢復指定發球機的訓練"""
    # 1. 恢復訓練執行器
    # 2. 更新會話狀態
    # 3. 更新UI狀態

def stop_individual_training(self, machine_id: str):
    """停止指定發球機的訓練"""
    # 1. 停止訓練執行器
    # 2. 清理會話
    # 3. 重置UI狀態
```

### 全局控制方法
```python
def pause_all_machines(self):
    """暫停所有發球機"""
    for machine_id in self.multi_machine_manager.training_sessions:
        self.pause_individual_training(machine_id)

def start_all_machines(self):
    """開始所有發球機"""
    for machine_id in self.multi_machine_manager.training_sessions:
        if self.multi_machine_manager.training_sessions[machine_id].status == "paused":
            self.resume_individual_training(machine_id)

def stop_all_machines(self):
    """停止所有發球機"""
    for machine_id in list(self.multi_machine_manager.training_sessions.keys()):
        self.stop_individual_training(machine_id)

def reset_all_machines(self):
    """重置所有發球機"""
    self.stop_all_machines()
    for i in range(1, 5):
        machine_id = f"machine_{i}"
        self._reset_machine_ui(machine_id)
```

## 📊 訓練套餐配置

### 基礎訓練套餐
```json
{
    "基礎訓練": {
        "id": "basic_training",
        "shots": [
            {"section": "sec25_1", "description": "正手高遠球"},
            {"section": "sec21_1", "description": "反手高遠球"},
            {"section": "sec25_1", "description": "正手切球"},
            {"section": "sec21_1", "description": "反手切球"},
            {"section": "sec25_1", "description": "正手殺球"},
            {"section": "sec21_1", "description": "反手殺球"},
            {"section": "sec15_1", "description": "正手平抽球"},
            {"section": "sec11_1", "description": "反手平抽球"},
            {"section": "sec5_1", "description": "正手小球"},
            {"section": "sec1_1", "description": "反手小球"},
            {"section": "sec5_1", "description": "正手挑球"},
            {"section": "sec1_1", "description": "反手挑球"},
            {"section": "sec13_1", "description": "平推球"},
            {"section": "sec20_1", "description": "正手接殺球"},
            {"section": "sec16_1", "description": "反手接殺球"},
            {"section": "sec18_1", "description": "近身接殺"}
        ]
    }
}
```

### 進階訓練套餐
```json
{
    "近身隨機接殺": {
        "id": "near_body_random_kill",
        "mode": "random",
        "sections": ["sec17_1", "sec18_1", "sec19_1"]
    },
    "前場隨機": {
        "id": "front_court_random",
        "mode": "random", 
        "sections": ["sec1_1", "sec2_1", "sec3_1", "sec4_1", "sec5_1"]
    },
    "後場隨機": {
        "id": "back_court_random",
        "mode": "random",
        "sections": ["sec21_1", "sec22_1", "sec23_1", "sec24_1", "sec25_1"]
    },
    "四角隨機": {
        "id": "four_corner_random",
        "mode": "random",
        "sections": ["sec1_1", "sec5_1", "sec21_1", "sec25_1"]
    },
    "六角隨機": {
        "id": "six_corner_random", 
        "mode": "random",
        "sections": ["sec1_1", "sec5_1", "sec11_1", "sec15_1", "sec21_1", "sec25_1"]
    },
    "殺球上網": {
        "id": "kill_and_approach",
        "mode": "sequence",
        "sections": ["sec25_1", "sec5_1", "sec21_1", "sec1_1"]
    },
    "殺抽壓連貫": {
        "id": "kill_drive_press",
        "mode": "sequence", 
        "sections": ["sec25_1", "sec15_1", "sec5_1", "sec21_1", "sec11_1", "sec1_1"]
    }
}
```

## 🚀 開發計劃

### Phase 1: 基礎架構擴展 (2-3週)
1. **擴展現有雙發球機架構**
   - 創建 `MultiMachineManager` 類別（基於 `DualBluetoothManager`）
   - 擴展藍牙連接管理支援四台設備
   - 實現設備識別和自動分配機制
   - **風險評估**：藍牙連接穩定性測試

2. **訓練會話管理**
   - 實現 `TrainingSession` 類別
   - 建立會話狀態管理機制
   - 實現會話配置和參數管理
   - **整合現有**：重用 `BasicTrainingExecutor` 和 `AdvancedTrainingExecutor`

### Phase 2: 核心功能實現 (3-4週)
1. **獨立訓練執行器**
   - 實現 `IndividualTrainingWorker` 類別
   - 支援背景執行緒和暫停/恢復功能
   - 整合現有的發球邏輯和套餐配置
   - **重點**：避免與現有系統衝突

2. **套餐配置系統**
   - 載入基礎訓練和進階訓練套餐（重用現有配置）
   - 實現套餐選擇和配置機制
   - 支援隨機和依序發球模式
   - **新增**：自定義套餐創建功能

### Phase 3: GUI界面開發 (2-3週)
1. **四台發球機控制面板**
   - 設計單台發球機控制界面
   - 實現狀態顯示和進度監控
   - 添加套餐選擇和參數設定
   - **整合**：與現有GUI架構保持一致

2. **教練控制中心**
   - 實現全局控制按鈕
   - 添加狀態總覽功能
   - 實現緊急停止和重置功能
   - **安全**：緊急停止功能優先級最高

### Phase 4: 整合測試與優化 (2-3週)
1. **功能測試**
   - 測試四台發球機同時控制
   - 驗證暫停/恢復功能
   - 測試全局控制功能
   - **壓力測試**：長時間運行穩定性

2. **用戶體驗優化**
   - 優化界面響應性
   - 添加錯誤處理和提示
   - 完善日誌記錄功能
   - **性能**：記憶體使用和CPU負載優化

### Phase 5: 部署與維護 (1週)
1. **部署準備**
   - 創建安裝和配置指南
   - 準備故障排除文檔
   - 建立用戶培訓材料

2. **維護機制**
   - 建立錯誤回報機制
   - 準備系統更新流程
   - 建立性能監控機制

## 🔍 技術要點

### 關鍵技術挑戰
1. **藍牙連接管理**：同時管理四台設備的連接狀態
2. **資源競爭**：避免多個訓練同時執行時的資源衝突
3. **UI響應性**：確保多台設備狀態更新不影響UI性能
4. **狀態同步**：保持UI狀態與實際訓練狀態的一致性
5. **設備識別**：準確識別和分配四台不同的發球機
6. **連接穩定性**：處理藍牙連接中斷和重連問題
7. **記憶體管理**：避免長時間運行時的記憶體洩漏

### 解決方案
1. **異步處理**：使用QThread和asyncio處理多個訓練任務
2. **狀態管理**：建立清晰的狀態機管理訓練會話
3. **信號機制**：使用Qt信號槽機制實現UI更新
4. **錯誤處理**：建立完善的錯誤處理和恢復機制
5. **設備池管理**：實現設備連接池和自動重連機制
6. **資源隔離**：每台發球機使用獨立的執行緒和資源
7. **監控機制**：定期檢查設備狀態和系統健康度

## 📝 使用流程

### 教練操作流程
1. **初始設定**
   - 掃描並連接四台發球機
   - 為每台發球機選擇訓練套餐
   - 設定每台發球機的發球間隔

2. **開始訓練**
   - 點擊各台發球機的「開始」按鈕
   - 或使用「開始全部」一鍵啟動所有發球機
   - 監控每台發球機的訓練狀態

3. **訓練控制**
   - 隨時暫停/恢復任意一台發球機
   - 使用全局控制按鈕管理所有發球機
   - 進行技術指導時暫停相關發球機

4. **結束訓練**
   - 使用「停止全部」停止所有發球機
   - 或個別停止每台發球機
   - 使用「重置全部」清理所有狀態

## 🎯 預期效果

### 教練體驗提升
- **靈活控制**：可隨時暫停任意發球機進行講解
- **效率提升**：同時訓練多個球員，提高場地利用率
- **個性化訓練**：每台發球機可設定不同難度的套餐
- **統一管理**：全局控制功能方便管理所有發球機

### 系統功能擴展
- **多設備支援**：從雙發球機擴展到四台發球機
- **套餐多樣化**：整合基礎訓練和進階訓練套餐
- **控制精細化**：提供個別和全局兩種控制方式
- **狀態可視化**：實時顯示每台發球機的運行狀態

## 📁 檔案結構

### 新增檔案
```
core/managers/
├── multi_machine_manager.py          # 四台發球機管理器（基於DualBluetoothManager擴展）
├── training_session.py               # 訓練會話管理
└── individual_training_worker.py     # 獨立訓練執行器

gui/
├── ui_multi_machine_control.py       # 四台發球機控制界面
└── ui_coach_control_center.py        # 教練控制中心

config/
└── multi_machine_programs.json       # 四台發球機套餐配置（擴展現有配置）

docs/
└── FOUR_MACHINE_DEPLOYMENT_GUIDE.md  # 部署和故障排除指南
```

### 修改檔案
```
gui/main_gui.py                       # 主GUI，添加四台發球機標籤頁
core/managers/dual_bluetooth_manager.py  # 擴展支援四台設備（向後兼容）
core/executors/basic_training_executor.py  # 支援多設備訓練
core/executors/advanced_training_executor.py  # 支援多設備訓練
training_programs.json                # 擴展套餐配置
```

### 重用現有檔案
```
core/parsers/basic_training_parser.py     # 基礎訓練解析器
core/parsers/advanced_training_parser.py  # 進階訓練解析器
core/services/training_service.py         # 訓練服務
commands.py                               # 發球指令
area.json                                 # 區域配置
```

## 🔧 實現細節

### 1. 藍牙連接擴展
- 基於現有 `DualBluetoothManager` 擴展為 `MultiMachineManager`
- 支援同時管理四台發球機的藍牙連接
- 實現設備識別和自動分配機制
- **向後兼容**：保持現有雙發球機功能不受影響
- **連接池**：實現設備連接池管理，提高連接穩定性

### 2. 訓練執行邏輯
- 每台發球機使用獨立的 `IndividualTrainingWorker` 執行緒
- 支援暫停/恢復/停止操作
- 實現無限發球模式
- **資源隔離**：每台設備使用獨立的資源，避免衝突
- **狀態同步**：確保UI狀態與實際訓練狀態一致

### 3. UI狀態管理
- 使用Qt信號槽機制實現UI更新
- 實時顯示每台發球機的狀態和進度
- 提供全局控制功能
- **響應性**：優化UI更新頻率，避免性能問題
- **錯誤處理**：完善的錯誤提示和恢復機制

### 4. 套餐配置管理
- 整合現有的基礎訓練和進階訓練套餐
- 支援隨機和依序兩種發球模式
- 提供靈活的套餐選擇機制
- **配置重用**：重用現有的 `training_programs.json` 配置
- **自定義套餐**：支援教練創建和保存自定義訓練序列

### 5. 系統整合策略
- **漸進式開發**：先實現基本功能，再逐步添加進階特性
- **模組化設計**：保持各模組獨立，便於測試和維護
- **配置驅動**：使用配置文件管理套餐和參數
- **日誌記錄**：完善的日誌系統，便於問題診斷

### 6. 與現有系統的整合方式
- **重用現有組件**：
  - `BasicTrainingExecutor` 和 `AdvancedTrainingExecutor` 支援多設備
  - 重用 `training_programs.json` 配置檔案
  - 整合現有的速度映射和球數解析邏輯
- **擴展現有管理器**：
  - `DualBluetoothManager` 擴展為 `MultiMachineManager`
  - 保持現有API不變，新功能作為擴展
- **UI整合**：
  - 在 `main_gui.py` 添加新的四台發球機標籤頁
  - 重用現有的UI組件和樣式
- **配置整合**：
  - 擴展 `area.json` 支援四台設備的區域配置
  - 重用現有的球種到區域映射邏輯

## ⚠️ 風險評估與建議

### 主要風險
1. **藍牙連接穩定性**
   - **風險**：四台設備同時連接可能導致藍牙頻寬不足
   - **建議**：實施連接池管理和自動重連機制
   - **測試**：在實際場域進行長時間穩定性測試

2. **系統資源消耗**
   - **風險**：四台設備同時運行可能導致系統負載過高
   - **建議**：優化執行緒管理和記憶體使用
   - **監控**：實施系統資源監控機制

3. **用戶界面複雜度**
   - **風險**：四台設備控制界面可能過於複雜
   - **建議**：設計直觀的UI，提供快速操作方式
   - **測試**：進行用戶體驗測試和改進

4. **向後兼容性**
   - **風險**：新功能可能影響現有雙發球機功能
   - **建議**：保持現有API不變，新功能作為擴展
   - **測試**：確保現有功能完全不受影響

### 實施建議
1. **分階段實施**：先實現基本功能，再逐步添加進階特性
2. **充分測試**：每個階段都要進行完整的功能測試
3. **用戶反饋**：及時收集教練使用反饋，持續改進
4. **文檔維護**：保持技術文檔和用戶手冊的更新

### 成功指標
- 四台發球機可同時穩定運行超過2小時
- 教練可在30秒內完成所有設備的初始設定
- 系統響應時間小於1秒
- 用戶滿意度達到90%以上

## 🧪 測試策略

### 單元測試
- **MultiMachineManager**：測試設備連接、會話管理、套餐配置
- **TrainingSession**：測試狀態管理、進度追蹤、參數配置
- **IndividualTrainingWorker**：測試執行緒控制、暫停/恢復、發球邏輯

### 整合測試
- **藍牙連接測試**：四台設備同時連接和斷線重連
- **訓練執行測試**：多台設備同時執行不同套餐
- **UI響應測試**：界面更新和用戶操作響應性

### 壓力測試
- **長時間運行**：連續運行8小時以上
- **高頻操作**：快速切換設備狀態和套餐
- **資源消耗**：監控記憶體和CPU使用率

### 用戶驗收測試
- **教練操作流程**：完整的訓練設定和執行流程
- **錯誤處理**：設備斷線、套餐切換等異常情況
- **性能驗證**：響應時間和穩定性驗證

---

**文檔版本**: v1.1  
**創建日期**: 2024年12月  
**最後更新**: 2024年12月  
**負責人**: 開發團隊  

此文檔將作為四台發球機多套餐控制系統開發的指導文件，請開發團隊按照此文檔進行系統性開發。

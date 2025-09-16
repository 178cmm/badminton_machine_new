# 🏸 羽球發球機語音控制系統

## 📋 系統概述

這是一個完整的羽球發球機語音控制系統，支援：
- **語音識別**：使用 Whisper API（高準確度）
- **智能規則匹配**：快速回應羽球訓練指令
- **LLM 對話**：支援自然語言對話
- **語音合成**：TTS 語音回覆
- **預載入優化**：智能快取和預測

## 🚀 快速開始

### 1. 環境設定

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# macOS 系統依賴（建議）
brew install ffmpeg portaudio
```

### 2. 環境變數設定

```bash
# 設定 OpenAI API Key
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 執行系統

```bash
# 基本使用（推薦）
python main.py

# 多回合對話模式
python main.py --continuous

# 低延遲模式
python main.py --low-latency
```

## 📁 檔案結構

```
badminton_tts_package/
├── main.py                 # 主要程式（Whisper API 版本）
├── requirements.txt       # Python 依賴
├── README.md             # 使用說明
├── rules/                # 規則配置檔案
│   ├── badminton_rules.yaml      # 主要羽球規則
│   ├── badminton_rules_en.yaml   # 英文規則
│   └── rules.yaml               # 通用規則
└── cache/                # 快取檔案
    └── reply_cache.json         # 回覆快取
```

## 🎯 主要功能

### 語音控制指令

系統支援以下羽球訓練指令：

- **基本控制**：開始、停止、暫停
- **速度調整**：快速、慢速、中速
- **角度控制**：左邊、右邊、中間
- **高度調整**：提高、降低
- **訓練模式**：前場、後場、殺球、吊球
- **球路練習**：直線、斜線、正手、反手

### 進階功能

- **模式切換**：控制模式 vs 思考模式
- **預載入系統**：智能預測和快取
- **低延遲優化**：快速響應
- **多回合對話**：支援上下文記憶

## ⚙️ 進階選項

### 基本參數

```bash
# 指定語音
python main.py -v nova

# 調整語速
python main.py --speed 1.5

# 指定輸出檔案
python main.py -o reply.mp3

# 使用自訂規則檔
python main.py --rules rules/custom_rules.yaml
```

### 優化參數

```bash
# 啟用預載入系統
python main.py --preload --preload-common

# 低延遲模式
python main.py --low-latency --no-progress

# 超快速模式
python main.py --ultra-fast

# 並行處理（實驗性）
python main.py --parallel
```

### 快取管理

```bash
# 查看快取統計
python main.py --cache-stats

# 清空快取
python main.py --clear-cache

# 立即儲存快取
python main.py --save-cache
```

## 🔧 故障排除

### 常見問題

1. **錄音問題**
   ```bash
   # 列出可用音訊裝置
   python -c "import sounddevice as sd; print(sd.query_devices())"
   
   # 指定音訊裝置
   python main.py --sd-device 1
   ```

2. **依賴問題**
   ```bash
   # 重新安裝依賴
   pip install -r requirements.txt --force-reinstall
   ```

3. **API 問題**
   ```bash
   # 檢查 API Key
   echo $OPENAI_API_KEY
   ```

### 日誌檔案

系統會自動產生 `badminton_tts.log` 日誌檔案，可用於除錯。

## 📞 支援

如有問題，請檢查：
1. Python 版本（建議 3.8+）
2. 依賴套件是否正確安裝
3. 環境變數是否設定
4. 音訊裝置是否正常

## 🎉 開始使用

現在您可以開始使用羽球發球機語音控制系統了！

```bash
python main.py
```

說出「開始訓練」或「啟動發球機」來開始您的羽球訓練！

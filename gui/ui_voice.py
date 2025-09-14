import asyncio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, QHBoxLayout, QCheckBox
import sounddevice as sd


def create_voice_tab(self):
    """建立語音控制獨立頁面。"""
    voice_widget = QWidget()
    layout = QVBoxLayout(voice_widget)

    # 標題與說明
    title = QLabel("🎙️ 語音控制")
    layout.addWidget(title)

    instruction_label = QLabel(
        "請用下列格式發出指令：\n"
        "- 正手高遠球 20 顆 間隔 3 秒\n"
        "- 反手切球 10 顆\n"
        "- 平推球 間隔 5 秒\n"
        "（如果未指定，預設顆數 10、間隔 5 秒）"
    )
    instruction_label.setStyleSheet("color: #ffffff; font-size: 14px;")
    layout.addWidget(instruction_label)

    # 裝置選擇區
    device_row = QHBoxLayout()
    device_row.addWidget(QLabel("輸入裝置:"))
    self.voice_device_combo = QComboBox()
    try:
        devices = sd.query_devices()
        default_in = sd.default.device[0] if hasattr(sd, 'default') and sd.default and sd.default.device else None
        for idx, d in enumerate(devices):
            name = d.get('name', f'Device {idx}')
            if d.get('max_input_channels', 0) > 0:
                label = f"{idx}: {name}"
                self.voice_device_combo.addItem(label, idx)
                if default_in is not None and idx == default_in:
                    self.voice_device_combo.setCurrentIndex(self.voice_device_combo.count()-1)
    except Exception:
        pass
    device_row.addWidget(self.voice_device_combo)
    layout.addLayout(device_row)

    # 對話/日誌視窗（顯示辨識與系統訊息）
    layout.addWidget(QLabel("對話"))
    self.voice_chat_log = QTextEdit()
    self.voice_chat_log.setReadOnly(True)
    self.voice_chat_log.setMinimumHeight(220)
    layout.addWidget(self.voice_chat_log)

    # 控制按鈕
    self.voice_start_button = QPushButton("啟動語音控制")
    self.voice_stop_button = QPushButton("停止語音控制")
    self.voice_use_grammar = QCheckBox("啟用限制詞彙 (Grammar)")
    self.voice_use_grammar.setChecked(False)
    layout.addWidget(self.voice_start_button)
    layout.addWidget(self.voice_use_grammar)
    layout.addWidget(self.voice_stop_button)

    # 綁定事件（非阻塞）
    def _start_voice():
        device_idx = self.voice_device_combo.currentData()
        # 重新建立 VoiceControl 以套用裝置
        try:
            if hasattr(self, 'voice_control') and self.voice_control is not None:
                # 停舊的
                asyncio.create_task(self.voice_control.stop())
        except Exception:
            pass
        from voice_control import VoiceControl
        self.voice_control = VoiceControl(
            self,
            model_path=getattr(self, 'voice_model_path', 'models/vosk-model-small-cn-0.22'),
            input_device=device_idx,
            use_grammar=self.voice_use_grammar.isChecked(),
        )
        asyncio.create_task(self.voice_control.start())

    self.voice_start_button.clicked.connect(_start_voice)
    self.voice_stop_button.clicked.connect(lambda: asyncio.create_task(self.stop_voice_control()))

    # 加入標籤頁
    self.tab_widget.addTab(voice_widget, "語音控制")


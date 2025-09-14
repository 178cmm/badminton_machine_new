import asyncio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox, QHBoxLayout, QProgressBar, QTextEdit
from PyQt5.QtCore import Qt


def create_warmup_tab(self):
    """建立熱身標籤頁，提供基礎/進階/全面熱身三種模式。"""
    warmup_widget = QWidget()
    layout = QVBoxLayout(warmup_widget)

    # 控制區塊
    control_group = QGroupBox("熱身設定")
    control_layout = QVBoxLayout(control_group)

    # 速度/間隔
    speed_row = QHBoxLayout()
    speed_row.addWidget(QLabel("發球間隔/速度:"))
    self.warmup_speed_combo = QComboBox()
    self.warmup_speed_combo.addItems(["慢", "正常", "快", "極限快"])
    speed_row.addWidget(self.warmup_speed_combo)
    speed_row.addStretch()
    control_layout.addLayout(speed_row)

    # 熱身按鈕列
    buttons_row = QHBoxLayout()
    basic_btn = QPushButton("基礎熱身")
    adv_btn = QPushButton("進階熱身")
    full_btn = QPushButton("全面熱身")
    stop_btn = QPushButton("停止熱身")
    stop_btn.setStyleSheet("""
        QPushButton { background-color: #E53935; color: white; }
        QPushButton:hover { background-color: #D32F2F; }
        QPushButton:disabled { background-color: #8E8E8E; color: #ECECEC; }
    """)

    basic_btn.clicked.connect(lambda checked=False: self.start_warmup("basic"))
    adv_btn.clicked.connect(lambda checked=False: self.start_warmup("advanced"))
    full_btn.clicked.connect(lambda checked=False: self.start_warmup("comprehensive"))
    stop_btn.clicked.connect(self.stop_training)

    buttons_row.addWidget(basic_btn)
    buttons_row.addWidget(adv_btn)
    buttons_row.addWidget(full_btn)
    buttons_row.addWidget(stop_btn)
    control_layout.addLayout(buttons_row)

    layout.addWidget(control_group)

    # 熱身說明區
    info_group = QGroupBox("熱身說明")
    info_layout = QVBoxLayout(info_group)

    # 類型選擇（用於切換描述）
    self._warmup_types_order = ["basic", "advanced", "comprehensive"]
    self.warmup_info_combo = QComboBox()
    self.warmup_info_combo.addItems(["簡單熱身", "進階熱身", "全面熱身"])  # 對應 _warmup_types_order
    self.warmup_info_combo.currentIndexChanged.connect(lambda idx: self.update_warmup_description())
    info_layout.addWidget(self.warmup_info_combo)

    self.warmup_description = QTextEdit()
    self.warmup_description.setReadOnly(True)
    self.warmup_description.setMinimumHeight(160)
    info_layout.addWidget(self.warmup_description)

    layout.addWidget(info_group)

    # 進度條（獨立於課程訓練頁）
    self.warmup_progress_bar = QProgressBar()
    self.warmup_progress_bar.setVisible(False)
    layout.addWidget(self.warmup_progress_bar)

    layout.addStretch()
    self.tab_widget.addTab(warmup_widget, "熱身套餐")

    # 初始化描述
    self.update_warmup_description("basic")


def _map_speed_to_interval(text: str) -> float:
    if text == "慢":
        return 4
    if text == "正常":
        return 3.5
    if text == "快":
        return 2.5
    if text == "極限快":
        return 1.4
    return 3.5


def start_warmup(self, warmup_type: str):
    """依所選熱身類型啟動熱身流程。"""
    if not self.bluetooth_thread:
        self.log_message("請先掃描設備")
        return
    if not self.bluetooth_thread.is_connected:
        self.log_message("請先連接發球機")
        return

    speed_text = self.warmup_speed_combo.currentText() if hasattr(self, 'warmup_speed_combo') else "正常"
    interval = _map_speed_to_interval(speed_text)

    # 依需求建立精確序列
    if warmup_type == "basic":
        sequence = ["sec23_2"] * 5 + ["sec3_1"] * 5
        title = "基礎熱身"
    elif warmup_type == "advanced":
        sequence = ["sec13_1"] * 5 + ["sec23_2"] * 5 + ["sec3_1"] * 5
        title = "進階熱身"
    elif warmup_type == "comprehensive":
        alternating = []
        for _ in range(5):
            alternating.extend(["sec23_2", "sec3_1"])  # 交錯各發5顆（共10顆）
        sequence = ["sec13_1"] * 5 + ["sec23_2"] * 5 + ["sec3_1"] * 5 + alternating
        title = "全面熱身"
    else:
        self.log_message("未知的熱身類型")
        return

    # 同步顯示描述
    self.update_warmup_description(warmup_type)

    # 啟動異步任務
    if hasattr(self, 'training_task') and self.training_task and not self.training_task.done():
        self.log_message("已有訓練進行中，請先停止後再開始新熱身")
        return

    self.log_message(f"開始 {title} | 速度:{speed_text} | 間隔:{interval}s | 總顆數:{len(sequence)}")
    self.warmup_progress_bar.setMaximum(len(sequence))
    self.warmup_progress_bar.setValue(0)
    self.warmup_progress_bar.setVisible(True)
    self.stop_flag = False

    self.training_task = asyncio.create_task(self._execute_warmup(sequence, interval, title))


async def _execute_warmup(self, sequence, interval: float, title: str):
    """依序列以固定間隔發送，並回饋進度。"""
    try:
        sent = 0
        for section in sequence:
            if self.stop_flag:
                raise asyncio.CancelledError()
            result = await self.bluetooth_thread.send_shot(section)
            if not result:
                self.log_message("發送失敗，已中止熱身")
                break
            sent += 1
            self.log_message(f"{title}: 已發送 {section} 第 {sent} 顆")
            if hasattr(self, 'warmup_progress_bar'):
                self.warmup_progress_bar.setValue(sent)
            await asyncio.sleep(interval)
        else:
            self.log_message(f"{title} 完成！")
    except asyncio.CancelledError:
        self.log_message(f"{title} 已停止")
    except Exception as e:
        self.log_message(f"{title} 執行失敗: {e}")
    finally:
        if hasattr(self, 'warmup_progress_bar'):
            self.warmup_progress_bar.setVisible(False)
        # 保持與既有停止流程一致
        self.training_task = None


# ==== 描述顯示 ====
_WARMUP_INFO = {
    "basic": {
        "title": "簡單熱身",
        "contents": [
            "高遠球 30 顆",
            "小球 30 顆",
        ],
        "purpose": "上手球熱身，供初學者培養擊球空間感使用",
        "time": "3 分鐘",
    },
    "advanced": {
        "title": "進階熱身",
        "contents": [
            "平球 20 顆",
            "高遠球 20 顆",
            "切球 20 顆",
            "殺球 20 顆",
            "小球 20 顆",
        ],
        "purpose": "綜合熱身，活動各方向肌肉與關節",
        "time": "5 分鐘",
    },
    "comprehensive": {
        "title": "全面熱身",
        "contents": [
            "平球 20 顆",
            "高遠球 20 顆",
            "切球 20 顆",
            "殺球 20 顆",
            "小球 20 顆",
            "前後跑動 20 顆",
        ],
        "purpose": "全方位熱身，活動全身肌肉與關節",
        "time": "8 分鐘",
    },
}


def _format_warmup_info_text(warmup_type: str) -> str:
    info = _WARMUP_INFO.get(warmup_type)
    if not info:
        return ""
    lines = [f"{info['title']}"]
    lines.append("訓練內容")
    for item in info["contents"]:
        lines.append(item)
    lines.append("訓練目的")
    lines.append(info["purpose"])
    lines.append(f"預估時間  :   {info['time']}")
    return "\n".join(lines)


def update_warmup_description(self, warmup_type: str = None):
    """更新描述視窗。可帶入 warmup_type 直接切換。"""
    if not hasattr(self, 'warmup_description'):
        return
    # 若有指定類型，先同步選單
    if warmup_type:
        if not hasattr(self, '_warmup_types_order'):
            self._warmup_types_order = ["basic", "advanced", "comprehensive"]
        try:
            idx = self._warmup_types_order.index(warmup_type)
            if hasattr(self, 'warmup_info_combo'):
                self.warmup_info_combo.blockSignals(True)
                self.warmup_info_combo.setCurrentIndex(idx)
                self.warmup_info_combo.blockSignals(False)
        except ValueError:
            pass
    # 從選單取得類型
    if hasattr(self, 'warmup_info_combo') and hasattr(self, '_warmup_types_order'):
        current_idx = self.warmup_info_combo.currentIndex()
        warmup_type = self._warmup_types_order[current_idx]
    text = _format_warmup_info_text(warmup_type)
    self.warmup_description.setText(text)

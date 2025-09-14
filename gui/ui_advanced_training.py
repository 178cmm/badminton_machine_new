import asyncio
import random
from typing import Dict, List, Tuple
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox, QHBoxLayout, QProgressBar, QTextEdit


ADVANCE_FILE_PATH = "adavance_training.txt"


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


def _parse_advance_specs(file_path: str) -> Dict[str, Dict]:
    """
    解析 adavance_training.txt，輸出每個課程的設定：
    {
        title: {
            "mode": "random" | "sequence",
            "sections": ["secX_1", ...],
            "description": "完整描述文字"
        }
    }
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]
    except Exception:
        return {}

    blocks: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)

    result: Dict[str, Dict] = {}
    for blk in blocks:
        if not blk:
            continue
        title = blk[0].strip()
        description = "\n".join(blk).strip()

        mode = None
        sections: List[str] = []
        # 尋找「發球點位」下的模式行
        for idx, line in enumerate(blk):
            if line.strip() == "發球點位" and idx + 1 < len(blk):
                next_line = blk[idx + 1].strip()
                if next_line.startswith("隨機發"):
                    mode = "random"
                elif next_line.startswith("依序發"):
                    mode = "sequence"
                # 擷取所有 sec 標記
                tokens = next_line.split()
                sections = [tok for tok in tokens if tok.startswith("sec")]
                break

        if title and mode and sections:
            result[title] = {
                "mode": mode,
                "sections": sections,
                "description": description,
            }

    return result


def create_advanced_training_tab(self):
    """建立進階訓練標籤頁，依據檔案內容提供隨機/依序的發球模式。"""
    self._advanced_specs = _parse_advance_specs(ADVANCE_FILE_PATH)

    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 控制區塊
    control_group = QGroupBox("進階訓練設定")
    control_layout = QVBoxLayout(control_group)

    # 項目選擇
    row1 = QHBoxLayout()
    row1.addWidget(QLabel("選擇進階訓練項目:"))
    self.advanced_combo = QComboBox()
    titles = list(self._advanced_specs.keys())
    if titles:
        self.advanced_combo.addItems(titles)
    # 切換時更新說明
    self.advanced_combo.currentIndexChanged.connect(lambda idx: _update_advanced_description(self))
    row1.addWidget(self.advanced_combo)
    row1.addStretch()
    control_layout.addLayout(row1)

    # 速度/間隔
    row2 = QHBoxLayout()
    row2.addWidget(QLabel("發球間隔/速度:"))
    self.advanced_speed_combo = QComboBox()
    self.advanced_speed_combo.addItems(["慢", "正常", "快", "極限快"])
    row2.addWidget(self.advanced_speed_combo)

    # 球數
    row2.addWidget(QLabel("發球數量:"))
    self.advanced_ball_count_combo = QComboBox()
    self.advanced_ball_count_combo.addItems(["10顆", "20顆", "30顆"]) 
    row2.addWidget(self.advanced_ball_count_combo)
    row2.addStretch()
    control_layout.addLayout(row2)

    # 按鈕列
    row3 = QHBoxLayout()
    start_btn = QPushButton("開始進階訓練")
    stop_btn = QPushButton("停止")
    stop_btn.setStyleSheet(
        """
        QPushButton { background-color: #E53935; color: white; }
        QPushButton:hover { background-color: #D32F2F; }
        QPushButton:disabled { background-color: #8E8E8E; color: #ECECEC; }
        """
    )
    start_btn.clicked.connect(self.start_advanced_training)
    stop_btn.clicked.connect(self.stop_training)
    row3.addWidget(start_btn)
    row3.addWidget(stop_btn)
    control_layout.addLayout(row3)

    layout.addWidget(control_group)

    # 說明區
    info_group = QGroupBox("訓練說明")
    info_layout = QVBoxLayout(info_group)
    self.advanced_description = QTextEdit()
    self.advanced_description.setReadOnly(True)
    self.advanced_description.setMinimumHeight(220)
    info_layout.addWidget(self.advanced_description)
    layout.addWidget(info_group)

    # 進度條
    self.advanced_progress_bar = QProgressBar()
    self.advanced_progress_bar.setVisible(False)
    layout.addWidget(self.advanced_progress_bar)

    layout.addStretch()
    self.tab_widget.addTab(widget, "進階訓練")

    # 初始化描述
    _update_advanced_description(self)


def _update_advanced_description(self):
    if not hasattr(self, 'advanced_combo') or not hasattr(self, '_advanced_specs'):
        return
    title = self.advanced_combo.currentText() if self.advanced_combo.count() else ""
    spec = self._advanced_specs.get(title, {})
    if not spec:
        self.advanced_description.setText("尚未載入進階訓練內容")
        return
    mode_label = "隨機發" if spec.get("mode") == "random" else "依序發"
    sections = " ".join(spec.get("sections", []))
    desc = spec.get("description", title)
    extra = f"\n\n模式: {mode_label}\n發球點位: {sections}"
    self.advanced_description.setText(desc + extra)


def _parse_ball_count(text: str) -> int:
    if text == "10顆":
        return 10
    if text == "20顆":
        return 20
    if text == "30顆":
        return 30
    return 10


def start_advanced_training(self):
    """開始目前所選進階訓練。"""
    if not hasattr(self, '_advanced_specs') or not self._advanced_specs:
        self.log_message("進階訓練內容尚未載入或檔案解析失敗")
        return
    if not self.bluetooth_thread:
        self.log_message("請先掃描設備")
        return
    if not self.bluetooth_thread.is_connected:
        self.log_message("請先連接發球機")
        return
    if hasattr(self, 'training_task') and self.training_task and not self.training_task.done():
        self.log_message("已有訓練進行中，請先停止後再開始")
        return

    title = self.advanced_combo.currentText()
    spec = self._advanced_specs.get(title)
    if not spec:
        self.log_message("未找到所選進階訓練內容")
        return

    speed_text = self.advanced_speed_combo.currentText() if hasattr(self, 'advanced_speed_combo') else "正常"
    interval = _map_speed_to_interval(speed_text)
    balls = _parse_ball_count(self.advanced_ball_count_combo.currentText() if hasattr(self, 'advanced_ball_count_combo') else "10顆")

    self.stop_flag = False
    self.advanced_progress_bar.setMaximum(balls)
    self.advanced_progress_bar.setValue(0)
    self.advanced_progress_bar.setVisible(True)

    self.log_message(f"開始進階訓練: {title} | 模式:{'隨機' if spec['mode']=='random' else '依序'} | 速度:{speed_text} | 間隔:{interval}s | 總顆數:{balls}")
    self.training_task = asyncio.create_task(_execute_advanced_training(self, title, spec, interval, balls))


async def _execute_advanced_training(self, title: str, spec: Dict, interval: float, total_balls: int):
    try:
        sent = 0
        sections = spec.get("sections", [])
        mode = spec.get("mode")
        while sent < total_balls:
            if self.stop_flag:
                raise asyncio.CancelledError()
            if mode == "sequence":
                section = sections[sent % len(sections)]
            else:
                section = random.choice(sections)
            result = await self.bluetooth_thread.send_shot(section)
            if not result:
                self.log_message("發送失敗，已中止進階訓練")
                break
            sent += 1
            self.log_message(f"{title}: 已發送 {section} 第 {sent} 顆")
            if hasattr(self, 'advanced_progress_bar'):
                self.advanced_progress_bar.setValue(sent)
            await asyncio.sleep(interval)
        else:
            self.log_message(f"{title} 完成！")
    except asyncio.CancelledError:
        self.log_message(f"{title} 已停止")
    except Exception as e:
        self.log_message(f"{title} 執行失敗: {e}")
    finally:
        if hasattr(self, 'advanced_progress_bar'):
            self.advanced_progress_bar.setVisible(False)
        self.training_task = None


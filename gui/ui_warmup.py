from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox, QHBoxLayout, QProgressBar, QTextEdit
from PyQt5.QtCore import Qt
import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.executors import create_warmup_executor
from core.parsers import format_warmup_info_text


def create_warmup_tab(self):
    """建立熱身標籤頁，提供基礎/進階/全面熱身三種模式。"""
    warmup_widget = QWidget()
    layout = QVBoxLayout(warmup_widget)
    
    # 創建滾動區域以防止內容溢出
    from PyQt5.QtWidgets import QScrollArea
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)

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
    
    # 建立熱身執行器
    self.warmup_executor = create_warmup_executor(self)

    buttons_row.addWidget(basic_btn)
    buttons_row.addWidget(adv_btn)
    buttons_row.addWidget(full_btn)
    buttons_row.addWidget(stop_btn)
    control_layout.addLayout(buttons_row)

    scroll_layout.addWidget(control_group)

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
    self.warmup_description.setMinimumHeight(120)  # 減少最小高度以適應小螢幕
    info_layout.addWidget(self.warmup_description)

    scroll_layout.addWidget(info_group)

    # 進度條（獨立於課程訓練頁）
    self.warmup_progress_bar = QProgressBar()
    self.warmup_progress_bar.setVisible(False)
    scroll_layout.addWidget(self.warmup_progress_bar)

    scroll_layout.addStretch()
    
    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    layout.addWidget(scroll_area)
    self.tab_widget.addTab(warmup_widget, "熱身套餐")

    # 初始化描述
    self.update_warmup_description("basic")


def start_warmup(self, warmup_type: str):
    """依所選熱身類型啟動熱身流程（UI 層面的處理）"""
    if not hasattr(self, 'warmup_executor'):
        self.warmup_executor = create_warmup_executor(self)
    
    # 使用熱身執行器處理熱身邏輯
    self.warmup_executor.start_warmup(warmup_type)


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
    
    # 使用執行器中的格式化函數
    text = format_warmup_info_text(warmup_type)
    self.warmup_description.setText(text)

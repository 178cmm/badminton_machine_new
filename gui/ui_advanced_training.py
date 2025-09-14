from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox, QHBoxLayout, QProgressBar, QTextEdit
from PyQt5.QtCore import Qt
import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parsers import load_advanced_training_specs, get_advanced_training_titles, get_advanced_training_description
from core.executors import create_advanced_training_executor


def create_advanced_training_tab(self):
    """建立進階訓練標籤頁，依據檔案內容提供隨機/依序的發球模式。"""
    # 載入進階訓練規格
    self._advanced_specs = load_advanced_training_specs()

    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # 創建滾動區域以防止內容溢出
    from PyQt5.QtWidgets import QScrollArea
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)

    # 控制區塊
    control_group = QGroupBox("進階訓練設定")
    control_layout = QVBoxLayout(control_group)

    # 項目選擇
    row1 = QHBoxLayout()
    row1.addWidget(QLabel("選擇進階訓練項目:"))
    self.advanced_combo = QComboBox()
    titles = get_advanced_training_titles(self._advanced_specs)
    if titles:
        self.advanced_combo.addItems(titles)
    # 切換時更新說明
    self.advanced_combo.currentIndexChanged.connect(lambda idx: update_advanced_description(self))
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
    
    # 建立進階訓練執行器
    self.advanced_training_executor = create_advanced_training_executor(self)
    row3.addWidget(start_btn)
    row3.addWidget(stop_btn)
    control_layout.addLayout(row3)

    scroll_layout.addWidget(control_group)

    # 說明區
    info_group = QGroupBox("訓練說明")
    info_layout = QVBoxLayout(info_group)
    self.advanced_description = QTextEdit()
    self.advanced_description.setReadOnly(True)
    self.advanced_description.setMinimumHeight(150)  # 減少最小高度以適應小螢幕
    info_layout.addWidget(self.advanced_description)
    scroll_layout.addWidget(info_group)

    # 進度條
    self.advanced_progress_bar = QProgressBar()
    self.advanced_progress_bar.setVisible(False)
    scroll_layout.addWidget(self.advanced_progress_bar)

    scroll_layout.addStretch()
    
    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    layout.addWidget(scroll_area)
    self.tab_widget.addTab(widget, "進階訓練")

    # 初始化描述
    update_advanced_description(self)


def update_advanced_description(self):
    """更新進階訓練描述"""
    if not hasattr(self, 'advanced_combo') or not hasattr(self, '_advanced_specs'):
        return
    title = self.advanced_combo.currentText() if self.advanced_combo.count() else ""
    description = get_advanced_training_description(title, self._advanced_specs)
    self.advanced_description.setText(description)


def start_advanced_training(self):
    """開始目前所選進階訓練（UI 層面的處理）"""
    title = self.advanced_combo.currentText()
    spec = self._advanced_specs.get(title)
    if not spec:
        self.log_message("未找到所選進階訓練內容")
        return

    speed_text = self.advanced_speed_combo.currentText() if hasattr(self, 'advanced_speed_combo') else "正常"
    ball_count_text = self.advanced_ball_count_combo.currentText() if hasattr(self, 'advanced_ball_count_combo') else "10顆"
    
    # 使用執行器處理訓練邏輯
    self.advanced_training_executor.start_advanced_training(title, spec, speed_text, ball_count_text)


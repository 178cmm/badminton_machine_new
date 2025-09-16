from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox, QTabWidget, QProgressBar, QDialog, QGridLayout, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt
import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.executors import create_course_executor

def create_training_tab(self):
    """創建訓練標籤頁"""
    training_widget = QWidget()
    layout = QVBoxLayout(training_widget)
    
    # 創建滾動區域以防止內容溢出
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    
    # 訓練套餐選擇組
    program_group = QGroupBox("課程訓練選擇")
    program_layout = QVBoxLayout(program_group)
    
    # 等級選擇
    self.level_combo = QComboBox()
    self.level_combo.addItems(["2", "3", "4", "5", "6", "7"])
    self.level_combo.currentTextChanged.connect(self.update_program_list)
    program_layout.addWidget(QLabel("等級: "))
    program_layout.addWidget(self.level_combo)
    
    # 套餐選擇
    self.program_combo = QComboBox()
    self.program_combo.currentIndexChanged.connect(self.update_program_description)
    program_layout.addWidget(QLabel("訓練套餐: "))
    program_layout.addWidget(self.program_combo)
    
    # 套餐描述
    self.program_description = QTextEdit()
    self.program_description.setMaximumHeight(150)  # 增加高度讓文字更容易閱讀
    self.program_description.setMinimumHeight(100)  # 增加最小高度
    self.program_description.setReadOnly(True)
    self.program_description.setStyleSheet("""
        QTextEdit {
            font-size: 13px;
            line-height: 1.4;
            padding: 8px;
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 4px;
        }
    """)
    program_layout.addWidget(QLabel("套餐描述: "))
    program_layout.addWidget(self.program_description)
    
    # 發球間隔（速度）選擇
    self.speed_combo = QComboBox()
    self.speed_combo.addItems(["慢", "正常", "快", "極限快"])
    program_layout.addWidget(QLabel("發球間隔/速度: "))
    program_layout.addWidget(self.speed_combo)
    
    # 發球數量選擇
    self.ball_count_combo = QComboBox()
    self.ball_count_combo.addItems(["10顆", "20顆", "30顆"])
    program_layout.addWidget(QLabel("發球數量: "))
    program_layout.addWidget(self.ball_count_combo)
    
    # 在課程頁面新增停止鍵（與開始鍵相鄰）
    # 停止鍵（使用純文字，避免某些系統字型不支援 emoji 導致顯示為奇怪圖示）
    self.stop_training_button = QPushButton("停止訓練")
    self.stop_training_button.setToolTip("立即停止當前訓練")
    self.stop_training_button.setMinimumHeight(44)
    self.stop_training_button.setCursor(Qt.PointingHandCursor)
    self.stop_training_button.setStyleSheet("""
        QPushButton { background-color: #E53935; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 14px; font-weight: bold; }
        QPushButton:hover { background-color: #D32F2F; }
        QPushButton:disabled { background-color: #8E8E8E; color: #ECECEC; }
    """)
    self.stop_training_button.clicked.connect(self.stop_training)
    self.stop_training_button.setEnabled(False)
    program_layout.addWidget(self.stop_training_button)
    
    # 開始訓練按鈕
    self.start_training_button = QPushButton("🚀 開始訓練")
     # 直接呼叫 asyncSlot 包裝的 start_training
    self.start_training_button.clicked.connect(lambda checked=False: self.start_training())
    self.start_training_button.setEnabled(False)
    program_layout.addWidget(self.start_training_button)
    
    # 建立課程執行器
    self.course_executor = create_course_executor(self)
    
    # 進度條
    self.progress_bar = QProgressBar()
    self.progress_bar.setVisible(False)
    program_layout.addWidget(self.progress_bar)
    
    scroll_layout.addWidget(program_group)
    scroll_layout.addStretch()
    
    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    layout.addWidget(scroll_area)
    
    self.tab_widget.addTab(training_widget, "課程訓練")


def execute_training_command(self, command, programs_data):
    """根據用戶的指令，執行相應的訓練操作（UI 層面的處理）"""
    if not hasattr(self, 'course_executor'):
        self.course_executor = create_course_executor(self)
    
    # 使用課程執行器處理命令邏輯
    self.course_executor.execute_training_command(command, programs_data)
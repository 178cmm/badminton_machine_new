import asyncio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox, QTabWidget, QProgressBar, QDialog, QGridLayout, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt
from commands import read_data_from_json
import time
from qasync import asyncSlot

AREA_FILE_PATH = "area.json"

def create_training_tab(self):
    """創建訓練標籤頁"""
    training_widget = QWidget()
    layout = QVBoxLayout(training_widget)
    
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
    self.program_description.setMaximumHeight(100)
    self.program_description.setReadOnly(True)
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
    
    # 移除重複的停止鍵建立（避免覆蓋之前的按鈕與狀態）
    
    # 進度條
    self.progress_bar = QProgressBar()
    self.progress_bar.setVisible(False)
    program_layout.addWidget(self.progress_bar)
    
    layout.addWidget(program_group)
    layout.addStretch()
    
    self.tab_widget.addTab(training_widget, "課程訓練")


def execute_training_command(self, command, programs_data):
    """
    根據用戶的指令，執行相應的訓練操作。
    
    :param command: 用戶的指令，包含訓練類型、項目、數量、間隔等信息
    :param programs_data: 訓練套餐的數據
    """
    if command['type'] == 'specific_shot':
        # 處理特定項目的練習
        shot_name = command['shot_name']
        count = command['count']
        interval = command['interval']
        self.practice_specific_shot(shot_name, count, interval)
    elif command['type'] == 'stop':
        # 停止目前訓練
        self.stop_training()
    elif command['type'] == 'scan':
        # 掃描發球機
        try:
            asyncio.create_task(self.scan_devices())
        except Exception:
            pass
    elif command['type'] == 'connect':
        # 連接當前選擇的發球機
        try:
            asyncio.create_task(self.connect_device())
        except Exception:
            pass
    elif command['type'] == 'disconnect':
        # 斷開當前連線
        try:
            asyncio.create_task(self.disconnect_device())
        except Exception:
            pass
    elif command['type'] == 'start_warmup':
        # 熱身（可選速度）
        warmup_type = command.get('warmup_type', 'basic')
        speed = command.get('speed')
        try:
            if speed and hasattr(self, 'warmup_speed_combo'):
                # 僅在選項存在時設定
                if speed in ["慢", "正常", "快", "極限快"]:
                    self.warmup_speed_combo.setCurrentText(speed)
            self.start_warmup(warmup_type)
        except Exception:
            pass
    elif command['type'] == 'start_advanced':
        # 進階訓練（可選標題/速度/球數）
        title = command.get('title')
        speed = command.get('speed')
        balls = command.get('balls')
        try:
            if title and hasattr(self, 'advanced_combo') and self.advanced_combo.count():
                # 設定對應標題
                for idx in range(self.advanced_combo.count()):
                    if self.advanced_combo.itemText(idx) == title:
                        self.advanced_combo.setCurrentIndex(idx)
                        break
            if speed and hasattr(self, 'advanced_speed_combo'):
                if speed in ["慢", "正常", "快", "極限快"]:
                    self.advanced_speed_combo.setCurrentText(speed)
            if balls and hasattr(self, 'advanced_ball_count_combo'):
                label = f"{int(balls)}顆" if int(balls) in [10, 20, 30] else None
                if label:
                    self.advanced_ball_count_combo.setCurrentText(label)
            self.start_advanced_training()
        except Exception:
            pass
    elif command['type'] == 'start_current':
        # 直接開始目前所選（可選速度/球數）
        speed = command.get('speed')
        balls = command.get('balls')
        try:
            if speed and hasattr(self, 'speed_combo'):
                if speed in ["慢", "正常", "快", "極限快"]:
                    self.speed_combo.setCurrentText(speed)
            if balls and hasattr(self, 'ball_count_combo'):
                label = f"{int(balls)}顆" if int(balls) in [10, 20, 30] else None
                if label:
                    self.ball_count_combo.setCurrentText(label)
            # asyncSlot 可直接呼叫，內部會建立 task 或返回協程
            self.start_training()
        except Exception:
            pass
    elif command['type'] == 'level_program':
        # 處理特定等級的套餐練習
        level = command['level']
        self.practice_level_programs(level, programs_data)
    else:
        print("未知的指令類型")
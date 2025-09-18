"""
手動控制界面模組

提供手動控制發球機的功能，包括：
- 單發模式：點擊位置按鈕直接發球
- 連發模式：設定球數和間隔，連續發球
- 25宮格發球區域控制
"""

import asyncio
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, 
                             QGroupBox, QTabWidget, QProgressBar, QDialog, QGridLayout, QHBoxLayout, 
                             QScrollArea, QSpinBox, QCheckBox, QSlider, QButtonGroup, QRadioButton)
from PyQt5.QtCore import Qt, QTimer
from commands import read_data_from_json
import time
from qasync import asyncSlot

def create_manual_tab(self):
    """創建手動控制標籤頁"""
    manual_widget = QWidget()
    layout = QVBoxLayout(manual_widget)
    
    # 創建滾動區域
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    
    # 連發模式控制組 - AI風格（移到最上面）
    burst_group = QGroupBox("🚀 BURST MODE • 智能連發系統")
    burst_group.setStyleSheet("""
        QGroupBox::title {
            color: #ff3366;
            font-weight: bold;
            font-size: 14px;
        }
    """)
    burst_layout = QVBoxLayout(burst_group)
    
    # 模式選擇
    mode_selection_layout = QHBoxLayout()
    mode_selection_layout.addWidget(QLabel("🎯 發球模式:"))
    
    # 創建模式選擇按鈕組
    self.shot_mode_group = QButtonGroup()
    self.single_mode_radio = QRadioButton("單發模式")
    self.burst_mode_radio = QRadioButton("連發模式")
    self.single_mode_radio.setChecked(True)  # 預設單發模式
    
    self.shot_mode_group.addButton(self.single_mode_radio, 0)
    self.shot_mode_group.addButton(self.burst_mode_radio, 1)
    
    # 設置單選按鈕樣式
    self.single_mode_radio.setStyleSheet("""
        QRadioButton {
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        QRadioButton::indicator:unchecked {
            border: 2px solid #4CAF50;
            border-radius: 8px;
            background-color: transparent;
        }
        QRadioButton::indicator:checked {
            border: 2px solid #4CAF50;
            border-radius: 8px;
            background-color: #4CAF50;
        }
    """)
    
    self.burst_mode_radio.setStyleSheet("""
        QRadioButton {
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        QRadioButton::indicator:unchecked {
            border: 2px solid #ff3366;
            border-radius: 8px;
            background-color: transparent;
        }
        QRadioButton::indicator:checked {
            border: 2px solid #ff3366;
            border-radius: 8px;
            background-color: #ff3366;
        }
    """)
    
    mode_selection_layout.addWidget(self.single_mode_radio)
    mode_selection_layout.addWidget(self.burst_mode_radio)
    mode_selection_layout.addStretch()
    burst_layout.addLayout(mode_selection_layout)
    
    # 連發設定區域
    burst_settings_layout = QHBoxLayout()
    
    # 球數設定
    ball_count_layout = QVBoxLayout()
    ball_count_layout.addWidget(QLabel("發球數量:"))
    self.ball_count_spinbox = QSpinBox()
    self.ball_count_spinbox.setRange(1, 50)
    self.ball_count_spinbox.setValue(5)
    self.ball_count_spinbox.setStyleSheet("""
        QSpinBox {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid #ff3366;
            border-radius: 5px;
            padding: 5px;
            font-size: 14px;
            font-weight: bold;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #ff3366;
            border: none;
            width: 20px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #ff5588;
        }
    """)
    ball_count_layout.addWidget(self.ball_count_spinbox)
    burst_settings_layout.addLayout(ball_count_layout)
    
    # 間隔設定
    interval_layout = QVBoxLayout()
    interval_layout.addWidget(QLabel("發球間隔 (秒):"))
    self.interval_spinbox = QSpinBox()
    self.interval_spinbox.setRange(1, 10)
    self.interval_spinbox.setValue(2)
    self.interval_spinbox.setSuffix(" 秒")
    self.interval_spinbox.setStyleSheet("""
        QSpinBox {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid #ff3366;
            border-radius: 5px;
            padding: 5px;
            font-size: 14px;
            font-weight: bold;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #ff3366;
            border: none;
            width: 20px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #ff5588;
        }
    """)
    interval_layout.addWidget(self.interval_spinbox)
    burst_settings_layout.addLayout(interval_layout)
    
    burst_layout.addLayout(burst_settings_layout)
    
    # 連發狀態顯示
    self.burst_status_label = QLabel("💤 等待連發指令...")
    self.burst_status_label.setStyleSheet("""
        QLabel {
            color: #4ecdc4;
            font-weight: bold;
            font-size: 12px;
            padding: 8px;
            background-color: rgba(78, 205, 196, 0.1);
            border: 1px solid #4ecdc4;
            border-radius: 5px;
        }
    """)
    burst_layout.addWidget(self.burst_status_label)
    
    # 連發控制按鈕
    burst_control_layout = QHBoxLayout()
    
    self.start_burst_btn = QPushButton("🚀 開始連發")
    self.start_burst_btn.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ff3366, stop:1 #ff5588);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ff5588, stop:1 #ff77aa);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #cc1144, stop:1 #aa1144);
        }
    """)
    self.start_burst_btn.clicked.connect(self.start_burst_mode)
    
    self.stop_burst_btn = QPushButton("⏹️ 停止連發")
    self.stop_burst_btn.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #666666, stop:1 #888888);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #888888, stop:1 #aaaaaa);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #444444, stop:1 #666666);
        }
    """)
    self.stop_burst_btn.clicked.connect(self.stop_burst_mode)
    self.stop_burst_btn.setEnabled(False)
    
    burst_control_layout.addWidget(self.start_burst_btn)
    burst_control_layout.addWidget(self.stop_burst_btn)
    burst_control_layout.addStretch()
    
    burst_layout.addLayout(burst_control_layout)
    
    # 連發說明
    burst_info = QLabel("💡 連發模式：選擇位置後設定球數和間隔，點擊「開始連發」即可連續發球")
    burst_info.setStyleSheet("color: #ffcc00; font-size: 11px;")
    burst_info.setWordWrap(True)
    burst_layout.addWidget(burst_info)
    
    scroll_layout.addWidget(burst_group)
    
    # 前場區域組 - AI風格
    front_group = QGroupBox("🎯 FRONT ZONE • 前場精準區域 (sec1-sec5)")
    front_group.setStyleSheet("""
        QGroupBox::title {
            color: #00ff88;
            font-weight: bold;
            font-size: 14px;
        }
    """)
    front_layout = QGridLayout(front_group)
    self.create_area_buttons(front_layout, 1, 5)
    scroll_layout.addWidget(front_group)
    
    # 中場區域組 - AI風格
    middle_group = QGroupBox("⚡ MID ZONE • 中場戰術區域 (sec6-sec15)")
    middle_group.setStyleSheet("""
        QGroupBox::title {
            color: #ffaa00;
            font-weight: bold;
            font-size: 14px;
        }
    """)
    middle_layout = QGridLayout(middle_group)
    self.create_area_buttons(middle_layout, 6, 15)
    scroll_layout.addWidget(middle_group)
    
    # 後場區域組 - AI風格
    back_group = QGroupBox("🔥 BACK ZONE • 後場威力區域 (sec16-sec25)")
    back_group.setStyleSheet("""
        QGroupBox::title {
            color: #ff6644;
            font-weight: bold;
            font-size: 14px;
        }
    """)
    back_layout = QGridLayout(back_group)
    self.create_area_buttons(back_layout, 16, 25)
    scroll_layout.addWidget(back_group)
    
    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    layout.addWidget(scroll_area)
    
    # 初始化連發模式相關變數
    self.burst_mode_active = False
    self.burst_task = None
    self.current_burst_section = None
    
    self.tab_widget.addTab(manual_widget, "手動控制")


def handle_shot_button_click(self, section):
    """處理發球按鈕點擊事件，根據模式決定單發或連發"""
    if hasattr(self, 'burst_mode_radio') and self.burst_mode_radio.isChecked():
        # 連發模式：設定目標位置並準備連發
        self.current_burst_section = section
        self.update_burst_status(f"🎯 已選擇位置: {section}，準備連發")
        self.log_message(f"連發模式：已選擇位置 {section}，請設定球數和間隔後開始連發")
    else:
        # 單發模式：直接發球
        self.send_single_shot(section)


def start_burst_mode(self):
    """開始連發模式"""
    if not self.current_burst_section:
        self.log_message("請先選擇發球位置")
        return
    
    if not self.bluetooth_thread:
        self.log_message("請先掃描設備")
        return

    if not self.bluetooth_thread.is_connected:
        self.log_message("請先連接發球機")
        return
    
    ball_count = self.ball_count_spinbox.value()
    interval = self.interval_spinbox.value()
    
    self.burst_mode_active = True
    self.start_burst_btn.setEnabled(False)
    self.stop_burst_btn.setEnabled(True)
    
    self.update_burst_status(f"🚀 連發中：{self.current_burst_section} ({ball_count}球，間隔{interval}秒)")
    self.log_message(f"開始連發：{self.current_burst_section}，{ball_count}球，間隔{interval}秒")
    
    # 創建連發任務
    self.burst_task = asyncio.create_task(self.execute_burst_sequence())


def stop_burst_mode(self):
    """停止連發模式"""
    self.burst_mode_active = False
    
    if self.burst_task and not self.burst_task.done():
        self.burst_task.cancel()
    
    self.start_burst_btn.setEnabled(True)
    self.stop_burst_btn.setEnabled(False)
    
    self.update_burst_status("⏹️ 連發已停止")
    self.log_message("連發模式已停止")


async def execute_burst_sequence(self):
    """執行連發序列"""
    try:
        ball_count = self.ball_count_spinbox.value()
        interval = self.interval_spinbox.value()
        section = self.current_burst_section
        
        for i in range(ball_count):
            if not self.burst_mode_active:
                break
                
            # 發送單球
            await self.bluetooth_thread.send_shot(section)
            
            # 更新狀態
            remaining = ball_count - i - 1
            self.update_burst_status(f"🚀 連發中：{section} ({i+1}/{ball_count}，剩餘{remaining}球)")
            self.log_message(f"連發進度：{section} 第{i+1}球")
            
            # 如果不是最後一球，等待間隔時間
            if i < ball_count - 1 and self.burst_mode_active:
                await asyncio.sleep(interval)
        
        if self.burst_mode_active:
            self.update_burst_status("✅ 連發完成")
            self.log_message(f"連發完成：{section}，共發送{ball_count}球")
        
    except asyncio.CancelledError:
        self.log_message("連發被取消")
    except Exception as e:
        self.log_message(f"連發過程中發生錯誤：{e}")
    finally:
        # 重置狀態
        self.burst_mode_active = False
        self.start_burst_btn.setEnabled(True)
        self.stop_burst_btn.setEnabled(False)
        if not self.burst_mode_active:
            self.update_burst_status("💤 等待連發指令...")


def update_burst_status(self, status):
    """更新連發狀態顯示"""
    if hasattr(self, 'burst_status_label'):
        self.burst_status_label.setText(status)
        
        # 根據狀態更新顏色
        if "連發中" in status:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #ff3366;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(255, 51, 102, 0.1);
                    border: 1px solid #ff3366;
                    border-radius: 5px;
                }
            """)
        elif "完成" in status:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #51cf66;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(81, 207, 102, 0.1);
                    border: 1px solid #51cf66;
                    border-radius: 5px;
                }
            """)
        elif "停止" in status:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #ff6b6b;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(255, 107, 107, 0.1);
                    border: 1px solid #ff6b6b;
                    border-radius: 5px;
                }
            """)
        else:
            self.burst_status_label.setStyleSheet("""
                QLabel {
                    color: #4ecdc4;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 8px;
                    background-color: rgba(78, 205, 196, 0.1);
                    border: 1px solid #4ecdc4;
                    border-radius: 5px;
                }
            """)


def log_message(self, message):
    """記錄訊息到日誌"""
    if hasattr(self, 'log_message'):
        self.log_message(message)
    else:
        print(f"[手動控制] {message}")
        
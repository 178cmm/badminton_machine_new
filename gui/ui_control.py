import asyncio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox, QTabWidget, QProgressBar, QDialog, QGridLayout, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt
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
    
    # 快速發球組 - AI風格
    quick_group = QGroupBox("⚡ QUICK LAUNCH • AI 快速發球系統")
    quick_group.setStyleSheet("""
        QGroupBox::title {
            color: #00d4ff;
            font-weight: bold;
            font-size: 14px;
        }
    """)
    quick_layout = QHBoxLayout(quick_group)
    
    # AI風格常用球路按鈕
    common_shots = [
        ("🎯 前場精準", "sec1_1"), ("🔄 前場變化", "sec6_1"),
        ("⚡ 中場快攻", "sec11_1"), ("🌀 中場旋轉", "sec16_1"),
        ("🔥 後場威力", "sec21_1"), ("💫 後場變線", "sec25_1")
    ]
    
    for name, section in common_shots:
        button = QPushButton(name)
        button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff6b35, stop:0.5 #f7931e, stop:1 #ff6b35);
                color: #ffffff;
                padding: 12px 16px;
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #ff6b35;
                border-radius: 10px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff8c5a, stop:0.5 #ffaa44, stop:1 #ff8c5a);
                border: 2px solid #ff8c5a;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #cc5529, stop:1 #aa4422);
            }
        """)
        button.clicked.connect(lambda checked, s=section: self.send_single_shot(s))
        quick_layout.addWidget(button)
    
    scroll_layout.addWidget(quick_group)
    
    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    layout.addWidget(scroll_area)
    
    self.tab_widget.addTab(manual_widget, "手動控制")
        
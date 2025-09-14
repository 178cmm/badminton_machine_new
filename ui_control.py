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
    
    # 前場區域組
    front_group = QGroupBox("🏸 前場區域 (sec1-sec5)")
    front_layout = QGridLayout(front_group)
    self.create_area_buttons(front_layout, 1, 5)
    scroll_layout.addWidget(front_group)
    
    # 中場區域組
    middle_group = QGroupBox("🎯 中場區域 (sec6-sec15)")
    middle_layout = QGridLayout(middle_group)
    self.create_area_buttons(middle_layout, 6, 15)
    scroll_layout.addWidget(middle_group)
    
    # 後場區域組
    back_group = QGroupBox("🏁 後場區域 (sec16-sec25)")
    back_layout = QGridLayout(back_group)
    self.create_area_buttons(back_layout, 16, 25)
    scroll_layout.addWidget(back_group)
    
    # 快速發球組
    quick_group = QGroupBox("⚡ 快速發球")
    quick_layout = QHBoxLayout(quick_group)
    
    # 常用球路按鈕
    common_shots = [
        ("前場正手", "sec1_1"), ("前場反手", "sec6_1"),
        ("中場正手", "sec11_1"), ("中場反手", "sec16_1"),
        ("後場正手", "sec21_1"), ("後場反手", "sec25_1")
    ]
    
    for name, section in common_shots:
        button = QPushButton(name)
        button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 15px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
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
        
"""
自定義發球控制頁面模組

提供使用者直接輸入4個參數控制發球機，並可以排列自定義球序的功能。
包括：
- 4個參數的直接輸入控制 (速度、水平角度、垂直角度、高度)
- 球序建構器，讓使用者可以排列自定義的球
- 依序發球功能
- 球序保存和載入功能
"""

import time
import json
import os
from typing import Dict, List, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QGroupBox, QProgressBar, QGridLayout, QTextEdit, QSizePolicy, QScrollArea,
    QSpinBox, QFormLayout, QSlider, QListWidget, QListWidgetItem, QMessageBox,
    QInputDialog, QFileDialog, QSplitter, QFrame, QLineEdit, QDoubleSpinBox
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QThread
from PyQt5.QtGui import QFont, QIcon, QPixmap

# 導入現有的發球指令創建函數
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commands import create_shot_command


class ParameterControlWidget(QWidget):
    """參數控制組件 - 用於直接輸入4個發球參數"""
    
    # 信號定義
    sig_parameters_changed = pyqtSignal(dict)  # 參數變更信號
    sig_test_shot = pyqtSignal(dict)  # 測試發球信號
    
    def __init__(self):
        super().__init__()
        self.current_params = {
            'speed': 2,
            'horizontal_angle': 0,
            'vertical_angle': 50,
            'height': 0
        }
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)  # 減少間距
        layout.setContentsMargins(20, 10, 20, 20)  # 減少上邊距
        
        # 標題
        title_label = QLabel("🎯 發球參數控制")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #4CAF50; margin-bottom: 5px;")  # 減少下邊距
        layout.addWidget(title_label)
        
        # 參數控制組
        params_group = QGroupBox("發球參數設定")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: rgba(76, 175, 80, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #4CAF50;
                font-size: 14px;
            }
        """)
        params_layout = QGridLayout(params_group)
        params_layout.setSpacing(15)
        
        # 參數控制元件
        self.param_controls = {}
        
        # 速度控制
        speed_label = QLabel("速度 (1-10):")
        speed_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 10)
        self.speed_spin.setValue(2)
        self.speed_spin.setStyleSheet(self._get_spinbox_style("#FF5722"))
        self.param_controls['speed'] = self.speed_spin
        params_layout.addWidget(speed_label, 0, 0)
        params_layout.addWidget(self.speed_spin, 0, 1)
        
        # 水平角度控制
        h_angle_label = QLabel("水平角度 (0-60):")
        h_angle_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        self.h_angle_spin = QSpinBox()
        self.h_angle_spin.setRange(0, 60)
        self.h_angle_spin.setValue(0)
        self.h_angle_spin.setStyleSheet(self._get_spinbox_style("#2196F3"))
        self.param_controls['horizontal_angle'] = self.h_angle_spin
        params_layout.addWidget(h_angle_label, 0, 2)
        params_layout.addWidget(self.h_angle_spin, 0, 3)
        
        # 垂直角度控制
        v_angle_label = QLabel("垂直角度 (0-60):")
        v_angle_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        self.v_angle_spin = QSpinBox()
        self.v_angle_spin.setRange(0, 60)
        self.v_angle_spin.setValue(50)
        self.v_angle_spin.setStyleSheet(self._get_spinbox_style("#9C27B0"))
        self.param_controls['vertical_angle'] = self.v_angle_spin
        params_layout.addWidget(v_angle_label, 1, 0)
        params_layout.addWidget(self.v_angle_spin, 1, 1)
        
        # 高度控制 (注意：實際配置中所有區域的高度都是0)
        height_label = QLabel("高度 (0-10) [註: 實際配置中均為0]:")
        height_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        self.height_spin = QSpinBox()
        self.height_spin.setRange(0, 10)
        self.height_spin.setValue(0)
        self.height_spin.setStyleSheet(self._get_spinbox_style("#FF9800"))
        self.param_controls['height'] = self.height_spin
        params_layout.addWidget(height_label, 1, 2)
        params_layout.addWidget(self.height_spin, 1, 3)
        
        layout.addWidget(params_group)
        
        # 參數預覽區域 - 創建一個群組框來顯示當前設定的參數
        preview_group = QGroupBox("參數預覽")  # 創建群組框，標題為"參數預覽"
        
        # 設定群組框的樣式 - 使用 CSS 語法來美化外觀
        preview_group.setStyleSheet("""
            QGroupBox {  /* 群組框主體的樣式 */
                font-weight: bold;  /* 字體加粗 */
                border: 2px solid #FF9800;  /* 邊框：2像素寬，橙色 (#FF9800) */
                border-radius: 10px;  /* 圓角：10像素，讓邊框變成圓角矩形 */
                margin-top: 1ex;  /* 上邊距：1個字符高度 */
                padding-top: 15px;  /* 內邊距頂部：15像素 */
                background-color: rgba(255, 152, 0, 0.1);  /* 背景色：橙色半透明 (10% 透明度) */
            }
            QGroupBox::title {  /* 群組框標題的樣式 */
                subcontrol-origin: margin;  /* 標題位置基準：邊距 */
                left: 15px;  /* 標題左邊距：15像素 */
                padding: 0 8px 0 8px;  /* 標題內邊距：上下0，左右8像素 */
                color: #FF9800;  /* 標題文字顏色：橙色 */
                font-size: 14px;  /* 標題字體大小：14像素 */
            }
        """)
        
        # 創建垂直布局管理器，用於排列群組框內的元件
        preview_layout = QVBoxLayout(preview_group)
        
        # 創建預覽標籤 - 顯示當前設定的參數值
        self.preview_label = QLabel("速度: 2, 水平: 0°, 垂直: 50°, 高度: 0")  # 初始顯示的參數文字
        
        # 設定預覽標籤的樣式
        self.preview_label.setStyleSheet("""
            color: #ffffff;  /* 文字顏色：白色 */
            font-size: 14px;  /* 字體大小：14像素 */
            font-weight: bold;  /* 字體加粗 */
            padding: 10px;  /* 內邊距：10像素 */
            background-color: rgba(255, 255, 255, 0.1);  /* 背景色：白色半透明 (10% 透明度) */
            border-radius: 5px;  /* 圓角：5像素 */
        """)
        
        # 將預覽標籤添加到預覽區域的布局中
        preview_layout.addWidget(self.preview_label)
        
        # 將整個預覽群組添加到主布局中
        layout.addWidget(preview_group)
        
        # 測試發球按鈕 - 用於測試當前設定的參數
        test_btn = QPushButton("🎯 測試發球")  # 創建按鈕，文字包含emoji和中文
        
        # 設定按鈕的樣式 - 使用漸層背景和互動效果
        test_btn.setStyleSheet("""
            QPushButton {  /* 按鈕正常狀態的樣式 */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,  /* 線性漸層：從左到右 */
                    stop:0 #4CAF50, stop:1 #45a049);  /* 漸層顏色：從綠色到深綠色 */
                color: #ffffff;  /* 文字顏色：白色 */
                border: none;  /* 無邊框 */
                padding: 10px 20px;  /* 內邊距：上下12像素，左右20像素 */
                border-radius: 8px;  /* 圓角：8像素 */
                font-weight: bold;  /* 字體加粗 */
                font-size: 14px;  /* 字體大小：14像素 */
                min-height: 10px;  /* 最小高度：20像素 */
            }
            QPushButton:hover {  /* 滑鼠懸停時的樣式 */
                opacity: 0.8;  /* 透明度：80%，產生變暗效果 */
            }
            QPushButton:pressed {  /* 按鈕被按下時的樣式 */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,  /* 反向漸層 */
                    stop:0 #45a049, stop:1 #4CAF50);  /* 顏色順序相反，產生按壓效果 */
            }
        """)
        
        # 將測試按鈕添加到主布局中
        layout.addWidget(test_btn)
        
        # 添加到球序按鈕 - 將當前參數添加到球序列表中
        add_to_sequence_btn = QPushButton("➕ 添加到球序")  # 創建按鈕，使用加號emoji
        
        # 設定按鈕樣式 - 使用藍色漸層主題
        add_to_sequence_btn.setStyleSheet("""
            QPushButton {  /* 按鈕正常狀態的樣式 */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,  /* 線性漸層：從左到右 */
                    stop:0 #2196F3, stop:1 #1976D2);  /* 漸層顏色：從藍色到深藍色 */
                color: #ffffff;  /* 文字顏色：白色 */
                border: none;  /* 無邊框 */
                padding: 12px 20px;  /* 內邊距：上下12像素，左右20像素 */
                border-radius: 8px;  /* 圓角：8像素 */
                font-weight: bold;  /* 字體加粗 */
                font-size: 14px;  /* 字體大小：14像素 */
                min-height: 20px;  /* 最小高度：20像素 */
            }
            QPushButton:hover {  /* 滑鼠懸停時的樣式 */
                opacity: 0.8;  /* 透明度：80%，產生變暗效果 */
            }
            QPushButton:pressed {  /* 按鈕被按下時的樣式 */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,  /* 反向漸層 */
                    stop:0 #1976D2, stop:1 #2196F3);  /* 顏色順序相反，產生按壓效果 */
            }
        """)
        
        # 將添加到球序按鈕添加到主布局中
        layout.addWidget(add_to_sequence_btn)
        
        # 儲存按鈕引用 - 將按鈕保存為實例變數，以便後續連接信號和事件處理
        self.test_btn = test_btn  # 保存測試發球按鈕的引用
        self.add_to_sequence_btn = add_to_sequence_btn  # 保存添加到球序按鈕的引用
    
    def _get_spinbox_style(self, color: str) -> str:
        """獲取 SpinBox 樣式"""
        return f"""
            QSpinBox {{
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: 2px solid {color};
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
                font-weight: bold;
                min-width: 60px;
            }}
            QSpinBox:focus {{
                border-color: {color};
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {color};
                border: none;
                width: 20px;
                border-radius: 3px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {color};
                opacity: 0.8;
            }}
        """
    
    def _setup_connections(self):
        """設置信號連接"""
        # 參數變更連接
        for param_name, control in self.param_controls.items():
            control.valueChanged.connect(self._on_parameter_changed)
        
        # 按鈕連接
        self.test_btn.clicked.connect(self._on_test_shot)
        self.add_to_sequence_btn.clicked.connect(self._on_add_to_sequence)
    
    def _on_parameter_changed(self):
        """參數變更處理"""
        self.current_params = {
            'speed': self.speed_spin.value(),
            'horizontal_angle': self.h_angle_spin.value(),
            'vertical_angle': self.v_angle_spin.value(),
            'height': self.height_spin.value()
        }
        
        # 更新預覽
        self.preview_label.setText(
            f"速度: {self.current_params['speed']}, "
            f"水平: {self.current_params['horizontal_angle']}°, "
            f"垂直: {self.current_params['vertical_angle']}°, "
            f"高度: {self.current_params['height']}"
        )
        
        # 發送參數變更信號
        self.sig_parameters_changed.emit(self.current_params)
    
    def _on_test_shot(self):
        """測試發球"""
        self.sig_test_shot.emit(self.current_params)
    
    def _on_add_to_sequence(self):
        """添加到球序"""
        # 這個信號將由父組件處理
        pass
    
    def get_current_parameters(self) -> Dict[str, int]:
        """獲取當前參數"""
        return self.current_params.copy()
    
    def set_parameters(self, params: Dict[str, int]):
        """設置參數"""
        for param_name, value in params.items():
            if param_name in self.param_controls:
                self.param_controls[param_name].setValue(value)


class ShotSequenceBuilder(QWidget):
    """球序建構器 - 用於排列自定義的球"""
    
    # 信號定義
    sig_sequence_changed = pyqtSignal(list)  # 球序變更信號
    sig_play_sequence = pyqtSignal(list)  # 播放球序信號
    
    def __init__(self):
        super().__init__()
        self.shot_sequence = []  # 球序列表
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)  # 減少間距
        layout.setContentsMargins(20, 10, 20, 20)  # 減少上邊距
        
        # 標題
        title_label = QLabel("📋 球序建構器")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #9C27B0; margin-bottom: 5px;")  # 減少下邊距
        layout.addWidget(title_label)
        
        # 球序列表
        sequence_group = QGroupBox("球序列表")
        sequence_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #9C27B0;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: rgba(156, 39, 176, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #9C27B0;
                font-size: 14px;
            }
        """)
        sequence_layout = QVBoxLayout(sequence_group)
        
        # 創建滾動區域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: rgba(156, 39, 176, 0.3);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(156, 39, 176, 0.6);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(156, 39, 176, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: rgba(156, 39, 176, 0.3);
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(156, 39, 176, 0.6);
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(156, 39, 176, 0.8);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # 創建球序列表
        self.shot_list = QListWidget()
        self.shot_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid #9C27B0;
                border-radius: 5px;
                color: #ffffff;
                font-size: 12px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(156, 39, 176, 0.3);
                border-radius: 3px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: rgba(156, 39, 176, 0.5);
            }
            QListWidget::item:hover {
                background-color: rgba(156, 39, 176, 0.3);
            }
        """)
        # 設置球序列表為可拉伸
        self.shot_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 將球序列表設置為滾動區域的內容
        scroll_area.setWidget(self.shot_list)
        
        # 將滾動區域添加到佈局中
        sequence_layout.addWidget(scroll_area)
        
        # 將球序列表組設置為可拉伸，讓它佔據更多垂直空間
        sequence_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(sequence_group, 1)  # 拉伸比例設為1
        
        # 球序控制按鈕
        control_layout = QHBoxLayout()
        
        # 上移按鈕
        move_up_btn = QPushButton("⬆️ 上移")
        move_up_btn.setStyleSheet(self._get_button_style("#FF9800"))
        control_layout.addWidget(move_up_btn)
        
        # 下移按鈕
        move_down_btn = QPushButton("⬇️ 下移")
        move_down_btn.setStyleSheet(self._get_button_style("#FF9800"))
        control_layout.addWidget(move_down_btn)
        
        # 刪除按鈕
        delete_btn = QPushButton("🗑️ 刪除")
        delete_btn.setStyleSheet(self._get_button_style("#F44336"))
        control_layout.addWidget(delete_btn)
        
        # 清空按鈕
        clear_btn = QPushButton("🧹 清空")
        clear_btn.setStyleSheet(self._get_button_style("#F44336"))
        control_layout.addWidget(clear_btn)
        
        layout.addLayout(control_layout)
        
        # 球序操作按鈕
        operation_layout = QHBoxLayout()
        
        # 保存球序按鈕
        save_btn = QPushButton("💾 保存球序")
        save_btn.setStyleSheet(self._get_button_style("#4CAF50"))
        operation_layout.addWidget(save_btn)
        
        # 載入球序按鈕
        load_btn = QPushButton("📁 載入球序")
        load_btn.setStyleSheet(self._get_button_style("#2196F3"))
        operation_layout.addWidget(load_btn)
        
        layout.addLayout(operation_layout)
        
        # 儲存按鈕引用
        self.move_up_btn = move_up_btn
        self.move_down_btn = move_down_btn
        self.delete_btn = delete_btn
        self.clear_btn = clear_btn
        self.save_btn = save_btn
        self.load_btn = load_btn
    
    def _get_button_style(self, color: str) -> str:
        """獲取按鈕樣式"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: #ffffff;
                border: none;
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
                min-height: 18px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:pressed {{
                background-color: {color};
                opacity: 0.6;
            }}
        """
    
    def _setup_connections(self):
        """設置信號連接"""
        self.move_up_btn.clicked.connect(self._move_up)
        self.move_down_btn.clicked.connect(self._move_down)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.clear_btn.clicked.connect(self._clear_sequence)
        self.save_btn.clicked.connect(self._save_sequence)
        self.load_btn.clicked.connect(self._load_sequence)
    
    def add_shot(self, params: Dict[str, int], name: str = None):
        """添加球到序列"""
        if name is None:
            name = f"球 {len(self.shot_sequence) + 1}"
        
        shot_data = {
            'name': name,
            'params': params.copy(),
            'id': len(self.shot_sequence)
        }
        
        self.shot_sequence.append(shot_data)
        self._update_shot_list()
        self.sig_sequence_changed.emit(self.shot_sequence)
    
    def _update_shot_list(self):
        """更新球序列表顯示"""
        self.shot_list.clear()
        for i, shot in enumerate(self.shot_sequence):
            params = shot['params']
            item_text = f"{i+1}. {shot['name']} - 速度:{params['speed']}, 水平:{params['horizontal_angle']}°, 垂直:{params['vertical_angle']}°, 高度:{params['height']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, shot)
            self.shot_list.addItem(item)
    
    def _move_up(self):
        """上移選中的球"""
        current_row = self.shot_list.currentRow()
        if current_row > 0:
            # 交換列表中的位置
            self.shot_sequence[current_row], self.shot_sequence[current_row - 1] = \
                self.shot_sequence[current_row - 1], self.shot_sequence[current_row]
            self._update_shot_list()
            self.shot_list.setCurrentRow(current_row - 1)
            self.sig_sequence_changed.emit(self.shot_sequence)
    
    def _move_down(self):
        """下移選中的球"""
        current_row = self.shot_list.currentRow()
        if current_row < len(self.shot_sequence) - 1:
            # 交換列表中的位置
            self.shot_sequence[current_row], self.shot_sequence[current_row + 1] = \
                self.shot_sequence[current_row + 1], self.shot_sequence[current_row]
            self._update_shot_list()
            self.shot_list.setCurrentRow(current_row + 1)
            self.sig_sequence_changed.emit(self.shot_sequence)
    
    def _delete_selected(self):
        """刪除選中的球"""
        current_row = self.shot_list.currentRow()
        if current_row >= 0:
            del self.shot_sequence[current_row]
            self._update_shot_list()
            self.sig_sequence_changed.emit(self.shot_sequence)
    
    def _clear_sequence(self):
        """清空球序"""
        reply = QMessageBox.question(
            self, '確認清空', '確定要清空整個球序嗎？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.shot_sequence.clear()
            self._update_shot_list()
            self.sig_sequence_changed.emit(self.shot_sequence)
    
    def _save_sequence(self):
        """保存球序到檔案"""
        if not self.shot_sequence:
            QMessageBox.warning(self, '警告', '球序為空，無法保存！')
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存球序', 'shot_sequence.json', 'JSON files (*.json)'
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.shot_sequence, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, '成功', f'球序已保存到 {filename}')
            except Exception as e:
                QMessageBox.critical(self, '錯誤', f'保存失敗: {e}')
    
    def _load_sequence(self):
        """從檔案載入球序"""
        filename, _ = QFileDialog.getOpenFileName(
            self, '載入球序', '', 'JSON files (*.json)'
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.shot_sequence = json.load(f)
                self._update_shot_list()
                self.sig_sequence_changed.emit(self.shot_sequence)
                QMessageBox.information(self, '成功', f'球序已從 {filename} 載入')
            except Exception as e:
                QMessageBox.critical(self, '錯誤', f'載入失敗: {e}')
    
    
    def get_sequence(self) -> List[Dict[str, Any]]:
        """獲取當前球序"""
        return self.shot_sequence.copy()


class CustomShotControlWidget(QWidget):
    """自定義發球控制主界面"""
    
    # 信號定義
    sig_shot_command = pyqtSignal(dict)  # 發球指令信號
    sig_sequence_play = pyqtSignal(list)  # 球序播放信號
    
    def __init__(self, gui_instance):
        super().__init__()
        self.gui = gui_instance
        self.is_playing_sequence = False
        self.current_sequence = []
        self.sequence_timer = QTimer()
        self.sequence_timer.timeout.connect(self._play_next_shot)
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        # 創建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 20)  # 減少上邊距
        main_layout.setSpacing(15)  # 減少間距
        
        # 標題
        title_label = QLabel("🎯 自定義發球控制")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("""
            color: #4CAF50;
            margin-bottom: 10px;  /* 減少下邊距 */
            padding: 8px;  /* 減少內邊距 */
            background-color: rgba(76, 175, 80, 0.1);
            border-radius: 10px;
            border: 2px solid #4CAF50;
        """)
        main_layout.addWidget(title_label)
        
        # 創建分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #5a8c9a;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #4CAF50;
            }
        """)
        
        # 左側：參數控制
        self.param_control = ParameterControlWidget()
        splitter.addWidget(self.param_control)
        
        # 右側：球序建構器
        self.sequence_builder = ShotSequenceBuilder()
        splitter.addWidget(self.sequence_builder)
        
        # 設置分割器比例
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # 底部控制區域 - 狀態顯示和播放控制並排
        bottom_layout = QHBoxLayout()
        
        # 左側狀態顯示區域
        status_group = QGroupBox("狀態顯示")
        status_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #5a8c9a;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: rgba(90, 140, 154, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #5a8c9a;
                font-size: 14px;
            }
        """)
        status_group_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(120)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid #5a8c9a;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
                color: #ffffff;
            }
        """)
        status_group_layout.addWidget(self.status_text)
        
        # 右側播放控制區域
        play_group = QGroupBox("播放控制")
        play_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF5722;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: rgba(255, 87, 34, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #FF5722;
                font-size: 14px;
            }
        """)
        play_layout = QVBoxLayout(play_group)
        
        # 發球間隔設定
        interval_layout = QHBoxLayout()
        interval_label = QLabel("發球間隔:")
        interval_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        interval_layout.addWidget(interval_label)
        
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(1.0, 10.0)
        self.interval_spin.setValue(3.0)
        self.interval_spin.setSingleStep(0.5)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: 2px solid #FF5722;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
                font-weight: bold;
                min-width: 80px;
            }
            QDoubleSpinBox:focus {
                border-color: #FF5722;
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        play_layout.addLayout(interval_layout)
        
        # 開始播放按鈕
        self.play_btn = QPushButton("▶️ 開始發球")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: #ffffff;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #45a049, stop:1 #4CAF50);
            }
        """)
        play_layout.addWidget(self.play_btn)
        
        # 將狀態顯示和播放控制並排添加
        bottom_layout.addWidget(status_group, 1)
        bottom_layout.addWidget(play_group, 1)
        
        main_layout.addLayout(bottom_layout)
        
        # 設置整體樣式
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
    
    def _setup_connections(self):
        """設置信號連接"""
        # 參數控制信號
        self.param_control.sig_test_shot.connect(self._on_test_shot)
        self.param_control.add_to_sequence_btn.clicked.connect(self._on_add_to_sequence)
        
        # 播放控制信號
        self.play_btn.clicked.connect(self._on_play_sequence)
    
    def _on_test_shot(self, params: Dict[str, int]):
        """測試發球"""
        self._log_message(f"🎯 測試發球: 速度:{params['speed']}, 水平:{params['horizontal_angle']}°, 垂直:{params['vertical_angle']}°, 高度:{params['height']}")
        
        # 直接發送發球指令
        self._send_custom_shot(params)
    
    def _on_add_to_sequence(self):
        """添加球到序列"""
        params = self.param_control.get_current_parameters()
        
        # 獲取球的名稱
        name, ok = QInputDialog.getText(
            self, '球的名稱', '請輸入這顆球的名稱:',
            QLineEdit.Normal, f"球 {len(self.sequence_builder.get_sequence()) + 1}"
        )
        
        if ok and name:
            self.sequence_builder.add_shot(params, name)
            self._log_message(f"➕ 已添加球到序列: {name}")
    
    def _on_play_sequence(self):
        """播放球序"""
        if self.is_playing_sequence:
            self._stop_sequence()
            return
        
        # 從球序建構器獲取球序數據
        sequence = self.sequence_builder.get_sequence()
        if not sequence:
            self._log_message("❌ 球序為空，無法播放！")
            return
        
        # 添加間隔時間到球序數據
        sequence_with_interval = []
        for shot in sequence:
            shot_data = shot.copy()
            shot_data['interval'] = self.interval_spin.value()
            sequence_with_interval.append(shot_data)
        
        self.current_sequence = sequence_with_interval.copy()
        self.current_shot_index = 0
        self.is_playing_sequence = True
        
        self._log_message(f"▶️ 開始播放球序，共 {len(sequence)} 顆球")
        self._play_next_shot()
    
    def _play_next_shot(self):
        """播放下一顆球"""
        if not self.is_playing_sequence or self.current_shot_index >= len(self.current_sequence):
            self._stop_sequence()
            return
        
        shot = self.current_sequence[self.current_shot_index]
        params = shot['params']
        interval = shot.get('interval', 3.0)
        
        self._log_message(f"🎯 發球 {self.current_shot_index + 1}/{len(self.current_sequence)}: {shot['name']}")
        
        # 直接發送發球指令
        self._send_custom_shot(params)
        
        # 準備下一顆球
        self.current_shot_index += 1
        
        if self.current_shot_index < len(self.current_sequence):
            # 設置定時器，等待間隔時間後發送下一顆球
            self.sequence_timer.start(int(interval * 1000))
        else:
            # 球序播放完成
            self._stop_sequence()
    
    def _stop_sequence(self):
        """停止球序播放"""
        if self.is_playing_sequence:
            self.is_playing_sequence = False
            self.sequence_timer.stop()
            self._log_message("⏹️ 球序播放已停止")
    
    def _send_custom_shot(self, params: Dict[str, int]):
        """發送自定義參數的發球指令"""
        try:
            # 創建發球指令
            command = create_shot_command(
                params['speed'],
                params['horizontal_angle'],
                params['vertical_angle'],
                params['height']
            )
            
            # 嘗試通過現有的發球機系統發送
            success = False
            
            # 1. 嘗試通過藍牙線程發送
            if hasattr(self.gui, 'bluetooth_thread') and self.gui.bluetooth_thread:
                try:
                    # 檢查藍牙線程是否已連接
                    if (hasattr(self.gui.bluetooth_thread, 'client') and 
                        self.gui.bluetooth_thread.client and 
                        hasattr(self.gui.bluetooth_thread, 'is_connected') and 
                        self.gui.bluetooth_thread.is_connected):
                        
                        # 使用現有的藍牙連接發送自定義指令
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop and not loop.is_closed():
                            task = loop.create_task(self._send_via_bluetooth(command))
                            success = True
                        else:
                            self._log_message("❌ 事件循環不可用")
                    else:
                        self._log_message("❌ 藍牙設備未連接")
                except Exception as e:
                    self._log_message(f"❌ 藍牙發送失敗: {e}")
            
            # 2. 嘗試通過設備服務發送
            if not success and hasattr(self.gui, 'device_service') and self.gui.device_service:
                try:
                    # 創建一個臨時的區域代碼來使用現有的發送機制
                    temp_section = "custom_shot"
                    # 這裡需要修改設備服務來支持自定義參數
                    self._log_message("⚠️ 設備服務暫不支持自定義參數發球")
                except Exception as e:
                    self._log_message(f"❌ 設備服務發送失敗: {e}")
            
            # 3. 模擬模式
            if not success:
                import os
                if os.environ.get("SIMULATE", "0") == "1":
                    self._log_message(f"[simulate] 發送自定義發球指令: {params}")
                    success = True
                else:
                    self._log_message("❌ 發球機未連接或無法發送自定義參數")
            
            if success:
                self._log_message("✅ 自定義發球指令已發送")
            
        except Exception as e:
            self._log_message(f"❌ 發送自定義發球指令失敗: {e}")
            import traceback
            traceback.print_exc()
    
    async def _send_via_bluetooth(self, command):
        """通過藍牙發送指令"""
        try:
            if hasattr(self.gui.bluetooth_thread, 'client') and self.gui.bluetooth_thread.client:
                # 使用現有的藍牙連接發送指令
                write_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"  # 與系統其他部分一致的UUID
                await self.gui.bluetooth_thread.client.write_gatt_char(write_char_uuid, command)
                self._log_message("✅ 藍牙發球指令已發送")
            else:
                self._log_message("❌ 藍牙設備未連接")
        except Exception as e:
            self._log_message(f"❌ 藍牙發送失敗: {e}")
    
    def _log_message(self, message: str):
        """記錄日誌訊息"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.status_text.append(log_entry)
        
        # 限制日誌行數並自動滾動
        if self.status_text.document().blockCount() > 50:
            cursor = self.status_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 5)
            cursor.removeSelectedText()
        
        self.status_text.moveCursor(self.status_text.textCursor().End)
        
        # 同時記錄到主GUI
        if hasattr(self.gui, 'log_message'):
            self.gui.log_message(message)


def create_custom_shot_control_tab(gui_instance):
    """創建自定義發球控制標籤頁"""
    try:
        custom_shot_widget = CustomShotControlWidget(gui_instance)
        custom_shot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        gui_instance.tab_widget.addTab(custom_shot_widget, "🎯 自定義發球")
        gui_instance.log_message("✅ 自定義發球控制界面已載入")
        
        return custom_shot_widget
        
    except Exception as e:
        gui_instance.log_message(f"❌ 自定義發球控制界面載入失敗: {e}")
        return None

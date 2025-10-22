"""
三發球機簡易控制界面模組

提供三台發球機的簡易控制功能，包括：
- 三等份橫向布局
- 每台發球機獨立的掃描、連線、套餐選擇、開始/暫停功能
- 基礎訓練套餐選擇
"""

import time
import json
import os
import threading
from typing import Dict
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QGroupBox, QProgressBar, QGridLayout, QTextEdit, QSizePolicy, QScrollArea,
    QSpinBox, QFormLayout
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont

# 導入智能協調管理器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.managers.smart_coordination_manager import SmartCoordinationManager


class SingleMachineWidget(QWidget):
    """單台發球機控制組件"""
    
    # 信號定義
    sig_scan = pyqtSignal(str)
    sig_connect = pyqtSignal(str)
    sig_disconnect = pyqtSignal(str)
    sig_start_training = pyqtSignal(str, str, float, int)  # machine_id, program, interval, ball_count
    sig_pause_training = pyqtSignal(str)
    sig_resume_training = pyqtSignal(str)
    sig_stop_training = pyqtSignal(str)
    
    # 樣式常數
    BUTTON_STYLE = """
        QPushButton {
            color: #ffffff;
            border: none;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 11px;
            min-height: 22px;
        }
        QPushButton:hover {
            opacity: 0.8;
        }
        QPushButton:disabled {
            background: #666666;
            color: #cccccc;
        }
    """
    
    COMBO_STYLE = """
        QComboBox {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid {color};
            border-radius: 5px;
            padding: 6px;
            font-size: 11px;
        }
        QComboBox:focus {
            border-color: {dark_color};
        }
        QComboBox::drop-down {
            border: none;
            width: 15px;
        }
        QComboBox::down-arrow {
            width: 10px;
            height: 10px;
        }
    """
    
    def __init__(self, machine_id: str, machine_name: str, color: str, icon: str, advanced_training_programs: Dict = None):
        super().__init__()
        self.machine_id = machine_id
        self.machine_name = machine_name
        self.color = color
        self.icon = icon
        self.is_connected = False
        self.is_training = False
        self.training_programs = self._load_training_programs()
        self.advanced_training_programs = advanced_training_programs or {}
        
        self._setup_ui()
        self._setup_connections()
    
    def _load_training_programs(self) -> Dict:
        """載入訓練套餐數據"""
        try:
            # 優先使用新的配置管理器
            from core.config import get_config_manager
            config_manager = get_config_manager()
            
            # 載入基礎訓練
            basic_training = config_manager.get_basic_training_config("basic_training")
            if basic_training and "config" in basic_training:
                return basic_training["config"]
            
            # 回退到舊檔案
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            programs_file = os.path.join(project_root, "training_programs.json")
            
            if os.path.exists(programs_file):
                with open(programs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("training_programs", {}).get("basic_training", {})
            else:
                print(f"訓練套餐文件不存在: {programs_file}")
                return {}
        except Exception as e:
            print(f"載入訓練套餐失敗: {e}")
            return {}
    
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)  # 增加間距，為掃描控制組拉伸預留空間
        layout.setContentsMargins(20, 20, 20, 20)  # 增加邊距
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(380)  # 增加最小寬度
        self.setMinimumHeight(650)  # 增加最小高度，為掃描控制組拉伸預留空間
        
        # 標題
        title_layout = QHBoxLayout()
        self.title_label = QLabel(f"{self.icon} {self.machine_name}")
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {self.color};")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        # 連接狀態指示器
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: red; font-size: 18px;")
        self.connection_indicator.setToolTip("未連接")
        title_layout.addWidget(self.connection_indicator)
        
        layout.addLayout(title_layout)
        
        # 連接信息
        self.connection_info = QLabel("未連接")
        self.connection_info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.connection_info)
        
        # 掃描控制
        scan_group = QGroupBox("🔍 掃描控制")
        scan_group.setStyleSheet("""
            QGroupBox::title {
                color: #9C27B0;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        scan_layout = QVBoxLayout(scan_group)
        
        # 掃描按鈕
        self.scan_btn = QPushButton("🔍 掃描設備")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: #ffffff;
                border: none;
                padding: 4px 8px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A1B9A;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #cccccc;
            }
        """)
        scan_layout.addWidget(self.scan_btn)
        
        # 掃描狀態指示器
        
        # 設備選擇
    
        self.device_combo = QComboBox()
        self.device_combo.addItem("請先掃描設備")
        combo_style = self.COMBO_STYLE.replace('{color}', self.color).replace('{dark_color}', self._darken_color(self.color))
        self.device_combo.setStyleSheet(combo_style)
        scan_layout.addWidget(self.device_combo)
        
        # 添加彈性空間，讓掃描控制組垂直拉伸1.2倍
        scan_layout.addStretch()
        
        # 設置掃描控制組的最小高度，實現1.2倍拉伸
        scan_group.setMinimumHeight(120)  # 約為原始高度的1.2倍
        
        layout.addWidget(scan_group)
        
        # 連接控制
        connect_group = QGroupBox()
        connect_group.setStyleSheet("""
            QGroupBox::title {
                color: #4CAF50;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        connect_layout = QHBoxLayout(connect_group)
        
        self.connect_btn = QPushButton("🔗 連接")
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color};
                color: #ffffff;
                border: none;
                padding: 4px 8px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-height: 22px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(self.color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(self._darken_color(self.color))};
            }}
            QPushButton:disabled {{
                background-color: #666666;
                color: #cccccc;
            }}
        """)
        
        self.disconnect_btn = QPushButton("❌ 斷開")
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                padding: 4px 8px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #cccccc;
            }
        """)
        self.disconnect_btn.setEnabled(False)
        
        connect_layout.addWidget(self.connect_btn)
        connect_layout.addWidget(self.disconnect_btn)
        layout.addWidget(connect_group)
        
        # 訓練套餐選擇
        program_group = QGroupBox("📋 訓練套餐")
        program_group.setStyleSheet("""
            QGroupBox::title {
                color: #2196F3;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        program_layout = QVBoxLayout(program_group)
        
        self.program_combo = QComboBox()
        
        # 添加基礎訓練項目
        if self.training_programs and "shots" in self.training_programs:
            for shot in self.training_programs["shots"]:
                description = shot.get("description", "未知訓練")
                section = shot.get("section", "")
                self.program_combo.addItem(f"基礎 - {description}", section)
        else:
            # 後備選項 - 使用預設的section映射
            fallback_shots = [
                ("正手高遠球", "sec25_1"), ("反手高遠球", "sec21_1"), 
                ("正手切球", "sec25_1"), ("反手切球", "sec21_1"),
                ("正手殺球", "sec25_1"), ("反手殺球", "sec21_1"), 
                ("正手平抽球", "sec15_1"), ("反手平抽球", "sec11_1"),
                ("正手小球", "sec5_1"), ("反手小球", "sec1_1"), 
                ("正手挑球", "sec5_1"), ("反手挑球", "sec1_1"),
                ("平推球", "sec13_1"), ("正手接殺球", "sec20_1"), 
                ("反手接殺球", "sec16_1"), ("近身接殺", "sec18_1")
            ]
            for description, section in fallback_shots:
                self.program_combo.addItem(f"基礎 - {description}", section)
        
        # 添加進階訓練套餐
        if self.advanced_training_programs:
            for program_id, program_data in self.advanced_training_programs.items():
                program_name = program_data.get("name", program_id)
                program_type = program_data.get("type", "advanced")
                self.program_combo.addItem(f"進階 - {program_name}", f"advanced:{program_id}")
        
        program_style = self.COMBO_STYLE.replace('{color}', '#2196F3').replace('{dark_color}', '#1976D2')
        program_style = program_style.replace("padding: 6px;", "padding: 8px;").replace("font-size: 11px;", "font-size: 12px;")
        self.program_combo.setStyleSheet(program_style)
        program_layout.addWidget(self.program_combo)
        layout.addWidget(program_group)
        
        # 訓練參數設定
        params_group = QGroupBox("⚙️ 訓練參數")
        params_group.setStyleSheet("""
            QGroupBox::title {
                color: #FF5722;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        params_layout = QHBoxLayout(params_group)  # 改為水平布局
        
        # 間隔秒數選擇
        interval_label = QLabel("發球間隔:")
        interval_label.setStyleSheet("color: #FF5722; font-weight: bold; font-size: 11px;")
        params_layout.addWidget(interval_label)
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItems([
            "1.5秒 (極快)", "2.0秒 (很快)", "2.5秒 (快)", 
            "3.0秒 (正常)", "3.5秒 (慢)", "4.0秒 (很慢)", "5.0秒 (極慢)"
        ])
        self.interval_combo.setCurrentText("3.0秒 (正常)")  # 預設值
        interval_style = self.COMBO_STYLE.replace('{color}', '#FF5722').replace('{dark_color}', '#D84315')
        self.interval_combo.setStyleSheet(interval_style)
        params_layout.addWidget(self.interval_combo)
        
        # 添加間距
        params_layout.addSpacing(15)
        
        # 球數選擇
        ball_count_label = QLabel("發球數量:")
        ball_count_label.setStyleSheet("color: #FF5722; font-weight: bold; font-size: 11px;")
        params_layout.addWidget(ball_count_label)
        
        self.ball_count_spin = QSpinBox()
        self.ball_count_spin.setRange(1, 999)
        self.ball_count_spin.setValue(50)  # 預設50球
        self.ball_count_spin.setSuffix(" 球")
        self.ball_count_spin.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                border: 2px solid #FF5722;
                border-radius: 5px;
                padding: 6px;
                font-size: 11px;
            }
            QSpinBox:focus {
                border-color: #D84315;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #FF5722;
                border: none;
                width: 15px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #D84315;
            }
        """)
        params_layout.addWidget(self.ball_count_spin)
        
        # 添加彈性空間，讓控制項靠左對齊
        params_layout.addStretch()
        
        layout.addWidget(params_group)
        
        # 訓練控制
        control_group = QGroupBox("🎮 訓練控制")
        control_group.setStyleSheet("""
            QGroupBox::title {
                color: #FF9800;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        control_layout = QGridLayout(control_group)
        control_layout.setVerticalSpacing(8)  # 設置行間距，防止按鈕重疊
        control_layout.setHorizontalSpacing(8)  # 設置列間距
        
        # 訓練控制按鈕
        button_configs = [
            ("start_btn", "▶️ 開始訓練", "#4CAF50", "#45a049"),
            ("pause_btn", "⏸️ 暫停", "#FF9800", "#F57C00"),
            ("resume_btn", "▶️ 恢復", "#2196F3", "#1976D2"),
            ("stop_btn", "⏹️ 停止", "#F44336", "#D32F2F")
        ]
        
        for attr_name, text, color1, color2 in button_configs:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color1};
                    color: #ffffff;
                    border: none;
                    padding: 5px 3px;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 10px;
                    min-height: 20px;
                }}
                QPushButton:hover {{
                    background-color: {color2};
                }}
                QPushButton:pressed {{
                    background-color: {color1};
                    opacity: 0.8;
                }}
                QPushButton:disabled {{
                    background-color: #666666;
                    color: #cccccc;
                }}
            """)
            if attr_name in ["pause_btn", "resume_btn", "stop_btn"]:
                btn.setEnabled(False)
            setattr(self, attr_name, btn)
        
        # 使用2x2網格布局
        control_layout.addWidget(self.start_btn, 0, 0)    # 第一行第一列
        control_layout.addWidget(self.pause_btn, 0, 1)    # 第一行第二列
        control_layout.addWidget(self.resume_btn, 1, 0)   # 第二行第一列
        control_layout.addWidget(self.stop_btn, 1, 1)     # 第二行第二列
        
        # 添加彈性空間，讓訓練控制組垂直拉伸1.2倍
        control_layout.addWidget(QLabel(), 2, 0, 1, 2)  # 添加空標籤佔位
        control_layout.setRowStretch(2, 1)  # 讓第三行拉伸
        
        # 設置訓練控制組的最小高度，實現1.2倍拉伸
        control_group.setMinimumHeight(120)  # 約為原始高度的1.2倍
        
        layout.addWidget(control_group)
        
        # 已移除「訓練狀態」視覺欄位以簡化界面
        
        # 設置組件樣式
        self.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.color};
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: {self.color};
            }}
        """)
    
    def _setup_connections(self):
        """設置信號連接"""
        self.scan_btn.clicked.connect(self._on_scan)
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.start_btn.clicked.connect(self._on_start_training)
        self.pause_btn.clicked.connect(self._on_pause_training)
        self.resume_btn.clicked.connect(self._on_resume_training)
        self.stop_btn.clicked.connect(self._on_stop_training)
    
    def _on_scan(self):
        """掃描設備"""
        self.sig_scan.emit(self.machine_id)
    
    def _on_connect(self):
        """連接發球機"""
        self.sig_connect.emit(self.machine_id)
    
    def _on_disconnect(self):
        """斷開發球機"""
        self.sig_disconnect.emit(self.machine_id)
    
    def _on_start_training(self):
        """開始訓練"""
        program = self.program_combo.currentText()
        section = self.program_combo.currentData()
        
        # 解析間隔秒數
        interval_text = self.interval_combo.currentText()
        interval = self._parse_interval(interval_text)
        
        # 獲取球數
        ball_count = self.ball_count_spin.value()
        
        self.sig_start_training.emit(self.machine_id, program, interval, ball_count)
    
    def _parse_interval(self, interval_text: str) -> float:
        """解析間隔秒數文字為數值"""
        try:
            # 從文字中提取數字，例如 "3.0秒 (正常)" -> 3.0
            import re
            match = re.search(r'(\d+\.?\d*)', interval_text)
            if match:
                return float(match.group(1))
            else:
                return 3.0  # 預設值
        except:
            return 3.0  # 預設值
    
    def _on_pause_training(self):
        """暫停訓練"""
        self.sig_pause_training.emit(self.machine_id)
    
    def _on_resume_training(self):
        """恢復訓練"""
        self.sig_resume_training.emit(self.machine_id)
    
    def _on_stop_training(self):
        """停止訓練"""
        self.sig_stop_training.emit(self.machine_id)
    
    def _darken_color(self, color: str) -> str:
        """將顏色變暗"""
        color_map = {
            '#4CAF50': '#45a049',  # 綠色
            '#2196F3': '#1976D2',  # 藍色
            '#FF9800': '#F57C00'   # 橙色
        }
        return color_map.get(color, color)
    
    def update_connection_status(self, connected: bool, device_name: str = "", address: str = ""):
        """更新連接狀態"""
        self.is_connected = connected
        
        if connected:
            self.connection_indicator.setStyleSheet("color: green; font-size: 18px;")
            self.connection_indicator.setToolTip("已連接")
            self.connection_info.setText(f"已連接: {device_name}")
            self.connection_info.setStyleSheet("color: green; font-size: 11px;")
        else:
            self.connection_indicator.setStyleSheet("color: red; font-size: 18px;")
            self.connection_indicator.setToolTip("未連接")
            self.connection_info.setText("未連接")
            self.connection_info.setStyleSheet("color: gray; font-size: 11px;")
        
        self._update_button_states()
    
    def update_training_status(self, is_training: bool, program: str = "", 
                             current: int = 0, total: int = 0, status: str = ""):
        """更新訓練狀態"""
        self.is_training = is_training
        self.current_program = program
        
        # 若界面存在狀態元件才更新（本介面已移除狀態欄位）
        if hasattr(self, 'status_label') and hasattr(self, 'progress_bar'):
            if is_training:
                self.status_label.setText(f"訓練中: {program}")
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;")
                if total > 0:
                    self.progress_bar.setVisible(True)
                    self.progress_bar.setMaximum(total)
                    self.progress_bar.setValue(current)
                else:
                    self.progress_bar.setVisible(True)
                    self.progress_bar.setMaximum(0)  # 無限模式
            else:
                self.status_label.setText("待機中")
                self.status_label.setStyleSheet("color: #666; font-size: 11px;")
                self.progress_bar.setVisible(False)
        
        self._update_button_states()
    
    def _update_button_states(self):
        """更新按鈕狀態"""
        # 連接按鈕狀態
        self.connect_btn.setEnabled(not self.is_connected)
        self.disconnect_btn.setEnabled(self.is_connected)
        
        # 訓練按鈕狀態
        can_start = self.is_connected and not self.is_training
        can_control = self.is_connected and self.is_training
        
        self.start_btn.setEnabled(can_start)
        self.pause_btn.setEnabled(can_control)
        self.resume_btn.setEnabled(can_control)
        self.stop_btn.setEnabled(can_control)
        
        # 套餐選擇和訓練參數狀態
        self.program_combo.setEnabled(self.is_connected)
        self.interval_combo.setEnabled(self.is_connected)
        self.ball_count_spin.setEnabled(self.is_connected)
    
    def update_scan_status(self, status: str, is_scanning: bool = False):
        """更新掃描狀態"""
        # 移除對不存在的 scan_status_label 的引用
        self.scan_btn.setEnabled(not is_scanning)
        
        # 狀態樣式映射
        status_styles = {
            "scanning": ("#2196F3", "掃描中..."),
            "success": ("#4CAF50", "🔍 掃描設備"),
            "error": ("#f44336", "🔍 掃描設備"),
            "default": ("#ffcc00", "🔍 掃描設備")
        }
        
        if is_scanning:
            color, text = status_styles["scanning"]
            self.scan_btn.setText(text)
        else:
            if "找到" in status:
                color, text = status_styles["success"]
            elif "失敗" in status or "錯誤" in status:
                color, text = status_styles["error"]
            else:
                color, text = status_styles["default"]
            self.scan_btn.setText(text)
        
        # 更新掃描按鈕樣式
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: #ffffff;
                border: none;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 11px;
                min-height: 22px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: #666666;
                color: #999999;
            }}
        """)
    
    def update_device_list(self, devices: list):
        """更新設備列表"""
        self.device_combo.clear()
        
        if not devices:
            self.device_combo.addItem("未找到設備")
            self.connect_btn.setEnabled(False)
        else:
            for device in devices:
                device_name = device.get('name', '未知設備')
                device_address = device.get('address', '')
                display_text = f"{device_name} ({device_address})"
                self.device_combo.addItem(display_text, device_address)
            
            self.connect_btn.setEnabled(True)


class ThreeMachineSimpleWidget(QWidget):
    """三發球機簡易控制主界面"""
    
    def __init__(self, gui_instance):
        super().__init__()
        self.gui = gui_instance
        self.machine_widgets: Dict[str, SingleMachineWidget] = {}
        
        # 初始化智能協調管理器
        self.smart_coordinator = SmartCoordinationManager()
        self._setup_coordinator_connections()
        
        # 初始化訓練狀態管理
        self.training_threads: Dict[str, threading.Thread] = {}
        self.training_stop_flags: Dict[str, bool] = {}
        self.training_pause_flags: Dict[str, bool] = {}
        
        # 載入進階訓練套餐
        self.advanced_training_programs = self._load_advanced_training_programs()
        
        self._setup_ui()
        self._setup_connections()
    
    def _load_advanced_training_programs(self) -> Dict:
        """載入進階訓練套餐數據"""
        try:
            from core.config import get_config_manager
            config_manager = get_config_manager()
            
            # 載入進階訓練配置
            advanced_configs = config_manager.get_advanced_configs()
            if advanced_configs and "categories" in advanced_configs:
                return advanced_configs["categories"]
            
            return {}
        except Exception as e:
            print(f"載入進階訓練套餐失敗: {e}")
            return {}
    
    def _setup_coordinator_connections(self):
        """設置協調管理器信號連接"""
        self.smart_coordinator.shot_scheduled.connect(self._on_shot_scheduled)
        self.smart_coordinator.shot_completed.connect(self._on_shot_completed)
        self.smart_coordinator.coordination_update.connect(self._on_coordination_update)
    
    def _on_shot_scheduled(self, machine_id: str, area: str, delay: float):
        """發球已調度"""
        self._log_message(f"📅 {machine_id} 發球已調度: {area} (延遲: {delay:.2f}秒)")
    
    def _on_shot_completed(self, machine_id: str, success: bool, message: str):
        """發球完成"""
        status_icon = "✅" if success else "❌"
        self._log_message(f"{status_icon} {machine_id} {message}")
        
        # 更新發球機狀態
        widget = self.machine_widgets.get(machine_id)
        if widget:
            if success:
                widget.update_training_status(True, widget.current_program, 
                                            widget.current_shot + 1, widget.total_shots, "訓練中")
            else:
                widget.update_training_status(True, widget.current_program, 
                                            widget.current_shot, widget.total_shots, "發球失敗")
    
    def _on_coordination_update(self, status: dict):
        """協調狀態更新"""
        # 可以在此處更新協調狀態顯示
        pass
    
    def _setup_ui(self):
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
                background-color: rgba(255, 255, 255, 0.1);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: rgba(255, 255, 255, 0.1);
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # 創建主容器
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(35)  # 增加間距，為掃描控制組拉伸預留空間
        layout.setContentsMargins(40, 40, 40, 40)  # 增加邊距
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 三台發球機橫向布局
        machines_layout = QHBoxLayout()
        machines_layout.setSpacing(40)  # 增加發球機之間的間距
        machines_layout.setContentsMargins(0, 0, 0, 0)
        
        # 創建三台發球機組件
        machine_configs = [
            ("machine_1", "發球機 1", "#4CAF50", " "),
            ("machine_2", "發球機 2", "#2196F3", " "),
            ("machine_3", "發球機 3", "#FF9800", " ")
        ]
        
        for machine_id, machine_name, color, icon in machine_configs:
            widget = SingleMachineWidget(machine_id, machine_name, color, icon, self.advanced_training_programs)
            self.machine_widgets[machine_id] = widget
            # 設置每個組件的拉伸比例為1，確保平均分配空間
            machines_layout.addWidget(widget, 1)
        
        layout.addLayout(machines_layout)
        
        # 全局控制
        global_group = QGroupBox("全局控制")
        global_layout = QHBoxLayout(global_group)
        global_layout.setSpacing(20)  # 增加按鈕間距
        global_layout.setContentsMargins(25, 25, 25, 25)  # 增加邊距
        
        # 全局控制按鈕配置
        global_buttons = [
            ("start_all_btn", "▶️ 全部開始", "#4CAF50", "#45a049"),
            ("pause_all_btn", "⏸️ 全部暫停", "#FF9800", "#F57C00"),
            ("resume_all_btn", "▶️ 全部恢復", "#2196F3", "#1976D2"),
            ("stop_all_btn", "⏹️ 全部停止", "#F44336", "#D32F2F")
        ]
        
        for attr_name, text, color1, color2 in global_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {color1}, stop:1 {color2});
                    color: #ffffff;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    opacity: 0.8;
                }}
            """)
            setattr(self, attr_name, btn)
            global_layout.addWidget(btn)
        
        global_layout.addStretch()
        
        layout.addWidget(global_group)
        
        # 狀態日誌
        log_group = QGroupBox("狀態日誌")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(15, 15, 15, 15)  # 增加日誌區域邊距
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)  # 減少日誌高度以節省空間
        self.log_text.setMinimumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
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
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # 設置滾動區域的內容
        scroll_area.setWidget(main_widget)
        
        # 創建主布局並添加滾動區域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        # 設置整體樣式
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #5a8c9a;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: rgba(90, 140, 154, 0.1);
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #4CAF50;
                font-size: 14px;
            }
        """)
    
    def _setup_connections(self):
        """設置信號連接"""
        # 全局控制按鈕
        self.start_all_btn.clicked.connect(self._on_start_all)
        self.pause_all_btn.clicked.connect(self._on_pause_all)
        self.resume_all_btn.clicked.connect(self._on_resume_all)
        self.stop_all_btn.clicked.connect(self._on_stop_all)
        
        # 連接各發球機組件的信號
        for machine_id, widget in self.machine_widgets.items():
            widget.sig_scan.connect(self._on_scan_machine)
            widget.sig_connect.connect(self._on_connect_machine)
            widget.sig_disconnect.connect(self._on_disconnect_machine)
            widget.sig_start_training.connect(self._on_start_training)
            widget.sig_pause_training.connect(self._on_pause_training)
            widget.sig_resume_training.connect(self._on_resume_training)
            widget.sig_stop_training.connect(self._on_stop_training)
    
    def _on_start_all(self):
        """全部開始訓練 - 使用智能協調管理器"""
        self._log_message("▶️ 開始所有發球機訓練（智能協調模式）...")
        
        # 設置發球機為就緒狀態
        for machine_id, widget in self.machine_widgets.items():
            if widget.is_connected:
                # 設置發球機線程引用
                if hasattr(self.gui, 'basic_training_executor'):
                    self.smart_coordinator.set_machine_thread(machine_id, self.gui.basic_training_executor)
                
                # 設置發球機為就緒狀態
                self.smart_coordinator.machine_states[machine_id] = self.smart_coordinator.MachineState.READY
                
                # 開始訓練循環
                self._start_machine_training(machine_id, widget)
                self._log_message(f"✅ {machine_id} 已加入智能協調訓練")
            else:
                self._log_message(f"⚠️ {machine_id} 未連接，跳過訓練")
    
    def _start_machine_training(self, machine_id: str, widget):
        """開始單台發球機訓練"""
        program = widget.program_combo.currentText()
        section = widget.program_combo.currentData()
        interval_text = widget.interval_combo.currentText()
        interval = widget._parse_interval(interval_text)
        ball_count = widget.ball_count_spin.value()
        
        # 更新訓練狀態
        widget.update_training_status(True, program, 0, ball_count, "訓練中")
        widget.current_program = program
        widget.current_shot = 0
        widget.total_shots = ball_count
        
        # 使用智能協調管理器請求發球
        for i in range(ball_count):
            # 計算發球時間（錯開時間避免衝突）
            shot_delay = i * interval + (hash(machine_id) % 100) / 1000  # 微小的隨機延遲
            self._schedule_shot(machine_id, section, shot_delay)
    
    def _schedule_shot(self, machine_id: str, area: str, delay: float):
        """調度發球"""
        # 使用QTimer延遲發球請求
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.smart_coordinator.request_shot(machine_id, area, priority=1))
        timer.start(int(delay * 1000))  # 轉換為毫秒
    
    def _on_pause_all(self):
        """全部暫停訓練 - 使用智能協調管理器"""
        self._log_message("⏸️ 暫停所有發球機訓練...")
        
        for machine_id in self.machine_widgets.keys():
            success = self.smart_coordinator.pause_machine(machine_id)
            if success:
                widget = self.machine_widgets.get(machine_id)
                if widget and widget.is_training:
                    widget.update_training_status(True, widget.current_program, 
                                                widget.current_shot, widget.total_shots, "已暫停")
        
        self._log_message("✅ 所有發球機訓練已暫停")
    
    def _on_resume_all(self):
        """全部恢復訓練 - 使用智能協調管理器"""
        self._log_message("▶️ 恢復所有發球機訓練...")
        
        for machine_id in self.machine_widgets.keys():
            success = self.smart_coordinator.resume_machine(machine_id)
            if success:
                widget = self.machine_widgets.get(machine_id)
                if widget and widget.is_training:
                    widget.update_training_status(True, widget.current_program, 
                                                widget.current_shot, widget.total_shots, "訓練中")
        
        self._log_message("✅ 所有發球機訓練已恢復")
    
    def _on_stop_all(self):
        """全部停止訓練 - 使用智能協調管理器"""
        self._log_message("⏹️ 停止所有發球機訓練...")
        
        # 停止所有發球機
        for machine_id in self.machine_widgets.keys():
            self.smart_coordinator.stop_machine(machine_id)
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
        
        # 清空發球隊列
        self.smart_coordinator.clear_queue()
        
        # 停止基礎訓練執行器
        if hasattr(self.gui, 'basic_training_executor'):
            self.gui.basic_training_executor.stop_training()
        
        self._log_message("✅ 所有發球機訓練已停止")
    
    def _execute_global_training_action(self, action: str, status_text: str, success_msg: str, failure_msg: str):
        """執行全局訓練操作的通用方法"""
        if hasattr(self.gui, 'basic_training_executor'):
            executor = self.gui.basic_training_executor
            if action == 'pause_training':
                success = executor.pause_training()
            elif action == 'resume_training':
                success = executor.resume_training()
            else:
                success = False
            
            if success:
                # 更新所有發球機的訓練狀態
                for machine_id, widget in self.machine_widgets.items():
                    if widget.is_training:
                        widget.update_training_status(True, widget.current_program, 
                                                    widget.current_shot, widget.total_shots, status_text)
                self._log_message(success_msg)
            else:
                self._log_message(failure_msg)
        else:
            self._log_message("❌ 訓練執行器未初始化")
    
    def _on_scan_machine(self, machine_id: str):
        """掃描指定發球機"""
        self._log_message(f"🔍 開始掃描 {machine_id}...")
        widget = self.machine_widgets.get(machine_id)
        if widget:
            widget.update_scan_status("🔍 正在掃描設備...", True)
            # 使用真實的藍牙掃描功能
            self._perform_real_scan(machine_id)
    
    def _perform_real_scan(self, machine_id: str):
        """執行真實的藍牙掃描"""
        try:
            # 直接使用同步掃描，避免事件循環問題
            self._log_message(f"🔍 {machine_id} 使用同步掃描模式...")
            self._perform_sync_scan(machine_id)
        except Exception as e:
            self._log_message(f"❌ 掃描失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_scan_status("❌ 掃描失敗", False)
    
    async def _scan_bluetooth_devices(self, machine_id: str):
        """異步藍牙設備掃描"""
        try:
            from bleak import BleakScanner
            import asyncio
            
            self._log_message(f"🔍 {machine_id} 開始藍牙掃描...")
            
            # 掃描藍牙設備
            devices = await BleakScanner.discover(timeout=5.0)
            
            # 過濾發球機設備
            found_devices = []
            # 只掃描前綴為YX的設備
            
            for device in devices or []:
                try:
                    name = getattr(device, 'name', None)
                    if name:
                        # 只檢查前綴為YX的設備
                        if name.upper().startswith('YX'):
                            device_info = {
                                'name': name,
                                'address': device.address,
                                'rssi': getattr(device, 'rssi', 0)
                            }
                            found_devices.append(device_info)
                except Exception:
                    continue
            
            # 更新UI
            widget = self.machine_widgets.get(machine_id)
            if widget:
                if found_devices:
                    widget.update_device_list(found_devices)
                    widget.update_scan_status(f"✅ 找到 {len(found_devices)} 個設備")
                    self._log_message(f"✅ {machine_id} 掃描完成，找到 {len(found_devices)} 個發球機設備")
                else:
                    widget.update_device_list([])
                    widget.update_scan_status("❌ 未找到設備")
                    self._log_message(f"❌ {machine_id} 未找到發球機設備")
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 藍牙掃描失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_scan_status("❌ 掃描失敗", False)
    
    def _perform_sync_scan(self, machine_id: str):
        """同步掃描（優化版本）"""
        try:
            import threading
            import queue
            import asyncio
            
            result_queue = queue.Queue()
            
            def run_scan_in_thread():
                try:
                    # 創建新的事件循環
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # 直接運行掃描邏輯，避免異步函數調用問題
                    result = new_loop.run_until_complete(self._scan_bluetooth_devices_sync(machine_id))
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    try:
                        new_loop.close()
                    except:
                        pass
            
            # 在後台線程中運行掃描
            scan_thread = threading.Thread(target=run_scan_in_thread, daemon=True)
            scan_thread.start()
            
            # 等待結果（最多等待15秒）
            try:
                status, result = result_queue.get(timeout=15)
                if status == 'error':
                    self._log_message(f"❌ {machine_id} 同步掃描失敗: {result}")
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_scan_status("❌ 掃描失敗", False)
            except queue.Empty:
                self._log_message(f"❌ {machine_id} 掃描超時")
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_scan_status("❌ 掃描超時", False)
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 同步掃描錯誤: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_scan_status("❌ 掃描錯誤", False)
    
    async def _scan_bluetooth_devices_sync(self, machine_id: str):
        """同步掃描專用的藍牙設備掃描"""
        try:
            from bleak import BleakScanner
            
            self._log_message(f"🔍 {machine_id} 開始藍牙掃描...")
            
            # 掃描藍牙設備
            devices = await BleakScanner.discover(timeout=5.0)
            
            # 過濾發球機設備
            found_devices = []
            # 只掃描前綴為YX的設備
            
            for device in devices or []:
                try:
                    name = getattr(device, 'name', None)
                    if name:
                        # 只檢查前綴為YX的設備
                        if name.upper().startswith('YX'):
                            device_info = {
                                'name': name,
                                'address': device.address,
                                'rssi': getattr(device, 'rssi', 0)
                            }
                            found_devices.append(device_info)
                except Exception:
                    continue
            
            # 更新UI
            widget = self.machine_widgets.get(machine_id)
            if widget:
                if found_devices:
                    widget.update_device_list(found_devices)
                    widget.update_scan_status(f"✅ 找到 {len(found_devices)} 個設備")
                    self._log_message(f"✅ {machine_id} 掃描完成，找到 {len(found_devices)} 個發球機設備")
                else:
                    widget.update_device_list([])
                    widget.update_scan_status("❌ 未找到設備")
                    self._log_message(f"❌ {machine_id} 未找到發球機設備")
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 藍牙掃描失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_scan_status("❌ 掃描失敗", False)
    
    def _on_connect_machine(self, machine_id: str):
        """連接指定發球機"""
        widget = self.machine_widgets.get(machine_id)
        if widget:
            selected_device = widget.device_combo.currentData()
            if selected_device:
                self._log_message(f"🔗 連接 {machine_id} 到設備 {selected_device}...")
                # 執行真實的藍牙連接
                self._perform_real_connect(machine_id, selected_device)
            else:
                self._log_message(f"❌ {machine_id} 請先選擇設備")
    
    def _perform_real_connect(self, machine_id: str, device_address: str):
        """執行真實的藍牙連接"""
        try:
            widget = self.machine_widgets.get(machine_id)
            if not widget:
                return
            
            # 直接使用同步連接，避免事件循環問題
            self._log_message(f"🔗 {machine_id} 使用同步連接模式...")
            self._perform_sync_connect(machine_id, device_address)
        except Exception as e:
            self._log_message(f"❌ {machine_id} 連接失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    async def _connect_bluetooth_device(self, machine_id: str, device_address: str):
        """異步藍牙設備連接"""
        try:
            from bleak import BleakClient
            import asyncio
            
            self._log_message(f"🔗 {machine_id} 開始連接藍牙設備 {device_address}...")
            
            # 創建藍牙客戶端
            client = BleakClient(device_address)
            
            # 嘗試連接
            await asyncio.wait_for(client.connect(), timeout=10.0)
            
            if client.is_connected:
                # 獲取設備名稱
                try:
                    device_name_bytes = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                    device_name = device_name_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    device_name = f"YX-BE241-{machine_id[-1]}"
                
                # 更新UI
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_connection_status(True, device_name, device_address)
                    self._log_message(f"✅ {machine_id} 連接成功: {device_name} ({device_address})")
                
                # 保存連接信息供後續使用
                if not hasattr(self, 'connected_devices'):
                    self.connected_devices = {}
                self.connected_devices[machine_id] = {
                    'client': client,
                    'address': device_address,
                    'name': device_name
                }
            else:
                self._log_message(f"❌ {machine_id} 連接失敗")
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_connection_status(False)
                    
        except asyncio.TimeoutError:
            self._log_message(f"❌ {machine_id} 連接超時")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
        except Exception as e:
            self._log_message(f"❌ {machine_id} 藍牙連接失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    def _perform_sync_connect(self, machine_id: str, device_address: str):
        """同步連接（優化版本）"""
        try:
            import threading
            import queue
            import asyncio
            
            result_queue = queue.Queue()
            
            def run_connect_in_thread():
                try:
                    # 創建新的事件循環
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # 直接運行連接邏輯，避免異步函數調用問題
                    result = new_loop.run_until_complete(self._connect_bluetooth_device_sync(machine_id, device_address))
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    try:
                        new_loop.close()
                    except:
                        pass
            
            # 在後台線程中運行連接
            connect_thread = threading.Thread(target=run_connect_in_thread, daemon=True)
            connect_thread.start()
            
            # 等待結果（最多等待15秒）
            try:
                status, result = result_queue.get(timeout=15)
                if status == 'error':
                    self._log_message(f"❌ {machine_id} 同步連接失敗: {result}")
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_connection_status(False)
            except queue.Empty:
                self._log_message(f"❌ {machine_id} 連接超時")
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_connection_status(False)
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 同步連接錯誤: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    async def _connect_bluetooth_device_sync(self, machine_id: str, device_address: str):
        """同步連接專用的藍牙設備連接"""
        try:
            from bleak import BleakClient
            import asyncio
            
            self._log_message(f"🔗 {machine_id} 開始連接藍牙設備 {device_address}...")
            
            # 創建藍牙客戶端
            client = BleakClient(device_address)
            
            # 嘗試連接
            await asyncio.wait_for(client.connect(), timeout=10.0)
            
            if client.is_connected:
                # 獲取設備名稱
                try:
                    device_name_bytes = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                    device_name = device_name_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    device_name = f"YX-BE241-{machine_id[-1]}"
                
                # 更新UI
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_connection_status(True, device_name, device_address)
                    self._log_message(f"✅ {machine_id} 連接成功: {device_name} ({device_address})")
                
                # 保存連接信息供後續使用
                if not hasattr(self, 'connected_devices'):
                    self.connected_devices = {}
                self.connected_devices[machine_id] = {
                    'client': client,
                    'address': device_address,
                    'name': device_name
                }
            else:
                self._log_message(f"❌ {machine_id} 連接失敗")
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_connection_status(False)
                    
        except asyncio.TimeoutError:
            self._log_message(f"❌ {machine_id} 連接超時")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
        except Exception as e:
            self._log_message(f"❌ {machine_id} 藍牙連接失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    def _on_disconnect_machine(self, machine_id: str):
        """斷開指定發球機"""
        widget = self.machine_widgets.get(machine_id)
        if widget:
            self._log_message(f"❌ 斷開 {machine_id}...")
            # 執行真實的藍牙斷開
            self._perform_real_disconnect(machine_id)
    
    def _perform_real_disconnect(self, machine_id: str):
        """執行真實的藍牙斷開"""
        try:
            # 檢查是否有連接的設備
            if hasattr(self, 'connected_devices') and machine_id in self.connected_devices:
                device_info = self.connected_devices[machine_id]
                client = device_info.get('client')
                
                if client and hasattr(client, 'is_connected') and client.is_connected:
                    # 直接使用同步斷開，避免事件循環問題
                    self._log_message(f"❌ {machine_id} 使用同步斷開模式...")
                    self._perform_sync_disconnect(machine_id)
                else:
                    # 設備已經斷開，直接更新UI
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_connection_status(False)
                    self._log_message(f"✅ {machine_id} 已斷開")
            else:
                # 沒有連接記錄，直接更新UI
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_connection_status(False)
                self._log_message(f"✅ {machine_id} 已斷開")
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 斷開失敗: {e}")
            # 即使斷開失敗，也更新UI狀態
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    async def _disconnect_bluetooth_device(self, machine_id: str):
        """異步藍牙設備斷開"""
        try:
            if hasattr(self, 'connected_devices') and machine_id in self.connected_devices:
                device_info = self.connected_devices[machine_id]
                client = device_info.get('client')
                
                if client and hasattr(client, 'is_connected') and client.is_connected:
                    await client.disconnect()
                    self._log_message(f"✅ {machine_id} 藍牙連接已斷開")
                
                # 清理連接記錄
                del self.connected_devices[machine_id]
            
            # 更新UI
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 藍牙斷開失敗: {e}")
            # 即使斷開失敗，也更新UI狀態
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    def _perform_sync_disconnect(self, machine_id: str):
        """同步斷開（優化版本）"""
        try:
            import threading
            import queue
            import asyncio
            
            result_queue = queue.Queue()
            
            def run_disconnect_in_thread():
                try:
                    # 創建新的事件循環
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # 直接運行斷開邏輯，避免異步函數調用問題
                    result = new_loop.run_until_complete(self._disconnect_bluetooth_device_sync(machine_id))
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    try:
                        new_loop.close()
                    except:
                        pass
            
            # 在後台線程中運行斷開
            disconnect_thread = threading.Thread(target=run_disconnect_in_thread, daemon=True)
            disconnect_thread.start()
            
            # 等待結果（最多等待5秒）
            try:
                status, result = result_queue.get(timeout=5)
                if status == 'error':
                    self._log_message(f"❌ {machine_id} 同步斷開失敗: {result}")
                    # 即使斷開失敗，也更新UI狀態
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_connection_status(False)
            except queue.Empty:
                self._log_message(f"❌ {machine_id} 斷開超時")
                # 即使斷開超時，也更新UI狀態
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_connection_status(False)
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 同步斷開錯誤: {e}")
            # 即使斷開錯誤，也更新UI狀態
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    async def _disconnect_bluetooth_device_sync(self, machine_id: str):
        """同步斷開專用的藍牙設備斷開"""
        try:
            if hasattr(self, 'connected_devices') and machine_id in self.connected_devices:
                device_info = self.connected_devices[machine_id]
                client = device_info.get('client')
                
                if client and hasattr(client, 'is_connected') and client.is_connected:
                    await client.disconnect()
                    self._log_message(f"✅ {machine_id} 藍牙連接已斷開")
                
                # 清理連接記錄
                del self.connected_devices[machine_id]
            
            # 更新UI
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 藍牙斷開失敗: {e}")
            # 即使斷開失敗，也更新UI狀態
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_connection_status(False)
    
    def _on_start_training(self, machine_id: str, program: str, interval: float, ball_count: int):
        """開始指定發球機訓練"""
        self._log_message(f"▶️ {machine_id} 開始訓練: {program} (間隔: {interval}秒, 球數: {ball_count})")
        
        # 獲取對應的發球機組件
        widget = self.machine_widgets.get(machine_id)
        if not widget:
            self._log_message(f"❌ 找不到發球機組件: {machine_id}")
            return
        
        # 獲取選中的訓練項目數據
        section = widget.program_combo.currentData()
        if not section:
            self._log_message(f"❌ {machine_id} 未選擇有效的訓練項目")
            return
        
        # 檢查是否為進階訓練
        if section.startswith("advanced:"):
            # 進階訓練處理
            advanced_program_id = section.replace("advanced:", "")
            self._execute_advanced_training(machine_id, advanced_program_id, program, ball_count, interval)
            return
        
        # 基礎訓練處理
        training_config = {
            "section": section,
            "description": program,
            "interval": interval,
            "ball_count": ball_count,
            "machine_id": machine_id
        }
        
        # 直接執行三發球機訓練，不依賴基礎訓練執行器
        try:
            # 檢查是否有連接的設備
            if not hasattr(self, 'connected_devices') or machine_id not in self.connected_devices:
                self._log_message(f"❌ {machine_id} 未連接，無法開始訓練")
                return
            
            device_info = self.connected_devices[machine_id]
            client = device_info.get('client')
            
            if not client or not client.is_connected:
                self._log_message(f"❌ {machine_id} 藍牙連接已斷開，無法開始訓練")
                return
            
            # 開始執行訓練
            self._log_message(f"✅ {machine_id} 開始執行訓練: {program}")
            widget.update_training_status(True, program, 0, ball_count, "訓練中")
            
            # 使用非阻塞的異步訓練，避免阻塞其他發球機
            self._log_message(f"🔧 {machine_id} 使用非阻塞訓練模式...")
            self._execute_training_non_blocking(machine_id, section, program, ball_count, interval)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 訓練執行錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    def _execute_advanced_training(self, machine_id: str, program_id: str, program_name: str, ball_count: int, interval: float):
        """執行進階訓練"""
        try:
            # 獲取進階訓練配置
            if program_id not in self.advanced_training_programs:
                self._log_message(f"❌ {machine_id} 找不到進階訓練配置: {program_id}")
                return
            
            advanced_config = self.advanced_training_programs[program_id]
            config_data = advanced_config.get("config", {})
            shots = config_data.get("shots", [])
            
            if not shots:
                self._log_message(f"❌ {machine_id} 進階訓練配置無效: {program_id}")
                return
            
            # 檢查是否有連接的設備
            if not hasattr(self, 'connected_devices') or machine_id not in self.connected_devices:
                self._log_message(f"❌ {machine_id} 未連接，無法開始進階訓練")
                return
            
            device_info = self.connected_devices[machine_id]
            client = device_info.get('client')
            
            if not client or not client.is_connected:
                self._log_message(f"❌ {machine_id} 藍牙連接已斷開，無法開始進階訓練")
                return
            
            # 開始執行進階訓練
            self._log_message(f"✅ {machine_id} 開始執行進階訓練: {program_name}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(True, program_name, 0, ball_count, "進階訓練中")
            
            # 使用非阻塞的異步訓練
            self._log_message(f"🔧 {machine_id} 使用非阻塞進階訓練模式...")
            self._execute_advanced_training_non_blocking(machine_id, program_id, program_name, shots, ball_count, interval)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 進階訓練執行錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    def _execute_advanced_training_non_blocking(self, machine_id: str, program_id: str, program_name: str, shots: list, ball_count: int, interval: float):
        """非阻塞執行進階訓練"""
        try:
            # 檢查是否已經有訓練在進行
            if machine_id in self.training_threads and self.training_threads[machine_id].is_alive():
                self._log_message(f"⚠️ {machine_id} 已有訓練在進行中")
                return
            
            # 設置停止標誌為False，暫停標誌為False
            self.training_stop_flags[machine_id] = False
            self.training_pause_flags[machine_id] = False
            
            def run_advanced_training_in_thread():
                try:
                    # 在獨立線程中執行進階訓練，不阻塞主線程
                    self._execute_advanced_training_in_thread(machine_id, program_id, program_name, shots, ball_count, interval)
                except Exception as e:
                    self._log_message(f"❌ {machine_id} 進階訓練線程錯誤: {e}")
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_training_status(False)
                finally:
                    # 清理訓練線程記錄
                    if machine_id in self.training_threads:
                        del self.training_threads[machine_id]
                    if machine_id in self.training_stop_flags:
                        del self.training_stop_flags[machine_id]
                    if machine_id in self.training_pause_flags:
                        del self.training_pause_flags[machine_id]
            
            # 在後台線程中運行進階訓練，不阻塞主線程
            training_thread = threading.Thread(target=run_advanced_training_in_thread, daemon=True)
            self.training_threads[machine_id] = training_thread
            training_thread.start()
            
            # 立即返回，不等待訓練完成
            self._log_message(f"🚀 {machine_id} 進階訓練已在後台啟動")
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 非阻塞進階訓練錯誤: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    def _execute_advanced_training_in_thread(self, machine_id: str, program_id: str, program_name: str, shots: list, ball_count: int, interval: float):
        """在線程中執行進階訓練"""
        try:
            import asyncio
            import time
            import random
            
            # 創建新的事件循環
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            try:
                # 在事件循環中執行進階訓練
                new_loop.run_until_complete(
                    self._execute_advanced_training_async_in_thread(machine_id, program_id, program_name, shots, ball_count, interval)
                )
            except Exception as e:
                self._log_message(f"❌ {machine_id} 進階訓練事件循環執行錯誤: {e}")
            finally:
                # 安全清理事件循環
                try:
                    # 取消所有未完成的任務
                    pending = asyncio.all_tasks(new_loop)
                    for task in pending:
                        task.cancel()
                    
                    # 等待所有任務完成
                    if pending:
                        new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    
                    # 關閉事件循環
                    new_loop.close()
                except Exception as cleanup_error:
                    self._log_message(f"⚠️ {machine_id} 進階訓練事件循環清理警告: {cleanup_error}")
                    try:
                        new_loop.close()
                    except:
                        pass
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 進階訓練線程失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    async def _execute_advanced_training_async_in_thread(self, machine_id: str, program_id: str, program_name: str, shots: list, ball_count: int, interval: float):
        """在線程中異步執行進階訓練"""
        try:
            import asyncio
            import random
            
            device_info = self.connected_devices[machine_id]
            client = device_info.get('client')
            
            if not client or not client.is_connected:
                self._log_message(f"❌ {machine_id} 藍牙連接已斷開")
                return
            
            # 根據進階訓練配置執行訓練
            total_shots_sent = 0
            
            for i in range(ball_count):
                # 檢查停止標誌
                if machine_id in self.training_stop_flags and self.training_stop_flags[machine_id]:
                    self._log_message(f"⏹️ {machine_id} 進階訓練已被停止")
                    break
                
                # 檢查暫停標誌
                while (hasattr(self, 'training_pause_flags') and 
                       machine_id in self.training_pause_flags and 
                       self.training_pause_flags[machine_id]):
                    # 如果被暫停，等待恢復
                    await asyncio.sleep(0.1)
                    
                    # 再次檢查停止標誌
                    if machine_id in self.training_stop_flags and self.training_stop_flags[machine_id]:
                        self._log_message(f"⏹️ {machine_id} 進階訓練已被停止")
                        return
                
                try:
                    # 隨機選擇一個shot配置
                    selected_shot = random.choice(shots)
                    section = selected_shot.get("section", "")
                    description = selected_shot.get("description", "進階訓練")
                    
                    # 創建發球指令
                    command = self._create_shot_command(section)
                    
                    # 發送指令
                    write_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"
                    await client.write_gatt_char(write_char_uuid, command)
                    
                    # 更新進度
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_training_status(True, program_name, i + 1, ball_count, "進階訓練中")
                        # 保存當前狀態供暫停/恢復使用
                        widget.current_program = program_name
                        widget.current_progress = i + 1
                        widget.total_balls = ball_count
                    
                    self._log_message(f"🎯 {machine_id} 進階發球 {i + 1}/{ball_count}: {description}")
                    
                    # 等待間隔時間
                    if i < ball_count - 1:  # 最後一球不需要等待
                        await asyncio.sleep(interval)
                        
                except Exception as e:
                    self._log_message(f"❌ {machine_id} 第 {i + 1} 球發送失敗: {e}")
                    # 繼續發送下一球，不中斷訓練
                    continue
            
            # 進階訓練完成
            self._log_message(f"✅ {machine_id} 進階訓練完成")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 進階訓練執行失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    async def _execute_training_async(self, machine_id: str, section: str, program: str, ball_count: int, interval: float):
        """異步執行三發球機訓練"""
        try:
            import asyncio
            
            device_info = self.connected_devices[machine_id]
            client = device_info.get('client')
            
            if not client or not client.is_connected:
                self._log_message(f"❌ {machine_id} 藍牙連接已斷開")
                return
            
            # 發送訓練指令
            for i in range(ball_count):
                try:
                    # 創建發球指令
                    command = self._create_shot_command(section)
                    
                    # 發送指令
                    write_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"
                    await client.write_gatt_char(write_char_uuid, command)
                    
                    # 更新進度
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_training_status(True, program, i + 1, ball_count, "訓練中")
                    
                    self._log_message(f"🎯 {machine_id} 發球 {i + 1}/{ball_count}: {program}")
                    
                    # 等待間隔時間
                    if i < ball_count - 1:  # 最後一球不需要等待
                        await asyncio.sleep(interval)
                        
                except Exception as e:
                    self._log_message(f"❌ {machine_id} 第 {i + 1} 球發送失敗: {e}")
                    break
            
            # 訓練完成
            self._log_message(f"✅ {machine_id} 訓練完成")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 訓練執行失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    def _execute_training_non_blocking(self, machine_id: str, section: str, program: str, ball_count: int, interval: float):
        """非阻塞執行三發球機訓練"""
        try:
            # 檢查是否已經有訓練在進行
            if machine_id in self.training_threads and self.training_threads[machine_id].is_alive():
                self._log_message(f"⚠️ {machine_id} 已有訓練在進行中")
                return
            
            # 設置停止標誌為False，暫停標誌為False
            self.training_stop_flags[machine_id] = False
            self.training_pause_flags[machine_id] = False
            
            def run_training_in_thread():
                try:
                    # 在獨立線程中執行訓練，不阻塞主線程
                    self._execute_training_in_thread(machine_id, section, program, ball_count, interval)
                except Exception as e:
                    self._log_message(f"❌ {machine_id} 訓練線程錯誤: {e}")
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_training_status(False)
                finally:
                    # 清理訓練線程記錄
                    if machine_id in self.training_threads:
                        del self.training_threads[machine_id]
                    if machine_id in self.training_stop_flags:
                        del self.training_stop_flags[machine_id]
                    if machine_id in self.training_pause_flags:
                        del self.training_pause_flags[machine_id]
            
            # 在後台線程中運行訓練，不阻塞主線程
            training_thread = threading.Thread(target=run_training_in_thread, daemon=True)
            self.training_threads[machine_id] = training_thread
            training_thread.start()
            
            # 立即返回，不等待訓練完成
            self._log_message(f"🚀 {machine_id} 訓練已在後台啟動")
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 非阻塞訓練錯誤: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    def _execute_training_in_thread(self, machine_id: str, section: str, program: str, ball_count: int, interval: float):
        """在線程中執行訓練"""
        try:
            import asyncio
            import time
            
            # 創建新的事件循環
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            try:
                # 在事件循環中執行訓練
                new_loop.run_until_complete(
                    self._execute_training_async_in_thread(machine_id, section, program, ball_count, interval)
                )
            except Exception as e:
                self._log_message(f"❌ {machine_id} 事件循環執行錯誤: {e}")
            finally:
                # 安全清理事件循環
                try:
                    # 取消所有未完成的任務
                    pending = asyncio.all_tasks(new_loop)
                    for task in pending:
                        task.cancel()
                    
                    # 等待所有任務完成
                    if pending:
                        new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    
                    # 關閉事件循環
                    new_loop.close()
                except Exception as cleanup_error:
                    self._log_message(f"⚠️ {machine_id} 事件循環清理警告: {cleanup_error}")
                    try:
                        new_loop.close()
                    except:
                        pass
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 線程訓練失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    async def _execute_training_async_in_thread(self, machine_id: str, section: str, program: str, ball_count: int, interval: float):
        """在線程中異步執行訓練"""
        try:
            import asyncio
            
            device_info = self.connected_devices[machine_id]
            client = device_info.get('client')
            
            if not client or not client.is_connected:
                self._log_message(f"❌ {machine_id} 藍牙連接已斷開")
                return
            
            # 發送訓練指令
            for i in range(ball_count):
                # 檢查停止標誌
                if machine_id in self.training_stop_flags and self.training_stop_flags[machine_id]:
                    self._log_message(f"⏹️ {machine_id} 訓練已被停止")
                    break
                
                # 檢查暫停標誌
                while (hasattr(self, 'training_pause_flags') and 
                       machine_id in self.training_pause_flags and 
                       self.training_pause_flags[machine_id]):
                    # 如果被暫停，等待恢復
                    await asyncio.sleep(0.1)
                    
                    # 再次檢查停止標誌
                    if machine_id in self.training_stop_flags and self.training_stop_flags[machine_id]:
                        self._log_message(f"⏹️ {machine_id} 訓練已被停止")
                        return
                
                try:
                    # 創建發球指令
                    command = self._create_shot_command(section)
                    
                    # 發送指令
                    write_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"
                    await client.write_gatt_char(write_char_uuid, command)
                    
                    # 更新進度
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_training_status(True, program, i + 1, ball_count, "訓練中")
                        # 保存當前狀態供暫停/恢復使用
                        widget.current_program = program
                        widget.current_progress = i + 1
                        widget.total_balls = ball_count
                    
                    self._log_message(f"🎯 {machine_id} 發球 {i + 1}/{ball_count}: {program}")
                    
                    # 等待間隔時間
                    if i < ball_count - 1:  # 最後一球不需要等待
                        await asyncio.sleep(interval)
                        
                except Exception as e:
                    self._log_message(f"❌ {machine_id} 第 {i + 1} 球發送失敗: {e}")
                    # 繼續發送下一球，不中斷訓練
                    continue
            
            # 訓練完成
            self._log_message(f"✅ {machine_id} 訓練完成")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 訓練執行失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    def _execute_training_sync(self, machine_id: str, section: str, program: str, ball_count: int, interval: float):
        """同步執行三發球機訓練（優化版本）"""
        try:
            import threading
            import queue
            import asyncio
            import time
            
            result_queue = queue.Queue()
            
            def run_training_in_thread():
                try:
                    # 創建新的事件循環
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    # 運行訓練
                    result = new_loop.run_until_complete(
                        self._execute_training_async_sync(machine_id, section, program, ball_count, interval)
                    )
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    try:
                        new_loop.close()
                    except:
                        pass
            
            # 在後台線程中運行訓練
            training_thread = threading.Thread(target=run_training_in_thread, daemon=True)
            training_thread.start()
            
            # 等待結果（最多等待訓練時間 + 30秒緩衝）
            max_wait_time = ball_count * interval + 30
            try:
                status, result = result_queue.get(timeout=max_wait_time)
                if status == 'error':
                    self._log_message(f"❌ {machine_id} 同步訓練失敗: {result}")
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_training_status(False)
            except queue.Empty:
                self._log_message(f"❌ {machine_id} 訓練超時")
                widget = self.machine_widgets.get(machine_id)
                if widget:
                    widget.update_training_status(False)
                    
        except Exception as e:
            self._log_message(f"❌ {machine_id} 同步訓練錯誤: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    async def _execute_training_async_sync(self, machine_id: str, section: str, program: str, ball_count: int, interval: float):
        """同步訓練專用的異步執行方法"""
        try:
            import asyncio
            
            device_info = self.connected_devices[machine_id]
            client = device_info.get('client')
            
            if not client or not client.is_connected:
                self._log_message(f"❌ {machine_id} 藍牙連接已斷開")
                return
            
            # 發送訓練指令
            for i in range(ball_count):
                try:
                    # 創建發球指令
                    command = self._create_shot_command(section)
                    
                    # 發送指令
                    write_char_uuid = "0000ff01-0000-1000-8000-00805f9b34fb"
                    await client.write_gatt_char(write_char_uuid, command)
                    
                    # 更新進度
                    widget = self.machine_widgets.get(machine_id)
                    if widget:
                        widget.update_training_status(True, program, i + 1, ball_count, "訓練中")
                    
                    self._log_message(f"🎯 {machine_id} 發球 {i + 1}/{ball_count}: {program}")
                    
                    # 等待間隔時間
                    if i < ball_count - 1:  # 最後一球不需要等待
                        await asyncio.sleep(interval)
                        
                except Exception as e:
                    self._log_message(f"❌ {machine_id} 第 {i + 1} 球發送失敗: {e}")
                    break
            
            # 訓練完成
            self._log_message(f"✅ {machine_id} 訓練完成")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
                
        except Exception as e:
            self._log_message(f"❌ {machine_id} 訓練執行失敗: {e}")
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
    
    def _create_shot_command(self, section: str) -> bytes:
        """創建發球指令"""
        try:
            # 使用commands.py中的get_area_params函數獲取參數
            from commands import get_area_params, create_shot_command
            
            # 獲取section對應的參數
            params = get_area_params(section, "section", "config/area.json")
            if params:
                # 使用參數創建發球指令
                command = create_shot_command(
                    speed=params['speed'],
                    horizontal_angle=params['horizontal_angle'],
                    vertical_angle=params['vertical_angle'],
                    height=params['height']
                )
                self._log_message(f"✅ 使用section {section}的發球參數: speed={params['speed']}, h_angle={params['horizontal_angle']}, v_angle={params['vertical_angle']}, height={params['height']}")
                return command
            else:
                self._log_message(f"⚠️ 找不到section {section}的發球參數，使用預設指令")
                # 使用預設參數
                return create_shot_command(speed=2, horizontal_angle=0, vertical_angle=50, height=0)
            
        except Exception as e:
            self._log_message(f"❌ 創建發球指令失敗: {e}")
            # 返回預設指令
            try:
                from commands import create_shot_command
                return create_shot_command(speed=2, horizontal_angle=0, vertical_angle=50, height=0)
            except:
                return b'\x01\x02\x00\x32\x00'
    
    def _on_pause_training(self, machine_id: str):
        """暫停指定發球機訓練"""
        self._log_message(f"⏸️ {machine_id} 暫停訓練")
        
        try:
            # 設置暫停標誌
            if machine_id not in self.training_stop_flags:
                self.training_stop_flags[machine_id] = False
            
            # 設置暫停狀態
            if not hasattr(self, 'training_pause_flags'):
                self.training_pause_flags = {}
            self.training_pause_flags[machine_id] = True
            
            # 更新界面狀態
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(True, widget.current_program, widget.current_progress, widget.total_balls, "已暫停")
            
            self._log_message(f"✅ {machine_id} 訓練已暫停")
            
        except Exception as e:
            self._log_message(f"❌ {machine_id} 暫停訓練錯誤: {e}")
    
    def _on_resume_training(self, machine_id: str):
        """恢復指定發球機訓練"""
        self._log_message(f"▶️ {machine_id} 恢復訓練")
        
        try:
            # 清除暫停標誌
            if hasattr(self, 'training_pause_flags') and machine_id in self.training_pause_flags:
                self.training_pause_flags[machine_id] = False
            
            # 更新界面狀態
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(True, widget.current_program, widget.current_progress, widget.total_balls, "訓練中")
            
            self._log_message(f"✅ {machine_id} 訓練已恢復")
            
        except Exception as e:
            self._log_message(f"❌ {machine_id} 恢復訓練錯誤: {e}")
    
    def _on_stop_training(self, machine_id: str):
        """停止指定發球機訓練"""
        self._log_message(f"⏹️ {machine_id} 停止訓練")
        
        try:
            # 設置停止標誌
            if machine_id in self.training_stop_flags:
                self.training_stop_flags[machine_id] = True
            
            # 更新界面狀態
            widget = self.machine_widgets.get(machine_id)
            if widget:
                widget.update_training_status(False)
            
            self._log_message(f"✅ {machine_id} 訓練停止指令已發送")
            
        except Exception as e:
            self._log_message(f"❌ {machine_id} 停止訓練錯誤: {e}")
    
    def _log_message(self, message: str):
        """記錄日誌訊息"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_text.append(log_entry)
        
        # 限制日誌行數並自動滾動
        if self.log_text.document().blockCount() > 50:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 5)
            cursor.removeSelectedText()
        
        self.log_text.moveCursor(self.log_text.textCursor().End)
        
        # 同時記錄到主GUI
        if hasattr(self.gui, 'log_message'):
            self.gui.log_message(message)
    
    def update_machine_status(self, machine_id: str, connected: bool, training: bool = False, 
                            program: str = "", current: int = 0, total: int = 0):
        """更新發球機狀態"""
        widget = self.machine_widgets.get(machine_id)
        if widget:
            widget.update_connection_status(connected)
            widget.update_training_status(training, program, current, total)


def create_three_machine_tab(self):
    """創建三發球機簡易控制標籤頁"""
    try:
        three_machine_widget = ThreeMachineSimpleWidget(self)
        # 移除固定尺寸限制，讓界面更靈活
        three_machine_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.tab_widget.addTab(three_machine_widget, "🏸 三發球機")
        self.log_message("✅ 三發球機簡易控制界面已載入")
        
    except Exception as e:
        self.log_message(f"❌ 三發球機簡易控制界面載入失敗: {e}")

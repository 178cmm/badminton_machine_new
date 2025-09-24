"""
模擬對打模式 UI 模組

這個模組負責創建模擬對打模式的用戶界面。
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QGroupBox, QGridLayout,
                             QSpinBox, QCheckBox, QTextEdit, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from core.services.device_service import DeviceService
from PyQt5.QtGui import QFont, QPixmap, QPalette


def create_simulation_tab(self):
    """
    創建模擬對打模式標籤頁
    """
    # 創建主容器
    simulation_widget = QWidget()
    simulation_widget.setObjectName("simulation_widget")
    
    # 主布局
    main_layout = QVBoxLayout(simulation_widget)
    main_layout.setSpacing(10)  # 減少間距以節省空間
    main_layout.setContentsMargins(10, 10, 10, 10)  # 減少邊距
    
    # 創建滾動區域以防止內容溢出
    from PyQt5.QtWidgets import QScrollArea
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    scroll_layout.setSpacing(15)
    scroll_layout.setContentsMargins(10, 10, 10, 10)
    
    # AI風格標題
    title_label = QLabel("🤖 AI SIMULATION MODE • 智能模擬對打系統")
    title_label.setObjectName("title_label")
    title_label.setAlignment(Qt.AlignCenter)
    title_label.setStyleSheet("""
        QLabel {
            font-size: 22px;
            font-weight: bold;
            color: #ffffff;
            padding: 16px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(0, 255, 136, 0.3), stop:0.5 rgba(0, 212, 255, 0.2), stop:1 rgba(0, 255, 136, 0.3));
            border-radius: 12px;
            border: 3px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #00ff88, stop:0.5 #00d4ff, stop:1 #00ff88);
            letter-spacing: 1px;
        }
    """)
    scroll_layout.addWidget(title_label)
    
    # AI風格說明文字
    description_label = QLabel("🧠 AI 智能分析您的技能等級，自動調整發球策略、難度係數和時間間隔，提供最佳訓練體驗")
    description_label.setObjectName("description_label")
    description_label.setAlignment(Qt.AlignCenter)
    description_label.setWordWrap(True)  # 允許文字換行
    description_label.setStyleSheet("""
        QLabel {
            font-size: 13px;
            color: #e0e6ff;
            padding: 12px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 212, 255, 0.1), stop:1 rgba(0, 255, 136, 0.05));
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.3);
            font-weight: 500;
        }
    """)
    scroll_layout.addWidget(description_label)
    
    # 等級選擇區域
    level_group = _create_level_selection_group(self)
    scroll_layout.addWidget(level_group)
    
    # 設定區域
    settings_group = _create_settings_group(self)
    scroll_layout.addWidget(settings_group)
    
    # 控制按鈕區域
    control_group = _create_control_group(self)
    scroll_layout.addWidget(control_group)
    
    # 狀態顯示區域
    status_group = _create_status_group(self)
    scroll_layout.addWidget(status_group)
    
    # 添加彈性空間
    scroll_layout.addStretch()
    
    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    main_layout.addWidget(scroll_area)
    
    # 連接事件
    connect_simulation_events(self)
    
    # 將標籤頁添加到主標籤組件
    self.tab_widget.addTab(simulation_widget, "模擬對打")


def _create_level_selection_group(self):
    """創建等級選擇區域"""
    group = QGroupBox("🎮 AI SKILL LEVEL • 智能技能等級選擇")
    group.setObjectName("level_group")
    group.setStyleSheet("""
        QGroupBox {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            border: 2px solid #555555;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 15px;
            background-color: #3c3c3c;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 10px 0 10px;
            color: #4CAF50;
        }
    """)
    
    layout = QVBoxLayout(group)
    layout.setSpacing(15)
    
    # 等級選擇器
    level_layout = QHBoxLayout()
    
    level_label = QLabel("選擇等級:")
    level_label.setObjectName("level_label")
    level_label.setStyleSheet("""
        QLabel {
            font-size: 14px;
            color: #ffffff;
            font-weight: bold;
        }
    """)
    level_layout.addWidget(level_label)
    
    self.simulation_level_combo = QComboBox()
    self.simulation_level_combo.setObjectName("simulation_level_combo")
    self.simulation_level_combo.setStyleSheet("""
        QComboBox {
            padding: 8px;
            border: 2px solid #555555;
            border-radius: 5px;
            font-size: 14px;
            background-color: #2b2b2b;
            color: #ffffff;
            min-width: 200px;
        }
        QComboBox:hover {
            border-color: #4CAF50;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #ffffff;
            margin-right: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555555;
            selection-background-color: #4CAF50;
        }
    """)
    
    # 添加等級選項
    _populate_level_combo(self.simulation_level_combo)
    level_layout.addWidget(self.simulation_level_combo)
    level_layout.addStretch()
    
    layout.addLayout(level_layout)
    
    # 等級詳細信息
    self.simulation_level_info = QTextEdit()
    self.simulation_level_info.setObjectName("simulation_level_info")
    self.simulation_level_info.setMaximumHeight(80)  # 減少高度以適應小螢幕
    self.simulation_level_info.setMinimumHeight(60)
    self.simulation_level_info.setReadOnly(True)
    self.simulation_level_info.setStyleSheet("""
        QTextEdit {
            background-color: #2b2b2b;
            color: #cccccc;
            border: 1px solid #555555;
            border-radius: 5px;
            padding: 10px;
            font-size: 12px;
        }
    """)
    
    # 連接等級選擇事件
    self.simulation_level_combo.currentTextChanged.connect(
        lambda: _update_level_info(self)
    )
    
    layout.addWidget(self.simulation_level_info)
    
    return group


def _create_settings_group(self):
    """創建設定區域"""
    group = QGroupBox("⚙️ ADVANCED CONFIG • AI 進階配置")
    group.setObjectName("settings_group")
    group.setStyleSheet("""
        QGroupBox {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            border: 2px solid #555555;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 15px;
            background-color: #3c3c3c;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 10px 0 10px;
            color: #4CAF50;
        }
    """)
    
    layout = QGridLayout(group)
    layout.setSpacing(15)
    
    # 雙發球機選項
    self.simulation_dual_machine_check = QCheckBox("🤖 使用雙發球機模式")
    self.simulation_dual_machine_check.setObjectName("simulation_dual_machine_check")
    self.simulation_dual_machine_check.setStyleSheet("""
        QCheckBox {
            font-size: 14px;
            color: #ffffff;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            border: 2px solid #555555;
            background-color: #2b2b2b;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            border: 2px solid #ff9800;
            background-color: #ff9800;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked:after {
            color: white;
            font-weight: bold;
        }
    """)
    self.simulation_dual_machine_check.setEnabled(True)  # 啟用雙發球機選項
    layout.addWidget(self.simulation_dual_machine_check, 0, 0, 1, 2)
    
    # 自定義間隔時間
    interval_label = QLabel("自定義間隔時間 (秒):")
    interval_label.setObjectName("interval_label")
    interval_label.setStyleSheet("""
        QLabel {
            font-size: 14px;
            color: #ffffff;
            font-weight: bold;
        }
    """)
    layout.addWidget(interval_label, 1, 0)
    
    self.simulation_custom_interval = QSpinBox()
    self.simulation_custom_interval.setObjectName("simulation_custom_interval")
    self.simulation_custom_interval.setRange(1, 10)
    self.simulation_custom_interval.setValue(2)
    self.simulation_custom_interval.setSuffix(" 秒")
    self.simulation_custom_interval.setStyleSheet("""
        QSpinBox {
            padding: 8px;
            border: 2px solid #555555;
            border-radius: 5px;
            font-size: 14px;
            background-color: #2b2b2b;
            color: #ffffff;
            min-width: 100px;
        }
        QSpinBox:hover {
            border-color: #4CAF50;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #4CAF50;
            border: none;
            width: 20px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #45a049;
        }
    """)
    self.simulation_custom_interval.setEnabled(False)  # 暫時禁用
    layout.addWidget(self.simulation_custom_interval, 1, 1)
    
    return group


def _create_control_group(self):
    """創建控制按鈕區域"""
    group = QGroupBox("🚀 MISSION CONTROL • AI 任務控制中心")
    group.setObjectName("control_group")
    group.setStyleSheet("""
        QGroupBox {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            border: 2px solid #555555;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 15px;
            background-color: #3c3c3c;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 10px 0 10px;
            color: #4CAF50;
        }
    """)
    
    layout = QHBoxLayout(group)
    layout.setSpacing(20)
    
    # 開始按鈕
    self.simulation_start_button = QPushButton("🚀 開始模擬對打")
    self.simulation_start_button.setObjectName("simulation_start_button")
    self.simulation_start_button.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            min-width: 150px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QPushButton:disabled {
            background-color: #555555;
            color: #888888;
        }
    """)
    layout.addWidget(self.simulation_start_button)
    
    # 停止按鈕
    self.simulation_stop_button = QPushButton("🛑 停止對打")
    self.simulation_stop_button.setObjectName("simulation_stop_button")
    self.simulation_stop_button.setStyleSheet("""
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            min-width: 150px;
        }
        QPushButton:hover {
            background-color: #da190b;
        }
        QPushButton:pressed {
            background-color: #c1170b;
        }
        QPushButton:disabled {
            background-color: #555555;
            color: #888888;
        }
    """)
    self.simulation_stop_button.setEnabled(False)
    layout.addWidget(self.simulation_stop_button)
    
    return group


def _create_status_group(self):
    """創建狀態顯示區域"""
    group = QGroupBox("📊 SYSTEM STATUS • AI 系統狀態監控")
    group.setObjectName("status_group")
    group.setStyleSheet("""
        QGroupBox {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            border: 2px solid #555555;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 15px;
            background-color: #3c3c3c;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 10px 0 10px;
            color: #4CAF50;
        }
    """)
    
    layout = QVBoxLayout(group)
    layout.setSpacing(10)
    
    # 當前狀態
    status_layout = QHBoxLayout()
    
    status_label = QLabel("當前狀態:")
    status_label.setObjectName("status_label")
    status_label.setStyleSheet("""
        QLabel {
            font-size: 14px;
            color: #ffffff;
            font-weight: bold;
        }
    """)
    status_layout.addWidget(status_label)
    
    self.simulation_status_label = QLabel("待機中")
    self.simulation_status_label.setObjectName("simulation_status_label")
    self.simulation_status_label.setStyleSheet("""
        QLabel {
            font-size: 14px;
            color: #ff9800;
            font-weight: bold;
            padding: 5px 10px;
            background-color: rgba(255, 152, 0, 0.2);
            border-radius: 5px;
            border: 1px solid #ff9800;
        }
    """)
    status_layout.addWidget(self.simulation_status_label)
    status_layout.addStretch()
    
    layout.addLayout(status_layout)
    
    # 統計信息
    stats_layout = QHBoxLayout()
    
    self.simulation_stats_label = QLabel("發球次數: 0 | 運行時間: 00:00")
    self.simulation_stats_label.setObjectName("simulation_stats_label")
    self.simulation_stats_label.setStyleSheet("""
        QLabel {
            font-size: 12px;
            color: #cccccc;
            padding: 5px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
        }
    """)
    stats_layout.addWidget(self.simulation_stats_label)
    stats_layout.addStretch()
    
    layout.addLayout(stats_layout)
    
    return group


def _populate_level_combo(combo):
    """填充等級選擇器"""
    levels = [
        ("等級 1 - 初學者", 1, "全部高球，間隔 3 秒"),
        ("等級 2 - 初學者+", 2, "全部高球，間隔 2.5 秒"),
        ("等級 3 - 中級", 3, "後高前低，間隔 2.5 秒"),
        ("等級 4 - 中級+", 4, "後高前低，間隔 2 秒"),
        ("等級 5 - 中高級", 5, "後高前低，間隔 2 秒"),
        ("等級 6 - 中高級+", 6, "後高前低，間隔 1.5 秒"),
        ("等級 7 - 高級", 7, "後高中殺前低，間隔 1.5 秒"),
        ("等級 8 - 高級+", 8, "後高中殺前低，間隔 1 秒"),
        ("等級 9 - 專業級", 9, "後高中殺前低，間隔 2 秒 (推薦雙發球機)"),
        ("等級 10 - 專業級+", 10, "後高中殺前低，間隔 1.5 秒 (推薦雙發球機)"),
        ("等級 11 - 大師級", 11, "後高中殺前低，間隔 1.5 秒 (強烈推薦雙發球機)"),
        ("等級 12 - 大師級+", 12, "後高中殺前低，間隔 1 秒 (強烈推薦雙發球機)")
    ]
    
    for display_text, level, description in levels:
        combo.addItem(display_text, level)


def _update_level_info(self):
    """更新等級詳細信息"""
    if not hasattr(self, 'simulation_level_combo'):
        return
    
    current_data = self.simulation_level_combo.currentData()
    if current_data:
        level = current_data
        descriptions = {
            1: "初學者等級 - 全部高球，間隔 3 秒\n適合剛開始學習羽毛球的初學者\n支援單/雙發球機模式",
            2: "初學者+等級 - 全部高球，間隔 2.5 秒\n適合有一定基礎的初學者\n支援單/雙發球機模式",
            3: "中級等級 - 後高前低，間隔 2.5 秒\n開始練習不同球路組合\n支援單/雙發球機模式",
            4: "中級+等級 - 後高前低，間隔 2 秒\n提升反應速度和球路變化\n支援單/雙發球機模式",
            5: "中高級等級 - 後高前低，間隔 2 秒\n進一步提升技術水平\n支援單/雙發球機模式",
            6: "中高級+等級 - 後高前低，間隔 1.5 秒\n接近高級水平的訓練\n支援單/雙發球機模式",
            7: "高級等級 - 後高中殺前低，間隔 1.5 秒\n包含殺球的高強度訓練\n支援單/雙發球機模式",
            8: "高級+等級 - 後高中殺前低，間隔 1 秒\n高強度快速反應訓練\n支援單/雙發球機模式",
            9: "專業級等級 - 後高中殺前低，間隔 2 秒\n專業級訓練，推薦使用雙發球機\n雙發球機交替發球，提升真實感",
            10: "專業級+等級 - 後高中殺前低，間隔 1.5 秒\n專業級高強度訓練\n雙發球機模式提供更豐富的球路變化",
            11: "大師級等級 - 後高中殺前低，間隔 1.5 秒\n大師級訓練，強烈推薦雙發球機\n雙發球機協調發球，模擬真實對戰",
            12: "大師級+等級 - 後高中殺前低，間隔 1 秒\n最高等級訓練，極限挑戰\n雙發球機模式提供最真實的對戰體驗"
        }
        
        description = descriptions.get(level, "未知等級")
        self.simulation_level_info.setText(description)


def connect_simulation_events(self):
    """
    連接模擬對打模式的事件
    
    Args:
        parent: 父窗口實例
    """
    # 連接按鈕事件
    if hasattr(self, 'simulation_start_button'):
        self.simulation_start_button.clicked.connect(
            lambda: start_simulation_training(self)
        )
    
    if hasattr(self, 'simulation_stop_button'):
        self.simulation_stop_button.clicked.connect(
            lambda: stop_simulation_training(self)
        )


def start_simulation_training(self):
    """
    開始模擬對打訓練
    
    Args:
        parent: 父窗口實例
    """
    try:
        # 檢查連接狀態（統一 DeviceService）
        if not hasattr(self, 'device_service'):
            self.device_service = DeviceService(self, simulate=False)
        if not self.device_service.is_connected():
            self.log_message("❌ 請先連接發球機")
            return
        
        # 獲取選擇的等級
        if not hasattr(self, 'simulation_level_combo'):
            self.log_message("❌ 無法獲取等級選擇")
            return
        
        level = self.simulation_level_combo.currentData()
        if not level:
            self.log_message("❌ 請選擇對打等級")
            return
        
        # 檢查是否使用雙發球機
        use_dual = False
        if hasattr(self, 'simulation_dual_machine_check'):
            use_dual = self.simulation_dual_machine_check.isChecked()
        
        # 如果選擇雙發球機模式，檢查雙發球機連接狀態
        if use_dual:
            if not hasattr(self, 'dual_bluetooth_manager') or not self.dual_bluetooth_manager:
                self.log_message("❌ 雙發球機管理器未初始化")
                return
            
            if not self.dual_bluetooth_manager.is_dual_connected():
                self.log_message("❌ 雙發球機未完全連接，請先在連接設定中連接雙發球機")
                return
        
        # 創建模擬對打執行器
        if not hasattr(self, 'simulation_executor'):
            from core.executors.simulation_executor import create_simulation_executor
            self.simulation_executor = create_simulation_executor(self)
        
        # 開始模擬對打
        success = self.simulation_executor.start_simulation(level, use_dual)
        
        if success:
            # 更新UI狀態
            if hasattr(self, 'simulation_start_button'):
                self.simulation_start_button.setEnabled(False)
            if hasattr(self, 'simulation_stop_button'):
                self.simulation_stop_button.setEnabled(True)
            
            update_simulation_status(self, "運行中", "發球次數: 0 | 運行時間: 00:00")
            self.log_message(f"✅ 模擬對打已開始 - 等級 {level}")
        else:
            self.log_message("❌ 開始模擬對打失敗")
            
    except Exception as e:
        self.log_message(f"❌ 開始模擬對打時發生錯誤: {e}")


def stop_simulation_training(self):
    """
    停止模擬對打訓練
    
    Args:
        parent: 父窗口實例
    """
    try:
        # 停止模擬對打
        if hasattr(self, 'simulation_executor'):
            success = self.simulation_executor.stop_simulation()
            
            if success:
                # 更新UI狀態
                if hasattr(self, 'simulation_start_button'):
                    self.simulation_start_button.setEnabled(True)
                if hasattr(self, 'simulation_stop_button'):
                    self.simulation_stop_button.setEnabled(False)
                
                update_simulation_status(self, "已停止", "發球次數: 0 | 運行時間: 00:00")
                self.log_message("✅ 模擬對打已停止")
            else:
                self.log_message("❌ 停止模擬對打失敗")
        else:
            self.log_message("❌ 沒有正在運行的模擬對打")
            
    except Exception as e:
        self.log_message(f"❌ 停止模擬對打時發生錯誤: {e}")


def update_simulation_status(self, status: str, stats: str = ""):
    """
    更新模擬對打狀態
    
    Args:
        parent: 父窗口實例
        status: 狀態文字
        stats: 統計信息
    """
    if hasattr(self, 'simulation_status_label'):
        self.simulation_status_label.setText(status)
        
        # 根據狀態更新顏色
        if "運行中" in status or "對打中" in status or "雙發球機" in status:
            self.simulation_status_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #4CAF50;
                    font-weight: bold;
                    padding: 5px 10px;
                    background-color: rgba(76, 175, 80, 0.2);
                    border-radius: 5px;
                    border: 1px solid #4CAF50;
                }
            """)
        elif "停止" in status or "結束" in status:
            self.simulation_status_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #f44336;
                    font-weight: bold;
                    padding: 5px 10px;
                    background-color: rgba(244, 67, 54, 0.2);
                    border-radius: 5px;
                    border: 1px solid #f44336;
                }
            """)
        else:
            self.simulation_status_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #ff9800;
                    font-weight: bold;
                    padding: 5px 10px;
                    background-color: rgba(255, 152, 0, 0.2);
                    border-radius: 5px;
                    border: 1px solid #ff9800;
                }
            """)
    
    if hasattr(self, 'simulation_stats_label') and stats:
        self.simulation_stats_label.setText(stats)

"""
UI Simulate 解析面板
僅在 simulate 模式下顯示，用於 demo 與除錯
"""

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QGroupBox, QScrollArea,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from core.audit import AuditReader


def create_simulate_panel(self):
    """創建 simulate 解析面板"""
    # 只在 simulate 模式下顯示
    if not os.environ.get("SIMULATE", "").lower() in ["true", "1", "yes"]:
        return None
    
    panel_widget = QWidget()
    layout = QVBoxLayout(panel_widget)
    
    # 標題
    title = QLabel("🔍 Simulate 解析面板")
    title.setStyleSheet("""
        font-size: 16px; 
        font-weight: bold; 
        color: #ffffff; 
        padding: 12px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 193, 7, 0.3), stop:0.5 rgba(255, 152, 0, 0.2), stop:1 rgba(255, 193, 7, 0.3));
        border-radius: 8px;
        border: 2px solid #ffc107;
    """)
    layout.addWidget(title)
    
    # 說明
    info_label = QLabel("此面板僅在 SIMULATE=true 時顯示，用於除錯和 demo")
    info_label.setStyleSheet("color: #ffc107; font-size: 12px; padding: 8px;")
    layout.addWidget(info_label)
    
    # 控制按鈕
    control_layout = QHBoxLayout()
    
    self.simulate_refresh_btn = QPushButton("🔄 重新整理")
    self.simulate_refresh_btn.setStyleSheet("""
        QPushButton {
            background-color: #ffc107;
            color: #000000;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #ffb300;
        }
    """)
    control_layout.addWidget(self.simulate_refresh_btn)
    
    self.simulate_clear_btn = QPushButton("🗑️ 清空日誌")
    self.simulate_clear_btn.setStyleSheet("""
        QPushButton {
            background-color: #f44336;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #d32f2f;
        }
    """)
    control_layout.addWidget(self.simulate_clear_btn)
    
    layout.addLayout(control_layout)
    
    # 最新指令摘要
    latest_group = QGroupBox("📋 最新指令摘要")
    latest_layout = QVBoxLayout(latest_group)
    
    self.simulate_latest_text = QTextEdit()
    self.simulate_latest_text.setReadOnly(True)
    self.simulate_latest_text.setMaximumHeight(150)
    self.simulate_latest_text.setStyleSheet("""
        QTextEdit {
            background-color: rgba(0, 0, 0, 0.8);
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
        }
    """)
    latest_layout.addWidget(self.simulate_latest_text)
    layout.addWidget(latest_group)
    
    # 統計資訊
    stats_group = QGroupBox("📊 統計資訊")
    stats_layout = QVBoxLayout(stats_group)
    
    self.simulate_stats_text = QTextEdit()
    self.simulate_stats_text.setReadOnly(True)
    self.simulate_stats_text.setMaximumHeight(120)
    self.simulate_stats_text.setStyleSheet("""
        QTextEdit {
            background-color: rgba(0, 0, 0, 0.8);
            color: #4caf50;
            border: 1px solid #555;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
        }
    """)
    stats_layout.addWidget(self.simulate_stats_text)
    layout.addWidget(stats_group)
    
    # 最近活動表格
    activity_group = QGroupBox("📈 最近活動 (最近 5 分鐘)")
    activity_layout = QVBoxLayout(activity_group)
    
    self.simulate_activity_table = QTableWidget()
    self.simulate_activity_table.setColumnCount(6)
    self.simulate_activity_table.setHorizontalHeaderLabels([
        "時間", "來源", "指令", "類型", "結果", "服務"
    ])
    
    # 設定表格樣式
    self.simulate_activity_table.setStyleSheet("""
        QTableWidget {
            background-color: rgba(0, 0, 0, 0.8);
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 4px;
            gridline-color: #555;
        }
        QTableWidget::item {
            padding: 4px;
            border-bottom: 1px solid #333;
        }
        QHeaderView::section {
            background-color: #333;
            color: #ffffff;
            padding: 6px;
            border: 1px solid #555;
            font-weight: bold;
        }
    """)
    
    # 設定列寬
    header = self.simulate_activity_table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 時間
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 來源
    header.setSectionResizeMode(2, QHeaderView.Stretch)          # 指令
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # 類型
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # 結果
    header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # 服務
    
    activity_layout.addWidget(self.simulate_activity_table)
    layout.addWidget(activity_group)
    
    # 初始化審計讀取器
    self.audit_reader = AuditReader()
    
    # 綁定事件
    self.simulate_refresh_btn.clicked.connect(lambda: self._refresh_simulate_panel())
    self.simulate_clear_btn.clicked.connect(lambda: self._clear_simulate_logs())
    
    # 自動刷新計時器
    self.simulate_timer = QTimer()
    self.simulate_timer.timeout.connect(lambda: self._refresh_simulate_panel())
    self.simulate_timer.start(5000)  # 每 5 秒刷新一次
    
    # 初始載入
    self._refresh_simulate_panel()
    
    return panel_widget


def _refresh_simulate_panel(self):
    """刷新 simulate 面板"""
    try:
        # 更新最新指令摘要
        latest = self.audit_reader.get_latest_command()
        if latest:
            summary = self.audit_reader.get_command_summary(latest)
            latest_text = f"""時間: {summary['timestamp']}
來源: {summary['source']}
原始文字: {summary['raw_text']}
指令類型: {summary['command_type']}
指令內容: {summary['command_payload']}
NLU 規則: {summary['nlu_rule']}
路由狀態: {summary['router_state']}
目標服務: {summary['target_service']}
結果: {summary['result']}
錯誤: {summary['error']}"""
            self.simulate_latest_text.setText(latest_text)
        else:
            self.simulate_latest_text.setText("暫無指令記錄")
        
        # 更新統計資訊
        stats = self.audit_reader.get_statistics()
        stats_text = f"""總指令數: {stats['total_commands']}
成功率: {stats['success_rate']:.1f}%
錯誤數: {stats['error_count']}
常見指令: {', '.join([f'{cmd}({count})' for cmd, count in stats['common_commands']])}"""
        self.simulate_stats_text.setText(stats_text)
        
        # 更新最近活動表格
        recent_activity = self.audit_reader.get_recent_activity(5)
        self.simulate_activity_table.setRowCount(len(recent_activity))
        
        for i, activity in enumerate(recent_activity):
            # 格式化時間戳
            timestamp = activity['timestamp']
            if timestamp:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = timestamp[:8] if len(timestamp) > 8 else timestamp
            else:
                time_str = "N/A"
            
            self.simulate_activity_table.setItem(i, 0, QTableWidgetItem(time_str))
            self.simulate_activity_table.setItem(i, 1, QTableWidgetItem(activity['source']))
            self.simulate_activity_table.setItem(i, 2, QTableWidgetItem(activity['raw_text'][:30] + "..." if len(activity['raw_text']) > 30 else activity['raw_text']))
            self.simulate_activity_table.setItem(i, 3, QTableWidgetItem(activity['command_type']))
            
            # 結果顏色
            result_item = QTableWidgetItem(activity['result'])
            if activity['result'] == 'ok':
                result_item.setBackground(Qt.green)
            elif activity['result'] == 'error':
                result_item.setBackground(Qt.red)
            self.simulate_activity_table.setItem(i, 4, result_item)
            
            self.simulate_activity_table.setItem(i, 5, QTableWidgetItem(activity['target_service']))
        
    except Exception as e:
        print(f"⚠️ 刷新 simulate 面板失敗：{e}")


def _clear_simulate_logs(self):
    """清空 simulate 日誌"""
    try:
        log_file = "logs/commands.jsonl"
        if os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("")
            self.simulate_latest_text.setText("日誌已清空")
            self.simulate_stats_text.setText("統計已重置")
            self.simulate_activity_table.setRowCount(0)
            print("✅ Simulate 日誌已清空")
    except Exception as e:
        print(f"⚠️ 清空日誌失敗：{e}")

# Auto-split UI module from gui_text.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QPushButton


def create_log_tab(self):
    """創建日誌標籤頁"""
    log_widget = QWidget()
    layout = QVBoxLayout(log_widget)
    
    # 日誌顯示
    self.log_text = QTextEdit()
    self.log_text.setReadOnly(True)
    layout.addWidget(QLabel("系統日誌:"))
    layout.addWidget(self.log_text)
    
    # 清除日誌按鈕
    clear_button = QPushButton("🗑️ 清除日誌")
    clear_button.clicked.connect(self.log_text.clear)
    layout.addWidget(clear_button)
    
    self.tab_widget.addTab(log_widget, "系統日誌")


def log_message(self, message):
    """記錄日誌"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    self.log_text.append(line)
    self.log_text.ensureCursorVisible()
    # 若文本控制頁面存在聊天視窗，鏡像輸出到同頁聊天區
    try:
        if hasattr(self, 'text_chat_log') and self.text_chat_log is not None:
            self.text_chat_log.append(f"系統: {message}")
            self.text_chat_log.ensureCursorVisible()
    except Exception:
        pass


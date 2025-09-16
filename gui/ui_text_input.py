from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit
import sys
import os
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.executors import create_text_command_executor


def create_text_input_tab(self):
    """創建文本輸入控制標籤頁"""
    text_input_widget = QWidget()
    layout = QVBoxLayout(text_input_widget)
    
    # 創建滾動區域以防止內容溢出
    from PyQt5.QtWidgets import QScrollArea
    from PyQt5.QtCore import Qt
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)

    # AI風格標題
    title_label = QLabel("💬 AI TEXT COMMANDER • 智能文字指令系統")
    title_label.setAlignment(Qt.AlignCenter)
    title_label.setStyleSheet("""
        font-size: 18px;
        font-weight: bold;
        color: #ffffff;
        padding: 14px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 20, 147, 0.3), stop:0.5 rgba(199, 21, 133, 0.2), stop:1 rgba(255, 20, 147, 0.3));
        border-radius: 10px;
        border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #ff1493, stop:0.5 #c71585, stop:1 #ff1493);
        letter-spacing: 1px;
        margin-bottom: 10px;
    """)
    scroll_layout.addWidget(title_label)

    # 對話/日誌視窗（同頁顯示用戶輸入與系統/發球機回饋）
    chat_label = QLabel("🤖 AI 對話終端")
    chat_label.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 14px; margin-top: 10px;")
    scroll_layout.addWidget(chat_label)
    self.text_chat_log = QTextEdit()
    self.text_chat_log.setReadOnly(True)
    self.text_chat_log.setMinimumHeight(120)  # 減少最小高度以適應小螢幕
    self.text_chat_log.setStyleSheet("""
        QTextEdit {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 0, 0, 0.9), stop:1 rgba(0, 212, 255, 0.05));
            color: #00ff88;
            font-family: 'Consolas', 'Monaco', monospace;
            border: 2px solid #00ff88;
            border-radius: 8px;
            padding: 8px;
        }
    """)
    scroll_layout.addWidget(self.text_chat_log)

    # AI風格提示標籤
    instruction_label = QLabel(
        "🧠 AI 自然語言處理引擎，理解您的指令意圖：\n"
        "• 正手高遠球 20顆 每3秒\n"
        "• 開始熱身 進階 速度快\n"
        "• 開始進階訓練 XXX課程 速度正常 球數20顆\n"
        "• 掃描發球機 / 連接 / 斷開 / 停止訓練\n"
        "• 開始訓練 速度快 球數20顆"
    )
    instruction_label.setStyleSheet("color: #ffffff; font-size: 12px;")  # 稍微縮小字體
    instruction_label.setWordWrap(True)  # 允許文字換行
    scroll_layout.addWidget(instruction_label)

    # AI指令輸入區
    input_label = QLabel("⚡ AI 指令輸入")
    input_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 14px; margin-top: 15px;")
    scroll_layout.addWidget(input_label)
    
    self.text_input = QLineEdit()
    self.text_input.setPlaceholderText("🤖 輸入自然語言指令... 例如：正手高遠球 20顆 每3秒")
    self.text_input.setStyleSheet("""
        QLineEdit {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 212, 255, 0.15), stop:1 rgba(0, 153, 204, 0.08));
            color: #ffffff;
            font-size: 14px;
            padding: 12px 16px;
            border: 2px solid #00d4ff;
            border-radius: 10px;
            font-weight: 500;
        }
        QLineEdit:focus {
            border: 2px solid #33ddff;
        }
    """)
    # 連接Enter鍵事件
    self.text_input.returnPressed.connect(self.execute_text_command)
    scroll_layout.addWidget(self.text_input)

    self.execute_button = QPushButton("🚀 AI 執行指令")
    self.execute_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ff1493, stop:0.5 #c71585, stop:1 #ff1493);
            color: #ffffff;
            border: 2px solid #ff1493;
            padding: 12px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ff69b4, stop:0.5 #da70d6, stop:1 #ff69b4);
            border: 2px solid #ff69b4;
        }
    """)
    self.execute_button.clicked.connect(self.execute_text_command)
    scroll_layout.addWidget(self.execute_button)

    # 建立命令執行器
    self.text_command_executor = create_text_command_executor(self)

    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    layout.addWidget(scroll_area)

    self.tab_widget.addTab(text_input_widget, "文本控制")

def execute_text_command(self):
    """執行文字命令（UI 層面的處理）"""
    command_text = (self.text_input.text() or "").strip()
    
    # 清空輸入框
    self.text_input.clear()
    
    # 使用命令執行器處理命令
    self.text_command_executor.execute_text_command(command_text)

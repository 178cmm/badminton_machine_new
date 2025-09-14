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

    # 對話/日誌視窗（同頁顯示用戶輸入與系統/發球機回饋）
    layout.addWidget(QLabel("對話"))
    self.text_chat_log = QTextEdit()
    self.text_chat_log.setReadOnly(True)
    self.text_chat_log.setMinimumHeight(180)
    layout.addWidget(self.text_chat_log)

    # 新增提示標籤（提供多種語句風格範例）
    instruction_label = QLabel(
        "您可以直接用一句話控制，例如：\n"
        "- 正手高遠球 20顆 每3秒\n"
        "- 開始熱身 進階 速度快\n"
        "- 開始進階訓練 XXX課程 速度正常 球數20顆\n"
        "- 掃描發球機 / 連接 / 斷開 / 停止訓練\n"
        "- 開始訓練 速度快 球數20顆"
    )
    instruction_label.setStyleSheet("color: #ffffff; font-size: 14px;")
    layout.addWidget(instruction_label)

    self.text_input = QLineEdit()
    self.text_input.setPlaceholderText("例如：正手高遠球 20顆 每3秒 / 開始熱身 進階 速度快 / 掃描發球機")
    layout.addWidget(QLabel("輸入指令: "))
    layout.addWidget(self.text_input)

    self.execute_button = QPushButton("執行指令")
    self.execute_button.clicked.connect(self.execute_text_command)
    layout.addWidget(self.execute_button)

    # 建立命令執行器
    self.text_command_executor = create_text_command_executor(self)

    self.tab_widget.addTab(text_input_widget, "文本控制")

def execute_text_command(self):
    """執行文字命令（UI 層面的處理）"""
    command_text = (self.text_input.text() or "").strip()
    
    # 清空輸入框
    self.text_input.clear()
    
    # 使用命令執行器處理命令
    self.text_command_executor.execute_text_command(command_text)

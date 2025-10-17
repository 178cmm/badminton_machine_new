"""
AI教練界面模組

提供專門的AI教練對話界面，讓用戶可以與語言模型進行文字溝通，
獲得專業的羽球技術指導和建議。
"""

import asyncio
import json
import time
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QLineEdit, QGroupBox,
                             QScrollArea, QComboBox, QCheckBox, QFrame,
                             QSplitter, QTabWidget, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, QEvent
from PyQt5.QtGui import QFont, QPixmap, QPalette, QTextCursor
import sys
import os

# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audit.audit_reader import AuditReader
from scripts.voice_control_tts import VoiceControlTTS, VoiceConfig


class AICoachWorker(QThread):
    """AI教練工作線程"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, user_input, voice_control, audit_reader):
        super().__init__()
        self.user_input = user_input
        self.voice_control = voice_control
        self.audit_reader = audit_reader
    
    def run(self):
        """執行AI教練回覆生成"""
        try:
            # 獲取用戶訓練數據
            recent_activity = self.audit_reader.get_recent_activity(minutes=60)
            training_prefs = self._analyze_training_preferences()
            
            # 構建上下文
            context = self._build_context(recent_activity, training_prefs)
            
            # 生成AI教練回覆
            response = asyncio.run(self._generate_coach_response(context))
            self.response_ready.emit(response)
            
        except Exception as e:
            self.error_occurred.emit(f"AI教練回覆生成失敗：{str(e)}")
    
    def _analyze_training_preferences(self):
        """分析用戶訓練偏好"""
        entries = self.audit_reader.get_latest_entries(50)
        
        preferences = {
            "favorite_programs": [],
            "training_frequency": 0,
            "preferred_ball_count": 10,
            "preferred_interval": 3.0,
            "skill_level": "中級"
        }
        
        # 分析最近50次訓練記錄
        for entry in entries:
            if entry.get("command", {}).get("type") == "RUN_PROGRAM_BY_NAME":
                program_name = entry.get("command", {}).get("payload", {}).get("program_name")
                if program_name:
                    preferences["favorite_programs"].append(program_name)
                    preferences["training_frequency"] += 1
        
        # 根據訓練頻率判斷技能水平
        if preferences["training_frequency"] < 10:
            preferences["skill_level"] = "初級"
        elif preferences["training_frequency"] > 30:
            preferences["skill_level"] = "高級"
        
        return preferences
    
    def _build_context(self, recent_activity, training_prefs):
        """構建AI教練上下文"""
        context = {
            "user_query": self.user_input,
            "recent_activity": recent_activity[:5],  # 最近5次活動
            "training_preferences": training_prefs,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return context
    
    async def _generate_coach_response(self, context):
        """生成AI教練回覆"""
        # 構建系統提示詞
        system_prompt = f"""你是專業的羽球教練，具有豐富的教學經驗。請根據用戶的訓練歷史和當前問題，提供個性化的技術指導。

用戶資料：
- 技能水平：{context['training_preferences']['skill_level']}
- 訓練頻率：{context['training_preferences']['training_frequency']}次
- 偏好課程：{', '.join(context['training_preferences']['favorite_programs'][:3])}
- 最近活動：{len(context['recent_activity'])}次訓練

指導原則：
- 專注於羽球技術指導，不涉及發球機控制
- 用詞專業但親切，像真正的教練一樣
- 提供具體的技術要點和練習建議
- 根據學員程度調整指導內容
- 鼓勵學員，給予正面回饋
- 結合用戶的訓練歷史給出個性化建議

回覆風格：專業、親切、簡潔、實用，1-2句話回覆"""

        # 使用現有的語音控制系統生成回覆
        if self.voice_control and self.voice_control.client:
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context['user_query']}
                ]

                # 以執行緒呼叫同步 API，避免阻塞事件迴圈
                import asyncio
                loop = asyncio.get_running_loop()
                def _call_openai():
                    return self.voice_control.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        max_tokens=200,
                        temperature=0.7
                    )
                response = await loop.run_in_executor(None, _call_openai)
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"抱歉，AI教練暫時無法回應。請稍後再試。錯誤：{str(e)}"
        else:
            return "AI教練系統未初始化，請檢查OpenAI API設定。"


def create_ai_coach_tab(self):
    """創建AI教練標籤頁"""
    ai_coach_widget = QWidget()
    ai_coach_widget.setObjectName("ai_coach_widget")
    
    # 主布局
    main_layout = QVBoxLayout(ai_coach_widget)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(10, 10, 10, 10)
    
    # 創建滾動區域
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    scroll_layout.setSpacing(15)
    scroll_layout.setContentsMargins(10, 10, 10, 10)
    
    # AI教練風格標題
    title_label = QLabel("🧠 AI COACH • 智能羽球教練")
    title_label.setObjectName("title_label")
    title_label.setAlignment(Qt.AlignCenter)
    title_label.setStyleSheet("""
        QLabel {
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            padding: 20px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(138, 43, 226, 0.25), stop:0.5 rgba(75, 0, 130, 0.18), stop:1 rgba(138, 43, 226, 0.25));
            border-radius: 12px;
            border: 2px solid rgba(138, 43, 226, 0.45);
            letter-spacing: 1px;
            margin-bottom: 12px;
        }
    """)
    scroll_layout.addWidget(title_label)

    # OpenAI API Key 設定區（去除底色、改用細邊框）
    api_group = QGroupBox("🔑 OpenAI API 設定")
    api_group.setStyleSheet("""
        QGroupBox { border: 1px solid rgba(138, 43, 226, 0.25); border-radius: 8px; margin-top: 6px; padding-top: 10px; background-color: transparent; color: #eaeaea; }
        QGroupBox::title { left: 12px; padding: 3px 10px; background-color: rgba(138, 43, 226, 0.25); color: #000; border-radius: 6px; }
    """)
    api_layout = QVBoxLayout(api_group)
    from PyQt5.QtWidgets import QHBoxLayout
    api_row = QHBoxLayout()
    api_row.addWidget(QLabel("API Key:"))
    self.ai_coach_api_key_input = QLineEdit()
    self.ai_coach_api_key_input.setEchoMode(QLineEdit.Password)
    self.ai_coach_api_key_input.setStyleSheet("""
        QLineEdit { border: 1px solid #5a6b7a; border-radius: 6px; padding: 6px 10px; background-color: rgba(0,0,0,0.2); color: #ffffff; }
        QLineEdit:focus { border: 1px solid #7f8fa3; }
    """)
    current_key = os.environ.get("OPENAI_API_KEY", "")
    if current_key and current_key != "你的key":
        self.ai_coach_api_key_input.setText("已設定" if len(current_key) > 10 else current_key)
    self.ai_coach_api_key_input.setPlaceholderText("請輸入您的 OpenAI API Key")
    api_row.addWidget(self.ai_coach_api_key_input)
    self.ai_coach_api_key_save_btn = QPushButton("保存設定")
    self.ai_coach_api_key_save_btn.setStyleSheet("""
        QPushButton { background-color: #5a6b7a; color: #ffffff; border: 1px solid #5a6b7a; border-radius: 6px; padding: 8px 16px; }
        QPushButton:hover { background-color: #6b7c8c; border: 1px solid #6b7c8c; }
        QPushButton:pressed { background-color: #465664; border: 1px solid #465664; }
    """)
    api_row.addWidget(self.ai_coach_api_key_save_btn)
    api_layout.addLayout(api_row)

    # （移除黃色提示語以節省版面）
    scroll_layout.addWidget(api_group)

    # （已移除說明文字區塊以節省版面）
    
    # 創建分割器
    splitter = QSplitter(Qt.Vertical)
    
    # 對話區域
    chat_group = QGroupBox("💬 與AI教練對話")
    chat_group.setStyleSheet("""
        QGroupBox { font-weight: bold; font-size: 16px; border: 1px solid #5a6b7a; border-radius: 10px; margin-top: 12px; padding-top: 16px; background-color: transparent; color: #eaeaea; }
        QGroupBox::title { subcontrol-origin: margin; left: 20px; padding: 6px 12px; background-color: #5a6b7a; color: #ffffff; border-radius: 8px; font-weight: bold; }
    """)
    chat_layout = QVBoxLayout(chat_group)
    
    # 對話歷史顯示區域（改為聊天室泡泡風格）
    self.ai_coach_chat_scroll = QScrollArea()
    self.ai_coach_chat_scroll.setMinimumHeight(330)
    self.ai_coach_chat_scroll.setWidgetResizable(True)
    self.ai_coach_chat_scroll.setStyleSheet("""
        QScrollArea { border: 1px solid #5a6b7a; border-radius: 8px; background-color: rgba(0,0,0,0.45); }
    """)
    self._chat_container = QWidget()
    self._chat_layout = QVBoxLayout(self._chat_container)
    self._chat_layout.setContentsMargins(10, 10, 10, 10)
    self._chat_layout.setSpacing(8)
    self._chat_layout.addStretch()
    # 紀錄所有泡泡以便動態調整寬度
    self._chat_bubbles = []
    # 安裝 resize 事件過濾器以自適應寬度
    try:
        class _ChatResizeFilter(QObject):
            def __init__(self, owner):
                super().__init__()
                self._owner = owner
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Resize:
                    try:
                        self._owner._update_chat_bubble_widths()
                    except Exception:
                        pass
                return False
        self._chat_resize_filter = _ChatResizeFilter(self)
        self.ai_coach_chat_scroll.viewport().installEventFilter(self._chat_resize_filter)
    except Exception:
        pass
    self.ai_coach_chat_scroll.setWidget(self._chat_container)
    chat_layout.addWidget(self.ai_coach_chat_scroll)

    # 歡迎訊息（聊天室泡泡）
    welcome_message = (
        "🧠 AI教練：您好！我是您的專屬羽球教練AI。\n\n"
        "我已經分析了您的訓練記錄，可以為您提供個性化的技術指導。\n"
        "請告訴我您想了解什麼技術，或者遇到了什麼問題？\n\n"
        "例如：\n"
        "• \"我的正手高遠球總是打不遠，該怎麼辦？\"\n"
        "• \"如何改善我的反手技術？\"\n"
        "• \"適合初學者的練習方法有哪些？\"\n"
        "• \"我的殺球力量不夠，有什麼技巧？\"\n\n"
        "隨時向我提問，我會根據您的水平給出專業建議！"
    )
    try:
        # 系統風格泡泡
        def _add_bubble(role: str, text: str):
            from PyQt5.QtWidgets import QHBoxLayout
            bubble_wrap = QWidget()
            row = QHBoxLayout(bubble_wrap)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)

            bubble = QLabel(text)
            bubble.setWordWrap(True)
            bubble.setMaximumWidth(1000)
            bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
            try:
                bubble.setProperty('chat_role', role)
            except Exception:
                pass

            if role == "user":
                bubble.setStyleSheet("""
                    QLabel { background-color: #5a6b7a; color: #ffffff; border-radius: 10px; padding: 10px 12px; }
                """)
                row.addStretch()
                row.addWidget(bubble)
            elif role == "ai":
                bubble.setStyleSheet("""
                    QLabel { background-color: #3b4450; color: #eaeaea; border-radius: 10px; padding: 10px 12px; }
                """)
                row.addWidget(bubble)
                row.addStretch()
            else:  # system
                bubble.setStyleSheet("""
                    QLabel { background-color: #2b323a; color: #bfc9d4; border-radius: 8px; padding: 8px 10px; font-size: 12px; }
                """)
                row.addWidget(bubble)
                row.addStretch()

            self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble_wrap)
            # 記錄並根據容器尺寸調整寬度
            try:
                if hasattr(self, '_chat_bubbles'):
                    self._chat_bubbles.append(bubble)
                    if hasattr(self, '_update_chat_bubble_widths'):
                        self._update_chat_bubble_widths()
            except Exception:
                pass

        _add_bubble("system", welcome_message)
    except Exception:
        pass
    
    # 輸入區域
    input_group = QGroupBox("✍️ 輸入您的問題")
    input_group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            font-size: 14px;
            border: 2px solid #ffa500;
            border-radius: 10px;
            margin-top: 10px;
            padding-top: 15px;
            background-color: rgba(255, 165, 0, 0.05);
            color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 6px 12px;
            background-color: #ffa500;
            color: #000000;
            border-radius: 6px;
            font-weight: bold;
        }
    """)
    input_layout = QVBoxLayout(input_group)
    
    # 輸入框
    self.ai_coach_input = QLineEdit()
    self.ai_coach_input.setPlaceholderText("🤖 請輸入您的羽球技術問題...")
    self.ai_coach_input.setStyleSheet("""
        QLineEdit {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 165, 0, 0.15), stop:1 rgba(255, 140, 0, 0.08));
            color: #ffffff;
            font-size: 14px;
            padding: 12px 16px;
            border: 2px solid #ffa500;
            border-radius: 10px;
            font-weight: 500;
        }
        QLineEdit:focus {
            border: 2px solid #ffb84d;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 165, 0, 0.2), stop:1 rgba(255, 140, 0, 0.12));
        }
    """)
    self.ai_coach_input.returnPressed.connect(lambda: self.send_ai_coach_message())
    input_layout.addWidget(self.ai_coach_input)
    
    # 按鈕區域
    button_layout = QHBoxLayout()
    
    self.ai_coach_send_btn = QPushButton("🚀 發送問題")
    self.ai_coach_send_btn.setStyleSheet("""
        QPushButton { background-color: #5a6b7a; color: #ffffff; border: 1px solid #5a6b7a; border-radius: 8px; padding: 10px 20px; font-size: 14px; font-weight: 600; }
        QPushButton:hover { background-color: #6b7c8c; border: 1px solid #6b7c8c; }
        QPushButton:pressed { background-color: #465664; border: 1px solid #465664; }
    """)
    self.ai_coach_send_btn.clicked.connect(lambda: self.send_ai_coach_message())
    button_layout.addWidget(self.ai_coach_send_btn)
    
    self.ai_coach_clear_btn = QPushButton("🗑️ 清空對話")
    self.ai_coach_clear_btn.setStyleSheet("""
        QPushButton { background-color: #4a4a4a; color: #ffffff; border: 1px solid #4a4a4a; border-radius: 8px; padding: 10px 20px; font-size: 14px; font-weight: 600; }
        QPushButton:hover { background-color: #5a5a5a; border: 1px solid #5a5a5a; }
        QPushButton:pressed { background-color: #3a3a3a; border: 1px solid #3a3a3a; }
    """)
    self.ai_coach_clear_btn.clicked.connect(lambda: self.clear_ai_coach_chat())
    button_layout.addWidget(self.ai_coach_clear_btn)
    
    input_layout.addLayout(button_layout)
    
    # 進度指示器
    self.ai_coach_progress = QProgressBar()
    self.ai_coach_progress.setVisible(False)
    self.ai_coach_progress.setStyleSheet("""
        QProgressBar { border: 1px solid #5a6b7a; border-radius: 8px; text-align: center; background-color: rgba(0,0,0,0.3); color: #eaeaea; font-weight: bold; min-height: 18px; }
        QProgressBar::chunk { background-color: #5a6b7a; border-radius: 6px; margin: 2px; }
    """)
    input_layout.addWidget(self.ai_coach_progress)
    
    # 添加到分割器
    splitter.addWidget(chat_group)
    splitter.addWidget(input_group)
    splitter.setSizes([400, 200])  # 設定初始大小比例
    
    scroll_layout.addWidget(splitter)
    
    # 用戶資料顯示區域
    user_info_group = QGroupBox("📊 您的訓練資料")
    user_info_group.setStyleSheet("""
        QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #5a6b7a; border-radius: 10px; margin-top: 10px; padding-top: 15px; background-color: transparent; color: #eaeaea; }
        QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 6px 12px; background-color: #5a6b7a; color: #ffffff; border-radius: 6px; font-weight: bold; }
    """)
    user_info_layout = QVBoxLayout(user_info_group)

    # 用戶資料文字
    self.ai_coach_user_info = QLabel("正在分析您的訓練資料...")
    self.ai_coach_user_info.setStyleSheet("""
        color: #ffffff;
        font-size: 13px;
        padding: 10px;
        background-color: rgba(255, 165, 0, 0.1);
        border-radius: 8px;
        border: 1px solid rgba(255, 165, 0, 0.3);
    """)
    self.ai_coach_user_info.setWordWrap(True)
    user_info_layout.addWidget(self.ai_coach_user_info)

    # 加入用戶資料面板
    scroll_layout.addWidget(user_info_group)

    # 設定滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setStyleSheet("""
        QScrollArea { border: none; background-color: transparent; }
    """)

    main_layout.addWidget(scroll_area)

    # 初始化AI教練系統與資料
    self.init_ai_coach_system()

    # 綁定 API Key 保存事件
    def _save_ai_api_key():
        api_key = self.ai_coach_api_key_input.text().strip()
        if api_key and api_key != "已設定":
            os.environ["OPENAI_API_KEY"] = api_key
            self.ai_coach_api_key_input.setText("已設定")
            try:
                self.ai_coach_chat.append("✅ API Key 已保存")
            except Exception:
                pass
            # 重新初始化 AI 教練的 OpenAI 客戶端
            try:
                if hasattr(self, 'ai_coach_voice_control') and self.ai_coach_voice_control:
                    # 重新建立 OpenAI 客戶端
                    self.ai_coach_voice_control.client = None
                    # 調用其初始化邏輯
                    init_method = getattr(self.ai_coach_voice_control, '_init_openai_client', None)
                    if callable(init_method):
                        init_method()
                else:
                    # 若尚未建立，建立新的 VoiceControlTTS 實例
                    config = VoiceConfig()
                    self.ai_coach_voice_control = VoiceControlTTS(self, config)
                self.ai_coach_chat.append("🤖 AI 教練已就緒（OpenAI 已初始化）")
            except Exception as e:
                try:
                    self.ai_coach_chat.append(f"⚠️ 重新初始化失敗：{e}")
                except Exception:
                    pass
        else:
            try:
                self.ai_coach_chat.append("⚠️ 請輸入有效的 API Key")
            except Exception:
                pass
    self.ai_coach_api_key_save_btn.clicked.connect(_save_ai_api_key)

    # 週期更新用戶資料（每3分鐘）
    try:
        self._ai_coach_info_timer = QTimer(self)
        self._ai_coach_info_timer.timeout.connect(lambda: self.update_ai_coach_user_info())
        self._ai_coach_info_timer.start(180_000)
    except Exception:
        pass

    # 添加到主標籤頁
    self.tab_widget.addTab(ai_coach_widget, "🧠 AI教練")

    return ai_coach_widget


def init_ai_coach_system(self):
    """初始化AI教練系統"""
    try:
        # 初始化審計讀取器
        self.audit_reader = AuditReader()

        # 重新讀取環境中的 API Key（若剛剛透過輸入框保存）
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "你的key":
            if hasattr(self, 'ai_coach_chat'):
                self.ai_coach_chat.append("[系統] ⚠️ 尚未設定 OPENAI_API_KEY，AI 教練將無法生成回覆")

        # 獲取語音控制實例（如果存在）
        if hasattr(self, 'voice_control_tts') and self.voice_control_tts:
            self.ai_coach_voice_control = self.voice_control_tts
        else:
            # 創建新的語音控制實例用於AI教練
            config = VoiceConfig()
            self.ai_coach_voice_control = VoiceControlTTS(self, config)

        # 更新用戶資料顯示
        self.update_ai_coach_user_info()

        print("✅ AI教練系統初始化成功")

    except Exception as e:
        print(f"⚠️ AI教練系統初始化失敗：{e}")
        if hasattr(self, 'ai_coach_user_info'):
            self.ai_coach_user_info.setText(f"AI教練系統初始化失敗：{str(e)}")


def update_ai_coach_user_info(self):
    """更新AI教練用戶資料顯示"""
    try:
        if not hasattr(self, 'audit_reader'):
            return

        # 獲取用戶訓練資料
        recent_activity = self.audit_reader.get_recent_activity(minutes=1440)  # 24小時
        entries = self.audit_reader.get_latest_entries(50)

        # 分析訓練偏好
        training_count = 0
        favorite_programs = []

        for entry in entries:
            if entry.get("command", {}).get("type") == "RUN_PROGRAM_BY_NAME":
                training_count += 1
                program_name = entry.get("command", {}).get("payload", {}).get("program_name")
                if program_name and program_name not in favorite_programs:
                    favorite_programs.append(program_name)

        # 判斷技能水平
        if training_count < 10:
            skill_level = "初級"
            level_color = "#00ff88"
        elif training_count < 30:
            skill_level = "中級"
            level_color = "#ffa500"
        else:
            skill_level = "高級"
            level_color = "#ff6b6b"

        # 構建用戶資料文字
        user_info_text = f"""
🎯 技能水平：<span style="color: {level_color}; font-weight: bold;">{skill_level}</span>
📈 訓練次數：{training_count} 次
⏰ 最近活動：{len(recent_activity)} 次（24小時內）
🏆 偏好課程：{', '.join(favorite_programs[:3]) if favorite_programs else '尚未記錄'}
        """

        self.ai_coach_user_info.setText(user_info_text)

    except Exception:
        # 靜默錯誤以免中斷UI
        pass


def _append_ai_coach_chat(self, role: str, text: str):
    """在聊天窗新增一則訊息（泡泡風格）。"""
    try:
        from PyQt5.QtWidgets import QHBoxLayout
        bubble_wrap = QWidget()
        row = QHBoxLayout(bubble_wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(1000)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        try:
            label.setProperty('chat_role', role)
        except Exception:
            pass

        if role == "user":
            label.setStyleSheet("""
                QLabel { background-color: #5a6b7a; color: #ffffff; border-radius: 10px; padding: 10px 12px; }
            """)
            row.addStretch()
            row.addWidget(label)
        elif role == "ai":
            label.setStyleSheet("""
                QLabel { background-color: #3b4450; color: #eaeaea; border-radius: 10px; padding: 10px 12px; }
            """)
            row.addWidget(label)
            row.addStretch()
        else:
            label.setStyleSheet("""
                QLabel { background-color: #2b323a; color: #bfc9d4; border-radius: 8px; padding: 8px 10px; font-size: 12px; }
            """)
            row.addWidget(label)
            row.addStretch()

        # 插入到最後一個 stretch 之前
        if hasattr(self, '_chat_layout'):
            self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble_wrap)
            # 記錄並根據容器尺寸調整寬度
            try:
                if hasattr(self, '_chat_bubbles'):
                    self._chat_bubbles.append(label)
                    if hasattr(self, '_update_chat_bubble_widths'):
                        self._update_chat_bubble_widths()
            except Exception:
                pass
            # 自動滾動到底
            try:
                self.ai_coach_chat_scroll.verticalScrollBar().setValue(self.ai_coach_chat_scroll.verticalScrollBar().maximum())
            except Exception:
                pass
    except Exception:
        # 退回到簡單追加
        try:
            prefix = {"user": "你", "ai": "教練", "system": "系統"}.get(role, role)
            if hasattr(self, 'ai_coach_chat'):
                self.ai_coach_chat.append(f"[{prefix}] {text}")
        except Exception:
            pass


def clear_ai_coach_chat(self):
    """清空聊天記錄並顯示歡迎訊息（泡泡風格）。"""
    try:
        if hasattr(self, '_chat_layout'):
            # 移除除了最後一個 stretch 之外的所有項目
            while self._chat_layout.count() > 1:
                item = self._chat_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        if hasattr(self, '_chat_bubbles'):
            self._chat_bubbles = []
        # 加入歡迎泡泡
        _append_ai_coach_chat(self, "system", "🧠 AI教練：您好！開始提問吧～")
    except Exception:
        pass


def _update_chat_bubble_widths(self):
    """根據滾動區視口寬度調整聊天泡泡最大寬度，減少過早換行。"""
    try:
        if not hasattr(self, 'ai_coach_chat_scroll') or not hasattr(self, '_chat_bubbles'):
            return
        viewport = self.ai_coach_chat_scroll.viewport()
        vw = viewport.width()
        for lbl in list(self._chat_bubbles):
            try:
                role = lbl.property('chat_role') or ''
                if role == 'ai':
                    # 教練泡泡更寬：占視口寬度的 88%，並預留邊距 40
                    maxw = max(360, min(vw - 40, int(vw * 0.88)))
                elif role == 'user':
                    # 使用者泡泡稍窄，避免貼邊
                    maxw = max(320, int(vw * 0.72))
                else:
                    # 系統訊息較窄
                    maxw = max(280, int(vw * 0.60))
                lbl.setMaximumWidth(maxw)
            except Exception:
                continue
    except Exception:
        pass


def send_ai_coach_message(self):
    """傳送使用者問題到AI教練，並顯示回覆。"""
    user_text = (self.ai_coach_input.text() or "").strip()
    if not user_text:
        return
    _append_ai_coach_chat(self, "user", user_text)
    self.ai_coach_input.clear()

    # 顯示進度與鎖定按鈕
    try:
        self.ai_coach_progress.setVisible(True)
        self.ai_coach_progress.setRange(0, 0)  # 無限進度條
        self.ai_coach_send_btn.setEnabled(False)
    except Exception:
        pass

    # 啟動背景工作線程
    try:
        worker = AICoachWorker(user_text, getattr(self, 'ai_coach_voice_control', None), getattr(self, 'audit_reader', None))

        def on_ready(reply: str):
            _append_ai_coach_chat(self, "ai", reply)
            try:
                self.ai_coach_progress.setVisible(False)
                self.ai_coach_send_btn.setEnabled(True)
            except Exception:
                pass

        def on_error(err: str):
            _append_ai_coach_chat(self, "system", err)
            try:
                self.ai_coach_progress.setVisible(False)
                self.ai_coach_send_btn.setEnabled(True)
            except Exception:
                pass

        worker.response_ready.connect(on_ready)
        worker.error_occurred.connect(on_error)
        worker.start()

        # 保持引用避免GC
        if not hasattr(self, '_ai_coach_workers'):
            self._ai_coach_workers = []
        self._ai_coach_workers.append(worker)
    except Exception as e:
        _append_ai_coach_chat(self, "system", f"啟動AI教練任務失敗：{e}")
        try:
            self.ai_coach_progress.setVisible(False)
            self.ai_coach_send_btn.setEnabled(True)
        except Exception:
            pass


# 舊綁定名稱相容：供先前版本呼叫
def send_coach_message(self):
    return send_ai_coach_message(self)

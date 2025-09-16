import asyncio
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QComboBox, QHBoxLayout, QCheckBox, QGroupBox, QLineEdit)
import sounddevice as sd


def create_voice_tab(self):
    """建立語音控制獨立頁面 - TTS 整合版。"""
    voice_widget = QWidget()
    layout = QVBoxLayout(voice_widget)
    
    # 創建滾動區域以防止內容溢出
    from PyQt5.QtWidgets import QScrollArea
    from PyQt5.QtCore import Qt
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)

    # AI風格標題與說明
    title = QLabel("🎙️ AI VOICE COMMAND • 智能語音控制系統 (Whisper API)")
    title.setStyleSheet("""
        font-size: 20px; 
        font-weight: bold; 
        color: #ffffff; 
        padding: 16px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(138, 43, 226, 0.3), stop:0.5 rgba(75, 0, 130, 0.2), stop:1 rgba(138, 43, 226, 0.3));
        border-radius: 12px;
        border: 3px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #8a2be2, stop:0.5 #4b0082, stop:1 #8a2be2);
        letter-spacing: 1px;
    """)
    scroll_layout.addWidget(title)

    instruction_label = QLabel(
        "🧠 Whisper API 高準確度語音識別 + 智能規則匹配 + TTS 語音回覆：\n"
        "• 開始訓練 / 停止訓練 / 暫停\n"
        "• 快速發球 / 慢速發球 / 中速發球\n"
        "• 前場練習 / 後場練習 / 殺球練習\n"
        "• 左邊 / 右邊 / 中間 / 提高 / 降低\n"
        "💡 支援自然語言指令，系統會自動識別並執行對應動作"
    )
    instruction_label.setStyleSheet("color: #ffffff; font-size: 12px;")
    instruction_label.setWordWrap(True)  # 允許文字換行
    scroll_layout.addWidget(instruction_label)

    # OpenAI API 設定區
    api_group = QGroupBox("🔑 OpenAI API 設定")
    api_layout = QVBoxLayout(api_group)
    
    api_key_row = QHBoxLayout()
    api_key_row.addWidget(QLabel("API Key:"))
    self.api_key_input = QLineEdit()
    self.api_key_input.setEchoMode(QLineEdit.Password)
    current_key = os.environ.get("OPENAI_API_KEY", "")
    if current_key and current_key != "你的key":
        self.api_key_input.setText("已設定" if len(current_key) > 10 else current_key)
    self.api_key_input.setPlaceholderText("請輸入您的 OpenAI API Key")
    api_key_row.addWidget(self.api_key_input)
    
    self.api_key_save_button = QPushButton("保存設定")
    api_key_row.addWidget(self.api_key_save_button)
    api_layout.addLayout(api_key_row)
    
    api_status = QLabel("💡 需要 OpenAI API Key 才能使用 Whisper 語音識別和 TTS 語音合成")
    api_status.setStyleSheet("color: #ffcc00; font-size: 11px;")
    api_status.setWordWrap(True)
    api_layout.addWidget(api_status)
    scroll_layout.addWidget(api_group)

    # 裝置選擇區
    device_group = QGroupBox("🎤 音訊裝置設定")
    device_layout = QVBoxLayout(device_group)
    
    device_row = QHBoxLayout()
    device_row.addWidget(QLabel("輸入裝置:"))
    self.voice_device_combo = QComboBox()
    try:
        devices = sd.query_devices()
        default_in = sd.default.device[0] if hasattr(sd, 'default') and sd.default and sd.default.device else None
        for idx, d in enumerate(devices):
            name = d.get('name', f'Device {idx}')
            if d.get('max_input_channels', 0) > 0:
                label = f"{idx}: {name}"
                self.voice_device_combo.addItem(label, idx)
                if default_in is not None and idx == default_in:
                    self.voice_device_combo.setCurrentIndex(self.voice_device_combo.count()-1)
    except Exception:
        pass
    device_row.addWidget(self.voice_device_combo)
    device_layout.addLayout(device_row)
    scroll_layout.addWidget(device_group)

    # 語音設定區
    voice_settings_group = QGroupBox("🔊 語音設定")
    voice_settings_layout = QVBoxLayout(voice_settings_group)
    
    # TTS 語音選擇
    tts_voice_row = QHBoxLayout()
    tts_voice_row.addWidget(QLabel("TTS 語音:"))
    self.tts_voice_combo = QComboBox()
    tts_voices = ["nova", "alloy", "echo", "fable", "onyx", "shimmer"]
    for voice in tts_voices:
        self.tts_voice_combo.addItem(voice)
    self.tts_voice_combo.setCurrentText("nova")
    tts_voice_row.addWidget(self.tts_voice_combo)
    voice_settings_layout.addLayout(tts_voice_row)
    
    # 語音設定選項
    self.enable_tts_checkbox = QCheckBox("啟用 TTS 語音回覆")
    self.enable_tts_checkbox.setChecked(True)
    voice_settings_layout.addWidget(self.enable_tts_checkbox)
    
    self.enable_rules_checkbox = QCheckBox("啟用規則匹配系統")
    self.enable_rules_checkbox.setChecked(True)
    voice_settings_layout.addWidget(self.enable_rules_checkbox)
    
    self.safe_mode_checkbox = QCheckBox("啟用安全模式（推薦，減少記憶體使用）")
    self.safe_mode_checkbox.setChecked(True)
    voice_settings_layout.addWidget(self.safe_mode_checkbox)
    
    # 預載入系統選項
    self.enable_preload_checkbox = QCheckBox("啟用預載入系統（提升響應速度）")
    self.enable_preload_checkbox.setChecked(True)
    voice_settings_layout.addWidget(self.enable_preload_checkbox)
    
    # 模式管理選項
    mode_row = QHBoxLayout()
    mode_row.addWidget(QLabel("預設模式:"))
    self.mode_combo = QComboBox()
    self.mode_combo.addItems(["控制模式", "思考模式"])
    self.mode_combo.setCurrentText("控制模式")
    mode_row.addWidget(self.mode_combo)
    voice_settings_layout.addLayout(mode_row)
    
    scroll_layout.addWidget(voice_settings_group)

    # 對話/日誌視窗（顯示辨識與系統訊息）
    log_group = QGroupBox("💬 語音對話記錄")
    log_layout = QVBoxLayout(log_group)
    self.voice_chat_log = QTextEdit()
    self.voice_chat_log.setReadOnly(True)
    self.voice_chat_log.setMinimumHeight(200)
    self.voice_chat_log.setStyleSheet("""
        QTextEdit {
            background-color: rgba(30, 30, 30, 0.8);
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
        }
    """)
    log_layout.addWidget(self.voice_chat_log)
    scroll_layout.addWidget(log_group)

    # 控制按鈕
    control_group = QGroupBox("🎛️ 語音控制")
    control_layout = QVBoxLayout(control_group)
    
    self.voice_start_button = QPushButton("🎙️ 啟動語音控制")
    self.voice_start_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4CAF50, stop:1 #45a049);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #45a049, stop:1 #4CAF50);
        }
    """)
    
    self.voice_stop_button = QPushButton("🔇 停止語音控制")
    self.voice_stop_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f44336, stop:1 #da190b);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #da190b, stop:1 #f44336);
        }
    """)
    
    control_layout.addWidget(self.voice_start_button)
    control_layout.addWidget(self.voice_stop_button)
    
    # 添加手動錄音按鈕（簡化版）
    self.manual_record_button = QPushButton("🎤 開始錄音（簡化版）")
    self.manual_record_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2196F3, stop:1 #1976D2);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1976D2, stop:1 #2196F3);
        }
    """)
    control_layout.addWidget(self.manual_record_button)
    
    # 添加強制重置按鈕（調試用）
    self.force_reset_button = QPushButton("🔄 強制重置狀態")
    self.force_reset_button.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #FF9800, stop:1 #F57C00);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #F57C00, stop:1 #FF9800);
        }
    """)
    control_layout.addWidget(self.force_reset_button)
    
    # 模式說明
    mode_info = QLabel("💡 如果遇到閃退問題，請使用「簡化版」手動錄音模式")
    mode_info.setStyleSheet("color: #ffcc00; font-size: 11px;")
    mode_info.setWordWrap(True)
    control_layout.addWidget(mode_info)
    
    # 快取管理區
    cache_group = QGroupBox("💾 快取管理")
    cache_layout = QVBoxLayout(cache_group)
    
    cache_buttons_row = QHBoxLayout()
    self.save_cache_btn = QPushButton("儲存快取")
    self.clear_cache_btn = QPushButton("清空快取")
    self.cache_stats_btn = QPushButton("顯示統計")
    cache_buttons_row.addWidget(self.save_cache_btn)
    cache_buttons_row.addWidget(self.clear_cache_btn)
    cache_buttons_row.addWidget(self.cache_stats_btn)
    cache_layout.addLayout(cache_buttons_row)
    
    scroll_layout.addWidget(cache_group)
    scroll_layout.addWidget(control_group)

    # 綁定事件（非阻塞）
    def _save_api_key():
        """保存 API Key"""
        api_key = self.api_key_input.text().strip()
        if api_key and api_key != "已設定":
            os.environ["OPENAI_API_KEY"] = api_key
            self.api_key_input.setText("已設定")
            self.voice_chat_log.append("✅ API Key 已保存")
        else:
            self.voice_chat_log.append("⚠️ 請輸入有效的 API Key")
    
    def _start_voice():
        """啟動語音控制"""
        # 檢查 API Key
        if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "你的key":
            self.voice_chat_log.append("❌ 請先設定 OpenAI API Key")
            return
        
        device_idx = self.voice_device_combo.currentData()
        
        # 檢查是否已經在運行
        if hasattr(self, 'voice_control_tts') and self.voice_control_tts is not None:
            if self.voice_control_tts._running:
                self.voice_chat_log.append("⚠️ 語音控制已經在運行中")
                return
        
        # 停止舊的語音控制
        try:
            if hasattr(self, 'voice_control_tts') and self.voice_control_tts is not None:
                # 使用線程來處理異步停止
                def stop_voice_control():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.voice_control_tts.stop())
                        loop.close()
                    except Exception as e:
                        print(f"停止語音控制時發生錯誤：{e}")
                
                import threading
                stop_thread = threading.Thread(target=stop_voice_control, daemon=True)
                stop_thread.start()
                stop_thread.join(timeout=2)  # 等待最多2秒
        except Exception:
            pass
        
        # 創建新的語音控制
        try:
            from voice_control_tts import VoiceControlTTS, VoiceConfig
            
            # 配置語音設定
            config = VoiceConfig()
            config.default_voice = self.tts_voice_combo.currentText()
            config.enable_tts = self.enable_tts_checkbox.isChecked()
            config.enable_rules = self.enable_rules_checkbox.isChecked()
            config.safe_mode = self.safe_mode_checkbox.isChecked()
            
            # 配置預載入系統
            config.preload.enabled = self.enable_preload_checkbox.isChecked()
            
            self.voice_control_tts = VoiceControlTTS(self, config)
            if device_idx is not None:
                self.voice_control_tts.set_input_device(device_idx)
            
            # 設定預設模式
            default_mode = "control" if self.mode_combo.currentText() == "控制模式" else "think"
            self.voice_control_tts.mode_manager.current_mode = default_mode
            
            # 使用線程來處理異步啟動
            def start_voice_control():
                try:
                    # 創建新的事件循環
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # 啟動語音控制
                    loop.run_until_complete(self.voice_control_tts.start())
                    
                    # 保持循環運行，直到語音控制停止
                    try:
                        while self.voice_control_tts._running:
                            loop.run_until_complete(asyncio.sleep(0.1))
                    except Exception:
                        pass
                    
                except Exception as e:
                    self.voice_chat_log.append(f"❌ 語音控制啟動失敗：{e}")
                finally:
                    try:
                        loop.close()
                    except Exception:
                        pass
            
            import threading
            start_thread = threading.Thread(target=start_voice_control, daemon=True)
            start_thread.start()
            self.voice_chat_log.append("🎙️ 正在啟動語音控制...")
            
        except Exception as e:
            self.voice_chat_log.append(f"❌ 啟動語音控制失敗：{e}")
    
    def _stop_voice():
        """停止語音控制"""
        try:
            # 停止 TTS 語音控制
            if hasattr(self, 'voice_control_tts') and self.voice_control_tts is not None:
                def stop_voice_control():
                    try:
                        # 直接設置停止標誌，避免事件循環衝突
                        self.voice_control_tts._running = False
                        self.voice_control_tts._starting = False
                        
                        # 清理任務引用
                        if hasattr(self.voice_control_tts, '_listen_task') and self.voice_control_tts._listen_task:
                            try:
                                self.voice_control_tts._listen_task.cancel()
                            except Exception:
                                pass
                        
                        self.voice_control_tts._listen_task = None
                        self.voice_control_tts._capture_task = None
                        self.voice_control_tts._audio_stream = None
                        
                        print("語音控制已停止")
                    except Exception as e:
                        print(f"停止語音控制時發生錯誤：{e}")
                        # 如果停止失敗，強制重置狀態
                        try:
                            self.voice_control_tts.force_reset()
                        except Exception:
                            pass
                
                import threading
                stop_thread = threading.Thread(target=stop_voice_control, daemon=True)
                stop_thread.start()
                stop_thread.join(timeout=2)  # 等待最多2秒
                self.voice_chat_log.append("🔇 正在停止語音控制...")
            
            # 停止簡化版語音控制
            if hasattr(self, 'simple_voice_control') and self.simple_voice_control is not None:
                def stop_simple_voice_control():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.simple_voice_control.stop())
                        loop.close()
                    except Exception as e:
                        print(f"停止簡化版語音控制時發生錯誤：{e}")
                
                import threading
                stop_thread = threading.Thread(target=stop_simple_voice_control, daemon=True)
                stop_thread.start()
                stop_thread.join(timeout=3)  # 等待最多3秒
                self.voice_chat_log.append("🔇 正在停止簡化版語音控制...")
                
        except Exception as e:
            self.voice_chat_log.append(f"⚠️ 停止語音控制時發生錯誤：{e}")
    
    def _manual_record():
        """手動錄音（簡化版）"""
        # 檢查 API Key
        if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "你的key":
            self.voice_chat_log.append("❌ 請先設定 OpenAI API Key")
            return
        
        device_idx = self.voice_device_combo.currentData()
        
        # 使用現有的語音控制進行單次錄音
        try:
            from voice_control_tts import VoiceControlTTS, VoiceConfig
            
            # 配置設定
            config = VoiceConfig()
            config.default_voice = self.tts_voice_combo.currentText()
            config.enable_tts = self.enable_tts_checkbox.isChecked()
            config.enable_rules = self.enable_rules_checkbox.isChecked()
            config.safe_mode = True  # 使用安全模式
            
            # 創建臨時語音控制實例
            temp_voice_control = VoiceControlTTS(self, config)
            if device_idx is not None:
                temp_voice_control.set_input_device(device_idx)
            
            # 開始錄音和處理
            def record_and_process():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # 執行單次錄音和識別
                    async def single_record():
                        try:
                            # 錄音
                            audio_data = await temp_voice_control._record_audio_simple()
                            if not audio_data:
                                self.voice_chat_log.append("⚠️ 錄音失敗")
                                return
                            
                            # 語音識別
                            text = await temp_voice_control._transcribe_audio(audio_data)
                            if not text.strip():
                                self.voice_chat_log.append("⚠️ 語音識別結果為空")
                                return
                            
                            self.voice_chat_log.append(f"🎤 識別結果：{text}")
                            
                            # 處理指令
                            await temp_voice_control._process_command(text)
                            
                        except Exception as e:
                            self.voice_chat_log.append(f"❌ 錄音處理失敗：{e}")
                    
                    loop.run_until_complete(single_record())
                    loop.close()
                except Exception as e:
                    self.voice_chat_log.append(f"❌ 錄音處理失敗：{e}")
            
            import threading
            record_thread = threading.Thread(target=record_and_process, daemon=True)
            record_thread.start()
            self.voice_chat_log.append("🎤 開始錄音處理...")
            
        except Exception as e:
            self.voice_chat_log.append(f"❌ 手動錄音失敗：{e}")
    
    def _force_reset():
        """強制重置語音控制狀態"""
        try:
            if hasattr(self, 'voice_control_tts') and self.voice_control_tts is not None:
                self.voice_control_tts.force_reset()
                self.voice_chat_log.append("🔄 語音控制狀態已強制重置")
            else:
                self.voice_chat_log.append("⚠️ 沒有找到語音控制實例")
        except Exception as e:
            self.voice_chat_log.append(f"❌ 強制重置失敗：{e}")

    # 綁定按鈕事件
    self.api_key_save_button.clicked.connect(_save_api_key)
    self.voice_start_button.clicked.connect(_start_voice)
    self.voice_stop_button.clicked.connect(_stop_voice)
    self.manual_record_button.clicked.connect(_manual_record)
    self.force_reset_button.clicked.connect(_force_reset)
    
    # 快取管理事件
    def _save_cache():
        """儲存快取"""
        if hasattr(self, 'voice_control_tts') and self.voice_control_tts and self.voice_control_tts.reply_cache:
            self.voice_control_tts.reply_cache.save_cache_now()
            self.voice_chat_log.append("💾 快取已儲存")
        else:
            self.voice_chat_log.append("⚠️ 語音控制未啟動或快取系統未啟用")
    
    def _clear_cache():
        """清空快取"""
        if hasattr(self, 'voice_control_tts') and self.voice_control_tts and self.voice_control_tts.reply_cache:
            self.voice_control_tts.reply_cache.clear_cache()
            self.voice_chat_log.append("🗑️ 快取已清空")
        else:
            self.voice_chat_log.append("⚠️ 語音控制未啟動或快取系統未啟用")
    
    def _show_cache_stats():
        """顯示快取統計"""
        if hasattr(self, 'voice_control_tts') and self.voice_control_tts and self.voice_control_tts.reply_cache:
            stats = self.voice_control_tts.reply_cache.get_cache_stats()
            self.voice_chat_log.append(f"📊 快取統計：{stats}")
        else:
            self.voice_chat_log.append("⚠️ 語音控制未啟動或快取系統未啟用")
    
    self.save_cache_btn.clicked.connect(_save_cache)
    self.clear_cache_btn.clicked.connect(_clear_cache)
    self.cache_stats_btn.clicked.connect(_show_cache_stats)

    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    layout.addWidget(scroll_area)

    # 加入標籤頁
    self.tab_widget.addTab(voice_widget, "語音控制")


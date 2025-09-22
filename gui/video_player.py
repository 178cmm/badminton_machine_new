"""
影片播放器組件

這個模組提供影片播放功能，用於在基礎訓練中顯示教學影片。
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QSlider, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl
import os


class VideoPlayer(QWidget):
    """影片播放器組件"""
    
    # 定義信號
    video_ended = pyqtSignal()
    video_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.setup_ui()
        self.setup_media_player()
        
    def setup_ui(self):
        """設置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 影片顯示區域
        self.video_widget.setMinimumSize(400, 300)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("""
            QVideoWidget {
                background-color: #000000;
                border: 1px solid #555555;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.video_widget)
        
        # 控制面板
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 5, 10, 5)
        control_layout.setSpacing(10)
        
        # 播放/暫停按鈕
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(40, 30)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.play_button.clicked.connect(self.toggle_play_pause)
        control_layout.addWidget(self.play_button)
        
        # 停止按鈕
        self.stop_button = QPushButton("⏹")
        self.stop_button.setFixedSize(40, 30)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170b;
            }
        """)
        self.stop_button.clicked.connect(self.stop_video)
        control_layout.addWidget(self.stop_button)
        
        # 進度條
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #2b2b2b;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #555555;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #45a049;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border: 1px solid #555555;
                height: 8px;
                border-radius: 4px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.valueChanged.connect(self.on_slider_value_changed)
        control_layout.addWidget(self.progress_slider)
        
        # 時間標籤
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12px;
                font-family: monospace;
                min-width: 80px;
            }
        """)
        control_layout.addWidget(self.time_label)
        
        layout.addWidget(control_frame)
        
        # 狀態標籤
        self.status_label = QLabel("請選擇影片")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 11px;
                padding: 5px;
                text-align: center;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
    def setup_media_player(self):
        """設置媒體播放器"""
        self.media_player.setVideoOutput(self.video_widget)
        
        # 連接信號
        self.media_player.stateChanged.connect(self.on_state_changed)
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        self.media_player.error.connect(self.on_error)
        
        # 定時器用於更新進度
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(1000)  # 每秒更新一次
        
        self.slider_pressed = False
        self.video_loaded = False
        self.playback_failed = False
        
    def load_video(self, video_path):
        """載入影片"""
        # 確保使用絕對路徑
        abs_video_path = os.path.abspath(video_path)
        
        if not os.path.exists(abs_video_path):
            self.status_label.setText(f"影片文件不存在: {abs_video_path}")
            self.video_error.emit(f"影片文件不存在: {abs_video_path}")
            return False
        
        # 檢查文件是否可讀
        if not os.access(abs_video_path, os.R_OK):
            self.status_label.setText(f"影片文件無法讀取: {abs_video_path}")
            self.video_error.emit(f"影片文件無法讀取: {abs_video_path}")
            return False
            
        try:
            # 使用絕對路徑創建URL
            media_content = QMediaContent(QUrl.fromLocalFile(abs_video_path))
            self.media_player.setMedia(media_content)
            self.status_label.setText(f"已載入: {os.path.basename(abs_video_path)}")
            self.video_loaded = True
            self.playback_failed = False
            return True
        except Exception as e:
            error_msg = f"載入影片失敗: {str(e)}"
            self.status_label.setText(error_msg)
            self.video_error.emit(error_msg)
            print(f"影片載入錯誤: {error_msg}")
            print(f"影片路徑: {abs_video_path}")
            self.video_loaded = False
            return False
    
    def toggle_play_pause(self):
        """切換播放/暫停"""
        if not self.video_loaded:
            self.status_label.setText("請先載入影片")
            return
            
        if self.playback_failed:
            self.status_label.setText("影片播放失敗，請檢查編解碼器設定")
            return
            
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def stop_video(self):
        """停止播放"""
        self.media_player.stop()
        self.progress_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
    
    def on_state_changed(self, state):
        """播放狀態改變"""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("⏸")
            self.status_label.setText("播放中...")
        elif state == QMediaPlayer.PausedState:
            self.play_button.setText("▶")
            self.status_label.setText("已暫停")
        elif state == QMediaPlayer.StoppedState:
            self.play_button.setText("▶")
            self.status_label.setText("已停止")
    
    def on_position_changed(self, position):
        """播放位置改變"""
        if not self.slider_pressed and self.media_player.duration() > 0:
            progress = int((position / self.media_player.duration()) * 100)
            self.progress_slider.setValue(progress)
    
    def on_duration_changed(self, duration):
        """影片長度改變"""
        if duration > 0:
            self.progress_slider.setMaximum(100)
            self.update_time_display()
    
    def on_error(self, error):
        """播放錯誤"""
        from PyQt5.QtMultimedia import QMediaPlayer
        
        # 處理QMediaPlayer錯誤代碼
        error_code = int(error) if str(error).isdigit() else error
        error_messages = {
            QMediaPlayer.NoError: "無錯誤",
            QMediaPlayer.ResourceError: "資源錯誤 - 無法載入媒體資源",
            QMediaPlayer.FormatError: "格式錯誤 - 不支援的媒體格式",
            QMediaPlayer.NetworkError: "網路錯誤 - 網路連接問題",
            QMediaPlayer.AccessDeniedError: "存取被拒絕 - 沒有權限存取媒體資源"
        }
        
        # 獲取錯誤描述
        if error_code in error_messages:
            error_desc = error_messages[error_code]
        else:
            error_desc = f"未知錯誤 (代碼: {error_code})"
        
        # 根據錯誤類型提供解決建議
        if error_code == QMediaPlayer.FormatError:
            solution = "\n建議: 請安裝額外的媒體編解碼器或轉換影片格式"
        elif error_code == QMediaPlayer.ResourceError:
            solution = "\n建議: 檢查影片檔案是否損壞或路徑是否正確"
        elif error_code == QMediaPlayer.AccessDeniedError:
            solution = "\n建議: 檢查檔案權限或防毒軟體設定"
        else:
            solution = "\n建議: 請嘗試重新啟動應用程式或檢查系統設定"
        
        error_msg = f"播放錯誤: {error_desc}{solution}"
        
        # 標記播放失敗
        self.playback_failed = True
        
        self.status_label.setText(error_msg)
        self.video_error.emit(error_msg)
        print(f"影片播放錯誤: {error_msg}")
        print(f"錯誤代碼: {error_code}")
        
        # 如果是格式錯誤，提供安裝編解碼器的建議
        if error_code == QMediaPlayer.FormatError:
            self.show_codec_install_hint()
    
    def on_slider_pressed(self):
        """滑塊被按下"""
        self.slider_pressed = True
    
    def on_slider_released(self):
        """滑塊被釋放"""
        self.slider_pressed = False
        if self.media_player.duration() > 0:
            position = int((self.progress_slider.value() / 100) * self.media_player.duration())
            self.media_player.setPosition(position)
    
    def on_slider_value_changed(self, value):
        """滑塊值改變"""
        if self.slider_pressed and self.media_player.duration() > 0:
            position = int((value / 100) * self.media_player.duration())
            self.media_player.setPosition(position)
    
    def update_progress(self):
        """更新進度顯示"""
        if self.media_player.duration() > 0:
            self.update_time_display()
    
    def update_time_display(self):
        """更新時間顯示"""
        position = self.media_player.position()
        duration = self.media_player.duration()
        
        pos_time = self.format_time(position)
        dur_time = self.format_time(duration)
        
        self.time_label.setText(f"{pos_time} / {dur_time}")
    
    def format_time(self, milliseconds):
        """格式化時間"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def show_codec_install_hint(self):
        """顯示編解碼器安裝提示"""
        hint_msg = """
編解碼器安裝提示:

如果影片無法播放，請執行以下命令安裝編解碼器:

1. 執行安裝腳本:
   ./install_media_codecs.sh

2. 或手動安裝:
   brew install gstreamer gst-plugins-base gst-plugins-good
   brew install gst-plugins-bad gst-plugins-ugly ffmpeg

3. 重新啟動應用程式

影片格式: H.264/AAC (標準MP4格式)
        """
        self.status_label.setText(f"編解碼器問題\n{hint_msg}")
    
    def cleanup(self):
        """清理資源"""
        if hasattr(self, 'media_player'):
            self.media_player.stop()
        if hasattr(self, 'timer'):
            self.timer.stop()

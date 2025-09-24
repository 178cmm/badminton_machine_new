from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox, QTabWidget, QProgressBar, QDialog, QGridLayout, QHBoxLayout, QScrollArea, QSplitter
from PyQt5.QtCore import Qt
from qasync import asyncSlot
import sys
import os
import asyncio
# 將父目錄加入路徑以便匯入上層模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parsers import get_basic_training_items, load_descriptions
from core.executors import create_basic_training_executor
from core.services.device_service import DeviceService
from core.services.training_service import TrainingService
from core.utils.video_config import get_video_config
from commands import read_data_from_json
from bluetooth import AREA_FILE_PATH
from gui.video_player import VideoPlayer

def create_basic_training_tab(self):
    """創建基礎訓練標籤頁"""
    basic_training_widget = QWidget()
    layout = QVBoxLayout(basic_training_widget)
    
    # 創建滾動區域以防止內容溢出
    scroll_area = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    
    # 創建按鈕網格
    button_grid = QGridLayout()
    
    # 取得基礎訓練項目
    basic_trainings = get_basic_training_items()
    
    # 建立 section 對應名稱，供描述顯示使用
    self.section_to_name = {}

    # 創建按鈕 - 小幅美化原有設計
    for i, (name, section) in enumerate(basic_trainings):
        self.section_to_name[section] = name
        button = QPushButton(name)
        button.clicked.connect(lambda checked, s=section, n=name: self.select_basic_training(s, n))
        
        # 小幅美化按鈕樣式
        button.setStyleSheet("""
            QPushButton {
                background-color: #5a8c9a;
                color: #ffffff;
                border: 1px solid #5a8c9a;
                padding: 10px 16px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #6a9caa;
                border: 1px solid #6a9caa;
            }
            QPushButton:pressed {
                background-color: #4a7c8a;
                border: 1px solid #4a7c8a;
            }
        """)
        
        row, col = divmod(i, 4)  # 保持原本的4列布局
        button_grid.addWidget(button, row, col)
    
    scroll_layout.addLayout(button_grid)
    
    # 添加進度條區域 - 小幅美化
    progress_group = QGroupBox("訓練進度")
    progress_group.setStyleSheet("""
        QGroupBox {
            font-size: 13px;
            font-weight: bold;
            color: #ffffff;
            border: 1px solid #5a8c9a;
            border-radius: 8px;
            margin-top: 8px;
            padding-top: 10px;
            background-color: rgba(90, 140, 154, 0.1);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #4CAF50;
        }
    """)
    progress_layout = QVBoxLayout(progress_group)
    progress_layout.setContentsMargins(8, 8, 8, 8)
    progress_layout.setSpacing(5)
    
    # 進度條 - 小幅美化
    self.basic_training_progress_bar = QProgressBar()
    self.basic_training_progress_bar.setVisible(False)
    self.basic_training_progress_bar.setMaximumHeight(18)
    self.basic_training_progress_bar.setStyleSheet("""
        QProgressBar {
            border: 1px solid #5a8c9a;
            border-radius: 5px;
            text-align: center;
            background-color: #2b2b2b;
            color: #ffffff;
            font-weight: bold;
            font-size: 11px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4CAF50, stop:1 #45a049);
            border-radius: 4px;
        }
    """)
    progress_layout.addWidget(self.basic_training_progress_bar)
    
    # 進度文字標籤 - 小幅美化
    self.basic_training_progress_label = QLabel("")
    self.basic_training_progress_label.setStyleSheet("""
        QLabel {
            color: #ffffff;
            font-size: 12px;
            padding: 5px;
        }
    """)
    self.basic_training_progress_label.setVisible(False)
    progress_layout.addWidget(self.basic_training_progress_label)
    
    scroll_layout.addWidget(progress_group)
    
    # 設置滾動區域
    scroll_area.setWidget(scroll_widget)
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
    layout.addWidget(scroll_area)
    
    self.tab_widget.addTab(basic_training_widget, "基礎訓練")

    
def select_basic_training(self, section, shot_name=None):
    """選擇基礎訓練項目後進階選擇速度和發球數量"""
    # 彈出對話框讓用戶選擇速度和發球數量
    dialog = QDialog(self)
    dialog.setWindowTitle("選擇訓練設置")
    dialog_layout = QVBoxLayout(dialog)

    # 載入描述檔案
    if not hasattr(self, 'basic_discription_map'):
        self.basic_discription_map = load_descriptions()

    # 顯示描述區塊
    display_name = shot_name or getattr(self, 'section_to_name', {}).get(section, None)
    if display_name:
        try:
            dialog.setWindowTitle(f"選擇訓練設置 - {display_name}")
        except Exception:
            pass
    
    # 創建分割器來分離描述和影片區域
    splitter = QSplitter(Qt.Horizontal)
    dialog_layout.addWidget(splitter)
    
    # 左側：描述區域
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    
    desc_title = QLabel("項目說明:")
    left_layout.addWidget(desc_title)
    desc_text = QTextEdit()
    desc_text.setReadOnly(True)
    description_body = self.basic_discription_map.get(display_name or "", "暫無說明")
    if display_name and description_body and not description_body.startswith(display_name):
        full_text = f"{display_name}\n" + description_body
    else:
        full_text = description_body if description_body else (display_name or section)
    desc_text.setText(full_text)
    desc_text.setMinimumHeight(200)
    left_layout.addWidget(desc_text)
    
    splitter.addWidget(left_widget)
    
    # 右側：影片播放區域
    right_widget = QWidget()
    right_layout = QVBoxLayout(right_widget)
    
    video_title = QLabel("教學影片:")
    right_layout.addWidget(video_title)
    
    # 創建影片播放器
    video_player = VideoPlayer()
    video_config = get_video_config()
    
    # 檢查是否有對應的影片
    if display_name and video_config.has_video(display_name):
        video_path = video_config.get_video_path(display_name)
        if video_path:
            # 載入影片並檢查是否成功
            success = video_player.load_video(video_path)
            if not success:
                # 如果載入失敗，顯示錯誤信息
                error_label = QLabel(f"影片載入失敗:\n{video_path}")
                error_label.setStyleSheet("""
                    QLabel {
                        color: #ff6b6b;
                        font-size: 12px;
                        text-align: center;
                        padding: 20px;
                        border: 2px dashed #ff6b6b;
                        border-radius: 5px;
                        background-color: #2b2b2b;
                    }
                """)
                error_label.setAlignment(Qt.AlignCenter)
                right_layout.addWidget(error_label)
        else:
            # 如果路徑為空，顯示提示信息
            no_video_label = QLabel("影片檔案路徑錯誤")
            no_video_label.setStyleSheet("""
                QLabel {
                    color: #ffa726;
                    font-size: 14px;
                    text-align: center;
                    padding: 50px;
                    border: 2px dashed #ffa726;
                    border-radius: 5px;
                    background-color: #2b2b2b;
                }
            """)
            no_video_label.setAlignment(Qt.AlignCenter)
            right_layout.addWidget(no_video_label)
    else:
        # 如果沒有影片，顯示提示信息
        no_video_label = QLabel("暫無教學影片")
        no_video_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 14px;
                text-align: center;
                padding: 50px;
                border: 2px dashed #555555;
                border-radius: 5px;
                background-color: #2b2b2b;
            }
        """)
        no_video_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(no_video_label)
    
    # 總是添加影片播放器，即使載入失敗也能顯示錯誤狀態
    right_layout.addWidget(video_player)
    splitter.addWidget(right_widget)
    
    # 設置分割器比例（左側40%，右側60%）
    splitter.setSizes([400, 600])
    
    # 速度選擇
    speed_label = QLabel("選擇速度:")
    speed_combo = QComboBox()
    speed_combo.addItems(["慢", "正常", "快", "極限快"])  # 添加"極限快"選項
    dialog_layout.addWidget(speed_label)
    dialog_layout.addWidget(speed_combo)
    
    # 發球數量選擇
    count_label = QLabel("選擇發球數量:")
    count_combo = QComboBox()
    count_combo.addItems(["10顆", "20顆", "30顆"])
    dialog_layout.addWidget(count_label)
    dialog_layout.addWidget(count_combo)
    
    # 動態設置對話框大小，根據螢幕尺寸調整（考慮影片播放器需要更大空間）
    from PyQt5.QtWidgets import QApplication
    screen = QApplication.desktop().screenGeometry()
    dialog_width = min(1000, int(screen.width() * 0.7))  # 增加寬度以容納影片播放器
    dialog_height = min(700, int(screen.height() * 0.7))  # 增加高度
    dialog.resize(dialog_width, dialog_height)
    dialog.setMinimumSize(800, 500)  # 設定最小尺寸

    # 確認和停止按鈕佈局
    button_layout = QHBoxLayout()
    confirm_button = QPushButton("開始發球")
    button_layout.addWidget(confirm_button)

    stop_button = QPushButton("停止")
    stop_button.clicked.connect(self.stop_training)
    button_layout.addWidget(stop_button)

    dialog_layout.addLayout(button_layout)

    # 以非阻塞方式處理開始，保持小視窗不關閉，保留停止鍵可用
    def on_confirm_start():
        # 若已有訓練進行中則忽略
        if hasattr(self, 'training_task') and self.training_task and not self.training_task.done():
            try:
                self.log_message("已有訓練進行中，請先停止後再開始")
            except Exception:
                pass
            return

        selected_speed = speed_combo.currentText()
        selected_count = count_combo.currentText()
        try:
            self.log_message(f"已確認設定，準備開始：速度={selected_speed}，球數={selected_count}")
        except Exception:
            pass

        # 禁用確認鍵避免重複觸發，並啟動訓練任務
        confirm_button.setEnabled(False)
        
        # 創建基礎訓練執行器並啟動訓練
        if not hasattr(self, 'basic_training_executor'):
            self.basic_training_executor = create_basic_training_executor(self)
        
        # 使用執行器啟動訓練
        success = self.basic_training_executor.start_selected_training(section, selected_speed, selected_count)
        
        if success:
            # 設置訓練任務引用
            self.training_task = self.basic_training_executor.training_task
        else:
            # 如果啟動失敗，恢復按鈕狀態
            confirm_button.setEnabled(True)

    confirm_button.clicked.connect(on_confirm_start)

    # 紀錄對話框開啟
    try:
        self.log_message(f"已選擇球路: {section}，開啟速度/球數設定視窗")
    except Exception:
        pass

    # 添加對話框關閉時的清理邏輯
    def on_dialog_finished():
        if hasattr(video_player, 'cleanup'):
            video_player.cleanup()
    
    dialog.finished.connect(on_dialog_finished)
    
    # 以 modeless 方式顯示並保留參考，避免被垃圾回收
    self._basic_training_dialog = dialog
    dialog.show()

async def start_selected_training(self, section, speed, count):
    """開始選擇的基礎訓練（UI 層面的處理）"""
    if not hasattr(self, 'basic_training_executor'):
        self.basic_training_executor = create_basic_training_executor(self)
    
    # 使用執行器處理訓練邏輯
    self.basic_training_executor.start_selected_training(section, speed, count)

        

def practice_specific_shot(self, shot_name, count, interval):
    """練習特定球種（UI 層面的處理）"""
    if not hasattr(self, 'basic_training_executor'):
        self.basic_training_executor = create_basic_training_executor(self)
    
    self.basic_training_executor.practice_specific_shot(shot_name, count, interval)

def practice_level_programs(self, level, programs_data):
    """練習特定等級的所有訓練套餐（UI 層面的處理）"""
    if not hasattr(self, 'basic_training_executor'):
        self.basic_training_executor = create_basic_training_executor(self)
    
    self.basic_training_executor.practice_level_programs(level, programs_data)

def get_section_by_shot_name(self, shot_name):
    """取得球種名稱對應的區域代碼"""
    from core.parsers import get_section_by_shot_name
    return get_section_by_shot_name(shot_name)

def send_shot_command(self, section):
    """
    發送發球指令的邏輯。
    
    :param section: 發球的區域代碼
    """
    if not hasattr(self, 'device_service'):
        self.device_service = DeviceService(self, simulate=False)
    if not self.device_service.is_connected():
        self.log_message("請先連接發球機")
        return
    self.create_async_task(self.device_service.send_shot(section))
    self.log_message(f"發送指令到區域: {section}")

def create_area_buttons(self, layout, start_sec, end_sec):
    """創建指定區域範圍的按鈕"""
    # 讀取區域配置
    area_data = read_data_from_json(AREA_FILE_PATH)
    if not area_data:
        return
    
    row, col = 0, 0
    max_cols = 5
    
    # 創建指定範圍的按鈕
    for sec_num in range(start_sec, end_sec + 1):
        for sub_num in [1, 2]:  # secX_1 和 secX_2
            section = f"sec{sec_num}_{sub_num}"
            if section in area_data["section"]:
                # 創建按鈕
                button = QPushButton(section)
                button.setMaximumWidth(100)
                button.setMaximumHeight(40)
                
                # 設置按鈕樣式
                if sub_num == 1:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border-radius: 3px;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #45a049;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #FF9800;
                            color: white;
                            border-radius: 3px;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #F57C00;
                        }
                    """)
                
                button.clicked.connect(lambda checked, s=section: self.handle_shot_button_click(s))
                layout.addWidget(button, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

def create_shot_buttons(self, layout):
    """創建發球按鈕（保留原有方法以備用）"""
    # 讀取區域配置
    area_data = read_data_from_json(AREA_FILE_PATH)
    if not area_data:
        return
    
    # 創建按鈕網格
    row, col = 0, 0
    max_cols = 5
    
    for section in sorted(area_data["section"].keys()):
        button = QPushButton(section)
        button.setMaximumWidth(120)
        button.clicked.connect(lambda checked, s=section: self.handle_shot_button_click(s))
        layout.addWidget(button, row, col)
        
        col += 1
        if col >= max_cols:
            col = 0
            row += 1


@asyncSlot()
async def send_single_shot(self, section):
    """發送單球"""
    if not hasattr(self, 'device_service'):
        self.device_service = DeviceService(self, simulate=False)
    if not self.device_service.is_connected():
        self.log_message("請先連接發球機")
        return

    await self.device_service.send_shot(section)

@asyncSlot()
async def start_training(self):
    """開始訓練"""
    self.log_message("準備開始課程訓練...")
    if not hasattr(self, 'device_service'):
        self.device_service = DeviceService(self, simulate=False)
    if not self.device_service.is_connected():
        self.log_message("請先連接發球機")
        return

    current_program_id = self.program_combo.currentData()
    if not current_program_id:
        # 後備：嘗試以文字匹配目前等級的球路描述
        current_text = self.program_combo.currentText()
        level_text = self.level_combo.currentText() if hasattr(self, 'level_combo') else None
        level_id_map = {
            "2": "level2_basic",
            "3": "level3_intermediate",
            "4": "level4_advanced",
            "5": "level5_movement",
            "6": "level6_multi_point",
            "7": "level7_advanced_skills",
        }
        level_program_id = level_id_map.get(level_text)
        section = None
        if level_program_id and self.programs_data and level_program_id in self.programs_data.get("training_programs", {}):
            for shot in self.programs_data["training_programs"][level_program_id].get("shots", []):
                if shot.get("description") == current_text:
                    section = shot.get("section")
                    break
        if section:
            current_program_id = {"type": "single_shot", "section": section, "description": current_text}
            self.log_message(f"未取得 userData，已用文字匹配到 section={section}")
        else:
            self.log_message("請選擇訓練套餐")
            return

    # 讀取速度與球數（使用課程頁面上的選擇，不跳出視窗）
    speed_text = getattr(self, 'speed_combo', None).currentText() if hasattr(self, 'speed_combo') else None
    count_text = getattr(self, 'ball_count_combo', None).currentText() if hasattr(self, 'ball_count_combo') else None

    def map_speed_to_interval(text):
        if text == "慢":
            return 4
        if text == "正常":
            return 3.5
        if text == "快":
            return 2.5
        if text == "極限快":
            return 1.4
        return 3.5

    def map_count(text):
        if text == "10顆":
            return 10
        if text == "20顆":
            return 20
        if text == "30顆":
            return 30
        return 10

    interval_override = map_speed_to_interval(speed_text)
    balls_override = map_count(count_text)

    # 單一球路模式：直接依大視窗選擇開始訓練（與手動/基礎一致，直接 await BLE 發送）
    if isinstance(current_program_id, dict) and current_program_id.get("type") == "single_shot":
        section = current_program_id.get("section")
        if not section:
            self.log_message("所選球路資料有誤")
            return
        # 使用基礎訓練執行器處理單一球路
        self.log_message(f"開始執行單一球路: {current_program_id.get('description', section)} | 速度:{speed_text} | 間隔:{interval_override}s | 球數:{balls_override}")
        speed_label = speed_text if speed_text else "正常"
        count_label = count_text if count_text else "10顆"
        
        # 創建基礎訓練執行器並啟動訓練
        if not hasattr(self, 'basic_training_executor'):
            self.basic_training_executor = create_basic_training_executor(self)
        
        # 使用執行器啟動訓練
        success = self.basic_training_executor.start_selected_training(section, speed_label, count_label)
        
        if success:
            # 設置訓練任務引用
            self.training_task = self.basic_training_executor.training_task
        return
    else:
        # 套餐模式
        program = self.programs_data["training_programs"][current_program_id]
        
        # 設置UI狀態
        self.start_training_button.setEnabled(False)
        self.stop_training_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.stop_flag = False
        self.progress_bar.setMaximum(program['repeat_times'])
        self.progress_bar.setValue(0)
        self.log_message(f"開始執行: {program['name']}")
        
        # 直接使用execute_training方法
        self.training_task = self.create_async_task(self.execute_training(program, interval_override, balls_override))

    # 執行訓練
    if hasattr(self, 'training_task') and self.training_task is not None:
        try:
            await self.training_task
        except asyncio.CancelledError:
            self.log_message("訓練已取消")

async def execute_training(self, program, interval_override=None, balls_override=None):
    """執行訓練套餐
    - 若提供 interval_override 與 balls_override，則依使用者設定以固定間隔執行指定顆數，循環套用 program['shots']
    - 否則使用原本套餐內每顆的 delay_seconds 與 repeat_times
    """
    try:
        # 使用者指定球數與間隔的模式
        if interval_override and balls_override:
            shots = program['shots']
            total = balls_override
            for i in range(total):
                if self.stop_flag:
                    raise asyncio.CancelledError()
                shot = shots[i % len(shots)]
                section = shot['section']
                if section == "random" and "random_sections" in program:
                    import random
                    section = random.choice(program["random_sections"])
                await self.device_service.send_shot(section)
                self.log_message(f"已發送 {section} 第 {i + 1} 顆")
                self.progress_bar.setValue(i + 1)
                await asyncio.sleep(interval_override)
            self.log_message("訓練完成！")
            return

        # 預設模式：照套餐 delay 與 repeat_times
        for repeat in range(program['repeat_times']):
            if self.stop_flag:
                raise asyncio.CancelledError()

            self.log_message(f"第 {repeat + 1} 輪訓練")

            for shot in program['shots']:
                if self.stop_flag:
                    raise asyncio.CancelledError()
                section = shot['section']
                if section == "random" and "random_sections" in program:
                    import random
                    section = random.choice(program["random_sections"])
                await self.device_service.send_shot(section)
                self.log_message(f"已發送 {section}")
                await asyncio.sleep(shot['delay_seconds'])

            self.progress_bar.setValue(repeat + 1)

        self.log_message("訓練完成！")

    except asyncio.CancelledError:
        self.log_message("訓練已停止")
    except Exception as e:
        self.log_message(f"訓練執行失敗: {e}")
    finally:
        self.start_training_button.setEnabled(True)
        self.stop_training_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.training_task = None

async def execute_single_shot(self, section, interval_override, balls_override):
    """以固定間隔發送固定顆數的單一球路"""
    try:
        if not interval_override or not balls_override:
            self.log_message("請選擇發球間隔與球數")
            return
        self.log_message(f"execute_single_shot: section={section}, interval={interval_override}, balls={balls_override}")
        if not hasattr(self, 'device_service'):
            self.device_service = DeviceService(self, simulate=False)
        if not self.device_service.is_connected():
            self.log_message("execute_single_shot: 未連接發球機")
            return
        total = balls_override
        for i in range(total):
            if self.stop_flag:
                raise asyncio.CancelledError()
            result = await self.device_service.send_shot(section)
            if not result:
                self.log_message("execute_single_shot: 發送指令未成功 (returned False)")
            self.progress_bar.setValue(i + 1)
            await asyncio.sleep(interval_override)
        self.log_message("訓練完成！")
    except asyncio.CancelledError:
        self.log_message("訓練已停止")
    except Exception as e:
        self.log_message(f"訓練執行失敗: {e}")
    finally:
        self.start_training_button.setEnabled(True)
        self.stop_training_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.training_task = None

def stop_training(self):
    """停止訓練"""
    self.stop_flag = True
    try:
        if self.training_task and not self.training_task.done():
            self.training_task.cancel()
        # 立即反饋 UI 狀態，避免用戶以為按鈕沒作用
        self.start_training_button.setEnabled(True)
        self.stop_training_button.setEnabled(False)
        self.progress_bar.setVisible(False)
    except Exception:
        pass
    self.log_message("正在停止訓練...")

def on_start_training_button_clicked(self):
    # start_training 已以 @asyncSlot 裝飾，直接呼叫即可由 qasync 建立任務
    self.start_training()
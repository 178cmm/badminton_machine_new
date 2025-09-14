import asyncio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox, QTabWidget, QProgressBar, QDialog, QGridLayout, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt
from commands import read_data_from_json
import time
from qasync import asyncSlot

AREA_FILE_PATH = "area.json"
DISCRIPTION_FILE_PATH = "discription.txt"

def create_basic_training_tab(self):
    """創建基礎訓練標籤頁"""
    basic_training_widget = QWidget()
    layout = QVBoxLayout(basic_training_widget)
    
    # 創建按鈕網格
    button_grid = QGridLayout()
    
    # 基礎訓練項目
    basic_trainings = [
        ("正手高遠球", "sec25_1"),
        ("反手高遠球", "sec21_1"),
        ("正手切球", "sec25_1"),
        ("反手切球", "sec21_1"),
        ("正手殺球", "sec25_1"),
        ("反手殺球", "sec21_1"),
        ("正手平抽球", "sec15_1"),
        ("反手平抽球", "sec11_1"),
        ("正手小球", "sec5_1"),
        ("反手小球", "sec1_1"),
        ("正手挑球", "sec5_1"),
        ("反手挑球", "sec1_1"),
        ("平推球", "sec13_1"),
        ("正手接殺球", "sec20_1"),
        ("反手接殺球", "sec16_1"),
        ("近身接殺", "sec18_1")
    ]
    
    # 建立 section 對應名稱，供描述顯示使用
    self.section_to_name = {}

    # 創建按鈕
    for i, (name, section) in enumerate(basic_trainings):
        self.section_to_name[section] = name
        button = QPushButton(name)
        button.clicked.connect(lambda checked, s=section, n=name: self.select_basic_training(s, n))
        row, col = divmod(i, 4)  # 4列
        button_grid.addWidget(button, row, col)
    
    layout.addLayout(button_grid)
    
    self.tab_widget.addTab(basic_training_widget, "基礎訓練")

    
def select_basic_training(self, section, shot_name=None):
    """選擇基礎訓練項目後進階選擇速度和發球數量"""
    # 彈出對話框讓用戶選擇速度和發球數量
    dialog = QDialog(self)
    dialog.setWindowTitle("選擇訓練設置")
    dialog_layout = QVBoxLayout(dialog)

    # 解析 discription.txt 並載入描述
    def parse_discriptions(file_path):
        mapping = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.rstrip('\n') for line in f]
        except Exception:
            return mapping
        current_title = None
        current_block_lines = []
        def flush_block():
            if current_title is not None:
                # 去除尾端空行
                while current_block_lines and current_block_lines[-1].strip() == "":
                    current_block_lines.pop()
                mapping[current_title] = "\n".join(current_block_lines).strip()
        for line in lines:
            if line.strip() == "":
                flush_block()
                current_title = None
                current_block_lines = []
                continue
            if current_title is None:
                current_title = line.strip()
                current_block_lines = []
            else:
                current_block_lines.append(line)
        flush_block()
        return mapping

    if not hasattr(self, 'basic_discription_map'):
        self.basic_discription_map = parse_discriptions(DISCRIPTION_FILE_PATH)

    # 顯示描述區塊
    display_name = shot_name or getattr(self, 'section_to_name', {}).get(section, None)
    if display_name:
        try:
            dialog.setWindowTitle(f"選擇訓練設置 - {display_name}")
        except Exception:
            pass
    desc_title = QLabel("項目說明:")
    dialog_layout.addWidget(desc_title)
    desc_text = QTextEdit()
    desc_text.setReadOnly(True)
    description_body = self.basic_discription_map.get(display_name or "", "暫無說明")
    if display_name and description_body and not description_body.startswith(display_name):
        full_text = f"{display_name}\n" + description_body
    else:
        full_text = description_body if description_body else (display_name or section)
    desc_text.setText(full_text)
    desc_text.setMinimumHeight(220)
    dialog_layout.addWidget(desc_text)
    
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
    
    dialog.setFixedSize(530, 480)  # 設置對話框大小，容納描述與設定

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
        self.training_task = asyncio.create_task(self.start_selected_training(section, selected_speed, selected_count))

        # 任務結束後恢復確認鍵狀態
        def _restore_after_done(_):
            try:
                confirm_button.setEnabled(True)
            except Exception:
                pass

        self.training_task.add_done_callback(_restore_after_done)

    confirm_button.clicked.connect(on_confirm_start)

    # 紀錄對話框開啟
    try:
        self.log_message(f"已選擇球路: {section}，開啟速度/球數設定視窗")
    except Exception:
        pass

    # 以 modeless 方式顯示並保留參考，避免被垃圾回收
    self._basic_training_dialog = dialog
    dialog.show()

async def start_selected_training(self, section, speed, count):
    """
    開始選擇的基礎訓練
    """
    self.log_message(f"開始訓練: {section}, 速度: {speed}, 發球數量: {count}")

    # 設定間隔時間
    interval = 4 if speed == "慢" else 3.5 if speed == "正常" else 2.5 if speed == "快" else 1.4  
    # 設定發球次數
    num_shots = 10 if count == "10顆" else 20 if count == "20顆" else 30

    # UI 狀態（與課程頁面一致）
    self.start_training_button.setEnabled(False)
    self.stop_training_button.setEnabled(True)
    self.progress_bar.setVisible(True)
    self.progress_bar.setMaximum(num_shots)
    self.progress_bar.setValue(0)

    # 開始發球（與手動/單球一致：直接 await 藍牙發送）
    self.stop_flag = False
    sent_count = 0
    try:
        for _ in range(num_shots):
            if self.stop_flag:
                self.log_message("訓練已被停止")
                break
            if not self.bluetooth_thread or not self.bluetooth_thread.is_connected:
                self.log_message("請先連接發球機")
                break
            try:
                await self.bluetooth_thread.send_shot(section)
            except Exception as e:
                self.log_message(f"發球失敗: {e}")
                break
            sent_count += 1
            self.log_message(f"已發送 {section} 第 {sent_count} 顆")
            self.progress_bar.setValue(sent_count)
            await asyncio.sleep(interval)
        self.log_message(f"完成 {section} 的訓練，共發送 {sent_count} 顆球")
    finally:
        self.start_training_button.setEnabled(True)
        self.stop_training_button.setEnabled(False)
        self.progress_bar.setVisible(False)

        

def practice_specific_shot(self, shot_name, count, interval):
    """
    根據用戶的指令，練習特定的擊球項目。
    
    :param shot_name: 擊球項目的名稱，例如 "正手平抽球"
    :param count: 發球的數量
    :param interval: 每顆球之間的間隔時間（秒）
    """
    # 根據 shot_name 找到對應的 section
    section = self.get_section_by_shot_name(shot_name)
    if not section:
        print(f"無法找到擊球項目: {shot_name}")
        return
    
    # 開始練習，確保在發送指定數量的球後停止
    for i in range(count):
        self.send_shot_command(section)
        print(f"已發送 {shot_name} 第 {i+1} 顆")
        time.sleep(interval)
    print(f"完成 {shot_name} 的練習，共發送 {count} 顆球")
    # 確保方法結束後不再發球
    return

def practice_level_programs(self, level, programs_data):
    """
    根據用戶的指令，練習特定等級的所有訓練套餐。
    
    :param level: 等級，例如 2
    :param programs_data: 訓練套餐的數據
    """
    # 獲取該等級的所有訓練套餐
    level_key = f"level{level}_basic"
    if level_key not in programs_data["program_categories"]:
        print(f"無法找到等級 {level} 的訓練套餐")
        return
    
    # 遍歷並練習每個套餐
    for program_id in programs_data["program_categories"][level_key]:
        if program_id in programs_data["training_programs"]:
            program = programs_data["training_programs"][program_id]
            print(f"開始練習套餐: {program['name']}")
            for shot in program['shots']:
                self.send_shot_command(shot['section'])
                print(f"已發送 {shot['description']}")
                time.sleep(shot['delay_seconds'])

def get_section_by_shot_name(self, shot_name):
    """
    將擊球名稱映射到相應的區域代碼。
    
    :param shot_name: 擊球項目的名稱
    :return: 對應的區域代碼
    """
    # 更新映射表，確保包含所有擊球名稱
    shot_to_section_map = {
        "正手平抽球": "sec15_1",
        "反手平抽球": "sec11_1",
        "正手高遠球": "sec25_1",
        "反手高遠球": "sec21_1",
        "正手切球": "sec25_1",
        "反手切球": "sec21_1",
        "正手殺球": "sec25_1",
        "反手殺球": "sec21_1",
        "正手小球": "sec5_1",
        "反手小球": "sec1_1",
        "正手挑球": "sec5_1",
        "反手挑球": "sec1_1",
        "平推球": "sec13_1",
        "正手接殺球": "sec20_1",
        "反手接殺球": "sec16_1",
        "近身接殺": "sec18_1"
    }
    return shot_to_section_map.get(shot_name)

def send_shot_command(self, section):
    """
    發送發球指令的邏輯。
    
    :param section: 發球的區域代碼
    """
    if not self.bluetooth_thread:
        self.log_message("請先掃描設備")
        return
    
    if not self.bluetooth_thread.is_connected:
        self.log_message("請先連接發球機")
        return
    
    # 調用 BluetoothThread 的 send_shot 方法
    asyncio.create_task(self.bluetooth_thread.send_shot(section))
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
                
                button.clicked.connect(lambda checked, s=section: self.send_single_shot(s))
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
        button.clicked.connect(lambda checked, s=section: self.send_single_shot(s))
        layout.addWidget(button, row, col)
        
        col += 1
        if col >= max_cols:
            col = 0
            row += 1


@asyncSlot()
async def send_single_shot(self, section):
    """發送單球"""
    if not self.bluetooth_thread:
        self.log_message("請先掃描設備")
        return

    if not self.bluetooth_thread.is_connected:
        self.log_message("請先連接發球機")
        return

    await self.bluetooth_thread.send_shot(section)

@asyncSlot()
async def start_training(self):
    """開始訓練"""
    self.log_message("準備開始課程訓練...")
    if not self.bluetooth_thread:
        self.log_message("請先掃描設備")
        return

    if not self.bluetooth_thread.is_connected:
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
        # 直接沿用基礎訓練的已驗證流程（建立任務，不在此 await）
        self.log_message(f"開始執行單一球路: {current_program_id.get('description', section)} | 速度:{speed_text} | 間隔:{interval_override}s | 球數:{balls_override}")
        speed_label = speed_text if speed_text else "正常"
        count_label = count_text if count_text else "10顆"
        self.training_task = asyncio.create_task(self.start_selected_training(section, speed_label, count_label))
        return
    else:
        # 套餐模式
        program = self.programs_data["training_programs"][current_program_id]
        # 保留原套餐模式（若未來需要整套執行）
        self.start_training_button.setEnabled(False)
        self.stop_training_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.stop_flag = False
        self.progress_bar.setMaximum(program['repeat_times'])
        self.progress_bar.setValue(0)
        self.log_message(f"開始執行: {program['name']}")
        self.training_task = asyncio.create_task(self.execute_training(program))

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
                await self.bluetooth_thread.send_shot(section)
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
                await self.bluetooth_thread.send_shot(section)
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
        if not self.bluetooth_thread:
            self.log_message("execute_single_shot: 未初始化藍牙，請先掃描設備")
            return
        if not self.bluetooth_thread.is_connected:
            self.log_message("execute_single_shot: 未連接發球機")
            return
        total = balls_override
        for i in range(total):
            if self.stop_flag:
                raise asyncio.CancelledError()
            result = await self.bluetooth_thread.send_shot(section)
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
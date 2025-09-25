from commands import read_data_from_json
from PyQt5.QtWidgets import QPushButton

PROGRAMS_FILE_PATH = "training_programs.json"


def load_programs(self):
    """載入訓練套餐"""
    self.programs_data = read_data_from_json(PROGRAMS_FILE_PATH)
    if not self.programs_data:
        self.log_message("無法載入訓練套餐配置")
        return
    
    self.update_program_list()
    
def update_program_list(self):
    """更新套餐列表"""
    if not self.programs_data:
        return
        
    # 使用等級作為選單選項
    self.program_combo.clear()
    current_level = self.level_combo.currentText()
    # 將所選等級的套餐展開為單一球路選項
    level_to_program_ids_map = {
        "2": ["level2_basic"],
        "3": ["level3_intermediate"],
        "4": ["level4_advanced"],
        "5": ["level5_movement"],
        "6": ["level6_multi_point"],
        "7": ["level7_advanced_skills"],
    }
    program_ids = level_to_program_ids_map.get(current_level, [])
    for program_id in program_ids:
        program = self.programs_data["training_programs"].get(program_id)
        if not program:
            continue
        for shot in program.get("shots", []):
            item_text = shot.get("description", shot.get("section", ""))
            # 使用 dict 作為 userData，標示為單一球路模式
            self.program_combo.addItem(item_text, {
                "type": "single_shot",
                "section": shot.get("section"),
                "description": shot.get("description", "")
            })

    # 若有選項，預設選中第一個，避免沒有 currentData 的情況
    if self.program_combo.count() > 0 and self.program_combo.currentIndex() < 0:
        self.program_combo.setCurrentIndex(0)
    
    # 根據是否有可選項啟用開始按鈕
    if hasattr(self, 'start_training_button'):
        self.start_training_button.setEnabled(self.program_combo.count() > 0)

    self.update_program_description()

def update_program_description(self):
    """更新套餐描述，並提供發球模式和發球數量選擇"""
    if not self.programs_data:
        return
        
    current_program_id = self.program_combo.currentData()
    # 單一球路（各等級展開模式）
    if isinstance(current_program_id, dict) and current_program_id.get("type") == "single_shot":
        desc = current_program_id.get("description", "單一球路")
        section = current_program_id.get("section", "")
        description = f"已選擇單一球路:\n{desc} ({section})\n\n請從下方選擇發球間隔/速度與發球數量，然後開始訓練。"
        self.program_description.setText(description)
        if hasattr(self, 'start_training_button'):
            self.start_training_button.setEnabled(True)
        return

    # 非展開模式（若未來保留套餐選擇時使用）
    self.program_description.setText("請選擇訓練套餐或球路")
    if hasattr(self, 'start_training_button'):
        self.start_training_button.setEnabled(False)

def create_area_buttons(self, layout, start_sec, end_sec, handler=None):
    """建立區域按鈕，允許注入自訂 handler(section)"""
    row = 0
    col = 0
    max_cols = 5
    for section_num in range(start_sec, end_sec + 1):
        # 創建兩個按鈕：sec1_1 和 sec1_2
        section_1 = f"sec{section_num}_1"
        section_2 = f"sec{section_num}_2"
        
        # 第一個按鈕 (sec1_1)
        button_1 = QPushButton(section_1)
        if handler is None:
            # 回退到預設處理器
            button_1.clicked.connect(lambda checked, s=section_1: self.handle_shot_button_click(s))
        else:
            button_1.clicked.connect(lambda checked, s=section_1: handler(s))
        layout.addWidget(button_1, row, col)
        col += 1
        
        # 第二個按鈕 (sec1_2)
        button_2 = QPushButton(section_2)
        if handler is None:
            # 回退到預設處理器
            button_2.clicked.connect(lambda checked, s=section_2: self.handle_shot_button_click(s))
        else:
            button_2.clicked.connect(lambda checked, s=section_2: handler(s))
        layout.addWidget(button_2, row, col)
        col += 1
        
        if col >= max_cols:
            col = 0
            row += 1
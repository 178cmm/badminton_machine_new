"""
羽毛球發球機控制系統 GUI 模組

這個模組包含所有與使用者介面相關的程式碼：
- main_gui.py: 主要的 GUI 類別和視窗設定
- ui_connection.py: 藍牙連接控制介面
- ui_training.py: 基礎訓練控制介面
- ui_course.py: 課程訓練控制介面
- ui_control.py: 手動控制介面
- ui_log.py: 系統日誌介面
- ui_utils.py: GUI 工具函數
- ui_text_input.py: 文字輸入控制介面
- ui_voice.py: 語音控制介面
- ui_warmup.py: 熱身控制介面
- ui_advanced_training.py: 進階訓練控制介面
"""

from .main_gui import BadmintonLauncherGUI

__all__ = ['BadmintonLauncherGUI']

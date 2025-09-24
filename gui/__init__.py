"""
羽毛球發球機控制系統 GUI 模組

此模組於 CLI simulate 環境不需要載入 PyQt5。
"""

# 直接導出，避免吞掉實際的 ImportError，方便偵錯
from .main_gui import BadmintonLauncherGUI  # type: ignore

__all__ = ["BadmintonLauncherGUI"]

"""
羽毛球發球機控制系統 GUI 模組

此模組於 CLI simulate 環境不需要載入 PyQt5。
"""

# 提供惰性載入，避免在無 PyQt5 環境下導入
try:
    from .main_gui import BadmintonLauncherGUI  # type: ignore
    __all__ = ['BadmintonLauncherGUI']
except Exception:
    __all__ = []

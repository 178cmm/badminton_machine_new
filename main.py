
# Entry point launcher
import sys
from PyQt5.QtWidgets import QApplication
from qasync import QEventLoop
import asyncio
from app2 import BadmintonLauncherGUI

def main():
    """主程式"""
    app = QApplication(sys.argv)
    
    # 創建事件循環
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 創建主視窗
    window = BadmintonLauncherGUI()
    window.show()
    
    # 運行應用程式
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main() 
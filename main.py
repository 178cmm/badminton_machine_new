
#!/usr/bin/env python3
"""
🏸 羽球發球機控制系統主程式
Entry point launcher - 修復版本，避免 segfault 問題
"""

import sys
import signal
import logging

# 設定基本日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_signal_handlers(app):
    """設定信號處理器，優雅地處理程式終止"""
    def signal_handler(signum, frame):
        logger.info(f"收到信號 {signum}，正在退出...")
        app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """主程式 - 修復版本"""
    try:
        logger.info("🚀 啟動羽球發球機控制系統...")
        
        # 匯入必要模組
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt, QTimer
        import qasync
        import asyncio
        from gui import BadmintonLauncherGUI
        
        # 創建應用程式
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        
        # 設定信號處理
        setup_signal_handlers(app)
        
        # 創建事件循環
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        logger.info("✅ 事件循環創建完成")
        
        # 創建主視窗
        window = BadmintonLauncherGUI()
        window.show()
        window.raise_()  # 確保視窗在最前面
        
        logger.info("✅ 主視窗創建並顯示完成")
        
        logger.info("🎯 開始運行事件循環...")
        
        # 使用更安全的事件循環運行方式，避免定時器問題
        try:
            with loop:
                # 使用 app.exec() 而不是 loop.run_forever()，避免段錯誤
                app.exec_()
                logger.info("應用程式正常退出")
                return 0
        except KeyboardInterrupt:
            logger.info("收到鍵盤中斷，正在退出...")
            return 0
        except Exception as e:
            logger.error(f"事件循環運行時發生錯誤: {e}")
            return 1
            
    except ImportError as e:
        logger.error(f"模組匯入失敗: {e}")
        print("❌ 請確認所有依賴套件都已正確安裝：")
        print("   pip install -r requirements.txt")
        return 1
    except Exception as e:
        logger.error(f"程式啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ 程式啟動失敗: {e}")
        sys.exit(1) 
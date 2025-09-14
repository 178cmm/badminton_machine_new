"""
文字命令執行器

這個模組負責執行解析後的命令，處理與 GUI 的互動和命令的實際執行。
"""

from typing import Dict, Any, Optional
from ..parsers import parse_command


class TextCommandExecutor:
    """文字命令執行器類別"""
    
    def __init__(self, gui_instance):
        """
        初始化執行器
        
        Args:
            gui_instance: GUI 主類別的實例
        """
        self.gui = gui_instance
    
    def execute_text_command(self, command_text: str) -> bool:
        """
        執行文字命令
        
        Args:
            command_text: 使用者輸入的文字命令
            
        Returns:
            是否成功執行命令
        """
        # 先將使用者輸入寫入聊天視窗
        self._log_user_input(command_text)
        
        # 解析命令
        command = parse_command(command_text, getattr(self.gui, '_advanced_specs', None))
        
        if command:
            # 顯示解析結果
            self._log_system_response(f"已解析 → {command}")
            
            # 執行命令
            self._execute_parsed_command(command)
            return True
        else:
            # 無法解析的指令
            self._log_error("無法解析的指令，請再試一次或換種說法")
            return False
    
    def _log_user_input(self, command_text: str):
        """記錄使用者輸入到聊天視窗"""
        try:
            if hasattr(self.gui, 'text_chat_log'):
                self.gui.text_chat_log.append(f"你: {command_text}")
                self.gui.text_chat_log.ensureCursorVisible()
        except Exception:
            pass
    
    def _log_system_response(self, message: str):
        """記錄系統回應到聊天視窗"""
        try:
            if hasattr(self.gui, 'text_chat_log'):
                self.gui.text_chat_log.append(f"系統: {message}")
                self.gui.text_chat_log.ensureCursorVisible()
        except Exception:
            pass
    
    def _log_error(self, message: str):
        """記錄錯誤訊息"""
        try:
            self.gui.log_message(message)
        except Exception:
            print(message)
    
    def _execute_parsed_command(self, command: Dict[str, Any]):
        """執行解析後的命令"""
        try:
            # 使用 GUI 的 execute_training_command 方法
            programs_data = getattr(self.gui, 'programs_data', None)
            self.gui.execute_training_command(command, programs_data)
        except Exception as e:
            self._log_error(f"執行命令時發生錯誤: {str(e)}")


def create_text_command_executor(gui_instance) -> TextCommandExecutor:
    """
    建立文字命令執行器的工廠函數
    
    Args:
        gui_instance: GUI 主類別的實例
        
    Returns:
        TextCommandExecutor 實例
    """
    return TextCommandExecutor(gui_instance)

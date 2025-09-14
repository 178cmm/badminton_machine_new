"""
模擬對打模式解析器

這個模組負責解析模擬對打模式相關的語音指令和文字指令。
"""

import re
from typing import Dict, Any, Optional, List


class SimulationParser:
    """模擬對打模式解析器類別"""
    
    def __init__(self):
        """初始化解析器"""
        self.level_keywords = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
            "7": 7, "8": 8, "9": 9, "10": 10, "11": 11, "12": 12
        }
        
        self.simulation_keywords = [
            "模擬對打", "對打模式", "對打", "模擬", "對戰", "對練",
            "simulation", "duel", "match", "practice"
        ]
        
        self.start_keywords = [
            "開始", "啟動", "執行", "進行", "開始模擬", "開始對打",
            "start", "begin", "run", "execute"
        ]
        
        self.stop_keywords = [
            "停止", "結束", "暫停", "停止模擬", "停止對打",
            "stop", "end", "pause", "quit"
        ]
        
        self.dual_machine_keywords = [
            "雙發球機", "兩台", "雙機", "雙球機", "兩台發球機",
            "dual", "two", "double", "both"
        ]
    
    def parse_simulation_command(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析模擬對打指令
        
        Args:
            text: 輸入的文字
            
        Returns:
            解析結果字典，如果無法解析則返回 None
        """
        text = text.strip().lower()
        
        # 檢查是否包含模擬對打關鍵字
        if not any(keyword in text for keyword in self.simulation_keywords):
            return None
        
        # 解析開始指令
        start_result = self._parse_start_command(text)
        if start_result:
            return start_result
        
        # 解析停止指令
        stop_result = self._parse_stop_command(text)
        if stop_result:
            return stop_result
        
        return None
    
    def _parse_start_command(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析開始模擬對打指令
        
        Args:
            text: 輸入的文字
            
        Returns:
            解析結果字典
        """
        # 檢查是否包含開始關鍵字
        if not any(keyword in text for keyword in self.start_keywords):
            return None
        
        # 提取等級
        level = self._extract_level(text)
        if level is None:
            return {
                "type": "start_simulation",
                "level": 1,  # 預設等級
                "use_dual_machine": False,
                "message": "開始模擬對打 (預設等級 1)"
            }
        
        # 檢查是否使用雙發球機
        use_dual = any(keyword in text for keyword in self.dual_machine_keywords)
        
        return {
            "type": "start_simulation",
            "level": level,
            "use_dual_machine": use_dual,
            "message": f"開始模擬對打 - 等級 {level}" + (" (雙發球機)" if use_dual else "")
        }
    
    def _parse_stop_command(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析停止模擬對打指令
        
        Args:
            text: 輸入的文字
            
        Returns:
            解析結果字典
        """
        if any(keyword in text for keyword in self.stop_keywords):
            return {
                "type": "stop_simulation",
                "message": "停止模擬對打"
            }
        return None
    
    def _extract_level(self, text: str) -> Optional[int]:
        """
        從文字中提取等級
        
        Args:
            text: 輸入的文字
            
        Returns:
            等級數字，如果找不到則返回 None
        """
        # 直接匹配關鍵字
        for keyword, level in self.level_keywords.items():
            if keyword in text:
                return level
        
        # 使用正則表達式匹配數字
        number_patterns = [
            r'等級\s*(\d+)',
            r'level\s*(\d+)',
            r'(\d+)\s*級',
            r'(\d+)\s*等'
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, text)
            if match:
                level = int(match.group(1))
                if 1 <= level <= 12:
                    return level
        
        return None
    
    def parse_level_selection(self, text: str) -> Optional[int]:
        """
        解析等級選擇
        
        Args:
            text: 輸入的文字
            
        Returns:
            等級數字，如果無法解析則返回 None
        """
        return self._extract_level(text)
    
    def get_available_levels(self) -> List[Dict[str, Any]]:
        """
        獲取可用的等級列表
        
        Returns:
            等級列表
        """
        levels = []
        
        # 等級 1-2: 初學者
        levels.extend([
            {"level": 1, "name": "初學者", "description": "全部高球，間隔 3 秒"},
            {"level": 2, "name": "初學者+", "description": "全部高球，間隔 2.5 秒"}
        ])
        
        # 等級 3-6: 中級
        levels.extend([
            {"level": 3, "name": "中級", "description": "後高前低，間隔 2.5 秒"},
            {"level": 4, "name": "中級+", "description": "後高前低，間隔 2 秒"},
            {"level": 5, "name": "中高級", "description": "後高前低，間隔 2 秒"},
            {"level": 6, "name": "中高級+", "description": "後高前低，間隔 1.5 秒"}
        ])
        
        # 等級 7-12: 高級
        levels.extend([
            {"level": 7, "name": "高級", "description": "後高中殺前低，間隔 1.5 秒"},
            {"level": 8, "name": "高級+", "description": "後高中殺前低，間隔 1 秒"},
            {"level": 9, "name": "專業級", "description": "後高中殺前低，間隔 2 秒 (支援雙發球機)"},
            {"level": 10, "name": "專業級+", "description": "後高中殺前低，間隔 1.5 秒 (支援雙發球機)"},
            {"level": 11, "name": "大師級", "description": "後高中殺前低，間隔 1.5 秒 (支援雙發球機)"},
            {"level": 12, "name": "大師級+", "description": "後高中殺前低，間隔 1 秒 (支援雙發球機)"}
        ])
        
        return levels
    
    def get_level_info(self, level: int) -> Optional[Dict[str, Any]]:
        """
        獲取特定等級的詳細信息
        
        Args:
            level: 等級數字
            
        Returns:
            等級信息字典
        """
        levels = self.get_available_levels()
        for level_info in levels:
            if level_info["level"] == level:
                return level_info
        return None
    
    def validate_level(self, level: int) -> bool:
        """
        驗證等級是否有效
        
        Args:
            level: 等級數字
            
        Returns:
            是否有效
        """
        return 1 <= level <= 12
    
    def get_simulation_help(self) -> str:
        """
        獲取模擬對打模式的幫助信息
        
        Returns:
            幫助文字
        """
        help_text = """
模擬對打模式指令說明：

開始指令：
- "開始模擬對打" 或 "開始對打"
- "模擬對打等級X" (X為1-12)
- "開始對打模式等級X"

停止指令：
- "停止模擬對打" 或 "停止對打"
- "結束模擬對打"

等級說明：
- 等級 1-2: 初學者 (全部高球)
- 等級 3-6: 中級 (後高前低)
- 等級 7-12: 高級 (後高中殺前低)
- 等級 9-12: 支援雙發球機 (功能保留)

範例：
- "開始模擬對打等級5"
- "模擬對打等級8"
- "停止對打"
        """
        return help_text.strip()


def create_simulation_parser() -> SimulationParser:
    """
    建立模擬對打解析器的工廠函數
    
    Returns:
        SimulationParser 實例
    """
    return SimulationParser()

"""
審計日誌讀取器
用於 UI simulate 面板顯示最新的指令和回覆
"""

import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime


class AuditReader:
    """審計日誌讀取器"""
    
    def __init__(self, log_file: str = "logs/commands.jsonl"):
        self.log_file = log_file
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """確保日誌目錄存在"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    def get_latest_entries(self, count: int = 10) -> List[Dict[str, Any]]:
        """獲取最新的日誌條目"""
        if not os.path.exists(self.log_file):
            return []
        
        entries = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 從最後開始讀取
                for line in reversed(lines[-count:]):
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"⚠️ 讀取審計日誌失敗：{e}")
        
        return entries
    
    def get_latest_command(self) -> Optional[Dict[str, Any]]:
        """獲取最新的指令"""
        entries = self.get_latest_entries(1)
        return entries[0] if entries else None
    
    def get_command_summary(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """獲取指令摘要"""
        return {
            "timestamp": entry.get("timestamp", ""),
            "source": entry.get("source", ""),
            "raw_text": entry.get("raw_text", ""),
            "command_type": entry.get("command", {}).get("type", ""),
            "command_payload": entry.get("command", {}).get("payload", {}),
            "result": entry.get("result", ""),
            "error": entry.get("error", ""),
            "nlu_rule": entry.get("nlu", {}).get("matcher_rule_id", ""),
            "router_state": entry.get("router", {}).get("state_after", ""),
            "target_service": entry.get("router", {}).get("target_service", "")
        }
    
    def get_recent_activity(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """獲取最近幾分鐘的活動"""
        entries = self.get_latest_entries(50)  # 獲取更多條目以篩選時間
        
        if not entries:
            return []
        
        # 解析時間戳並篩選
        recent_entries = []
        try:
            cutoff_time = datetime.now().timestamp() - (minutes * 60)
            
            for entry in entries:
                timestamp_str = entry.get("timestamp", "")
                if timestamp_str:
                    try:
                        # 嘗試解析 ISO 格式時間戳
                        entry_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
                        if entry_time >= cutoff_time:
                            recent_entries.append(self.get_command_summary(entry))
                    except ValueError:
                        # 如果時間戳格式不正確，跳過
                        continue
        except Exception as e:
            print(f"⚠️ 解析時間戳失敗：{e}")
        
        return recent_entries
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        entries = self.get_latest_entries(100)
        
        if not entries:
            return {
                "total_commands": 0,
                "success_rate": 0.0,
                "common_commands": [],
                "error_count": 0
            }
        
        total = len(entries)
        success_count = sum(1 for e in entries if e.get("result") == "ok")
        error_count = total - success_count
        
        # 統計常見指令
        command_types = {}
        for entry in entries:
            cmd_type = entry.get("command", {}).get("type", "unknown")
            command_types[cmd_type] = command_types.get(cmd_type, 0) + 1
        
        common_commands = sorted(command_types.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_commands": total,
            "success_rate": (success_count / total * 100) if total > 0 else 0.0,
            "common_commands": common_commands,
            "error_count": error_count
        }

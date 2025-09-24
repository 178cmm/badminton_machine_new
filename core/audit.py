"""
審計紀錄器：將每次解析與回覆寫入 logs/commands.jsonl。
"""

import json
import os
import time
from typing import Any, Dict, Optional


def _ensure_logs_dir() -> str:
    logs_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.isdir(logs_dir):
        try:
            os.makedirs(logs_dir, exist_ok=True)
        except Exception:
            pass
    return logs_dir


def write(raw_text: Optional[str], command_dto: Optional[Dict[str, Any]], reply_text: Optional[str], meta: Optional[Dict[str, Any]] = None) -> None:
    try:
        logs_dir = _ensure_logs_dir()
        path = os.path.join(logs_dir, "commands.jsonl")
        record = {
            "ts": time.time(),
            "raw_text": raw_text,
            "command": command_dto,
            "reply": reply_text,
            "meta": meta or {},
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # 靜默失敗，避免影響主流程
        pass



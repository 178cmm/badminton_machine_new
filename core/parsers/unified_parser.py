"""
Unified Parser

將文字/語音輸入統一解析為 CommandDTO。
"""

import re
from typing import Optional
from ..commands.dto import CommandDTO, make_command
from ..nlu.matcher import normalize_query, extract_numbers
from ..registry.program_registry import ProgramRegistry


class UnifiedParser:
    """統一解析器，負責將任何文字輸入轉換為 CommandDTO。"""

    def parse(self, text: str, source: str = "text") -> Optional[CommandDTO]:
        t = (text or "").strip()
        if not t:
            return None

        # WAKE（啟動）
        if re.fullmatch(r"(喚醒|啟動|醒來|開始|你好|哈囉)", t):
            return make_command("WAKE", source, text)

        # SCAN（掃描）
        if re.fullmatch(r"(掃描|掃描發球機|搜尋|搜尋發球機|搜索|搜索發球機)", t):
            return make_command("SCAN", source, text)

        # CONNECT（連線）
        if re.fullmatch(r"(連線|連接|配對)", t):
            return make_command("CONNECT", source, text)

        # DISCONNECT（斷開）
        if re.fullmatch(r"(斷開|斷線|解除連線|解除連接|取消配對)", t):
            return make_command("DISCONNECT", source, text)

        # 程式名稱匹配：RUN_PROGRAM_BY_NAME
        # 先解析參數
        balls, interval = extract_numbers(t)
        balls = int(balls) if balls is not None else 10
        interval = float(interval) if interval is not None else 3.0

        # 準備送入比對的查詢字串：移除數字與單位詞
        cleaned = re.sub(r"(每)?\s*\d+(?:\.\d+)?\s*(顆|秒)", "", t)
        cleaned = re.sub(r"(間隔)", "", cleaned)
        cleaned = cleaned.strip()

        # 名稱正規化後比對
        registry = ProgramRegistry()
        pid, pname, candidates = registry.find_best_match(normalize_query(cleaned))
        if pid and pname:
            return make_command("RUN_PROGRAM_BY_NAME", source, text, slots={
                "program_id": pid,
                "program_name": pname,
                "balls": balls,
                "interval_sec": interval,
            })

        # 多筆或找不到，先回 None 讓上層決定回覆（之後 Router 可處理多筆提示）
        # 為了讓 Router 能區分情境，這裡使用 meta 帶出 candidates
        if candidates:
            cmd = make_command("RUN_PROGRAM_BY_NAME", source, text, slots={
                "candidates": candidates,
                "balls": balls,
                "interval_sec": interval,
            })
            return cmd

        return None



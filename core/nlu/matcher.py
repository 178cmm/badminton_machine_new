"""
NLU Matcher

提供名稱正規化、參數抽取（顆數/間隔秒）、同義詞處理與名稱比對。
"""

import re
from typing import Optional, Tuple


_SYNONYMS = {
    "正手": ["正拍"],
    "反手": ["反拍"],
}


def normalize_query(text: str) -> str:
    t = (text or "").strip()
    # 去常見尾綴
    t = re.sub(r"(訓練|套餐|球)$", "", t)
    # 同義詞替換（簡易）
    for k, vs in _SYNONYMS.items():
        for v in vs:
            t = t.replace(v, k)
    # 去空白
    t = t.replace(" ", "")
    return t


def extract_numbers(text: str) -> Tuple[Optional[float], Optional[float]]:
    """回傳 (balls, interval_sec) 若有覆蓋則回傳數值"""
    balls = None
    interval = None

    # 顆數：12顆 / 12 顆
    m_balls = re.search(r"(\d+(?:\.\d+)?)\s*顆", text)
    if m_balls:
        try:
            balls = float(m_balls.group(1))
        except Exception:
            balls = None

    # 間隔：2.5秒 / 2 秒 / 每3秒
    m_interval = re.search(r"(?:每)?(\d+(?:\.\d+)?)\s*秒", text)
    if m_interval:
        try:
            interval = float(m_interval.group(1))
        except Exception:
            interval = None

    return balls, interval



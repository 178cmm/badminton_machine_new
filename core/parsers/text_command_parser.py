"""
自然語言命令解析器

這個模組負責將使用者的自然語言輸入解析為結構化的命令物件。
支援中文數字、口語表達、球種同義詞等多種輸入格式。
"""

import re
from typing import Dict, Optional, Any


# 中文數字映射表
_CN_NUM_MAP = {
    "零": 0, "〇": 0, "○": 0,
    "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# 球種同義詞（口語變體）→ 對應到系統既有的標準名稱
_SHOT_SYNONYMS = [
    # 高遠球
    (r"(正手).*?(高遠|後場高遠|後場)", "正手高遠球"),
    (r"(反手).*?(高遠|後場高遠|後場)", "反手高遠球"),
    # 切球（掉/吊 口語）
    (r"(正手).*?(切|掉|吊)", "正手切球"),
    (r"(反手).*?(切|掉|吊)", "反手切球"),
    # 殺球（扣殺 口語）
    (r"(正手).*?(殺|扣殺)", "正手殺球"),
    (r"(反手).*?(殺|扣殺)", "反手殺球"),
    # 平抽球（平球/抽球 口語）
    (r"(正手).*?(平抽|平球|抽)", "正手平抽球"),
    (r"(反手).*?(平抽|平球|抽)", "反手平抽球"),
    # 小球（放網前/搓 口語）
    (r"(正手).*?(小球|放小|放網|搓)", "正手小球"),
    (r"(反手).*?(小球|放小|放網|搓)", "反手小球"),
    # 挑球（挑/挑後場）
    (r"(正手).*?(挑|挑球)", "正手挑球"),
    (r"(反手).*?(挑|挑球)", "反手挑球"),
    # 平推球（推/推球 口語，無正反手）
    (r"(平推|推球|平推球)", "平推球"),
    # 接殺（擋殺 口語）
    (r"(正手).*?(接殺|擋殺)", "正手接殺球"),
    (r"(反手).*?(接殺|擋殺)", "反手接殺球"),
    (r"(近身).*?(接殺|擋殺)", "近身接殺"),
]


def _extract_number(text: str, pattern: str) -> Optional[float]:
    """從文字中提取數字"""
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _extract_speed(text: str) -> Optional[str]:
    """從文字中提取速度設定"""
    # 更豐富的口語變體 → 標準標籤
    synonyms = [
        (r"(極限|極限快|極限速度|爆速)", "極限快"),
        (r"(超快|極快|很快|飛快|爆快)", "快"),
        (r"(正常|一般|普通|中等)", "正常"),
        (r"(超慢|很慢|慢速|慢)", "慢"),
    ]
    for pat, label in synonyms:
        if re.search(pat, text):
            return label
    return None


def _parse_cn_numeral(token: str) -> int:
    """解析中文數字"""
    token = token.strip()
    if not token:
        return 0
    # 特例："十" / "二十" / "三十" ...；支援 1~30
    if token == "十":
        return 10
    # "二十"/"三十"
    if len(token) == 2 and token[1] == "十" and token[0] in _CN_NUM_MAP:
        return _CN_NUM_MAP[token[0]] * 10
    # "十X"
    if len(token) == 2 and token[0] == "十" and token[1] in _CN_NUM_MAP:
        return 10 + _CN_NUM_MAP[token[1]]
    # "X十Y"
    if len(token) == 3 and token[1] == "十" and token[0] in _CN_NUM_MAP and token[2] in _CN_NUM_MAP:
        return _CN_NUM_MAP[token[0]] * 10 + _CN_NUM_MAP[token[2]]
    # 单字數字
    if token in _CN_NUM_MAP:
        return _CN_NUM_MAP[token]
    return 0


def _extract_balls(text: str) -> Optional[int]:
    """從文字中提取球數"""
    # 阿拉伯數字
    m = re.search(r"(\d+)\s*(顆|球|次)", text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    # 中文數字
    m = re.search(r"([零○〇一二兩三四五六七八九十]{1,3})\s*(顆|球|次)", text)
    if m:
        return _parse_cn_numeral(m.group(1))
    return None


def _extract_interval_seconds(text: str) -> Optional[float]:
    """從文字中提取時間間隔"""
    # 直接數值（支援小數）：每 1.5 秒 / 1.5 秒 / 間隔 1.5 秒
    val = (_extract_number(text, r"每\s*(\d+(?:\.\d+)?)\s*秒") or 
           _extract_number(text, r"間隔\s*(\d+(?:\.\d+)?)\s*秒") or 
           _extract_number(text, r"(\d+(?:\.\d+)?)\s*秒"))
    if val is not None:
        return float(val)
    # 口語：半秒 / 一秒半 / 每半秒 / 每一秒半
    if re.search(r"每?\s*半\s*秒", text):
        return 0.5
    if re.search(r"每?\s*一\s*秒\s*半", text):
        return 1.5
    return None


def _extract_shot_name(text: str) -> Optional[str]:
    """從文字中提取球種名稱"""
    # 先嘗試標準全名（最精確）
    canonical = r"(正手高遠球|反手高遠球|正手切球|反手切球|正手殺球|反手殺球|正手平抽球|反手平抽球|正手小球|反手小球|正手挑球|反手挑球|平推球|正手接殺球|反手接殺球|近身接殺)"
    m = re.search(canonical, text)
    if m:
        return m.group(1)
    # 再嘗試同義詞/口語變體
    for pat, name in _SHOT_SYNONYMS:
        if re.search(pat, text):
            return name
    return None


def _match_advanced_title(text: str, advanced_specs: Dict[str, Any]) -> Optional[str]:
    """匹配進階訓練標題"""
    try:
        titles = list(advanced_specs.keys())
    except Exception:
        titles = []
    for t in titles:
        if t and t in text:
            return t
    return titles[0] if titles else None


def parse_command(command_text: str, advanced_specs: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    解析自然語言命令
    
    Args:
        command_text: 使用者輸入的文字命令
        advanced_specs: 進階訓練規格字典
        
    Returns:
        解析後的命令字典，如果無法解析則返回 None
    """
    # 一般化前處理
    text = (command_text or "").strip()
    if not text:
        return None

    # 1) 全局控制：停止 / 掃描 / 連接 / 斷開
    if re.search(r"^(停止|停止訓練|停一下|先停|暫停|停)$", text):
        return {"type": "stop"}
    if re.search(r"(掃描發球機|掃描|搜尋發球機|搜索發球機|搜索|搜尋)", text):
        return {"type": "scan"}
    if re.search(r"(連接|連線|配對)", text):
        return {"type": "connect"}
    if re.search(r"(斷開|解除連接|取消配對|斷線)", text):
        return {"type": "disconnect"}

    # 2) 熱身：基礎/進階/全面 + 速度（口語：簡單/全面/全方位）
    if "熱身" in text:
        warmup_type = "basic"
        if re.search(r"(進階)", text):
            warmup_type = "advanced"
        elif re.search(r"(全面|全方位|完整)", text):
            warmup_type = "comprehensive"
        speed = _extract_speed(text)
        return {"type": "start_warmup", "warmup_type": warmup_type, "speed": speed}

    # 3) 進階訓練：標題 + 速度 + 球數（口語：進階課程/進階項目/進階模式）
    if re.search(r"(進階訓練|進階課程|進階項目|進階模式)", text):
        title = _match_advanced_title(text, advanced_specs or {})
        speed = _extract_speed(text)
        balls = _extract_balls(text)
        return {"type": "start_advanced", "title": title, "speed": speed, "balls": balls}

    # 4) 等級套餐（保留老路徑）：等級X
    m_level = re.search(r"等級\s*(\d+)", text)
    if m_level:
        return {"type": "level_program", "level": int(m_level.group(1))}

    # 5) 單一球路（名稱 + 球數 + 間隔或速度）
    shot_name = _extract_shot_name(text)
    if shot_name:
        balls = _extract_balls(text)
        interval = _extract_interval_seconds(text)
        if interval is None:
            speed = _extract_speed(text)
            # 以速度映射秒數（與系統一致）
            if speed == "慢":
                interval = 4
            elif speed == "正常":
                interval = 3.5
            elif speed == "快":
                interval = 2.5
            elif speed == "極限快":
                interval = 1.4
        # 預設值
        if balls is None:
            balls = 10
        if interval is None:
            interval = 3.5
        return {"type": "specific_shot", "shot_name": shot_name, "count": int(balls), "interval": float(interval)}

    # 6) 開始目前所選訓練（可夾帶 速度/球數）
    if re.search(r"開始訓練", text):
        speed = _extract_speed(text)
        balls = _extract_balls(text)
        return {"type": "start_current", "speed": speed, "balls": balls}

    return None

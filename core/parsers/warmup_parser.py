"""
熱身解析器

這個模組負責解析熱身相關的配置和格式化功能。
"""

from typing import Dict, List


# 熱身資訊配置
WARMUP_INFO = {
    "basic": {
        "title": "簡單熱身",
        "contents": [
            "高遠球 30 顆",
            "小球 30 顆",
        ],
        "purpose": "上手球熱身，供初學者培養擊球空間感使用",
        "time": "3 分鐘",
    },
    "advanced": {
        "title": "進階熱身",
        "contents": [
            "平球 20 顆",
            "高遠球 20 顆",
            "切球 20 顆",
            "殺球 20 顆",
            "小球 20 顆",
        ],
        "purpose": "綜合熱身，活動各方向肌肉與關節",
        "time": "5 分鐘",
    },
    "comprehensive": {
        "title": "全面熱身",
        "contents": [
            "平球 20 顆",
            "高遠球 20 顆",
            "切球 20 顆",
            "殺球 20 顆",
            "小球 20 顆",
            "前後跑動 20 顆",
        ],
        "purpose": "全方位熱身，活動全身肌肉與關節",
        "time": "8 分鐘",
    },
}


def get_warmup_sequence(warmup_type: str) -> List[str]:
    """
    取得指定熱身類型的發球序列
    
    Args:
        warmup_type: 熱身類型（"basic", "advanced", "comprehensive"）
        
    Returns:
        發球序列
    """
    if warmup_type == "basic":
        return ["sec23_2"] * 5 + ["sec3_1"] * 5
    elif warmup_type == "advanced":
        return ["sec13_1"] * 5 + ["sec23_2"] * 5 + ["sec3_1"] * 5
    elif warmup_type == "comprehensive":
        alternating = []
        for _ in range(5):
            alternating.extend(["sec23_2", "sec3_1"])  # 交錯各發5顆（共10顆）
        return ["sec13_1"] * 5 + ["sec23_2"] * 5 + ["sec3_1"] * 5 + alternating
    else:
        return []


def get_warmup_title(warmup_type: str) -> str:
    """
    取得熱身標題
    
    Args:
        warmup_type: 熱身類型
        
    Returns:
        熱身標題
    """
    return WARMUP_INFO.get(warmup_type, {}).get("title", "未知熱身")


def format_warmup_info_text(warmup_type: str) -> str:
    """
    格式化熱身資訊文字
    
    Args:
        warmup_type: 熱身類型
        
    Returns:
        格式化的資訊文字
    """
    info = WARMUP_INFO.get(warmup_type)
    if not info:
        return ""
    
    lines = [f"{info['title']}"]
    lines.append("訓練內容")
    for item in info["contents"]:
        lines.append(item)
    lines.append("訓練目的")
    lines.append(info["purpose"])
    lines.append(f"預估時間  :   {info['time']}")
    return "\n".join(lines)

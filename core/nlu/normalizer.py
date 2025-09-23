"""
文本正規化：大小寫、去尾綴、同義詞、（可選）繁簡、全半形。
支援從配置檔案載入，若缺檔則使用內建最小集合。
"""

import os
import yaml
from typing import Dict, List, Optional


# 內建最小集合（fallback）
_BUILTIN_SYNONYMS: Dict[str, List[str]] = {
    "正手": ["正拍"],
    "反手": ["反拍"],
    "高遠球": ["高遠", "高远"],
    "平抽球": ["平抽"],
    "切球": ["切"],
    "推挑球": ["推挑"],
    "接殺球": ["接殺"],
}

_BUILTIN_SUFFIXES = ["球", "訓練", "套餐"]


def _load_config_file(config_path: str) -> Optional[dict]:
    """載入配置檔案"""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ 載入配置檔案失敗 {config_path}: {e}")
    return None


def _load_synonyms() -> Dict[str, List[str]]:
    """載入同義詞配置"""
    config_path = os.path.join(os.getcwd(), "config", "aliases.yaml")
    config = _load_config_file(config_path)
    
    if config and "synonyms" in config:
        return config["synonyms"]
    
    return _BUILTIN_SYNONYMS


def _load_suffixes() -> List[str]:
    """載入尾綴配置"""
    config_path = os.path.join(os.getcwd(), "config", "suffixes.yaml")
    config = _load_config_file(config_path)
    
    if config and "suffixes" in config:
        return config["suffixes"]
    
    return _BUILTIN_SUFFIXES


# 動態載入配置
SYNONYMS = _load_synonyms()
SUFFIXES = _load_suffixes()


def strip_suffix(s: str) -> str:
    t = (s or "").strip().lower().replace(" ", "")
    for suf in SUFFIXES:
        if t.endswith(suf):
            t = t[: -len(suf)]
    return t


def apply_synonyms(s: str) -> str:
    t = s
    # 雙向映射：同義詞 → 標準詞
    for k, vs in SYNONYMS.items():
        for v in vs:
            t = t.replace(v, k)
    return t


def normalize_query(text: str) -> str:
    # to_halfwidth + lower + 去標點（最小化：去空白與常見符號）
    t = (text or "").strip().lower()
    for ch in [" ", "\t", "\n", ",", ".", "；", ";", "，", "。", "！", "!", "?", "？", "-", "_", "(", ")"]:
        t = t.replace(ch, "")
    # 簡繁對映（最小：高远→高遠）
    t = t.replace("高远", "高遠")
    # 去尾綴 + 同義詞
    t = strip_suffix(t)
    t = apply_synonyms(t)
    return t



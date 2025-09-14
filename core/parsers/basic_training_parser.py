"""
基礎訓練解析器

這個模組負責解析基礎訓練配置和提供訓練相關的工具函數。
"""

from typing import Dict, List, Tuple, Optional
import os


# 基礎訓練項目配置
BASIC_TRAININGS = [
    ("正手高遠球", "sec25_1"),
    ("反手高遠球", "sec21_1"),
    ("正手切球", "sec25_1"),
    ("反手切球", "sec21_1"),
    ("正手殺球", "sec25_1"),
    ("反手殺球", "sec21_1"),
    ("正手平抽球", "sec15_1"),
    ("反手平抽球", "sec11_1"),
    ("正手小球", "sec5_1"),
    ("反手小球", "sec1_1"),
    ("正手挑球", "sec5_1"),
    ("反手挑球", "sec1_1"),
    ("平推球", "sec13_1"),
    ("正手接殺球", "sec20_1"),
    ("反手接殺球", "sec16_1"),
    ("近身接殺", "sec18_1")
]

# 球種名稱到區域代碼的映射
SHOT_TO_SECTION_MAP = {
    "正手平抽球": "sec15_1",
    "反手平抽球": "sec11_1",
    "正手高遠球": "sec25_1",
    "反手高遠球": "sec21_1",
    "正手切球": "sec25_1",
    "反手切球": "sec21_1",
    "正手殺球": "sec25_1",
    "反手殺球": "sec21_1",
    "正手小球": "sec5_1",
    "反手小球": "sec1_1",
    "正手挑球": "sec5_1",
    "反手挑球": "sec1_1",
    "平推球": "sec13_1",
    "正手接殺球": "sec20_1",
    "反手接殺球": "sec16_1",
    "近身接殺": "sec18_1"
}

# 區域代碼到球種名稱的映射
SECTION_TO_NAME_MAP = {section: name for name, section in BASIC_TRAININGS}


def map_speed_to_interval(speed_text: str) -> float:
    """
    將速度文字轉換為時間間隔（秒）
    
    Args:
        speed_text: 速度文字（"慢", "正常", "快", "極限快"）
        
    Returns:
        對應的時間間隔（秒）
    """
    speed_mapping = {
        "慢": 4.0,
        "正常": 3.5,
        "快": 2.5,
        "極限快": 1.4
    }
    return speed_mapping.get(speed_text, 3.5)


def map_count_to_number(count_text: str) -> int:
    """
    將球數文字轉換為數字
    
    Args:
        count_text: 球數文字（"10顆", "20顆", "30顆"）
        
    Returns:
        球數
    """
    count_mapping = {
        "10顆": 10,
        "20顆": 20,
        "30顆": 30
    }
    return count_mapping.get(count_text, 10)


def get_section_by_shot_name(shot_name: str) -> Optional[str]:
    """
    根據球種名稱取得對應的區域代碼
    
    Args:
        shot_name: 球種名稱
        
    Returns:
        對應的區域代碼，如果找不到則返回 None
    """
    return SHOT_TO_SECTION_MAP.get(shot_name)


def get_shot_name_by_section(section: str) -> Optional[str]:
    """
    根據區域代碼取得對應的球種名稱
    
    Args:
        section: 區域代碼
        
    Returns:
        對應的球種名稱，如果找不到則返回 None
    """
    return SECTION_TO_NAME_MAP.get(section)


def get_basic_training_items() -> List[Tuple[str, str]]:
    """
    取得所有基礎訓練項目
    
    Returns:
        基礎訓練項目列表，每個項目包含 (名稱, 區域代碼)
    """
    return BASIC_TRAININGS.copy()


def parse_descriptions(file_path: str) -> Dict[str, str]:
    """
    解析描述檔案
    
    Args:
        file_path: 描述檔案路徑
        
    Returns:
        描述映射字典
    """
    mapping = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]
    except Exception:
        return mapping
    
    current_title = None
    current_block_lines = []
    
    def flush_block():
        if current_title is not None:
            # 去除尾端空行
            while current_block_lines and current_block_lines[-1].strip() == "":
                current_block_lines.pop()
            mapping[current_title] = "\n".join(current_block_lines).strip()
    
    for line in lines:
        if line.strip() == "":
            flush_block()
            current_title = None
            current_block_lines = []
            continue
        if current_title is None:
            current_title = line.strip()
            current_block_lines = []
        else:
            current_block_lines.append(line)
    
    flush_block()
    return mapping


def load_descriptions(file_path: str = "discription.txt") -> Dict[str, str]:
    """
    載入描述檔案
    
    Args:
        file_path: 描述檔案路徑
        
    Returns:
        描述映射字典
    """
    if not os.path.exists(file_path):
        return {}
    
    return parse_descriptions(file_path)

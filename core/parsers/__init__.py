"""
解析器模組

這個模組包含所有資料解析和轉換功能：
- text_command_parser: 自然語言命令解析
- advanced_training_parser: 進階訓練檔案解析
- basic_training_parser: 基礎訓練配置解析
"""

try:
    from .text_command_parser import parse_command  # DEPRECATED
except Exception:
    parse_command = None
from .unified_parser import UnifiedParser
from .advanced_training_parser import (
    load_advanced_training_specs, 
    get_advanced_training_titles, 
    get_advanced_training_description,
    map_speed_to_interval as adv_map_speed_to_interval,
    parse_ball_count
)
from .basic_training_parser import (
    get_basic_training_items,
    get_section_by_shot_name,
    get_shot_name_by_section,
    load_descriptions,
    map_speed_to_interval as basic_map_speed_to_interval,
    map_count_to_number
)
from .warmup_parser import (
    get_warmup_sequence,
    get_warmup_title,
    format_warmup_info_text
)

__all__ = [
    'parse_command',
    'UnifiedParser',
    'load_advanced_training_specs',
    'get_advanced_training_titles', 
    'get_advanced_training_description',
    'adv_map_speed_to_interval',
    'parse_ball_count',
    'get_basic_training_items',
    'get_section_by_shot_name',
    'get_shot_name_by_section',
    'load_descriptions',
    'basic_map_speed_to_interval',
    'map_count_to_number',
    'get_warmup_sequence',
    'get_warmup_title',
    'format_warmup_info_text'
]

"""
執行器模組

這個模組包含所有業務邏輯執行功能：
- text_command_executor: 文字命令執行
- advanced_training_executor: 進階訓練執行
- basic_training_executor: 基礎訓練執行
- course_executor: 課程執行
- warmup_executor: 熱身執行
"""

try:
    from .text_command_executor import create_text_command_executor, TextCommandExecutor
except Exception:
    # Deprecated：若不存在則忽略
    create_text_command_executor = None
    TextCommandExecutor = None
from .advanced_training_executor import create_advanced_training_executor, AdvancedTrainingExecutor
from .basic_training_executor import create_basic_training_executor, BasicTrainingExecutor
try:
    from .course_executor import create_course_executor, CourseExecutor
except Exception:
    create_course_executor = None
    CourseExecutor = None
from .warmup_executor import create_warmup_executor, WarmupExecutor

__all__ = [
    'create_text_command_executor',
    'TextCommandExecutor',
    'create_advanced_training_executor',
    'AdvancedTrainingExecutor',
    'create_basic_training_executor',
    'BasicTrainingExecutor',
    'create_course_executor',
    'CourseExecutor',
    'create_warmup_executor',
    'WarmupExecutor'
]

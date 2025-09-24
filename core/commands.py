"""
統一 Command/Intent/Slots 定義（對外單一入口）。

為避免重複定義，直接轉出既有 DTO。
"""

from .commands.dto import CommandDTO as Command, IntentType, make_command

__all__ = [
    "Command",
    "IntentType",
    "make_command",
]



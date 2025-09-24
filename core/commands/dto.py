"""
統一的 Command DTO 定義

此模組定義通用的指令資料結構，供 Parser → Router → Service 使用。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Literal


IntentType = Literal[
    "WAKE",
    "SCAN",
    "CONNECT",
    "DISCONNECT",
    "RUN_PROGRAM_BY_NAME",
    "RUN_SINGLE_SHOT",
]


@dataclass
class CommandDTO:
    intent: IntentType
    slots: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


def make_command(intent: IntentType, source: str, raw: str, slots: Dict[str, Any] | None = None) -> CommandDTO:
    return CommandDTO(
        intent=intent,
        slots=slots or {},
        meta={
            "source": source,
            "raw": raw,
        },
    )



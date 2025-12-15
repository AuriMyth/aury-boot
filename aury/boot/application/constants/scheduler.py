"""调度器运行模式常量。

定义调度器运行模式的枚举。
"""

from __future__ import annotations

from enum import Enum


class SchedulerMode(str, Enum):
    """调度器运行模式枚举（应用层配置）。

    - EMBEDDED: 伴随 API 运行（默认）
    - STANDALONE: 独立运行
    - DISABLED: 禁用调度器
    """

    EMBEDDED = "embedded"
    STANDALONE = "standalone"
    DISABLED = "disabled"


__all__ = [
    "SchedulerMode",
]



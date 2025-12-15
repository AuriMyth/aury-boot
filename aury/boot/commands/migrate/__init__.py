"""迁移命令行工具。

提供数据库迁移管理的命令行接口。
"""

from .app import app, get_manager
from .commands import (
    check,
    down,
    history,
    make,
    merge,
    show,
    status,
    up,
)


def main() -> None:
    """命令行入口函数。"""
    app()


__all__ = [
    "app",
    "check",
    "down",
    "get_manager",
    "history",
    "main",
    "make",
    "merge",
    "show",
    "status",
    "up",
]


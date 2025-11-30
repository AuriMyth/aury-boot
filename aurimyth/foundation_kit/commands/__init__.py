"""命令行工具模块。

提供各种命令行接口。
"""

from .migrate import app, main

__all__ = [
    "app",
    "main",
]

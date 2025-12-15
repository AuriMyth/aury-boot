"""服务器管理命令。

提供 CLI 接口来管理和运行应用服务器。

使用示例:
    python -m aury.boot.commands.server run \\
        --host 0.0.0.0 \\
        --port 8000 \\
        --workers 4 \\
        --reload
"""

from .app import app, server_cli

__all__ = [
    "app",
    "server_cli",
]




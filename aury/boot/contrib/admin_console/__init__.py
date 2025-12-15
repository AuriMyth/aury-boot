"""SQLAdmin 管理后台（Admin Console）集成。

设计目标：
- 默认路径 `/api/admin-console`，避免与业务 URL 冲突
- 默认只内置 basic / bearer 两种可用认证模式
- 允许通过 settings 或项目模块显式覆盖认证/视图注册
- 不依赖 CLI command，适合生产快速集成
"""

from __future__ import annotations

from .install import install_admin_console

__all__ = [
    "install_admin_console",
]



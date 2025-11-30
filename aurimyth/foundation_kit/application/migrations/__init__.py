"""数据库迁移管理模块。

提供类似 Django 的迁移管理接口。
"""

from .manager import MigrationManager

__all__ = [
    "MigrationManager",
]



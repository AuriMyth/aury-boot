"""数据库管理模块。

提供统一的数据库连接管理、会话创建和健康检查功能。
"""

from .exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseQueryError,
    DatabaseTransactionError,
)
from .manager import DatabaseManager

__all__ = [
    "DatabaseManager",
    # 异常
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "DatabaseTransactionError",
]


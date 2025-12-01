"""数据库管理模块。

提供统一的数据库连接管理、会话创建、健康检查、UPSERT策略和查询优化。
"""

from .exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseQueryError,
    DatabaseTransactionError,
)
from .manager import DatabaseManager
from .query_tools import cache_query, monitor_query
from .strategies import (
    MySQLUpsertStrategy,
    PostgreSQLUpsertStrategy,
    SQLiteUpsertStrategy,
    UpsertStrategy,
    UpsertStrategyFactory,
)

__all__ = [
    # 异常
    "DatabaseConnectionError",
    "DatabaseError",
    "DatabaseManager",
    "DatabaseQueryError",
    "DatabaseTransactionError",
    # UPSERT 策略
    "MySQLUpsertStrategy",
    "PostgreSQLUpsertStrategy",
    "SQLiteUpsertStrategy",
    "UpsertStrategy",
    "UpsertStrategyFactory",
    # 查询优化
    "cache_query",
    "monitor_query",
]


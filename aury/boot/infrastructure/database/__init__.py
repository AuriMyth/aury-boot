"""数据库管理模块。

提供统一的数据库连接管理、会话创建、健康检查、UPSERT策略和查询优化。
"""

from .connection_tracker import (
    ConnectionTrace,
    ConnectionTracker,
    DbHealthChecker,
    MySQLHealthChecker,
    PostgreSQLHealthChecker,
    SQLiteHealthChecker,
    get_health_checker,
    setup_connection_tracking,
)
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
    # 连接追踪（对标 HikariCP leakDetectionThreshold）
    "ConnectionTrace",
    "ConnectionTracker",
    "DbHealthChecker",
    "MySQLHealthChecker",
    "PostgreSQLHealthChecker",
    "SQLiteHealthChecker",
    "get_health_checker",
    "setup_connection_tracking",
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


"""Infrastructure 层仓储适配模块。

提供数据库驱动特定的适配代码（UPSERT 策略、装饰器等）。

**架构说明**：
BaseRepository 和 QueryBuilder 现在在 domain 层。
Infrastructure 层仅提供数据库方言相关的实现。
"""

from .decorators import cache_query, monitor_query, requires_transaction
from .upsert_strategies import (
    MySQLUpsertStrategy,
    PostgreSQLUpsertStrategy,
    SQLiteUpsertStrategy,
    UpsertStrategy,
    UpsertStrategyFactory,
)

__all__ = [
    "MySQLUpsertStrategy",
    "PostgreSQLUpsertStrategy",
    "SQLiteUpsertStrategy",
    "UpsertStrategy",
    "UpsertStrategyFactory",
    "cache_query",
    "monitor_query",
    "requires_transaction",
]



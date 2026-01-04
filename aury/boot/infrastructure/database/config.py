"""数据库配置。

Infrastructure 层配置数据类，由 application 层传入。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# 支持的事务隔离级别
ISOLATION_LEVELS = (
    "READ UNCOMMITTED",
    "READ COMMITTED",
    "REPEATABLE READ",
    "SERIALIZABLE",
    "AUTOCOMMIT",
)


class DatabaseConfig(BaseModel):
    """数据库基础设施配置。
    
    纯数据类，由 application 层构造并传入 infrastructure 层。
    不直接读取环境变量。
    """
    
    url: str = Field(
        description="数据库连接URL（支持所有 SQLAlchemy 支持的数据库）"
    )
    echo: bool = Field(
        default=False,
        description="是否打印SQL语句"
    )
    pool_size: int = Field(
        default=5,
        description="连接池大小"
    )
    max_overflow: int = Field(
        default=10,
        description="最大溢出连接数"
    )
    pool_timeout: int = Field(
        default=30,
        description="连接超时时间（秒）"
    )
    pool_recycle: int = Field(
        default=1800,
        description="连接回收时间（秒）"
    )
    isolation_level: str | None = Field(
        default=None,
        description="事务隔离级别: READ UNCOMMITTED / READ COMMITTED / REPEATABLE READ / SERIALIZABLE / AUTOCOMMIT"
    )


__all__ = [
    "ISOLATION_LEVELS",
    "DatabaseConfig",
]




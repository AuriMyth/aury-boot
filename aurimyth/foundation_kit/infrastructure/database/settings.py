"""数据库配置。

Infrastructure 层配置，不依赖 application 层。
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置。
    
    环境变量前缀: DATABASE_
    示例: DATABASE_URL, DATABASE_ECHO, DATABASE_POOL_SIZE
    """
    
    url: str = Field(
        description="数据库连接URL（支持所有 SQLAlchemy 支持的数据库），必需配置"
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
    
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        case_sensitive=False,
    )


__all__ = [
    "DatabaseSettings",
]


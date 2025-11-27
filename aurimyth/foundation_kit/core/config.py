"""共享配置基类。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置。
    
    环境变量前缀: DATABASE_
    示例: DATABASE_URL, DATABASE_ECHO, DATABASE_POOL_SIZE
    """
    
    url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/aurimyth",
        description="数据库连接URL"
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


class CacheSettings(BaseSettings):
    """缓存配置。
    
    环境变量前缀: CACHE_
    示例: CACHE_TYPE, CACHE_REDIS_URL, CACHE_MAX_SIZE
    """
    
    cache_type: str = Field(
        default="memory",
        description="缓存类型"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis缓存URL"
    )
    max_size: int = Field(
        default=1000,
        description="内存缓存最大大小"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        case_sensitive=False,
    )


class ServerSettings(BaseSettings):
    """服务器配置。
    
    环境变量前缀: SERVER_
    示例: SERVER_HOST, SERVER_PORT, SERVER_RELOAD
    """
    
    host: str = Field(
        default="127.0.0.1",
        description="服务器监听地址"
    )
    port: int = Field(
        default=8000,
        description="服务器监听端口"
    )
    reload: bool = Field(
        default=True,
        description="是否启用热重载"
    )
    workers: int = Field(
        default=1,
        description="工作进程数"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="SERVER_",
        case_sensitive=False,
    )


class CORSSettings(BaseSettings):
    """CORS配置。
    
    环境变量前缀: CORS_
    示例: CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS
    """
    
    origins: list[str] = Field(
        default=["*"],
        description="允许的CORS源"
    )
    allow_credentials: bool = Field(
        default=True,
        description="是否允许CORS凭据"
    )
    allow_methods: list[str] = Field(
        default=["*"],
        description="允许的CORS方法"
    )
    allow_headers: list[str] = Field(
        default=["*"],
        description="允许的CORS头"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        case_sensitive=False,
    )


class LogSettings(BaseSettings):
    """日志配置。
    
    环境变量前缀: LOG_
    示例: LOG_LEVEL
    """
    
    level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
    )


class BaseConfig(BaseSettings):
    """基础配置类。
    
    所有应用配置的基类，提供通用配置项。
    使用 pydantic-settings 自动从环境变量和 .env 文件加载配置。
    """
    
    # 数据库配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    
    # 缓存配置
    cache: CacheSettings = Field(default_factory=CacheSettings)
    
    # 服务器配置
    server: ServerSettings = Field(default_factory=ServerSettings)
    
    # CORS配置
    cors: CORSSettings = Field(default_factory=CORSSettings)
    
    # 日志配置
    log: LogSettings = Field(default_factory=LogSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境。"""
        return self.log.level.upper() == "ERROR"


__all__ = [
    "BaseConfig",
    "DatabaseSettings",
    "CacheSettings",
    "ServerSettings",
    "CORSSettings",
    "LogSettings",
]




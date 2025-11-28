"""共享配置基类。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。

注意：Application 层的配置作为适配层，映射 Infrastructure 层的配置。
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 导入 Infrastructure 层的配置（作为基础配置）
from aurimyth.foundation_kit.infrastructure.database.settings import (
    DatabaseSettings as InfrastructureDatabaseSettings,
)
from aurimyth.foundation_kit.infrastructure.tasks.settings import (
    TaskSettings as InfrastructureTaskSettings,
)


# Application 层的配置类，映射 Infrastructure 层的配置
class DatabaseSettings(InfrastructureDatabaseSettings):
    """数据库配置（Application 层适配）。
    
    继承自 infrastructure.database.settings.DatabaseSettings，
    在 Application 层提供统一的配置接口。
    
    环境变量前缀: DATABASE_
    示例: DATABASE_URL, DATABASE_ECHO, DATABASE_POOL_SIZE
    """
    pass


class CacheSettings(BaseSettings):
    """缓存配置。
    
    环境变量前缀: CACHE_
    示例: CACHE_TYPE, CACHE_REDIS_URL, CACHE_MAX_SIZE
    """
    
    cache_type: str = Field(
        default="memory",
        description="缓存类型"
    )
    redis_url: str | None = Field(
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


class ServiceSettings(BaseSettings):
    """服务配置。
    
    环境变量前缀: SERVICE_
    示例: SERVICE_TYPE
    
    服务类型说明：
    - api: 运行 API 服务（可伴随调度器，根据 SCHEDULER_MODE 决定调度器运行方式）
    - worker: 运行任务队列 Worker（处理异步任务）
    - scheduler: 仅运行调度器进程（独立 pod，只运行定时任务，不运行 API）
    """
    
    service_type: str = Field(
        default="api",
        description="服务类型（api/worker/scheduler）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="SERVICE_",
        case_sensitive=False,
    )


class SchedulerSettings(BaseSettings):
    """调度器配置。
    
    环境变量前缀: SCHEDULER_
    示例: SCHEDULER_MODE
    
    调度器模式说明（仅在 SERVICE_TYPE=api 时有效）：
    - embedded: 在 API 进程中运行调度器（默认）
    - standalone: 调度器在独立进程中运行
    - disabled: 禁用调度器
    
    当 SERVICE_TYPE=scheduler 时，会启动一个独立的调度器进程，此配置无效。
    """
    
    mode: str = Field(
        default="embedded",
        description="调度器运行模式（embedded/standalone/disabled），仅在 SERVICE_TYPE=api 时有效"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="SCHEDULER_",
        case_sensitive=False,
    )


# Application 层的配置类，映射 Infrastructure 层的配置
class TaskSettings(InfrastructureTaskSettings):
    """任务队列配置（Application 层适配）。
    
    继承自 infrastructure.tasks.settings.TaskSettings，
    在 Application 层提供统一的配置接口。
    
    环境变量前缀: TASK_
    示例: TASK_BROKER_URL, TASK_MAX_RETRIES
    """
    pass


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
    
    # 服务配置
    service: ServiceSettings = Field(default_factory=ServiceSettings)
    
    # 调度器配置
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    
    # 任务队列配置
    task: TaskSettings = Field(default_factory=TaskSettings)
    
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
    "ServiceSettings",
    "SchedulerSettings",
    "TaskSettings",
]


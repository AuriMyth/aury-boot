"""配置模块。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。

注意：Application 层的配置作为适配层，映射 Infrastructure 层的配置。
"""

from .settings import (
    BaseConfig,
    CacheSettings,
    CORSSettings,
    DatabaseSettings,
    EventSettings,
    HealthCheckSettings,
    LogSettings,
    RPCClientSettings,
    RPCServiceSettings,
    SchedulerSettings,
    ServerSettings,
    ServiceSettings,
    TaskSettings,
)

__all__ = [
    "BaseConfig",
    "CORSSettings",
    "CacheSettings",
    "DatabaseSettings",  # 映射自 infrastructure.database.settings.DatabaseSettings
    "EventSettings",
    "HealthCheckSettings",
    "LogSettings",
    "RPCClientSettings",
    "RPCServiceSettings",
    "SchedulerSettings",
    "ServerSettings",
    "ServiceSettings",
    "TaskSettings",  # 映射自 infrastructure.tasks.settings.TaskSettings
]


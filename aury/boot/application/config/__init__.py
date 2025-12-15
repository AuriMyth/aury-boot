"""配置模块。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。

设计原则：
- Application 层配置完全独立，不依赖 Infrastructure 层
- 配置是纯粹的数据模型定义
"""

from .settings import (
    BaseConfig,
    CacheSettings,
    CORSSettings,
    DatabaseSettings,
    EventSettings,
    HealthCheckSettings,
    LogSettings,
    MigrationSettings,
    RPCClientSettings,
    RPCServiceSettings,
    SchedulerSettings,
    ServerSettings,
    ServiceSettings,
    TaskSettings,
)

__all__ = [
    "BaseConfig",
    "CacheSettings",
    "CORSSettings",
    "DatabaseSettings",
    "EventSettings",
    "HealthCheckSettings",
    "LogSettings",
    "MigrationSettings",
    "RPCClientSettings",
    "RPCServiceSettings",
    "SchedulerSettings",
    "ServerSettings",
    "ServiceSettings",
    "TaskSettings",
]


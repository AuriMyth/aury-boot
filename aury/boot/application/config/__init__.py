"""配置模块。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。

设计原则：
- Application 层配置完全独立，不依赖 Infrastructure 层
- 配置是纯粹的数据模型定义

多实例配置:
框架支持多种组件的多实例配置，使用统一的环境变量格式:
    {PREFIX}_{INSTANCE}_{FIELD}=value

示例:
    DATABASE_DEFAULT_URL=postgresql://main...
    DATABASE_ANALYTICS_URL=postgresql://analytics...
    CACHE_DEFAULT_URL=redis://localhost:6379/1
    MQ_DEFAULT_URL=redis://localhost:6379/2
"""

from .multi_instance import (
    MultiInstanceConfigLoader,
    MultiInstanceSettings,
    parse_multi_instance_env,
)
from .settings import (
    BaseConfig,
    CacheInstanceConfig,
    CacheSettings,
    ChannelInstanceConfig,
    CORSSettings,
    DatabaseInstanceConfig,
    DatabaseSettings,
    EventInstanceConfig,
    EventSettings,
    HealthCheckSettings,
    LogSettings,
    MessageQueueSettings,
    MigrationSettings,
    MQInstanceConfig,
    RPCClientSettings,
    RPCServiceSettings,
    SchedulerSettings,
    ServerSettings,
    ServiceSettings,
    StorageInstanceConfig,
    TaskSettings,
)

__all__ = [
    # 配置类
    "BaseConfig",
    "CORSSettings",
    # 多实例配置类
    "CacheInstanceConfig",
    "CacheSettings",
    "ChannelInstanceConfig",
    "DatabaseInstanceConfig",
    "DatabaseSettings",
    "EventInstanceConfig",
    "EventSettings",
    "HealthCheckSettings",
    "LogSettings",
    "MQInstanceConfig",
    "MessageQueueSettings",
    "MigrationSettings",
    # 多实例配置工具
    "MultiInstanceConfigLoader",
    "MultiInstanceSettings",
    "RPCClientSettings",
    "RPCServiceSettings",
    "SchedulerSettings",
    "ServerSettings",
    "ServiceSettings",
    "StorageInstanceConfig",
    "TaskSettings",
    "parse_multi_instance_env",
]


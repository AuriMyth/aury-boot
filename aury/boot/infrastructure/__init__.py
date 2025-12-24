"""基础设施层模块。

提供外部依赖的实现，包括：
- 数据库管理
- 缓存管理
- 存储管理
- 调度器
- 任务队列
- 消息队列
- 通道 (SSE/PubSub)
- 事件总线
- Redis 客户端
- RabbitMQ 客户端
"""

# 数据库
# 缓存
from .cache import (
    CacheBackend,
    CacheFactory,
    CacheManager,
    ICache,
    MemcachedCache,
    MemoryCache,
    RedisCache,
)

# 通道 (SSE/PubSub)
from .channel import (
    ChannelBackend,
    ChannelManager,
    ChannelMessage,
    IChannel,
    MemoryChannel,
    RedisChannel,
)

# RabbitMQ 客户端
from .clients.rabbitmq import RabbitMQClient, RabbitMQConfig

# Redis 客户端
from .clients.redis import RedisClient, RedisConfig
from .database import DatabaseManager

# 依赖注入
from .di import Container, Lifetime, Scope, ServiceDescriptor

# 事件总线
from .events import (
    Event,
    EventBackend,
    EventBusManager,
    EventHandler,
    EventType,
    IEventBus,
    MemoryEventBus,
    RabbitMQEventBus,
    RedisEventBus,
)

# 消息队列
from .mq import (
    IMQ,
    MQBackend,
    MQManager,
    MQMessage,
    RabbitMQ,
    RedisMQ,
)

# 存储（基于 aury-sdk-storage）
from .storage import (
    IStorage,
    LocalStorage,
    S3Storage,
    StorageBackend,
    StorageConfig,
    StorageFactory,
    StorageFile,
    StorageManager,
    UploadResult,
)

# 调度器（可选依赖）
try:
    from .scheduler import SchedulerManager
except ImportError:
    SchedulerManager = None  # type: ignore[assignment, misc]

# 任务队列（可选依赖）
try:
    from .tasks import TaskManager, TaskProxy, conditional_task
except ImportError:
    TaskManager = None  # type: ignore[assignment, misc]
    TaskProxy = None  # type: ignore[assignment, misc]
    conditional_task = None  # type: ignore[assignment, misc]

__all__ = [
    # 消息队列
    "IMQ",
    # 缓存
    "CacheBackend",
    "CacheFactory",
    "CacheManager",
    # 通道
    "ChannelBackend",
    "ChannelManager",
    "ChannelMessage",
    # 依赖注入
    "Container",
    # 数据库
    "DatabaseManager",
    # 事件总线
    "Event",
    "EventBackend",
    "EventBusManager",
    "EventHandler",
    "EventType",
    "ICache",
    "IChannel",
    "IEventBus",
    # 存储
    "IStorage",
    "Lifetime",
    "LocalStorage",
    "MQBackend",
    "MQManager",
    "MQMessage",
    "MemcachedCache",
    "MemoryCache",
    "MemoryChannel",
    "MemoryEventBus",
    "RabbitMQ",
    # RabbitMQ 客户端
    "RabbitMQClient",
    "RabbitMQConfig",
    "RabbitMQEventBus",
    "RedisCache",
    "RedisChannel",
    # Redis 客户端
    "RedisClient",
    "RedisConfig",
    "RedisEventBus",
    "RedisMQ",
    "S3Storage",
    # 调度器
    "SchedulerManager",
    "Scope",
    "ServiceDescriptor",
    "StorageBackend",
    "StorageConfig",
    "StorageFactory",
    "StorageFile",
    "StorageManager",
    # 任务队列
    "TaskManager",
    "TaskProxy",
    "UploadResult",
    "conditional_task",
]


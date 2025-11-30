"""基础设施层模块。

提供外部依赖的实现，包括：
- 数据库管理
- 缓存管理
- 存储管理
- 调度器
- 任务队列
- 日志
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
from .database import DatabaseManager

# 日志（已迁移到 common 层）
# 从 common.logging 导入

# 调度器（可选依赖）
try:
    from .scheduler import SchedulerManager
except ImportError:
    SchedulerManager = None  # type: ignore[assignment, misc]

# 存储
from .storage import (
    IStorage,
    LocalStorage,
    StorageBackend,
    StorageConfig,
    StorageFactory,
    StorageFile,
    StorageManager,
)

# S3Storage（可选依赖，延迟导入）
try:
    from .storage import S3Storage
except ImportError:
    S3Storage = None  # type: ignore[assignment, misc]

# 任务队列（可选依赖）
try:
    from .tasks import TaskManager, TaskProxy, conditional_actor
except ImportError:
    TaskManager = None  # type: ignore[assignment, misc]
    TaskProxy = None  # type: ignore[assignment, misc]
    conditional_actor = None  # type: ignore[assignment, misc]

# 事件总线
# 依赖注入
from .di import Container, Lifetime, Scope, ServiceDescriptor
from .events import (
    EventBus,
    EventConsumer,
    EventLoggingMiddleware,
    EventMiddleware,
)

__all__ = [
    "CacheBackend",
    "CacheFactory",
    # 缓存
    "CacheManager",
    # 依赖注入
    "Container",
    # 数据库
    "DatabaseManager",
    # 事件总线
    "EventBus",
    "EventConsumer",
    "EventLoggingMiddleware",
    "EventMiddleware",
    "ICache",
    "IStorage",
    "Lifetime",
    "LocalStorage",
    "MemcachedCache",
    "MemoryCache",
    "RedisCache",
    "S3Storage",
    # 调度器
    "SchedulerManager",
    "Scope",
    "ServiceDescriptor",
    "StorageBackend",
    "StorageConfig",
    "StorageFactory",
    "StorageFile",
    # 存储
    "StorageManager",
    # 任务队列
    "TaskManager",
    "TaskProxy",
    "conditional_actor",
    # 日志（已迁移到 common 层，请从 common.logging 导入）
]


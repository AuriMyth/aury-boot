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
# 调度器
from .scheduler import SchedulerManager

# 存储
from .storage import (
    IStorage,
    LocalStorage,
    S3Storage,
    StorageBackend,
    StorageConfig,
    StorageFactory,
    StorageFile,
    StorageManager,
)

# 任务队列
from .tasks import TaskManager, TaskProxy, conditional_actor

__all__ = [
    # 数据库
    "DatabaseManager",
    # 缓存
    "CacheManager",
    "CacheFactory",
    "CacheBackend",
    "ICache",
    "RedisCache",
    "MemoryCache",
    "MemcachedCache",
    # 调度器
    "SchedulerManager",
    # 任务队列
    "TaskManager",
    "TaskProxy",
    "conditional_actor",
    # 存储
    "StorageManager",
    "StorageFactory",
    "StorageBackend",
    "IStorage",
    "StorageConfig",
    "StorageFile",
    "LocalStorage",
    "S3Storage",
    # 日志（已迁移到 common 层，请从 common.logging 导入）
]


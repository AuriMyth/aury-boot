"""核心基础设施模块。

提供数据库、缓存、调度器等核心功能。
"""

# 数据库
from .database import DatabaseManager

# 缓存
from .cache import (
    CacheBackend,
    CacheFactory,
    CacheManager,
    ICache,
    MemoryCache,
    MemcachedCache,
    RedisCache,
)

# 调度器
from .scheduler import SchedulerManager

# 任务队列
from .tasks import TaskManager

# 存储
from .storage.base import (
    IStorage,
    StorageBackend,
    StorageConfig,
    StorageFactory,
    StorageManager,
    StorageFile,
)

# 数据库迁移
from .migrations import run_migrations

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
    # 存储
    "StorageManager",
    "StorageFactory",
    "StorageBackend",
    "IStorage",
    "StorageConfig",
    "StorageFile",
    # 迁移
    "run_migrations",
]

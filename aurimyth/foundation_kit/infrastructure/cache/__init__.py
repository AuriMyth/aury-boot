"""缓存系统模块。

支持多种缓存后端：
- Redis
- Memory（内存）
- Memcached（可选）
- 可扩展其他类型

使用策略模式，可以轻松切换缓存后端。
"""

from .backends import MemcachedCache, MemoryCache, RedisCache
from .base import CacheBackend, ICache
from .exceptions import CacheBackendError, CacheError, CacheMissError
from .factory import CacheFactory
from .manager import CacheManager

__all__ = [
    "CacheBackend",
    "CacheBackendError",
    # 异常
    "CacheError",
    "CacheFactory",
    "CacheManager",
    "CacheMissError",
    "ICache",
    "MemcachedCache",
    "MemoryCache",
    "RedisCache",
]


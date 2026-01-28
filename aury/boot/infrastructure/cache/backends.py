"""缓存后端实现（兼容层）。

实际实现在 redis.py 和 memory.py 中。
"""

from .memory import MemcachedCache, MemoryCache
from .redis import RedisCache

__all__ = [
    "MemcachedCache",
    "MemoryCache",
    "RedisCache",
]


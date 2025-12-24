"""Redis 客户端模块。

提供统一的 Redis 连接管理，支持多实例。

使用示例:
    # 默认实例
    client = RedisClient.get_instance()
    client.configure(url="redis://localhost:6379/0")
    await client.initialize()
    
    # 命名实例
    cache_redis = RedisClient.get_instance("cache")
    queue_redis = RedisClient.get_instance("queue")
    
    # 使用
    redis = client.connection
    await redis.set("key", "value")
"""

from __future__ import annotations

from .config import RedisConfig
from .manager import RedisClient

__all__ = [
    "RedisClient",
    "RedisConfig",
]

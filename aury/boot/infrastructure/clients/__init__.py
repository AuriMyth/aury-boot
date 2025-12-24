"""客户端模块 - 外部服务连接管理。

提供统一的外部服务客户端，支持多实例。

包含:
- redis: Redis 客户端
- rabbitmq: RabbitMQ 客户端
"""

from __future__ import annotations

from .rabbitmq import RabbitMQClient, RabbitMQConfig
from .redis import RedisClient, RedisConfig

__all__ = [
    # RabbitMQ
    "RabbitMQClient",
    "RabbitMQConfig",
    # Redis
    "RedisClient",
    "RedisConfig",
]

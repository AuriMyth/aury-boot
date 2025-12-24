"""事件总线模块。

提供发布/订阅模式的事件总线功能，用于模块间解耦通信。

支持的后端:
- memory: 内存事件总线（单进程）
- redis: Redis Pub/Sub（多进程/多实例）
- rabbitmq: RabbitMQ Exchange（分布式）
"""

from .backends import MemoryEventBus, RabbitMQEventBus, RedisEventBus
from .base import Event, EventBackend, EventHandler, EventType, IEventBus
from .manager import EventBusManager

__all__ = [
    # 接口和类型
    "Event",
    "EventBackend",
    # 管理器
    "EventBusManager",
    "EventHandler",
    "EventType",
    "IEventBus",
    # 后端实现
    "MemoryEventBus",
    "RabbitMQEventBus",
    "RedisEventBus",
]



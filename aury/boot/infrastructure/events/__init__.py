"""事件总线模块。

提供发布/订阅模式的事件总线功能，用于模块间解耦通信。

支持的后端:
- broadcaster: 基于 broadcaster 库（推荐，支持 memory/redis/kafka/postgres）
- rabbitmq: RabbitMQ Exchange（复杂消息场景）
"""

from .backends import BroadcasterEventBus, RabbitMQEventBus
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
    "BroadcasterEventBus",
    "RabbitMQEventBus",
]



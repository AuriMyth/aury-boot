"""消息队列模块。

提供生产者/消费者模式的消息队列功能，用于异步任务处理、服务间通信等场景。

支持的后端:
- redis: Redis List 实现
- rabbitmq: RabbitMQ (aio-pika)
"""

from .backends import RabbitMQ, RedisMQ
from .base import IMQ, MQBackend, MQMessage
from .manager import MQManager

__all__ = [
    # 接口和类型
    "IMQ",
    "MQBackend",
    # 管理器
    "MQManager",
    "MQMessage",
    # 后端实现
    "RabbitMQ",
    "RedisMQ",
]

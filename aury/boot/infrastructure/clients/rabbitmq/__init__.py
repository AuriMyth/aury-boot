"""RabbitMQ 客户端模块。

提供 RabbitMQ 连接的多实例管理。
"""

from .config import RabbitMQConfig
from .manager import RabbitMQClient

__all__ = ["RabbitMQClient", "RabbitMQConfig"]

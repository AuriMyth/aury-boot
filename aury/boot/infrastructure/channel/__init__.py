"""流式通道模块。

提供发布/订阅模式的通道功能，用于 SSE、WebSocket 等实时通信场景。

支持的后端（通过 Broadcaster 库）:
- memory:// - 内存通道（单进程，开发/测试用）
- redis:// - Redis Pub/Sub（多进程/分布式）
- kafka:// - Apache Kafka
- postgres:// - PostgreSQL LISTEN/NOTIFY
"""

from .backends import BroadcasterChannel
from .base import ChannelBackend, ChannelMessage, IChannel
from .manager import ChannelManager

__all__ = [
    # 接口和类型
    "ChannelBackend",
    "ChannelMessage",
    "IChannel",
    # 管理器
    "ChannelManager",
    # 后端实现
    "BroadcasterChannel",
]

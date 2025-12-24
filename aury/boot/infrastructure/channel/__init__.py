"""流式通道模块。

提供发布/订阅模式的通道功能，用于 SSE、WebSocket 等实时通信场景。

支持的后端:
- memory: 内存通道（单进程）
- redis: Redis Pub/Sub（多进程/多实例）
"""

from .backends import MemoryChannel, RedisChannel
from .base import ChannelBackend, ChannelMessage, IChannel
from .manager import ChannelManager

__all__ = [
    # 接口和类型
    "ChannelBackend",
    # 管理器
    "ChannelManager",
    "ChannelMessage",
    "IChannel",
    # 后端实现
    "MemoryChannel",
    "RedisChannel",
]

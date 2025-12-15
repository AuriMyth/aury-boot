"""事件系统 - 基于 Kombu 消息队列的分布式事件总线。

提供事件基础定义、发布/订阅机制，实现模块间的解耦。
支持本地模式（内存）和分布式模式（Kombu 消息队列）。

**架构说明**：
Event 基类定义在 infrastructure 层，这是最底层的公共数据结构。
Domain 层依赖 infrastructure.events 获取 Event 基类。
这样完全断开了 infrastructure 对 domain 的循环依赖。

事件模型定义在单独的 models.py 文件中，避免循环导入问题。
"""

from __future__ import annotations

from .bus import EventBus
from .config import EventConfig
from .consumer import EventConsumer
from .middleware import EventLoggingMiddleware, EventMiddleware
from .models import Event, EventHandler, EventType

__all__ = [
    "Event",
    "EventBus",
    "EventConfig",
    "EventConsumer",
    "EventHandler",
    "EventLoggingMiddleware",
    "EventMiddleware",
    "EventType",
]



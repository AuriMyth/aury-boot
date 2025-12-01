"""事件系统 - 基于 Kombu 消息队列的分布式事件总线。

提供事件基础定义、发布/订阅机制，实现模块间的解耦。
支持本地模式（内存）和分布式模式（Kombu 消息队列）。

**架构说明**：
Event 基类定义在 infrastructure 层，这是最底层的公共数据结构。
Domain 层依赖 infrastructure.events 获取 Event 基类。
这样完全断开了 infrastructure 对 domain 的循环依赖。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any, ClassVar, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

from .bus import EventBus
from .config import EventConfig
from .consumer import EventConsumer
from .middleware import EventLoggingMiddleware, EventMiddleware

# 事件类型定义（基础数据结构）
EventType = TypeVar("EventType", bound="Event")
EventHandler = (
    Callable[[EventType], None] |
    Callable[[EventType], Coroutine[Any, Any, None]]
)


class Event(BaseModel, ABC):
    """事件基类（Pydantic）。
    
    所有业务事件应继承此类。
    Pydantic 提供自动验证和序列化功能。
    
    Attributes:
        event_id: 事件ID（自动生成UUID）
        timestamp: 事件时间戳
        metadata: 事件元数据
    """
    
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="事件ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    metadata: dict[str, Any] = Field(default_factory=dict, description="事件元数据")
    
    @property
    @abstractmethod
    def event_name(self) -> str:
        """事件名称（子类必须实现）。"""
        pass
    
    class Config:
        """Pydantic配置。"""
        json_encoders: ClassVar[dict] = {
            datetime: lambda v: v.isoformat(),
        }
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<{self.__class__.__name__} id={self.event_id} time={self.timestamp}>"


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



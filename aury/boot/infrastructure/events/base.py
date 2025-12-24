"""事件总线基础接口定义。

提供事件总线的抽象接口，用于模块间解耦通信。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar
import uuid


class EventBackend(Enum):
    """事件总线后端类型。"""

    MEMORY = "memory"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"


@dataclass
class Event:
    """事件基类。"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_name(self) -> str:
        """获取事件名称。"""
        return self.__class__.__name__

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "event_name": self.event_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "data": self._get_data(),
        }

    def _get_data(self) -> dict[str, Any]:
        """获取事件数据（子类应重写）。"""
        # 获取所有非基类的字段
        base_fields = {"id", "timestamp", "metadata"}
        return {
            k: v
            for k, v in self.__dict__.items()
            if k not in base_fields and not k.startswith("_")
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """从字典创建事件。"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if data.get("timestamp")
            else datetime.now(),
            metadata=data.get("metadata", {}),
        )


# 事件处理器类型
EventHandler = Callable[[Event], Any]
EventType = TypeVar("EventType", bound=Event)


class IEventBus(ABC):
    """事件总线接口。"""

    @abstractmethod
    def subscribe(
        self,
        event_type: type[Event] | str,
        handler: EventHandler,
    ) -> None:
        """订阅事件。

        Args:
            event_type: 事件类型或事件名称
            handler: 事件处理函数
        """
        ...

    @abstractmethod
    def unsubscribe(
        self,
        event_type: type[Event] | str,
        handler: EventHandler,
    ) -> None:
        """取消订阅事件。

        Args:
            event_type: 事件类型或事件名称
            handler: 事件处理函数
        """
        ...

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """发布事件。

        Args:
            event: 事件对象
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭事件总线。"""
        ...


__all__ = [
    "Event",
    "EventBackend",
    "EventHandler",
    "EventType",
    "IEventBus",
]

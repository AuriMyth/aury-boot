"""事件模型定义 - 独立文件避免循环导入。

提供事件基类、类型变量、处理器定义等基础数据结构。
此模块不依赖任何其他 infrastructure 模块，可被安全导入。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any, ClassVar, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

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
    "EventHandler",
    "EventType",
]


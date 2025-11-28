"""事件系统 - 观察者模式实现 + Pydantic。

提供事件发布/订阅机制，实现模块间的解耦。
所有事件基于Pydantic进行类型验证。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any, Optional, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

from aurimyth.foundation_kit.common.logging import logger

EventType = TypeVar("EventType", bound="Event")
EventHandler = (
    Callable[[EventType], None] |
    Callable[[EventType], Coroutine[Any, Any, None]]
)


class Event(BaseModel, ABC):
    """事件基类（Pydantic）。
    
    所有业务事件应继承此类。
    Pydantic提供自动验证和序列化功能。
    
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
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<{self.__class__.__name__} id={self.event_id} time={self.timestamp}>"


class EventBus:
    """事件总线（单例模式）。
    
    职责：
    1. 管理事件订阅者
    2. 分发事件
    3. 异步事件处理
    
    使用示例:
        # 订阅事件
        event_bus = EventBus.get_instance()
        
        @event_bus.subscribe(MyEvent)
        async def on_my_event(event: MyEvent):
            print(f"Event {event.event_name} received!")
        
        # 发布事件
        await event_bus.publish(MyEvent(...))
    """
    
    _instance: EventBus | None = None
    
    def __init__(self) -> None:
        """私有构造函数，使用 get_instance() 获取实例。"""
        if EventBus._instance is not None:
            raise RuntimeError("EventBus 是单例类，请使用 get_instance() 获取实例")
        
        self._handlers: dict[type[Event], list[EventHandler]] = {}
        self._event_history: list[Event] = []
        self._max_history_size: int = 1000
        logger.debug("事件总线已创建")
    
    @classmethod
    def get_instance(cls) -> EventBus:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def subscribe(
        self,
        event_type: type[EventType],
        handler: EventHandler | None = None,
    ) -> EventHandler | Callable[[EventHandler], EventHandler]:
        """订阅事件。
        
        可以作为装饰器使用：
            @event_bus.subscribe(MyEvent)
            async def handler(event):
                pass
        
        或直接调用：
            event_bus.subscribe(MyEvent, handler)
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
            
        Returns:
            EventHandler | Callable: 处理器或装饰器
        """
        def decorator(fn: EventHandler) -> EventHandler:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            
            self._handlers[event_type].append(fn)
            logger.debug(f"订阅事件: {event_type.__name__} -> {fn.__name__}")
            return fn
        
        if handler is not None:
            return decorator(handler)
        return decorator
    
    def unsubscribe(self, event_type: type[EventType], handler: EventHandler) -> None:
        """取消订阅事件。
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"取消订阅事件: {event_type.__name__} -> {handler.__name__}")
            except ValueError:
                pass
    
    async def publish(self, event: EventType) -> None:
        """发布事件。
        
        Args:
            event: 事件对象
        """
        logger.info(f"发布事件: {event}")
        
        # 记录事件历史
        self._add_to_history(event)
        
        # 获取处理器
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            logger.debug(f"事件 {event.event_name} 没有订阅者")
            return
        
        # 执行处理器
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                logger.debug(f"事件处理成功: {handler.__name__}")
            except Exception as exc:
                logger.error(f"事件处理失败: {handler.__name__}, 错误: {exc}")
    
    async def publish_many(self, events: list[Event]) -> None:
        """批量发布事件。
        
        Args:
            events: 事件列表
        """
        for event in events:
            await self.publish(event)
    
    def _add_to_history(self, event: Event) -> None:
        """添加事件到历史记录。
        
        Args:
            event: 事件对象
        """
        self._event_history.append(event)
        
        # 限制历史记录大小
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]
    
    def get_history(
        self,
        event_type: type[EventType] | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """获取事件历史。
        
        Args:
            event_type: 事件类型（可选，不指定则返回所有事件）
            limit: 返回数量限制
            
        Returns:
            list[Event]: 事件列表
        """
        if event_type is None:
            return self._event_history[-limit:]
        
        filtered = [e for e in self._event_history if isinstance(e, event_type)]
        return filtered[-limit:]
    
    def clear_history(self) -> None:
        """清空事件历史。"""
        self._event_history.clear()
        logger.debug("事件历史已清空")
    
    def clear_handlers(self) -> None:
        """清空所有事件处理器。"""
        self._handlers.clear()
        logger.debug("事件处理器已清空")
    
    def get_handler_count(self, event_type: type[EventType] | None = None) -> int:
        """获取处理器数量。
        
        Args:
            event_type: 事件类型（可选）
            
        Returns:
            int: 处理器数量
        """
        if event_type is None:
            return sum(len(handlers) for handlers in self._handlers.values())
        return len(self._handlers.get(event_type, []))
    
    def __repr__(self) -> str:
        """字符串表示。"""
        event_count = len(self._handlers)
        history_size = len(self._event_history)
        return f"<EventBus events={event_count} history={history_size}>"


class EventMiddleware(ABC):
    """事件中间件基类。
    
    可用于实现事件拦截、转换、日志记录等功能。
    """
    
    @abstractmethod
    async def process(self, event: Event, next_handler: Callable) -> None:
        """处理事件。
        
        Args:
            event: 事件对象
            next_handler: 下一个处理器
        """
        pass


class LoggingMiddleware(EventMiddleware):
    """日志中间件（示例）。"""
    
    async def process(self, event: Event, next_handler: Callable) -> None:
        """记录事件日志。"""
        logger.info(f"[EventMiddleware] 处理事件: {event}")
        await next_handler(event)
        logger.info(f"[EventMiddleware] 事件处理完成: {event}")


__all__ = [
    "Event",
    "EventBus",
    "EventMiddleware",
    "LoggingMiddleware",
]


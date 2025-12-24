"""内存事件总线后端。

适用于单进程场景，如开发环境或简单应用。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from aury.boot.common.logging import logger

from ..base import Event, EventHandler, IEventBus


class MemoryEventBus(IEventBus):
    """内存事件总线实现。

    使用内存中的字典存储订阅关系，支持同步和异步处理器。

    注意：仅适用于单进程，不支持跨进程事件传递。
    """

    def __init__(self) -> None:
        """初始化内存事件总线。"""
        # event_name -> list of handlers
        self._handlers: dict[str, list[EventHandler]] = {}

    def _get_event_name(self, event_type: type[Event] | str) -> str:
        """获取事件名称。"""
        if isinstance(event_type, str):
            return event_type
        return event_type.__name__

    def subscribe(
        self,
        event_type: type[Event] | str,
        handler: EventHandler,
    ) -> None:
        """订阅事件。"""
        event_name = self._get_event_name(event_type)
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)
            logger.debug(f"订阅事件: {event_name} -> {handler.__name__}")

    def unsubscribe(
        self,
        event_type: type[Event] | str,
        handler: EventHandler,
    ) -> None:
        """取消订阅事件。"""
        event_name = self._get_event_name(event_type)
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
                logger.debug(f"取消订阅事件: {event_name} -> {handler.__name__}")
            except ValueError:
                pass

    async def publish(self, event: Event) -> None:
        """发布事件。"""
        event_name = event.event_name
        handlers = self._handlers.get(event_name, [])

        if not handlers:
            logger.debug(f"事件 {event_name} 没有订阅者")
            return

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"处理事件 {event_name} 失败: {e}")

    async def close(self) -> None:
        """关闭事件总线。"""
        self._handlers.clear()
        logger.debug("内存事件总线已关闭")


__all__ = ["MemoryEventBus"]

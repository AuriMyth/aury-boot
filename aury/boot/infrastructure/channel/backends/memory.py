"""内存通道后端。

适用于单进程场景，如开发环境或简单应用。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import contextlib

from aury.boot.common.logging import logger

from ..base import ChannelMessage, IChannel


class MemoryChannel(IChannel):
    """内存通道实现。

    使用 asyncio.Queue 实现进程内的发布/订阅。

    注意：仅适用于单进程，不支持跨进程通信。
    """

    def __init__(self, max_subscribers: int = 1000) -> None:
        """初始化内存通道。

        Args:
            max_subscribers: 每个通道最大订阅者数量
        """
        self._max_subscribers = max_subscribers
        # channel -> list of queues
        self._subscribers: dict[str, list[asyncio.Queue[ChannelMessage]]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, message: ChannelMessage) -> None:
        """发布消息到通道。"""
        message.channel = channel
        async with self._lock:
            subscribers = self._subscribers.get(channel, [])
            for queue in subscribers:
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning(f"通道 [{channel}] 订阅者队列已满，消息被丢弃")

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        """订阅通道。"""
        queue: asyncio.Queue[ChannelMessage] = asyncio.Queue(maxsize=100)

        async with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = []
            if len(self._subscribers[channel]) >= self._max_subscribers:
                raise RuntimeError(f"通道 [{channel}] 订阅者数量已达上限")
            self._subscribers[channel].append(queue)

        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            async with self._lock:
                if channel in self._subscribers:
                    with contextlib.suppress(ValueError):
                        self._subscribers[channel].remove(queue)
                    if not self._subscribers[channel]:
                        del self._subscribers[channel]

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅通道（清除所有订阅者）。"""
        async with self._lock:
            if channel in self._subscribers:
                del self._subscribers[channel]

    async def close(self) -> None:
        """关闭通道，清理所有订阅。"""
        async with self._lock:
            self._subscribers.clear()
        logger.debug("内存通道已关闭")


__all__ = ["MemoryChannel"]

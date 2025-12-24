"""Redis 事件总线后端。

适用于多进程/多实例场景，支持跨进程事件传递。
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from aury.boot.common.logging import logger

from ..base import Event, EventHandler, IEventBus

if TYPE_CHECKING:
    from aury.boot.infrastructure.clients.redis import RedisClient


class RedisEventBus(IEventBus):
    """Redis 事件总线实现。

    使用 Redis Pub/Sub 实现跨进程的事件发布/订阅。
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        redis_client: RedisClient | None = None,
        channel_prefix: str = "events:",
    ) -> None:
        """初始化 Redis 事件总线。

        Args:
            url: Redis 连接 URL（当 redis_client 为 None 时必须提供）
            redis_client: RedisClient 实例（可选，优先使用）
            channel_prefix: 频道名称前缀
        
        Raises:
            ValueError: 当 url 和 redis_client 都为 None 时
        """
        if redis_client is None and url is None:
            raise ValueError("Redis 事件总线需要提供 url 或 redis_client 参数")
        
        self._url = url
        self._client = redis_client
        self._channel_prefix = channel_prefix
        # event_name -> list of handlers (本地订阅)
        self._handlers: dict[str, list[EventHandler]] = {}
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None
        self._running = False
        self._owns_client = False  # 是否自己创建的客户端
    
    async def _ensure_client(self) -> None:
        """确保 Redis 客户端已初始化。"""
        if self._client is None and self._url:
            from aury.boot.infrastructure.clients.redis import RedisClient
            self._client = RedisClient()
            await self._client.initialize(url=self._url)
            self._owns_client = True

    def _get_event_name(self, event_type: type[Event] | str) -> str:
        """获取事件名称。"""
        if isinstance(event_type, str):
            return event_type
        return event_type.__name__

    def _get_channel(self, event_name: str) -> str:
        """获取 Redis 频道名称。"""
        return f"{self._channel_prefix}{event_name}"

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
        await self._ensure_client()
        event_name = event.event_name
        channel = self._get_channel(event_name)
        data = json.dumps(event.to_dict())
        await self._client.connection.publish(channel, data)

    async def start_listening(self) -> None:
        """开始监听事件（需要在后台任务中运行）。"""
        if self._running:
            return
        
        await self._ensure_client()
        self._pubsub = self._client.connection.pubsub()
        self._running = True

        # 订阅所有已注册事件的频道
        channels = [self._get_channel(name) for name in self._handlers]
        if channels:
            await self._pubsub.subscribe(*channels)

        # 监听消息
        async for message in self._pubsub.listen():
            if not self._running:
                break

            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    event_name = data.get("event_name")
                    handlers = self._handlers.get(event_name, [])

                    for handler in handlers:
                        try:
                            # 创建事件对象
                            event = Event.from_dict(data)
                            result = handler(event)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(f"处理事件 {event_name} 失败: {e}")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"解析事件消息失败: {e}")

    async def close(self) -> None:
        """关闭事件总线。"""
        self._running = False
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        if self._listener_task:
            self._listener_task.cancel()
            self._listener_task = None
        if self._owns_client and self._client:
            await self._client.close()
            self._client = None
        self._handlers.clear()
        logger.debug("Redis 事件总线已关闭")


__all__ = ["RedisEventBus"]

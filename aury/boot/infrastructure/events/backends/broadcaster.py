"""Broadcaster 事件总线后端。

使用 broadcaster 库实现事件发布/订阅，支持多种后端：
- memory://  内存（单进程）
- redis://   Redis Pub/Sub（多进程/多实例）
- kafka://   Apache Kafka
- postgres:// PostgreSQL LISTEN/NOTIFY
"""

from __future__ import annotations

import asyncio
import json

from broadcaster import Broadcast

from aury.boot.common.logging import logger

from ..base import Event, EventHandler, IEventBus

# 框架默认前缀
DEFAULT_CHANNEL_PREFIX = "aury:event:"


class BroadcasterEventBus(IEventBus):
    """Broadcaster 事件总线实现。

    使用 broadcaster 库实现事件发布/订阅。
    
    频道命名格式：{channel_prefix}{event_name}
    默认：aury:event:user.created
    
    优点：
    - 统一接口支持多种后端
    - 内置连接池管理
    - 自动重连机制
    """

    def __init__(
        self,
        url: str,
        *,
        channel_prefix: str = DEFAULT_CHANNEL_PREFIX,
    ) -> None:
        """初始化 Broadcaster 事件总线。

        Args:
            url: 连接 URL，格式：
                - memory://          内存（单进程）
                - redis://host:port  Redis Pub/Sub
                - kafka://host:port  Apache Kafka
                - postgres://...     PostgreSQL
            channel_prefix: 频道名称前缀，默认 "aury:event:"

        """
        self._url = url
        self._channel_prefix = channel_prefix
        self._broadcast: Broadcast | None = None
        # event_name -> list of handlers (本地订阅)
        self._handlers: dict[str, list[EventHandler]] = {}
        self._listener_tasks: dict[str, asyncio.Task] = {}
        self._running = False

    async def _ensure_connected(self) -> None:
        """确保已连接。"""
        if self._broadcast is None:
            self._broadcast = Broadcast(self._url)
            await self._broadcast.connect()
            logger.debug(f"Broadcaster 事件总线已连接: {self._url}")

    def _get_event_name(self, event_type: type[Event] | str) -> str:
        """获取事件名称。"""
        if isinstance(event_type, str):
            return event_type
        return event_type.__name__

    def _get_channel(self, event_name: str) -> str:
        """获取频道名称。"""
        return f"{self._channel_prefix}{event_name}"

    def subscribe(
        self,
        event_type: type[Event] | str,
        handler: EventHandler,
    ) -> None:
        """订阅事件。

        注意：这是同步注册 handler，真正的监听在 start_listening() 中启动。
        """
        event_name = self._get_event_name(event_type)
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)
            logger.debug(f"订阅事件: {event_name} -> {handler.__name__}")

            # 如果已经在运行，立即为新事件启动监听
            if self._running and event_name not in self._listener_tasks:
                task = asyncio.create_task(self._listen_event(event_name))
                self._listener_tasks[event_name] = task

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
                
                # 如果该事件没有处理器了，停止监听
                if not self._handlers[event_name] and event_name in self._listener_tasks:
                    self._listener_tasks[event_name].cancel()
                    del self._listener_tasks[event_name]
            except ValueError:
                pass

    async def publish(self, event: Event) -> None:
        """发布事件。"""
        await self._ensure_connected()
        event_name = event.event_name
        channel = self._get_channel(event_name)
        data = json.dumps(event.to_dict())
        await self._broadcast.publish(channel=channel, message=data)

    async def _listen_event(self, event_name: str) -> None:
        """监听单个事件的消息。"""
        channel = self._get_channel(event_name)
        try:
            async with self._broadcast.subscribe(channel=channel) as subscriber:
                async for event_data in subscriber:
                    if not self._running:
                        break
                    try:
                        data = json.loads(event_data.message)
                        handlers = self._handlers.get(event_name, [])
                        for handler in handlers:
                            try:
                                event = Event.from_dict(data)
                                result = handler(event)
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception as e:
                                logger.error(f"处理事件 {event_name} 失败: {e}")
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"解析事件消息失败: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"事件监听异常 {event_name}: {e}")

    async def start_listening(self) -> None:
        """开始监听事件（需要在后台任务中运行）。"""
        if self._running:
            return

        await self._ensure_connected()
        self._running = True

        # 为每个已订阅的事件启动监听任务
        for event_name in self._handlers:
            if event_name not in self._listener_tasks:
                task = asyncio.create_task(self._listen_event(event_name))
                self._listener_tasks[event_name] = task

        logger.debug(f"Broadcaster 事件总线开始监听，事件数: {len(self._handlers)}")

    async def close(self) -> None:
        """关闭事件总线。"""
        self._running = False

        # 取消所有监听任务
        for task in self._listener_tasks.values():
            task.cancel()
        self._listener_tasks.clear()

        # 关闭连接
        if self._broadcast:
            await self._broadcast.disconnect()
            self._broadcast = None

        self._handlers.clear()
        logger.debug("Broadcaster 事件总线已关闭")


__all__ = ["BroadcasterEventBus"]

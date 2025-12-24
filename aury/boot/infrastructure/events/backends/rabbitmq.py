"""RabbitMQ 事件总线后端。

使用 aio-pika 实现 RabbitMQ 事件总线。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aury.boot.common.logging import logger

from ..base import Event, EventHandler, IEventBus

# 延迟导入 aio-pika（可选依赖）
try:
    import aio_pika
    from aio_pika import ExchangeType
    from aio_pika import Message as AioPikaMessage
    from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange

    _AIO_PIKA_AVAILABLE = True
except ImportError:
    _AIO_PIKA_AVAILABLE = False
    aio_pika = None
    ExchangeType = None
    AioPikaMessage = None
    AbstractChannel = None
    AbstractConnection = None
    AbstractExchange = None


class RabbitMQEventBus(IEventBus):
    """RabbitMQ 事件总线实现。

    使用 RabbitMQ Exchange (fanout/topic) 实现事件发布/订阅。

    注意：需要安装 aio-pika: pip install aio-pika
    """

    def __init__(
        self,
        url: str,
        *,
        exchange_name: str = "events",
        exchange_type: str = "topic",
    ) -> None:
        """初始化 RabbitMQ 事件总线。

        Args:
            url: RabbitMQ 连接 URL
            exchange_name: 交换机名称
            exchange_type: 交换机类型 (topic/fanout)
        """
        if not _AIO_PIKA_AVAILABLE:
            raise ImportError("aio-pika 未安装。请安装: pip install aio-pika")

        self._url = url
        self._exchange_name = exchange_name
        self._exchange_type = exchange_type
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None
        # event_name -> list of handlers
        self._handlers: dict[str, list[EventHandler]] = {}
        self._consumer_tasks: list[asyncio.Task] = []
        self._running = False

    async def _ensure_connection(self) -> None:
        """确保连接已建立。"""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._url)
            self._channel = await self._connection.channel()

            # 声明交换机
            exchange_type = (
                ExchangeType.TOPIC
                if self._exchange_type == "topic"
                else ExchangeType.FANOUT
            )
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                exchange_type,
                durable=True,
            )
            logger.info("RabbitMQ 事件总线连接已建立")

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
        await self._ensure_connection()
        event_name = event.event_name
        data = json.dumps(event.to_dict())

        message = AioPikaMessage(
            body=data.encode(),
            content_type="application/json",
        )

        # 使用事件名称作为 routing key
        await self._exchange.publish(message, routing_key=event_name)

    async def start_listening(self) -> None:
        """开始监听事件（需要在后台任务中运行）。"""
        await self._ensure_connection()
        self._running = True

        # 为每个事件类型创建队列和消费者
        for event_name in self._handlers:
            queue = await self._channel.declare_queue(
                f"events.{event_name}",
                durable=True,
            )
            await queue.bind(self._exchange, routing_key=event_name)

            async def process_message(message, en=event_name):
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        handlers = self._handlers.get(en, [])
                        for handler in handlers:
                            try:
                                event = Event.from_dict(data)
                                result = handler(event)
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception as e:
                                logger.error(f"处理事件 {en} 失败: {e}")
                    except Exception as e:
                        logger.warning(f"解析事件消息失败: {e}")

            task = asyncio.create_task(self._consume_queue(queue, process_message))
            self._consumer_tasks.append(task)

    async def _consume_queue(self, queue, callback) -> None:
        """消费队列消息。"""
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self._running:
                    break
                await callback(message)

    async def close(self) -> None:
        """关闭事件总线。"""
        self._running = False
        for task in self._consumer_tasks:
            task.cancel()
        self._consumer_tasks.clear()

        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None

        self._handlers.clear()
        logger.debug("RabbitMQ 事件总线已关闭")


__all__ = ["RabbitMQEventBus"]

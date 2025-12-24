"""RabbitMQ 消息队列后端。

使用 aio-pika 实现 RabbitMQ 消息队列。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
from typing import Any

from aury.boot.common.logging import logger

from ..base import IMQ, MQMessage

# 延迟导入 aio-pika（可选依赖）
try:
    import aio_pika
    from aio_pika import Message as AioPikaMessage
    from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractQueue

    _AIO_PIKA_AVAILABLE = True
except ImportError:
    _AIO_PIKA_AVAILABLE = False
    aio_pika = None
    AioPikaMessage = None
    AbstractChannel = None
    AbstractConnection = None
    AbstractQueue = None


class RabbitMQ(IMQ):
    """RabbitMQ 消息队列实现。

    使用 aio-pika 实现 AMQP 0.9.1 协议的消息队列。

    注意：需要安装 aio-pika: pip install aio-pika
    """

    def __init__(self, url: str) -> None:
        """初始化 RabbitMQ 消息队列。

        Args:
            url: RabbitMQ 连接 URL (amqp://user:pass@host:port/vhost)
        """
        if not _AIO_PIKA_AVAILABLE:
            raise ImportError(
                "aio-pika 未安装。请安装: pip install aio-pika"
            )
        self._url = url
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._queues: dict[str, AbstractQueue] = {}
        self._consuming = False

    async def _ensure_connection(self) -> None:
        """确保连接已建立。"""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._url)
            self._channel = await self._connection.channel()
            logger.info("RabbitMQ 连接已建立")

    async def _get_queue(self, queue: str) -> AbstractQueue:
        """获取或创建队列。"""
        await self._ensure_connection()
        if queue not in self._queues:
            self._queues[queue] = await self._channel.declare_queue(
                queue, durable=True
            )
        return self._queues[queue]

    async def send(self, queue: str, message: MQMessage) -> str:
        """发送消息到队列。"""
        await self._ensure_connection()
        message.queue = queue

        aio_message = AioPikaMessage(
            body=json.dumps(message.to_dict()).encode(),
            message_id=message.id,
            headers=message.headers,
        )

        await self._channel.default_exchange.publish(
            aio_message,
            routing_key=queue,
        )
        return message.id

    async def receive(
        self,
        queue: str,
        timeout: float | None = None,
    ) -> MQMessage | None:
        """从队列接收消息。"""
        queue_obj = await self._get_queue(queue)

        try:
            if timeout:
                incoming = await asyncio.wait_for(
                    queue_obj.get(no_ack=False),
                    timeout=timeout,
                )
            else:
                incoming = await queue_obj.get(no_ack=False)

            if incoming is None:
                return None

            data = json.loads(incoming.body.decode())
            message = MQMessage.from_dict(data)
            # 存储原始消息用于 ack/nack
            message.headers["_raw_message"] = incoming
            return message

        except TimeoutError:
            return None
        except Exception as e:
            logger.error(f"接收消息失败: {e}")
            return None

    async def ack(self, message: MQMessage) -> None:
        """确认消息已处理。"""
        raw_message = message.headers.get("_raw_message")
        if raw_message:
            await raw_message.ack()

    async def nack(self, message: MQMessage, requeue: bool = True) -> None:
        """拒绝消息。"""
        raw_message = message.headers.get("_raw_message")
        if raw_message:
            await raw_message.nack(requeue=requeue)

    async def consume(
        self,
        queue: str,
        handler: Callable[[MQMessage], Any],
        *,
        prefetch: int = 1,
    ) -> None:
        """消费队列消息。"""
        await self._ensure_connection()
        await self._channel.set_qos(prefetch_count=prefetch)

        queue_obj = await self._get_queue(queue)
        self._consuming = True
        logger.info(f"开始消费队列: {queue}")

        async with queue_obj.iterator() as queue_iter:
            async for incoming in queue_iter:
                if not self._consuming:
                    break

                try:
                    data = json.loads(incoming.body.decode())
                    message = MQMessage.from_dict(data)
                    message.headers["_raw_message"] = incoming

                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        await result
                    await incoming.ack()

                except Exception as e:
                    logger.error(f"处理消息失败: {e}")
                    await incoming.nack(requeue=True)

    async def close(self) -> None:
        """关闭连接。"""
        self._consuming = False
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._queues.clear()
        logger.debug("RabbitMQ 连接已关闭")


__all__ = ["RabbitMQ"]

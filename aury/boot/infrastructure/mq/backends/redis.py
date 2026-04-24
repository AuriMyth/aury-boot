"""Redis 消息队列后端。

使用 Redis List 实现简单的消息队列。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

from ..base import IMQ, MQBackend, MQMessage, MQPosition, MQPublishResult, MQReceivedMessage

if TYPE_CHECKING:
    from aury.boot.infrastructure.clients.redis import RedisClient


class RedisMQ(IMQ):
    """Redis 消息队列实现。

    使用 Redis List (LPUSH/BRPOP) 实现可靠的消息队列。
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        redis_client: RedisClient | None = None,
        prefix: str = "mq:",
    ) -> None:
        """初始化 Redis 消息队列。

        Args:
            url: Redis 连接 URL（当 redis_client 为 None 时必须提供）
            redis_client: RedisClient 实例（可选，优先使用）
            prefix: 队列名称前缀
        
        Raises:
            ValueError: 当 url 和 redis_client 都为 None 时
        """
        if redis_client is None and url is None:
            raise ValueError("Redis 消息队列需要提供 url 或 redis_client 参数")
        
        self._url = url
        self._client = redis_client
        self._prefix = prefix
        self._consuming = False
        self._owns_client = False  # 是否自己创建的客户端
    
    async def _ensure_client(self) -> None:
        """确保 Redis 客户端已初始化。"""
        if self._client is None and self._url:
            from aury.boot.infrastructure.clients.redis import RedisClient
            self._client = RedisClient()
            await self._client.initialize(url=self._url)
            self._owns_client = True

    def _queue_key(self, queue: str) -> str:
        """获取队列的 Redis key。"""
        return f"{self._prefix}{queue}"

    def _processing_key(self, queue: str) -> str:
        """获取处理中队列的 Redis key。"""
        return f"{self._prefix}{queue}:processing"

    async def send(self, queue: str, message: MQMessage) -> MQPublishResult:
        """发送消息到队列。"""
        await self._ensure_client()
        message.queue = queue
        data = json.dumps(message.to_dict())
        await self._client.connection.lpush(self._queue_key(queue), data)
        return MQPublishResult(
            message_id=message.id,
            position=MQPosition(
                backend=MQBackend.REDIS,
                queue=queue,
                id=message.id,
                metadata={"queue_key": self._queue_key(queue)},
            ),
        )

    async def receive(
        self,
        queue: str,
        timeout: float | None = None,
    ) -> MQReceivedMessage | None:
        """从队列接收消息。"""
        await self._ensure_client()
        timeout_int = int(timeout) if timeout else 0
        result = await self._client.connection.brpop(
            self._queue_key(queue),
            timeout=timeout_int,
        )
        if result is None:
            return None

        _, data = result
        try:
            msg_dict = json.loads(data)
            message = MQMessage.from_dict(msg_dict)
            # 将消息放入处理中队列
            await self._client.connection.hset(
                self._processing_key(queue),
                message.id,
                data,
            )
            return MQReceivedMessage(
                message=message,
                position=MQPosition(
                    backend=MQBackend.REDIS,
                    queue=queue,
                    id=message.id,
                    metadata={
                        "queue_key": self._queue_key(queue),
                        "processing_key": self._processing_key(queue),
                    },
                ),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析消息失败: {e}")
            return None

    async def ack(self, received: MQReceivedMessage | MQPosition) -> None:
        """确认消息已处理。"""
        queue = received.position.queue if isinstance(received, MQReceivedMessage) and received.position else received.queue
        message_id = received.message.id if isinstance(received, MQReceivedMessage) else str(received.id)
        await self._client.connection.hdel(
            self._processing_key(queue),
            message_id,
        )

    async def nack(self, received: MQReceivedMessage | MQPosition, requeue: bool = True) -> None:
        """拒绝消息。"""
        queue = received.position.queue if isinstance(received, MQReceivedMessage) and received.position else received.queue
        message_id = received.message.id if isinstance(received, MQReceivedMessage) else str(received.id)
        await self._client.connection.hdel(
            self._processing_key(queue),
            message_id,
        )
        if not isinstance(received, MQReceivedMessage):
            return
        message = received.message
        if requeue and message.retry_count < message.max_retries:
            message.retry_count += 1
            await self.send(queue, message)

    async def consume(
        self,
        queue: str,
        handler: Callable[[MQReceivedMessage], Any],
        *,
        prefetch: int = 1,
    ) -> None:
        """消费队列消息。"""
        self._consuming = True
        logger.info(f"开始消费队列: {queue}")

        while self._consuming:
            try:
                received = await self.receive(queue, timeout=1.0)
                if received is None:
                    continue

                try:
                    result = handler(received)
                    if asyncio.iscoroutine(result):
                        await result
                    await self.ack(received)
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")
                    await self.nack(received, requeue=True)

            except Exception as e:
                logger.error(f"消费消息异常: {e}")
                await asyncio.sleep(1)

    async def close(self) -> None:
        """关闭连接。"""
        self._consuming = False
        if self._owns_client and self._client:
            await self._client.cleanup()
            self._client = None
        logger.debug("Redis 消息队列已关闭")


__all__ = ["RedisMQ"]

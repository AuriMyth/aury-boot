"""Redis Stream 消息队列后端。

使用 Redis Stream 实现支持消费者组的消息队列。
相比 Redis List，提供更强的持久化和消费保证。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

from ..base import IMQ, MQMessage

if TYPE_CHECKING:
    from aury.boot.infrastructure.clients.redis import RedisClient


class RedisStreamMQ(IMQ):
    """Redis Stream 消息队列实现。

    使用 Redis Stream (XADD/XREADGROUP/XACK) 实现可靠的消息队列。
    
    特性:
    - 消费者组支持多实例消费
    - 消息持久化 (配合 AOF)
    - 消息确认机制
    - 支持消息重放
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        redis_client: RedisClient | None = None,
        prefix: str = "stream:",
        consumer_group: str = "default",
        consumer_name: str | None = None,
        max_len: int | None = None,
    ) -> None:
        """初始化 Redis Stream 消息队列。

        Args:
            url: Redis 连接 URL（当 redis_client 为 None 时必须提供）
            redis_client: RedisClient 实例（可选，优先使用）
            prefix: 队列名称前缀
            consumer_group: 消费者组名称
            consumer_name: 消费者名称（默认自动生成）
            max_len: Stream 最大长度（可选，用于自动裁剪）
        
        Raises:
            ValueError: 当 url 和 redis_client 都为 None 时
        """
        if redis_client is None and url is None:
            raise ValueError("Redis Stream 消息队列需要提供 url 或 redis_client 参数")
        
        self._url = url
        self._client = redis_client
        self._prefix = prefix
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name or f"consumer-{id(self)}"
        self._max_len = max_len
        self._consuming = False
        self._owns_client = False
        self._log_sample_counter = 0  # 日志采样计数器
    
    # 日志采样率：每 N 个 send 打印 1 次
    LOG_SAMPLE_RATE = 100
    
    async def _ensure_client(self) -> None:
        """确保 Redis 客户端已初始化。"""
        if self._client is None and self._url:
            from aury.boot.infrastructure.clients.redis import RedisClient
            # 创建独立实例（不使用 get_instance 避免和全局实例冲突）
            self._client = RedisClient(name=f"mq-{id(self)}")
            self._client.configure(url=self._url)
            await self._client.initialize()
            self._owns_client = True

    def _stream_key(self, queue: str) -> str:
        """获取 Stream 的 Redis key。"""
        return f"{self._prefix}{queue}"

    async def _ensure_group(self, queue: str) -> None:
        """确保消费者组存在。"""
        stream_key = self._stream_key(queue)
        try:
            await self._client.connection.xgroup_create(
                stream_key,
                self._consumer_group,
                id="0",
                mkstream=True,
            )
            logger.debug(f"创建消费者组: {self._consumer_group} on {stream_key}")
        except Exception as e:
            # 组已存在，忽略
            if "BUSYGROUP" not in str(e):
                raise

    async def send(self, queue: str, message: MQMessage) -> str:
        """发送消息到 Stream。
        
        使用 XADD 命令，支持 MAXLEN 自动裁剪。
        """
        await self._ensure_client()
        message.queue = queue
        
        # 序列化消息
        data = {
            "payload": json.dumps(message.to_dict()),
        }
        
        stream_key = self._stream_key(queue)
        
        # XADD with optional MAXLEN
        if self._max_len:
            msg_id = await self._client.connection.xadd(
                stream_key,
                data,
                maxlen=self._max_len,
                approximate=True,  # ~ 近似裁剪，性能更好
            )
        else:
            msg_id = await self._client.connection.xadd(stream_key, data)
        
        # 采样日志：每 N 个消息打印 1 次
        self._log_sample_counter += 1
        if self._log_sample_counter % self.LOG_SAMPLE_RATE == 1:
            logger.debug(f"发送消息到 Stream: {stream_key}, id={msg_id}, count={self._log_sample_counter}")
        return message.id

    async def receive(
        self,
        queue: str,
        timeout: float | None = None,
    ) -> MQMessage | None:
        """从 Stream 接收消息（不使用消费者组）。
        
        用于简单场景，直接 XREAD 读取最新消息。
        """
        await self._ensure_client()
        
        stream_key = self._stream_key(queue)
        timeout_ms = int(timeout * 1000) if timeout else 0
        
        result = await self._client.connection.xread(
            streams={stream_key: "$"},
            count=1,
            block=timeout_ms,
        )
        
        if not result:
            return None
        
        # 解析结果: [[stream_key, [(msg_id, data)]]]
        for stream, messages in result:
            for msg_id, data in messages:
                try:
                    payload = data.get(b"payload") or data.get("payload")
                    if isinstance(payload, bytes):
                        payload = payload.decode()
                    msg_dict = json.loads(payload)
                    message = MQMessage.from_dict(msg_dict)
                    message._stream_id = msg_id  # 保存 stream ID 用于 ACK
                    return message
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"解析消息失败: {e}")
                    return None
        
        return None

    async def receive_group(
        self,
        queue: str,
        timeout: float | None = None,
    ) -> MQMessage | None:
        """从 Stream 接收消息（使用消费者组）。
        
        使用 XREADGROUP 从消费者组读取，支持多实例消费。
        """
        await self._ensure_client()
        await self._ensure_group(queue)
        
        stream_key = self._stream_key(queue)
        timeout_ms = int(timeout * 1000) if timeout else 0
        
        result = await self._client.connection.xreadgroup(
            groupname=self._consumer_group,
            consumername=self._consumer_name,
            streams={stream_key: ">"},  # > 表示只读取新消息
            count=1,
            block=timeout_ms,
        )
        
        if not result:
            return None
        
        # 解析结果
        for stream, messages in result:
            for msg_id, data in messages:
                try:
                    payload = data.get(b"payload") or data.get("payload")
                    if isinstance(payload, bytes):
                        payload = payload.decode()
                    msg_dict = json.loads(payload)
                    message = MQMessage.from_dict(msg_dict)
                    message._stream_id = msg_id  # 保存用于 ACK
                    message.queue = queue
                    return message
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"解析消息失败: {e}")
                    # ACK 损坏的消息，防止阻塞
                    await self._client.connection.xack(
                        stream_key, self._consumer_group, msg_id
                    )
                    return None
        
        return None

    async def ack(self, message: MQMessage) -> None:
        """确认消息已处理。"""
        if not message.queue:
            return
        
        stream_id = getattr(message, "_stream_id", None)
        if stream_id:
            stream_key = self._stream_key(message.queue)
            await self._client.connection.xack(
                stream_key, self._consumer_group, stream_id
            )
            logger.debug(f"ACK 消息: {stream_id}")

    async def nack(self, message: MQMessage, requeue: bool = True) -> None:
        """拒绝消息。
        
        Redis Stream 没有原生 NACK，通过重新发送实现。
        """
        if not message.queue:
            return
        
        stream_id = getattr(message, "_stream_id", None)
        if stream_id:
            stream_key = self._stream_key(message.queue)
            # 先 ACK 原消息
            await self._client.connection.xack(
                stream_key, self._consumer_group, stream_id
            )
            
            if requeue and message.retry_count < message.max_retries:
                # 重新发送
                message.retry_count += 1
                await self.send(message.queue, message)
                logger.debug(f"NACK 重新入队: {message.id}, retry={message.retry_count}")

    async def consume(
        self,
        queue: str,
        handler: Callable[[MQMessage], Any],
        *,
        prefetch: int = 1,
    ) -> None:
        """消费队列消息（使用消费者组）。"""
        self._consuming = True
        await self._ensure_group(queue)
        logger.info(f"开始消费 Stream: {queue}, group={self._consumer_group}")

        while self._consuming:
            try:
                message = await self.receive_group(queue, timeout=1.0)
                if message is None:
                    continue

                try:
                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        await result
                    await self.ack(message)
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")
                    await self.nack(message, requeue=True)

            except Exception as e:
                logger.error(f"消费消息异常: {e}")
                await asyncio.sleep(1)

    async def read_all(
        self,
        queue: str,
        start: str = "-",
        end: str = "+",
        count: int | None = None,
    ) -> list[MQMessage]:
        """读取 Stream 中的所有消息（用于 compaction）。
        
        使用 XRANGE 读取指定范围的消息。
        
        Args:
            queue: 队列名称
            start: 起始 ID（"-" 表示最早）
            end: 结束 ID（"+" 表示最新）
            count: 最大数量
            
        Returns:
            消息列表
        """
        await self._ensure_client()
        stream_key = self._stream_key(queue)
        
        result = await self._client.connection.xrange(
            stream_key,
            min=start,
            max=end,
            count=count,
        )
        
        messages = []
        for msg_id, data in result:
            try:
                payload = data.get(b"payload") or data.get("payload")
                if isinstance(payload, bytes):
                    payload = payload.decode()
                msg_dict = json.loads(payload)
                message = MQMessage.from_dict(msg_dict)
                message._stream_id = msg_id
                messages.append(message)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"跳过损坏的消息 {msg_id}: {e}")
        
        return messages

    async def read_blocking(
        self,
        queue: str,
        last_id: str = "$",
        count: int = 10,
        block_ms: int = 100,
    ) -> list[MQMessage]:
        """阻塞读取 Stream 中的新消息（使用 XREAD BLOCK）。
        
        Args:
            queue: 队列名称
            last_id: 起始 ID（"$" 表示只等待新消息，"0" 表示从开头）
            count: 最大读取数量
            block_ms: 阻塞等待超时（毫秒），0 表示不阻塞
            
        Returns:
            消息列表
        """
        await self._ensure_client()
        stream_key = self._stream_key(queue)
        
        result = await self._client.connection.xread(
            streams={stream_key: last_id},
            count=count,
            block=block_ms,
        )
        
        if not result:
            return []
        
        messages = []
        for stream, stream_messages in result:
            for msg_id, data in stream_messages:
                try:
                    payload = data.get(b"payload") or data.get("payload")
                    if isinstance(payload, bytes):
                        payload = payload.decode()
                    msg_dict = json.loads(payload)
                    message = MQMessage.from_dict(msg_dict)
                    message._stream_id = msg_id
                    messages.append(message)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"跳过损坏的消息 {msg_id}: {e}")
        
        return messages

    async def trim(
        self,
        queue: str,
        *,
        maxlen: int | None = None,
        minid: str | None = None,
    ) -> int:
        """裁剪 Stream。
        
        Args:
            queue: 队列名称
            maxlen: 保留的最大长度
            minid: 保留此 ID 之后的消息
            
        Returns:
            删除的消息数量
        """
        await self._ensure_client()
        stream_key = self._stream_key(queue)
        
        if minid:
            return await self._client.connection.xtrim(
                stream_key, minid=minid, approximate=False
            )
        elif maxlen is not None:
            # maxlen=0 也应该生效（清空 stream）
            return await self._client.connection.xtrim(
                stream_key, maxlen=maxlen, approximate=False
            )
        return 0

    async def delete_stream(self, queue: str) -> bool:
        """删除整个 Stream。"""
        await self._ensure_client()
        stream_key = self._stream_key(queue)
        return await self._client.connection.delete(stream_key) > 0

    async def stream_info(self, queue: str) -> dict[str, Any]:
        """获取 Stream 信息。"""
        await self._ensure_client()
        stream_key = self._stream_key(queue)
        try:
            return await self._client.connection.xinfo_stream(stream_key)
        except Exception:
            return {}

    async def close(self) -> None:
        """关闭连接。"""
        self._consuming = False
        if self._owns_client and self._client:
            await self._client.cleanup()
            self._client = None
        logger.debug("Redis Stream 消息队列已关闭")


__all__ = ["RedisStreamMQ"]

"""Redis 通道后端。

适用于多进程/多实例场景，支持跨进程通信。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
import json
from typing import TYPE_CHECKING

from aury.boot.common.logging import logger

from ..base import ChannelMessage, IChannel

if TYPE_CHECKING:
    from aury.boot.infrastructure.clients.redis import RedisClient


class RedisChannel(IChannel):
    """Redis 通道实现。

    使用 Redis Pub/Sub 实现跨进程的发布/订阅。
    """

    def __init__(self, redis_client: RedisClient) -> None:
        """初始化 Redis 通道。

        Args:
            redis_client: RedisClient 实例
        """
        self._client = redis_client
        self._pubsub = None

    async def publish(self, channel: str, message: ChannelMessage) -> None:
        """发布消息到通道。"""
        message.channel = channel
        # 序列化消息
        data = {
            "data": message.data,
            "event": message.event,
            "id": message.id,
            "channel": message.channel,
            "timestamp": message.timestamp.isoformat(),
        }
        await self._client.connection.publish(channel, json.dumps(data))

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        """订阅通道。"""
        pubsub = self._client.connection.pubsub()
        await pubsub.subscribe(channel)

        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] == "message":
                    try:
                        data = json.loads(raw_message["data"])
                        message = ChannelMessage(
                            data=data.get("data"),
                            event=data.get("event"),
                            id=data.get("id"),
                            channel=data.get("channel"),
                            timestamp=datetime.fromisoformat(data["timestamp"])
                            if data.get("timestamp")
                            else datetime.now(),
                        )
                        yield message
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"解析通道消息失败: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅通道。"""
        if self._pubsub:
            await self._pubsub.unsubscribe(channel)

    async def close(self) -> None:
        """关闭通道。"""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        logger.debug("Redis 通道已关闭")


__all__ = ["RedisChannel"]

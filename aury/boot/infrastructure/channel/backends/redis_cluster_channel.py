"""Redis Cluster 通道封装。

使用 RedisClusterBackend，提供与 BroadcasterChannel 一致的接口。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime

from aury.boot.common.logging import logger

from ..base import ChannelMessage, IChannel
from .redis_cluster import RedisClusterBackend


class RedisClusterChannel(IChannel):
    """Redis Cluster 通道实现。
    
    使用 broadcaster 架构：共享连接 + Queue 分发。
    支持 Sharded Pub/Sub (Redis 7.0+)。
    """

    def __init__(self, url: str) -> None:
        """初始化 Redis Cluster 通道。

        Args:
            url: redis-cluster://[password@]host:port
        """
        self._url = url
        self._backend = RedisClusterBackend(url)
        self._connected = False
        # 订阅者管理（与 broadcaster 相同的模式）
        self._subscribers: dict[str, set] = {}
        self._listener_task = None

    async def _ensure_connected(self) -> None:
        if not self._connected:
            await self._backend.connect()
            self._listener_task = __import__("asyncio").create_task(self._listener())
            self._connected = True
            logger.debug(f"Redis Cluster 通道已连接: {self._mask_url(self._url)}")

    def _mask_url(self, url: str) -> str:
        if "@" in url:
            parts = url.split("@")
            prefix = parts[0]
            suffix = parts[1]
            if "://" in prefix:
                scheme = prefix.split("://")[0]
                return f"{scheme}://***@{suffix}"
        return url

    async def _listener(self) -> None:
        """监听后端消息，分发到订阅者。"""
        import asyncio
        while True:
            try:
                event = await self._backend.next_published()
                channel = event.channel
                if channel in self._subscribers:
                    for queue in list(self._subscribers[channel]):
                        await queue.put(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Redis Cluster listener error: {e}")

    async def publish(self, channel: str, message: ChannelMessage) -> None:
        await self._ensure_connected()
        message.channel = channel
        data = {
            "data": message.data,
            "event": message.event,
            "id": message.id,
            "channel": message.channel,
            "timestamp": message.timestamp.isoformat(),
        }
        await self._backend.publish(channel, json.dumps(data))

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        import asyncio
        await self._ensure_connected()
        
        queue: asyncio.Queue = asyncio.Queue()
        
        try:
            # 首个订阅者时订阅 Redis
            if channel not in self._subscribers:
                await self._backend.subscribe(channel)
                self._subscribers[channel] = set()
            self._subscribers[channel].add(queue)
            
            while True:
                event = await queue.get()
                try:
                    data = json.loads(event.message)
                    yield ChannelMessage(
                        data=data.get("data"),
                        event=data.get("event"),
                        id=data.get("id"),
                        channel=data.get("channel") or channel,
                        timestamp=datetime.fromisoformat(data["timestamp"])
                        if data.get("timestamp")
                        else datetime.now(),
                    )
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"解析通道消息失败: {e}")
        finally:
            if channel in self._subscribers:
                self._subscribers[channel].discard(queue)
                if not self._subscribers[channel]:
                    del self._subscribers[channel]
                    try:
                        await self._backend.unsubscribe(channel)
                    except Exception:
                        pass

    async def psubscribe(self, pattern: str) -> AsyncIterator[ChannelMessage]:
        raise NotImplementedError(
            "Redis Cluster Sharded Pub/Sub 不支持模式订阅。"
            "请使用具体的 channel 名称。"
        )

    async def unsubscribe(self, channel: str) -> None:
        pass  # subscribe() 的 finally 块自动处理

    async def close(self) -> None:
        if self._connected:
            if self._listener_task:
                self._listener_task.cancel()
            await self._backend.disconnect()
            self._connected = False
            self._subscribers.clear()
            logger.debug("Redis Cluster 通道已关闭")


__all__ = ["RedisClusterChannel"]

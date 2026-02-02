"""Redis Cluster 通道后端。

使用 coredis 库支持异步 Redis Cluster Sharded Pub/Sub (Redis 7.0+)。

URL 格式：
    redis-cluster://password@host:port
    redis-cluster://host:port
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from aury.boot.common.logging import logger

try:
    from coredis import RedisCluster
except ImportError as exc:
    raise ImportError(
        "Redis Cluster Channel 需要安装 coredis: pip install coredis"
    ) from exc


@dataclass
class Event:
    """与 broadcaster._base.Event 兼容的事件类。"""
    channel: str
    message: str


class RedisClusterBackend:
    """Redis Cluster Pub/Sub 后端。
    
    使用 coredis 库的 sharded_pubsub() 支持 Sharded Pub/Sub。
    与 broadcaster.RedisBackend 接口兼容。
    """

    def __init__(self, url: str) -> None:
        host, port, password = self._parse_url(url)
        
        self._client: RedisCluster = RedisCluster(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
        )
        self._pubsub: Any = None
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._listener_task: asyncio.Task | None = None
        self._subscribed_channels: set[str] = set()

    def _parse_url(self, url: str) -> tuple[str, int, str | None]:
        """解析 URL。"""
        url = url.replace("redis-cluster://", "redis://")
        parsed = urlparse(url)
        password = parsed.password
        # 支持 password@host 格式
        if not password and parsed.username:
            password = parsed.username
        return parsed.hostname or "localhost", parsed.port or 6379, password

    async def connect(self) -> None:
        """连接并初始化 pubsub。"""
        # coredis 的 sharded_pubsub() 支持 Redis 7.0+ Sharded Pub/Sub
        self._pubsub = self._client.sharded_pubsub()
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.debug("Redis Cluster Channel 已连接")

    async def disconnect(self) -> None:
        """断开连接。"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.sunsubscribe()
        await self._client.close()
        logger.debug("Redis Cluster Channel 已断开")

    async def subscribe(self, channel: str) -> None:
        """订阅频道。"""
        if self._pubsub:
            await self._pubsub.ssubscribe(channel)
            self._subscribed_channels.add(channel)

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅。"""
        if self._pubsub and channel in self._subscribed_channels:
            await self._pubsub.sunsubscribe(channel)
            self._subscribed_channels.discard(channel)

    async def publish(self, channel: str, message: str) -> None:
        """发布消息（使用 SPUBLISH）。"""
        await self._client.spublish(channel, message)

    async def next_published(self) -> Event:
        """获取下一条消息。"""
        return await self._queue.get()

    async def _listen_loop(self) -> None:
        """监听消息循环。"""
        while True:
            try:
                if self._pubsub:
                    async for message in self._pubsub:
                        if message and message.get("type") in ("message", "smessage"):
                            event = Event(
                                channel=message.get("channel", ""),
                                message=message.get("data", ""),
                            )
                            await self._queue.put(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Redis Cluster pubsub error: {e}")
                await asyncio.sleep(1)


__all__ = ["RedisClusterBackend"]

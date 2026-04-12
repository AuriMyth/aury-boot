"""Redis Sentinel 支持工具。

提供 Aury 基础设施组件可复用的 Sentinel 连接适配器与前缀包装器。
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import replace
from datetime import datetime, timedelta
import json
from typing import Any
from weakref import WeakSet

from redis.asyncio import Redis
from redis.asyncio.sentinel import Sentinel

from aury.boot.common.logging import logger
from aury.boot.infrastructure.cache.base import ICache
from aury.boot.infrastructure.channel.base import ChannelMessage, ChannelStatsTracker, IChannel


def normalize_prefix(prefix: str | None) -> str:
    """标准化前缀，统一补齐结尾冒号。"""
    value = str(prefix or "").strip()
    if not value:
        return ""
    return value if value.endswith(":") else f"{value}:"


def instance_prefix(base_prefix: str | None, instance_name: str) -> str:
    """为多实例资源生成独立前缀。"""
    normalized = normalize_prefix(base_prefix)
    if not normalized:
        return ""
    if instance_name == "default":
        return normalized
    return f"{normalized}{instance_name}:"


def parse_sentinel_nodes(nodes: list[str]) -> list[tuple[str, int]]:
    """解析 Sentinel 节点列表。"""
    sentinels: list[tuple[str, int]] = []
    for node in nodes:
        host, _, port = str(node).strip().partition(":")
        if not host or not port:
            raise ValueError(f"Invalid sentinel node: {node}")
        sentinels.append((host, int(port)))
    if not sentinels:
        raise ValueError("Redis sentinel nodes are required")
    return sentinels


class SentinelRedisClientAdapter:
    """兼容 Aury Redis 依赖后端的 Sentinel 适配器。"""

    def __init__(
        self,
        *,
        name: str,
        sentinels: list[tuple[str, int]],
        master_name: str,
        redis_password: str | None,
        sentinel_password: str | None,
        db: int,
        decode_responses: bool,
        socket_timeout: float,
        max_connections: int,
    ) -> None:
        self.name = name
        self._sentinels = sentinels
        self._master_name = master_name
        self._redis_password = redis_password or None
        self._sentinel_password = sentinel_password or None
        self._db = db
        self._decode_responses = decode_responses
        self._socket_timeout = socket_timeout
        self._max_connections = max_connections
        self._sentinel: Sentinel | None = None
        self._redis: Redis | None = None
        self._initialized = False

    @property
    def is_cluster(self) -> bool:
        return False

    @property
    def connection(self) -> Redis:
        if self._redis is None:
            raise RuntimeError(f"Sentinel redis client [{self.name}] not initialized")
        return self._redis

    async def initialize(self) -> None:
        if self._initialized:
            return

        sentinel_kwargs: dict[str, Any] = {}
        if self._sentinel_password:
            sentinel_kwargs["password"] = self._sentinel_password

        self._sentinel = Sentinel(
            self._sentinels,
            sentinel_kwargs=sentinel_kwargs or None,
            socket_timeout=self._socket_timeout,
        )
        self._redis = self._sentinel.master_for(
            service_name=self._master_name,
            password=self._redis_password,
            db=self._db,
            decode_responses=self._decode_responses,
            socket_timeout=self._socket_timeout,
            socket_connect_timeout=self._socket_timeout,
            health_check_interval=30,
            max_connections=self._max_connections,
        )
        await self._redis.ping()
        self._initialized = True
        logger.info(
            f"Redis sentinel client [{self.name}] initialized: "
            f"master={self._master_name} db={self._db} "
            f"sentinels={','.join(f'{host}:{port}' for host, port in self._sentinels)}"
        )

    async def cleanup(self) -> None:
        if self._redis is not None:
            close = getattr(self._redis, "aclose", None) or getattr(self._redis, "close", None)
            if close is not None:
                with suppress(Exception):
                    result = close()
                    if asyncio.iscoroutine(result):
                        await result
        self._redis = None
        self._sentinel = None
        self._initialized = False


class PrefixedCache(ICache):
    """为共享 Redis 提供命名空间隔离的缓存包装器。"""

    def __init__(
        self,
        backend: ICache,
        *,
        prefix: str,
        close_callback: Any | None = None,
    ) -> None:
        self._backend = backend
        self._prefix = normalize_prefix(prefix)
        self._close_callback = close_callback

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}" if self._prefix else key

    def _pattern(self, pattern: str) -> str:
        return f"{self._prefix}{pattern}" if self._prefix else pattern

    async def get(self, key: str, default: Any = None) -> Any:
        return await self._backend.get(self._key(key), default)

    async def set(
        self,
        key: str,
        value: Any,
        expire: int | timedelta | None = None,
    ) -> bool:
        return await self._backend.set(self._key(key), value, expire)

    async def delete(self, *keys: str) -> int:
        return await self._backend.delete(*(self._key(key) for key in keys))

    async def exists(self, *keys: str) -> int:
        return await self._backend.exists(*(self._key(key) for key in keys))

    async def clear(self) -> None:
        if self._prefix:
            await self._backend.delete_pattern(f"{self._prefix}*")
            return
        await self._backend.clear()

    async def delete_pattern(self, pattern: str) -> int:
        return await self._backend.delete_pattern(self._pattern(pattern))

    async def close(self) -> None:
        try:
            await self._backend.close()
        finally:
            if self._close_callback is not None:
                result = self._close_callback()
                if asyncio.iscoroutine(result):
                    await result

    async def acquire_lock(
        self,
        key: str,
        token: str,
        timeout: int,
        blocking: bool,
        blocking_timeout: float | None,
    ) -> bool:
        return await self._backend.acquire_lock(
            self._key(key),
            token,
            timeout,
            blocking,
            blocking_timeout,
        )

    async def release_lock(self, key: str, token: str) -> bool:
        return await self._backend.release_lock(self._key(key), token)


class SentinelRedisChannel(IChannel):
    """基于 Sentinel 主节点的 Redis Pub/Sub 通道。"""

    def __init__(self, redis_client: SentinelRedisClientAdapter) -> None:
        self._client = redis_client
        self._redis: Redis | None = None
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None
        self._connected = False
        self._subscribers: dict[str, WeakSet[asyncio.Queue]] = defaultdict(WeakSet)
        self._pattern_subscribers: dict[str, WeakSet[asyncio.Queue]] = defaultdict(WeakSet)
        self._subscription_lock = asyncio.Lock()
        self._subscribed_channels: set[str] = set()
        self._subscribed_patterns: set[str] = set()
        self._stats = ChannelStatsTracker()

    async def _ensure_connected(self) -> None:
        if self._connected:
            return
        await self._client.initialize()
        self._redis = self._client.connection
        self._pubsub = self._redis.pubsub()
        self._connected = True

    async def _start_listener(self) -> None:
        if self._listener_task is not None and not self._listener_task.done():
            return
        self._listener_task = asyncio.create_task(
            self._pubsub_listener(),
            name="sentinel-redis-pubsub-listener",
        )

    async def _pubsub_listener(self) -> None:
        if self._pubsub is None:
            return
        try:
            while self._connected:
                try:
                    message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message is None:
                        continue
                    await self._dispatch_message(message)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    if self._connected:
                        logger.warning(f"Sentinel Redis pubsub listener error: {exc}")
                        await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def _dispatch_message(self, message: dict[str, Any]) -> None:
        msg_type = message.get("type")
        channel = message.get("channel")
        pattern = message.get("pattern")
        data = message.get("data")

        if msg_type == "message" and channel:
            channel_name = channel if isinstance(channel, str) else channel.decode()
            queues = self._subscribers.get(channel_name, set())
            await self._broadcast_to_queues(queues, data, channel_name)
        elif msg_type == "pmessage" and pattern and channel:
            pattern_name = pattern if isinstance(pattern, str) else pattern.decode()
            channel_name = channel if isinstance(channel, str) else channel.decode()
            queues = self._pattern_subscribers.get(pattern_name, set())
            await self._broadcast_to_queues(queues, data, channel_name)

    async def _broadcast_to_queues(self, queues: WeakSet[asyncio.Queue], data: Any, channel: str) -> None:
        if not queues:
            return

        try:
            if isinstance(data, bytes):
                data = data.decode()
            parsed = json.loads(data)
            message = ChannelMessage(
                data=parsed.get("data"),
                event=parsed.get("event"),
                id=parsed.get("id"),
                channel=parsed.get("channel") or channel,
                timestamp=datetime.fromisoformat(parsed["timestamp"])
                if parsed.get("timestamp")
                else datetime.now(),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(f"Failed to decode Redis pubsub message: {exc}")
            return

        dead_queues: list[asyncio.Queue] = []
        for queue in list(queues):
            try:
                queue.put_nowait(message)
                self._stats.record_delivered(message.delivery_latency_ms())
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full, dropping message: {channel}")
                self._stats.record_dropped()
            except Exception:
                dead_queues.append(queue)

        for queue in dead_queues:
            queues.discard(queue)

    async def publish(self, channel: str, message: ChannelMessage) -> None:
        await self._ensure_connected()
        if self._redis is None:
            raise RuntimeError("Redis channel not initialized")

        payload = {
            "data": message.data,
            "event": message.event,
            "id": message.id,
            "channel": channel,
            "timestamp": message.timestamp.isoformat(),
        }
        await self._redis.publish(channel, json.dumps(payload))
        self._stats.record_published()

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        await self._ensure_connected()
        if self._pubsub is None:
            raise RuntimeError("Redis pubsub not initialized")

        queue: asyncio.Queue[ChannelMessage] = asyncio.Queue(maxsize=1000)
        self._subscribers[channel].add(queue)

        async with self._subscription_lock:
            if channel not in self._subscribed_channels:
                await self._pubsub.subscribe(channel)
                self._subscribed_channels.add(channel)

        await self._start_listener()

        try:
            while True:
                try:
                    yield await queue.get()
                except asyncio.CancelledError:
                    break
        finally:
            self._subscribers[channel].discard(queue)
            async with self._subscription_lock:
                if not self._subscribers[channel] and channel in self._subscribed_channels:
                    with suppress(Exception):
                        await self._pubsub.unsubscribe(channel)
                    self._subscribed_channels.discard(channel)

    async def psubscribe(self, pattern: str) -> AsyncIterator[ChannelMessage]:
        await self._ensure_connected()
        if self._pubsub is None:
            raise RuntimeError("Redis pubsub not initialized")

        queue: asyncio.Queue[ChannelMessage] = asyncio.Queue(maxsize=1000)
        self._pattern_subscribers[pattern].add(queue)

        async with self._subscription_lock:
            if pattern not in self._subscribed_patterns:
                await self._pubsub.psubscribe(pattern)
                self._subscribed_patterns.add(pattern)

        await self._start_listener()

        try:
            while True:
                try:
                    yield await queue.get()
                except asyncio.CancelledError:
                    break
        finally:
            self._pattern_subscribers[pattern].discard(queue)
            async with self._subscription_lock:
                if not self._pattern_subscribers[pattern] and pattern in self._subscribed_patterns:
                    with suppress(Exception):
                        await self._pubsub.punsubscribe(pattern)
                    self._subscribed_patterns.discard(pattern)

    async def unsubscribe(self, channel: str) -> None:
        async with self._subscription_lock:
            if self._pubsub and channel in self._subscribed_channels:
                with suppress(Exception):
                    await self._pubsub.unsubscribe(channel)
                self._subscribed_channels.discard(channel)
                self._subscribers.pop(channel, None)

    async def close(self) -> None:
        self._connected = False

        if self._listener_task is not None:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None

        if self._pubsub is not None:
            close = getattr(self._pubsub, "aclose", None) or getattr(self._pubsub, "close", None)
            if close is not None:
                with suppress(Exception):
                    result = close()
                    if asyncio.iscoroutine(result):
                        await result

        self._pubsub = None
        self._redis = None
        await self._client.cleanup()

    def get_stats(self) -> dict[str, Any]:
        stats = self._stats.snapshot()
        stats.update(
            {
                "backend": "redis-sentinel",
                "connected": self._connected,
                "subscribed_channels": len(self._subscribed_channels),
                "subscribed_patterns": len(self._subscribed_patterns),
            }
        )
        return stats


class PrefixedChannel(IChannel):
    """为共享 Pub/Sub 资源提供命名空间隔离。"""

    def __init__(self, backend: IChannel, *, prefix: str) -> None:
        self._backend = backend
        self._prefix = normalize_prefix(prefix)

    def _channel(self, value: str) -> str:
        return f"{self._prefix}{value}" if self._prefix else value

    def _strip(self, message: ChannelMessage) -> ChannelMessage:
        if self._prefix and message.channel and message.channel.startswith(self._prefix):
            return replace(message, channel=message.channel[len(self._prefix):])
        return message

    async def publish(self, channel: str, message: ChannelMessage) -> None:
        await self._backend.publish(self._channel(channel), message)

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        async for message in self._backend.subscribe(self._channel(channel)):
            yield self._strip(message)

    async def psubscribe(self, pattern: str) -> AsyncIterator[ChannelMessage]:
        async for message in self._backend.psubscribe(self._channel(pattern)):
            yield self._strip(message)

    async def unsubscribe(self, channel: str) -> None:
        await self._backend.unsubscribe(self._channel(channel))

    async def close(self) -> None:
        await self._backend.close()

    def get_stats(self) -> dict[str, Any]:
        stats = self._backend.get_stats()
        stats["prefix"] = self._prefix
        return stats


__all__ = [
    "PrefixedCache",
    "PrefixedChannel",
    "SentinelRedisChannel",
    "SentinelRedisClientAdapter",
    "instance_prefix",
    "normalize_prefix",
    "parse_sentinel_nodes",
]

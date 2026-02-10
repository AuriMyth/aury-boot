"""原生 Redis Pub/Sub 后端。

解决 broadcaster 库的并发读取问题：
- 使用单个 pubsub 连接 + 单个 listener 任务
- 内部使用 asyncio.Queue 分发消息到各订阅者
- 避免多协程同时读取同一连接

实现参考：HikariCP 的连接池设计思路 - 单点监听，多路分发。
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse
from weakref import WeakSet

import redis.asyncio as aioredis

from aury.boot.common.logging import logger

from ..base import ChannelMessage, IChannel


class RedisChannel(IChannel):
    """原生 Redis Pub/Sub 通道实现。

    架构：
    1. 单个 pubsub 连接 + 单个 listener 任务（避免并发读取冲突）
    2. 每个 channel 维护一组 subscriber queues
    3. listener 收到消息后，分发到对应 channel 的所有 queues

    优势：
    - 解决 broadcaster 的 readuntil() 并发问题
    - 支持成千上万并发订阅者
    - 按需订阅，避免无用消息传输
    """

    def __init__(self, url: str) -> None:
        """初始化 Redis 通道。

        Args:
            url: Redis 连接 URL，支持格式：
                - redis://host:port/db
                - redis://:password@host:port/db
                - redis://host:port/db?decode_responses=true
        """
        self._url = url
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None
        self._connected = False

        # channel -> set of subscriber queues
        self._subscribers: dict[str, WeakSet[asyncio.Queue]] = defaultdict(WeakSet)
        # pattern -> set of subscriber queues (for psubscribe)
        self._pattern_subscribers: dict[str, WeakSet[asyncio.Queue]] = defaultdict(WeakSet)

        # 保护订阅/取消订阅操作的锁
        self._subscription_lock = asyncio.Lock()
        # 跟踪已订阅的 channels/patterns
        self._subscribed_channels: set[str] = set()
        self._subscribed_patterns: set[str] = set()

    async def _ensure_connected(self) -> None:
        """确保已连接并启动 listener。"""
        if self._connected:
            return

        # 解析 URL
        parsed = urlparse(self._url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        db = int(parsed.path.lstrip("/") or 0) if parsed.path else 0
        password = parsed.password

        # 解析查询参数
        query_params = parse_qs(parsed.query)
        decode_responses = query_params.get("decode_responses", ["true"])[0].lower() == "true"

        # 创建连接
        self._redis = aioredis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
        )

        # 创建 pubsub（只用于订阅，不用于发布）
        self._pubsub = self._redis.pubsub()

        self._connected = True
        logger.debug(f"Redis 通道已连接: {self._mask_url(self._url)}")

    def _mask_url(self, url: str) -> str:
        """URL 脱敏（隐藏密码）。"""
        if "@" in url:
            parts = url.split("@")
            prefix = parts[0]
            suffix = parts[1]
            if ":" in prefix:
                scheme_and_user = prefix.rsplit(":", 1)[0]
                return f"{scheme_and_user}:***@{suffix}"
        return url

    async def _start_listener(self) -> None:
        """启动 pubsub listener 任务（如果尚未启动）。"""
        if self._listener_task is not None and not self._listener_task.done():
            return

        self._listener_task = asyncio.create_task(
            self._pubsub_listener(), name="redis-pubsub-listener"
        )

    async def _pubsub_listener(self) -> None:
        """Pubsub 消息监听循环。

        单点监听，收到消息后分发到对应 channel 的所有 subscriber queues。
        """
        if self._pubsub is None:
            return

        try:
            while self._connected:
                try:
                    # 使用 get_message 而非 listen()，避免长时间阻塞
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message is None:
                        continue

                    await self._dispatch_message(message)

                except asyncio.CancelledError:
                    logger.debug("Redis pubsub listener 被取消")
                    raise
                except Exception as e:
                    if self._connected:
                        logger.warning(f"Redis pubsub listener 错误: {e}")
                        await asyncio.sleep(1)  # 错误后稍等再重试
        except asyncio.CancelledError:
            pass
        finally:
            logger.debug("Redis pubsub listener 已退出")

    async def _dispatch_message(self, message: dict[str, Any]) -> None:
        """分发消息到对应的 subscriber queues。"""
        msg_type = message.get("type")
        channel = message.get("channel")
        pattern = message.get("pattern")
        data = message.get("data")

        if msg_type == "message" and channel:
            # 普通订阅消息
            channel_name = channel if isinstance(channel, str) else channel.decode()
            queues = self._subscribers.get(channel_name, set())
            await self._broadcast_to_queues(queues, data, channel_name)

        elif msg_type == "pmessage" and pattern and channel:
            # 模式订阅消息
            pattern_name = pattern if isinstance(pattern, str) else pattern.decode()
            channel_name = channel if isinstance(channel, str) else channel.decode()
            queues = self._pattern_subscribers.get(pattern_name, set())
            await self._broadcast_to_queues(queues, data, channel_name)

    async def _broadcast_to_queues(
        self, queues: WeakSet[asyncio.Queue], data: Any, channel: str
    ) -> None:
        """广播消息到所有 subscriber queues。"""
        if not queues:
            return

        try:
            # 解析消息
            if isinstance(data, bytes):
                data = data.decode()
            parsed = json.loads(data)
            msg = ChannelMessage(
                data=parsed.get("data"),
                event=parsed.get("event"),
                id=parsed.get("id"),
                channel=parsed.get("channel") or channel,
                timestamp=datetime.fromisoformat(parsed["timestamp"])
                if parsed.get("timestamp")
                else datetime.now(),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"解析 Redis 消息失败: {e}")
            return

        # 分发到所有 queues（非阻塞）
        dead_queues = []
        for queue in list(queues):
            try:
                queue.put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning(f"订阅者队列已满，丢弃消息: channel={channel}")
            except Exception:
                dead_queues.append(queue)

        # 清理已失效的 queues
        for q in dead_queues:
            queues.discard(q)

    async def publish(self, channel: str, message: ChannelMessage) -> None:
        """发布消息到通道。"""
        await self._ensure_connected()
        if self._redis is None:
            raise RuntimeError("Redis 未连接")

        message.channel = channel
        data = {
            "data": message.data,
            "event": message.event,
            "id": message.id,
            "channel": message.channel,
            "timestamp": message.timestamp.isoformat(),
        }
        await self._redis.publish(channel, json.dumps(data))

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        """订阅通道。

        每个调用者获得独立的 queue，共享底层 pubsub 连接。
        """
        await self._ensure_connected()
        if self._pubsub is None:
            raise RuntimeError("Redis pubsub 未初始化")

        # 创建 subscriber queue
        queue: asyncio.Queue[ChannelMessage] = asyncio.Queue(maxsize=1000)
        self._subscribers[channel].add(queue)

        # 确保 channel 已订阅
        async with self._subscription_lock:
            if channel not in self._subscribed_channels:
                await self._pubsub.subscribe(channel)
                self._subscribed_channels.add(channel)
                logger.debug(f"Redis 已订阅 channel: {channel}")

        # 确保 listener 在运行
        await self._start_listener()

        try:
            while True:
                try:
                    msg = await queue.get()
                    yield msg
                except asyncio.CancelledError:
                    break
        finally:
            # 清理
            self._subscribers[channel].discard(queue)

            # 如果没有订阅者了，取消订阅
            async with self._subscription_lock:
                if not self._subscribers[channel] and channel in self._subscribed_channels:
                    with suppress(Exception):
                        await self._pubsub.unsubscribe(channel)
                    self._subscribed_channels.discard(channel)
                    logger.debug(f"Redis 已取消订阅 channel: {channel}")

    async def psubscribe(self, pattern: str) -> AsyncIterator[ChannelMessage]:
        """模式订阅（通配符）。"""
        await self._ensure_connected()
        if self._pubsub is None:
            raise RuntimeError("Redis pubsub 未初始化")

        # 创建 subscriber queue
        queue: asyncio.Queue[ChannelMessage] = asyncio.Queue(maxsize=1000)
        self._pattern_subscribers[pattern].add(queue)

        # 确保 pattern 已订阅
        async with self._subscription_lock:
            if pattern not in self._subscribed_patterns:
                await self._pubsub.psubscribe(pattern)
                self._subscribed_patterns.add(pattern)
                logger.debug(f"Redis 已订阅 pattern: {pattern}")

        # 确保 listener 在运行
        await self._start_listener()

        try:
            while True:
                try:
                    msg = await queue.get()
                    yield msg
                except asyncio.CancelledError:
                    break
        finally:
            # 清理
            self._pattern_subscribers[pattern].discard(queue)

            # 如果没有订阅者了，取消订阅
            async with self._subscription_lock:
                if not self._pattern_subscribers[pattern] and pattern in self._subscribed_patterns:
                    with suppress(Exception):
                        await self._pubsub.punsubscribe(pattern)
                    self._subscribed_patterns.discard(pattern)
                    logger.debug(f"Redis 已取消订阅 pattern: {pattern}")

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅通道。

        注意：通常不需要手动调用，subscribe() 的 async for 退出时会自动清理。
        """
        async with self._subscription_lock:
            if self._pubsub and channel in self._subscribed_channels:
                with suppress(Exception):
                    await self._pubsub.unsubscribe(channel)
                self._subscribed_channels.discard(channel)
                self._subscribers.pop(channel, None)
                logger.debug(f"Redis 已取消订阅 channel: {channel}")

    async def close(self) -> None:
        """关闭通道。"""
        self._connected = False

        # 取消 listener 任务
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None

        # 关闭 pubsub
        if self._pubsub:
            with suppress(Exception):
                await self._pubsub.close()
            self._pubsub = None

        # 关闭 redis 连接
        if self._redis:
            with suppress(Exception):
                await self._redis.close()
            self._redis = None

        self._subscribed_channels.clear()
        self._subscribed_patterns.clear()
        self._subscribers.clear()
        self._pattern_subscribers.clear()

        logger.debug("Redis 通道已关闭")


__all__ = ["RedisChannel"]

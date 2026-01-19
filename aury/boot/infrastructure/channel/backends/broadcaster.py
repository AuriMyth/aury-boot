"""Broadcaster 通道后端。

基于 Broadcaster 库实现，支持多种后端：
- memory:// - 内存（单进程，开发/测试用）
- redis:// - Redis Pub/Sub（多进程/分布式）
- kafka:// - Apache Kafka
- postgres:// - PostgreSQL LISTEN/NOTIFY

优势：
- 共享连接池，支持成千上万并发订阅
- 自动重连机制
- 统一 API，通过 URL scheme 切换后端
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime

from broadcaster import Broadcast

from aury.boot.common.logging import logger

from ..base import ChannelMessage, IChannel


class BroadcasterChannel(IChannel):
    """Broadcaster 通道实现。

    使用 Broadcaster 库统一处理多种后端，解决原生实现的连接池问题：
    - 共享单个连接处理所有订阅
    - 内部通过 asyncio.Queue 分发消息
    - 支持成千上万并发订阅者
    """

    def __init__(self, url: str) -> None:
        """初始化 Broadcaster 通道。

        Args:
            url: 连接 URL，支持的 scheme：
                - memory:// - 内存后端
                - redis://host:port/db - Redis Pub/Sub
                - kafka://host:port - Apache Kafka
                - postgres://user:pass@host:port/db - PostgreSQL
        """
        self._url = url
        self._broadcast = Broadcast(url)
        self._connected = False

    async def _ensure_connected(self) -> None:
        """确保已连接。"""
        if not self._connected:
            await self._broadcast.connect()
            self._connected = True
            logger.debug(f"Broadcaster 通道已连接: {self._mask_url(self._url)}")

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

    async def publish(self, channel: str, message: ChannelMessage) -> None:
        """发布消息到通道。"""
        await self._ensure_connected()

        message.channel = channel
        # 序列化消息
        data = {
            "data": message.data,
            "event": message.event,
            "id": message.id,
            "channel": message.channel,
            "timestamp": message.timestamp.isoformat(),
        }
        await self._broadcast.publish(channel=channel, message=json.dumps(data))

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        """订阅通道。

        Broadcaster 内部共享连接，每个订阅者不会创建新的连接。
        """
        await self._ensure_connected()

        async with self._broadcast.subscribe(channel=channel) as subscriber:
            async for event in subscriber:
                try:
                    data = json.loads(event.message)
                    message = ChannelMessage(
                        data=data.get("data"),
                        event=data.get("event"),
                        id=data.get("id"),
                        channel=data.get("channel") or channel,
                        timestamp=datetime.fromisoformat(data["timestamp"])
                        if data.get("timestamp")
                        else datetime.now(),
                    )
                    yield message
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"解析通道消息失败: {e}")

    async def psubscribe(self, pattern: str) -> AsyncIterator[ChannelMessage]:
        """模式订阅（通配符）。

        注意：Broadcaster 目前不支持模式订阅，此方法会抛出 NotImplementedError。
        如需模式订阅，请使用具体的 channel 名称。

        Args:
            pattern: 通道模式

        Raises:
            NotImplementedError: Broadcaster 不支持模式订阅
        """
        raise NotImplementedError(
            "Broadcaster 后端不支持模式订阅 (psubscribe)。"
            "请使用具体的 channel 名称。"
        )

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅通道。

        注意：Broadcaster 的订阅通过上下文管理器自动处理，
        退出 subscribe() 的 async for 循环即可取消订阅。
        """
        pass

    async def close(self) -> None:
        """关闭通道。"""
        if self._connected:
            await self._broadcast.disconnect()
            self._connected = False
            logger.debug("Broadcaster 通道已关闭")


__all__ = ["BroadcasterChannel"]

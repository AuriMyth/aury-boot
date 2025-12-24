"""通道管理器 - 命名多实例模式。

提供统一的通道管理接口，支持多后端和多实例。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from aury.boot.common.logging import logger

from .backends.memory import MemoryChannel
from .backends.redis import RedisChannel
from .base import ChannelBackend, ChannelMessage, IChannel

if TYPE_CHECKING:
    from aury.boot.infrastructure.clients.redis import RedisClient


class ChannelManager:
    """通道管理器（命名多实例）。

    提供统一的通道管理接口，支持：
    - 多实例管理（如 sse、notification 各自独立）
    - 多后端支持（memory、redis）
    - 发布/订阅模式

    使用示例:
        # 默认实例
        channel = ChannelManager.get_instance()
        await channel.initialize(backend="memory")

        # 命名实例
        sse_channel = ChannelManager.get_instance("sse")
        notification_channel = ChannelManager.get_instance("notification")

        # 发布消息
        await channel.publish("events", ChannelMessage(data="hello"))

        # 订阅消息
        async for msg in channel.subscribe("events"):
            print(msg.data)
    """

    _instances: dict[str, ChannelManager] = {}

    def __init__(self, name: str = "default") -> None:
        """初始化通道管理器。

        Args:
            name: 实例名称
        """
        self.name = name
        self._backend: IChannel | None = None
        self._backend_type: ChannelBackend | None = None
        self._initialized: bool = False

    @classmethod
    def get_instance(cls, name: str = "default") -> ChannelManager:
        """获取指定名称的实例。

        Args:
            name: 实例名称，默认为 "default"

        Returns:
            ChannelManager: 通道管理器实例
        """
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]

    @classmethod
    def reset_instance(cls, name: str | None = None) -> None:
        """重置实例（仅用于测试）。

        Args:
            name: 要重置的实例名称。如果为 None，则重置所有实例。

        注意：调用此方法前应先调用 cleanup() 释放资源。
        """
        if name is None:
            cls._instances.clear()
        elif name in cls._instances:
            del cls._instances[name]

    async def initialize(
        self,
        backend: ChannelBackend | str = ChannelBackend.MEMORY,
        *,
        redis_client: RedisClient | None = None,
        max_subscribers: int = 1000,
    ) -> ChannelManager:
        """初始化通道（链式调用）。

        Args:
            backend: 后端类型
            redis_client: Redis 客户端（当 backend=redis 时需要）
            max_subscribers: 内存后端的最大订阅者数量

        Returns:
            self: 支持链式调用
        """
        if self._initialized:
            logger.warning(f"通道管理器 [{self.name}] 已初始化，跳过")
            return self

        # 处理字符串类型的 backend
        if isinstance(backend, str):
            backend = ChannelBackend(backend.lower())

        self._backend_type = backend

        if backend == ChannelBackend.MEMORY:
            self._backend = MemoryChannel(max_subscribers=max_subscribers)
        elif backend == ChannelBackend.REDIS:
            if redis_client is None:
                raise ValueError("Redis 通道需要提供 redis_client 参数")
            self._backend = RedisChannel(redis_client)
        else:
            raise ValueError(f"不支持的通道后端: {backend}")

        self._initialized = True
        logger.info(f"通道管理器 [{self.name}] 初始化完成: {backend.value}")
        return self

    @property
    def backend(self) -> IChannel:
        """获取通道后端。"""
        if self._backend is None:
            raise RuntimeError(
                f"通道管理器 [{self.name}] 未初始化，请先调用 initialize()"
            )
        return self._backend

    @property
    def backend_type(self) -> str:
        """获取当前后端类型。"""
        return self._backend_type.value if self._backend_type else "unknown"

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化。"""
        return self._initialized

    async def publish(
        self,
        channel: str,
        message: ChannelMessage | str | dict,
        *,
        event: str | None = None,
    ) -> None:
        """发布消息到通道。

        Args:
            channel: 通道名称
            message: 消息内容（ChannelMessage、字符串或字典）
            event: 事件类型（当 message 不是 ChannelMessage 时使用）
        """
        if isinstance(message, ChannelMessage):
            msg = message
        elif isinstance(message, dict):
            msg = ChannelMessage(data=message, event=event)
        else:
            msg = ChannelMessage(data=str(message), event=event)

        await self.backend.publish(channel, msg)

    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        """订阅通道。

        Args:
            channel: 通道名称

        Yields:
            ChannelMessage: 接收到的消息
        """
        async for message in self.backend.subscribe(channel):
            yield message

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅通道。

        Args:
            channel: 通道名称
        """
        await self.backend.unsubscribe(channel)

    async def cleanup(self) -> None:
        """清理资源，关闭通道。"""
        if self._backend:
            await self._backend.close()
            self._backend = None
            self._initialized = False
            logger.info(f"通道管理器 [{self.name}] 已关闭")

    def __repr__(self) -> str:
        """字符串表示。"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<ChannelManager name={self.name} backend={self.backend_type} status={status}>"


__all__ = ["ChannelManager"]

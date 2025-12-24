"""消息队列管理器 - 命名多实例模式。

提供统一的消息队列管理接口，支持多后端和多实例。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

from .backends.rabbitmq import RabbitMQ
from .backends.redis import RedisMQ
from .base import IMQ, MQBackend, MQMessage

if TYPE_CHECKING:
    from aury.boot.application.config import MQInstanceConfig
    from aury.boot.infrastructure.clients.redis import RedisClient


class MQManager:
    """消息队列管理器（命名多实例）。

    提供统一的消息队列管理接口，支持：
    - 多实例管理（如 tasks、notifications 各自独立）
    - 多后端支持（redis、rabbitmq）
    - 生产者/消费者模式

    使用示例:
        # 默认实例
        mq = MQManager.get_instance()
        await mq.initialize(backend="redis", redis_client=redis_client)

        # 命名实例
        task_mq = MQManager.get_instance("tasks")
        notification_mq = MQManager.get_instance("notifications")

        # 发送消息
        await mq.send("orders", MQMessage(body={"order_id": 123}))

        # 消费消息
        await mq.consume("orders", handler=process_order)
    """

    _instances: dict[str, MQManager] = {}

    def __init__(self, name: str = "default") -> None:
        """初始化消息队列管理器。

        Args:
            name: 实例名称
        """
        self.name = name
        self._backend: IMQ | None = None
        self._backend_type: MQBackend | None = None
        self._initialized: bool = False

    @classmethod
    def get_instance(cls, name: str = "default") -> MQManager:
        """获取指定名称的实例。

        Args:
            name: 实例名称，默认为 "default"

        Returns:
            MQManager: 消息队列管理器实例
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
        backend: MQBackend | str = MQBackend.REDIS,
        *,
        config: MQInstanceConfig | None = None,
        redis_client: RedisClient | None = None,
        url: str | None = None,
        prefix: str = "mq:",
    ) -> MQManager:
        """初始化消息队列（链式调用）。

        Args:
            backend: 后端类型（当 config 不为 None 时忽略）
            config: MQ 实例配置（推荐，自动根据 backend 初始化）
            redis_client: Redis 客户端（当 backend=redis 且 config=None 时需要）
            url: 连接 URL（当 config=None 时需要）
            prefix: Redis 队列名称前缀

        Returns:
            self: 支持链式调用
        """
        if self._initialized:
            logger.warning(f"消息队列管理器 [{self.name}] 已初始化，跳过")
            return self

        # 使用配置对象时，从配置中提取参数
        if config is not None:
            backend = config.backend
            url = config.url

        # 处理字符串类型的 backend
        if isinstance(backend, str):
            try:
                backend = MQBackend(backend.lower())
            except ValueError:
                supported = ", ".join(b.value for b in MQBackend)
                raise ValueError(f"不支持的消息队列后端: {backend}。支持: {supported}")

        self._backend_type = backend

        # 根据后端类型创建实例，参数校验由后端自己处理
        if backend == MQBackend.REDIS:
            self._backend = RedisMQ(url=url, redis_client=redis_client, prefix=prefix)
        elif backend == MQBackend.RABBITMQ:
            self._backend = RabbitMQ(url=url)
        else:
            supported = ", ".join(b.value for b in MQBackend)
            raise ValueError(f"不支持的消息队列后端: {backend}。支持: {supported}")

        self._initialized = True
        logger.info(f"消息队列管理器 [{self.name}] 初始化完成: {backend.value}")
        return self

    @property
    def backend(self) -> IMQ:
        """获取消息队列后端。"""
        if self._backend is None:
            raise RuntimeError(
                f"消息队列管理器 [{self.name}] 未初始化，请先调用 initialize()"
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

    async def send(
        self,
        queue: str,
        message: MQMessage | dict | Any,
        *,
        headers: dict[str, Any] | None = None,
    ) -> str:
        """发送消息到队列。

        Args:
            queue: 队列名称
            message: 消息内容（MQMessage、字典或其他可序列化对象）
            headers: 消息头

        Returns:
            str: 消息 ID
        """
        if isinstance(message, MQMessage):
            msg = message
        elif isinstance(message, dict):
            msg = MQMessage(body=message, headers=headers or {})
        else:
            msg = MQMessage(body=message, headers=headers or {})

        return await self.backend.send(queue, msg)

    async def receive(
        self,
        queue: str,
        timeout: float | None = None,
    ) -> MQMessage | None:
        """从队列接收消息。

        Args:
            queue: 队列名称
            timeout: 超时时间（秒）

        Returns:
            MQMessage | None: 消息对象
        """
        return await self.backend.receive(queue, timeout)

    async def ack(self, message: MQMessage) -> None:
        """确认消息已处理。"""
        await self.backend.ack(message)

    async def nack(self, message: MQMessage, requeue: bool = True) -> None:
        """拒绝消息。"""
        await self.backend.nack(message, requeue)

    async def consume(
        self,
        queue: str,
        handler: Callable[[MQMessage], Any],
        *,
        prefetch: int = 1,
    ) -> None:
        """消费队列消息。

        Args:
            queue: 队列名称
            handler: 消息处理函数
            prefetch: 预取数量
        """
        await self.backend.consume(queue, handler, prefetch=prefetch)

    async def cleanup(self) -> None:
        """清理资源，关闭连接。"""
        if self._backend:
            await self._backend.close()
            self._backend = None
            self._initialized = False
            logger.info(f"消息队列管理器 [{self.name}] 已关闭")

    def __repr__(self) -> str:
        """字符串表示。"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<MQManager name={self.name} backend={self.backend_type} status={status}>"


__all__ = ["MQManager"]

"""事件总线管理器 - 命名多实例模式。

提供统一的事件总线管理接口，支持多后端和多实例。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

from .backends.memory import MemoryEventBus
from .backends.rabbitmq import RabbitMQEventBus
from .backends.redis import RedisEventBus
from .base import Event, EventBackend, EventHandler, IEventBus

if TYPE_CHECKING:
    from aury.boot.application.config import EventInstanceConfig
    from aury.boot.infrastructure.clients.redis import RedisClient


class EventBusManager:
    """事件总线管理器（命名多实例）。

    提供统一的事件总线管理接口，支持：
    - 多实例管理（如 local、distributed 各自独立）
    - 多后端支持（memory、redis、rabbitmq）
    - 发布/订阅模式

    使用示例:
        # 默认实例（内存）
        events = EventBusManager.get_instance()
        await events.initialize(backend="memory")

        # 分布式实例
        distributed = EventBusManager.get_instance("distributed")
        await distributed.initialize(
            backend="redis",
            redis_client=redis_client,
        )

        # 订阅事件
        @events.on(MyEvent)
        async def handle_my_event(event: MyEvent):
            print(event)

        # 发布事件
        await events.publish(MyEvent(...))
    """

    _instances: dict[str, EventBusManager] = {}

    def __init__(self, name: str = "default") -> None:
        """初始化事件总线管理器。

        Args:
            name: 实例名称
        """
        self.name = name
        self._backend: IEventBus | None = None
        self._backend_type: EventBackend | None = None
        self._initialized: bool = False

    @classmethod
    def get_instance(cls, name: str = "default") -> EventBusManager:
        """获取指定名称的实例。

        Args:
            name: 实例名称，默认为 "default"

        Returns:
            EventBusManager: 事件总线管理器实例
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
        backend: EventBackend | str = EventBackend.MEMORY,
        *,
        config: EventInstanceConfig | None = None,
        redis_client: RedisClient | None = None,
        url: str | None = None,
        channel_prefix: str = "events:",
        exchange_name: str = "events",
    ) -> EventBusManager:
        """初始化事件总线（链式调用）。

        Args:
            backend: 后端类型（当 config 不为 None 时忽略）
            config: Event 实例配置（推荐，自动根据 backend 初始化）
            redis_client: Redis 客户端（当 backend=redis 且 config=None 时需要）
            url: 连接 URL（当 config=None 时需要）
            channel_prefix: Redis 频道前缀
            exchange_name: RabbitMQ 交换机名称

        Returns:
            self: 支持链式调用
        """
        if self._initialized:
            logger.warning(f"事件总线管理器 [{self.name}] 已初始化，跳过")
            return self

        # 使用配置对象时，从配置中提取参数
        if config is not None:
            backend = config.backend
            url = config.url

        # 处理字符串类型的 backend
        if isinstance(backend, str):
            try:
                backend = EventBackend(backend.lower())
            except ValueError:
                supported = ", ".join(b.value for b in EventBackend)
                raise ValueError(f"不支持的事件总线后端: {backend}。支持: {supported}")

        self._backend_type = backend

        # 根据后端类型创建实例，参数校验由后端自己处理
        if backend == EventBackend.MEMORY:
            self._backend = MemoryEventBus()
        elif backend == EventBackend.REDIS:
            self._backend = RedisEventBus(url=url, redis_client=redis_client, channel_prefix=channel_prefix)
        elif backend == EventBackend.RABBITMQ:
            self._backend = RabbitMQEventBus(url=url, exchange_name=exchange_name)
        else:
            supported = ", ".join(b.value for b in EventBackend)
            raise ValueError(f"不支持的事件总线后端: {backend}。支持: {supported}")

        self._initialized = True
        logger.info(f"事件总线管理器 [{self.name}] 初始化完成: {backend.value}")
        return self

    @property
    def backend(self) -> IEventBus:
        """获取事件总线后端。"""
        if self._backend is None:
            raise RuntimeError(
                f"事件总线管理器 [{self.name}] 未初始化，请先调用 initialize()"
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

    def subscribe(
        self,
        event_type: type[Event] | str,
        handler: EventHandler | None = None,
    ) -> EventHandler | Callable[[EventHandler], EventHandler]:
        """订阅事件（可作为装饰器使用）。

        Args:
            event_type: 事件类型或事件名称
            handler: 事件处理函数（作为装饰器时为 None）

        Returns:
            EventHandler | Callable: 处理器或装饰器
        """

        def decorator(fn: EventHandler) -> EventHandler:
            self.backend.subscribe(event_type, fn)
            return fn

        if handler is not None:
            return decorator(handler)
        return decorator

    # 别名方法
    on = subscribe

    def unsubscribe(
        self,
        event_type: type[Event] | str,
        handler: EventHandler,
    ) -> None:
        """取消订阅事件。"""
        self.backend.unsubscribe(event_type, handler)

    async def publish(self, event: Event) -> None:
        """发布事件。"""
        await self.backend.publish(event)

    # 别名方法
    emit = publish

    async def cleanup(self) -> None:
        """清理资源，关闭事件总线。"""
        if self._backend:
            await self._backend.close()
            self._backend = None
            self._initialized = False
            logger.info(f"事件总线管理器 [{self.name}] 已关闭")

    def __repr__(self) -> str:
        """字符串表示。"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<EventBusManager name={self.name} backend={self.backend_type} status={status}>"


__all__ = ["EventBusManager"]

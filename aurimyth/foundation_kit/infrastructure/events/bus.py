"""事件总线实现。

提供事件发布/订阅机制，支持本地和分布式模式。

**架构说明**：
本模块不依赖具体的 domain.events 实现，而是通过接口和类型变量来保持通用性。
事件总线作为 infrastructure 组件只需要事件对象能够被序列化。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from kombu import Connection, Exchange

from aurimyth.foundation_kit.common.logging import logger

from .config import EventConfig
from .consumer import EventConsumer
from .models import Event, EventHandler, EventType


class EventBus:
    """事件总线（单例模式）。
    
    职责：
    1. 管理事件订阅者
    2. 分发事件（支持本地和分布式模式）
    3. 异步事件处理
    
    模式：
    - 本地模式：内存中的观察者模式（默认，无需消息队列）
    - 分布式模式：使用 Kombu 消息队列（需要配置 broker_url）
    
    使用示例:
        # 本地模式（内存）
        event_bus = EventBus.get_instance()
        
        @event_bus.subscribe(MyEvent)
        async def on_my_event(event: MyEvent):
            print(f"Event {event.event_name} received!")
        
        await event_bus.publish(MyEvent(...))
        
        # 分布式模式（Kombu）
        await event_bus.initialize(broker_url="redis://localhost:6379/0")
        await event_bus.publish(MyEvent(...))  # 通过消息队列发布
    """
    
    _instance: EventBus | None = None
    
    def __init__(self, settings: EventConfig | None = None) -> None:
        """私有构造函数，使用 get_instance() 获取实例。
        
        Args:
            settings: 事件总线配置（如果为 None 则使用默认配置）
        """
        if EventBus._instance is not None:
            raise RuntimeError("EventBus 是单例类，请使用 get_instance() 获取实例")
        
        self._settings = settings or EventConfig()
        self._handlers: dict[type[Event], list[EventHandler]] = {}
        self._event_history: list[Event] = []
        
        # Kombu 相关
        self._connection: Any = None  # Connection | None
        self._exchange: Any = None  # Exchange | None
        self._producer: Any = None  # Producer | None
        self._consumer: Any = None  # EventConsumer | None
        self._consumer_task: Any = None  # asyncio.Task | None
        self._initialized: bool = False
        self._use_distributed: bool = False
        self._broker_url: str | None = None
        
        logger.debug("事件总线已创建（本地模式）")
    
    @classmethod
    def get_instance(cls) -> EventBus:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(
        self,
        broker_url: str | None = None,
        *,
        exchange_name: str | None = None,
        queue_prefix: str | None = None,
    ) -> None:
        """初始化分布式事件总线（使用 Kombu）。
        
        Args:
            broker_url: 消息队列 URL（如 "redis://localhost:6379/0" 或 "amqp://guest:guest@localhost:5672//"）
                        如果不指定则使用配置中的值
            exchange_name: 交换机名称，如果不指定则使用配置中的值
            queue_prefix: 队列名称前缀，如果不指定则使用配置中的值
        """
        if self._initialized:
            logger.warning("事件总线已初始化，跳过")
            return
        
        # 使用提供的参数或配置中的值
        final_broker_url = broker_url or self._settings.broker_url
        final_exchange_name = exchange_name or self._settings.exchange_name
        final_queue_prefix = queue_prefix or self._settings.queue_prefix
        
        if not final_broker_url:
            logger.info("未提供 broker_url，使用本地模式（内存）")
            self._use_distributed = False
            self._initialized = True
            return
        
        try:
            self._broker_url = final_broker_url
            self._connection = Connection(final_broker_url)
            self._exchange = Exchange(final_exchange_name, type="topic", durable=True)
            
            # 创建生产者
            self._producer = self._connection.Producer(
                exchange=self._exchange,
                serializer="json",
            )
            
            # 启动消费者（在后台任务中）
            self._consumer = EventConsumer(
                connection=self._connection,
                exchange=self._exchange,
                queue_prefix=final_queue_prefix,
                handlers=self._handlers,
            )
            
            # 在后台启动消费者
            self._consumer_task = asyncio.create_task(self._start_consumer())
            
            self._use_distributed = True
            self._initialized = True
            logger.info(f"事件总线已初始化（分布式模式，broker: {broker_url}）")
        except Exception as exc:
            logger.error(f"事件总线初始化失败: {exc}")
            raise
    
    async def _start_consumer(self) -> None:
        """启动消费者（在后台运行）。"""
        if self._consumer:
            try:
                # 在事件循环中运行消费者
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._consumer.run)
            except Exception as exc:
                logger.error(f"事件消费者运行失败: {exc}")
    
    def subscribe(
        self,
        event_type: type[EventType],
        handler: EventHandler | None = None,
    ) -> EventHandler | Callable[[EventHandler], EventHandler]:
        """订阅事件。
        
        可以作为装饰器使用：
            @event_bus.subscribe(MyEvent)
            async def handler(event):
                pass
        
        或直接调用：
            event_bus.subscribe(MyEvent, handler)
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
            
        Returns:
            EventHandler | Callable: 处理器或装饰器
        """
        def decorator(fn: EventHandler) -> EventHandler:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            
            self._handlers[event_type].append(fn)
            logger.debug(f"订阅事件: {event_type.__name__} -> {fn.__name__}")
            
            # 如果使用分布式模式，需要注册队列
            if self._use_distributed and self._consumer:
                self._consumer.register_event_type(event_type)
            
            return fn
        
        if handler is not None:
            return decorator(handler)
        return decorator
    
    def unsubscribe(self, event_type: type[EventType], handler: EventHandler) -> None:
        """取消订阅事件。
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"取消订阅事件: {event_type.__name__} -> {handler.__name__}")
            except ValueError:
                pass
    
    async def publish(self, event: EventType) -> None:
        """发布事件。
        
        Args:
            event: 事件对象
        """
        logger.info(f"发布事件: {event}")
        
        # 记录事件历史
        self._add_to_history(event)
        
        if self._use_distributed:
            # 分布式模式：通过消息队列发布
            await self._publish_distributed(event)
        else:
            # 本地模式：直接调用处理器
            await self._publish_local(event)
    
    async def _publish_local(self, event: EventType) -> None:
        """本地模式：直接调用处理器。"""
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            logger.debug(f"事件 {event.event_name} 没有订阅者")
            return
        
        # 执行处理器
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                logger.debug(f"事件处理成功: {handler.__name__}")
            except Exception as exc:
                logger.error(f"事件处理失败: {handler.__name__}, 错误: {exc}")
    
    async def _publish_distributed(self, event: EventType) -> None:
        """分布式模式：通过消息队列发布。"""
        if not self._producer:
            logger.warning("生产者未初始化，回退到本地模式")
            await self._publish_local(event)
            return
        
        try:
            # 序列化事件（使用 model_dump 而不是 model_dump_json，因为 kombu 会自动序列化）
            event_data = event.model_dump()
            routing_key = event.event_name.lower().replace("event", "")
            
            # 发布到消息队列
            self._producer.publish(
                event_data,
                routing_key=routing_key,
                declare=[self._exchange],
            )
            logger.debug(f"事件已发布到消息队列: {routing_key}")
        except Exception as exc:
            logger.error(f"发布事件到消息队列失败: {exc}")
            # 失败时回退到本地模式
            await self._publish_local(event)
    
    async def publish_many(self, events: list[Event]) -> None:
        """批量发布事件。
        
        Args:
            events: 事件列表
        """
        for event in events:
            await self.publish(event)
    
    def _add_to_history(self, event: Event) -> None:
        """添加事件到历史记录。
        
        Args:
            event: 事件对象
        """
        # 检查是否启用了历史记录
        if not self._settings.enable_history:
            return
        
        self._event_history.append(event)
        
        # 限制历史记录大小
        if (
            self._settings.max_history_size is not None
            and len(self._event_history) > self._settings.max_history_size
        ):
            self._event_history = self._event_history[-self._settings.max_history_size:]
    
    def get_history(
        self,
        event_type: type[EventType] | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """获取事件历史。
        
        Args:
            event_type: 事件类型（可选，不指定则返回所有事件）
            limit: 返回数量限制
            
        Returns:
            list[Event]: 事件列表
        """
        if event_type is None:
            return self._event_history[-limit:]
        
        filtered = [e for e in self._event_history if isinstance(e, event_type)]
        return filtered[-limit:]
    
    def clear_history(self) -> None:
        """清空事件历史。"""
        self._event_history.clear()
        logger.debug("事件历史已清空")
    
    def clear_handlers(self) -> None:
        """清空所有事件处理器。"""
        self._handlers.clear()
        logger.debug("事件处理器已清空")
    
    def get_handler_count(self, event_type: type[EventType] | None = None) -> int:
        """获取处理器数量。
        
        Args:
            event_type: 事件类型（可选）
            
        Returns:
            int: 处理器数量
        """
        if event_type is None:
            return sum(len(handlers) for handlers in self._handlers.values())
        return len(self._handlers.get(event_type, []))
    
    async def cleanup(self) -> None:
        """清理资源。"""
        if self._consumer:
            self._consumer.should_stop = True
        
        if self._connection:
            self._connection.close()
        
        self._initialized = False
        self._use_distributed = False
        logger.info("事件总线已清理")
    
    def __repr__(self) -> str:
        """字符串表示。"""
        event_count = len(self._handlers)
        history_size = len(self._event_history)
        mode = "distributed" if self._use_distributed else "local"
        return f"<EventBus mode={mode} events={event_count} history={history_size}>"


__all__ = [
    "EventBus",
]


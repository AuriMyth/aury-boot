"""事件消费者实现。

基于 Kombu ConsumerMixin 实现消息队列事件消费。

**架构说明**：
本模块使用通用的 Any 类型而非直接导入 domain.events，保持 infrastructure 层的独立性。
"""

from __future__ import annotations

import asyncio
from typing import Any

from kombu import Queue
from kombu.mixins import ConsumerMixin

from aurimyth.foundation_kit.common.logging import logger


class EventConsumer(ConsumerMixin):
    """事件消费者（基于 Kombu ConsumerMixin）。
    
    在后台消费消息队列中的事件并调用本地处理器。
    """
    
    def __init__(
        self,
        connection: Any,  # Connection
        exchange: Any,  # Exchange
        queue_prefix: str,
        handlers: dict[Any, list[Any]],  # dict[type[EventType], list[EventHandler]]
    ) -> None:
        """初始化事件消费者。
        
        Args:
            connection: Kombu 连接
            exchange: 交换机
            queue_prefix: 队列名称前缀
            handlers: 事件处理器字典 {事件类型: [处理器列表]}
        """
        self.connection = connection
        self._exchange = exchange
        self._queue_prefix = queue_prefix
        self._handlers = handlers
        self._queues: dict[str, Any] = {}  # dict[str, Queue]
        self._event_types: dict[str, Any] = {}  # dict[str, type[EventType]]
    
    def register_event_type(self, event_type: Any) -> None:
        """注册事件类型（创建对应的队列）。
        
        Args:
            event_type: 事件类型（应实现 __name__ 和 model_validate()）
        """
        event_name = event_type.__name__
        routing_key = event_name.lower().replace("event", "")
        
        if routing_key not in self._queues:
            queue_name = f"{self._queue_prefix}.{routing_key}"
            queue = Queue(
                queue_name,
                exchange=self._exchange,
                routing_key=routing_key,
                durable=True,
            )
            self._queues[routing_key] = queue
            self._event_types[routing_key] = event_type
            logger.debug(f"注册事件队列: {queue_name} -> {routing_key}")
    
    def get_consumers(self, consumer_class: type, channel: Any) -> list:
        """获取消费者列表。
        
        Args:
            consumer_class: Kombu Consumer 类
            channel: 消息通道
            
        Returns:
            list: 消费者列表
        """
        consumers = []
        for _routing_key, queue in self._queues.items():
            consumer = consumer_class(
                queues=[queue],
                callbacks=[self.on_message],
                accept=["json"],
            )
            consumers.append(consumer)
        return consumers
    
    def on_message(self, body: dict[str, Any], message: Any) -> None:
        """处理接收到的消息。
        
        Args:
            body: 消息体
            message: 消息对象
        """
        try:
            routing_key = message.delivery_info.get("routing_key", "")
            event_type = self._event_types.get(routing_key)
            
            if not event_type:
                logger.warning(f"未知的事件类型: {routing_key}")
                message.ack()
                return
            
            # 反序列化事件
            event = event_type.model_validate(body)
            
            # 获取处理器
            handlers = self._handlers.get(event_type, [])
            
            # 在事件循环中执行处理器
            loop = asyncio.get_event_loop()
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        task = loop.create_task(handler(event))
                        # 保存任务引用以避免警告
                        _ = task
                    else:
                        handler(event)
                    logger.debug(f"事件处理成功: {handler.__name__}")
                except Exception as exc:
                    logger.error(f"事件处理失败: {handler.__name__}, 错误: {exc}")
            
            message.ack()
        except Exception as exc:
            logger.error(f"处理事件消息失败: {exc}")
            message.reject(requeue=False)


__all__ = [
    "EventConsumer",
]


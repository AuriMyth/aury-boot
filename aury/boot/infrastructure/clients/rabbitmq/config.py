"""RabbitMQ 客户端配置。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RabbitMQConfig(BaseModel):
    """RabbitMQ 连接配置。
    
    Attributes:
        url: AMQP 连接 URL，如 amqp://guest:guest@localhost:5672/
        heartbeat: 心跳间隔（秒）
        connection_timeout: 连接超时（秒）
        blocked_connection_timeout: 阻塞连接超时（秒）
        prefetch_count: 预取消息数量
        publisher_confirms: 是否启用发布确认
    """
    
    url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="AMQP 连接 URL"
    )
    heartbeat: int = Field(
        default=60,
        description="心跳间隔（秒）"
    )
    connection_timeout: float = Field(
        default=10.0,
        description="连接超时（秒）"
    )
    blocked_connection_timeout: float = Field(
        default=300.0,
        description="阻塞连接超时（秒）"
    )
    prefetch_count: int = Field(
        default=10,
        description="预取消息数量（QoS）"
    )
    publisher_confirms: bool = Field(
        default=True,
        description="是否启用发布确认"
    )


__all__ = ["RabbitMQConfig"]

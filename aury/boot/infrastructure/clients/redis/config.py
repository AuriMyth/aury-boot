"""Redis 客户端配置。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RedisConfig(BaseModel):
    """Redis 连接配置。
    
    Attributes:
        url: Redis 连接 URL，如 redis://localhost:6379/0
        max_connections: 最大连接数
        socket_timeout: 套接字超时时间（秒）
        socket_connect_timeout: 连接超时时间（秒）
        retry_on_timeout: 超时是否重试
        health_check_interval: 健康检查间隔（秒）
        decode_responses: 是否自动解码响应
    """
    
    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 连接 URL"
    )
    max_connections: int = Field(
        default=10,
        description="最大连接数"
    )
    socket_timeout: float = Field(
        default=5.0,
        description="套接字超时时间（秒）"
    )
    socket_connect_timeout: float = Field(
        default=5.0,
        description="连接超时时间（秒）"
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="超时是否重试"
    )
    health_check_interval: int = Field(
        default=30,
        description="健康检查间隔（秒）"
    )
    decode_responses: bool = Field(
        default=False,
        description="是否自动解码响应（设为 False 以支持二进制数据）"
    )


__all__ = ["RedisConfig"]

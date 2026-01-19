"""通道基础接口定义。

提供流式通道的抽象接口，用于 SSE、WebSocket 等实时通信场景。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ChannelBackend(Enum):
    """通道后端类型。"""

    # Broadcaster 统一后端（支持 memory/redis/kafka/postgres，通过 URL scheme 区分）
    BROADCASTER = "broadcaster"
    # 未来扩展
    RABBITMQ = "rabbitmq"
    ROCKETMQ = "rocketmq"


@dataclass
class ChannelMessage:
    """通道消息。"""

    data: Any
    event: str | None = None
    id: str | None = None
    channel: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_sse(self) -> str:
        """转换为 SSE 格式。
        
        SSE 规范要求每个消息以双换行符结束。
        """
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        # data 可能是多行
        data_str = str(self.data) if not isinstance(self.data, str) else self.data
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")
        lines.append("")  # 空行结束
        # SSE 规范要求消息以双换行符结束
        return "\n".join(lines) + "\n"


class IChannel(ABC):
    """通道接口。"""

    @abstractmethod
    async def publish(self, channel: str, message: ChannelMessage) -> None:
        """发布消息到通道。

        Args:
            channel: 通道名称
            message: 消息对象
        """
        ...

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncIterator[ChannelMessage]:
        """订阅通道。

        Args:
            channel: 通道名称

        Yields:
            ChannelMessage: 接收到的消息
        """
        ...

    async def psubscribe(self, pattern: str) -> AsyncIterator[ChannelMessage]:
        """模式订阅（通配符）。

        Args:
            pattern: 通道模式，如 "space:123:*" 订阅 space:123 下所有事件

        Yields:
            ChannelMessage: 接收到的消息
        
        注意：内存后端默认回退到普通 subscribe，Redis 后端支持真正的模式匹配。
        """
        # 默认实现：回退到普通订阅（子类可覆盖）
        async for msg in self.subscribe(pattern):
            yield msg

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """取消订阅通道。

        Args:
            channel: 通道名称
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭通道连接。"""
        ...


__all__ = [
    "ChannelBackend",
    "ChannelMessage",
    "IChannel",
]

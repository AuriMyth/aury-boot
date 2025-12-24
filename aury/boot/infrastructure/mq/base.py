"""消息队列基础接口定义。

提供消息队列的抽象接口，用于异步任务处理、服务间通信等场景。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class MQBackend(Enum):
    """消息队列后端类型。"""

    REDIS = "redis"
    RABBITMQ = "rabbitmq"


@dataclass
class MQMessage:
    """消息队列消息。"""

    body: Any
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    queue: str | None = None
    headers: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "body": self.body,
            "queue": self.queue,
            "headers": self.headers,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MQMessage:
        """从字典创建消息。"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            body=data["body"],
            queue=data.get("queue"),
            headers=data.get("headers", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if data.get("timestamp")
            else datetime.now(),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


class IMQ(ABC):
    """消息队列接口。"""

    @abstractmethod
    async def send(self, queue: str, message: MQMessage) -> str:
        """发送消息到队列。

        Args:
            queue: 队列名称
            message: 消息对象

        Returns:
            str: 消息 ID
        """
        ...

    @abstractmethod
    async def receive(
        self,
        queue: str,
        timeout: float | None = None,
    ) -> MQMessage | None:
        """从队列接收消息。

        Args:
            queue: 队列名称
            timeout: 超时时间（秒），None 表示阻塞等待

        Returns:
            MQMessage | None: 消息对象，超时返回 None
        """
        ...

    @abstractmethod
    async def ack(self, message: MQMessage) -> None:
        """确认消息已处理。

        Args:
            message: 消息对象
        """
        ...

    @abstractmethod
    async def nack(self, message: MQMessage, requeue: bool = True) -> None:
        """拒绝消息。

        Args:
            message: 消息对象
            requeue: 是否重新入队
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭连接。"""
        ...


__all__ = [
    "IMQ",
    "MQBackend",
    "MQMessage",
]

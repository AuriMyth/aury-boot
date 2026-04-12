"""通道基础接口定义。

提供流式通道的抽象接口，用于 SSE、WebSocket 等实时通信场景。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
from typing import Any


class ChannelBackend(Enum):
    """通道后端类型。"""

    # Broadcaster 统一后端（支持 memory/redis/redis-cluster/kafka/postgres，通过 URL scheme 区分）
    BROADCASTER = "broadcaster"
    # 原生 Redis 后端（解决 broadcaster 的并发读取问题，推荐用于 Redis）
    REDIS = "redis"
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

    def delivery_latency_ms(self, now: datetime | None = None) -> float:
        """计算从 publish 到当前消费点的端到端延迟。"""
        reference = now or (
            datetime.now(self.timestamp.tzinfo) if self.timestamp.tzinfo else datetime.now()
        )
        return max((reference - self.timestamp).total_seconds() * 1000, 0.0)

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

    def get_stats(self) -> dict[str, Any]:
        """获取通道运行指标。"""
        return {}


class ChannelStatsTracker:
    """轻量级通道统计器。"""

    def __init__(self, max_samples: int = 2048) -> None:
        self._max_samples = max_samples
        self._latency_samples: deque[float] = deque(maxlen=max_samples)
        self._published_count = 0
        self._delivered_count = 0
        self._dropped_count = 0
        self._lock = threading.Lock()

    def record_published(self, count: int = 1) -> None:
        with self._lock:
            self._published_count += count

    def record_delivered(self, latency_ms: float, count: int = 1) -> None:
        sample = round(latency_ms, 3)
        with self._lock:
            self._delivered_count += count
            self._latency_samples.append(sample)

    def record_dropped(self, count: int = 1) -> None:
        with self._lock:
            self._dropped_count += count

    def _percentile(self, values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
        return round(ordered[index], 3)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            samples = list(self._latency_samples)
            published_count = self._published_count
            delivered_count = self._delivered_count
            dropped_count = self._dropped_count

        if not samples:
            latency = {
                "sample_count": 0,
                "min_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "p99_ms": None,
                "max_ms": None,
                "over_20ms": 0,
                "over_50ms": 0,
                "over_100ms": 0,
            }
        else:
            latency = {
                "sample_count": len(samples),
                "min_ms": round(min(samples), 3),
                "p50_ms": self._percentile(samples, 0.50),
                "p95_ms": self._percentile(samples, 0.95),
                "p99_ms": self._percentile(samples, 0.99),
                "max_ms": round(max(samples), 3),
                "over_20ms": sum(1 for item in samples if item >= 20),
                "over_50ms": sum(1 for item in samples if item >= 50),
                "over_100ms": sum(1 for item in samples if item >= 100),
            }

        return {
            "published_count": published_count,
            "delivered_count": delivered_count,
            "dropped_count": dropped_count,
            "delivery_latency_ms": latency,
        }


__all__ = [
    "ChannelBackend",
    "ChannelMessage",
    "ChannelStatsTracker",
    "IChannel",
]

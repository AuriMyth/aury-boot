"""告警事件定义。

定义告警事件类型、严重级别和事件数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import hashlib


class AlertEventType(str, Enum):
    """告警事件类型。"""
    
    SLOW_REQUEST = "slow_request"       # 慢请求
    SLOW_SQL = "slow_sql"               # 慢 SQL
    EXCEPTION = "exception"             # 异常
    TASK_FAILURE = "task_failure"       # 任务失败
    TASK_TIMEOUT = "task_timeout"       # 任务超时
    CUSTOM = "custom"                   # 自定义


class AlertSeverity(str, Enum):
    """告警严重级别。"""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertEvent:
    """告警事件。
    
    包含告警的所有上下文信息。
    """
    
    event_type: AlertEventType
    severity: AlertSeverity
    message: str
    trace_id: str
    
    source: str = "unknown"           # api / scheduler / task
    service_name: str = ""            # 服务名
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # 用于聚合/去重的指纹（相同指纹的事件会被聚合）
    _fingerprint: str | None = field(default=None, repr=False)
    
    @property
    def fingerprint(self) -> str:
        """获取事件指纹。
        
        相同指纹的事件会被聚合处理。
        """
        if self._fingerprint:
            return self._fingerprint
        
        # 默认指纹：类型 + 来源 + 关键元数据
        key_parts = [
            self.event_type.value,
            self.source,
            self.metadata.get("endpoint", ""),
            self.metadata.get("task_name", ""),
            self.metadata.get("error_type", ""),
        ]
        key_str = ":".join(str(p) for p in key_parts if p)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    @fingerprint.setter
    def fingerprint(self, value: str) -> None:
        self._fingerprint = value
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "trace_id": self.trace_id,
            "source": self.source,
            "service_name": self.service_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "fingerprint": self.fingerprint,
        }


@dataclass
class AlertNotification:
    """告警通知（发送给 Notifier 的数据）。
    
    包含聚合后的告警信息。
    """
    
    title: str
    message: str
    severity: AlertSeverity
    event_type: AlertEventType
    source: str
    service_name: str
    
    # 聚合信息
    count: int = 1                    # 聚合的事件数量
    first_timestamp: datetime = field(default_factory=datetime.now)
    last_timestamp: datetime = field(default_factory=datetime.now)
    
    # 关联的 trace_id 列表（最多保留最近几个）
    trace_ids: list[str] = field(default_factory=list)
    
    # 额外元数据
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "event_type": self.event_type.value,
            "source": self.source,
            "service_name": self.service_name,
            "count": self.count,
            "first_timestamp": self.first_timestamp.isoformat(),
            "last_timestamp": self.last_timestamp.isoformat(),
            "trace_ids": self.trace_ids,
            "metadata": self.metadata,
        }


__all__ = [
    "AlertEvent",
    "AlertEventType",
    "AlertNotification",
    "AlertSeverity",
]

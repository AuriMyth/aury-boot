"""告警聚合器。

实现累计触发和抑制逻辑：
- 滑动窗口计数：在窗口时间内达到阈值才触发
- 抑制机制：相同告警在抑制时间内不重复发送
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .events import AlertEvent


@dataclass
class AggregationState:
    """单个指纹的聚合状态。"""
    
    fingerprint: str
    
    # 滑动窗口内的事件时间戳
    event_timestamps: deque[datetime] = field(default_factory=deque)
    
    # 最后一次发送告警的时间
    last_alert_time: datetime | None = None
    
    # 聚合的 trace_id 列表（最多保留 5 个）
    trace_ids: deque[str] = field(default_factory=lambda: deque(maxlen=5))
    
    # 窗口内事件总数（用于通知）
    window_count: int = 0


class AlertAggregator:
    """告警聚合器。
    
    实现两层控制：
    1. 累计触发：窗口时间内达到阈值才触发告警
    2. 抑制机制：触发后的抑制时间内不重复发送
    
    示例：
        aggregator = AlertAggregator(
            window_seconds=60,      # 1 分钟窗口
            threshold=5,            # 5 次触发
            suppress_seconds=300,   # 5 分钟抑制
        )
        
        if aggregator.should_alert(event):
            # 发送告警
            ...
    """
    
    def __init__(
        self,
        window_seconds: int = 60,
        threshold: int = 1,
        suppress_seconds: int = 300,
    ) -> None:
        """初始化聚合器。
        
        Args:
            window_seconds: 滑动窗口大小（秒）
            threshold: 窗口内触发阈值
            suppress_seconds: 告警抑制时间（秒）
        """
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.suppress_seconds = suppress_seconds
        
        self._states: dict[str, AggregationState] = {}
        self._lock = threading.Lock()
    
    def should_alert(self, event: "AlertEvent") -> bool:
        """判断是否应该触发告警。
        
        Args:
            event: 告警事件
        
        Returns:
            bool: 是否应该发送告警
        """
        fingerprint = event.fingerprint
        now = event.timestamp
        
        with self._lock:
            # 获取或创建状态
            if fingerprint not in self._states:
                self._states[fingerprint] = AggregationState(fingerprint=fingerprint)
            
            state = self._states[fingerprint]
            
            # 清理过期的时间戳
            window_start = now - timedelta(seconds=self.window_seconds)
            while state.event_timestamps and state.event_timestamps[0] < window_start:
                state.event_timestamps.popleft()
            
            # 添加当前事件
            state.event_timestamps.append(now)
            state.trace_ids.append(event.trace_id)
            state.window_count = len(state.event_timestamps)
            
            # 检查是否达到阈值
            if state.window_count < self.threshold:
                return False
            
            # 检查是否在抑制期内
            if state.last_alert_time:
                suppress_until = state.last_alert_time + timedelta(seconds=self.suppress_seconds)
                if now < suppress_until:
                    return False
            
            # 触发告警，更新最后告警时间
            state.last_alert_time = now
            return True
    
    def get_state(self, fingerprint: str) -> AggregationState | None:
        """获取指纹的聚合状态。
        
        Args:
            fingerprint: 事件指纹
        
        Returns:
            聚合状态，如果不存在返回 None
        """
        with self._lock:
            return self._states.get(fingerprint)
    
    def get_aggregation_info(self, event: "AlertEvent") -> dict:
        """获取聚合信息（用于告警通知）。
        
        Args:
            event: 告警事件
        
        Returns:
            包含聚合信息的字典
        """
        state = self.get_state(event.fingerprint)
        if not state:
            return {
                "count": 1,
                "trace_ids": [event.trace_id],
            }
        
        return {
            "count": state.window_count,
            "trace_ids": list(state.trace_ids),
        }
    
    def reset(self, fingerprint: str | None = None) -> None:
        """重置聚合状态。
        
        Args:
            fingerprint: 指定指纹，如果为 None 则重置所有
        """
        with self._lock:
            if fingerprint:
                self._states.pop(fingerprint, None)
            else:
                self._states.clear()
    
    def cleanup_expired(self) -> int:
        """清理过期的状态。
        
        返回清理的状态数量。
        """
        now = datetime.now()
        expire_time = now - timedelta(seconds=self.window_seconds + self.suppress_seconds)
        
        cleaned = 0
        with self._lock:
            to_remove = []
            for fp, state in self._states.items():
                # 如果窗口为空且已过抑制期，可以清理
                if not state.event_timestamps:
                    if not state.last_alert_time or state.last_alert_time < expire_time:
                        to_remove.append(fp)
            
            for fp in to_remove:
                del self._states[fp]
                cleaned += 1
        
        return cleaned


__all__ = [
    "AggregationState",
    "AlertAggregator",
]

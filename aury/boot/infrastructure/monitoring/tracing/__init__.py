"""OpenTelemetry 集成模块。

提供 OpenTelemetry 遍测功能的封装，包括：
- TracerProvider 配置和初始化
- 自定义 SpanProcessor（用于触发告警）
- trace_id 获取函数
- 便捷的 span API
- 日志告警集成

使用方式：
    # 自动集成（通过 TelemetryComponent）
    TELEMETRY__ENABLED=true
    
    # 手动追踪
    from aury.boot.infrastructure.monitoring.tracing import span, trace_span
    
    @trace_span(kind="llm", model="gpt-4")
    async def call_llm(prompt: str):
        ...
    
    with span("tool.search", kind="tool"):
        result = await search()
"""

from __future__ import annotations

from .context import get_otel_trace_id, is_otel_available
from .logging import setup_otel_logging
from .processor import AlertingSpanProcessor
from .provider import TelemetryConfig, TelemetryProvider
from .tracing import (
    SpanKind,
    set_span_attribute,
    set_span_error,
    span,
    trace_span,
)

__all__ = [
    # Provider
    "AlertingSpanProcessor",
    "TelemetryConfig",
    "TelemetryProvider",
    # Context
    "get_otel_trace_id",
    "is_otel_available",
    # Tracing API
    "SpanKind",
    "set_span_attribute",
    "set_span_error",
    "span",
    "trace_span",
    # Logging
    "setup_otel_logging",
]

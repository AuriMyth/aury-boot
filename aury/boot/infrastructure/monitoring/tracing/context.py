"""OpenTelemetry context 工具函数。

提供从 OTel 获取 trace_id 的函数。
"""

from __future__ import annotations


def is_otel_available() -> bool:
    """检查 OpenTelemetry 是否可用。"""
    try:
        from opentelemetry import trace
        return bool(trace)  # 确保引用被使用
    except ImportError:
        return False


def get_otel_trace_id() -> str | None:
    """从 OpenTelemetry 获取当前 trace_id。
    
    Returns:
        str | None: 32 位十六进制 trace_id，如果不可用则返回 None
    """
    try:
        from opentelemetry import trace
        
        span = trace.get_current_span()
        if span and span.is_recording():
            trace_id = span.get_span_context().trace_id
            if trace_id:
                return format(trace_id, "032x")
    except ImportError:
        pass
    except Exception:
        pass
    
    return None


__all__ = [
    "get_otel_trace_id",
    "is_otel_available",
]

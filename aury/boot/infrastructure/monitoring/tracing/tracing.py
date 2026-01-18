"""便捷的链路追踪 API。

提供简洁的 span 创建方式，用于手动追踪自定义业务逻辑。

用法:
    # 上下文管理器方式（kind 可自定义，如 "llm"、"tool" 等）
    with span("llm.chat", kind="llm", model="gpt-4") as s:
        response = await call_openai()
        s.set_attribute("tokens", response.usage.total_tokens)
    
    # 装饰器方式
    @trace_span("tool.search", kind="tool")
    async def search(query: str):
        ...
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any

# OTel 可选依赖
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.trace import SpanKind as OTelSpanKind
    from opentelemetry.trace import StatusCode
except ImportError:
    otel_trace = None  # type: ignore[assignment]
    OTelSpanKind = None  # type: ignore[assignment, misc]
    StatusCode = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from opentelemetry.trace import Span


class SpanKind:
    """OTel 标准 Span 类型常量。
    
    开发者也可传入任意字符串作为 kind（如 "llm"、"tool"），
    会作为属性记录，并默认映射为 INTERNAL。
    """
    
    INTERNAL = "internal"   # 内部操作
    CLIENT = "client"       # 外部调用（HTTP client、DB）
    SERVER = "server"       # 处理请求
    PRODUCER = "producer"   # 消息生产者
    CONSUMER = "consumer"   # 消息消费者


def _get_tracer():
    """获取 tracer 实例。"""
    if otel_trace is None:
        return None
    return otel_trace.get_tracer("aury")


def _to_otel_span_kind(kind: str):
    """转换为 OTel SpanKind。
    
    标准类型（internal/client/server/producer/consumer）映射到对应的 OTel SpanKind，
    其他自定义类型（如 llm/tool 等）默认映射为 INTERNAL。
    """
    if OTelSpanKind is None:
        return None
    
    mapping = {
        "internal": OTelSpanKind.INTERNAL,
        "client": OTelSpanKind.CLIENT,
        "server": OTelSpanKind.SERVER,
        "producer": OTelSpanKind.PRODUCER,
        "consumer": OTelSpanKind.CONSUMER,
    }
    return mapping.get(kind, OTelSpanKind.INTERNAL)


@contextmanager
def span(
    name: str,
    kind: str = "internal",
    **attributes: Any,
):
    """创建追踪 span（上下文管理器）。
    
    Args:
        name: span 名称，建议格式 "{category}.{operation}"
        kind: span 类型，可自由定义（如 "llm"、"tool"、"task" 等），
              标准类型（internal/client/server）会映射到 OTel SpanKind
        **attributes: 附加属性
    
    Yields:
        Span: OTel span 对象，可调用 set_attribute() 添加更多属性
    
    用法:
        # 追踪 LLM 调用
        with span("llm.chat", kind="llm", model="gpt-4") as s:
            response = await openai.chat.completions.create(...)
            s.set_attribute("llm.tokens", response.usage.total_tokens)
        
        # 追踪工具调用
        with span("tool.web_search", kind="tool", query=query):
            result = await search(query)
        
        # 追踪自定义业务
        with span("payment.process", order_id=order_id):
            await process_payment(order_id)
    """
    tracer = _get_tracer()
    
    if tracer is None:
        # OTel 未安装，使用空上下文
        yield _DummySpan()
        return
    
    otel_kind = _to_otel_span_kind(kind)
    
    with tracer.start_as_current_span(name, kind=otel_kind) as s:
        # 设置自定义类型标识（用于 AlertingSpanProcessor 识别）
        s.set_attribute("aury.span_kind", kind)
        
        # 设置用户传入的属性
        for key, value in attributes.items():
            if value is not None:
                s.set_attribute(key, _safe_attribute_value(value))
        
        yield s


def trace_span(
    name: str | None = None,
    kind: str = "internal",
    **attributes: Any,
) -> Callable:
    """追踪装饰器。
    
    Args:
        name: span 名称，默认使用函数名
        kind: span 类型，可自由定义
        **attributes: 附加属性
    
    用法:
        @trace_span(kind="llm", model="gpt-4")
        async def chat(prompt: str):
            return await openai.chat.completions.create(...)
        
        @trace_span("custom.operation")
        def sync_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__qualname__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with span(span_name, kind=kind, **attributes):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with span(span_name, kind=kind, **attributes):
                return func(*args, **kwargs)
        
        # 根据函数类型返回对应包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def set_span_error(error: Exception, message: str | None = None) -> None:
    """在当前 span 上记录错误。
    
    Args:
        error: 异常对象
        message: 错误消息（可选）
    """
    if otel_trace is None or StatusCode is None:
        return
    
    current_span = otel_trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.set_status(StatusCode.ERROR, message or str(error))
        current_span.record_exception(error)


def set_span_attribute(key: str, value: Any) -> None:
    """在当前 span 上设置属性。
    
    Args:
        key: 属性名
        value: 属性值
    """
    if otel_trace is None:
        return
    
    current_span = otel_trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.set_attribute(key, _safe_attribute_value(value))


def _safe_attribute_value(value: Any) -> Any:
    """转换属性值为 OTel 支持的类型。"""
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [_safe_attribute_value(v) for v in value]
    return str(value)


class _DummySpan:
    """占位 span，用于 OTel 未安装时。"""
    
    def set_attribute(self, key: str, value: Any) -> None:
        pass
    
    def set_status(self, status, description: str | None = None) -> None:
        pass
    
    def record_exception(self, exception: Exception) -> None:
        pass
    
    def add_event(self, name: str, attributes: dict | None = None) -> None:
        pass


__all__ = [
    "SpanKind",
    "set_span_attribute",
    "set_span_error",
    "span",
    "trace_span",
]

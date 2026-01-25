"""自定义 SpanProcessor，用于检测慢 span 和异常 span 并触发告警。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import fnmatch
import re
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

# OTel 可选依赖
try:
    from opentelemetry.trace import SpanKind as OTelSpanKind
    from opentelemetry.trace import StatusCode
except ImportError:
    OTelSpanKind = None  # type: ignore[assignment, misc]
    StatusCode = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from asyncio import Task

    from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

# 告警回调类型: async def callback(event_type, message, **metadata)
AlertCallback = Callable[[str, str], Awaitable[None]] | Callable[..., Awaitable[None]]


class AlertingSpanProcessor:
    """告警 SpanProcessor。
    
    在 span 结束时检测：
    - 慢 span（duration > threshold）
    - 异常 span（status = ERROR）
    
    通过回调函数触发告警，不直接依赖 alerting 模块。
    
    注意：这是一个同步 SpanProcessor，告警发送会在后台异步执行。
    """
    
    # 保存后台任务引用，避免被 GC 回收
    _background_tasks: set["Task"] = set()
    
    def __init__(
        self,
        *,
        slow_request_threshold: float = 1.0,
        slow_sql_threshold: float = 0.5,
        alert_on_slow_request: bool = True,
        alert_on_slow_sql: bool = True,
        alert_on_error: bool = True,
        alert_callback: AlertCallback | None = None,
        slow_request_exclude_paths: list[str] | None = None,
    ) -> None:
        """初始化 AlertingSpanProcessor。
        
        Args:
            slow_request_threshold: HTTP 请求慢阈值（秒）
            slow_sql_threshold: SQL 查询慢阈值（秒）
            alert_on_slow_request: 是否对慢 HTTP 请求发送告警
            alert_on_slow_sql: 是否对慢 SQL 发送告警
            alert_on_error: 是否对异常 span 发送告警
            alert_callback: 告警回调函数，签名: async (event_type, message, **metadata) -> None
            slow_request_exclude_paths: 慢请求排除路径列表（支持 * 通配符），如 SSE/WebSocket 长连接
        """
        self._slow_request_threshold = slow_request_threshold
        self._slow_sql_threshold = slow_sql_threshold
        self._alert_on_slow_request = alert_on_slow_request
        self._alert_on_slow_sql = alert_on_slow_sql
        self._alert_on_error = alert_on_error
        self._alert_callback = alert_callback
        
        # 编译排除路径正则
        self._exclude_regexes: list[re.Pattern] = []
        if slow_request_exclude_paths:
            for pattern in slow_request_exclude_paths:
                regex_pattern = fnmatch.translate(pattern)
                self._exclude_regexes.append(re.compile(regex_pattern))
    
    def on_start(self, span: "Span", parent_context: object = None) -> None:
        """span 开始时调用（不做处理）。"""
        pass
    
    def on_end(self, span: "ReadableSpan") -> None:
        """span 结束时调用，检测并触发告警。"""
        if StatusCode is None:
            return
        
        # 获取 span 信息
        name = span.name
        duration_ns = (span.end_time or 0) - (span.start_time or 0)
        duration_s = duration_ns / 1e9
        status = span.status
        trace_id = format(span.context.trace_id, "032x") if span.context else ""
        
        # 获取 span 属性
        attributes = dict(span.attributes) if span.attributes else {}
        
        # 判断 span 类型
        span_kind = _get_span_kind(span)
        
        # 根据 span 类型获取对应的慢阈值和开关
        threshold = self._get_slow_threshold(span_kind)
        should_alert = self._should_alert_slow(span_kind)
        
        # 检测慢 span
        if should_alert and threshold > 0 and duration_s >= threshold:
            # 检查是否在排除路径中
            if self._is_path_excluded(name, attributes):
                return
            
            self._emit_slow_alert(
                name=name,
                duration=duration_s,
                trace_id=trace_id,
                span_kind=span_kind,
                attributes=attributes,
                threshold=threshold,
            )
        
        # 检测异常 span（只对 SERVER span 发告警，避免重复）
        if (
            self._alert_on_error
            and status
            and status.status_code == StatusCode.ERROR
            and span_kind == "http"  # 只对 HTTP SERVER span 发异常告警
        ):
            # 过滤 4xx 业务异常（如 401/403/404 等），只对 5xx 系统异常告警
            http_status = attributes.get("http.status_code", 0)
            if 400 <= http_status < 500:
                return  # 业务异常不告警
            
            # 从 span events 中提取异常详情
            exception_info = _extract_exception_info(span)
            self._emit_error_alert(
                name=name,
                duration=duration_s,
                trace_id=trace_id,
                span_kind=span_kind,
                error_message=exception_info.get("message") or status.description or "Unknown error",
                attributes=attributes,
                exception_info=exception_info,
            )
    
    def shutdown(self) -> None:
        """关闭处理器。"""
        pass
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """强制刷新（无缓冲，直接返回）。"""
        return True
    
    def _get_slow_threshold(self, span_kind: str) -> float:
        """根据 span 类型获取对应的慢阈值。"""
        if span_kind == "database":
            return self._slow_sql_threshold
        elif span_kind in ("http", "http_client"):
            return self._slow_request_threshold
        # 其他类型使用 HTTP 阈值作为默认
        return self._slow_request_threshold
    
    def _should_alert_slow(self, span_kind: str) -> bool:
        """根据 span 类型判断是否应该发送慢告警。"""
        if span_kind == "database":
            return self._alert_on_slow_sql
        elif span_kind in ("http", "http_client", "internal"):
            return self._alert_on_slow_request
        # 其他类型默认使用 HTTP 的开关
        return self._alert_on_slow_request
    
    def _is_path_excluded(self, name: str, attributes: dict) -> bool:
        """检查路径是否在排除列表中。"""
        if not self._exclude_regexes:
            return False
        
        # 从 attributes 或 span name 中提取路径
        path = (
            attributes.get("http.route")
            or attributes.get("http.target")
            or name
        )
        
        # 检查所有可能的路径来源
        paths_to_check = [path]
        
        # 也检查 span name 中的路径（可能包含 HTTP 方法和后缀）
        # 例如 "GET /api/v1/spaces/{space_id}/subscribe http receive"
        if name and name != path:
            # 尝试提取 span name 中的路径部分
            parts = name.split()
            for part in parts:
                if part.startswith("/"):
                    paths_to_check.append(part)
        
        for p in paths_to_check:
            if any(regex.fullmatch(p) for regex in self._exclude_regexes):
                return True
        
        return False
    
    def _emit_slow_alert(
        self,
        name: str,
        duration: float,
        trace_id: str,
        span_kind: str,
        attributes: dict,
        threshold: float,
    ) -> None:
        """发送慢 span 告警。"""
        if not self._alert_callback:
            return
        
        try:
            task = asyncio.create_task(
                self._alert_callback(
                    _get_event_type_for_slow(span_kind),
                    f"慢 {span_kind}: {name}",
                    severity="warning",
                    trace_id=trace_id,
                    source=span_kind,
                    duration=duration,
                    threshold=threshold,
                    **_extract_alert_context(attributes),
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except RuntimeError:
            logger.debug(f"无法发送慢 span 告警（无事件循环）: {name}")
    
    def _emit_error_alert(
        self,
        name: str,
        duration: float,
        trace_id: str,
        span_kind: str,
        error_message: str,
        attributes: dict,
        exception_info: dict | None = None,
    ) -> None:
        """发送异常 span 告警。"""
        if not self._alert_callback:
            return
        
        # 合并异常信息
        extra_context = _extract_alert_context(attributes)
        if exception_info:
            if exception_info.get("type"):
                extra_context["error_type"] = exception_info["type"]
            if exception_info.get("stacktrace"):
                extra_context["stacktrace"] = exception_info["stacktrace"]
        
        try:
            task = asyncio.create_task(
                self._alert_callback(
                    "exception",
                    f"异常: {error_message}",
                    severity="error",
                    trace_id=trace_id,
                    source=span_kind,
                    duration=duration,
                    error_message=error_message,
                    **extra_context,
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except RuntimeError:
            logger.debug(f"无法发送异常 span 告警（无事件循环）: {name}")


def _get_span_kind(span: "ReadableSpan") -> str:
    """根据 span 属性推断类型。"""
    if OTelSpanKind is None:
        return "unknown"
    
    kind = span.kind
    
    if kind == OTelSpanKind.SERVER:
        # HTTP 请求
        return "http"
    elif kind == OTelSpanKind.CLIENT:
        # 外部调用（DB、HTTP client 等）
        attributes = dict(span.attributes) if span.attributes else {}
        if "db.system" in attributes:
            return "database"
        elif "http.url" in attributes or "http.target" in attributes:
            return "http_client"
        return "client"
    elif kind == OTelSpanKind.INTERNAL:
        return "internal"
    elif kind == OTelSpanKind.PRODUCER:
        return "producer"
    elif kind == OTelSpanKind.CONSUMER:
        return "consumer"
    
    return "unknown"


def _get_event_type_for_slow(span_kind: str) -> str:
    """根据 span 类型获取慢操作的告警事件类型。"""
    mapping = {
        "http": "slow_request",
        "database": "slow_sql",
        "http_client": "slow_request",
        "internal": "slow_request",  # internal span 也用 slow_request 类型
    }
    return mapping.get(span_kind, "custom")


def _extract_exception_info(span: "ReadableSpan") -> dict:
    """从 span events 中提取异常信息。
    
    OTEL 会将异常作为 span event 记录，包含：
    - exception.type: 异常类型
    - exception.message: 异常消息
    - exception.stacktrace: 堆栈信息
    """
    info = {}
    
    if not span.events:
        return info
    
    for event in span.events:
        if event.name == "exception":
            attrs = dict(event.attributes) if event.attributes else {}
            if "exception.type" in attrs:
                info["type"] = str(attrs["exception.type"])
            if "exception.message" in attrs:
                info["message"] = str(attrs["exception.message"])
            if "exception.stacktrace" in attrs:
                info["stacktrace"] = str(attrs["exception.stacktrace"])
            break  # 只取第一个异常事件
    
    return info


def _extract_alert_context(attributes: dict) -> dict:
    """从 span 属性中提取告警上下文。"""
    context = {}
    
    # HTTP 相关
    if "http.method" in attributes:
        context["method"] = attributes["http.method"]
    if "http.route" in attributes:
        context["route"] = attributes["http.route"]
    if "http.target" in attributes:
        context["endpoint"] = attributes["http.target"]
    if "http.url" in attributes:
        context["url"] = attributes["http.url"]
    if "http.status_code" in attributes:
        context["status_code"] = attributes["http.status_code"]
    
    # 数据库相关
    if "db.system" in attributes:
        context["db_system"] = attributes["db.system"]
    if "db.statement" in attributes:
        context["sql"] = _normalize_sql(str(attributes["db.statement"]))
    
    return context


def _normalize_sql(sql: str) -> str:
    """清理 SQL 多余空白。"""
    import re
    # 将多个空白字符（包括换行、制表符）合并为单个空格
    sql = re.sub(r'\s+', ' ', sql)
    return sql.strip()


__all__ = ["AlertingSpanProcessor"]

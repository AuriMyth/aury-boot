"""日志管理器 - 统一的日志配置和管理。

提供：
- 统一的日志配置（多日志级别、滚动机制）
- 性能监控装饰器
- 异常日志装饰器
- 链路追踪 ID 支持
- 请求上下文注入（user_id 等）
- 自定义日志 sink 注册 API

日志文件：
- {service_type}_info_{date}.log  - INFO/WARNING/DEBUG 日志
- {service_type}_error_{date}.log - ERROR/CRITICAL 日志
- 可通过 register_log_sink() 注册自定义日志文件（如 access.log）

注意：HTTP 相关的日志功能（RequestLoggingMiddleware, log_request）已移至
application.middleware.logging
"""

from __future__ import annotations

from loguru import logger

# 移除默认配置，由setup_logging统一配置
logger.remove()

# 从子模块导入
from aury.boot.common.logging.context import (
    ServiceContext,
    get_request_contexts,
    get_service_context,
    get_trace_id,
    register_request_context,
    set_service_context,
    set_trace_id,
)
from aury.boot.common.logging.decorators import (
    get_class_logger,
    log_exceptions,
    log_performance,
)
from aury.boot.common.logging.format import (
    format_exception_java_style,
    log_exception,
)
from aury.boot.common.logging.setup import (
    DEFAULT_INTERCEPT_LOGGERS,
    register_log_sink,
    setup_intercept,
    setup_logging,
)

__all__ = [
    "DEFAULT_INTERCEPT_LOGGERS",
    "ServiceContext",
    "format_exception_java_style",
    "get_class_logger",
    "get_request_contexts",
    "get_service_context",
    "get_trace_id",
    "log_exception",
    "log_exceptions",
    "log_performance",
    "logger",
    "register_log_sink",
    "register_request_context",
    "set_service_context",
    "set_trace_id",
    "setup_intercept",
    "setup_logging",
]


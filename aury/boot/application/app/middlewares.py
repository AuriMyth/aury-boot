"""默认中间件实现。

提供所有内置 HTTP 中间件的实现。
"""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from starlette.middleware import Middleware as StarletteMiddleware

from aury.boot.application.app.base import FoundationApp, Middleware
from aury.boot.application.config import BaseConfig
from aury.boot.application.constants import MiddlewareName
from aury.boot.application.middleware.logging import (
    RequestLoggingMiddleware as StarletteRequestLoggingMiddleware,
)
from aury.boot.application.middleware.logging import (
    WebSocketLoggingMiddleware as StarletteWebSocketLoggingMiddleware,
)

__all__ = [
    "CORSMiddleware",
    "RequestLoggingMiddleware",
    "WebSocketLoggingMiddleware",
]


class RequestLoggingMiddleware(Middleware):
    """请求日志中间件。

    自动记录所有 HTTP 请求的详细信息，包括：
    - 请求方法、路径、查询参数
    - 客户端 IP、User-Agent
    - 响应状态码、耗时
    - 链路追踪 ID（X-Trace-ID / X-Request-ID）
    """

    name = MiddlewareName.REQUEST_LOGGING
    enabled = True
    order = 0  # 最先执行，确保日志记录所有请求

    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建请求日志中间件实例。"""
        return StarletteMiddleware(StarletteRequestLoggingMiddleware)


class CORSMiddleware(Middleware):
    """CORS 跨域处理中间件。

    处理跨域资源共享（CORS）请求，允许配置：
    - 允许的源（origins）
    - 允许的方法（methods）
    - 允许的头（headers）
    - 凭证支持（credentials）
    """

    name = MiddlewareName.CORS
    enabled = True
    order = 10  # 在请求日志之后执行

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当配置了 origins 时启用。"""
        return self.enabled and bool(config.cors.origins)

    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建 CORS 中间件实例。"""
        return StarletteMiddleware(
            FastAPICORSMiddleware,
            allow_origins=config.cors.origins,
            allow_credentials=config.cors.allow_credentials,
            allow_methods=config.cors.allow_methods,
            allow_headers=config.cors.allow_headers,
        )


class WebSocketLoggingMiddleware(Middleware):
    """WebSocket 日志中间件。

    记录 WebSocket 连接生命周期：
    - 连接建立/断开
    - 消息收发统计
    - 异常断开
    - 链路追踪 ID
    """

    name = MiddlewareName.WEBSOCKET_LOGGING
    enabled = True
    order = 1  # 紧随 HTTP 日志中间件

    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建 WebSocket 日志中间件实例。"""
        return StarletteMiddleware(
            StarletteWebSocketLoggingMiddleware,
            log_messages=config.log.websocket_log_messages,
        )


# 设置默认中间件
FoundationApp.middlewares = [
    RequestLoggingMiddleware,
    WebSocketLoggingMiddleware,
    CORSMiddleware,
]

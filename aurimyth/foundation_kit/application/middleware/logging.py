"""HTTP 请求日志中间件。

提供 HTTP 相关的日志功能，包括：
- 请求日志中间件
- 请求日志装饰器
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import time
from typing import TypeVar

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

T = TypeVar("T")


def log_request(func: Callable[..., T]) -> Callable[..., T]:
    """请求日志装饰器。
    
    记录请求的详细信息。
    
    使用示例:
        @router.get("/users")
        @log_request
        async def get_users(request: Request):
            return {"users": []}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        request: Request | None = None
        
        # 查找Request对象
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            request = kwargs.get("request")
        
        # 记录请求信息
        if request:
            logger.info(
                f"请求: {request.method} {request.url.path} | "
                f"客户端: {request.client.host if request.client else 'unknown'} | "
                f"查询参数: {dict(request.query_params)}"
            )
        
        try:
            # 执行函数
            start_time = time.time()
            response = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 记录响应信息
            if request:
                logger.info(
                    f"响应: {request.method} {request.url.path} | "
                    f"耗时: {duration:.3f}s"
                )
            
            return response
        except Exception as exc:
            # 记录错误
            if request:
                logger.error(
                    f"错误: {request.method} {request.url.path} | "
                    f"异常: {type(exc).__name__}: {exc}"
                )
            raise
    
    return wrapper


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。
    
    自动记录所有HTTP请求的详细信息，包括：
    - 请求方法、路径、查询参数
    - 客户端IP、User-Agent
    - 响应状态码、耗时
    - 请求体大小（如果可获取）
    
    使用示例:
        from aurimyth.foundation_kit.application.middleware.logging import RequestLoggingMiddleware
        
        app.add_middleware(RequestLoggingMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并记录日志。"""
        start_time = time.time()
        
        # 获取客户端信息
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # 记录请求信息
        logger.info(
            f"→ {request.method} {request.url.path} | "
            f"客户端: {client_host} | "
            f"User-Agent: {user_agent[:50]}"
        )
        
        # 记录查询参数（如果有）
        if request.query_params:
            logger.debug(f"  查询参数: {dict(request.query_params)}")
        
        # 执行请求
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # 记录响应信息
            status_code = response.status_code
            log_level = "error" if status_code >= 500 else "warning" if status_code >= 400 else "info"
            
            logger.log(
                log_level.upper(),
                f"← {request.method} {request.url.path} | "
                f"状态: {status_code} | "
                f"耗时: {duration:.3f}s"
            )
            
            # 如果响应时间过长，记录警告
            if duration > 1.0:
                logger.warning(
                    f"慢请求: {request.method} {request.url.path} | "
                    f"耗时: {duration:.3f}s (超过1秒)"
                )
            
            return response
            
        except Exception as exc:
            duration = time.time() - start_time
            logger.error(
                f"✗ {request.method} {request.url.path} | "
                f"异常: {type(exc).__name__}: {exc} | "
                f"耗时: {duration:.3f}s"
            )
            raise


__all__ = [
    "RequestLoggingMiddleware",
    "log_request",
]


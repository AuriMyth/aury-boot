"""日志管理器 - 统一的日志配置和管理。

提供：
- 统一的日志配置
- 请求日志装饰器
- 性能监控装饰器
- 结构化日志
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Callable, Optional, TypeVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from loguru import logger

T = TypeVar("T")

# 移除默认配置，由setup_logging统一配置
logger.remove()


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """设置日志配置。
    
    根据环境配置日志级别和输出方式。
    
    Args:
        log_level: 日志级别（默认：INFO）
        log_file: 日志文件路径（可选）
    """
    log_level = log_level.upper()
    
    # 控制台输出
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # 文件输出
    if log_file:
        logger.add(
            log_file,
            rotation="00:00",
            retention="7 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8",
            enqueue=True,  # 异步写入
        )
    else:
        # 默认日志文件
        logger.add(
            "log/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="7 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8",
            enqueue=True,
        )
    
    logger.info(f"日志系统初始化完成，级别: {log_level}")


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
        request: Optional[Request] = None
        
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


def log_performance(threshold: float = 1.0) -> Callable:
    """性能监控装饰器。
    
    记录函数执行时间，超过阈值时警告。
    
    Args:
        threshold: 警告阈值（秒）
    
    使用示例:
        @log_performance(threshold=0.5)
        async def slow_operation():
            # 如果执行时间超过0.5秒，会记录警告
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > threshold:
                    logger.warning(
                        f"性能警告: {func.__module__}.{func.__name__} 执行耗时 {duration:.3f}s "
                        f"(阈值: {threshold}s)"
                    )
                else:
                    logger.debug(
                        f"性能: {func.__module__}.{func.__name__} 执行耗时 {duration:.3f}s"
                    )
                
                return result
            except Exception as exc:
                duration = time.time() - start_time
                logger.error(
                    f"执行失败: {func.__module__}.{func.__name__} | "
                    f"耗时: {duration:.3f}s | "
                    f"异常: {type(exc).__name__}: {exc}"
                )
                raise
        
        return wrapper
    return decorator


def log_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """异常日志装饰器。
    
    自动记录函数抛出的异常。
    
    使用示例:
        @log_exceptions
        async def risky_operation():
            # 如果抛出异常，会自动记录
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            logger.exception(
                f"异常捕获: {func.__module__}.{func.__name__} | "
                f"参数: args={args}, kwargs={kwargs} | "
                f"异常: {type(exc).__name__}: {exc}"
            )
            raise
    
    return wrapper


class LoggerMixin:
    """日志混入类。
    
    为类提供日志功能。
    
    使用示例:
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("执行操作")
    """
    
    @property
    def logger(self):
        """获取类专用的日志器。"""
        class_name = self.__class__.__name__
        module_name = self.__class__.__module__
        return logger.bind(name=f"{module_name}.{class_name}")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件。
    
    自动记录所有HTTP请求的详细信息，包括：
    - 请求方法、路径、查询参数
    - 客户端IP、User-Agent
    - 响应状态码、耗时
    - 请求体大小（如果可获取）
    
    使用示例:
        from aurimyth.foundation_kit.utils.logging import RequestLoggingMiddleware
        
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
    "logger",
    "setup_logging",
    "log_request",
    "log_performance",
    "log_exceptions",
    "LoggerMixin",
    "RequestLoggingMiddleware",
]

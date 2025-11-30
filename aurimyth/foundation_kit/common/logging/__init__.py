"""日志管理器 - 统一的日志配置和管理。

提供：
- 统一的日志配置
- 性能监控装饰器
- 异常日志装饰器
- 结构化日志

注意：HTTP 相关的日志功能（RequestLoggingMiddleware, log_request）已移至
application.middleware.logging
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import time
from typing import Any

from loguru import logger

# 移除默认配置，由setup_logging统一配置
logger.remove()


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
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
    def decorator[T](func: Callable[..., T]) -> Callable[..., T]:
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


def log_exceptions[T](func: Callable[..., T]) -> Callable[..., T]:
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


def get_class_logger(obj: object) -> Any:
    """获取类专用的日志器（函数式工具函数）。
    
    根据对象的类和模块名创建绑定的日志器。
    
    Args:
        obj: 对象实例或类
        
    Returns:
        绑定的日志器实例
        
    使用示例:
        class MyService:
            def do_something(self):
                log = get_class_logger(self)
                log.info("执行操作")
    """
    if isinstance(obj, type):
        class_name = obj.__name__
        module_name = obj.__module__
    else:
        class_name = obj.__class__.__name__
        module_name = obj.__class__.__module__
    return logger.bind(name=f"{module_name}.{class_name}")


__all__ = [
    "get_class_logger",
    "log_exceptions",
    "log_performance",
    "logger",
    "setup_logging",
]


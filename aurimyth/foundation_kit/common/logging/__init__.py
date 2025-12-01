"""日志管理器 - 统一的日志配置和管理。

提供：
- 统一的日志配置（多日志级别、滚动机制、文件分类）
- 性能监控装饰器
- 异常日志装饰器
- 结构化日志
- 链路追踪 ID 支持

注意：HTTP 相关的日志功能（RequestLoggingMiddleware, log_request）已移至
application.middleware.logging
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import os
import time
from typing import Any
import uuid

from loguru import logger

# 移除默认配置，由setup_logging统一配置
logger.remove()

# 全局链路追踪ID
_trace_id: str | None = None


def get_trace_id() -> str:
    """获取当前链路追踪ID。"""
    global _trace_id
    if _trace_id is None:
        _trace_id = str(uuid.uuid4())
    return _trace_id


def set_trace_id(trace_id: str) -> None:
    """设置链路追踪ID。"""
    global _trace_id
    _trace_id = trace_id
    logger.bind(trace_id=trace_id)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str | None = None,
    enable_file_rotation: bool = True,
    rotation_size: str = "100 MB",
    rotation_time: str = "00:00",
    retention_days: int = 7,
    enable_classify: bool = True,
    enable_console: bool = True,
    enable_error_file: bool = True,
) -> None:
    """设置日志配置。
    
    根据环境配置日志级别、输出方式、文件分类和滚动机制。
    
    Args:
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_dir: 日志目录（默认：./log）
        enable_file_rotation: 是否启用文件滚动
        rotation_size: 文件大小阈值（默认：100 MB）
        rotation_time: 每日滚动时间（默认：00:00，仅当 enable_file_rotation=True 时有效）
        retention_days: 日志保留天数（默认：7 天）
        enable_classify: 是否按日志级别分类存储（ERROR 单独一个文件）
        enable_console: 是否输出到控制台
        enable_error_file: 是否单独记录错误日志
    """
    log_level = log_level.upper()
    log_dir = log_dir or "log"
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}:{function}:{line}</cyan> | "
        "{extra[trace_id]:.8} - "
        "<level>{message}</level>"
    )
    
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{extra[trace_id]} - "
        "{message}"
    )
    
    # 控制台输出
    if enable_console:
        logger.add(
            lambda msg: print(msg, end=""),
            format=console_format,
            level=log_level,
            colorize=True,
        )
    
    # 通用日志文件（所有级别）
    if enable_file_rotation:
        logger.add(
            os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log"),
            rotation=rotation_time,
            retention=f"{retention_days} days",
            level=log_level,
            format=file_format,
            encoding="utf-8",
            enqueue=True,  # 异步写入
        )
    else:
        logger.add(
            os.path.join(log_dir, "app.log"),
            rotation=rotation_size,
            retention=f"{retention_days} days",
            level=log_level,
            format=file_format,
            encoding="utf-8",
            enqueue=True,
        )
    
    # 按级别分文件
    if enable_error_file:
        # ERROR 级别日志
        if enable_file_rotation:
            logger.add(
                os.path.join(log_dir, "error_{time:YYYY-MM-DD}.log"),
                rotation=rotation_time,
                retention=f"{retention_days} days",
                level="ERROR",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
            )
        else:
            logger.add(
                os.path.join(log_dir, "error.log"),
                rotation=rotation_size,
                retention=f"{retention_days} days",
                level="ERROR",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
            )
        
        # WARNING 级别日志
        if enable_file_rotation:
            logger.add(
                os.path.join(log_dir, "warning_{time:YYYY-MM-DD}.log"),
                rotation=rotation_time,
                retention=f"{retention_days} days",
                level="WARNING",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
                filter=lambda record: record["level"].name == "WARNING",
            )
        else:
            logger.add(
                os.path.join(log_dir, "warning.log"),
                rotation=rotation_size,
                retention=f"{retention_days} days",
                level="WARNING",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
                filter=lambda record: record["level"].name == "WARNING",
            )
        
        # INFO 级别日志
        if enable_file_rotation:
            logger.add(
                os.path.join(log_dir, "info_{time:YYYY-MM-DD}.log"),
                rotation=rotation_time,
                retention=f"{retention_days} days",
                level="INFO",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
                filter=lambda record: record["level"].name == "INFO",
            )
        else:
            logger.add(
                os.path.join(log_dir, "info.log"),
                rotation=rotation_size,
                retention=f"{retention_days} days",
                level="INFO",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
                filter=lambda record: record["level"].name == "INFO",
            )
        
        # DEBUG 级别日志
        if enable_file_rotation:
            logger.add(
                os.path.join(log_dir, "debug_{time:YYYY-MM-DD}.log"),
                rotation=rotation_time,
                retention=f"{retention_days} days",
                level="DEBUG",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
                filter=lambda record: record["level"].name == "DEBUG",
            )
        else:
            logger.add(
                os.path.join(log_dir, "debug.log"),
                rotation=rotation_size,
                retention=f"{retention_days} days",
                level="DEBUG",
                format=file_format,
                encoding="utf-8",
                enqueue=True,
                filter=lambda record: record["level"].name == "DEBUG",
            )
    
    # 分类日志（按模块）
    if enable_classify:
        # 数据库操作日志
        logger.add(
            os.path.join(log_dir, "database_{time:YYYY-MM-DD}.log"),
            rotation=rotation_time if enable_file_rotation else rotation_size,
            retention=f"{retention_days} days",
            level="DEBUG",
            format=file_format,
            encoding="utf-8",
            filter=lambda record: "database" in record["name"].lower() or "repo" in record["name"].lower(),
            enqueue=True,
        )
        
        # 缓存操作日志
        logger.add(
            os.path.join(log_dir, "cache_{time:YYYY-MM-DD}.log"),
            rotation=rotation_time if enable_file_rotation else rotation_size,
            retention=f"{retention_days} days",
            level="DEBUG",
            format=file_format,
            encoding="utf-8",
            filter=lambda record: "cache" in record["name"].lower(),
            enqueue=True,
        )
        
        # RPC 调用日志
        logger.add(
            os.path.join(log_dir, "rpc_{time:YYYY-MM-DD}.log"),
            rotation=rotation_time if enable_file_rotation else rotation_size,
            retention=f"{retention_days} days",
            level="DEBUG",
            format=file_format,
            encoding="utf-8",
            filter=lambda record: "rpc" in record["name"].lower(),
            enqueue=True,
        )
        
        # HTTP 请求日志
        logger.add(
            os.path.join(log_dir, "http_{time:YYYY-MM-DD}.log"),
            rotation=rotation_time if enable_file_rotation else rotation_size,
            retention=f"{retention_days} days",
            level="DEBUG",
            format=file_format,
            encoding="utf-8",
            filter=lambda record: "http" in record["name"].lower() or "request" in record["name"].lower(),
            enqueue=True,
        )
    
    # 日志系统初始化完成
    logger.info(
        f"日志系统初始化完成 | 级别: {log_level} | "
        f"目录: {log_dir} | "
        f"分类: {enable_classify} | "
        f"滚动: {enable_file_rotation}"
    )


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
    "get_trace_id",
    "log_exceptions",
    "log_performance",
    "logger",
    "set_trace_id",
    "setup_logging",
]


"""日志配置和初始化。

提供 setup_logging 和 register_log_sink 功能。
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

from aury.boot.common.logging.context import (
    ServiceContext,
    _to_service_context,
    get_service_context,
    get_trace_id,
    set_service_context,
)
from aury.boot.common.logging.format import create_console_sink, format_message

# 全局日志配置状态
_log_config: dict[str, Any] = {
    "log_dir": "logs",
    "rotation": "00:00",
    "retention_days": 7,
    "file_format": "",
    "initialized": False,
}


def register_log_sink(
    name: str,
    *,
    filter_key: str | None = None,
    level: str = "INFO",
    sink_format: str | None = None,
) -> None:
    """注册自定义日志 sink。
    
    使用 logger.bind() 标记的日志会写入对应文件。
    
    Args:
        name: 日志文件名前缀（如 "access" -> access_2024-01-01.log）
        filter_key: 过滤键名，日志需要 logger.bind(key=True) 才会写入
        level: 日志级别
        sink_format: 自定义格式（默认使用简化格式）
    
    使用示例:
        # 注册 access 日志
        register_log_sink("access", filter_key="access")
        
        # 写入 access 日志
        logger.bind(access=True).info("GET /api/users 200 0.05s")
    """
    if not _log_config["initialized"]:
        raise RuntimeError("请先调用 setup_logging() 初始化日志系统")
    
    log_dir = _log_config["log_dir"]
    rotation = _log_config["rotation"]
    retention_days = _log_config["retention_days"]
    
    default_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{extra[trace_id]} | "
        "{message}"
    )
    
    # 创建 filter
    if filter_key:
        def sink_filter(record, key=filter_key):
            return record["extra"].get(key, False)
    else:
        sink_filter = None
    
    logger.add(
        os.path.join(log_dir, f"{name}_{{time:YYYY-MM-DD}}.log"),
        rotation=rotation,
        retention=f"{retention_days} days",
        level=level,
        format=sink_format or default_format,
        encoding="utf-8",
        enqueue=True,
        delay=True,
        filter=sink_filter,
    )
    
    logger.debug(f"注册日志 sink: {name} (filter_key={filter_key})")


def setup_logging(
    log_level: str = "INFO",
    log_dir: str | None = None,
    service_type: ServiceContext | str = ServiceContext.API,
    enable_file_rotation: bool = True,
    rotation_time: str = "00:00",
    retention_days: int = 7,
    rotation_size: str = "50 MB",
    enable_console: bool = True,
) -> None:
    """设置日志配置。

    日志文件按服务类型分离：
    - {service_type}_info_{date}.log  - INFO/WARNING/DEBUG 日志
    - {service_type}_error_{date}.log - ERROR/CRITICAL 日志
    
    轮转策略：
    - 文件名包含日期，每天自动创建新文件
    - 单文件超过大小限制时，会轮转产生 .1, .2 等后缀
    
    可通过 register_log_sink() 注册额外的日志文件（如 access.log）。

    Args:
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_dir: 日志目录（默认：./logs）
        service_type: 服务类型（app/scheduler/worker）
        enable_file_rotation: 是否启用日志轮转
        rotation_time: 每日轮转时间（默认：00:00）
        retention_days: 日志保留天数（默认：7 天）
        rotation_size: 单文件大小上限（默认：50 MB）
        enable_console: 是否输出到控制台
    """
    log_level = log_level.upper()
    log_dir = log_dir or "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 滚动策略：基于大小轮转（文件名已包含日期，每天自动新文件）
    rotation = rotation_size if enable_file_rotation else None

    # 标准化服务类型
    service_type_enum = _to_service_context(service_type)

    # 清理旧的 sink，避免重复日志（idempotent）
    logger.remove()

    # 保存全局配置（供 register_log_sink 使用）
    _log_config.update({
        "log_dir": log_dir,
        "rotation": rotation,
        "retention_days": retention_days,
        "initialized": True,
    })

    # 设置默认服务上下文
    set_service_context(service_type_enum)

    # 配置 patcher，确保每条日志都有 service 和 trace_id
    logger.configure(patcher=lambda record: (
        record["extra"].update({
            "trace_id": get_trace_id(),
            # 记录字符串值，便于过滤器比较
            "service": get_service_context().value,
        })
    ))

    # 控制台输出（使用 Java 风格堆栈）
    if enable_console:
        logger.add(
            create_console_sink(),
            format="{message}",  # 简单格式，避免解析 <module> 等函数名
            level=log_level,
            colorize=False,  # 颜色在 sink 内处理
        )

    # 为 app 和 scheduler 分别创建日志文件（通过 ContextVar 区分）
    # API 模式下会同时运行嵌入式 scheduler，需要两个文件
    contexts_to_create: list[str] = [service_type_enum.value]
    # API 模式下也需要 scheduler 日志文件
    if service_type_enum is ServiceContext.API:
        contexts_to_create.append(ServiceContext.SCHEDULER.value)
    
    for ctx in contexts_to_create:
        # INFO 级别文件（使用 Java 风格堆栈）
        info_file = os.path.join(
            log_dir,
            f"{ctx}_info_{{time:YYYY-MM-DD}}.log" if enable_file_rotation else f"{ctx}_info.log"
        )
        logger.add(
            info_file,
            format=lambda record: format_message(record),
            rotation=rotation,
            retention=f"{retention_days} days",
            level=log_level,  # >= INFO 都写入（包含 WARNING/ERROR/CRITICAL）
            encoding="utf-8",
            enqueue=True,
            filter=lambda record, c=ctx: (
                record["extra"].get("service") == c
                and not record["extra"].get("access", False)
            ),
        )

        # ERROR 级别文件（使用 Java 风格堆栈）
        error_file = os.path.join(
            log_dir,
            f"{ctx}_error_{{time:YYYY-MM-DD}}.log" if enable_file_rotation else f"{ctx}_error.log"
        )
        logger.add(
            error_file,
            format=lambda record: format_message(record),
            rotation=rotation,
            retention=f"{retention_days} days",
            level="ERROR",
            encoding="utf-8",
            enqueue=True,
            filter=lambda record, c=ctx: record["extra"].get("service") == c,
        )

    logger.info(f"日志系统初始化完成 | 服务: {service_type} | 级别: {log_level} | 目录: {log_dir}")


__all__ = [
    "register_log_sink",
    "setup_logging",
]

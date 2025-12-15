"""日志管理器 - 统一的日志配置和管理。

提供：
- 统一的日志配置（多日志级别、滚动机制）
- 性能监控装饰器
- 异常日志装饰器
- 链路追踪 ID 支持
- 自定义日志 sink 注册 API

日志文件：
- {service_type}_info_{date}.log  - INFO/WARNING/DEBUG 日志
- {service_type}_error_{date}.log - ERROR/CRITICAL 日志
- 可通过 register_log_sink() 注册自定义日志文件（如 access.log）

注意：HTTP 相关的日志功能（RequestLoggingMiddleware, log_request）已移至
application.middleware.logging
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from enum import Enum
from functools import wraps
import os
import sys
import time
import traceback
from typing import Any
import uuid

from loguru import logger

# 移除默认配置，由setup_logging统一配置
logger.remove()

# ============================================================
# 服务上下文（ContextVar）
# ============================================================

class ServiceContext(str, Enum):
    """日志用服务上下文常量（避免跨层依赖）。"""
    API = "api"
    SCHEDULER = "scheduler"
    WORKER = "worker"

# 当前服务上下文（用于决定日志写入哪个文件）
_service_context: ContextVar[ServiceContext] = ContextVar("service_context", default=ServiceContext.API)

# 链路追踪 ID
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_service_context() -> ServiceContext:
    """获取当前服务上下文。"""
    return _service_context.get()


def _to_service_context(ctx: ServiceContext | str) -> ServiceContext:
    """将输入标准化为 ServiceContext。"""
    if isinstance(ctx, ServiceContext):
        return ctx
    val = str(ctx).strip().lower()
    if val == "app":  # 兼容旧值
        val = ServiceContext.API.value
    try:
        return ServiceContext(val)
    except ValueError:
        return ServiceContext.API


def set_service_context(context: ServiceContext | str) -> None:
    """设置当前服务上下文。

    在调度器任务执行前调用 set_service_context("scheduler")，
    后续该任务中的所有日志都会写入 scheduler_xxx.log。

    Args:
        context: 服务类型（api/scheduler/worker，或兼容 "app"）
    """
    _service_context.set(_to_service_context(context))


def get_trace_id() -> str:
    """获取当前链路追踪ID。

    如果尚未设置，则生成一个新的随机 ID。
    """
    trace_id = _trace_id_var.get()
    if not trace_id:
        trace_id = str(uuid.uuid4())
        _trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """设置链路追踪ID。"""
    _trace_id_var.set(trace_id)


# ============================================================
# 日志配置
# ============================================================

# 全局日志配置状态
_log_config: dict[str, Any] = {
    "log_dir": "logs",
    "rotation": "00:00",
    "retention_days": 7,
    "file_format": "",
    "initialized": False,
}

# 要过滤的内部模块（不显示在堆栈中）
_INTERNAL_MODULES = {
    "asyncio", "runners", "base_events", "events", "tasks",
    "starlette", "uvicorn", "anyio", "httptools",
}


def _format_exception_compact(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> str:
    """格式化异常为 Java 风格堆栈 + 参数摘要。"""
    import linecache
    
    lines = [f"{exc_type.__name__}: {exc_value}"]
    
    all_locals: dict[str, str] = {}
    seen_values: set[str] = set()  # 用于去重
    
    tb = exc_tb
    while tb:
        frame = tb.tb_frame
        filename = frame.f_code.co_filename
        short_file = filename.split("/")[-1]
        func_name = frame.f_code.co_name
        lineno = tb.tb_lineno
        
        # 简化模块路径
        is_site_package = "site-packages/" in filename
        if is_site_package:
            module = filename.split("site-packages/")[-1].replace("/", ".").replace(".py", "")
            # 过滤内部模块
            module_root = module.split(".")[0]
            if module_root in _INTERNAL_MODULES:
                tb = tb.tb_next
                continue
        else:
            module = short_file.replace(".py", "")
        
        lines.append(f"    at {module}.{func_name}({short_file}:{lineno})")
        
        # 对于用户代码（非 site-packages），显示具体代码行
        if not is_site_package:
            source_line = linecache.getline(filename, lineno).strip()
            if source_line:
                lines.append(f"        >> {source_line}")
        
        # 收集局部变量（排除内部变量和 self）
        for k, v in frame.f_locals.items():
            if k.startswith("_") or k in ("self", "cls"):
                continue
            # 尝试获取变量的字符串表示
            try:
                # Pydantic 模型使用 model_dump
                if hasattr(v, "model_dump"):
                    val_str = repr(v.model_dump())
                elif isinstance(v, str | int | float | bool | dict | list | tuple):
                    val_str = repr(v)
                else:
                    # 其他类型显示类名
                    val_str = f"<{type(v).__name__}>"
            except Exception:
                val_str = f"<{type(v).__name__}>"
            
            # 截断过长的值（200 字符）
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            
            # 去重：相同值的变量只保留第一个
            if val_str not in seen_values and k not in all_locals:
                all_locals[k] = val_str
                seen_values.add(val_str)
        
        tb = tb.tb_next
    
    # 输出参数
    if all_locals:
        lines.append("  Locals:")
        for k, v in list(all_locals.items())[:10]:  # 最多 10 个
            lines.append(f"    {k} = {v}")
    
    return "\n".join(lines)


def _create_console_sink(colorize: bool = True):
    """创建控制台 sink（Java 风格异常格式）。"""
    import sys
    
    # ANSI 颜色码
    if colorize:
        GREEN = "\033[32m"
        CYAN = "\033[36m"
        YELLOW = "\033[33m"
        RED = "\033[31m"
        RESET = "\033[0m"
        BOLD = "\033[1m"
    else:
        GREEN = CYAN = YELLOW = RED = RESET = BOLD = ""
    
    LEVEL_COLORS = {
        "DEBUG": CYAN,
        "INFO": GREEN,
        "WARNING": YELLOW,
        "ERROR": RED,
        "CRITICAL": f"{BOLD}{RED}",
    }
    
    def sink(message):
        record = message.record
        exc = record.get("exception")
        
        time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S")
        level = record["level"].name
        level_color = LEVEL_COLORS.get(level, "")
        service = record["extra"].get("service", "api")
        trace_id = record["extra"].get("trace_id", "")[:8]
        name = record["name"]
        func = record["function"]
        line = record["line"]
        msg = record["message"]
        
        # 基础日志行
        output = (
            f"{GREEN}{time_str}{RESET} | "
            f"{CYAN}[{service}]{RESET} | "
            f"{level_color}{level: <8}{RESET} | "
            f"{CYAN}{name}:{func}:{line}{RESET} | "
            f"{trace_id} - "
            f"{level_color}{msg}{RESET}\n"
        )
        
        # 异常堆栈
        if exc and exc.type:
            stack = _format_exception_compact(exc.type, exc.value, exc.traceback)
            output += f"{RED}{stack}{RESET}\n"
        
        sys.stderr.write(output)
    
    return sink


def _escape_tags(s: str) -> str:
    """转义 loguru 格式特殊字符，避免解析错误。"""
    # 转义 { } 避免被当作 format 字段
    s = s.replace("{", "{{").replace("}", "}}")
    # 转义 < 避免被当作颜色标签
    return s.replace("<", r"\<")


def _format_message(record: dict) -> str:
    """格式化日志消息（用于文件 sink）。"""
    exc = record.get("exception")
    
    time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S")
    level_name = record["level"].name
    trace_id = record["extra"].get("trace_id", "")
    name = record["name"]
    func = _escape_tags(record["function"])  # 转义 <module> 等
    line = record["line"]
    msg = _escape_tags(record["message"])  # 转义消息中的 <
    
    # 基础日志行
    output = (
        f"{time_str} | {level_name: <8} | "
        f"{name}:{func}:{line} | "
        f"{trace_id} - {msg}\n"
    )
    
    # 异常堆栈
    if exc and exc.type:
        stack = _format_exception_compact(exc.type, exc.value, exc.traceback)
        output += f"{_escape_tags(stack)}\n"
    
    return output


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


def _parse_size(size_str: str) -> int:
    """解析大小字符串为字节数。"""
    size_str = size_str.strip().upper()
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            return int(float(size_str[:-len(unit)].strip()) * multiplier)
    return int(size_str)


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
        rotation_size: 单文件大小上限（默认：100 MB）
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
            _create_console_sink(),
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
            format=lambda record: _format_message(record),
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
            format=lambda record: _format_message(record),
            rotation=rotation,
            retention=f"{retention_days} days",
            level="ERROR",
            encoding="utf-8",
            enqueue=True,
            filter=lambda record, c=ctx: record["extra"].get("service") == c,
        )

    logger.info(f"日志系统初始化完成 | 服务: {service_type} | 级别: {log_level} | 目录: {log_dir}")


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


# ============================================================
# Java 风格堆栈格式化
# ============================================================

def format_exception_java_style(
    exc_type: type[BaseException] | None = None,
    exc_value: BaseException | None = None,
    exc_tb: Any | None = None,
    *,
    max_frames: int = 20,
    skip_site_packages: bool = False,
) -> str:
    """将异常堆栈格式化为 Java 风格。
    
    输出格式:
        ValueError: error message
            at module.function(file.py:42)
            at module.Class.method(file.py:100)
    
    Args:
        exc_type: 异常类型（默认从 sys.exc_info() 获取）
        exc_value: 异常值
        exc_tb: 异常 traceback
        max_frames: 最大堆栈帧数
        skip_site_packages: 是否跳过第三方库的堆栈帧
        
    Returns:
        Java 风格的堆栈字符串
        
    使用示例:
        try:
            risky_operation()
        except Exception:
            logger.error(format_exception_java_style())
    """
    if exc_type is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
    
    if exc_type is None or exc_value is None:
        return "No exception"
    
    lines = [f"{exc_type.__name__}: {exc_value}"]
    
    frames = traceback.extract_tb(exc_tb)
    if len(frames) > max_frames:
        frames = frames[-max_frames:]
        lines.append(f"    ... ({len(traceback.extract_tb(exc_tb)) - max_frames} frames omitted)")
    
    for frame in frames:
        filename = frame.filename
        
        # 跳过第三方库
        if skip_site_packages and "site-packages" in filename:
            continue
        
        # 简化文件路径为模块风格
        short_file = filename.split("/")[-1]
        
        # 构建模块路径
        if "site-packages/" in filename:
            # 第三方库: 提取包名
            module_part = filename.split("site-packages/")[-1]
            module_path = module_part.replace("/", ".").replace(".py", "")
        else:
            # 项目代码: 使用文件名
            module_path = short_file.replace(".py", "")
        
        lines.append(f"    at {module_path}.{frame.name}({short_file}:{frame.lineno})")
    
    return "\n".join(lines)


def log_exception(
    message: str = "异常",
    *,
    exc_info: tuple | None = None,
    level: str = "ERROR",
    context: dict[str, Any] | None = None,
    max_frames: int = 20,
) -> None:
    """记录异常日志（Java 风格堆栈）。
    
    相比 logger.exception()，输出更简洁的堆栈信息。
    
    Args:
        message: 日志消息
        exc_info: 异常信息元组 (type, value, tb)，默认从 sys.exc_info() 获取
        level: 日志级别
        context: 额外上下文信息（如请求参数）
        max_frames: 最大堆栈帧数
        
    使用示例:
        try:
            user_service.create(data)
        except Exception:
            log_exception(
                "创建用户失败",
                context={"user_data": data.model_dump()}
            )
            raise
    """
    if exc_info is None:
        exc_info = sys.exc_info()
    
    exc_type, exc_value, exc_tb = exc_info
    
    # 构建日志消息
    parts = [message]
    
    # 添加上下文
    if context:
        ctx_str = " | ".join(f"{k}={v}" for k, v in context.items())
        parts.append(f"上下文: {ctx_str}")
    
    # 添加堆栈
    stack = format_exception_java_style(exc_type, exc_value, exc_tb, max_frames=max_frames)
    parts.append(f"\n{stack}")
    
    full_message = " | ".join(parts[:2]) + parts[2] if len(parts) > 2 else " | ".join(parts)
    
    logger.opt(depth=1).log(level, full_message)


__all__ = [
    "ServiceContext",
    "format_exception_java_style",
    "get_class_logger",
    "get_service_context",
    "get_trace_id",
    "log_exception",
    "log_exceptions",
    "log_performance",
    "logger",
    "register_log_sink",
    "set_service_context",
    "set_trace_id",
    "setup_logging",
]


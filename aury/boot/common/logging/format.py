"""日志格式化函数。

提供 Java 风格堆栈格式化等功能。
"""

from __future__ import annotations

import sys
import traceback
from typing import Any

from loguru import logger

from aury.boot.common.logging.context import get_service_context, get_trace_id

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


def create_console_sink(colorize: bool = True):
    """创建控制台 sink（Java 风格异常格式）。"""
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


def format_message(record: dict) -> str:
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
    "create_console_sink",
    "format_exception_java_style",
    "format_message",
    "log_exception",
]

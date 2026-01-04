"""日志上下文管理。

提供链路追踪 ID、服务上下文、请求上下文的管理。
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from enum import Enum
import uuid


class ServiceContext(str, Enum):
    """日志用服务上下文常量（避免跨层依赖）。"""
    API = "api"
    SCHEDULER = "scheduler"
    WORKER = "worker"


# 当前服务上下文（用于决定日志写入哪个文件）
_service_context: ContextVar[ServiceContext] = ContextVar("service_context", default=ServiceContext.API)

# 链路追踪 ID
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

# 请求上下文字段注册表（用户可注册自定义字段，如 user_id, tenant_id）
_request_context_getters: dict[str, Callable[[], str]] = {}


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


def register_request_context(name: str, getter: Callable[[], str]) -> None:
    """注册请求上下文字段。
    
    注册后，该字段会在每个请求结束时记录一次（与 trace_id 关联）。
    适用于 user_id、tenant_id 等需要关联到请求但不需要每行日志都记录的信息。
    
    Args:
        name: 字段名（如 "user_id", "tenant_id"）
        getter: 获取当前值的函数（通常从 ContextVar 读取）
    
    使用示例:
        from contextvars import ContextVar
        from aury.boot.common.logging import register_request_context
        
        # 定义上下文变量
        _user_id: ContextVar[str] = ContextVar("user_id", default="")
        
        def set_user_id(uid: str):
            _user_id.set(uid)
        
        # 启动时注册（一次）
        register_request_context("user_id", _user_id.get)
        
        # Auth 中间件中设置（每次请求）
        set_user_id(str(user.id))
    """
    _request_context_getters[name] = getter


def get_request_contexts() -> dict[str, str]:
    """获取所有已注册的请求上下文当前值。
    
    Returns:
        字段名到值的字典（仅包含非空值）
    """
    result = {}
    for name, getter in _request_context_getters.items():
        try:
            value = getter()
            if value:  # 只包含非空值
                result[name] = value
        except Exception:
            pass  # 忽略获取失败的字段
    return result


__all__ = [
    "ServiceContext",
    "get_request_contexts",
    "get_service_context",
    "get_trace_id",
    "register_request_context",
    "set_service_context",
    "set_trace_id",
]

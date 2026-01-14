"""日志上下文管理。

提供链路追踪 ID、服务上下文的管理。
"""

from __future__ import annotations

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


__all__ = [
    "ServiceContext",
    "get_service_context",
    "get_trace_id",
    "set_service_context",
    "set_trace_id",
]

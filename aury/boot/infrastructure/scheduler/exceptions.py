"""调度器相关异常定义。

Infrastructure 层异常，继承自 FoundationError。
"""

from __future__ import annotations

from aury.boot.common.exceptions import FoundationError


class SchedulerError(FoundationError):
    """调度器相关错误基类。
    
    所有调度器相关的异常都应该继承此类。
    """
    
    pass


class SchedulerJobError(SchedulerError):
    """调度器任务错误。"""
    
    pass


class SchedulerBackendError(SchedulerError):
    """调度器后端错误。"""
    
    pass


__all__ = [
    "SchedulerBackendError",
    "SchedulerError",
    "SchedulerJobError",
]


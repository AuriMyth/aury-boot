"""任务队列相关异常定义。

Infrastructure 层异常，继承自 FoundationError。
"""

from __future__ import annotations

from aury.boot.common.exceptions import FoundationError


class TaskError(FoundationError):
    """任务队列相关错误基类。
    
    所有任务队列相关的异常都应该继承此类。
    """
    
    pass


class TaskQueueError(TaskError):
    """任务队列错误。"""
    
    pass


class TaskExecutionError(TaskError):
    """任务执行错误。"""
    
    pass


__all__ = [
    "TaskError",
    "TaskExecutionError",
    "TaskQueueError",
]


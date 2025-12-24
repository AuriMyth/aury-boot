"""异步任务管理器模块。

提供统一的任务队列接口，支持条件注册以避免 API 模式下重复注册。
"""

from .constants import TaskQueueName, TaskRunMode
from .exceptions import (
    TaskError,
    TaskExecutionError,
    TaskQueueError,
)
from .manager import TaskManager, TaskProxy, conditional_task

__all__ = [
    "TaskError",
    "TaskExecutionError",
    "TaskManager",
    "TaskProxy",
    "TaskQueueError",
    "TaskQueueName",
    "TaskRunMode",
    "conditional_task",
]


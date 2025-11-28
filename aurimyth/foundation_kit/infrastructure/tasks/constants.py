"""任务队列常量。

任务队列模块内部的常量定义。
"""

from __future__ import annotations

from enum import Enum


class TaskQueueName(str, Enum):
    """任务队列名称常量。

    框架提供的通用队列名称。业务相关的队列名称应由用户自行定义。
    """

    DEFAULT = "default"
    HIGH_PRIORITY = "high_priority"
    LOW_PRIORITY = "low_priority"


class TaskRunMode(str, Enum):
    """任务运行模式（任务队列模块内部使用）。

    用于控制任务装饰器的行为：
    - WORKER: Worker 模式（执行者），正常注册为 actor，执行任务
    - PRODUCER: Producer 模式（生产者），返回 TaskProxy，不注册但可以发送消息
    """

    WORKER = "worker"
    PRODUCER = "producer"


__all__ = [
    "TaskQueueName",
    "TaskRunMode",
]

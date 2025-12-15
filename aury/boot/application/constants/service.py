"""服务类型常量。

定义服务运行模式的枚举。
"""

from __future__ import annotations

from enum import Enum


class ServiceType(str, Enum):
    """服务类型枚举（应用层配置）。

    用于区分不同的服务运行模式：
    - API: 运行 API 服务（可伴随调度器）
    - WORKER: 运行任务队列 Worker
    - SCHEDULER: 仅运行调度器（独立 pod）
    """

    API = "api"
    WORKER = "worker"
    SCHEDULER = "scheduler"


__all__ = [
    "ServiceType",
]



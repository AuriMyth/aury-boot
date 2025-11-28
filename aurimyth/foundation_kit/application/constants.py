"""应用层常量。"""

from __future__ import annotations

from enum import Enum


class ComponentName(str, Enum):
    """组件名称常量。

    所有内置和常用组件的标准命名。
    """

    # 中间件组件
    REQUEST_LOGGING = "request_logging"
    CORS = "cors"

    # 基础设施组件
    DATABASE = "database"
    CACHE = "cache"
    TASK_QUEUE = "task_queue"
    SCHEDULER = "scheduler"

    # 存储组件
    STORAGE = "storage"

    # 迁移组件
    MIGRATIONS = "migrations"


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


class SchedulerMode(str, Enum):
    """调度器运行模式枚举（应用层配置）。

    - EMBEDDED: 伴随 API 运行（默认）
    - STANDALONE: 独立运行
    - DISABLED: 禁用调度器
    """

    EMBEDDED = "embedded"
    STANDALONE = "standalone"
    DISABLED = "disabled"


__all__ = [
    "ComponentName",
    "ServiceType",
    "SchedulerMode",
]


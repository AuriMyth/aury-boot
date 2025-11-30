"""组件名称常量。

定义所有内置和常用组件的标准命名。
"""

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


__all__ = [
    "ComponentName",
]



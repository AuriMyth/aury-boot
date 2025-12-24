"""中间件和组件名称常量。

定义所有内置中间件和组件的标准命名。
"""

from __future__ import annotations

from enum import Enum


class MiddlewareName(str, Enum):
    """中间件名称常量。

    所有内置 HTTP 中间件的标准命名。
    """

    # HTTP 中间件
    REQUEST_LOGGING = "request_logging"
    WEBSOCKET_LOGGING = "websocket_logging"
    CORS = "cors"


class ComponentName(str, Enum):
    """组件名称常量。

    所有内置基础设施组件的标准命名。
    """

    # 基础设施组件
    DATABASE = "database"
    CACHE = "cache"
    TASK_QUEUE = "task_queue"
    SCHEDULER = "scheduler"

    # 存储组件
    STORAGE = "storage"

    # 消息队列组件
    MESSAGE_QUEUE = "message_queue"

    # 事件总线组件
    EVENT_BUS = "event_bus"

    # 迁移组件
    MIGRATIONS = "migrations"

    # 管理后台（可选扩展）
    ADMIN_CONSOLE = "admin_console"


__all__ = [
    "ComponentName",
    "MiddlewareName",
]



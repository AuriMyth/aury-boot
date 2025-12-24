"""应用框架模块。

提供 FoundationApp、Middleware 和 Component 系统。
"""

from .base import Component, FoundationApp, Middleware
from .components import (
    AdminConsoleComponent,
    CacheComponent,
    DatabaseComponent,
    EventBusComponent,
    MessageQueueComponent,
    MigrationComponent,
    SchedulerComponent,
    TaskComponent,
)
from .middlewares import (
    CORSMiddleware,
    RequestLoggingMiddleware,
)

__all__ = [
    # 组件
    "AdminConsoleComponent",
    # 中间件
    "CORSMiddleware",
    "CacheComponent",
    # 基类
    "Component",
    "DatabaseComponent",
    "EventBusComponent",
    # 应用框架
    "FoundationApp",
    "MessageQueueComponent",
    "Middleware",
    "MigrationComponent",
    "RequestLoggingMiddleware",
    "SchedulerComponent",
    "TaskComponent",
]




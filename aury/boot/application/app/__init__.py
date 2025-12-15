"""应用框架模块。

提供 FoundationApp、Middleware 和 Component 系统。
"""

from .base import Component, FoundationApp, Middleware
from .components import (
    AdminConsoleComponent,
    CacheComponent,
    DatabaseComponent,
    MigrationComponent,
    SchedulerComponent,
    TaskComponent,
)
from .middlewares import (
    CORSMiddleware,
    RequestLoggingMiddleware,
)

__all__ = [
    # 应用框架
    "FoundationApp",
    # 基类
    "Component",
    "Middleware",
    # 中间件
    "CORSMiddleware",
    "RequestLoggingMiddleware",
    # 组件
    "AdminConsoleComponent",
    "CacheComponent",
    "DatabaseComponent",
    "MigrationComponent",
    "SchedulerComponent",
    "TaskComponent",
]




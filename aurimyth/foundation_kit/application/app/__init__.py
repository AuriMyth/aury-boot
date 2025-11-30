"""应用框架模块。

提供 FoundationApp 和 Component 系统。
"""

from .base import Component, FoundationApp
from .components import (
    CacheComponent,
    CORSComponent,
    DatabaseComponent,
    RequestLoggingComponent,
    SchedulerComponent,
    TaskComponent,
)

__all__ = [
    "CORSComponent",
    "CacheComponent",
    "Component",
    "DatabaseComponent",
    "FoundationApp",
    "RequestLoggingComponent",
    "SchedulerComponent",
    "TaskComponent",
]




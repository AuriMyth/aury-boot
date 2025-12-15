"""应用层模块。

提供用例编排、配置管理、RPC通信、依赖注入、事务管理和事件系统。
"""

# 事件系统（从 infrastructure 导入 - Event 定义在最底层）
# 事务管理（从 domain 导入）
from aury.boot.domain.transaction import (
    TransactionManager,
    TransactionRequiredError,
    ensure_transaction,
    transactional,
    transactional_context,
)

# 依赖注入容器（从 infrastructure 导入）
from aury.boot.infrastructure.di import Container, Lifetime, Scope, ServiceDescriptor
from aury.boot.infrastructure.events import (
    Event,
    EventBus,
    EventConsumer,
    EventLoggingMiddleware,
    EventMiddleware,
)

from . import interfaces, rpc

# 应用框架、中间件和组件系统
from .app import (
    CacheComponent,
    Component,
    CORSMiddleware,
    DatabaseComponent,
    FoundationApp,
    Middleware,
    MigrationComponent,
    RequestLoggingMiddleware,
    SchedulerComponent,
    TaskComponent,
)
from .config import (
    BaseConfig,
    CacheSettings,
    CORSSettings,
    LogSettings,
    ServerSettings,
)
from .constants import ComponentName, MiddlewareName, SchedulerMode, ServiceType

# HTTP 中间件装饰器
from .middleware import (
    log_request,
)

# 迁移管理
from .migrations import MigrationManager

# 调度器启动器
from .scheduler import run_scheduler, run_scheduler_sync

# 服务器集成
from .server import ApplicationServer, run_app

__all__ = [
    # 配置
    "BaseConfig",
    "CORSSettings",
    "CacheSettings",
    "LogSettings",
    "ServerSettings",
    # 常量
    "ComponentName",
    "MiddlewareName",
    "SchedulerMode",
    "ServiceType",
    # 应用框架
    "FoundationApp",
    # 基类
    "Component",
    "Middleware",
    # 中间件
    "CORSMiddleware",
    "RequestLoggingMiddleware",
    # 组件
    "CacheComponent",
    "DatabaseComponent",
    "MigrationComponent",
    "SchedulerComponent",
    "TaskComponent",
    # 依赖注入容器
    "Container",
    "Lifetime",
    "Scope",
    "ServiceDescriptor",
    # 事件系统
    "Event",
    "EventBus",
    "EventConsumer",
    "EventLoggingMiddleware",
    "EventMiddleware",
    # 迁移
    "MigrationManager",
    # HTTP 中间件装饰器
    "log_request",
    # 事务管理
    "TransactionManager",
    "TransactionRequiredError",
    "ensure_transaction",
    "transactional",
    "transactional_context",
    # RPC通信
    "rpc",
    # 调度器启动器
    "run_scheduler",
    "run_scheduler_sync",
    # 服务器集成
    "ApplicationServer",
    "run_app",
]


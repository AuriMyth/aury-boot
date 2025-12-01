"""应用层模块。

提供用例编排、配置管理、RPC通信、依赖注入、事务管理和事件系统。
"""

# 事件系统（从 infrastructure 导入 - Event 定义在最底层）
# 事务管理（从 domain 导入）
from aurimyth.foundation_kit.domain.transaction import (
    TransactionManager,
    TransactionRequiredError,
    ensure_transaction,
    transactional,
    transactional_context,
)

# 依赖注入容器（从 infrastructure 导入）
from aurimyth.foundation_kit.infrastructure.di import Container, Lifetime, Scope, ServiceDescriptor
from aurimyth.foundation_kit.infrastructure.events import (
    Event,
    EventBus,
    EventConsumer,
    EventLoggingMiddleware,
    EventMiddleware,
)

from . import interfaces, rpc

# 应用框架和组件系统
from .app import (
    CacheComponent,
    Component,
    CORSComponent,
    DatabaseComponent,
    FoundationApp,
    RequestLoggingComponent,
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
from .constants import ComponentName, SchedulerMode, ServiceType

# HTTP 中间件（FastAPI 中间件）
from .middleware import (
    RequestLoggingMiddleware,
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
    "CORSComponent",
    "CORSSettings",
    "CacheComponent",
    "CacheSettings",
    "Component",
    # 常量
    "ComponentName",
    # 依赖注入容器
    "Container",
    "DatabaseComponent",
    # 事件系统
    "Event",
    "EventBus",
    "EventConsumer",
    "EventLoggingMiddleware",
    "EventMiddleware",
    # 应用框架和组件系统
    "FoundationApp",
    "Lifetime",
    "LogSettings",
    # 迁移
    "MigrationManager",
    "RequestLoggingComponent",
    # HTTP 中间件
    "RequestLoggingMiddleware",
    "SchedulerComponent",
    "SchedulerMode",
    "Scope",
    "ServerSettings",
    "ServiceDescriptor",
    "ServiceType",
    "TaskComponent",
    "TransactionManager",
    "TransactionRequiredError",
    "ensure_transaction",
    "log_request",
    # RPC通信
    "rpc",
    # 调度器启动器
    "run_scheduler",
    "run_scheduler_sync",
    # 服务器集成
    "ApplicationServer",
    "run_app",
    # 事务管理
    "transactional",
    "transactional_context",
]


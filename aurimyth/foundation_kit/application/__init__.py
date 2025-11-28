"""应用层模块。

提供用例编排、配置管理、RPC通信、依赖注入、事务管理和事件系统。
"""

# API 接口层
# RPC通信
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
    DatabaseSettings,
    LogSettings,
    ServerSettings,
)

# 依赖注入容器
from .container import Container, Lifetime, Scope, ServiceDescriptor

# 事件系统
from .events import Event, EventBus, EventMiddleware, LoggingMiddleware
from .migrations import MigrationManager

# 调度器启动器
from .scheduler import run_scheduler, run_scheduler_sync

# 事务管理
from .transaction import (
    TransactionManager,
    TransactionRequired,
    ensure_transaction,
    transactional,
    transactional_context,
)

__all__ = [
    # 应用框架和组件系统
    "FoundationApp",
    "Component",
    "RequestLoggingComponent",
    "CORSComponent",
    "DatabaseComponent",
    "CacheComponent",
    "TaskComponent",
    "SchedulerComponent",
    # 配置
    "BaseConfig",
    "DatabaseSettings",
    "CacheSettings",
    "ServerSettings",
    "CORSSettings",
    "LogSettings",
    # 迁移
    "MigrationManager",
    # RPC通信
    "rpc",
    # 依赖注入容器
    "Container",
    "Scope",
    "Lifetime",
    "ServiceDescriptor",
    # 事务管理
    "transactional",
    "transactional_context",
    "TransactionManager",
    "ensure_transaction",
    "TransactionRequired",
    # 事件系统
    "Event",
    "EventBus",
    "EventMiddleware",
    "LoggingMiddleware",
    # 调度器启动器
    "run_scheduler",
    "run_scheduler_sync",
]


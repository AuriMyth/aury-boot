"""领域层模块。

提供领域模型和业务逻辑的基础类，包括：
- ORM 模型基类
- Repository 接口
- Service 模式
- 异常定义
- 事务管理

注意：Event 基类定义在 infrastructure.events 层，不在 domain 层。
使用事件时请直接从 infrastructure 导入。
"""

from .exceptions import CoreException, ModelError, VersionConflictError
from .models import (
    GUID,
    AuditableStateMixin,
    AuditableStateModel,
    Base,
    FullFeaturedModel,
    FullFeaturedUUIDModel,
    IDMixin,
    Model,
    TimestampMixin,
    UUIDAuditableStateModel,
    UUIDMixin,
    UUIDModel,
    VersionedModel,
    VersionedTimestampedModel,
    VersionedUUIDModel,
    VersionMixin,
)
from .repository import (
    IRepository,
    QueryInterceptor,
)
from .service import BaseService
from .transaction import (
    TransactionManager,
    TransactionRequiredError,
    ensure_transaction,
    transactional,
    transactional_context,
)

__all__ = [
    "GUID",
    "AuditableStateMixin",
    "AuditableStateModel",
    # 模型基类
    "Base",
    # Service
    "BaseService",
    # 异常
    "CoreException",
    "FullFeaturedModel",
    "FullFeaturedUUIDModel",
    "IDMixin",
    # Repository (接口)
    "IRepository",
    "Model",
    "ModelError",
    "QueryInterceptor",
    "TimestampMixin",
    "TransactionManager",
    "TransactionRequiredError",
    "UUIDAuditableStateModel",
    "UUIDMixin",
    "UUIDModel",
    "VersionConflictError",
    "VersionMixin",
    "VersionedModel",
    "VersionedTimestampedModel",
    "VersionedUUIDModel",
    "ensure_transaction",
    # Transaction
    "transactional",
    "transactional_context",
]

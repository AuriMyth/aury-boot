"""领域模型模块。

提供 ORM 模型基类、Mixin 和常用组合模型。
"""

from .base import GUID, Base
from .mixins import (
    AuditableStateMixin,
    IDMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)
from .models import (
    AuditableStateModel,
    FullFeaturedModel,
    FullFeaturedUUIDModel,
    IDOnlyModel,
    Model,
    UUIDAuditableStateModel,
    UUIDModel,
    UUIDOnlyModel,
    VersionedModel,
    VersionedTimestampedModel,
    VersionedUUIDModel,
)

__all__ = [
    "GUID",
    "AuditableStateMixin",
    "AuditableStateModel",
    # 基类和类型装饰器
    "Base",
    "FullFeaturedModel",
    "FullFeaturedUUIDModel",
    # Mixins
    "IDMixin",
    "IDOnlyModel",
    # 组合模型
    "Model",
    "TimestampMixin",
    "UUIDAuditableStateModel",
    "UUIDMixin",
    "UUIDModel",
    "UUIDOnlyModel",
    "VersionMixin",
    "VersionedModel",
    "VersionedTimestampedModel",
    "VersionedUUIDModel",
]


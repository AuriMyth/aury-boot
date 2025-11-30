"""常用组合模型。

提供预定义的模型组合，方便直接使用。
"""

from __future__ import annotations

from .base import Base
from .mixins import (
    AuditableStateMixin,
    IDMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


class Model(IDMixin, TimestampMixin, Base):
    """【常用】标准整数主键模型"""

    __abstract__ = True


class AuditableStateModel(IDMixin, TimestampMixin, AuditableStateMixin, Base):
    """【常用】带可审计状态的标准模型（整数主键 + 时间戳 + 软删除）"""

    __abstract__ = True


class UUIDModel(UUIDMixin, TimestampMixin, Base):
    """【常用】UUID 主键模型"""

    __abstract__ = True


class UUIDAuditableStateModel(UUIDMixin, TimestampMixin, AuditableStateMixin, Base):
    """【常用】带可审计状态的 UUID 主键模型（UUID 主键 + 时间戳 + 软删除）"""

    __abstract__ = True


class VersionedModel(IDMixin, VersionMixin, Base):
    """整数主键 + 乐观锁"""

    __abstract__ = True


class VersionedTimestampedModel(IDMixin, TimestampMixin, VersionMixin, Base):
    """整数主键 + 时间戳 + 乐观锁"""

    __abstract__ = True


class VersionedUUIDModel(UUIDMixin, TimestampMixin, VersionMixin, Base):
    """UUID 主键 + 时间戳 + 乐观锁"""

    __abstract__ = True


class FullFeaturedModel(IDMixin, TimestampMixin, AuditableStateMixin, VersionMixin, Base):
    """完整功能：整数主键 + 时间戳 + 可审计状态 + 乐观锁"""

    __abstract__ = True


class FullFeaturedUUIDModel(UUIDMixin, TimestampMixin, AuditableStateMixin, VersionMixin, Base):
    """完整功能：UUID 主键 + 时间戳 + 可审计状态 + 乐观锁"""

    __abstract__ = True


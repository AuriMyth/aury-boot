"""常用组合模型。

提供预定义的模型组合，方便直接使用。

**重要提示**：不要直接继承 Base 类用于 Repository，必须使用下列预定义模型或自己组合 Mixin。
直接使用 Base 会导致缺少 id 等必要字段，Repository 会报错。

可用模型：
- Model: 标准模型（int主键 + 时间戳）
- AuditableStateModel: 标准模型 + 软删除
- UUIDModel: UUID 主键模型（UUID 主键 + 时间戳）
- UUIDAuditableStateModel: UUID 主键模型 + 软删除
- VersionedModel: 乐观锁模型（int主键 + 乐观锁）
- VersionedTimestampedModel: 乐观锁 + 时间戳
- VersionedUUIDModel: UUID 主键 + 乐观锁 + 时间戳
- FullFeaturedModel: 完整功能（int主键 + 时间戳 + 软删除 + 乐观锁）
- FullFeaturedUUIDModel: 完整功能 UUID 版本
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


class IDOnlyModel(IDMixin, Base):
    """纯 int 主键模型（无时间戳，适合关系表）"""

    __abstract__ = True


class UUIDOnlyModel(UUIDMixin, Base):
    """纯 UUID 主键模型（无时间戳，适合关系表）"""

    __abstract__ = True


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


"""领域模型基类 (Refactored for SQLAlchemy 2.0)。

设计理念：
1. 组合优于继承：使用 Mixin 模式，按需组合功能。
2. 类型安全：完全采用 Mapped[] 类型注解。
3. 性能优先：可审计状态采用 BigInteger(0) 方案，适配 MySQL 唯一索引。
"""

from __future__ import annotations

from datetime import datetime
import time
from typing import TYPE_CHECKING
import uuid
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator
from sqlalchemy.types import Uuid as SQLAlchemyUuid

if TYPE_CHECKING:
    from sqlalchemy.sql import Select

# =============================================================================
# 1. 类型装饰器
# =============================================================================


class GUID(TypeDecorator):
    """跨数据库 UUID 类型装饰器。

    自动适配不同数据库：
    - PostgreSQL: 使用原生 UUID 类型
    - 其他数据库: 使用 CHAR(36) 存储字符串格式的 UUID
    """

    impl = PGUUID
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, UUID):
            raise TypeError(f"Expected UUID, got {type(value)}")
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, UUID):
            return value
        return UUID(value)


# =============================================================================
# 2. 核心基类
# =============================================================================


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类"""

    # 自动生成表名逻辑（可选，例如将 UserProfile 转为 user_profile）
    # pass


# =============================================================================
# 3. 功能 Mixins (按需组合)
# =============================================================================


class IDMixin:
    """标准自增主键 Mixin"""

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        sort_order=-1,  # 确保 ID 在 DDL 中排在前面
        comment="主键ID",
    )


class UUIDMixin:
    """UUID 主键 Mixin"""

    id: Mapped[uuid.UUID] = mapped_column(
        SQLAlchemyUuid(as_uuid=True),  # 2.0 会自动适配 PG(uuid) 和 MySQL(char(36))
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-1,
        comment="UUID主键",
    )


class TimestampMixin:
    """创建/更新时间 Mixin"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        sort_order=99,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # 使用数据库层面的更新，比 Python lambda 更准确
        sort_order=99,
        comment="更新时间",
    )


class AuditableStateMixin:
    """可审计状态 Mixin (软删除核心优化版)

    采用 '默认 0' 策略：
    - deleted_at = 0: 未删除
    - deleted_at > 0: 已删除 (Unix 时间戳)

    优势：
    1. 完美支持 MySQL 唯一索引 UNIQUE(email, deleted_at)。
    2. 整数索引查询极快。
    3. 可以记录删除时间（审计支持）。
    """

    deleted_at: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default=text("0"),  # 确保数据库层面默认值也是 0
        index=True,
        comment="删除时间戳(0=未删)",
    )

    @property
    def is_deleted(self) -> bool:
        """判断是否已删除。"""
        return self.deleted_at > 0

    def mark_deleted(self) -> None:
        """标记为已删除。"""
        self.deleted_at = int(time.time())

    def restore(self) -> None:
        """恢复数据。"""
        self.deleted_at = 0

    @classmethod
    def not_deleted(cls) -> Select:
        """返回未删除记录的查询条件（用于 SQLAlchemy 查询）。"""
        from sqlalchemy import select

        return select(cls).where(cls.deleted_at == 0)

    @classmethod
    def with_deleted(cls) -> Select:
        """返回包含已删除记录的查询（用于审计）。"""
        from sqlalchemy import select

        return select(cls)


class VersionMixin:
    """乐观锁版本控制 Mixin"""

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
        comment="乐观锁版本号",
    )

    __mapper_args__ = {
        "version_id_col": "version"  # SQLAlchemy 自动处理乐观锁逻辑
    }


# =============================================================================
# 4. 常用组合 (可选，方便直接使用)
# =============================================================================


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


# =============================================================================
# 5. 使用示例
# =============================================================================

"""
# 示例 1: 定义一个带可审计状态的用户表
from sqlalchemy import String, UniqueConstraint

class User(AuditableStateModel):
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100))
    
    # 建立唯一索引：同一个邮箱同一时间只能有一个未删除账号
    __table_args__ = (
        UniqueConstraint('email', 'deleted_at', name='uk_email_active'),
    )

# 示例 2: 只有 UUID 和 可审计状态，不需要时间戳
class ApiKey(UUIDMixin, AuditableStateMixin, Base):
    __tablename__ = "api_keys"
    key: Mapped[str] = mapped_column(String(64))

# 示例 3: 使用完整功能模型
class Article(FullFeaturedModel):
    __tablename__ = "articles"
    
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(5000))
"""


# =============================================================================
# 6. 导出
# =============================================================================

__all__ = [
    "Base",
    "GUID",
    "IDMixin",
    "UUIDMixin",
    "TimestampMixin",
    "AuditableStateMixin",
    "VersionMixin",
    "Model",
    "AuditableStateModel",
    "UUIDModel",
    "UUIDAuditableStateModel",
    "VersionedModel",
    "VersionedTimestampedModel",
    "VersionedUUIDModel",
    "FullFeaturedModel",
    "FullFeaturedUUIDModel",
]

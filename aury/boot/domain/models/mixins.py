"""模型功能 Mixins。

提供可组合的功能 Mixin，包括主键、时间戳、软删除、乐观锁等。
"""

from __future__ import annotations

from datetime import datetime
import time
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import BigInteger, DateTime, Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid as SQLAlchemyUuid

if TYPE_CHECKING:
    from sqlalchemy.sql import Select


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
        """返回未删除记录的查询条件（用于 SQLAlchemy 查询）。
        
        注意：这是简单的工具方法，仅构建查询对象，不执行查询。
        实际查询应在 Repository 层执行。
        """
        from sqlalchemy import select  # 延迟导入避免循环依赖

        return select(cls).where(cls.deleted_at == 0)

    @classmethod
    def with_deleted(cls) -> Select:
        """返回包含已删除记录的查询（用于审计）。
        
        注意：这是简单的工具方法，仅构建查询对象，不执行查询。
        实际查询应在 Repository 层执行。
        """
        from sqlalchemy import select  # 延迟导入避免循环依赖

        return select(cls)


class VersionMixin:
    """乐观锁版本控制 Mixin。
    
    用于防止并发更新冲突。每次更新时会检查 version 是否一致，
    如果不一致则抛出 VersionConflictError。
    
    工作原理:
    1. 读取记录时获取当前 version
    2. 更新时检查 version 是否与读取时一致
    3. 如果一致，version + 1 并完成更新
    4. 如果不一致，抛出 VersionConflictError
    
    使用场景:
    - 库存管理（防止超卖）
    - 订单状态更新（防止重复支付）
    - 文档编辑（防止覆盖他人修改）
    
    示例:
        class Product(IDMixin, VersionMixin, Base):
            __tablename__ = "products"
            name: Mapped[str]
            stock: Mapped[int]
        
        # 更新时自动检查版本
        product = await repo.get(1)  # version=1
        product.stock -= 1
        await repo.update(product)  # version 自动变为 2
        
        # 并发更新时抛出异常
        # 线程 A: product.version = 1, 准备更新
        # 线程 B: 已经更新，version = 2
        # 线程 A: await repo.update(product) -> VersionConflictError
    
    异常处理:
        from aury.boot.domain.exceptions import VersionConflictError
        
        try:
            await repo.update(product)
        except VersionConflictError as e:
            # 重新加载数据并重试
            product = await repo.get(product.id)
            # ... 重新应用业务逻辑 ...
            await repo.update(product)
    
    注意:
    - 乐观锁适用于读多写少的场景
    - 高并发写入场景建议使用悲观锁 (QueryBuilder.for_update())
    - BaseRepository.update() 已自动支持乐观锁检查
    """

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


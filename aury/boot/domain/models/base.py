"""模型基类和类型装饰器。

提供 SQLAlchemy 2.0 声明式基类和跨数据库类型装饰器。
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

from aury.boot.common.logging import logger

if TYPE_CHECKING:
    pass


class GUID(TypeDecorator):
    """跨数据库 UUID 类型装饰器。

    自动适配不同数据库：
    - PostgreSQL: 使用原生 UUID 类型（需要安装 [pg] 可选依赖）
    - 其他数据库: 使用 CHAR(36) 存储字符串格式的 UUID
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            # PostgreSQL: 使用原生 UUID 类型
            try:
                from sqlalchemy.dialects.postgresql import UUID as PGUUID
                return dialect.type_descriptor(PGUUID(as_uuid=True))
            except ImportError:
                # 如果未安装 PostgreSQL 支持，回退到字符串
                logger.warning(
                    "PostgreSQL UUID 支持需要安装 [pg] 可选依赖："
                    "pip install aury-boot[pg]"
                )
                return dialect.type_descriptor(String(36))
        else:
            # 其他数据库: 使用字符串
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


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类"""

    # 自动生成表名逻辑（可选，例如将 UserProfile 转为 user_profile）
    # pass


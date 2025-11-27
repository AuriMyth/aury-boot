"""ORM 基类定义。"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

# 纯净基类
Base = declarative_base()


class BaseModel(Base):
    """纯净基类，不包含任何字段。"""

    __abstract__ = True


class TimestampedModel(BaseModel):
    """带时间戳和软删除的通用基类。"""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, comment="主键")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    yn = Column(Boolean, default=True, comment="是否有效")


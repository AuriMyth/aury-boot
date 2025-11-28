"""核心层模块。

提供核心业务逻辑的基础类，包括：
- ORM 模型基类
- Repository 模式
- Service 模式
- 异常定义
"""

from .exceptions import CoreException, ModelError, VersionConflictError

# FoundationError 已迁移到 common.exceptions
from .models import Base, BaseModel, TimestampedModel
from .repository import (
    BaseRepository,
    IRepository,
    SimpleRepository,
)
from .service import BaseService

__all__ = [
    # 异常
    "CoreException",
    "ModelError",
    "VersionConflictError",
    # 模型基类
    "Base",
    "BaseModel",
    "TimestampedModel",
    # Repository
    "IRepository",
    "BaseRepository",
    "SimpleRepository",
    # Service
    "BaseService",
]

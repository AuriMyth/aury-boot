"""对象存储系统模块。

支持多种存储后端：
- S3协议存储（AWS S3, MinIO等）
- 本地文件系统
- 可扩展其他存储类型

使用工厂模式，可以轻松切换存储后端。
"""

from .base import (
    IStorage,
    LocalStorage,
    StorageBackend,
    StorageConfig,
    StorageFile,
    StorageManager,
)
from .exceptions import (
    StorageBackendError,
    StorageError,
    StorageNotFoundError,
)
from .factory import StorageFactory
from .s3 import S3Storage

# 注册S3后端
StorageFactory.register("s3", S3Storage)

__all__ = [
    "IStorage",
    "StorageBackend",
    "StorageConfig",
    "StorageFile",
    "StorageFactory",
    "StorageManager",
    "LocalStorage",
    "S3Storage",
    # 异常
    "StorageError",
    "StorageNotFoundError",
    "StorageBackendError",
]


"""对象存储系统模块。

支持多种存储后端：
- S3协议存储（AWS S3, MinIO等）
- 本地文件系统
- 可扩展其他存储类型

使用工厂模式，可以轻松切换存储后端。
"""

from .base import IStorage, LocalStorage, StorageBackend, StorageConfig, StorageFile, StorageManager
from .exceptions import StorageBackendError, StorageError, StorageNotFoundError
from .factory import StorageFactory
from .sts import (
    StorageSTSAction,
    StorageSTSConfig,
    StorageSTSCredentials,
    StorageSTSRequest,
    StorageSTSIssuer,
)

# 延迟导入 S3Storage（可选依赖）
try:
    from .s3 import S3Storage
    # 注册S3后端
    StorageFactory.register("s3", S3Storage)
    # 兼容别名：OSS/COS 通常可按 S3 协议接入
    StorageFactory.register("oss", S3Storage)
    StorageFactory.register("cos", S3Storage)
except ImportError:
    # aioboto3 未安装，S3Storage 不可用
    S3Storage = None  # type: ignore[assignment, misc]

__all__ = [
    "IStorage",
    "LocalStorage",
    "S3Storage",
    "StorageBackend",
    "StorageBackendError",
    "StorageConfig",
    "StorageError",
    "StorageFactory",
    "StorageFile",
    "StorageManager",
    "StorageNotFoundError",
    "StorageSTSAction",
    "StorageSTSConfig",
    "StorageSTSCredentials",
    "StorageSTSRequest",
    "StorageSTSIssuer",
]


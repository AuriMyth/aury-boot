"""对象存储系统模块（统一出口）。

本包基于 aurimyth-storage-sdk 提供的实现，对外暴露统一接口与管理器。
"""

from .base import StorageManager
from .exceptions import StorageBackendError, StorageError, StorageNotFoundError
from .factory import StorageFactory

# 从 SDK 直接导出核心类型
from aurimyth_storage_sdk.storage import (
    IStorage,
    LocalStorage,
    S3Storage,  # 可选依赖，未安装 aws extras 时为 None
    StorageBackend,
    StorageConfig,
    StorageFile,
    UploadResult,
)

__all__ = [
    # SDK 类型
    "IStorage",
    "LocalStorage",
    "S3Storage",
    "StorageBackend",
    "StorageConfig",
    "StorageFile",
    "UploadResult",
    # 管理器与工厂
    "StorageManager",
    "StorageFactory",
    # 异常
    "StorageError",
    "StorageBackendError",
    "StorageNotFoundError",
]


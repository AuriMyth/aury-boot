"""对象存储系统模块（统一出口）。

本包基于 aury-sdk-storage 提供的实现，对外暴露统一接口与管理器。
"""

# 从 SDK 直接导出核心类型
from aury.sdk.storage.storage import (
    COSStorage,  # 可选依赖，未安装 cos extras 时为 None
    IStorage,
    LocalStorage,
    S3Storage,  # 可选依赖，未安装 aws extras 时为 None
    StorageBackend,
    StorageConfig,
    StorageFile,
    StorageType,
    UploadResult,
)

# SDK 工厂（基于 StorageType 枚举）
from aury.sdk.storage.storage import StorageFactory as SDKStorageFactory

from .base import StorageManager
from .exceptions import StorageBackendError, StorageError, StorageNotFoundError

# Boot 工厂（注册机制）
from .factory import StorageFactory

__all__ = [
    # SDK 类型
    "COSStorage",
    "IStorage",
    "LocalStorage",
    "S3Storage",
    "StorageBackend",
    "StorageConfig",
    "StorageFile",
    "StorageType",
    "UploadResult",
    # 工厂
    "SDKStorageFactory",  # SDK 工厂（基于枚举类型）
    "StorageFactory",  # Boot 工厂（注册机制）
    # 异常
    "StorageBackendError",
    "StorageError",
    "StorageNotFoundError",
    # 管理器
    "StorageManager",
]


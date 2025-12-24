"""对象存储系统 - 基于 aury-sdk-storage。

本模块提供 StorageManager 命名多实例管理，内部委托给 aury-sdk-storage 的实现。
"""

from __future__ import annotations

from aury.boot.common.logging import logger
from aury.sdk.storage.storage import (
    IStorage,
    LocalStorage,
    S3Storage,
    StorageBackend,
    StorageConfig,
    StorageFile,
)


class StorageManager:
    """存储管理器（命名多实例）。

    - 仅负责装配具体后端，不读取环境变量
    - 对上层暴露稳定的最小接口
    - 支持多个命名实例，如 source/target 存储

    使用示例:
        # 默认实例
        storage = StorageManager.get_instance()
        await storage.init(config)

        # 命名实例
        source = StorageManager.get_instance("source")
        target = StorageManager.get_instance("target")
    """

    _instances: dict[str, StorageManager] = {}

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._backend: IStorage | None = None
        self._config: StorageConfig | None = None

    @classmethod
    def get_instance(cls, name: str = "default") -> StorageManager:
        """获取指定名称的实例。

        Args:
            name: 实例名称，默认为 "default"

        Returns:
            StorageManager: 存储管理器实例
        """
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]

    @classmethod
    def reset_instance(cls, name: str | None = None) -> None:
        """重置实例（仅用于测试）。

        Args:
            name: 要重置的实例名称。如果为 None，则重置所有实例。

        注意：调用此方法前应先调用 cleanup() 释放资源。
        """
        if name is None:
            cls._instances.clear()
        elif name in cls._instances:
            del cls._instances[name]

    async def initialize(self, config: StorageConfig) -> StorageManager:
        """初始化存储后端（链式调用）。
        
        Args:
            config: 存储配置对象
            
        Returns:
            self: 支持链式调用
        """
        self._config = config
        if config.backend == StorageBackend.LOCAL:
            self._backend = LocalStorage(base_path=config.base_path or "./storage")
        else:
            # S3/COS/OSS/MinIO 统一走 S3Storage
            self._backend = S3Storage(config)
        logger.info(f"存储管理器初始化完成: {config.backend.value}")
        return self

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化。"""
        return self._backend is not None
    
    @property
    def backend(self) -> IStorage:
        if self._backend is None:
            raise RuntimeError("存储管理器未初始化，请先调用 initialize()")
        return self._backend

    async def upload_file(
        self,
        file: StorageFile,
        *,
        bucket_name: str | None = None,
    ) -> str:
        """上传文件并返回 URL。"""
        result = await self.backend.upload_file(file, bucket_name=bucket_name)
        return result.url

    async def upload_files(
        self,
        files: list[StorageFile],
        *,
        bucket_name: str | None = None,
    ) -> list[str]:
        """批量上传文件并返回 URL 列表。"""
        results = await self.backend.upload_files(files, bucket_name=bucket_name)
        return [r.url for r in results]

    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> None:
        await self.backend.delete_file(object_name, bucket_name=bucket_name)

    async def get_file_url(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        return await self.backend.get_file_url(
            object_name, bucket_name=bucket_name, expires_in=expires_in
        )

    async def file_exists(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> bool:
        return await self.backend.file_exists(object_name, bucket_name=bucket_name)

    async def download_file(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> bytes:
        return await self.backend.download_file(object_name, bucket_name=bucket_name)

    async def cleanup(self) -> None:
        if self._backend:
            # SDK 的 IStorage 可能没有 close() 方法
            if hasattr(self._backend, "close"):
                await self._backend.close()
            self._backend = None
            logger.info("存储管理器已清理")

    def __repr__(self) -> str:
        backend_type = self._config.backend.value if self._config else "未初始化"
        return f"<StorageManager backend={backend_type}>"


__all__ = [
    "IStorage",
    "LocalStorage",
    "S3Storage",
    "StorageBackend",
    "StorageConfig",
    "StorageFile",
    "StorageManager",
]

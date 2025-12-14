"""对象存储系统 - 支持多种存储后端。

支持的后端：
- S3协议存储（AWS S3, MinIO等）
- 本地文件系统
- 可扩展其他存储类型

使用工厂模式，可以轻松切换存储后端。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import os
from typing import Any, BinaryIO

from pydantic import BaseModel, Field

from aurimyth.foundation_kit.common.logging import logger


class StorageBackend(str, Enum):
    """存储后端类型。"""
    
    S3 = "s3"  # S3协议存储（AWS S3, MinIO等）
    LOCAL = "local"  # 本地文件系统
    OSS = "oss"  # 对象存储服务（阿里云OSS等，支持S3协议）
    COS = "cos"  # 云对象存储（腾讯云COS等，支持S3协议）


@dataclass
class StorageFile:
    """存储文件对象。"""
    
    object_name: str
    bucket_name: str | None = None
    data: BinaryIO | None = None
    content_type: str | None = None
    metadata: dict[str, str] | None = None


class StorageConfig(BaseModel):
    """存储配置（Pydantic）。"""
    
    backend: StorageBackend = Field(..., description="存储后端类型")
    access_key_id: str | None = Field(None, description="访问密钥ID")
    access_key_secret: str | None = Field(None, description="访问密钥")
    session_token: str | None = Field(None, description="会话令牌（STS临时凭证）")
    endpoint: str | None = Field(None, description="端点URL")
    region: str | None = Field(None, description="区域")
    bucket_name: str | None = Field(None, description="默认桶名")
    base_path: str | None = Field(None, description="基础路径（本地存储）")
    addressing_style: str | None = Field(None, description="S3寻址风格（virtual/path）")
    role_arn: str | None = Field(None, description="STS AssumeRole 的角色ARN（由外部决定何时刷新）")
    role_session_name: str | None = Field(None, description="STS会话名（AssumeRole RoleSessionName）")
    external_id: str | None = Field(None, description="STS ExternalId（可选）")
    sts_endpoint: str | None = Field(None, description="STS端点（可选，私有云/非AWS）")
    sts_region: str | None = Field(None, description="STS区域（可选）")
    sts_duration_seconds: int | None = Field(None, description="AssumeRole DurationSeconds（默认3600）")


class IStorage(ABC):
    """存储接口。
    
    所有存储后端必须实现此接口。
    """
    
    @abstractmethod
    async def upload_file(
        self,
        file: StorageFile,
        *,
        bucket_name: str | None = None,
    ) -> str:
        """上传文件。
        
        Args:
            file: 文件对象
            bucket_name: 桶名（可选，使用默认桶）
            
        Returns:
            str: 文件URL或路径
        """
        pass
    
    @abstractmethod
    async def upload_files(
        self,
        files: list[StorageFile],
        *,
        bucket_name: str | None = None,
    ) -> list[str]:
        """批量上传文件。
        
        Args:
            files: 文件列表
            bucket_name: 桶名（可选）
            
        Returns:
            list[str]: 文件URL列表
        """
        pass
    
    @abstractmethod
    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> None:
        """删除文件。
        
        Args:
            object_name: 对象名
            bucket_name: 桶名（可选）
        """
        pass
    
    @abstractmethod
    async def get_file_url(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        """获取文件URL。
        
        Args:
            object_name: 对象名
            bucket_name: 桶名（可选）
            expires_in: 过期时间（秒，用于生成预签名URL）
            
        Returns:
            str: 文件URL
        """
        pass
    
    @abstractmethod
    async def file_exists(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> bool:
        """检查文件是否存在。
        
        Args:
            object_name: 对象名
            bucket_name: 桶名（可选）
            
        Returns:
            bool: 是否存在
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭连接。"""
        pass


class LocalStorage(IStorage):
    """本地文件系统存储实现。"""
    
    def __init__(self, base_path: str = "./storage"):
        """初始化本地存储。
        
        Args:
            base_path: 基础路径
        """
        self._base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"本地存储初始化: {base_path}")
    
    async def upload_file(
        self,
        file: StorageFile,
        *,
        bucket_name: str | None = None,
    ) -> str:
        """上传文件。"""
        bucket = bucket_name or file.bucket_name or "default"
        bucket_path = os.path.join(self._base_path, bucket)
        os.makedirs(bucket_path, exist_ok=True)
        
        file_path = os.path.join(bucket_path, file.object_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if file.data:
            with open(file_path, "wb") as f:
                f.write(file.data.read())
        
        logger.debug(f"文件上传成功: {file_path}")
        return file_path
    
    async def upload_files(
        self,
        files: list[StorageFile],
        *,
        bucket_name: str | None = None,
    ) -> list[str]:
        """批量上传文件。"""
        return [await self.upload_file(f, bucket_name=bucket_name) for f in files]
    
    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> None:
        """删除文件。"""
        bucket = bucket_name or "default"
        file_path = os.path.join(self._base_path, bucket, object_name)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"文件删除成功: {file_path}")
    
    async def get_file_url(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        """获取文件URL。"""
        bucket = bucket_name or "default"
        file_path = os.path.join(self._base_path, bucket, object_name)
        return f"file://{os.path.abspath(file_path)}"
    
    async def file_exists(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> bool:
        """检查文件是否存在。"""
        bucket = bucket_name or "default"
        file_path = os.path.join(self._base_path, bucket, object_name)
        return os.path.exists(file_path)
    
    async def close(self) -> None:
        """关闭连接（本地存储无需关闭）。"""
        pass


class StorageManager:
    """存储管理器 - 单例模式。
    
    类似CacheManager的设计，提供统一的存储接口。
    """
    
    _instance: StorageManager | None = None
    
    def __init__(self) -> None:
        """私有构造函数。"""
        if StorageManager._instance is not None:
            raise RuntimeError("StorageManager 是单例类，请使用 get_instance() 获取实例")
        
        self._backend: IStorage | None = None
        self._config: dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls) -> StorageManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def init(self, config: StorageConfig) -> None:
        """使用 Pydantic 校验后的 StorageConfig 初始化（SDK 友好）。

        说明：
        - storage 作为可抽离 SDK，不负责“从环境变量读取配置”
        - Application/调用方负责把配置读出来并构造 StorageConfig
        """
        self._config = config.model_dump()
        backend_name = config.backend.value

        backend_kwargs = self._config_to_backend_kwargs(config)

        from .factory import StorageFactory
        self._backend = await StorageFactory.create(backend_name, **backend_kwargs)
        logger.info(f"存储管理器初始化完成: {backend_name}")

    def _config_to_backend_kwargs(self, config: StorageConfig) -> dict[str, Any]:
        """将 StorageConfig 转换为后端构造参数。"""
        if config.backend == StorageBackend.LOCAL:
            return {
                "base_path": config.base_path or "./storage",
            }

        style = config.addressing_style or "virtual"
        if style not in {"virtual", "path"}:
            style = "virtual"

        return {
            "access_key_id": config.access_key_id,
            "access_key_secret": config.access_key_secret,
            "session_token": config.session_token,
            "endpoint": config.endpoint,
            "region": config.region,
            "bucket_name": config.bucket_name,
            "addressing_style": style,
            "role_arn": config.role_arn,
            "role_session_name": config.role_session_name or "aurimyth-storage",
            "external_id": config.external_id,
            "sts_endpoint": config.sts_endpoint,
            "sts_region": config.sts_region,
            "sts_duration_seconds": config.sts_duration_seconds or 3600,
        }
    
    @property
    def backend(self) -> IStorage:
        """获取存储后端。"""
        if self._backend is None:
            raise RuntimeError("存储管理器未初始化，请先调用 init_app()")
        return self._backend
    
    async def upload_file(
        self,
        file: StorageFile,
        *,
        bucket_name: str | None = None,
    ) -> str:
        """上传文件。"""
        return await self.backend.upload_file(file, bucket_name=bucket_name)
    
    async def upload_files(
        self,
        files: list[StorageFile],
        *,
        bucket_name: str | None = None,
    ) -> list[str]:
        """批量上传文件。"""
        return await self.backend.upload_files(files, bucket_name=bucket_name)
    
    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> None:
        """删除文件。"""
        await self.backend.delete_file(object_name, bucket_name=bucket_name)
    
    async def get_file_url(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        """获取文件URL。"""
        return await self.backend.get_file_url(
            object_name,
            bucket_name=bucket_name,
            expires_in=expires_in,
        )
    
    async def file_exists(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> bool:
        """检查文件是否存在。"""
        return await self.backend.file_exists(object_name, bucket_name=bucket_name)
    
    async def cleanup(self) -> None:
        """清理资源。"""
        if self._backend:
            await self._backend.close()
            self._backend = None
            logger.info("存储管理器已清理")
    
    def __repr__(self) -> str:
        """字符串表示。"""
        storage_type = self._config.get("STORAGE_TYPE", "未初始化")
        return f"<StorageManager backend={storage_type}>"


__all__ = [
    "IStorage",
    "LocalStorage",
    "StorageBackend",
    "StorageConfig",
    "StorageFile",
    "StorageManager",
]

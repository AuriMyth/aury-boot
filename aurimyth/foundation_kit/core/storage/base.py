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
from typing import BinaryIO, Dict, List, Optional

from pydantic import BaseModel, Field

from aurimyth.foundation_kit.utils.logging import logger


class StorageBackend(str, Enum):
    """存储后端类型。"""
    
    S3 = "s3"  # S3协议存储（AWS S3, MinIO等）
    LOCAL = "local"  # 本地文件系统
    OSS = "oss"  # 对象存储服务（阿里云OSS等，支持S3协议）
    COS = "cos"  # 云对象存储（腾讯云COS等，支持S3协议）


@dataclass
class StorageFile:
    """存储文件对象。"""
    
    bucket_name: str
    object_name: str
    data: Optional[BinaryIO] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class StorageConfig(BaseModel):
    """存储配置（Pydantic）。"""
    
    backend: StorageBackend = Field(..., description="存储后端类型")
    access_key_id: Optional[str] = Field(None, description="访问密钥ID")
    access_key_secret: Optional[str] = Field(None, description="访问密钥")
    endpoint: Optional[str] = Field(None, description="端点URL")
    region: Optional[str] = Field(None, description="区域")
    bucket_name: Optional[str] = Field(None, description="默认桶名")
    base_path: Optional[str] = Field(None, description="基础路径（本地存储）")


class IStorage(ABC):
    """存储接口。
    
    所有存储后端必须实现此接口。
    """
    
    @abstractmethod
    async def upload_file(
        self,
        file: StorageFile,
        *,
        bucket_name: Optional[str] = None,
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
        files: List[StorageFile],
        *,
        bucket_name: Optional[str] = None,
    ) -> List[str]:
        """批量上传文件。
        
        Args:
            files: 文件列表
            bucket_name: 桶名（可选）
            
        Returns:
            List[str]: 文件URL列表
        """
        pass
    
    @abstractmethod
    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: Optional[str] = None,
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
        bucket_name: Optional[str] = None,
        expires_in: Optional[int] = None,
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
        bucket_name: Optional[str] = None,
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
        import os
        self._base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"本地存储初始化: {base_path}")
    
    async def upload_file(
        self,
        file: StorageFile,
        *,
        bucket_name: Optional[str] = None,
    ) -> str:
        """上传文件。"""
        import os
        
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
        files: List[StorageFile],
        *,
        bucket_name: Optional[str] = None,
    ) -> List[str]:
        """批量上传文件。"""
        return [await self.upload_file(f, bucket_name=bucket_name) for f in files]
    
    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: Optional[str] = None,
    ) -> None:
        """删除文件。"""
        import os
        
        bucket = bucket_name or "default"
        file_path = os.path.join(self._base_path, bucket, object_name)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"文件删除成功: {file_path}")
    
    async def get_file_url(
        self,
        object_name: str,
        *,
        bucket_name: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> str:
        """获取文件URL。"""
        import os
        
        bucket = bucket_name or "default"
        file_path = os.path.join(self._base_path, bucket, object_name)
        return f"file://{os.path.abspath(file_path)}"
    
    async def file_exists(
        self,
        object_name: str,
        *,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """检查文件是否存在。"""
        import os
        
        bucket = bucket_name or "default"
        file_path = os.path.join(self._base_path, bucket, object_name)
        return os.path.exists(file_path)
    
    async def close(self) -> None:
        """关闭连接（本地存储无需关闭）。"""
        pass


class StorageFactory:
    """存储工厂 - 注册机制。
    
    类似缓存工厂的设计，通过注册机制支持多种后端。
    """
    
    _backends: Dict[str, type[IStorage]] = {}
    
    @classmethod
    def register(cls, name: str, backend_class: type[IStorage]) -> None:
        """注册存储后端。
        
        Args:
            name: 后端名称
            backend_class: 后端类
        """
        cls._backends[name] = backend_class
        logger.debug(f"注册存储后端: {name} -> {backend_class.__name__}")
    
    @classmethod
    async def create(cls, backend_name: str, **config) -> IStorage:
        """创建存储实例。
        
        Args:
            backend_name: 后端名称
            **config: 配置参数
            
        Returns:
            IStorage: 存储实例
            
        Raises:
            ValueError: 后端未注册
        """
        if backend_name not in cls._backends:
            available = ", ".join(cls._backends.keys())
            raise ValueError(
                f"存储后端 '{backend_name}' 未注册。"
                f"可用后端: {available}"
            )
        
        backend_class = cls._backends[backend_name]
        instance = backend_class(**config)
        
        # 如果后端需要初始化
        if hasattr(instance, "initialize"):
            await instance.initialize()
        
        logger.info(f"创建存储实例: {backend_name}")
        return instance
    
    @classmethod
    def get_registered(cls) -> List[str]:
        """获取已注册的后端名称。"""
        return list(cls._backends.keys())


# 注册默认后端
StorageFactory.register("local", LocalStorage)
# S3后端在s3.py中注册


class StorageManager:
    """存储管理器 - 单例模式。
    
    类似CacheManager的设计，提供统一的存储接口。
    """
    
    _instance: Optional[StorageManager] = None
    
    def __init__(self) -> None:
        """私有构造函数。"""
        if StorageManager._instance is not None:
            raise RuntimeError("StorageManager 是单例类，请使用 get_instance() 获取实例")
        
        self._backend: Optional[IStorage] = None
        self._config: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls) -> StorageManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def init_app(self, config: Dict[str, Any]) -> None:
        """初始化存储（类似CacheManager）。
        
        Args:
            config: 配置字典
                - STORAGE_TYPE: 存储类型（s3/local）
                - STORAGE_ACCESS_KEY_ID: 访问密钥ID
                - STORAGE_ACCESS_KEY_SECRET: 访问密钥
                - STORAGE_ENDPOINT: 端点URL
                - STORAGE_REGION: 区域
                - STORAGE_BUCKET_NAME: 默认桶名
                - STORAGE_BASE_PATH: 基础路径（本地存储）
        """
        self._config = config.copy()
        storage_type = config.get("STORAGE_TYPE", "local")
        
        # 构建后端配置
        backend_config = self._build_backend_config(storage_type, config)
        
        # 使用工厂创建后端
        self._backend = await StorageFactory.create(storage_type, **backend_config)
        logger.info(f"存储管理器初始化完成: {storage_type}")
    
    def _build_backend_config(self, storage_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """构建后端配置。"""
        backend_config = {}
        
        if storage_type == "s3":
            backend_config["access_key_id"] = config.get("STORAGE_ACCESS_KEY_ID")
            backend_config["access_key_secret"] = config.get("STORAGE_ACCESS_KEY_SECRET")
            backend_config["endpoint"] = config.get("STORAGE_ENDPOINT")
            backend_config["region"] = config.get("STORAGE_REGION")
            backend_config["bucket_name"] = config.get("STORAGE_BUCKET_NAME")
        
        elif storage_type == "local":
            backend_config["base_path"] = config.get("STORAGE_BASE_PATH", "./storage")
        
        return backend_config
    
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
        bucket_name: Optional[str] = None,
    ) -> str:
        """上传文件。"""
        return await self.backend.upload_file(file, bucket_name=bucket_name)
    
    async def upload_files(
        self,
        files: List[StorageFile],
        *,
        bucket_name: Optional[str] = None,
    ) -> List[str]:
        """批量上传文件。"""
        return await self.backend.upload_files(files, bucket_name=bucket_name)
    
    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: Optional[str] = None,
    ) -> None:
        """删除文件。"""
        await self.backend.delete_file(object_name, bucket_name=bucket_name)
    
    async def get_file_url(
        self,
        object_name: str,
        *,
        bucket_name: Optional[str] = None,
        expires_in: Optional[int] = None,
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
        bucket_name: Optional[str] = None,
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
    "StorageBackend",
    "StorageConfig",
    "StorageFile",
    "StorageFactory",
    "StorageManager",
    "LocalStorage",
]

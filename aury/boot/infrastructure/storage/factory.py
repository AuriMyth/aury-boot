"""存储工厂 - 注册机制。

通过注册机制支持多种存储后端。
"""

from __future__ import annotations

from typing import ClassVar

from aury.boot.common.logging import logger
from aury.sdk.storage.storage import IStorage, LocalStorage


class StorageFactory:
    """存储工厂 - 注册机制。
    
    类似缓存工厂的设计，通过注册机制支持多种后端。
    
    使用示例:
        # 注册后端
        StorageFactory.register("local", LocalStorage)
        StorageFactory.register("s3", S3Storage)
        
        # 创建存储实例
        storage = await StorageFactory.create("local", base_path="./storage")
        storage = await StorageFactory.create("s3", access_key_id="...", ...)
    """
    
    _backends: ClassVar[dict[str, type[IStorage]]] = {}
    
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
    def get_registered(cls) -> list[str]:
        """获取已注册的后端名称。"""
        return list(cls._backends.keys())


# 注册默认后端（本地）
StorageFactory.register("local", LocalStorage)
# 说明：S3/COS/OSS 请直接使用 StorageManager + StorageConfig 或 SDK 中的 S3Storage


__all__ = [
    "StorageFactory",
]


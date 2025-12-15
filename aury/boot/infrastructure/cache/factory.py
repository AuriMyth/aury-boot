"""缓存工厂 - 注册机制。

通过注册机制支持多种缓存后端。
"""

from __future__ import annotations

from typing import ClassVar

from aury.boot.common.logging import logger

from .backends import (
    MemcachedCache,
    MemoryCache,
    RedisCache,
)
from .base import ICache


class CacheFactory:
    """缓存工厂 - 注册机制。
    
    类似Flask-Cache的设计，通过注册机制支持多种后端。
    
    使用示例:
        # 注册后端
        CacheFactory.register("redis", RedisCache)
        CacheFactory.register("memory", MemoryCache)
        
        # 创建缓存实例
        cache = await CacheFactory.create("redis", url="redis://localhost:6379")
        cache = await CacheFactory.create("memory", max_size=1000)
    """
    
    _backends: ClassVar[dict[str, type[ICache]]] = {}
    
    @classmethod
    def register(cls, name: str, backend_class: type[ICache]) -> None:
        """注册缓存后端。
        
        Args:
            name: 后端名称
            backend_class: 后端类
        """
        cls._backends[name] = backend_class
        logger.debug(f"注册缓存后端: {name} -> {backend_class.__name__}")
    
    @classmethod
    async def create(cls, backend_name: str, **config) -> ICache:
        """创建缓存实例。
        
        Args:
            backend_name: 后端名称
            **config: 配置参数
            
        Returns:
            ICache: 缓存实例
            
        Raises:
            ValueError: 后端未注册
        """
        if backend_name not in cls._backends:
            available = ", ".join(cls._backends.keys())
            raise ValueError(
                f"缓存后端 '{backend_name}' 未注册。"
                f"可用后端: {available}"
            )
        
        backend_class = cls._backends[backend_name]
        instance = backend_class(**config)
        
        # 如果后端需要初始化
        if hasattr(instance, "initialize"):
            await instance.initialize()
        
        logger.info(f"创建缓存实例: {backend_name}")
        return instance
    
    @classmethod
    def get_registered(cls) -> list[str]:
        """获取已注册的后端名称。"""
        return list(cls._backends.keys())


# 注册默认后端
CacheFactory.register("redis", RedisCache)
CacheFactory.register("memory", MemoryCache)
CacheFactory.register("memcached", MemcachedCache)


__all__ = [
    "CacheFactory",
]


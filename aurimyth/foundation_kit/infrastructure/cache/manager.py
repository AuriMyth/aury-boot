"""缓存管理器 - 单例模式。

提供统一的缓存管理接口。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any, Optional, TypeVar

from aurimyth.foundation_kit.common.logging import logger

# from aurimyth.config import settings  # TODO: 需要从应用配置中获取
from .base import CacheBackend, ICache
from .factory import CacheFactory

T = TypeVar("T")


class CacheManager:
    """缓存管理器 - 单例模式。
    
    类似Flask-Cache的API设计，优雅简洁。
    
    使用示例:
        # 方式1：使用配置字典
        cache = CacheManager.get_instance()
        await cache.init_app({
            "CACHE_TYPE": "redis",
            "CACHE_REDIS_URL": "redis://localhost:6379"
        })
        
        # 方式2：直接指定后端
        await cache.init_app({
            "CACHE_TYPE": "memory",
            "CACHE_MAX_SIZE": 1000
        })
        
        # 使用
        await cache.set("key", "value", expire=60)
        value = await cache.get("key")
    """
    
    _instance: CacheManager | None = None
    
    def __init__(self) -> None:
        """私有构造函数。"""
        if CacheManager._instance is not None:
            raise RuntimeError("CacheManager 是单例类，请使用 get_instance() 获取实例")
        
        self._backend: ICache | None = None
        self._config: dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls) -> CacheManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def init_app(self, config: dict[str, Any]) -> None:
        """初始化缓存（类似Flask-Cache）。
        
        Args:
            config: 配置字典
                - CACHE_TYPE: 缓存类型（redis/memory/memcached）
                - CACHE_REDIS_URL: Redis连接URL
                - CACHE_MAX_SIZE: 内存缓存最大容量
                - CACHE_SERIALIZER: 序列化方式（json/pickle）
                - CACHE_MEMCACHED_SERVERS: Memcached服务器列表
        """
        self._config = config.copy()
        cache_type = config.get("CACHE_TYPE", "redis")
        
        # 构建后端配置
        backend_config = self._build_backend_config(cache_type, config)
        
        # 使用工厂创建后端
        self._backend = await CacheFactory.create(cache_type, **backend_config)
        logger.info(f"缓存管理器初始化完成: {cache_type}")
    
    def _build_backend_config(self, cache_type: str, config: dict[str, Any]) -> dict[str, Any]:
        """构建后端配置。"""
        backend_config = {}
        
        if cache_type == "redis":
            backend_config["url"] = (
                config.get("CACHE_REDIS_URL") or
                config.get("CACHE_URL") or
                None  # TODO: 从应用配置中获取
            )
            if not backend_config["url"]:
                raise ValueError("Redis URL未配置，请设置 CACHE_REDIS_URL")
            
            backend_config["serializer"] = config.get("CACHE_SERIALIZER", "json")
        
        elif cache_type == "memory":
            backend_config["max_size"] = config.get("CACHE_MAX_SIZE", 1000)
        
        elif cache_type == "memcached":
            backend_config["servers"] = config.get("CACHE_MEMCACHED_SERVERS")
            if not backend_config["servers"]:
                raise ValueError("Memcached服务器列表未配置，请设置 CACHE_MEMCACHED_SERVERS")
        
        return backend_config
    
    async def initialize(
        self,
        backend: CacheBackend = CacheBackend.REDIS,
        *,
        url: str | None = None,
        max_size: int = 1000,
        serializer: str = "json",
        servers: list[str] | None = None,
    ) -> None:
        """初始化缓存。
        
        Args:
            backend: 缓存后端类型
            url: Redis连接URL
            max_size: 最大缓存项数
            serializer: 序列化方式
            servers: Memcached服务器列表
        """
        # 转换为配置字典
        config = {"CACHE_TYPE": backend.value}
        
        if backend == CacheBackend.REDIS:
            config["CACHE_REDIS_URL"] = url  # TODO: 从应用配置中获取默认值
            config["CACHE_SERIALIZER"] = serializer
        elif backend == CacheBackend.MEMORY:
            config["CACHE_MAX_SIZE"] = max_size
        elif backend == CacheBackend.MEMCACHED:
            config["CACHE_MEMCACHED_SERVERS"] = servers
        
        await self.init_app(config)
    
    @property
    def backend(self) -> ICache:
        """获取缓存后端。"""
        if self._backend is None:
            raise RuntimeError("缓存管理器未初始化，请先调用 init_app() 或 initialize()")
        return self._backend
    
    @property
    def backend_type(self) -> str:
        """获取当前使用的后端类型。"""
        return self._config.get("CACHE_TYPE", "unknown")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存。"""
        return await self.backend.get(key, default)
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: int | timedelta | None = None,
    ) -> bool:
        """设置缓存。"""
        return await self.backend.set(key, value, expire)
    
    async def delete(self, *keys: str) -> int:
        """删除缓存。"""
        return await self.backend.delete(*keys)
    
    async def exists(self, *keys: str) -> int:
        """检查缓存是否存在。"""
        return await self.backend.exists(*keys)
    
    async def clear(self) -> None:
        """清空所有缓存。"""
        await self.backend.clear()
    
    def cached(
        self,
        expire: int | timedelta | None = None,
        *,
        key_prefix: str = "",
    ) -> Callable:
        """缓存装饰器。
        
        Args:
            expire: 过期时间
            key_prefix: 键前缀
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                # 生成缓存键
                import hashlib
                func_name = f"{func.__module__}.{func.__name__}"
                args_str = str(args) + str(sorted(kwargs.items()))
                key_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{key_prefix}:{func_name}:{key_hash}" if key_prefix else f"{func_name}:{key_hash}"
                
                # 尝试获取缓存
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_value
                
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 存入缓存
                await self.set(cache_key, result, expire)
                logger.debug(f"缓存更新: {cache_key}")
                
                return result
            
            return wrapper
        return decorator
    
    async def cleanup(self) -> None:
        """清理资源。"""
        if self._backend:
            await self._backend.close()
            self._backend = None
            self._backend_type = None
            logger.info("缓存管理器已清理")
    
    def __repr__(self) -> str:
        """字符串表示。"""
        backend_name = self.backend_type if self._backend else "未初始化"
        return f"<CacheManager backend={backend_name}>"


__all__ = [
    "CacheManager",
]


"""缓存管理器 - 命名多实例模式。

提供统一的缓存管理接口。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from functools import wraps
import hashlib
from typing import Any, TypeVar

from aurimyth.foundation_kit.common.logging import logger

# from aurimyth.config import settings  # TODO: 需要从应用配置中获取
from .base import CacheBackend, ICache
from .factory import CacheFactory


class CacheManager:
    """缓存管理器（命名多实例）。
    
    类似Flask-Cache的API设计，优雅简洁。
    支持多个命名实例，如不同的 Redis 实例或缓存策略。
    
    使用示例:
        # 默认实例
        cache = CacheManager.get_instance()
        await cache.init_app({
            "CACHE_TYPE": "redis",
            "CACHE_URL": "redis://localhost:6379"
        })
        
        # 命名实例
        session_cache = CacheManager.get_instance("session")
        rate_limit_cache = CacheManager.get_instance("rate_limit")
        
        # 使用
        await cache.set("key", "value", expire=60)
        value = await cache.get("key")
    """
    
    _instances: dict[str, CacheManager] = {}
    
    def __init__(self, name: str = "default") -> None:
        """初始化缓存管理器。
        
        Args:
            name: 实例名称
        """
        self.name = name
        self._backend: ICache | None = None
        self._config: dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls, name: str = "default") -> CacheManager:
        """获取指定名称的实例。
        
        Args:
            name: 实例名称，默认为 "default"
            
        Returns:
            CacheManager: 缓存管理器实例
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
    
    async def init_app(self, config: dict[str, Any]) -> None:
        """初始化缓存（类似Flask-Cache）。
        
        Args:
            config: 配置字典
                - CACHE_TYPE: 缓存类型（redis/memory/memcached）
                - CACHE_URL: 缓存服务 URL（通用）
                - CACHE_MAX_SIZE: 内存缓存最大容量
                - CACHE_SERIALIZER: 序列化方式（json/pickle）
        """
        self._config = config.copy()
        cache_type = config.get("CACHE_TYPE", "redis")
        
        # 构建后端配置
        backend_config = self._build_backend_config(cache_type, config)
        
        # 使用工厂创建后端
        self._backend = await CacheFactory.create(cache_type, **backend_config)
        logger.info(f"缓存管理器初始化完成: {cache_type}")
    
    def _build_backend_config(self, cache_type: str, config: dict[str, Any]) -> dict[str, Any]:
        """构建后端配置。
        
        使用函数式编程处理配置构建逻辑。
        """
        # 配置构建函数字典（函数式编程）
        config_builders: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "redis": lambda cfg: {
                "url": cfg.get("CACHE_URL"),
                "serializer": cfg.get("CACHE_SERIALIZER", "json"),
            },
            "memory": lambda cfg: {
                "max_size": cfg.get("CACHE_MAX_SIZE", 1000),
            },
            "memcached": lambda cfg: {
                "servers": cfg.get("CACHE_URL"),  # memcached 也用 URL
            },
        }
        
        if cache_type not in config_builders:
            available = ", ".join(config_builders.keys())
            raise ValueError(
                f"不支持的缓存类型: {cache_type}。可用类型: {available}"
            )
        
        builder = config_builders[cache_type]
        backend_config = builder(config)
        
        # 验证必需配置
        if cache_type == "redis" and not backend_config.get("url"):
            raise ValueError("缓存 URL 未配置，请设置 CACHE_URL")
        if cache_type == "memcached" and not backend_config.get("servers"):
            raise ValueError("缓存 URL 未配置，请设置 CACHE_URL")
        
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
        # 转换为配置字典（使用函数式编程）
        backend_config_map: dict[CacheBackend, Callable[[], dict[str, Any]]] = {
            CacheBackend.REDIS: lambda: {
                "CACHE_TYPE": backend.value,
                "CACHE_REDIS_URL": url,  # TODO: 从应用配置中获取默认值
                "CACHE_SERIALIZER": serializer,
            },
            CacheBackend.MEMORY: lambda: {
                "CACHE_TYPE": backend.value,
                "CACHE_MAX_SIZE": max_size,
            },
            CacheBackend.MEMCACHED: lambda: {
                "CACHE_TYPE": backend.value,
                "CACHE_MEMCACHED_SERVERS": servers,
            },
        }
        
        config_builder = backend_config_map.get(backend)
        if config_builder is None:
            raise ValueError(f"不支持的缓存后端: {backend}")
        
        config = config_builder()
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
    
    def cached[T](
        self,
        expire: int | timedelta | None = None,
        *,
        key_prefix: str = "",
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """缓存装饰器。
        
        Args:
            expire: 过期时间
            key_prefix: 键前缀
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                # 生成缓存键
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
            logger.info("缓存管理器已清理")
    
    def __repr__(self) -> str:
        """字符串表示。"""
        backend_name = self.backend_type if self._backend else "未初始化"
        return f"<CacheManager backend={backend_name}>"


__all__ = [
    "CacheManager",
]


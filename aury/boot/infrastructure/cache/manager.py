"""缓存管理器 - 命名多实例模式。

提供统一的缓存管理接口。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from functools import wraps
import hashlib
from typing import Any, TypeVar

from aury.boot.common.logging import logger

# from aury.boot.config import settings  # TODO: 需要从应用配置中获取
from .base import CacheBackend, ICache
from .factory import CacheFactory


class CacheManager:
    """缓存管理器（命名多实例）。
    
    支持多个命名实例，如不同的 Redis 实例或缓存策略。
    
    使用示例:
        # 默认实例
        cache = CacheManager.get_instance()
        await cache.initialize(backend="redis", url="redis://localhost:6379")
        
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
    
    async def initialize(
        self,
        backend: CacheBackend | str = CacheBackend.REDIS,
        *,
        url: str | None = None,
        max_size: int = 1000,
        serializer: str = "json",
        servers: list[str] | None = None,
    ) -> CacheManager:
        """初始化缓存（链式调用）。
        
        Args:
            backend: 缓存后端类型（redis/memory/memcached）
            url: Redis/Memcached 连接 URL
            max_size: 内存缓存最大容量（仅 memory 后端）
            serializer: 序列化方式（json/pickle）
            servers: Memcached 服务器列表（已弃用，请使用 url）
            
        Returns:
            self: 支持链式调用
        """
        if self._backend is not None:
            logger.warning(f"缓存管理器 [{self.name}] 已初始化，跳过")
            return self
        
        # 处理字符串类型的 backend
        if isinstance(backend, str):
            try:
                backend = CacheBackend(backend.lower())
            except ValueError:
                supported = ", ".join(b.value for b in CacheBackend)
                raise ValueError(f"不支持的缓存后端: {backend}。支持: {supported}")
        
        # 保存配置
        self._config = {"CACHE_TYPE": backend.value}
        
        # 根据后端类型构建配置并创建后端
        if backend == CacheBackend.REDIS:
            if not url:
                raise ValueError("Redis 缓存需要提供 url 参数")
            self._backend = await CacheFactory.create(
                "redis", url=url, serializer=serializer
            )
        elif backend == CacheBackend.MEMORY:
            self._backend = await CacheFactory.create(
                "memory", max_size=max_size
            )
        elif backend == CacheBackend.MEMCACHED:
            cache_url = url or (servers[0] if servers else None)
            if not cache_url:
                raise ValueError("Memcached 缓存需要提供 url 参数")
            self._backend = await CacheFactory.create(
                "memcached", servers=cache_url
            )
        else:
            supported = ", ".join(b.value for b in CacheBackend)
            raise ValueError(f"不支持的缓存后端: {backend}。支持: {supported}")
        
        logger.info(f"缓存管理器 [{self.name}] 初始化完成: {backend.value}")
        return self
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化。"""
        return self._backend is not None
    
    @property
    def backend(self) -> ICache:
        """获取缓存后端。"""
        if self._backend is None:
            raise RuntimeError("缓存管理器未初始化，请先调用 initialize()")
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
    
    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存。
        
        Args:
            pattern: 通配符模式，如 "todo:*" 或 "api:todo:list:*"
            
        Returns:
            int: 删除的键数量
            
        示例:
            # 删除所有 todo 相关缓存
            await cache.delete_pattern("todo:*")
            
            # 删除所有列表缓存
            await cache.delete_pattern("api:todo:list:*")
        """
        return await self.backend.delete_pattern(pattern)
    
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
    
    def cache_response[T](
        self,
        expire: int | timedelta | None = 300,
        *,
        key_builder: Callable[..., str] | None = None,
        key_prefix: str = "api",
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """API 响应缓存装饰器。
        
        专为 FastAPI 路由设计，自动从路径参数和查询参数生成缓存键。
        
        Args:
            expire: 过期时间（秒），默认 300 秒
            key_builder: 自定义缓存键生成函数，接收与被装饰函数相同的参数
            key_prefix: 缓存键前缀，默认 "api"
            
        示例:
            cache = CacheManager.get_instance()
            
            # 基本用法：自动生成缓存键
            @router.get("/todos/{{id}}")
            @cache.cache_response(expire=300)
            async def get_todo(id: UUID):
                return await service.get(id)
            # 缓存键: api:get_todo:<hash>
            
            # 自定义缓存键
            @router.get("/todos/{{id}}")
            @cache.cache_response(
                expire=300,
                key_builder=lambda id: f"todo:{{id}}"
            )
            async def get_todo(id: UUID):
                return await service.get(id)
            # 缓存键: api:todo:<id>
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                # 生成缓存键
                if key_builder:
                    # 使用自定义的 key_builder
                    custom_key = key_builder(*args, **kwargs)
                    cache_key = f"{key_prefix}:{custom_key}" if key_prefix else custom_key
                else:
                    # 自动生成：函数名 + 参数哈希
                    func_name = func.__name__
                    args_str = str(args) + str(sorted(kwargs.items()))
                    key_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                    cache_key = f"{key_prefix}:{func_name}:{key_hash}"
                
                # 尝试从缓存获取
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"API 缓存命中: {cache_key}")
                    return cached_value
                
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 存入缓存（尝试序列化）
                try:
                    # 如果结果有 model_dump 方法（Pydantic model），先序列化
                    if hasattr(result, "model_dump"):
                        cache_data = result.model_dump()
                    elif hasattr(result, "dict"):
                        cache_data = result.dict()
                    else:
                        cache_data = result
                    
                    await self.set(cache_key, cache_data, expire)
                    logger.debug(f"API 缓存更新: {cache_key}")
                except Exception as e:
                    logger.warning(f"API 缓存存储失败: {cache_key}, {e}")
                
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


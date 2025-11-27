"""缓存系统 - 支持多种缓存后端。

支持的后端类型：
- Redis
- Memory（内存）
- Memcached（可选）
- 可扩展其他类型

使用策略模式，可以轻松切换缓存后端。
"""

from __future__ import annotations

import asyncio
import json
import pickle
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import timedelta
from enum import Enum
from functools import wraps
from typing import Any, AsyncGenerator, Callable, Dict, Optional, TypeVar, Union

from redis.asyncio import Redis

from aurimyth.config import settings
from aurimyth.foundation_kit.utils.logging import logger

T = TypeVar("T")


class CacheBackend(str, Enum):
    """缓存后端类型。"""
    
    REDIS = "redis"
    MEMORY = "memory"
    MEMCACHED = "memcached"


class ICache(ABC):
    """缓存接口。
    
    所有缓存后端必须实现此接口。
    """
    
    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存。"""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """设置缓存。"""
        pass
    
    @abstractmethod
    async def delete(self, *keys: str) -> int:
        """删除缓存。"""
        pass
    
    @abstractmethod
    async def exists(self, *keys: str) -> int:
        """检查缓存是否存在。"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """清空所有缓存。"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭连接。"""
        pass


class RedisCache(ICache):
    """Redis缓存实现。"""
    
    def __init__(self, url: str, *, serializer: str = "json"):
        """初始化Redis缓存。
        
        Args:
            url: Redis连接URL
            serializer: 序列化方式（json/pickle）
        """
        self._url = url
        self._serializer = serializer
        self._redis: Optional[Redis] = None
    
    async def initialize(self) -> None:
        """初始化连接。"""
        try:
            self._redis = Redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self._redis.ping()
            logger.info("Redis缓存初始化成功")
        except Exception as exc:
            logger.error(f"Redis连接失败: {exc}")
            raise
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存。"""
        if not self._redis:
            return default
        
        try:
            data = await self._redis.get(key)
            if data is None:
                return default
            
            if self._serializer == "json":
                return json.loads(data.decode())
            elif self._serializer == "pickle":
                return pickle.loads(data)
            else:
                return data.decode()
        except Exception as exc:
            logger.error(f"Redis获取失败: {key}, {exc}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """设置缓存。"""
        if not self._redis:
            return False
        
        try:
            # 序列化
            if self._serializer == "json":
                data = json.dumps(value).encode()
            elif self._serializer == "pickle":
                data = pickle.dumps(value)
            else:
                data = str(value).encode()
            
            # 转换过期时间
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
            
            await self._redis.set(key, data, ex=expire)
            return True
        except Exception as exc:
            logger.error(f"Redis设置失败: {key}, {exc}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """删除缓存。"""
        if not self._redis or not keys:
            return 0
        
        try:
            return await self._redis.delete(*keys)
        except Exception as exc:
            logger.error(f"Redis删除失败: {keys}, {exc}")
            return 0
    
    async def exists(self, *keys: str) -> int:
        """检查缓存是否存在。"""
        if not self._redis or not keys:
            return 0
        
        try:
            return await self._redis.exists(*keys)
        except Exception as exc:
            logger.error(f"Redis检查失败: {keys}, {exc}")
            return 0
    
    async def clear(self) -> None:
        """清空所有缓存。"""
        if self._redis:
            await self._redis.flushdb()
            logger.info("Redis缓存已清空")
    
    async def close(self) -> None:
        """关闭连接。"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis连接已关闭")
    
    @property
    def redis(self) -> Optional[Redis]:
        """获取Redis客户端。"""
        return self._redis


class MemoryCache(ICache):
    """内存缓存实现。"""
    
    def __init__(self, max_size: int = 1000):
        """初始化内存缓存。
        
        Args:
            max_size: 最大缓存项数
        """
        self._max_size = max_size
        self._cache: Dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存。"""
        async with self._lock:
            if key not in self._cache:
                return default
            
            value, expire_at = self._cache[key]
            
            # 检查过期
            if expire_at is not None and asyncio.get_event_loop().time() > expire_at:
                del self._cache[key]
                return default
            
            return value
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """设置缓存。"""
        async with self._lock:
            # 转换过期时间
            expire_at = None
            if expire:
                if isinstance(expire, timedelta):
                    expire_seconds = expire.total_seconds()
                else:
                    expire_seconds = expire
                expire_at = asyncio.get_event_loop().time() + expire_seconds
            
            # 如果超出容量，删除最旧的
            if len(self._cache) >= self._max_size and key not in self._cache:
                # 简单策略：删除第一个
                first_key = next(iter(self._cache))
                del self._cache[first_key]
            
            self._cache[key] = (value, expire_at)
            return True
    
    async def delete(self, *keys: str) -> int:
        """删除缓存。"""
        async with self._lock:
            count = 0
            for key in keys:
                if key in self._cache:
                    del self._cache[key]
                    count += 1
            return count
    
    async def exists(self, *keys: str) -> int:
        """检查缓存是否存在。"""
        async with self._lock:
            count = 0
            for key in keys:
                if key in self._cache:
                    value, expire_at = self._cache[key]
                    # 检查是否过期
                    if expire_at is None or asyncio.get_event_loop().time() <= expire_at:
                        count += 1
            return count
    
    async def clear(self) -> None:
        """清空所有缓存。"""
        async with self._lock:
            self._cache.clear()
            logger.info("内存缓存已清空")
    
    async def close(self) -> None:
        """关闭连接（内存缓存无需关闭）。"""
        await self.clear()
    
    async def size(self) -> int:
        """获取缓存大小。"""
        return len(self._cache)


class MemcachedCache(ICache):
    """Memcached缓存实现（可选）。"""
    
    def __init__(self, servers: list[str]):
        """初始化Memcached缓存。
        
        Args:
            servers: Memcached服务器列表，如 ["127.0.0.1:11211"]
        """
        self._servers = servers
        self._client = None
    
    async def initialize(self) -> None:
        """初始化连接。"""
        try:
            # 需要安装 python-memcached 或 aiomcache
            try:
                import aiomcache
                self._client = aiomcache.Client(
                    self._servers[0].split(":")[0],
                    int(self._servers[0].split(":")[1]) if ":" in self._servers[0] else 11211,
                )
                logger.info("Memcached缓存初始化成功")
            except ImportError:
                logger.error("请安装 aiomcache: pip install aiomcache")
                raise
        except Exception as exc:
            logger.error(f"Memcached连接失败: {exc}")
            raise
    
    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存。"""
        if not self._client:
            return default
        
        try:
            data = await self._client.get(key.encode())
            if data is None:
                return default
            return json.loads(data.decode())
        except Exception as exc:
            logger.error(f"Memcached获取失败: {key}, {exc}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """设置缓存。"""
        if not self._client:
            return False
        
        try:
            if isinstance(expire, timedelta):
                expire = int(expire.total_seconds())
            
            data = json.dumps(value).encode()
            return await self._client.set(key.encode(), data, exptime=expire or 0)
        except Exception as exc:
            logger.error(f"Memcached设置失败: {key}, {exc}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """删除缓存。"""
        if not self._client or not keys:
            return 0
        
        count = 0
        for key in keys:
            try:
                if await self._client.delete(key.encode()):
                    count += 1
            except Exception as exc:
                logger.error(f"Memcached删除失败: {key}, {exc}")
        return count
    
    async def exists(self, *keys: str) -> int:
        """检查缓存是否存在。"""
        if not self._client or not keys:
            return 0
        
        count = 0
        for key in keys:
            try:
                if await self._client.get(key.encode()) is not None:
                    count += 1
            except Exception:
                pass
        return count
    
    async def clear(self) -> None:
        """清空所有缓存（Memcached不支持）。"""
        logger.warning("Memcached不支持清空所有缓存")
    
    async def close(self) -> None:
        """关闭连接。"""
        if self._client:
            self._client.close()
            logger.info("Memcached连接已关闭")


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
    
    _backends: Dict[str, type[ICache]] = {}
    
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
    
    _instance: Optional[CacheManager] = None
    
    def __init__(self) -> None:
        """私有构造函数。"""
        if CacheManager._instance is not None:
            raise RuntimeError("CacheManager 是单例类，请使用 get_instance() 获取实例")
        
        self._backend: Optional[ICache] = None
        self._config: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls) -> CacheManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def init_app(self, config: Dict[str, Any]) -> None:
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
    
    def _build_backend_config(self, cache_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """构建后端配置。"""
        backend_config = {}
        
        if cache_type == "redis":
            backend_config["url"] = (
                config.get("CACHE_REDIS_URL") or
                config.get("CACHE_URL") or
                settings.redis_url
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
        url: Optional[str] = None,
        max_size: int = 1000,
        serializer: str = "json",
        servers: Optional[list[str]] = None,
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
            config["CACHE_REDIS_URL"] = url or settings.redis_url
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
        expire: Optional[Union[int, timedelta]] = None,
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
        expire: Optional[Union[int, timedelta]] = None,
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
    "CacheFactory",
    "CacheBackend",
    "ICache",
    "RedisCache",
    "MemoryCache",
    "MemcachedCache",
]

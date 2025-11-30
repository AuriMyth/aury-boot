"""缓存后端实现。

提供 Redis、Memory、Memcached 等缓存后端的实现。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import timedelta
import json
import pickle
from typing import Any

from redis.asyncio import Redis

from aurimyth.foundation_kit.common.logging import logger

from .base import ICache


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
        self._redis: Redis | None = None
    
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
            
            # 使用函数式编程处理序列化器
            deserializers: dict[str, Callable[[bytes], Any]] = {
                "json": lambda d: json.loads(d.decode()),
                "pickle": pickle.loads,
            }
            
            deserializer = deserializers.get(self._serializer)
            if deserializer:
                return deserializer(data)
            return data.decode()
        except Exception as exc:
            logger.error(f"Redis获取失败: {key}, {exc}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: int | timedelta | None = None,
    ) -> bool:
        """设置缓存。"""
        if not self._redis:
            return False
        
        try:
            # 使用函数式编程处理序列化器
            serializers: dict[str, Callable[[Any], bytes]] = {
                "json": lambda v: json.dumps(v).encode(),
                "pickle": pickle.dumps,
            }
            
            serializer = serializers.get(self._serializer)
            if serializer:
                data = serializer(value)
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
    def redis(self) -> Redis | None:
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
        self._cache: dict[str, tuple[Any, float | None]] = {}
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
        expire: int | timedelta | None = None,
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
                    _value, expire_at = self._cache[key]
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
        expire: int | timedelta | None = None,
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


__all__ = [
    "MemcachedCache",
    "MemoryCache",
    "RedisCache",
]


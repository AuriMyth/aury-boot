"""内存和 Memcached 缓存后端实现。"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import time
from datetime import timedelta
from typing import Any

from aury.boot.common.logging import logger

from .base import ICache


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
    
    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存。
        
        Args:
            pattern: 通配符模式，支持 * 和 ?
            
        Returns:
            int: 删除的键数量
        """
        async with self._lock:
            keys_to_delete = [
                key for key in self._cache
                if fnmatch.fnmatch(key, pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
            logger.debug(f"按模式删除缓存: {pattern}, 删除 {len(keys_to_delete)} 个键")
            return len(keys_to_delete)
    
    async def close(self) -> None:
        """关闭连接（内存缓存无需关闭）。"""
        await self.clear()
    
    async def size(self) -> int:
        """获取缓存大小。"""
        return len(self._cache)
    
    # ==================== 内存锁 ====================
    
    async def acquire_lock(
        self,
        key: str,
        token: str,
        timeout: int,
        blocking: bool,
        blocking_timeout: float | None,
    ) -> bool:
        """获取内存锁（单进程）。"""
        start_time = time.monotonic()
        
        while True:
            async with self._lock:
                # 检查锁是否存在
                if key not in self._cache:
                    # 设置锁
                    expire_at = asyncio.get_event_loop().time() + timeout
                    self._cache[key] = (token, expire_at)
                    return True
                
                # 检查锁是否过期
                existing_token, expire_at = self._cache[key]
                if expire_at is not None and asyncio.get_event_loop().time() > expire_at:
                    # 锁已过期，重新获取
                    new_expire_at = asyncio.get_event_loop().time() + timeout
                    self._cache[key] = (token, new_expire_at)
                    return True
            
            if not blocking:
                return False
            
            # 检查是否超时
            if blocking_timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= blocking_timeout:
                    return False
            
            # 短暂等待后重试
            await asyncio.sleep(0.05)
    
    async def release_lock(self, key: str, token: str) -> bool:
        """释放内存锁。"""
        async with self._lock:
            if key not in self._cache:
                return False
            
            existing_token, _ = self._cache[key]
            if existing_token == token:
                del self._cache[key]
                return True
            return False


class MemcachedCache(ICache):
    """Memcached缓存实现（可选）。"""
    
    def __init__(self, servers: list[str]):
        """初始化Memcached缓存。
        
        Args:
            servers: Memcached服务器列表，如 ["*********:11211"]
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
    
    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存（Memcached 不支持）。"""
        logger.warning("Memcached 不支持模式删除，请使用 Redis 或 Memory 后端")
        return 0
    
    async def close(self) -> None:
        """关闭连接。"""
        if self._client:
            self._client.close()
            logger.info("Memcached连接已关闭")
    
    # Memcached 不支持分布式锁
    async def acquire_lock(
        self,
        key: str,
        token: str,
        timeout: int,
        blocking: bool,
        blocking_timeout: float | None,
    ) -> bool:
        """获取锁（Memcached 不支持）。"""
        logger.warning("Memcached 不支持分布式锁，请使用 Redis 或 Memory 后端")
        return False
    
    async def release_lock(self, key: str, token: str) -> bool:
        """释放锁（Memcached 不支持）。"""
        return False


__all__ = ["MemcachedCache", "MemoryCache"]

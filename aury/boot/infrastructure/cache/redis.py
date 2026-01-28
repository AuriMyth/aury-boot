"""Redis 缓存后端实现。"""

from __future__ import annotations

import asyncio
import json
import pickle
import time
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from redis.asyncio import Redis

from aury.boot.common.logging import logger

from .base import ICache

if TYPE_CHECKING:
    from aury.boot.infrastructure.clients.redis import RedisClient


class RedisCache(ICache):
    """Redis缓存实现。
    
    支持两种初始化方式：
    1. 传入 URL 自行创建连接
    2. 传入 RedisClient 实例（推荐）
    """
    
    def __init__(
        self,
        url: str | None = None,
        *,
        redis_client: RedisClient | None = None,
        serializer: str = "json",
    ):
        """初始化Redis缓存。
        
        Args:
            url: Redis连接URL
            redis_client: RedisClient 实例（推荐）
            serializer: 序列化方式（json/pickle）
        """
        self._url = url
        self._redis_client = redis_client
        self._serializer = serializer
        self._redis: Redis | None = None
        self._owns_connection = False  # 是否自己拥有连接（需要自己关闭）
    
    async def initialize(self) -> None:
        """初始化连接。"""
        # 优先使用 RedisClient
        if self._redis_client is not None:
            self._redis = self._redis_client.connection
            self._owns_connection = False
            logger.info("Redis缓存初始化成功（使用 RedisClient）")
            return
        
        # 使用 URL 创建连接
        if self._url:
            try:
                self._redis = Redis.from_url(
                    self._url,
                    encoding="utf-8",
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                await self._redis.ping()
                self._owns_connection = True
                logger.info("Redis缓存初始化成功")
            except Exception as exc:
                logger.error(f"Redis连接失败: {exc}")
                raise
        else:
            raise ValueError("Redis缓存需要提供 url 或 redis_client 参数")
    
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
    
    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存。
        
        Args:
            pattern: 通配符模式，如 "todo:*"
            
        Returns:
            int: 删除的键数量
        """
        if not self._redis:
            return 0
        
        try:
            # 使用 SCAN 遍历匹配的键（比 KEYS 更安全，不会阻塞）
            count = 0
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    count += await self._redis.delete(*keys)
                if cursor == 0:
                    break
            logger.debug(f"按模式删除缓存: {pattern}, 删除 {count} 个键")
            return count
        except Exception as exc:
            logger.error(f"Redis模式删除失败: {pattern}, {exc}")
            return 0
    
    async def close(self) -> None:
        """关闭连接（仅当自己拥有连接时）。"""
        if self._redis and self._owns_connection:
            await self._redis.close()
            logger.info("Redis连接已关闭")
        self._redis = None
    
    @property
    def redis(self) -> Redis | None:
        """获取Redis客户端。"""
        return self._redis
    
    # ==================== 分布式锁 ====================
    # TODO: 后续优化考虑：
    #   - 看门狗（Watchdog）机制：自动续期，防止业务执行超过锁超时导致提前释放
    #   - 可重入锁（Reentrant Lock）
    #   - Redlock 算法（多 Redis 实例）
    
    async def acquire_lock(
        self,
        key: str,
        token: str,
        timeout: int,
        blocking: bool,
        blocking_timeout: float | None,
    ) -> bool:
        """获取 Redis 分布式锁。"""
        if not self._redis:
            return False
        
        start_time = time.monotonic()
        
        while True:
            # SET NX EX 原子操作
            acquired = await self._redis.set(key, token, nx=True, ex=timeout)
            if acquired:
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
        """释放 Redis 锁（Lua 脚本保证原子性）。"""
        if not self._redis:
            return False
        
        # Lua 脚本：只有 token 匹配才删除
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self._redis.eval(script, 1, key, token)
        return bool(result)


__all__ = ["RedisCache"]

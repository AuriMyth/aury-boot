"""查询优化工具。

提供缓存和性能监控装饰器。
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import hashlib
import time

from aury.boot.common.logging import logger

# 查询性能监控配置
QUERY_SLOW_THRESHOLD = 1.0  # 慢查询阈值（秒）


def cache_query(
    ttl: int = 300,
    key_prefix: str = "",
    key_func: Callable | None = None,
) -> Callable:
    """查询结果缓存装饰器。
    
    缓存查询结果，减少数据库访问。
    集成现有的 CacheManager。
    
    Args:
        ttl: 缓存过期时间（秒），默认 300 秒
        key_prefix: 缓存键前缀
        key_func: 自定义缓存键生成函数
    
    用法:
        class UserRepository(BaseRepository):
            @cache_query(ttl=600, key_prefix="user")
            async def get_by_email(self, email: str):
                return await self.get_by(email=email)
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                from aury.boot.infrastructure.cache import CacheManager
                
                cache = CacheManager.get_instance()
                
                # 生成缓存键
                if key_func:
                    cache_key = key_func(self, *args, **kwargs)
                else:
                    # 默认缓存键生成策略
                    key_parts = [key_prefix, func.__name__]
                    if args:
                        key_parts.extend(str(arg) for arg in args)
                    if kwargs:
                        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                    
                    # 使用 MD5 生成固定长度的键
                    key_str = ":".join(str(p) for p in key_parts)
                    cache_key = f"repo:{hashlib.md5(key_str.encode()).hexdigest()}"
                
                # 尝试从缓存获取
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_result
                
                # 执行查询
                result = await func(self, *args, **kwargs)
                
                # 存入缓存
                await cache.set(cache_key, result, expire=ttl)
                logger.debug(f"缓存写入: {cache_key}, TTL={ttl}s")
                
                return result
            except Exception as e:
                # 缓存失败不影响主流程
                logger.warning(f"查询缓存失败: {e}，继续执行查询")
                return await func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator


def monitor_query(
    slow_threshold: float = QUERY_SLOW_THRESHOLD,
    enable_explain: bool = False,
) -> Callable:
    """查询性能监控装饰器。
    
    监控查询执行时间，记录慢查询日志。
    支持 SQLAlchemy explain() 功能。
    
    Args:
        slow_threshold: 慢查询阈值（秒），默认 1.0 秒
        enable_explain: 是否启用查询计划分析
    
    用法:
        class UserRepository(BaseRepository):
            @monitor_query(slow_threshold=0.5)
            async def list(self, **filters):
                return await super().list(**filters)
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            
            try:
                # 执行查询
                result = await func(self, *args, **kwargs)
                
                # 计算执行时间
                duration = time.time() - start_time
                
                # 记录慢查询
                if duration >= slow_threshold:
                    logger.warning(
                        f"慢查询检测: {func.__name__} 执行时间 {duration:.3f}s "
                        f"(阈值: {slow_threshold}s)"
                    )
                    
                    # 如果启用 explain，尝试获取查询计划
                    if enable_explain and hasattr(self, "_last_query"):
                        try:
                            from sqlalchemy import text
                            explain_result = await self._session.execute(
                                text(f"EXPLAIN {self._last_query!s}")
                            )
                            explain_text = "\n".join(str(row) for row in explain_result)
                            logger.debug(f"查询计划:\n{explain_text}")
                        except Exception as e:
                            logger.debug(f"无法获取查询计划: {e}")
                
                # 记录正常查询（调试级别）
                else:
                    logger.debug(
                        f"查询执行: {func.__name__} 耗时 {duration:.3f}s"
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"查询失败: {func.__name__} 执行时间 {duration:.3f}s, 错误: {e}"
                )
                raise
        
        return wrapper
    
    return decorator


__all__ = [
    "cache_query",
    "monitor_query",
]




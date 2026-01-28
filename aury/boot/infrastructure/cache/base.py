"""缓存系统基础接口和类型定义。

提供缓存接口和枚举类型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import Any


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
        expire: int | timedelta | None = None,
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
    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存。
        
        Args:
            pattern: 通配符模式，如 "todo:*" 或 "api:todo:list:*"
            
        Returns:
            int: 删除的键数量
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭连接。"""
        pass
    
    # ==================== 分布式锁 ====================
    
    @abstractmethod
    async def acquire_lock(
        self,
        key: str,
        token: str,
        timeout: int,
        blocking: bool,
        blocking_timeout: float | None,
    ) -> bool:
        """获取分布式锁。
        
        Args:
            key: 锁的键名（已加 lock: 前缀）
            token: 锁的 token
            timeout: 锁的超时时间（秒）
            blocking: 是否阻塞等待
            blocking_timeout: 阻塞等待的最大时间（秒）
            
        Returns:
            bool: 是否获取成功
        """
        pass
    
    @abstractmethod
    async def release_lock(self, key: str, token: str) -> bool:
        """释放分布式锁。
        
        Args:
            key: 锁的键名（已加 lock: 前缀）
            token: 获取锁时的 token
            
        Returns:
            bool: 是否成功释放
        """
        pass


__all__ = [
    "CacheBackend",
    "ICache",
]


"""缓存相关异常定义。

Infrastructure 层异常，继承自 FoundationError。
"""

from __future__ import annotations

from aury.boot.common.exceptions import FoundationError


class CacheError(FoundationError):
    """缓存相关错误基类。
    
    所有缓存相关的异常都应该继承此类。
    """
    
    pass


class CacheMissError(CacheError):
    """缓存未命中错误（可选，通常不抛出）。"""
    
    pass


class CacheBackendError(CacheError):
    """缓存后端错误。"""
    
    pass


__all__ = [
    "CacheBackendError",
    "CacheError",
    "CacheMissError",
]


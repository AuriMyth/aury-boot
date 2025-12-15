"""存储相关异常定义。

Infrastructure 层异常，继承自 FoundationError。
"""

from __future__ import annotations

from aury.boot.common.exceptions import FoundationError


class StorageError(FoundationError):
    """存储相关错误基类。
    
    所有存储相关的异常都应该继承此类。
    """
    
    pass


class StorageNotFoundError(StorageError):
    """存储文件不存在错误。"""
    
    pass


class StorageBackendError(StorageError):
    """存储后端错误。"""
    
    pass


__all__ = [
    "StorageBackendError",
    "StorageError",
    "StorageNotFoundError",
]


"""数据库相关异常定义。

Infrastructure 层异常，继承自 FoundationError。
"""

from __future__ import annotations

from aury.boot.common.exceptions import FoundationError


class DatabaseError(FoundationError):
    """数据库相关错误基类。
    
    所有数据库相关的异常都应该继承此类。
    """
    
    pass


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误。"""
    
    pass


class DatabaseQueryError(DatabaseError):
    """数据库查询错误。"""
    
    pass


class DatabaseTransactionError(DatabaseError):
    """数据库事务错误。"""
    
    pass


__all__ = [
    "DatabaseConnectionError",
    "DatabaseError",
    "DatabaseQueryError",
    "DatabaseTransactionError",
]


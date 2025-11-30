"""错误代码定义。

提供统一的错误代码枚举。
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """错误代码枚举。"""
    
    # 通用错误 (1xxx)
    UNKNOWN_ERROR = "1000"
    VALIDATION_ERROR = "1001"
    NOT_FOUND = "1002"
    ALREADY_EXISTS = "1003"
    UNAUTHORIZED = "1004"
    FORBIDDEN = "1005"
    
    # 数据库错误 (2xxx)
    DATABASE_ERROR = "2000"
    DUPLICATE_KEY = "2001"
    CONSTRAINT_VIOLATION = "2002"
    VERSION_CONFLICT = "2003"  # 乐观锁冲突
    
    # 业务错误 (3xxx)
    BUSINESS_ERROR = "3000"
    INVALID_OPERATION = "3001"
    INSUFFICIENT_PERMISSION = "3002"
    
    # 外部服务错误 (4xxx)
    EXTERNAL_SERVICE_ERROR = "4000"
    TIMEOUT_ERROR = "4001"
    NETWORK_ERROR = "4002"


__all__ = [
    "ErrorCode",
]



"""错误代码定义。

提供统一的错误代码枚举。

**重要提示**：
Python 的 Enum 不支持继承已有成员的枚举。
如果你需要扩展错误代码，请使用以下方式之一：

方式 1（推荐）：创建独立的枚举类
```python
class ServiceErrorCode(str, Enum):
    # 服务特定错误代码（5xxx）
    CUSTOM_ERROR = "5000"
```

方式 2：使用联合类型
```python
ErrorCodeType = ErrorCode | ServiceErrorCode
```
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Foundation Kit 基础错误代码。
    
    预留范围：
    - 1xxx: 通用错误
    - 2xxx: 数据库错误
    - 3xxx: 业务错误
    - 4xxx: 外部服务错误
    - 5xxx+: 留给各个服务自定义
    """
    
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



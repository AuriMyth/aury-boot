"""错误处理系统 - 责任链模式 + Pydantic。

提供统一的异常类和错误处理链。
"""

from .chain import ErrorHandlerChain, error_handler_chain, global_exception_handler
from .codes import ErrorCode
from .exceptions import (
    AlreadyExistsError,
    BaseError,
    BusinessError,
    DatabaseError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    VersionConflictError,
)
from .handlers import (
    BaseErrorHandler,
    DatabaseErrorHandler,
    ErrorHandler,
    HTTPExceptionHandler,
    ServiceErrorHandler,
    ValidationErrorHandler,
)
from .response import ErrorDetail

__all__ = [
    "AlreadyExistsError",
    "BaseError",
    "BaseErrorHandler",
    "BusinessError",
    "DatabaseError",
    "DatabaseErrorHandler",
    # 错误代码
    "ErrorCode",
    # 错误模型
    "ErrorDetail",
    # 错误处理器
    "ErrorHandler",
    # 错误处理链
    "ErrorHandlerChain",
    "ForbiddenError",
    "HTTPExceptionHandler",
    "NotFoundError",
    "ServiceErrorHandler",
    "UnauthorizedError",
    "ValidationError",
    "ValidationErrorHandler",
    "VersionConflictError",
    "error_handler_chain",
    "global_exception_handler",
]


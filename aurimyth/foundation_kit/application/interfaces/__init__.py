"""接口层模块。

提供API定义，包括：
- 错误处理
- 请求模型（Ingress）
- 响应模型（Egress）
"""

# 错误处理已移至 application.errors
from ..errors import (
    AlreadyExistsError,
    BaseError,
    BusinessError,
    DatabaseError,
    ErrorCode,
    ErrorDetail,
    ErrorHandler,
    ErrorHandlerChain,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    VersionConflictError,
    global_exception_handler,
)
from .egress import (
    BaseResponse,
    CountResponse,
    ErrorResponse,
    IDResponse,
    Pagination,
    PaginationResponse,
    ResponseBuilder,
    SuccessResponse,
)
from .ingress import (
    BaseRequest,
    FilterRequest,
    ListRequest,
    PaginationRequest,
    SortOrder,
)

__all__ = [
    "AlreadyExistsError",
    "BaseError",
    # 请求模型
    "BaseRequest",
    # 响应模型
    "BaseResponse",
    "BusinessError",
    "CountResponse",
    "DatabaseError",
    # 错误处理
    "ErrorCode",
    "ErrorDetail",
    "ErrorHandler",
    "ErrorHandlerChain",
    "ErrorResponse",
    "FilterRequest",
    "ForbiddenError",
    "IDResponse",
    "ListRequest",
    "NotFoundError",
    "Pagination",
    "PaginationRequest",
    "PaginationResponse",
    "ResponseBuilder",
    "SortOrder",
    "SuccessResponse",
    "UnauthorizedError",
    "ValidationError",
    "VersionConflictError",
    "global_exception_handler",
]


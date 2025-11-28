"""接口层模块。

提供API定义，包括：
- 错误处理
- 请求模型（Ingress）
- 响应模型（Egress）
"""

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
from .errors import (
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
from .ingress import (
    BaseRequest,
    FilterRequest,
    ListRequest,
    PaginationRequest,
    SortOrder,
)

__all__ = [
    # 错误处理
    "ErrorCode",
    "ErrorDetail",
    "BaseError",
    "ValidationError",
    "NotFoundError",
    "AlreadyExistsError",
    "VersionConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "DatabaseError",
    "BusinessError",
    "ErrorHandler",
    "ErrorHandlerChain",
    "global_exception_handler",
    # 请求模型
    "BaseRequest",
    "PaginationRequest",
    "ListRequest",
    "FilterRequest",
    "SortOrder",
    # 响应模型
    "BaseResponse",
    "ErrorResponse",
    "Pagination",
    "PaginationResponse",
    "SuccessResponse",
    "IDResponse",
    "CountResponse",
    "ResponseBuilder",
]


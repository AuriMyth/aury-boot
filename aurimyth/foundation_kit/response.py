"""响应模型。

统一导出 foundation_kit.schemas 中的响应模型，方便使用。
"""

from aurimyth.foundation_kit.schemas import (
    BaseResponse,
    ErrorResponse,
    Pagination,
    PaginationResponse,
    SuccessResponse,
    IDResponse,
    CountResponse,
)

__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "Pagination",
    "PaginationResponse",
    "SuccessResponse",
    "IDResponse",
    "CountResponse",
]





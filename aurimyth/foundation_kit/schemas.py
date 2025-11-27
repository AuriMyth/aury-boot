"""共享基础Schema。

提供所有服务通用的请求和响应模型。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Optional, List

from pydantic import BaseModel, Field

# 泛型类型变量
T = TypeVar("T")


class SortOrder(str, Enum):
    """排序方向枚举。"""
    
    ASC = "asc"
    DESC = "desc"


class BaseResponse(BaseModel, Generic[T]):
    """基础响应模型。
    
    所有API响应的统一格式。
    
    Attributes:
        code: 响应状态码，200表示成功
        message: 响应消息
        data: 响应数据
        timestamp: 响应时间戳
    """
    
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseResponse[None]):
    """错误响应模型。
    
    用于返回错误信息。
    
    Attributes:
        code: 错误状态码
        message: 错误消息
        error_code: 错误代码
        details: 错误详情
    """
    
    error_code: Optional[str] = Field(default=None, description="错误代码")
    details: Optional[dict] = Field(default=None, description="错误详情")
    
    @classmethod
    def create(
        cls,
        code: int = 400,
        message: str = "请求错误",
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> "ErrorResponse":
        """创建错误响应。"""
        return cls(
            code=code,
            message=message,
            error_code=error_code,
            details=details,
            data=None,
        )


class Pagination(BaseModel, Generic[T]):
    """分页数据模型。
    
    Attributes:
        total: 总记录数
        items: 数据列表
        page: 当前页码（从1开始）
        size: 每页数量
        pages: 总页数
    """
    
    total: int = Field(..., description="总记录数", ge=0)
    items: List[T] = Field(default_factory=list, description="数据列表")
    page: int = Field(default=1, description="当前页码", ge=1)
    size: int = Field(default=20, description="每页数量", ge=1, le=100)
    
    @property
    def pages(self) -> int:
        """总页数。"""
        if self.size == 0:
            return 0
        return (self.total + self.size - 1) // self.size
    
    @property
    def has_next(self) -> bool:
        """是否有下一页。"""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """是否有上一页。"""
        return self.page > 1
    
    @property
    def skip(self) -> int:
        """跳过的记录数。"""
        return (self.page - 1) * self.size


class PaginationResponse(BaseResponse[Pagination[T]]):
    """分页响应模型。
    
    用于返回分页数据。
    """
    
    pass


class BaseRequest(BaseModel):
    """基础请求模型。
    
    所有API请求的基类。
    
    Attributes:
        request_id: 请求ID（用于追踪）
    """
    
    request_id: Optional[str] = Field(default=None, description="请求ID（用于追踪）")


class PaginationRequest(BaseRequest):
    """分页请求模型。
    
    用于分页查询的请求参数。
    
    Attributes:
        page: 页码（从1开始）
        size: 每页数量
        sort: 排序字段
        order: 排序方向（asc/desc）
    """
    
    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    size: int = Field(default=20, ge=1, le=100, description="每页数量")
    sort: Optional[str] = Field(default=None, description="排序字段")
    order: SortOrder = Field(default=SortOrder.ASC, description="排序方向（asc/desc）")
    
    @property
    def skip(self) -> int:
        """跳过的记录数。"""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """限制的记录数。"""
        return self.size


class ListRequest(BaseRequest):
    """列表请求模型。
    
    用于列表查询的请求参数（不分页）。
    
    Attributes:
        limit: 限制返回数量
        offset: 偏移量
        sort: 排序字段
        order: 排序方向（asc/desc）
    """
    
    limit: Optional[int] = Field(default=None, ge=1, le=1000, description="限制返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")
    sort: Optional[str] = Field(default=None, description="排序字段")
    order: SortOrder = Field(default=SortOrder.ASC, description="排序方向（asc/desc）")


class FilterRequest(BaseRequest):
    """过滤请求模型。
    
    用于带过滤条件的查询。
    
    Attributes:
        filters: 过滤条件字典
    """
    
    filters: Optional[dict] = Field(default_factory=dict, description="过滤条件字典")


class SuccessResponse(BaseResponse[dict]):
    """成功响应模型。
    
    用于返回简单的成功消息。
    
    Attributes:
        success: 是否成功
    """
    
    success: bool = Field(default=True, description="是否成功")
    
    @classmethod
    def create(cls, message: str = "操作成功", data: Optional[dict] = None) -> "SuccessResponse":
        """创建成功响应。"""
        return cls(
            code=200,
            message=message,
            data=data or {},
            success=True,
        )


class IDResponse(BaseResponse[int]):
    """ID响应模型。
    
    用于返回创建的资源ID。
    """
    
    pass


class CountResponse(BaseResponse[int]):
    """计数响应模型。
    
    用于返回计数结果。
    """
    
    pass


__all__ = [
    "SortOrder",
    "BaseResponse",
    "ErrorResponse",
    "Pagination",
    "PaginationResponse",
    "BaseRequest",
    "PaginationRequest",
    "ListRequest",
    "FilterRequest",
    "SuccessResponse",
    "IDResponse",
    "CountResponse",
]


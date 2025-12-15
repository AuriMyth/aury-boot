"""API 响应模型（Egress）。

提供所有服务通用的响应模型。
这些是基础架构层的接口模型。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class BaseResponse[T](BaseModel):
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
    data: T | None = Field(default=None, description="响应数据")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="响应时间戳")
    
    model_config = ConfigDict(
        ser_json_timedelta="float",
        ser_json_bytes="utf8",
    )


class ErrorResponse(BaseResponse[None]):
    """错误响应模型。
    
    用于返回错误信息。
    
    Attributes:
        code: 错误状态码
        message: 错误消息
        error_code: 错误代码
        details: 错误详情
    """
    
    error_code: str | None = Field(default=None, description="错误代码")
    details: dict | None = Field(default=None, description="错误详情")
    
    @classmethod
    def create(
        cls,
        code: int = 400,
        message: str = "请求错误",
        error_code: str | None = None,
        details: dict | None = None,
    ) -> ErrorResponse:
        """创建错误响应。"""
        return cls(
            code=code,
            message=message,
            error_code=error_code,
            details=details,
            data=None,
        )


class Pagination[T](BaseModel):
    """分页数据模型。
    
    Attributes:
        total: 总记录数
        items: 数据列表
        page: 当前页码（从1开始）
        size: 每页数量
        pages: 总页数
    """
    
    total: int = Field(..., description="总记录数", ge=0)
    items: list[T] = Field(default_factory=list, description="数据列表")
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


class PaginationResponse[T](BaseResponse[Pagination[T]]):
    """分页响应模型。
    
    用于返回分页数据。
    """
    
    pass


class SuccessResponse(BaseResponse[dict]):
    """成功响应模型。
    
    用于返回简单的成功消息。
    
    Attributes:
        success: 是否成功
    """
    
    success: bool = Field(default=True, description="是否成功")
    
    @classmethod
    def create(cls, message: str = "操作成功", data: dict | None = None) -> SuccessResponse:
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


class ResponseBuilder:
    """响应构建器。
    
    提供便捷的响应创建方法。
    """
    
    @staticmethod
    def success[T](
        message: str = "操作成功",
        data: T | None = None,
        code: int = 200,
    ) -> BaseResponse[T]:
        """创建成功响应。
        
        Args:
            message: 响应消息
            data: 响应数据
            code: 响应状态码
            
        Returns:
            BaseResponse: 响应对象
        """
        return BaseResponse(
            code=code,
            message=message,
            data=data,
        )
    
    @staticmethod
    def fail(
        message: str = "操作失败",
        code: int = 400,
        errors: list[dict] | None = None,
        error_code: str | None = None,
    ) -> ErrorResponse:
        """创建失败响应。
        
        Args:
            message: 错误消息
            code: 错误状态码
            errors: 错误详情列表
            error_code: 错误代码
            
        Returns:
            ErrorResponse: 错误响应对象
        """
        return ErrorResponse(
            code=code,
            message=message,
            error_code=error_code,
            details={"errors": errors} if errors else None,
            data=None,
        )


__all__ = [
    "BaseResponse",
    "CountResponse",
    "ErrorResponse",
    "IDResponse",
    "Pagination",
    "PaginationResponse",
    "ResponseBuilder",
    "SuccessResponse",
]


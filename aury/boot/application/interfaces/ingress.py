"""API 请求模型（Ingress）。

提供所有服务通用的请求模型。
这些是基础架构层的接口模型。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SortOrder(str, Enum):
    """排序方向枚举。"""
    
    ASC = "asc"
    DESC = "desc"


class BaseRequest(BaseModel):
    """基础请求模型。
    
    所有API请求的基类。
    
    Attributes:
        request_id: 请求ID（用于追踪）
    """
    
    request_id: str | None = Field(default=None, description="请求ID（用于追踪）")


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
    sort: str | None = Field(default=None, description="排序字段")
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
    
    limit: int | None = Field(default=None, ge=1, le=1000, description="限制返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")
    sort: str | None = Field(default=None, description="排序字段")
    order: SortOrder = Field(default=SortOrder.ASC, description="排序方向（asc/desc）")


class FilterRequest(BaseRequest):
    """过滤请求模型。
    
    用于带过滤条件的查询。
    
    Attributes:
        filters: 过滤条件字典
    """
    
    filters: dict | None = Field(default_factory=dict, description="过滤条件字典")


__all__ = [
    "BaseRequest",
    "FilterRequest",
    "ListRequest",
    "PaginationRequest",
    "SortOrder",
]


"""错误响应模型（接口层）。

提供用于 HTTP API 响应的错误详情模型。
这是接口层的数据模型，用于序列化和传输。
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """错误详情模型（Pydantic）。
    
    支持两种错误类型：
    1. 字段错误：field不为空，表示特定字段的验证错误
    2. 通用错误：field为空，表示系统级或业务级错误
    
    使用示例:
        # 字段验证错误
        ErrorDetail(
            field="username",
            message="用户名格式不正确",
            code="INVALID_FORMAT",
            location="body"
        )
        
        # 通用业务错误
        ErrorDetail(
            message="库存不足",
            code="INSUFFICIENT_STOCK"
        )
        
        # 系统错误
        ErrorDetail(
            message="数据库连接失败",
            code="DB_CONNECTION_ERROR"
        )
    """
    
    message: str = Field(..., description="错误消息")
    code: str | None = Field(None, description="错误代码")
    field: str | None = Field(None, description="错误字段（仅字段验证错误）")
    location: str | None = Field(None, description="错误位置（如：body, query, path）")
    value: Any | None = Field(None, description="导致错误的值")
    
    @classmethod
    def field_error(
        cls,
        field: str,
        message: str,
        code: str | None = None,
        location: str = "body",
        value: Any | None = None,
    ) -> "ErrorDetail":
        """创建字段验证错误。
        
        Args:
            field: 字段名
            message: 错误消息
            code: 错误代码
            location: 错误位置
            value: 错误值
            
        Returns:
            ErrorDetail: 错误详情对象
        """
        return cls(
            message=message,
            code=code,
            field=field,
            location=location,
            value=value,
        )
    
    @classmethod
    def generic_error(
        cls,
        message: str,
        code: str | None = None,
    ) -> "ErrorDetail":
        """创建通用错误。
        
        Args:
            message: 错误消息
            code: 错误代码
            
        Returns:
            ErrorDetail: 错误详情对象
        """
        return cls(
            message=message,
            code=code,
        )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "用户名格式不正确",
                    "code": "INVALID_FORMAT",
                    "field": "username",
                    "location": "body",
                    "value": "user@123"
                },
                {
                    "message": "库存不足",
                    "code": "INSUFFICIENT_STOCK"
                }
            ]
        }
    )


__all__ = [
    "ErrorDetail",
]


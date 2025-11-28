"""错误处理系统 - 责任链模式 + Pydantic。

提供统一的异常类和错误处理链。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from aurimyth.foundation_kit.common.logging import logger

from .egress import ResponseBuilder


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
    ) -> ErrorDetail:
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
    ) -> ErrorDetail:
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
    
    class Config:
        schema_extra = {
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


class BaseError(Exception):
    """应用层异常基类（用于 HTTP 响应）。
    
    所有应用层的异常应继承此类。
    用于 HTTP API 响应，包含错误代码和状态码。
    
    注意：此异常继承自 Python 标准 Exception，不继承 FoundationError，
    因为它是应用层特有的，用于 HTTP 响应转换。
    
    Attributes:
        message: 错误消息
        code: 错误代码
        status_code: HTTP状态码
        details: 错误详情列表
        metadata: 元数据
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: list[ErrorDetail] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """初始化异常。
        
        Args:
            message: 错误消息
            code: 错误代码
            status_code: HTTP状态码
            details: 错误详情
            metadata: 元数据
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "message": self.message,
            "code": self.code.value,
            "status_code": self.status_code,
            "details": [detail.dict() for detail in self.details],
            "metadata": self.metadata,
        }
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<{self.__class__.__name__} code={self.code.value} message={self.message}>"


class ValidationError(BaseError):
    """验证异常。"""
    
    def __init__(
        self,
        message: str = "数据验证失败",
        details: list[ErrorDetail] | None = None,
        **kwargs
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            **kwargs
        )


class NotFoundError(BaseError):
    """资源不存在异常。"""
    
    def __init__(
        self,
        message: str = "资源不存在",
        resource: str | None = None,
        **kwargs
    ) -> None:
        metadata = kwargs.pop("metadata", {})
        if resource:
            metadata["resource"] = resource
        
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            metadata=metadata,
            **kwargs
        )


class AlreadyExistsError(BaseError):
    """资源已存在异常。"""
    
    def __init__(
        self,
        message: str = "资源已存在",
        resource: str | None = None,
        **kwargs
    ) -> None:
        metadata = kwargs.pop("metadata", {})
        if resource:
            metadata["resource"] = resource
        
        super().__init__(
            message=message,
            code=ErrorCode.ALREADY_EXISTS,
            status_code=status.HTTP_409_CONFLICT,
            metadata=metadata,
            **kwargs
        )


class VersionConflictError(BaseError):
    """版本冲突异常（乐观锁）。
    
    当使用 VersionedModel 时，如果更新时版本号不匹配，抛出此异常。
    
    注意：此异常继承自 BaseError，用于应用层（HTTP 响应）。
    Core 层的 VersionConflictError 在 core.exceptions 中定义。
    """
    
    def __init__(
        self,
        message: str = "数据已被其他操作修改，请刷新后重试",
        current_version: int | None = None,
        expected_version: int | None = None,
        **kwargs
    ) -> None:
        metadata = kwargs.pop("metadata", {})
        if current_version is not None:
            metadata["current_version"] = current_version
        if expected_version is not None:
            metadata["expected_version"] = expected_version
        
        super().__init__(
            message=message,
            code=ErrorCode.VERSION_CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            metadata=metadata,
            **kwargs
        )
    
    @classmethod
    def from_core_exception(
        cls,
        exc: aurimyth.foundation_kit.core.exceptions.VersionConflictError,  # noqa: F821
    ) -> VersionConflictError:
        """从 Core 层的 VersionConflictError 创建应用层异常。
        
        Args:
            exc: Core 层的 VersionConflictError 异常
            
        Returns:
            VersionConflictError: 应用层的异常对象
        """
        return cls(
            message=exc.message,
            current_version=exc.current_version,
            expected_version=exc.expected_version,
        )


class UnauthorizedError(BaseError):
    """未授权异常。"""
    
    def __init__(
        self,
        message: str = "未授权访问",
        **kwargs
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs
        )


class ForbiddenError(BaseError):
    """禁止访问异常。"""
    
    def __init__(
        self,
        message: str = "禁止访问",
        **kwargs
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs
        )


class DatabaseError(BaseError):
    """数据库异常。"""
    
    def __init__(
        self,
        message: str = "数据库错误",
        **kwargs
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            **kwargs
        )


class BusinessError(BaseError):
    """业务逻辑异常。"""
    
    def __init__(
        self,
        message: str,
        **kwargs
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.BUSINESS_ERROR,
            status_code=status.HTTP_400_BAD_REQUEST,
            **kwargs
        )


# 错误处理链 - 责任链模式

class ErrorHandler(ABC):
    """错误处理器抽象基类 - 责任链模式。"""
    
    def __init__(self) -> None:
        """初始化处理器。"""
        self._next_handler: ErrorHandler | None = None
    
    def set_next(self, handler: ErrorHandler) -> ErrorHandler:
        """设置下一个处理器。
        
        Args:
            handler: 下一个处理器
            
        Returns:
            ErrorHandler: 下一个处理器（支持链式调用）
        """
        self._next_handler = handler
        return handler
    
    @abstractmethod
    def can_handle(self, exception: Exception) -> bool:
        """判断是否可以处理该异常。
        
        Args:
            exception: 异常对象
            
        Returns:
            bool: 是否可以处理
        """
        pass
    
    @abstractmethod
    async def handle(self, exception: Exception, request: Request) -> JSONResponse:
        """处理异常。
        
        Args:
            exception: 异常对象
            request: 请求对象
            
        Returns:
            JSONResponse: 响应对象
        """
        pass
    
    async def process(self, exception: Exception, request: Request) -> JSONResponse:
        """处理异常（责任链入口）。
        
        Args:
            exception: 异常对象
            request: 请求对象
            
        Returns:
            JSONResponse: 响应对象
        """
        if self.can_handle(exception):
            return await self.handle(exception, request)
        
        if self._next_handler:
            return await self._next_handler.process(exception, request)
        
        # 默认处理
        return await self._default_handle(exception, request)
    
    async def _default_handle(self, exception: Exception, request: Request) -> JSONResponse:
        """默认异常处理。"""
        logger.exception(f"未处理的异常: {exception}")
        response = ResponseBuilder.fail(
            message="服务器内部错误",
            code=-1,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.dict(),
        )


class BaseErrorHandler(ErrorHandler):
    """自定义基础异常处理器。"""
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为自定义异常。"""
        return isinstance(exception, BaseError)
    
    async def handle(self, exception: BaseError, request: Request) -> JSONResponse:
        """处理自定义异常。"""
        logger.warning(f"业务异常: {exception}")
        
        errors = [detail.dict() for detail in exception.details] if exception.details else None
        
        response = ResponseBuilder.fail(
            message=exception.message,
            code=int(exception.code.value),
            errors=errors,
        )
        
        if exception.metadata:
            response.metadata = exception.metadata
        
        return JSONResponse(
            status_code=exception.status_code,
            content=response.dict(),
        )


class HTTPExceptionHandler(ErrorHandler):
    """FastAPI HTTP异常处理器。"""
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为HTTP异常。"""
        return isinstance(exception, HTTPException)
    
    async def handle(self, exception: HTTPException, request: Request) -> JSONResponse:
        """处理HTTP异常。"""
        logger.warning(f"HTTP异常: {exception.status_code} - {exception.detail}")
        
        response = ResponseBuilder.fail(
            message=exception.detail,
            code=exception.status_code,
        )
        
        return JSONResponse(
            status_code=exception.status_code,
            content=response.dict(),
        )


class ValidationErrorHandler(ErrorHandler):
    """Pydantic验证异常处理器。"""
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为验证异常。"""
        from pydantic import ValidationError
        return isinstance(exception, ValidationError)
    
    async def handle(self, exception: Exception, request: Request) -> JSONResponse:
        """处理验证异常。"""
        logger.warning(f"数据验证失败: {exception}")
        
        errors = []
        for error in exception.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        response = ResponseBuilder.fail(
            message="数据验证失败",
            code=400,
            errors=errors,
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response.dict(),
        )


class DatabaseErrorHandler(ErrorHandler):
    """数据库异常处理器。
    
    处理数据库相关错误，包括 Core 层的异常。
    """
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为数据库异常。"""
        from sqlalchemy.exc import SQLAlchemyError

        from aurimyth.foundation_kit.common.exceptions import FoundationError
        from aurimyth.foundation_kit.core.exceptions import ModelError
        from aurimyth.foundation_kit.infrastructure.database.exceptions import DatabaseError
        
        return isinstance(exception, SQLAlchemyError | ModelError | DatabaseError | FoundationError)
    
    async def handle(self, exception: Exception, request: Request) -> JSONResponse:
        """处理数据库异常。"""
        # 处理 Core 层的 VersionConflictError
        from aurimyth.foundation_kit.core.exceptions import VersionConflictError as CoreVersionConflictError
        
        if isinstance(exception, CoreVersionConflictError):
            # 转换为应用层异常
            app_error = VersionConflictError.from_core_exception(exception)
            response = ResponseBuilder.fail(
                message=app_error.message,
                code=app_error.status_code,
                details=[ErrorDetail(
                    message=app_error.message,
                    code=app_error.code,
                )],
            )
            return JSONResponse(
                status_code=app_error.status_code,
                content=response.dict(),
            )
        
        # 处理其他数据库错误
        logger.exception(f"数据库错误: {exception}")
        
        response = ResponseBuilder.fail(
            message="数据库操作失败",
            code=500,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.dict(),
        )


class ErrorHandlerChain:
    """错误处理链管理器。"""
    
    def __init__(self) -> None:
        """初始化处理链。"""
        self._chain = self._build_chain()
    
    def _build_chain(self) -> ErrorHandler:
        """构建处理链。
        
        Returns:
            ErrorHandler: 处理链头部
        """
        # 按优先级顺序构建处理链
        base_handler = BaseErrorHandler()
        http_handler = HTTPExceptionHandler()
        validation_handler = ValidationErrorHandler()
        db_handler = DatabaseErrorHandler()
        
        base_handler.set_next(http_handler).set_next(validation_handler).set_next(db_handler)
        
        return base_handler
    
    async def handle(self, exception: Exception, request: Request) -> JSONResponse:
        """处理异常。
        
        Args:
            exception: 异常对象
            request: 请求对象
            
        Returns:
            JSONResponse: 响应对象
        """
        return await self._chain.process(exception, request)


# 全局异常处理器实例
error_handler_chain = ErrorHandlerChain()


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器（FastAPI集成）。
    
    使用方式:
        app.add_exception_handler(Exception, global_exception_handler)
    """
    return await error_handler_chain.handle(exc, request)


__all__ = [
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
]


"""错误处理器实现。

提供责任链模式的错误处理器。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from aury.boot.common.exceptions import FoundationError
from aury.boot.common.logging import logger
from aury.boot.domain.exceptions import (
    ModelError,
    ServiceException,
)
from aury.boot.domain.exceptions import (
    VersionConflictError as DomainVersionConflictError,
)
from aury.boot.infrastructure.database.exceptions import (
    DatabaseError as InfraDatabaseError,
)

from ..interfaces.egress import ResponseBuilder
from .exceptions import BaseError, BusinessError, VersionConflictError
from .response import ErrorDetail


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
        logger.exception(f"未处理的异常: {request.method} {request.url.path}")
        
        response = ResponseBuilder.fail(
            message="服务器内部错误",
            code=-1,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump(mode="json"),
        )


class BaseErrorHandler(ErrorHandler):
    """自定义基础异常处理器。"""
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为自定义异常。"""
        return isinstance(exception, BaseError)
    
    async def handle(self, exception: BaseError, request: Request) -> JSONResponse:
        """处理自定义异常。"""
        logger.warning(f"业务异常: {exception}")
        
        errors = [detail.model_dump() for detail in exception.details] if exception.details else None
        
        # 兼容 ErrorCode 枚举和字符串
        code_value = exception.code.value if hasattr(exception.code, "value") else exception.code
        
        # 尝试转换为 int，如果失败则使用 status_code
        try:
            code_int = int(code_value)
        except (ValueError, TypeError):
            # 非数字字符串（如 "TODO_ATTACHMENT_ERROR"），使用 HTTP 状态码作为 code
            code_int = exception.status_code
        
        response = ResponseBuilder.fail(
            message=exception.message,
            code=code_int,
            errors=errors,
        )
        
        # metadata 放入 details 字段
        if exception.metadata:
            response.details = exception.metadata
        
        return JSONResponse(
            status_code=exception.status_code,
            content=response.model_dump(mode="json"),
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
            content=response.model_dump(mode="json"),
        )


class ValidationErrorHandler(ErrorHandler):
    """验证异常处理器。
    
    处理 Pydantic ValidationError 和 FastAPI RequestValidationError。
    """
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为验证异常。"""
        return isinstance(exception, ValidationError | RequestValidationError)
    
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
            content=response.model_dump(mode="json"),
        )


class ServiceErrorHandler(ErrorHandler):
    """服务层异常处理器。
    
    处理 Domain 层的 ServiceException。
    """
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为服务层异常。"""
        return isinstance(exception, ServiceException)
    
    async def handle(self, exception: Exception, request: Request) -> JSONResponse:
        """处理服务层异常。"""
        if not isinstance(exception, ServiceException):
            return await self._default_handle(exception, request)
        
        logger.warning(f"服务层异常: {exception}")
        
        # 直接使用 ServiceException 的信息
        response = ResponseBuilder.fail(
            message=exception.message,
            code=400,  # 服务层异常默认 400
        )
        
        # 构建 details
        details: dict = {}
        if exception.code:
            details["code"] = exception.code
        if exception.metadata:
            details.update(exception.metadata)
        if details:
            response.details = details
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response.model_dump(mode="json"),
        )


class DatabaseErrorHandler(ErrorHandler):
    """数据库异常处理器。
    
    处理数据库相关错误，包括 Domain 层的异常。
    """
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为数据库异常。"""
        return isinstance(exception, SQLAlchemyError | ModelError | InfraDatabaseError | FoundationError)
    
    async def handle(self, exception: Exception, request: Request) -> JSONResponse:
        """处理数据库异常。"""
        # 处理 Domain 层的 VersionConflictError
        if isinstance(exception, DomainVersionConflictError):
            # 转换为应用层异常
            app_error = VersionConflictError.from_domain_exception(exception)
            response = ResponseBuilder.fail(
                message=app_error.message,
                code=app_error.status_code,
                details=[ErrorDetail(
                    message=app_error.message,
                    code=app_error.code.value,
                )],
            )
            return JSONResponse(
                status_code=app_error.status_code,
                content=response.model_dump(mode="json"),
            )
        
        # 处理唯一约束冲突（如重复的 email、username 等）
        if isinstance(exception, IntegrityError):
            logger.warning(f"数据库完整性约束冲突: {exception}")
            
            # 解析错误信息，提取字段名
            error_msg = str(exception.orig) if exception.orig else str(exception)
            field_name = None
            
            # 尝试从错误信息中提取字段名
            if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
                # PostgreSQL: Key (email)=(xxx) already exists
                # MySQL: Duplicate entry 'xxx' for key 'users.email'
                import re
                # PostgreSQL 格式
                match = re.search(r"Key \((\w+)\)", error_msg)
                if match:
                    field_name = match.group(1)
                else:
                    # MySQL 格式
                    match = re.search(r"for key ['\"]?\w+\.(\w+)['\"]?", error_msg, re.IGNORECASE)
                    if match:
                        field_name = match.group(1)
            
            if field_name:
                message = f"{field_name} 已存在"
            else:
                message = "数据已存在，请检查唯一字段"
            
            response = ResponseBuilder.fail(
                message=message,
                code=409,
            )
            
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=response.model_dump(mode="json"),
            )
        
        # 处理其他数据库错误
        logger.exception(f"数据库错误: {request.method} {request.url.path}")
        
        response = ResponseBuilder.fail(
            message="数据库操作失败",
            code=500,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump(mode="json"),
        )


__all__ = [
    "BaseErrorHandler",
    "DatabaseErrorHandler",
    "ErrorHandler",
    "HTTPExceptionHandler",
    "ServiceErrorHandler",
    "ValidationErrorHandler",
]


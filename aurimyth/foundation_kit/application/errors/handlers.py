"""错误处理器实现。

提供责任链模式的错误处理器。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from aurimyth.foundation_kit.common.exceptions import FoundationError
from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.domain.exceptions import (
    ModelError,
    ServiceException,
    VersionConflictError as DomainVersionConflictError,
)
from aurimyth.foundation_kit.infrastructure.database.exceptions import (
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
        logger.exception(f"未处理的异常: {exception}")
        response = ResponseBuilder.fail(
            message="服务器内部错误",
            code=-1,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump(),
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
        
        response = ResponseBuilder.fail(
            message=exception.message,
            code=int(exception.code.value),
            errors=errors,
        )
        
        if exception.metadata:
            response.metadata = exception.metadata
        
        return JSONResponse(
            status_code=exception.status_code,
            content=response.model_dump(),
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
            content=response.model_dump(),
        )


class ValidationErrorHandler(ErrorHandler):
    """Pydantic验证异常处理器。"""
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为验证异常。"""
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
            content=response.model_dump(),
        )


class ServiceErrorHandler(ErrorHandler):
    """服务层异常处理器。
    
    处理 Domain 层的 ServiceException，转换为应用层的 BusinessError。
    """
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为服务层异常。"""
        return isinstance(exception, ServiceException)
    
    async def handle(self, exception: Exception, request: Request) -> JSONResponse:
        """处理服务层异常。"""
        if isinstance(exception, ServiceException):
            # 转换为应用层的 BusinessError
            business_error = BusinessError(
                message=exception.message,
                metadata={
                    "code": exception.code,
                    **exception.metadata,
                } if exception.code or exception.metadata else None,
            )
            
            # 使用 BusinessError 的响应格式
            response = ResponseBuilder.fail(
                message=business_error.message,
                code=int(business_error.code.value),
            )
            
            if business_error.metadata:
                response.metadata = business_error.metadata
            
            return JSONResponse(
                status_code=business_error.status_code,
                content=response.model_dump(),
            )
        
        # 不应该到达这里
        return await self._default_handle(exception, request)


class DatabaseErrorHandler(ErrorHandler):
    """数据库异常处理器。
    
    处理数据库相关错误，包括 Domain 层的异常。
    """
    
    def can_handle(self, exception: Exception) -> bool:
        """判断是否为数据库异常。"""
        return isinstance(exception, (SQLAlchemyError, ModelError, InfraDatabaseError, FoundationError))
    
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
                content=response.model_dump(),
            )
        
        # 处理其他数据库错误
        logger.exception(f"数据库错误: {exception}")
        
        response = ResponseBuilder.fail(
            message="数据库操作失败",
            code=500,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response.model_dump(),
        )


__all__ = [
    "BaseErrorHandler",
    "DatabaseErrorHandler",
    "ErrorHandler",
    "HTTPExceptionHandler",
    "ServiceErrorHandler",
    "ValidationErrorHandler",
]


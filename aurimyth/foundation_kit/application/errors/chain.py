"""错误处理链管理器。

提供错误处理链的构建和管理。
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from .handlers import (
    BaseErrorHandler,
    DatabaseErrorHandler,
    ErrorHandler,
    HTTPExceptionHandler,
    ServiceErrorHandler,
    ValidationErrorHandler,
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
        # 1. BaseErrorHandler - 处理应用层自定义异常
        # 2. ServiceErrorHandler - 处理 Domain 层 ServiceException（业务异常）
        # 3. HTTPExceptionHandler - 处理 FastAPI HTTP 异常
        # 4. ValidationErrorHandler - 处理 Pydantic 验证异常
        # 5. DatabaseErrorHandler - 处理数据库异常（包括 Domain 层其他异常）
        base_handler = BaseErrorHandler()
        service_handler = ServiceErrorHandler()
        http_handler = HTTPExceptionHandler()
        validation_handler = ValidationErrorHandler()
        db_handler = DatabaseErrorHandler()
        
        base_handler.set_next(service_handler).set_next(http_handler).set_next(validation_handler).set_next(db_handler)
        
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
    "ErrorHandlerChain",
    "error_handler_chain",
    "global_exception_handler",
]



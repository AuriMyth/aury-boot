"""应用层异常类定义。

提供应用层业务异常类，用于业务逻辑中抛出异常。
这些异常会被错误处理器转换为 HTTP 响应。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import status

from aurimyth.foundation_kit.common.exceptions import FoundationError

from .codes import ErrorCode
from .response import ErrorDetail

if TYPE_CHECKING:
    from aurimyth.foundation_kit.domain.exceptions import VersionConflictError as DomainVersionConflictError


class BaseError(FoundationError):
    """应用层异常基类（用于 HTTP 响应）。
    
    所有应用层的异常应继承此类。
    用于 HTTP API 响应，包含错误代码和状态码。
    
    继承自 FoundationError 以保持异常体系的一致性。
    
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
            "details": [detail.model_dump() for detail in self.details],
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
        resource: Any = None,
        **kwargs
    ) -> None:
        metadata = kwargs.pop("metadata", {})
        if resource:
            metadata["resource"] = str(resource)  # 自动转换为字符串，支持 GUID、UUID 等
        
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
        resource: Any = None,
        **kwargs
    ) -> None:
        metadata = kwargs.pop("metadata", {})
        if resource:
            metadata["resource"] = str(resource)  # 自动转换为字符串，支持 GUID、UUID 等
        
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
        Domain 层的 VersionConflictError 在 domain.exceptions 中定义。
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
    def from_domain_exception(
        cls,
        exc: DomainVersionConflictError,
    ) -> VersionConflictError:
        """从 Domain 层的 VersionConflictError 创建应用层异常。
        
        Args:
            exc: Domain 层的 VersionConflictError 异常
            
        Returns:
            VersionConflictError: 应用层的异常对象
        """
        from aurimyth.foundation_kit.domain.exceptions import VersionConflictError as DomainVersionConflictError
        
        if isinstance(exc, DomainVersionConflictError):
            return cls(
                message=exc.message,
                current_version=exc.current_version,
                expected_version=exc.expected_version,
            )
        # 不应该到达这里
        return cls(message=str(exc))


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


__all__ = [
    "AlreadyExistsError",
    "BaseError",
    "BusinessError",
    "DatabaseError",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationError",
    "VersionConflictError",
]


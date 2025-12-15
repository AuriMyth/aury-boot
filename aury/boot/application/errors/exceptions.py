"""应用层异常类定义。

提供应用层业务异常类，用于业务逻辑中抛出异常。
这些异常会被错误处理器转换为 HTTP 响应。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import status

from aury.boot.common.exceptions import FoundationError

from .codes import ErrorCode
from .response import ErrorDetail

if TYPE_CHECKING:
    from aury.boot.domain.exceptions import VersionConflictError as DomainVersionConflictError


class BaseError(FoundationError):
    """应用层异常基类（用于 HTTP 响应）。
    
    所有应用层的异常应继承此类。
    用于 HTTP API 响应，包含错误代码和状态码。
    
    继承示例：
        class OrderError(BaseError):
            default_message = "订单错误"
            default_code = "5001"  # 自定义错误码
            default_status_code = 400
        
        class OrderNotPaidError(OrderError):
            default_message = "订单未支付"
            default_code = "5002"
    
    Attributes:
        message: 错误消息
        code: 错误代码（字符串或 ErrorCode 枚举）
        status_code: HTTP状态码
        details: 错误详情列表
        metadata: 元数据
    """
    
    # 类级别默认值，子类可覆盖
    default_message: str = "未知错误"
    default_code: str | ErrorCode = ErrorCode.UNKNOWN_ERROR
    default_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def __init__(
        self,
        message: str | None = None,
        code: str | ErrorCode | None = None,
        status_code: int | None = None,
        details: list[ErrorDetail] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """初始化异常。
        
        Args:
            message: 错误消息（默认使用类的 default_message）
            code: 错误代码（默认使用类的 default_code）
            status_code: HTTP状态码（默认使用类的 default_status_code）
            details: 错误详情
            metadata: 元数据
        """
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.status_code = status_code or self.default_status_code
        self.details = details or []
        self.metadata = metadata or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        code_value = self.code.value if isinstance(self.code, ErrorCode) else self.code
        return {
            "message": self.message,
            "code": code_value,
            "status_code": self.status_code,
            "details": [detail.model_dump() for detail in self.details],
            "metadata": self.metadata,
        }
    
    def __repr__(self) -> str:
        """字符串表示。"""
        code_value = self.code.value if isinstance(self.code, ErrorCode) else self.code
        return f"<{self.__class__.__name__} code={code_value} message={self.message}>"


class ValidationError(BaseError):
    """验证异常。"""
    
    default_message = "数据验证失败"
    default_code = ErrorCode.VALIDATION_ERROR
    default_status_code = status.HTTP_400_BAD_REQUEST


class NotFoundError(BaseError):
    """资源不存在异常。"""
    
    default_message = "资源不存在"
    default_code = ErrorCode.NOT_FOUND
    default_status_code = status.HTTP_404_NOT_FOUND
    
    def __init__(
        self,
        message: str | None = None,
        resource: Any = None,
        **kwargs
    ) -> None:
        if resource:
            metadata = kwargs.get("metadata", {})
            metadata["resource"] = str(resource)
            kwargs["metadata"] = metadata
        super().__init__(message=message, **kwargs)


class AlreadyExistsError(BaseError):
    """资源已存在异常。"""
    
    default_message = "资源已存在"
    default_code = ErrorCode.ALREADY_EXISTS
    default_status_code = status.HTTP_409_CONFLICT
    
    def __init__(
        self,
        message: str | None = None,
        resource: Any = None,
        **kwargs
    ) -> None:
        if resource:
            metadata = kwargs.get("metadata", {})
            metadata["resource"] = str(resource)
            kwargs["metadata"] = metadata
        super().__init__(message=message, **kwargs)


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
        from aury.boot.domain.exceptions import VersionConflictError as DomainVersionConflictError
        
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
    
    default_message = "未授权访问"
    default_code = ErrorCode.UNAUTHORIZED
    default_status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(BaseError):
    """禁止访问异常。"""
    
    default_message = "禁止访问"
    default_code = ErrorCode.FORBIDDEN
    default_status_code = status.HTTP_403_FORBIDDEN


class DatabaseError(BaseError):
    """数据库异常。"""
    
    default_message = "数据库错误"
    default_code = ErrorCode.DATABASE_ERROR
    default_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class BusinessError(BaseError):
    """业务逻辑异常。"""
    
    default_message = "业务错误"
    default_code = ErrorCode.BUSINESS_ERROR
    default_status_code = status.HTTP_400_BAD_REQUEST


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


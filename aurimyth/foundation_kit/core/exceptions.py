"""Core 层异常定义。

Core 层异常，继承自 FoundationError。
"""

from __future__ import annotations

from aurimyth.foundation_kit.common.exceptions import FoundationError


class CoreException(FoundationError):  # noqa: N818
    """Core 层异常基类。
    
    所有 Core 层的异常都应该继承此类。
    
    注意：虽然命名为 CoreException，但它是 Core 层的异常基类。
    保持 Exception 后缀以与 FoundationError 区分。
    """
    
    pass


class ModelError(CoreException):
    """模型相关错误基类。
    
    所有模型相关的异常都应该继承此类。
    包括：版本冲突、约束违反、验证错误等。
    """
    
    pass


class VersionConflictError(ModelError):
    """版本冲突异常（乐观锁）。
    
    当使用 VersionedModel 时，如果更新时版本号不匹配，抛出此异常。
    
    Attributes:
        current_version: 当前数据库中的版本号
        expected_version: 期望的版本号
    """
    
    def __init__(
        self,
        message: str = "数据已被其他操作修改，请刷新后重试",
        current_version: int | None = None,
        expected_version: int | None = None,
        *args: object,
    ) -> None:
        """初始化版本冲突异常。
        
        Args:
            message: 错误消息
            current_version: 当前数据库中的版本号
            expected_version: 期望的版本号
            *args: 其他参数
        """
        super().__init__(message, *args)
        self.current_version = current_version
        self.expected_version = expected_version
    
    def __str__(self) -> str:
        """返回异常字符串表示。"""
        if self.current_version is not None and self.expected_version is not None:
            return (
                f"{self.message} "
                f"(当前版本: {self.current_version}, 期望版本: {self.expected_version})"
            )
        return self.message


__all__ = [
    "CoreException",
    "ModelError",
    "VersionConflictError",
]

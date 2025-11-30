"""基础异常定义。

Common 层是最底层，不依赖任何业务层。
所有框架异常都应该继承 FoundationError。
"""

from __future__ import annotations

from typing import Any


class FoundationError(Exception):
    """基础异常类（最底层）。
    
    所有框架异常都应该继承此类。
    这是整个异常体系的根类。
    
    提供可选的元数据和原因链支持，方便调试和异常包装。
    
    注意：虽然命名为 FoundationError，但它是异常体系的根类，
    所有其他异常都继承它。
    
    Attributes:
        message: 错误消息
        metadata: 可选的元数据字典，用于存储额外的上下文信息
        cause: 可选的原始异常，用于异常链
    
    使用示例:
        # 基本用法
        raise FoundationError("操作失败")
        
        # 带元数据
        raise FoundationError(
            "操作失败",
            metadata={"user_id": 123, "operation": "update"}
        )
        
        # 包装其他异常
        try:
            risky_operation()
        except ValueError as e:
            raise FoundationError(
                "操作失败",
                cause=e,
                metadata={"context": "data_processing"}
            ) from e
    """
    
    def __init__(
        self,
        message: str,
        *args: object,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """初始化异常。
        
        Args:
            message: 错误消息
            *args: 其他参数（传递给父类）
            metadata: 可选的元数据字典，用于存储额外的上下文信息
            cause: 可选的原始异常，用于异常链
        """
        self.message = message
        self.metadata = metadata or {}
        self.cause = cause
        
        super().__init__(message, *args)
        
        # 如果提供了 cause，设置异常链
        if cause is not None:
            self.__cause__ = cause
    
    def __str__(self) -> str:
        """返回异常字符串表示。"""
        return self.message
    
    def __repr__(self) -> str:
        """返回异常的详细表示，包含元数据信息。"""
        parts = [f"{self.__class__.__name__}(message={self.message!r}"]
        
        if self.metadata:
            parts.append(f", metadata={self.metadata}")
        
        if self.cause:
            parts.append(f", cause={self.cause.__class__.__name__}")
        
        parts.append(")")
        return "".join(parts)
    
    def with_metadata(self, **kwargs: Any) -> FoundationError:
        """添加或更新元数据（链式调用）。
        
        Args:
            **kwargs: 要添加的元数据键值对
        
        Returns:
            FoundationError: 返回自身，支持链式调用
        
        使用示例:
            raise FoundationError("操作失败").with_metadata(
                user_id=123,
                operation="update"
            )
        """
        self.metadata.update(kwargs)
        return self


__all__ = [
    "FoundationError",
]



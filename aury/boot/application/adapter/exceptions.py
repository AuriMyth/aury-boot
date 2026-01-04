"""第三方接口适配器异常定义。

用于第三方接口调用过程中的各类异常场景，所有异常都继承自 FoundationError。

异常类型：
- AdapterError: 通用错误（调用失败、第三方返回错误码等）
- AdapterDisabledError: 接口被禁用（mode=disabled 或 enabled=False）
- AdapterTimeoutError: 调用超时
- AdapterValidationError: 响应数据格式验证失败
"""

from __future__ import annotations

from typing import Any

from aury.boot.common.exceptions import FoundationError


class AdapterError(FoundationError):
    """第三方适配器通用错误。
    
    当第三方调用失败、返回错误码、数据解析异常等情况时抛出。
    
    Attributes:
        adapter_name: 适配器名称
        operation: 操作名称
        third_party_code: 第三方返回的错误码（如有）
        third_party_message: 第三方返回的错误消息（如有）
    
    使用示例:
        raise AdapterError(
            "支付失败",
            adapter_name="payment",
            operation="charge",
            third_party_code="INSUFFICIENT_FUNDS",
            third_party_message="余额不足",
        )
    """
    
    def __init__(
        self,
        message: str,
        *args: object,
        adapter_name: str | None = None,
        operation: str | None = None,
        third_party_code: str | None = None,
        third_party_message: str | None = None,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """初始化集成异常。
        
        Args:
            message: 错误消息
            adapter_name: 适配器名称
            operation: 操作名称
            third_party_code: 第三方错误码
            third_party_message: 第三方错误消息
            metadata: 额外元数据
            cause: 原始异常
        """
        self.adapter_name = adapter_name
        self.operation = operation
        self.third_party_code = third_party_code
        self.third_party_message = third_party_message
        
        # 构建完整的元数据
        full_metadata = metadata or {}
        if adapter_name:
            full_metadata["adapter_name"] = adapter_name
        if operation:
            full_metadata["operation"] = operation
        if third_party_code:
            full_metadata["third_party_code"] = third_party_code
        if third_party_message:
            full_metadata["third_party_message"] = third_party_message
        
        super().__init__(message, *args, metadata=full_metadata, cause=cause)
    
    def __str__(self) -> str:
        """返回异常字符串表示。"""
        parts = [self.message]
        if self.adapter_name:
            parts.append(f"adapter={self.adapter_name}")
        if self.operation:
            parts.append(f"operation={self.operation}")
        if self.third_party_code:
            parts.append(f"code={self.third_party_code}")
        return " | ".join(parts)


class AdapterDisabledError(AdapterError):
    """当前环境禁用了某个第三方功能。
    
    当 mode=disabled 或 enabled=False 时，调用任何操作都会抛出此异常。
    
    使用示例:
        # 在测试环境禁用支付功能
        settings = AdapterSettings(mode="disabled")
        adapter = PaymentAdapter("payment", settings)
        
        await adapter.charge(100)  # 抛出 AdapterDisabledError
    """
    
    def __init__(
        self,
        message: str,
        *args: object,
        adapter_name: str | None = None,
        operation: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """初始化禁用异常。"""
        super().__init__(
            message,
            *args,
            adapter_name=adapter_name,
            operation=operation,
            metadata=metadata,
        )


class AdapterTimeoutError(AdapterError):
    """第三方调用超时。
    
    当调用第三方接口超过配置的超时时间时抛出。
    
    Attributes:
        timeout_seconds: 超时时间（秒）
    """
    
    def __init__(
        self,
        message: str,
        *args: object,
        adapter_name: str | None = None,
        operation: str | None = None,
        timeout_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """初始化超时异常。"""
        self.timeout_seconds = timeout_seconds
        
        full_metadata = metadata or {}
        if timeout_seconds is not None:
            full_metadata["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message,
            *args,
            adapter_name=adapter_name,
            operation=operation,
            metadata=full_metadata,
            cause=cause,
        )


class AdapterValidationError(AdapterError):
    """第三方响应数据验证失败。
    
    当第三方返回的数据格式不符合预期时抛出。
    """
    
    def __init__(
        self,
        message: str,
        *args: object,
        adapter_name: str | None = None,
        operation: str | None = None,
        expected_format: str | None = None,
        actual_data: Any | None = None,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """初始化验证异常。"""
        full_metadata = metadata or {}
        if expected_format:
            full_metadata["expected_format"] = expected_format
        if actual_data is not None:
            # 截断过长的数据
            actual_str = str(actual_data)
            if len(actual_str) > 200:
                actual_str = actual_str[:200] + "..."
            full_metadata["actual_data"] = actual_str
        
        super().__init__(
            message,
            *args,
            adapter_name=adapter_name,
            operation=operation,
            metadata=full_metadata,
            cause=cause,
        )


__all__ = [
    "AdapterError",
    "AdapterDisabledError",
    "AdapterTimeoutError",
    "AdapterValidationError",
]

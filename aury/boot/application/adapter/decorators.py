"""第三方接口适配器装饰器。

提供 @adapter_method 装饰器，用于声明式定义 Adapter 方法和挡板（Mock）逻辑。

核心特性：
- 声明方法名称，用于配置层按方法覆盖模式（method_modes）
- 支持链式 .mock 注册挡板处理函数
- 自动根据 settings.mode 路由到真实调用或挡板逻辑
- 记录调用历史，便于测试断言

挡板定义方式：
1. @method.mock 装饰器：定义带逻辑的挡板函数，可以根据参数返回不同结果
2. mock_response 参数：简单场景直接指定固定响应值
3. 配置 mock_method_responses：按方法名配置固定响应
4. 配置 mock_default_response：全局默认响应

使用示例:
    class PaymentAdapter(HttpAdapter):
        # 方法 1：使用 @method.mock 定义挡板逻辑
        @adapter_method("create")
        async def create_order(self, amount: int, order_id: str) -> dict:
            # 真实调用逻辑
            return await self._request("POST", "/charge", json={...})
        
        @create_order.mock
        async def create_order_mock(self, amount: int, order_id: str) -> dict:
            # 挡板逻辑，可以模拟各种场景
            if amount > 10000:
                return {"success": False, "error": "金额超限"}  # 模拟失败
            return {"success": True, "mock": True}  # 模拟成功
        
        # 方法 2：简单场景直接指定固定响应
        @adapter_method("query", mock_response={"status": "paid", "mock": True})
        async def query_order(self, order_id: str) -> dict:
            return await self._request("GET", f"/orders/{order_id}")
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any, Awaitable, Callable, TypeVar

from aury.boot.common.logging import logger

from .config import AdapterMode
from .exceptions import AdapterDisabledError

if TYPE_CHECKING:
    from .base import BaseAdapter

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


@dataclass
class AdapterMethodMeta:
    """适配器方法元信息。
    
    存储 @adapter_method 装饰器声明的信息，包括：
    - 方法名称
    - mock 处理函数
    - 固定 mock 响应
    - 模式覆盖
    """
    
    name: str
    mock_handler: Callable[..., Awaitable[Any]] | None = None
    mock_response: Any = None
    mode_override: AdapterMode | None = None
    
    # 内部使用：原始真实方法
    _real_method: Callable[..., Awaitable[Any]] | None = field(default=None, repr=False)


class AdapterMethodDescriptor:
    """适配器方法描述符。
    
    实现类似 @property 的描述符协议，支持链式 .mock 注册。
    
    使用示例:
        class PaymentAdapter(HttpAdapter):
            @adapter_method("create")
            async def create_order(self, ...): ...
            
            @create_order.mock
            async def create_order_mock(self, ...): ...
    """
    
    def __init__(
        self,
        real_method: Callable[..., Awaitable[Any]],
        meta: AdapterMethodMeta,
    ) -> None:
        """初始化描述符。
        
        Args:
            real_method: 真实调用方法
            meta: 方法元信息
        """
        self._real_method = real_method
        self._meta = meta
        self._meta._real_method = real_method
        
        # 复制原方法的文档和名称
        self.__name__ = real_method.__name__
        self.__doc__ = real_method.__doc__
        self.__module__ = real_method.__module__
        self.__qualname__ = getattr(real_method, "__qualname__", real_method.__name__)
    
    def __get__(self, obj: BaseAdapter | None, objtype: type | None = None) -> Any:
        """描述符协议：获取绑定方法。"""
        if obj is None:
            # 类访问，返回描述符本身（用于 .mock 链式调用）
            return self
        
        # 实例访问，返回包装后的绑定方法
        return self._create_bound_method(obj)
    
    def __set_name__(self, owner: type, name: str) -> None:
        """描述符协议：设置属性名。"""
        self._attr_name = name
    
    def _create_bound_method(self, adapter: BaseAdapter) -> Callable[..., Awaitable[Any]]:
        """创建绑定到实例的方法。"""
        meta = self._meta
        real_method = self._real_method
        
        @wraps(real_method)
        async def bound_method(*args: Any, **kwargs: Any) -> Any:
            # 解析当前操作的有效模式
            mode = adapter._resolve_mode(meta)
            
            # 记录调用
            adapter._record_call(
                operation=meta.name,
                args=args,
                kwargs=kwargs,
                mode=mode,
            )
            
            # 检查是否禁用
            if not adapter.settings.enabled or mode == "disabled":
                raise AdapterDisabledError(
                    f"{adapter.name}.{meta.name} is disabled in current environment",
                    adapter_name=adapter.name,
                    operation=meta.name,
                )
            
            # mock 模式
            if mode == "mock":
                return await adapter._invoke_mock(meta, args, kwargs)
            
            # real / sandbox 模式：调用原始方法
            # 触发钩子
            await adapter._on_before_call(meta.name, args, kwargs)
            
            try:
                result = await real_method(adapter, *args, **kwargs)
                await adapter._on_after_call(meta.name, args, kwargs, result)
                return result
            except Exception as exc:
                await adapter._on_call_error(meta.name, args, kwargs, exc)
                raise
        
        return bound_method
    
    def mock(self, mock_method: F) -> F:
        """注册 mock 处理函数（链式装饰器）。
        
        使用示例:
            @adapter_method("create")
            async def create_order(self, ...): ...
            
            @create_order.mock
            async def create_order_mock(self, ...): ...
        
        Args:
            mock_method: mock 处理函数
            
        Returns:
            原始 mock 方法（保持可调用）
        """
        self._meta.mock_handler = mock_method
        logger.debug(f"Adapter 注册 mock handler: {self.__name__} -> {mock_method.__name__}")
        
        # 返回原方法，使其可以作为独立方法调用（如果需要）
        return mock_method


def adapter_method(
    name: str,
    *,
    mock_response: Any = None,
    mode_override: AdapterMode | None = None,
) -> Callable[[F], AdapterMethodDescriptor]:
    """适配器方法装饰器。
    
    声明一个 Adapter 方法，支持：
    - 根据配置自动切换 real/mock 模式
    - 链式 .mock 注册 mock 处理函数
    - 调用历史记录
    
    Args:
        name: 方法名称，用于配置层按方法覆盖模式
        mock_response: 简单 mock 场景的固定响应（可选）
        mode_override: 强制覆盖模式，不走配置（可选，用于某些方法必须真实调用的场景）
    
    使用示例:
        # 基础用法
        @adapter_method("create")
        async def create_order(self, amount: int) -> dict:
            return await self._request("POST", "/charge", json={"amount": amount})
        
        # 带固定 mock 响应
        @adapter_method("query", mock_response={"status": "paid", "mock": True})
        async def query_order(self, order_id: str) -> dict:
            return await self._request("GET", f"/orders/{order_id}")
        
        # 强制走真实（无论配置如何）
        @adapter_method("health", mode_override="real")
        async def health_check(self) -> dict:
            return await self._request("GET", "/health")
        
        # 链式 mock
        @adapter_method("create")
        async def create_order(self, amount: int) -> dict:
            return await self._request("POST", "/charge", json={"amount": amount})
        
        @create_order.mock
        async def create_order_mock(self, amount: int) -> dict:
            if amount > 10000:
                return {"success": False, "error": "超限"}
            return {"success": True, "mock": True, "amount": amount}
    
    Returns:
        装饰器函数
    """
    def decorator(fn: F) -> AdapterMethodDescriptor:
        meta = AdapterMethodMeta(
            name=name,
            mock_response=mock_response,
            mode_override=mode_override,
        )
        
        descriptor = AdapterMethodDescriptor(fn, meta)
        logger.debug(f"Adapter 注册方法: {fn.__name__} -> {name}")
        
        return descriptor
    
    return decorator


__all__ = [
    "AdapterMethodDescriptor",
    "AdapterMethodMeta",
    "adapter_method",
]

"""第三方接口适配器基类。

本模块用于封装第三方接口（如支付、短信、微信、云存储等外部服务）的调用，
提供统一的 Adapter 抽象，只约束"模式怎么切换"，不限制具体调用方式。
支持 HTTP、SDK、gRPC 等任意协议。

核心职责：
- 模式路由：real(生产)/sandbox(沙箱)/mock(挡板)/disabled(禁用)
- 调用历史记录：记录每次调用的参数、结果、耗时，便于测试断言
- 挡板调用分发：自动根据配置切换真实调用与挡板实现
- 生命周期钩子：before_call、after_call、on_error 等

挡板（Mock）配置说明：
1. 全局挡板：通过 settings.mode="mock" 设置整个 Adapter 使用挡板
2. 方法级挡板：通过 settings.method_modes={"create": "mock", "query": "real"}
   可以让不同方法使用不同模式（如查询走真实，写入走挡板）
3. 挡板实现：使用 @adapter_method("name") + @method.mock 装饰器定义挡板逻辑
4. 固定响应：简单场景可直接配置 mock_response 或 mock_method_responses

设计原则：
- 最小约束：只管模式路由，不限制调用方式
- 可扩展：通过钩子方法支持自定义行为
- 可观测：记录所有调用历史
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

from .config import AdapterMode, AdapterSettings

if TYPE_CHECKING:
    from .decorators import AdapterMethodMeta


@dataclass
class CallRecord:
    """调用记录。
    
    记录每次 Adapter 调用的详细信息，用于测试断言和调试。
    
    Attributes:
        operation: 操作名称
        args: 位置参数
        kwargs: 关键字参数
        mode: 调用时的模式
        timestamp: 调用时间戳
        result: 调用结果（如果成功）
        error: 异常信息（如果失败）
        duration_ms: 调用耗时（毫秒）
    """
    
    operation: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    mode: AdapterMode
    timestamp: datetime = field(default_factory=datetime.now)
    result: Any = None
    error: str | None = None
    duration_ms: float | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "operation": self.operation,
            "args": self.args,
            "kwargs": self.kwargs,
            "mode": self.mode,
            "timestamp": self.timestamp.isoformat(),
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class BaseAdapter:
    """第三方集成 Adapter 基类。
    
    封装模式路由和调用记录逻辑，子类只需实现具体的调用方法。
    
    核心功能：
    - 根据 settings.mode 和 operation_modes 自动路由
    - 支持 @adapter_method 装饰器声明的 mock 逻辑
    - 记录调用历史，便于测试断言
    - 提供生命周期钩子（before_call, after_call, on_error）
    
    使用示例:
        class PaymentAdapter(BaseAdapter):
            @adapter_method("create")
            async def create_order(self, amount: int) -> dict:
                # 这里是真实调用逻辑
                return await some_sdk.create(amount=amount)
            
            @create_order.mock
            async def create_order_mock(self, amount: int) -> dict:
                # mock 逻辑
                return {"success": True, "mock": True}
        
        # 使用
        settings = AdapterSettings(mode="mock")
        adapter = PaymentAdapter("payment", settings)
        result = await adapter.create_order(100)  # 走 mock
        
        # 测试断言
        assert len(adapter.call_history) == 1
        assert adapter.call_history[0].mode == "mock"
    
    Attributes:
        name: Adapter 名称（用于日志和异常信息）
        settings: 集成配置
    """
    
    def __init__(
        self,
        name: str,
        settings: AdapterSettings,
    ) -> None:
        """初始化 Adapter。
        
        Args:
            name: Adapter 名称
            settings: 集成配置
        """
        self.name = name
        self.settings = settings
        self._call_history: list[CallRecord] = []
        self._initialized = False
        
        logger.debug(
            f"初始化 Adapter: {name} | "
            f"mode={settings.mode} | "
            f"enabled={settings.enabled}"
        )
    
    # ========== 公共 API ==========
    
    @property
    def call_history(self) -> list[CallRecord]:
        """获取调用历史（只读）。
        
        Returns:
            list[CallRecord]: 调用记录列表
        """
        return list(self._call_history)
    
    def clear_history(self) -> None:
        """清空调用历史。
        
        通常在测试的 setUp 或 tearDown 中使用。
        """
        self._call_history.clear()
    
    def get_calls_by_operation(self, operation: str) -> list[CallRecord]:
        """获取指定操作的调用记录。
        
        Args:
            operation: 操作名称
            
        Returns:
            list[CallRecord]: 符合条件的调用记录
        """
        return [c for c in self._call_history if c.operation == operation]
    
    def get_last_call(self, operation: str | None = None) -> CallRecord | None:
        """获取最后一次调用记录。
        
        Args:
            operation: 操作名称（可选，不指定则返回最后一次任意调用）
            
        Returns:
            CallRecord | None: 最后一次调用记录
        """
        if operation:
            calls = self.get_calls_by_operation(operation)
            return calls[-1] if calls else None
        return self._call_history[-1] if self._call_history else None
    
    def assert_called(self, operation: str, times: int | None = None) -> None:
        """断言操作被调用（用于测试）。
        
        Args:
            operation: 操作名称
            times: 预期调用次数（可选，不指定则只检查是否被调用过）
            
        Raises:
            AssertionError: 断言失败
        """
        calls = self.get_calls_by_operation(operation)
        if times is not None:
            assert len(calls) == times, (
                f"Expected {operation} to be called {times} times, "
                f"but was called {len(calls)} times"
            )
        else:
            assert len(calls) > 0, f"Expected {operation} to be called, but was never called"
    
    def assert_not_called(self, operation: str) -> None:
        """断言操作未被调用（用于测试）。
        
        Args:
            operation: 操作名称
            
        Raises:
            AssertionError: 断言失败
        """
        calls = self.get_calls_by_operation(operation)
        assert len(calls) == 0, (
            f"Expected {operation} to not be called, "
            f"but was called {len(calls)} times"
        )
    
    # ========== 生命周期方法 ==========
    
    async def initialize(self) -> None:
        """初始化 Adapter（可选覆盖）。
        
        在首次使用前调用，用于初始化 SDK 客户端等资源。
        """
        if self._initialized:
            return
        await self._on_initialize()
        self._initialized = True
        logger.debug(f"Adapter 已初始化: {self.name}")
    
    async def cleanup(self) -> None:
        """清理 Adapter 资源（可选覆盖）。
        
        在关闭时调用，用于释放连接、关闭客户端等。
        """
        await self._on_cleanup()
        self._initialized = False
        logger.debug(f"Adapter 已清理: {self.name}")
    
    async def __aenter__(self) -> BaseAdapter:
        """异步上下文管理器入口。"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口。"""
        await self.cleanup()
    
    # ========== 内部方法（供装饰器使用） ==========
    
    def _resolve_mode(self, meta: AdapterMethodMeta) -> AdapterMode:
        """解析操作的有效模式。
        
        优先级：装饰器 mode_override > 配置 operation_modes > 配置全局 mode
        
        Args:
            meta: 操作元信息
            
        Returns:
            AdapterMode: 有效模式
        """
        # 1. 装饰器强制覆盖
        if meta.mode_override:
            return meta.mode_override
        
        # 2. 配置 per-method 覆盖
        if meta.name in self.settings.method_modes:
            return self.settings.method_modes[meta.name]
        
        # 3. 全局配置
        return self.settings.mode
    
    def _record_call(
        self,
        operation: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        mode: AdapterMode,
    ) -> CallRecord:
        """记录调用。
        
        Args:
            operation: 操作名称
            args: 位置参数
            kwargs: 关键字参数
            mode: 调用模式
            
        Returns:
            CallRecord: 调用记录
        """
        record = CallRecord(
            operation=operation,
            args=args,
            kwargs=kwargs,
            mode=mode,
        )
        self._call_history.append(record)
        
        logger.debug(
            f"Adapter 调用: {self.name}.{operation} | "
            f"mode={mode} | "
            f"args={args} | "
            f"kwargs={kwargs}"
        )
        
        return record
    
    async def _invoke_mock(
        self,
        meta: AdapterMethodMeta,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        """调用 mock 逻辑。
        
        优先级：
        1. 装饰器注册的 mock_handler（带逻辑）
        2. 装饰器的 mock_response（固定值）
        3. 配置的 mock_operation_responses（按操作）
        4. 配置的 mock_default_response（全局）
        5. 根据 mock_strategy 生成默认响应
        
        Args:
            meta: 操作元信息
            args: 位置参数
            kwargs: 关键字参数
            
        Returns:
            Any: mock 响应
        """
        # 模拟延迟
        if self.settings.mock_delay > 0:
            await asyncio.sleep(self.settings.mock_delay)
        
        # 1. 装饰器注册的 mock handler（带逻辑）
        if meta.mock_handler:
            logger.debug(f"使用 mock handler: {self.name}.{meta.name}")
            return await meta.mock_handler(self, *args, **kwargs)
        
        # 2. 装饰器的 mock_response
        if meta.mock_response is not None:
            logger.debug(f"使用装饰器 mock_response: {self.name}.{meta.name}")
            return meta.mock_response
        
        # 3. 配置的按方法 mock 响应
        method_response = self.settings.mock_method_responses.get(meta.name)
        if method_response is not None:
            logger.debug(f"使用配置 mock_method_responses: {self.name}.{meta.name}")
            return method_response
        
        # 4. 配置的全局 mock 响应
        if self.settings.mock_default_response is not None:
            logger.debug(f"使用配置 mock_default_response: {self.name}.{meta.name}")
            return self.settings.mock_default_response
        
        # 5. 根据策略生成默认响应
        return self._generate_mock_response(meta.name, args, kwargs)
    
    def _generate_mock_response(
        self,
        operation: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """根据 mock_strategy 生成默认响应。
        
        Args:
            operation: 操作名称
            args: 位置参数
            kwargs: 关键字参数
            
        Returns:
            dict: 默认 mock 响应
        """
        strategy = self.settings.mock_strategy
        
        if strategy == "success":
            return {
                "success": True,
                "mock": True,
                "gateway": self.name,
                "operation": operation,
            }
        
        if strategy == "failure":
            return {
                "success": False,
                "mock": True,
                "gateway": self.name,
                "operation": operation,
                "error": "mock failure",
            }
        
        if strategy == "echo":
            return {
                "success": True,
                "mock": True,
                "gateway": self.name,
                "operation": operation,
                "echo": {
                    "args": args,
                    "kwargs": kwargs,
                },
            }
        
        # noop / custom / 其他
        return {
            "success": True,
            "mock": True,
            "gateway": self.name,
            "operation": operation,
        }
    
    # ========== 钩子方法（子类可覆盖） ==========
    
    async def _on_initialize(self) -> None:
        """初始化钩子（子类可覆盖）。
        
        在 initialize() 中调用，用于初始化 SDK 客户端等。
        """
        pass
    
    async def _on_cleanup(self) -> None:
        """清理钩子（子类可覆盖）。
        
        在 cleanup() 中调用，用于释放资源。
        """
        pass
    
    async def _on_before_call(
        self,
        operation: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        """调用前钩子（子类可覆盖）。
        
        在真实调用前触发，可用于：
        - 参数验证
        - 日志记录
        - 指标采集
        
        Args:
            operation: 操作名称
            args: 位置参数
            kwargs: 关键字参数
        """
        pass
    
    async def _on_after_call(
        self,
        operation: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        result: Any,
    ) -> None:
        """调用后钩子（子类可覆盖）。
        
        在真实调用成功后触发，可用于：
        - 响应日志
        - 指标采集
        - 结果缓存
        
        Args:
            operation: 操作名称
            args: 位置参数
            kwargs: 关键字参数
            result: 调用结果
        """
        pass
    
    async def _on_call_error(
        self,
        operation: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        error: Exception,
    ) -> None:
        """调用异常钩子（子类可覆盖）。
        
        在真实调用抛出异常时触发，可用于：
        - 异常日志
        - 告警
        - 指标采集
        
        注意：此钩子不会吞掉异常，异常会继续向上抛出。
        
        Args:
            operation: 操作名称
            args: 位置参数
            kwargs: 关键字参数
            error: 异常对象
        """
        logger.error(
            f"Adapter 调用异常: {self.name}.{operation} | "
            f"error={type(error).__name__}: {error}"
        )
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name!r} "
            f"mode={self.settings.mode!r} "
            f"enabled={self.settings.enabled}>"
        )


__all__ = [
    "BaseAdapter",
    "CallRecord",
]

"""第三方接口适配器模块。

本模块用于封装第三方接口（如支付、短信、微信、云存储等外部服务）的调用，
解决测试环境中第三方接口不可用的问题，通过配置切换真实调用与挡板（Mock）实现。

核心特性:
- 多模式切换：real(真实)/sandbox(沙箱)/mock(挡板)/disabled(禁用)
- 按方法级别的模式覆盖：同一 Adapter 不同方法可用不同模式
- 装饰器声明式定义：@adapter_method + .mock 链式定义挡板逻辑
- HTTP 类第三方的便捷基类：HttpAdapter 封装请求/认证/错误处理
- 调用历史记录：便于测试断言，验证调用参数和结果

模式说明:
- real: 调用真实第三方接口（生产环境）
- sandbox: 调用第三方提供的沙箱环境（如果有）
- mock: 使用本地挡板实现，不发出真实请求（测试/开发环境）
- disabled: 禁用该接口，调用时抛出 AdapterDisabledError

设计原则:
- 最小约束：只约束"模式怎么切换"，不限制具体调用方式
- 最大自由：HTTP/SDK/gRPC/任意协议都能用
- 可组合：Adapter 可以组合其他 Adapter

典型使用场景:
1. 测试环境：第三方接口不可用，使用 mock 模式运行测试
2. 开发环境：避免消耗真实资源（如短信费用），使用 mock
3. 部分挡板：查询接口走真实，写入接口走 mock
4. 功能开关：禁用某些危险操作（如退款）在测试环境

使用示例:
    from aury.boot.application.adapter import (
        HttpAdapter, adapter_method, AdapterSettings
    )
    
    class PaymentAdapter(HttpAdapter):
        '''支付第三方接口适配器。'''
        
        @adapter_method("create")
        async def create_order(self, amount: int, order_id: str) -> dict:
            '''创建支付订单（真实实现）。'''
            return await self._request("POST", "/charge", json={"amount": amount, "order_id": order_id})
        
        @create_order.mock
        async def create_order_mock(self, amount: int, order_id: str) -> dict:
            '''创建支付订单（挡板实现）。
            
            挡板可以包含业务逻辑，模拟各种场景（成功、失败、边界情况）。
            '''
            if amount > 10000:
                return {"success": False, "error": "金额超限"}
            return {"success": True, "mock": True, "order_id": order_id}
    
    # 配置：测试环境使用挡板，但 query 走真实接口
    settings = AdapterSettings(
        mode="mock",                      # 默认走挡板
        method_modes={"query": "real"},   # query 走真实
        base_url="https://api.payment.com",
    )
    
    adapter = PaymentAdapter("payment", settings)
    result = await adapter.create_order(100, "order-1")  # 走挡板

环境变量配置:
    # 全局模式
    THIRD_PARTY_PAYMENT_MODE=mock
    
    # 连接配置
    THIRD_PARTY_PAYMENT_BASE_URL=https://api.payment.com
    THIRD_PARTY_PAYMENT_SANDBOX_URL=https://sandbox.payment.com
    THIRD_PARTY_PAYMENT_API_KEY=sk_test_xxx
    THIRD_PARTY_PAYMENT_TIMEOUT=30
    
    # 方法级模式覆盖（JSON 格式）
    THIRD_PARTY_PAYMENT_METHOD_MODES={"query": "real", "refund": "disabled"}
    
    # 挡板配置
    THIRD_PARTY_PAYMENT_MOCK_DELAY=0.1  # 模拟网络延迟
"""

from .base import BaseAdapter, CallRecord
from .config import (
    AdapterMode,
    AdapterSettings,
    MockStrategy,
    ThirdPartySettings,
)
from .decorators import adapter_method
from .exceptions import (
    AdapterDisabledError,
    AdapterError,
    AdapterTimeoutError,
)
from .http import HttpAdapter

__all__ = [
    # 基类
    "BaseAdapter",
    "HttpAdapter",
    # 配置
    "AdapterSettings",
    "AdapterMode",
    "MockStrategy",
    "ThirdPartySettings",
    # 装饰器
    "adapter_method",
    # 异常
    "AdapterError",
    "AdapterDisabledError",
    "AdapterTimeoutError",
    # 数据类
    "CallRecord",
]

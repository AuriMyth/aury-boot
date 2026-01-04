# Adapter（第三方接口适配器）

## 16.1 概述

Adapter 模块用于封装第三方接口（如支付、短信、微信等外部服务）的调用，支持在不同环境（开发、测试、生产）中灵活切换真实调用与 Mock 实现。

**核心特性**：
- 多模式支持：`real`（真实调用）、`sandbox`（沙箱环境）、`mock`（本地 Mock）、`disabled`（禁用）
- 方法级模式覆盖：同一 Adapter 的不同方法可以使用不同模式
- 装饰器式 Mock：使用 `.mock` 链式方法定义 Mock 逻辑
- 调用记录：测试时可追踪所有调用历史

## 16.2 基础用法

**文件**: `{package_name}/adapters/payment_adapter.py`

```python
"""支付适配器。"""

from aury.boot.application.adapter import (
    BaseAdapter,
    AdapterSettings,
    adapter_method,
)


class PaymentAdapter(BaseAdapter):
    """支付第三方适配器。"""

    @adapter_method("create_order")
    async def create_order(self, amount: int, order_id: str) -> dict:
        """创建支付订单（真实实现）。"""
        # 真实调用第三方 API
        response = await self.http_client.post(
            "https://api.payment.com/orders",
            json={"amount": amount, "order_id": order_id},
        )
        return response.json()

    @create_order.mock
    async def create_order_mock(self, amount: int, order_id: str) -> dict:
        """创建支付订单（Mock 实现）。"""
        if amount > 100000:
            return {"success": False, "error": "金额超限"}
        return {
            "success": True,
            "transaction_id": f"mock_tx_{order_id}",
            "amount": amount,
        }

    @adapter_method("query_order")
    async def query_order(self, transaction_id: str) -> dict:
        """查询支付订单。"""
        response = await self.http_client.get(
            f"https://api.payment.com/orders/{transaction_id}"
        )
        return response.json()

    @query_order.mock
    async def query_order_mock(self, transaction_id: str) -> dict:
        """查询支付订单（Mock）。"""
        return {
            "transaction_id": transaction_id,
            "status": "paid",
            "mock": True,
        }
```

## 16.3 Adapter 配置

### 环境变量配置

```bash
# .env

# 全局模式：real / sandbox / mock / disabled
THIRD_PARTY__GATEWAY_MODE=mock

# 方法级模式覆盖（JSON 格式）
# 例如：query 方法使用 real，其他方法使用全局配置
THIRD_PARTY__METHOD_MODES={"query_order": "real"}

# Mock 策略：decorator（装饰器）/ auto（自动生成）
THIRD_PARTY__MOCK_STRATEGY=decorator

# 调试模式
THIRD_PARTY__DEBUG=true
```

### 代码配置

```python
from aury.boot.application.adapter import AdapterSettings

# 方式 1：从环境变量加载
settings = AdapterSettings()

# 方式 2：代码显式配置
settings = AdapterSettings(
    mode="mock",
    method_modes={
        "query_order": "real",  # query_order 使用真实调用
        "create_order": "mock", # create_order 使用 Mock
    },
    debug=True,
)

# 创建 Adapter 实例
adapter = PaymentAdapter("payment", settings)
```

## 16.4 使用 HttpAdapter

对于 HTTP 类第三方 API，推荐使用 `HttpAdapter`：

```python
from aury.boot.application.adapter import HttpAdapter, AdapterSettings, adapter_method


class WechatAdapter(HttpAdapter):
    """微信 API 适配器。"""

    def __init__(self, settings: AdapterSettings | None = None):
        super().__init__(
            name="wechat",
            settings=settings,
            base_url="https://api.weixin.qq.com",
            timeout=30.0,
        )

    async def _prepare_headers(self, headers: dict | None) -> dict:
        """添加认证头。"""
        headers = await super()._prepare_headers(headers)
        headers["Authorization"] = f"Bearer {await self._get_access_token()}"
        return headers

    @adapter_method("send_message")
    async def send_message(self, openid: str, content: str) -> dict:
        """发送消息。"""
        return await self._request(
            "POST",
            "/cgi-bin/message/send",
            json={"touser": openid, "content": content},
        )

    @send_message.mock
    async def send_message_mock(self, openid: str, content: str) -> dict:
        """发送消息（Mock）。"""
        return {"errcode": 0, "errmsg": "ok", "mock": True}
```

## 16.5 方法级模式覆盖

同一 Adapter 的不同方法可以使用不同模式：

```python
settings = AdapterSettings(
    mode="mock",  # 默认 Mock
    method_modes={
        "query_order": "real",      # 查询走真实接口
        "create_order": "mock",     # 创建走 Mock
        "refund": "disabled",       # 退款禁用
    },
)

adapter = PaymentAdapter("payment", settings)

# query_order 会调用真实 API
result = await adapter.query_order("tx_123")

# create_order 会调用 Mock 方法
result = await adapter.create_order(100, "order_123")

# refund 会抛出 AdapterDisabledError
result = await adapter.refund("tx_123")  # 抛出异常
```

## 16.6 测试中使用

### 调用记录追踪

```python
import pytest
from {package_name}.adapters.payment_adapter import PaymentAdapter
from aury.boot.application.adapter import AdapterSettings


@pytest.fixture
def payment_adapter():
    settings = AdapterSettings(mode="mock")
    return PaymentAdapter("payment", settings)


async def test_create_order(payment_adapter):
    """测试创建订单。"""
    result = await payment_adapter.create_order(100, "order_001")

    assert result["success"] is True
    assert result["mock"] is True

    # 检查调用记录
    history = payment_adapter.call_history
    assert len(history) == 1
    assert history[0].method == "create_order"
    assert history[0].args == (100, "order_001")
    assert history[0].result == result


async def test_amount_limit(payment_adapter):
    """测试金额超限。"""
    result = await payment_adapter.create_order(200000, "order_002")

    assert result["success"] is False
    assert "超限" in result["error"]


async def test_clear_history(payment_adapter):
    """测试清除调用记录。"""
    await payment_adapter.create_order(100, "order_001")
    await payment_adapter.query_order("tx_001")

    assert len(payment_adapter.call_history) == 2

    payment_adapter.clear_history()
    assert len(payment_adapter.call_history) == 0
```

## 16.7 高级用法

### 钩子方法

```python
class PaymentAdapter(HttpAdapter):
    """带钩子的支付适配器。"""

    async def _on_before_call(
        self, method: str, args: tuple, kwargs: dict
    ) -> None:
        """调用前钩子。"""
        logger.info(f"调用 {method}，参数: {args}")

    async def _on_after_call(
        self, method: str, args: tuple, kwargs: dict, result: Any
    ) -> None:
        """调用后钩子。"""
        logger.info(f"{method} 返回: {result}")

    async def _on_call_error(
        self, method: str, args: tuple, kwargs: dict, error: Exception
    ) -> None:
        """调用异常钩子。"""
        logger.error(f"{method} 异常: {error}")
        # 可以在这里发送告警
```

### 复合适配器

```python
class CompositePaymentAdapter(BaseAdapter):
    """组合多个支付渠道。"""

    def __init__(self, settings: AdapterSettings | None = None):
        super().__init__("composite_payment", settings)
        self.alipay = AlipayAdapter(settings)
        self.wechat = WechatAdapter(settings)

    @adapter_method("pay")
    async def pay(self, channel: str, amount: int, order_id: str) -> dict:
        """根据渠道选择支付方式。"""
        if channel == "alipay":
            return await self.alipay.create_order(amount, order_id)
        elif channel == "wechat":
            return await self.wechat.create_order(amount, order_id)
        else:
            raise ValueError(f"不支持的支付渠道: {channel}")

    @pay.mock
    async def pay_mock(self, channel: str, amount: int, order_id: str) -> dict:
        """统一 Mock 实现。"""
        return {
            "success": True,
            "channel": channel,
            "transaction_id": f"mock_{channel}_{order_id}",
        }
```

## 16.8 异常处理

```python
from aury.boot.application.adapter import (
    AdapterError,
    AdapterDisabledError,
    AdapterTimeoutError,
    AdapterValidationError,
)

try:
    result = await adapter.create_order(100, "order_001")
except AdapterDisabledError:
    logger.warning("支付适配器已禁用")
    # 降级处理
except AdapterTimeoutError:
    logger.error("支付适配器超时")
    # 重试或告警
except AdapterValidationError as e:
    logger.error(f"参数校验失败: {e}")
except AdapterError as e:
    logger.error(f"适配器错误: {e}")
```

## 16.9 最佳实践

### 1. Adapter 放置位置

```
{package_name}/
├── adapters/                 # 第三方适配器
│   ├── __init__.py
│   ├── payment_adapter.py    # 支付适配器
│   ├── sms_adapter.py        # 短信适配器
│   └── wechat_adapter.py     # 微信适配器
```

### 2. Mock 逻辑应覆盖边界情况

```python
@create_order.mock
async def create_order_mock(self, amount: int, order_id: str) -> dict:
    """Mock 应模拟各种场景。"""
    # 模拟金额校验
    if amount <= 0:
        return {"success": False, "error": "金额必须大于0"}
    if amount > 100000:
        return {"success": False, "error": "金额超限"}

    # 模拟偶发失败（可选）
    import random
    if random.random() < 0.01:
        return {"success": False, "error": "系统繁忙"}

    return {"success": True, "transaction_id": f"mock_{order_id}"}
```

### 3. 环境配置建议

```bash
# 开发环境 (.env.development)
THIRD_PARTY__GATEWAY_MODE=mock
THIRD_PARTY__DEBUG=true

# 测试环境 (.env.testing)
THIRD_PARTY__GATEWAY_MODE=mock
THIRD_PARTY__METHOD_MODES={"query": "sandbox"}

# 生产环境 (.env.production)
THIRD_PARTY__GATEWAY_MODE=real
THIRD_PARTY__DEBUG=false
```

### 4. 在 Service 中使用

```python
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.domain.service.base import BaseService
from aury.boot.domain.transaction import transactional

from {package_name}.adapters.payment_adapter import PaymentAdapter
from {package_name}.repositories.order_repository import OrderRepository


class OrderService(BaseService):
    """订单服务。"""

    def __init__(self, session: AsyncSession, payment: PaymentAdapter):
        super().__init__(session)
        self.order_repo = OrderRepository(session)
        self.payment = payment

    @transactional
    async def create_order(self, user_id: str, amount: int) -> Order:
        """创建订单并发起支付。"""
        # 1. 创建订单记录
        order = await self.order_repo.create({
            "user_id": user_id,
            "amount": amount,
            "status": "pending",
        })

        # 2. 调用支付适配器
        pay_result = await self.payment.create_order(amount, str(order.id))

        if not pay_result["success"]:
            raise PaymentError(pay_result["error"])

        # 3. 更新订单状态
        await self.order_repo.update(order, {
            "transaction_id": pay_result["transaction_id"],
            "status": "paid",
        })

        return order
```

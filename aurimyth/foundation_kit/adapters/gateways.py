"""三方网关适配器伪代码。"""


class PaymentGateway:  # pragma: no cover - fake
    """支付网关示例。"""

    async def charge(self, amount: float):
        """发起扣款。"""

        raise NotImplementedError



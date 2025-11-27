"""第三方服务适配器。

提供支付、消息、存储等第三方服务的适配器。
这些适配器是公共的，所有应用都可以使用。
"""

from .clients import WebhookClient
from .gateways import PaymentGateway
from .third_party_clients import ThirdPartyClient

__all__ = [
    "WebhookClient",
    "PaymentGateway",
    "ThirdPartyClient",
]


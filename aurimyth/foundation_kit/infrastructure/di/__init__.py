"""依赖注入模块。

提供依赖注入容器和相关功能。
"""

from .container import Container, Lifetime, Scope, ServiceDescriptor

__all__ = [
    "Container",
    "Lifetime",
    "Scope",
    "ServiceDescriptor",
]



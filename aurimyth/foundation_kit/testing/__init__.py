"""测试框架模块。

提供便捷的测试工具，包括测试基类、测试客户端、数据工厂等。
"""

from .base import TestCase
from .client import TestClient
from .factory import Factory

__all__ = [
    "Factory",
    "TestCase",
    "TestClient",
]

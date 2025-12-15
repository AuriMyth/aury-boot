"""测试框架模块。

提供便捷的测试工具，包括测试基类、测试客户端、数据工厂等。

注意：此模块需要 pytest 作为依赖，仅在开发环境可用。
生产环境不会安装此模块的依赖，导入时会静默失败。
"""

# 检查 pytest 是否可用，如果不可用则静默失败（让外层捕获）
try:
    import pytest
except ImportError:
    # 在生产环境，pytest 不存在，让导入失败以便外层捕获
    raise ImportError("testing 模块需要 pytest，仅在开发环境可用")

from .base import TestCase
from .client import TestClient
from .factory import Factory

__all__ = [
    "Factory",
    "TestCase",
    "TestClient",
]

"""Aury Boot - 核心基础架构工具包。

提供数据库、缓存、认证等核心基础设施功能。

模块结构：
- common: 最基础层（异常基类、日志系统、国际化）
- domain: 领域层（业务模型、仓储接口、服务基类、分页、事务管理）
- infrastructure: 基础设施层（外部依赖的实现：数据库、缓存、存储、调度器等）
- application: 应用层（配置管理、RPC通信、依赖注入、事务管理、事件系统、迁移管理、API接口）
- toolkit: 工具包（通用工具函数）
- testing: 测试框架（测试基类、测试客户端、数据工厂）

使用方式：
    from aury.boot import application
    from aury.boot.domain.models import Model
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

# 版本号由 hatch-vcs 自动生成
try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

# 延迟导入：子模块仅在被访问时才加载
_SUBMODULES = {
    "application",
    "common",
    "domain",
    "infrastructure",
    "toolkit",
    "testing",
}


def __getattr__(name: str):
    """延迟导入子模块。"""
    if name in _SUBMODULES:
        try:
            return importlib.import_module(f".{name}", __name__)
        except ImportError:
            if name == "testing":
                # testing 模块可能在生产环境不可用
                return None
            raise
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """返回可用属性列表。"""
    return [*list(_SUBMODULES), "__version__"]


__all__ = [
    "__version__",
    "application",
    "common",
    "domain",
    "infrastructure",
    "testing",
    "toolkit",
]

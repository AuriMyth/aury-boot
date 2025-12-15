"""命令行工具模块。

统一入口: aum
"""

from __future__ import annotations

# 轻量配置模块可以直接导入
from .config import ProjectConfig, get_project_config, save_project_config


# 延迟导入 app 和 main，避免加载重型依赖
def __getattr__(name: str):
    if name in ("app", "main"):
        from .app import main as _main
        if name == "main":
            return _main
        # app 通过 app 模块的 __getattr__ 获取
        from . import app as app_module
        return app_module.app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "app",
    "main",
    "ProjectConfig",
    "get_project_config",
    "save_project_config",
]

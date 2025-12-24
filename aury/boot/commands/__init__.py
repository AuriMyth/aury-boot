"""命令行工具模块。

统一入口: aury

CLI 继承接口：
    子框架（如 aury-django、aury-cloud）可以通过以下接口继承基础命令：
    
    - register_commands(app): 将所有命令注册到目标 app
    - get_command_modules(): 获取所有命令模块，供进一步定制
    
    示例:
        ```python
        from typer import Typer
        from aury.boot.commands import register_commands
        
        app = Typer(name="aury-django")
        register_commands(app)  # 继承所有命令
        ```
"""

from __future__ import annotations

# 轻量配置模块可以直接导入
from .config import ProjectConfig, get_project_config, save_project_config


# 延迟导入 app、main、register_commands、get_command_modules，避免加载重型依赖
def __getattr__(name: str):
    if name in ("app", "main", "register_commands", "get_command_modules"):
        from .app import _get_app, get_command_modules, main, register_commands
        if name == "main":
            return main
        if name == "app":
            return _get_app()
        if name == "register_commands":
            return register_commands
        if name == "get_command_modules":
            return get_command_modules
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ProjectConfig",
    "app",
    "get_command_modules",
    "get_project_config",
    "main",
    "register_commands",
    "save_project_config",
]

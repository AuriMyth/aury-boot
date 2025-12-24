"""Aury Boot 统一命令行入口。

提供统一的 CLI 入口，整合所有子命令：
- aury init              项目脚手架初始化
- aury generate          代码生成器
- aury server            服务器管理
- aury scheduler         独立运行调度器
- aury worker            运行任务队列 Worker
- aury migrate           数据库迁移
- aury docker            Docker 配置生成
- aury docs              生成/更新项目文档

使用示例：
    aury init                      # 初始化项目
    aury generate crud user        # 生成 CRUD 代码
    aury server dev                # 启动开发服务器
    aury scheduler                 # 独立运行调度器
    aury worker                    # 运行 Worker
    aury migrate up                # 执行数据库迁移
    aury docs all --force          # 更新所有文档

CLI 继承：
    子框架（如 aury-django、aury-cloud）可以通过 `register_commands` 继承所有基础命令：
    
    ```python
    from typer import Typer
    from aury.boot.commands import register_commands
    
    app = Typer(name="aury-django")
    register_commands(app)  # 继承所有 aury-boot 命令
    
    # 添加 django 特有命令
    @app.command()
    def startapp(name: str):
        ...
    ```
"""

from __future__ import annotations

import typer

app: typer.Typer | None = None
_registered = False


def _get_app() -> typer.Typer:
    """获取并初始化 Typer 应用（延迟加载）。"""
    global app, _registered
    
    if app is None:
        app = typer.Typer(
            name="aury",
            help="🚀 Aury Boot CLI - 现代化微服务开发工具",
            add_completion=True,
            no_args_is_help=True,
            rich_markup_mode="rich",
        )
        
        @app.callback(invoke_without_command=True)
        def callback(
            ctx: typer.Context,
            version: bool = typer.Option(
                False,
                "--version",
                "-v",
                help="显示版本信息",
                is_eager=True,
            ),
        ) -> None:
            """Aury Boot - 现代化微服务基础架构框架。"""
            if version:
                from rich.console import Console

                from aury.boot import __version__
                console = Console()
                console.print(f"[bold cyan]Aury Boot[/bold cyan] v{__version__}")
                raise typer.Exit()
    
    if not _registered:
        _registered = True
        # 延迟导入子命令
        from .add import app as add_app
        from .docker import app as docker_app
        from .docs import app as docs_app
        from .generate import app as generate_app
        from .init import init
        from .migrate import app as migrate_app
        from .scheduler import app as scheduler_app
        from .server import app as server_app
        from .worker import app as worker_app

        app.command(name="init", help="🎯 初始化项目脚手架")(init)
        app.add_typer(add_app, name="add", help="➕ 添加可选模块")
        app.add_typer(generate_app, name="generate", help="⚡ 代码生成器")
        app.add_typer(server_app, name="server", help="🖥️  服务器管理")
        app.add_typer(scheduler_app, name="scheduler", help="🕐 独立运行调度器")
        app.add_typer(worker_app, name="worker", help="⚙️  运行任务队列 Worker")
        app.add_typer(migrate_app, name="migrate", help="🗃️  数据库迁移")
        app.add_typer(docker_app, name="docker", help="🐳 Docker 配置")
        app.add_typer(docs_app, name="docs", help="📚 生成/更新项目文档")
    
    return app


def main() -> None:
    """CLI 入口点。"""
    _get_app()()


def register_commands(
    target_app: typer.Typer,
    *,
    include_init: bool = True,
    include_add: bool = True,
    include_generate: bool = True,
    include_server: bool = True,
    include_scheduler: bool = True,
    include_worker: bool = True,
    include_migrate: bool = True,
    include_docker: bool = True,
    include_docs: bool = True,
) -> None:
    """将 aury-boot 的所有命令注册到目标 Typer app。
    
    用于子框架（如 aury-django、aury-cloud）继承基础命令。
    
    Args:
        target_app: 目标 Typer 应用
        include_*: 是否包含对应的命令组
    
    使用示例:
        ```python
        from typer import Typer
        from aury.boot.commands import register_commands
        
        app = Typer(name="aury-django")
        
        # 继承所有 aury-boot 命令
        register_commands(app)
        
        # 或选择性继承
        register_commands(app, include_docker=False)
        
        # 添加 django 特有命令
        django_app = Typer(name="django")
        
        @django_app.command()
        def startapp(name: str):
            '''Django startapp'''
            ...
        
        app.add_typer(django_app, name="django")
        ```
    """
    # 延迟导入子命令
    if include_init:
        from .init import init
        target_app.command(name="init", help="🎯 初始化项目脚手架")(init)
    
    if include_add:
        from .add import app as add_app
        target_app.add_typer(add_app, name="add", help="➕ 添加可选模块")
    
    if include_generate:
        from .generate import app as generate_app
        target_app.add_typer(generate_app, name="generate", help="⚡ 代码生成器")
    
    if include_server:
        from .server import app as server_app
        target_app.add_typer(server_app, name="server", help="🖥️  服务器管理")
    
    if include_scheduler:
        from .scheduler import app as scheduler_app
        target_app.add_typer(scheduler_app, name="scheduler", help="🕐 独立运行调度器")
    
    if include_worker:
        from .worker import app as worker_app
        target_app.add_typer(worker_app, name="worker", help="⚙️  运行任务队列 Worker")
    
    if include_migrate:
        from .migrate import app as migrate_app
        target_app.add_typer(migrate_app, name="migrate", help="🗃️  数据库迁移")
    
    if include_docker:
        from .docker import app as docker_app
        target_app.add_typer(docker_app, name="docker", help="🐳 Docker 配置")
    
    if include_docs:
        from .docs import app as docs_app
        target_app.add_typer(docs_app, name="docs", help="📚 生成/更新项目文档")


def get_command_modules() -> dict[str, type]:
    """获取所有命令模块，供子框架进一步定制。
    
    Returns:
        dict: 命令名 -> 模块对象
    
    使用示例:
        ```python
        from aury.boot.commands import get_command_modules
        
        modules = get_command_modules()
        # {'init': <module>, 'add': <module>, 'server': <module>, ...}
        ```
    """
    from . import add, docker, docs, generate, init, migrate, scheduler, server, worker
    
    return {
        "init": init,
        "add": add,
        "generate": generate,
        "server": server,
        "scheduler": scheduler,
        "worker": worker,
        "migrate": migrate,
        "docker": docker,
        "docs": docs,
    }


# 允许 `from .app import app`
def __getattr__(name: str):
    if name == "app":
        return _get_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "app",
    "get_command_modules",
    "main",
    "register_commands",
]

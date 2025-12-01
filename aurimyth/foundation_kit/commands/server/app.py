"""服务器运行命令实现。"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from aurimyth.foundation_kit.application.app.base import FoundationApp

# 创建 Typer 应用
app = typer.Typer(
    name="server",
    help="ASGI 服务器管理工具",
    add_completion=False,
)


def _get_app_instance() -> FoundationApp:
    """动态导入并获取应用实例。
    
    Returns:
        FoundationApp: 应用实例
        
    Raises:
        SystemExit: 如果无法找到应用
    """
    try:
        # 尝试从当前工作目录的 main.py 导入 app
        sys.path.insert(0, os.getcwd())
        
        try:
            from main import app  # type: ignore
            return app
        except ImportError as e:
            typer.echo("❌ 错误：无法找到 app 实例", err=True)
            typer.echo(
                "请确保在项目根目录运行此命令，或在 main.py 中定义 app 变量",
                err=True,
            )
            raise typer.Exit(1) from e
    finally:
        if os.getcwd() in sys.path:
            sys.path.remove(os.getcwd())


@app.command()
def run(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        envvar="SERVER_HOST",
        help="监听地址",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        envvar="SERVER_PORT",
        help="监听端口",
    ),
    workers: int = typer.Option(
        1,
        "--workers",
        "-w",
        envvar="SERVER_WORKERS",
        help="工作进程数",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        envvar="SERVER_RELOAD",
        help="启用热重载（开发模式）",
    ),
    reload_dir: list[str] = typer.Option(
        None,
        "--reload-dir",
        envvar="SERVER_RELOAD_DIR",
        help="热重载监控目录（可以指定多次）",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        envvar="DEBUG",
        help="启用调试模式",
    ),
    loop: str = typer.Option(
        "auto",
        "--loop",
        help="事件循环实现",
    ),
    http: str = typer.Option(
        "auto",
        "--http",
        help="HTTP 协议版本",
    ),
    ssl_keyfile: str | None = typer.Option(
        None,
        "--ssl-keyfile",
        help="SSL 密钥文件路径",
    ),
    ssl_certfile: str | None = typer.Option(
        None,
        "--ssl-certfile",
        help="SSL 证书文件路径",
    ),
    no_access_log: bool = typer.Option(
        False,
        "--no-access-log",
        help="禁用访问日志",
    ),
) -> None:
    """运行开发/生产服务器。
    
    示例：
    
        # 开发模式（热重载）
        aurimyth-server run --reload
        
        # 生产模式（多进程）
        aurimyth-server run --workers 4
        
        # HTTPS
        aurimyth-server run --ssl-keyfile key.pem --ssl-certfile cert.pem
    """
    from aurimyth.foundation_kit.application.server import ApplicationServer
    
    app_instance = _get_app_instance()
    
    # 创建服务器配置
    reload_dirs = reload_dir if reload_dir else None
    
    typer.echo(f"🚀 启动服务器...")
    typer.echo(f"   地址: http://{host}:{port}")
    typer.echo(f"   工作进程: {workers}")
    typer.echo(f"   热重载: {'✅' if reload else '❌'}")
    typer.echo(f"   调试模式: {'✅' if debug else '❌'}")
    
    if reload:
        typer.echo(f"   监控目录: {reload_dirs or ['./']}")
    
    # 创建并运行服务器
    try:
        server = ApplicationServer(
            app=app_instance,
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            reload_dirs=reload_dirs,
            loop=loop,
            http=http,
            debug=debug,
            access_log=not no_access_log,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
        )
        server.run()
    except KeyboardInterrupt:
        typer.echo("\n👋 服务器已停止")
    except Exception as e:
        typer.echo(f"❌ 错误：{e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def dev(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        envvar="SERVER_HOST",
        help="监听地址",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        envvar="SERVER_PORT",
        help="监听端口",
    ),
) -> None:
    """启动开发服务器（热重载）。
    
    快捷命令，相当于 run --reload --debug
    
    示例：
        aurimyth-server dev
        aurimyth-server dev --port 9000
    """
    # 直接调用 run 函数的逻辑
    run(
        host=host,
        port=port,
        workers=1,
        reload=True,
        reload_dir=["src/"],
        debug=True,
        loop="auto",
        http="auto",
        ssl_keyfile=None,
        ssl_certfile=None,
        no_access_log=False,
    )


@app.command()
def prod(
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        envvar="SERVER_HOST",
        help="监听地址",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        envvar="SERVER_PORT",
        help="监听端口",
    ),
    workers: int | None = typer.Option(
        None,
        "--workers",
        "-w",
        envvar="SERVER_WORKERS",
        help="工作进程数（默认：CPU核心数）",
    ),
) -> None:
    """启动生产服务器（多进程）。
    
    快捷命令，相当于 run --workers <cpu_count>
    
    示例：
        aurimyth-server prod
        aurimyth-server prod --workers 8
    """
    import os as os_module
    
    # 如果没有指定 workers，使用 CPU 核心数
    if workers is None:
        workers = os_module.cpu_count() or 4
    
    # 直接调用 run 函数的逻辑
    run(
        host=host,
        port=port,
        workers=workers,
        reload=False,
        reload_dir=None,
        debug=False,
        loop="auto",
        http="auto",
        ssl_keyfile=None,
        ssl_certfile=None,
        no_access_log=False,
    )


def server_cli() -> None:
    """CLI 入口点。
    
    使用示例:
        if __name__ == "__main__":
            server_cli()
    """
    app()


__all__ = [
    "app",
    "dev",
    "prod",
    "run",
    "server_cli",
]


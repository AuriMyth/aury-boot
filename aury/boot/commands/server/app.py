"""服务器运行命令实现。"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import typer
import uvicorn

if TYPE_CHECKING:
    from aury.boot.application.app.base import FoundationApp

# 创建 Typer 应用
app = typer.Typer(
    name="server",
    help="ASGI 服务器管理工具",
    add_completion=False,
)


def _detect_app_module() -> str:
    """自动检测应用模块路径。

    检测顺序：
    1. 环境变量 APP_MODULE
    2. pyproject.toml 的 [tool.aury].app
    3. 安装包的 entry points: [project.entry-points."aury.app"]
    4. 默认 main:app

    注意：main.py 默认在项目根目录。
    """
    # 1. 环境变量优先
    if env_app := os.environ.get("APP_MODULE"):
        return env_app

    # 2. 读取 pyproject.toml 配置
    try:
        from ..config import get_project_config
        cfg = get_project_config()
        if cfg.app:
            return cfg.app
    except Exception:
        pass

    # 3. 读取安装包 entry points（生产环境常用）
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="aury.app")
        # 优先名为 default 的项，否则取第一个
        if eps:
            ep = next((e for e in eps if e.name == "default"), eps[0])
            return ep.value
    except Exception:
        pass

    # 4. 默认
    return "main:app"


def _get_app_instance(app_path: str | None = None) -> FoundationApp:
    """动态导入并获取应用实例。

    Args:
        app_path: 应用模块路径，格式为 "module.path:variable"
                  例如: "main:app", "myproject.main:application"
                  如果不提供，会自动检测

    Returns:
        FoundationApp: 应用实例

    Raises:
        SystemExit: 如果无法找到应用
    """
    import importlib

    # 自动检测应用模块
    if app_path is None:
        app_path = _detect_app_module()
    
    # 解析模块路径
    if ":" not in app_path:
        typer.echo(f"❌ 错误：无效的 app 路径格式: {app_path}", err=True)
        typer.echo("格式应为: module.path:variable，例如: main:app", err=True)
        raise typer.Exit(1)
    
    module_path, var_name = app_path.rsplit(":", 1)
    
    try:
        # 添加当前工作目录到 sys.path
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        
        # 导入模块
        module = importlib.import_module(module_path)
        
        # 获取 app 实例
        if not hasattr(module, var_name):
            typer.echo(f"❌ 错误：模块 {module_path} 中找不到变量 {var_name}", err=True)
            raise typer.Exit(1)
        
        app_instance = getattr(module, var_name)
        return app_instance
        
    except ImportError as e:
        typer.echo(f"❌ 错误：无法导入模块 {module_path}", err=True)
        typer.echo(f"   {e}", err=True)
        typer.echo("请确保在项目根目录运行此命令", err=True)
        raise typer.Exit(1) from e


@app.command()
def run(
    app_path: str | None = typer.Option(
        None,
        "--app",
        "-a",
        envvar="APP_MODULE",
        help="应用模块路径，格式: module.path:variable（默认自动检测）",
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        "-h",
        help="监听地址（默认使用配置文件中的 SERVER_HOST）",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="监听端口（默认使用配置文件中的 SERVER_PORT）",
    ),
    workers: int | None = typer.Option(
        None,
        "--workers",
        "-w",
        help="工作进程数（默认使用配置文件中的 SERVER_WORKERS）",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="启用热重载（开发模式）",
    ),
    reload_dir: list[str] | None = typer.Option(
        None,
        "--reload-dir",
        help="热重载监控目录（可以指定多次）",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
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
    
    配置优先级: 命令行参数 > .env/环境变量 > 默认值
    
    示例：
    
        # 指定 app 模块
        aury server run --app myproject.main:app
        
        # 开发模式（热重载）
        aury server run --reload
        
        # 生产模式（多进程）
        aury server run --workers 4
        
        # HTTPS
        aury server run --ssl-keyfile key.pem --ssl-certfile cert.pem
    """
    from aury.boot.application.server import ApplicationServer
    
    app_instance = _get_app_instance(app_path)
    
    # 优先使用命令行参数，否则使用 app 配置
    server_host = host if host is not None else app_instance.config.server.host
    server_port = port if port is not None else app_instance.config.server.port
    server_workers = workers if workers is not None else app_instance.config.server.workers
    
    # 创建服务器配置
    reload_dirs = reload_dir if reload_dir else None
    
    typer.echo("🚀 启动服务器...")
    typer.echo(f"   地址: http://{server_host}:{server_port}")
    typer.echo(f"   工作进程: {server_workers}")
    typer.echo(f"   热重载: {'✅' if reload else '❌'}")
    typer.echo(f"   调试模式: {'✅' if debug else '❌'}")
    
    if reload:
        typer.echo(f"   监控目录: {reload_dirs or ['./']}")
    
    # 创建并运行服务器
    try:
        if reload:
            # 热重载模式：直接使用 uvicorn，传递 app 字符串路径
            import uvicorn
            app_module_path = app_path or _detect_app_module()
            uvicorn.run(
                app=app_module_path,
                host=server_host,
                port=server_port,
                reload=True,
                reload_dirs=reload_dirs,
                log_level="debug" if debug else "info",
                # 优雅关闭超时，确保 WS/SSE 连接有时间关闭
                timeout_graceful_shutdown=5,
            )
        else:
            # 非热重载模式：使用 ApplicationServer
            server = ApplicationServer(
                app=app_instance,
                host=server_host,
                port=server_port,
                workers=server_workers,
                reload=False,
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
    app_path: str | None = typer.Option(
        None,
        "--app",
        "-a",
        envvar="APP_MODULE",
        help="应用模块路径，格式: module.path:variable（默认自动检测）",
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        "-h",
        help="监听地址（默认使用配置文件中的 SERVER_HOST）",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="监听端口（默认使用配置文件中的 SERVER_PORT）",
    ),
    reload_include: list[str] | None = typer.Option(
        None,
        "--include",
        help="追加监控的文件模式（可多次指定，如 --include '*.jinja2'）",
    ),
    reload_exclude: list[str] | None = typer.Option(
        None,
        "--exclude",
        help="追加排除的文件模式（可多次指定，如 --exclude 'static/*'）",
    ),
) -> None:
    """启动开发服务器（热重载）。
    
    快捷命令，相当于 run --reload --debug
    
    配置优先级: 命令行参数 > .env/环境变量 > 默认值
    
    示例：
        aury server dev
        aury server dev --app myproject.main:app
        aury server dev --port 9000
    """
    app_instance = _get_app_instance(app_path)
    
    # 优先使用命令行参数，否则使用 app 配置
    server_host = host if host is not None else app_instance.config.server.host
    server_port = port if port is not None else app_instance.config.server.port

    # 构建默认监控目录：优先仅监控项目包目录，避免监控根目录导致日志等文件触发重载
    cwd = Path.cwd()
    reload_dirs: list[str] = []

    cfg = None
    try:
        from ..config import get_project_config
        cfg = get_project_config()
        if cfg.has_package:
            pkg_path = cwd / cfg.package
            if pkg_path.exists():
                reload_dirs.append(str(pkg_path))
    except Exception:
        pass

    # 如果没有检测到包目录，则退回到当前目录（单文件/平铺项目）
    if not reload_dirs:
        reload_dirs = [str(cwd)]

    # 去重
    seen = set()
    reload_dirs = [d for d in reload_dirs if not (d in seen or seen.add(d))]

    # 获取 app 模块路径（热重载需要字符串格式）
    app_module_path = app_path or _detect_app_module()
    
    typer.echo("🚀 启动开发服务器...")
    typer.echo(f"   地址: http://{server_host}:{server_port}")
    typer.echo("   工作进程: 1")
    typer.echo("   热重载: ✅")
    typer.echo("   调试模式: ✅")
    typer.echo(f"   监控目录: {reload_dirs}")
    typer.echo(f"   应用模块: {app_module_path}")

    # 在应用启动完成后打印一次服务地址
    with contextlib.suppress(Exception):
        app_instance.add_event_handler(
            "startup",
            lambda: typer.echo(f"✅ 服务已就绪: http://{server_host}:{server_port}"),
        )

    # 默认包含/排除规则（watchfiles 支持）
    reload_includes = [
        "*.py",
        "*.pyi",
        "*.ini",
        "*.toml",
        "*.yaml",
        "*.yml",
        "*.json",
        "*.env",
        "*.cfg",
        "*.conf",
        # 常见模板与静态资源（如需更少重载，可通过 --exclude 精确排除）
        "*.jinja2",
        "*.jinja",
        "*.j2",
        "*.html",
        "*.htm",
        "*.sql",
        "*.graphql",
        # 前端常见类型（node_modules 已排除）
        "*.ts",
        "*.tsx",
        "*.js",
        "*.jsx",
        "*.vue",
        "*.css",
        "*.scss",
        "*.sass",
    ]
    reload_excludes = [
        "logs/*",
        "*.log",
        "*.log.*",
        "migrations/versions/*",
        "alembic.ini",
        "__pycache__/*",
        ".pytest_cache/*",
        ".mypy_cache/*",
        ".ruff_cache/*",
        ".git/*",
        ".venv/*",
        "dist/*",
        "build/*",
        "coverage/*",
        "node_modules/*",
    ]

    # 追加用户自定义模式
    if reload_include:
        reload_includes.extend(reload_include)
    if reload_exclude:
        reload_excludes.extend(reload_exclude)

    typer.echo(f"   监控包含: {reload_includes}")
    typer.echo(f"   监控排除: {reload_excludes}")

    # 提示将使用的热重载实现
    try:
        import importlib
        importlib.import_module("watchfiles")
        typer.echo("   重载引擎: watchfiles ✅")
    except Exception:
        typer.echo("   重载引擎: watchdog/stat ❌  (建议安装: uv add watchfiles)")
    
    try:
        import os as os_module
        os_module.environ["AURIMYTH_RELOAD"] = "1"
        
        # 热重载模式下，直接使用 uvicorn，传递 app 字符串路径
        uvicorn.run(
            app=app_module_path,
            host=server_host,
            port=server_port,
            reload=True,
            reload_dirs=reload_dirs,
            reload_includes=reload_includes,
            reload_excludes=reload_excludes,
            log_level="info",
            # 优雅关闭超时，确保 WS/SSE 连接有时间关闭
            timeout_graceful_shutdown=5,
        )
    except KeyboardInterrupt:
        typer.echo("\n👋 服务器已停止")
    except Exception as e:
        typer.echo(f"❌ 错误：{e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def prod(
    app_path: str | None = typer.Option(
        None,
        "--app",
        "-a",
        envvar="APP_MODULE",
        help="应用模块路径，格式: module.path:variable（默认自动检测）",
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        "-h",
        help="监听地址（默认使用配置文件中的 SERVER_HOST，或 0.0.0.0）",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="监听端口（默认使用配置文件中的 SERVER_PORT）",
    ),
    workers: int | None = typer.Option(
        None,
        "--workers",
        "-w",
        help="工作进程数（默认使用配置文件中的 SERVER_WORKERS，或 CPU 核心数）",
    ),
) -> None:
    """启动生产服务器（多进程）。
    
    快捷命令，相当于 run --workers <cpu_count>
    
    配置优先级: 命令行参数 > .env/环境变量 > 默认值
    
    示例：
        aury server prod
        aury server prod --app myproject.main:app
        aury server prod --workers 8
    """
    import os as os_module
    
    from aury.boot.application.server import ApplicationServer
    
    app_instance = _get_app_instance(app_path)
    
    # 优先使用命令行参数，否则使用 app 配置
    server_host = host if host is not None else app_instance.config.server.host
    
    # 生产模式：如果是默认的 127.0.0.1，自动改成 0.0.0.0（适合 Docker/生产环境）
    # 用户如果明确通过命令行指定 --host 127.0.0.1，则会尊重
    if host is None and server_host == "127.0.0.1":
        server_host = "0.0.0.0"
    
    server_port = port if port is not None else app_instance.config.server.port
    server_workers = workers if workers is not None else app_instance.config.server.workers
    
    # 如果配置中 workers 也是默认值 1，则使用 CPU 核心数
    if server_workers <= 1:
        server_workers = os_module.cpu_count() or 4
    
    typer.echo("🚀 启动生产服务器...")
    typer.echo(f"   地址: http://{server_host}:{server_port}")
    typer.echo(f"   工作进程: {server_workers}")
    typer.echo("   热重载: ❌")
    typer.echo("   调试模式: ❌")
    
    # 获取 app 模块路径（多进程模式需要字符串格式）
    app_module_path = app_path or _detect_app_module()
    typer.echo(f"   应用模块: {app_module_path}")
    
    try:
        # 多进程模式必须使用字符串路径，否则子进程无法重新加载应用
        uvicorn.run(
            app=app_module_path,
            host=server_host,
            port=server_port,
            workers=server_workers,
            reload=False,
            loop="auto",
            http="auto",
            access_log=True,
        )
    except KeyboardInterrupt:
        typer.echo("\n👋 服务器已停止")
    except Exception as e:
        typer.echo(f"❌ 错误：{e}", err=True)
        raise typer.Exit(1) from e


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


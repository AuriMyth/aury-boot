"""调度器命令 - 独立运行调度器。

使用示例：
    aury scheduler              # 运行调度器
    aury scheduler --app main:app  # 指定应用模块
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from rich.console import Console
import typer

console = Console()

app = typer.Typer(
    name="scheduler",
    help="🕐 独立运行调度器",
    no_args_is_help=False,
)


def _detect_app_module() -> str:
    """自动检测应用模块路径。"""
    import os

    # 1. 环境变量
    if app_module := os.environ.get("APP_MODULE"):
        return app_module

    # 2. pyproject.toml 中的 [tool.aury] 配置
    pyproject_path = Path.cwd() / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            aury_cfg = data.get("tool", {}).get("aury", {})

            # 优先使用显式 app 配置，避免 package=app 时误推断为 app.main:app
            if app := aury_cfg.get("app"):
                return app

            if package := aury_cfg.get("package"):
                return f"{package}.main:app"
        except Exception:
            pass

    # 3. 默认
    return "main:app"


@app.callback(invoke_without_command=True)
def run_scheduler(
    ctx: typer.Context,
    app_path: str | None = typer.Option(
        None,
        "--app",
        "-a",
        help="应用模块路径（默认自动检测，如 main:app）",
    ),
) -> None:
    """独立运行调度器进程。

    调度器会加载应用中注册的所有定时任务并执行。

    示例：
        aury scheduler                    # 自动检测应用
        aury scheduler --app main:app     # 指定应用模块
        aury scheduler -a myapp.main:app  # 指定包中的应用
    """
    if ctx.invoked_subcommand is not None:
        return

    # 确保当前目录在 Python 路径中
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    app_module = app_path or _detect_app_module()
    console.print("[bold cyan]🕐 启动独立调度器[/bold cyan]")
    console.print(f"   应用: [green]{app_module}[/green]")

    try:
        # 导入应用
        module_path, app_name = app_module.rsplit(":", 1)
        module = __import__(module_path, fromlist=[app_name])
        application = getattr(module, app_name)

        # 设置日志（必须在其他操作之前）
        from aury.boot.common.logging import setup_logging
        setup_logging(
            log_level=getattr(application, "_config", None) and application._config.log.level or "INFO",
            service_type="scheduler",
        )

        # 获取调度器
        from aury.boot.infrastructure.scheduler import SchedulerManager
        scheduler = SchedulerManager.get_instance()

        console.print("[bold green]✅ 调度器启动成功[/bold green]")
        console.print("[dim]按 Ctrl+C 停止[/dim]")

        # 运行调度器
        async def _run():
            await scheduler.initialize()
            scheduler.start()
            try:
                # 保持运行
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                scheduler.shutdown()

        asyncio.run(_run())

    except KeyboardInterrupt:
        console.print("\n[yellow]调度器已停止[/yellow]")
    except ImportError as e:
        console.print(f"[red]❌ 无法导入应用: {e}[/red]")
        console.print("[dim]请确保应用模块路径正确，如 main:app[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(1)


__all__ = ["app"]

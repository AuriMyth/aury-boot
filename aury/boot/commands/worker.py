"""Worker 命令 - 运行任务队列 Worker。

使用示例：
    aury worker                  # 运行 worker
    aury worker --app main:app   # 指定应用模块
    aury worker -p 2 -t 50       # 2 进程 x 50 线程 = 100 并发槽位
    aury worker -c 50            # 兼容旧参数：等同 --threads 50
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
import os
from pathlib import Path
import sys

from rich.console import Console
import typer

console = Console()

app = typer.Typer(
    name="worker",
    help="⚙️  运行任务队列 Worker",
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
            if package := data.get("tool", {}).get("aury", {}).get("package"):
                return f"{package}.main:app"
        except Exception:
            pass

    # 3. 默认
    return "main:app"


@app.callback(invoke_without_command=True)
def run_worker(
    ctx: typer.Context,
    app_path: str | None = typer.Option(
        None,
        "--app",
        "-a",
        help="应用模块路径（默认自动检测，如 main:app）",
    ),
    processes: int = typer.Option(
        1,
        "--processes",
        "-p",
        min=1,
        help="Dramatiq 进程数",
    ),
    threads: int = typer.Option(
        4,
        "--threads",
        "-t",
        min=1,
        help="每进程线程数",
    ),
    concurrency: int | None = typer.Option(
        None,
        "--concurrency",
        "-c",
        min=1,
        help="兼容旧参数，等同 --threads",
    ),
    queues: str | None = typer.Option(
        None,
        "--queues",
        "-q",
        help="要处理的队列名称（逗号分隔）",
    ),
) -> None:
    """运行任务队列 Worker 进程。

    Worker 会消费任务队列中的异步任务并执行。

    示例：
        aury worker                       # 默认配置
        aury worker --app main:app        # 指定应用模块
        aury worker -p 2 -t 50            # 100 并发槽位
        aury worker -c 8                  # 兼容旧参数（等同 --threads 8）
        aury worker -q high,default       # 只处理指定队列
    """
    if ctx.invoked_subcommand is not None:
        return

    if concurrency is not None:
        threads = concurrency

    # 确保当前目录在 Python 路径中
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    app_module = app_path or _detect_app_module()
    console.print("[bold cyan]⚙️  启动 Worker[/bold cyan]")
    console.print(f"   应用: [green]{app_module}[/green]")
    console.print(f"   进程: [green]{processes}[/green]")
    console.print(f"   线程: [green]{threads}[/green]")
    console.print(f"   总并发槽位: [green]{processes * threads}[/green]")
    if queues:
        console.print(f"   队列: [green]{queues}[/green]")

    try:
        from aury.boot.application.constants.service import ServiceType

        # Worker 命令启动时强制覆盖 service type，避免与共享 .env 冲突。
        os.environ["SERVICE__SERVICE_TYPE"] = ServiceType.WORKER.value

        # 导入应用（确保任务被注册）
        module_path, app_name = app_module.rsplit(":", 1)
        module = __import__(module_path, fromlist=[app_name])
        application = getattr(module, app_name)

        # Ensure task broker/middleware are initialized for worker mode.
        # `aury worker` does not run full app startup, so TaskComponent.setup is not triggered.
        from aury.boot.infrastructure.tasks import TaskManager
        from aury.boot.infrastructure.tasks.constants import TaskRunMode
        broker_url = getattr(getattr(application, "_config", None), "task", None)
        broker_url = getattr(broker_url, "broker_url", None)
        if broker_url:
            with suppress(Exception):
                asyncio.run(
                    TaskManager.get_instance().initialize(
                        run_mode=TaskRunMode.WORKER,
                        broker_url=broker_url,
                    )
                )

        # 设置日志（必须在其他操作之前）
        from aury.boot.common.logging import setup_logging
        setup_logging(
            log_level=(getattr(application, "_config", None) and application._config.log.level) or "INFO",
            service_type="worker",
        )

        # 尝试导入 dramatiq
        try:
            import dramatiq
            from dramatiq.cli import main as dramatiq_main
        except ImportError:
            console.print("[red]❌ dramatiq 未安装[/red]")
            console.print("[dim]请安装: uv add 'aury-boot[tasks]'[/dim]")
            raise typer.Exit(1)

        console.print("[bold green]✅ Worker 启动中...[/bold green]")
        console.print("[dim]按 Ctrl+C 停止[/dim]")

        # 构建 dramatiq 参数
        args = [
            module_path,  # 模块路径
            "--processes",
            str(processes),
            "--threads",
            str(threads),
        ]
        if queues:
            args.extend(["--queues", queues])

        # 运行 dramatiq worker
        sys.argv = ["dramatiq", *args]
        dramatiq_main()

    except KeyboardInterrupt:
        console.print("\n[yellow]Worker 已停止[/yellow]")
    except ImportError as e:
        console.print(f"[red]❌ 无法导入应用: {e}[/red]")
        console.print("[dim]请确保应用模块路径正确，如 main:app[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(1)


__all__ = ["app"]

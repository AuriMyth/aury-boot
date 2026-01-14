"""包管理命令。

用法：
    aury pkg list                    # 列出所有可安装模块
    aury pkg list --installed        # 已安装的模块
    aury pkg preset                  # 列出预设
    aury pkg preset api              # 查看预设详情
    aury pkg install postgres redis  # 安装模块
    aury pkg install --preset api    # 按预设安装
    aury pkg remove redis            # 卸载模块
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import subprocess
import sys
from typing import Annotated

from rich.console import Console
from rich.table import Table
import typer

console = Console()

app = typer.Typer(
    name="pkg",
    help="包管理 - 安装/卸载 aury 生态模块",
    no_args_is_help=True,
)


# ============================================================================
# 数据定义
# ============================================================================


class Category(str, Enum):
    """模块分类。"""

    DATABASE = "database"
    CACHE = "cache"
    TASK = "task"
    SCHEDULER = "scheduler"
    ADMIN = "admin"
    STORAGE = "storage"
    ECOSYSTEM = "ecosystem"


@dataclass
class ModuleInfo:
    """模块信息。"""

    name: str
    desc: str
    usage: str
    category: Category
    deps: list[str]  # extras 的依赖包名
    is_extra: bool = True  # True=extras, False=生态包
    pkg: str | None = None  # 生态包的完整包名


# Extras（aury-boot 的可选依赖）
MODULES: dict[str, ModuleInfo] = {
    # 数据库驱动
    "postgres": ModuleInfo(
        name="postgres",
        desc="PostgreSQL 异步驱动",
        usage="DatabaseManager 使用 PostgreSQL 时需要",
        category=Category.DATABASE,
        deps=["asyncpg"],
    ),
    "mysql": ModuleInfo(
        name="mysql",
        desc="MySQL 异步驱动",
        usage="DatabaseManager 使用 MySQL 时需要",
        category=Category.DATABASE,
        deps=["aiomysql"],
    ),
    "sqlite": ModuleInfo(
        name="sqlite",
        desc="SQLite 异步驱动",
        usage="DatabaseManager 使用 SQLite 时需要（本地开发推荐）",
        category=Category.DATABASE,
        deps=["aiosqlite"],
    ),
    # 缓存
    "redis": ModuleInfo(
        name="redis",
        desc="Redis 客户端",
        usage="CacheManager 使用 Redis 后端时需要",
        category=Category.CACHE,
        deps=["redis"],
    ),
    # 任务队列
    "tasks": ModuleInfo(
        name="tasks",
        desc="Dramatiq 任务队列",
        usage="TaskManager 异步任务时需要（默认使用 Redis Broker）",
        category=Category.TASK,
        deps=["dramatiq", "redis"],
    ),
    "rabbitmq": ModuleInfo(
        name="rabbitmq",
        desc="RabbitMQ 消息队列后端",
        usage="TaskManager/EventBus 使用 RabbitMQ 时需要（需配合 tasks）",
        category=Category.TASK,
        deps=["pika"],
    ),
    # 调度器
    "scheduler": ModuleInfo(
        name="scheduler",
        desc="APScheduler 定时调度",
        usage="SchedulerManager 定时任务时需要",
        category=Category.SCHEDULER,
        deps=["apscheduler"],
    ),
    # 管理后台
    "admin": ModuleInfo(
        name="admin",
        desc="SQLAdmin 管理后台",
        usage="启用 /admin 管理界面时需要",
        category=Category.ADMIN,
        deps=["sqladmin", "itsdangerous"],
    ),
    # 存储（extras）
    "s3": ModuleInfo(
        name="s3",
        desc="S3 兼容存储（AWS/MinIO/OSS）",
        usage="StorageManager 使用 S3 兼容存储时需要",
        category=Category.STORAGE,
        deps=["aury-sdk-storage[aws]"],
    ),
    # 生态包
    "storage-aws": ModuleInfo(
        name="storage-aws",
        desc="AWS S3 兼容存储",
        usage="StorageManager 使用 AWS S3/MinIO/OSS 时需要",
        category=Category.ECOSYSTEM,
        deps=[],
        is_extra=False,
        pkg="aury-sdk-storage[aws]",
    ),
    "storage-cos": ModuleInfo(
        name="storage-cos",
        desc="腾讯云 COS 原生存储",
        usage="StorageManager 使用腾讯云 COS 时推荐（性能更好）",
        category=Category.ECOSYSTEM,
        deps=[],
        is_extra=False,
        pkg="aury-sdk-storage[cos]",
    ),
}


@dataclass
class PresetInfo:
    """预设信息。"""

    name: str
    desc: str
    modules: list[str]


PRESETS: dict[str, PresetInfo] = {
    "minimal": PresetInfo(
        name="minimal",
        desc="最小化（本地开发/测试）",
        modules=["sqlite"],
    ),
    "api": PresetInfo(
        name="api",
        desc="API 服务（Web 接口 + 管理后台）",
        modules=["postgres", "redis", "admin"],
    ),
    "worker": PresetInfo(
        name="worker",
        desc="后台 Worker（任务队列 + 调度器）",
        modules=["postgres", "redis", "tasks", "rabbitmq", "scheduler"],
    ),
    "full": PresetInfo(
        name="full",
        desc="完整功能（所有模块）",
        modules=["postgres", "redis", "tasks", "rabbitmq", "scheduler", "admin", "storage-cos"],
    ),
}


# 分类显示名称
CATEGORY_NAMES: dict[Category, str] = {
    Category.DATABASE: "📦 数据库驱动",
    Category.CACHE: "📦 缓存",
    Category.TASK: "📦 任务队列",
    Category.SCHEDULER: "📦 定时调度",
    Category.ADMIN: "📦 管理后台",
    Category.STORAGE: "📦 对象存储",
    Category.ECOSYSTEM: "🌐 生态包",
}


# ============================================================================
# 工具函数
# ============================================================================


def _get_installed_packages() -> set[str]:
    """获取已安装的包名。"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=True,
        )
        installed = set()
        for line in result.stdout.strip().split("\n"):
            if "==" in line:
                pkg_name = line.split("==")[0].lower().replace("-", "_")
                installed.add(pkg_name)
        return installed
    except subprocess.CalledProcessError:
        return set()


def _is_module_installed(module: ModuleInfo) -> bool:
    """检查模块是否已安装。"""
    installed = _get_installed_packages()

    if module.is_extra:
        # 检查 deps 中的包是否已安装
        for dep in module.deps:
            # 处理 extras 语法，如 aury-sdk-storage[aws]
            pkg_name = dep.split("[")[0].lower().replace("-", "_")
            if pkg_name not in installed:
                return False
        return bool(module.deps)
    else:
        # 生态包：检查包名
        if module.pkg:
            pkg_name = module.pkg.split("[")[0].lower().replace("-", "_")
            return pkg_name in installed
    return False


def _run_uv_command(args: list[str]) -> bool:
    """运行 uv 命令。"""
    cmd = ["uv", *args]
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]命令失败: {e}[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]错误: 未找到 uv，请先安装: pip install uv[/red]")
        return False


# ============================================================================
# 命令实现
# ============================================================================


@app.command(name="list")
def list_modules(
    installed: Annotated[
        bool,
        typer.Option("--installed", "-i", help="仅显示已安装的模块"),
    ] = False,
) -> None:
    """列出所有可安装的模块。"""
    installed_pkgs = _get_installed_packages() if installed else None

    # 按分类组织
    by_category: dict[Category, list[ModuleInfo]] = {}
    for module in MODULES.values():
        if module.category not in by_category:
            by_category[module.category] = []
        by_category[module.category].append(module)

    # 输出
    for category in Category:
        modules = by_category.get(category, [])
        if not modules:
            continue

        # 过滤已安装
        if installed:
            modules = [m for m in modules if _is_module_installed(m)]
            if not modules:
                continue

        console.print()
        console.print(f"[bold]{CATEGORY_NAMES[category]}[/bold]")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("名称", style="cyan", width=15)
        table.add_column("描述", width=30)
        table.add_column("用途", style="dim")

        for module in modules:
            status = ""
            if installed_pkgs is not None:
                is_installed = _is_module_installed(module)
                status = " [green]✓[/green]" if is_installed else ""
            table.add_row(
                f"{module.name}{status}",
                module.desc,
                f"→ {module.usage}",
            )

        console.print(table)

    console.print()
    console.print("[dim]提示: 使用 aury pkg install <模块名> 安装模块[/dim]")


@app.command(name="preset")
def list_presets(
    name: Annotated[
        str | None,
        typer.Argument(help="预设名称（留空列出所有预设）"),
    ] = None,
) -> None:
    """查看预设配置。"""
    if name is None:
        # 列出所有预设
        console.print()
        console.print("[bold]📋 可用预设[/bold]")
        console.print()

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("预设", style="cyan", width=12)
        table.add_column("描述", width=35)
        table.add_column("包含模块", style="dim")

        for preset in PRESETS.values():
            table.add_row(
                preset.name,
                preset.desc,
                ", ".join(preset.modules),
            )

        console.print(table)
        console.print()
        console.print("[dim]提示: 使用 aury pkg preset <预设名> 查看详情[/dim]")
        console.print("[dim]      使用 aury pkg install --preset <预设名> 安装[/dim]")
    else:
        # 查看指定预设
        if name not in PRESETS:
            console.print(f"[red]错误: 预设 '{name}' 不存在[/red]")
            console.print(f"[dim]可用预设: {', '.join(PRESETS.keys())}[/dim]")
            raise typer.Exit(1)

        preset = PRESETS[name]
        console.print()
        console.print(f"[bold]📋 预设: {preset.name}[/bold]")
        console.print(f"[dim]{preset.desc}[/dim]")
        console.print()

        console.print("[bold]包含模块:[/bold]")
        for module_name in preset.modules:
            module = MODULES.get(module_name)
            if module:
                installed = _is_module_installed(module)
                status = "[green]✓ 已安装[/green]" if installed else "[dim]未安装[/dim]"
                console.print(f"  • {module.name}: {module.desc} {status}")
            else:
                console.print(f"  • {module_name} [red](未知模块)[/red]")

        console.print()
        console.print(f"[dim]安装命令: aury pkg install --preset {name}[/dim]")


@app.command(name="install")
def install_modules(
    modules: Annotated[
        list[str] | None,
        typer.Argument(help="要安装的模块名称"),
    ] = None,
    preset: Annotated[
        str | None,
        typer.Option("--preset", "-p", help="使用预设安装"),
    ] = None,
) -> None:
    """安装模块。"""
    if preset:
        # 使用预设
        if preset not in PRESETS:
            console.print(f"[red]错误: 预设 '{preset}' 不存在[/red]")
            console.print(f"[dim]可用预设: {', '.join(PRESETS.keys())}[/dim]")
            raise typer.Exit(1)

        preset_info = PRESETS[preset]
        modules = preset_info.modules
        console.print(f"[bold]📦 安装预设: {preset_info.name}[/bold]")
        console.print(f"[dim]{preset_info.desc}[/dim]")
        console.print()

    if not modules:
        console.print("[red]错误: 请指定要安装的模块，或使用 --preset[/red]")
        raise typer.Exit(1)

    # 收集要安装的包
    extras_to_install: list[str] = []
    pkgs_to_install: list[str] = []

    for module_name in modules:
        if module_name not in MODULES:
            console.print(f"[yellow]警告: 模块 '{module_name}' 不存在，跳过[/yellow]")
            continue

        module = MODULES[module_name]
        if module.is_extra:
            extras_to_install.append(module.name)
        else:
            if module.pkg:
                pkgs_to_install.append(module.pkg)

    # 安装 extras
    if extras_to_install:
        extras_str = ",".join(extras_to_install)
        console.print(f"[bold]安装 extras: {extras_str}[/bold]")
        if not _run_uv_command(["add", f"aury-boot[{extras_str}]"]):
            raise typer.Exit(1)

    # 安装生态包
    for pkg in pkgs_to_install:
        console.print(f"[bold]安装生态包: {pkg}[/bold]")
        if not _run_uv_command(["add", pkg]):
            raise typer.Exit(1)

    console.print()
    console.print("[green]✅ 安装完成[/green]")


@app.command(name="remove")
def remove_modules(
    modules: Annotated[
        list[str],
        typer.Argument(help="要卸载的模块名称"),
    ],
) -> None:
    """卸载模块。"""
    for module_name in modules:
        if module_name not in MODULES:
            console.print(f"[yellow]警告: 模块 '{module_name}' 不存在，跳过[/yellow]")
            continue

        module = MODULES[module_name]

        if module.is_extra:
            # extras 需要移除具体的依赖包
            console.print(f"[bold]移除 {module.name} 的依赖...[/bold]")
            for dep in module.deps:
                pkg_name = dep.split("[")[0]  # 去掉 extras 语法
                _run_uv_command(["remove", pkg_name])
        else:
            # 生态包直接移除
            if module.pkg:
                pkg_name = module.pkg.split("[")[0]
                console.print(f"[bold]移除生态包: {pkg_name}[/bold]")
                _run_uv_command(["remove", pkg_name])

    console.print()
    console.print("[green]✅ 卸载完成[/green]")


__all__ = ["app"]

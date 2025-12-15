"""给已有项目添加可选模块。

用法：
    aury add admin-console   # 添加 Admin Console 模块
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
import typer

from .config import get_project_config

console = Console()

app = typer.Typer(
    name="add",
    help="给已有项目添加可选模块",
    no_args_is_help=True,
)


@app.command(name="admin-console")
def add_admin_console(
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖已有 admin_console.py"),
    enable_env: bool = typer.Option(True, "--enable-env", help="尝试在 .env.example 中开启 ADMIN_* 示例配置"),
) -> None:
    """添加 Admin Console 模块到现有项目。

    将在项目代码根（包根或平铺）下生成 `admin_console.py`，便于注册 SQLAdmin 的 ModelView / 自定义认证。

    同时（可选）在 `.env.example` 中启用 ADMIN 示例配置，方便快速启动。
    """
    from .init import init_admin_console_module

    base_path = Path.cwd()
    config = get_project_config(base_path)
    code_root = config.get_package_dir(base_path)
    import_prefix = config.get_import_prefix()

    result = init_admin_console_module(
        base_path=base_path,
        code_root=code_root,
        import_prefix=import_prefix,
        force=force,
        enable_env=enable_env,
    )

    # 输出结果
    admin_pkg = code_root / "admin_console"
    if result["file_created"]:
        console.print(f"[green]✅ 已生成: {admin_pkg.relative_to(base_path)}/[/green]")
    elif result["file_existed"]:
        console.print(f"[yellow]⚠️  已存在: {admin_pkg.relative_to(base_path)}/（使用 --force 覆盖）[/yellow]")

    if enable_env:
        if result["env_updated"]:
            console.print("[green]✅ 已在 .env.example 中启用 ADMIN_* 示例配置[/green]")
        elif (base_path / ".env.example").exists():
            console.print("[dim]ℹ️  .env.example 已包含 ADMIN_* 配置示例[/dim]")
        else:
            console.print("[dim]ℹ️  未找到 .env.example，已跳过环境示例更新[/dim]")

    console.print()
    console.print("[bold]下一步：[/bold]")
    console.print("  1. 安装扩展依赖（如未安装）：")
    console.print('     [cyan]uv add "aury-boot[admin]"[/cyan]')
    console.print("  2. 复制 .env.example 并按需修改：")
    console.print("     [cyan]cp .env.example .env[/cyan]")
    console.print("  3. 启动开发服务器并访问：")
    console.print("     [cyan]aury server dev[/cyan] → http://127.0.0.1:8000/api/admin-console")


__all__ = ["app"]

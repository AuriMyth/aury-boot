"""迁移命令实现。

实现所有迁移相关的命令行命令。
"""

from __future__ import annotations

import asyncio

from rich.console import Console
from rich.table import Table
import typer

from .app import app, get_manager

console = Console()


@app.command()
def make(
    message: str = typer.Option(..., "-m", "--message", help="迁移消息"),
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
    autogenerate: bool = typer.Option(True, "--autogenerate/--no-autogenerate", help="是否自动生成"),
    dry_run: bool = typer.Option(False, "--dry-run", help="干运行（只检测变更，不生成文件）"),
) -> None:
    """生成迁移文件（类似 Django 的 makemigrations）。
    
    示例:
        aurimyth-migrate make -m "add user table"
        aurimyth-migrate make -m "update schema" --no-autogenerate
        aurimyth-migrate make -m "check changes" --dry-run
    """
    try:
        manager = get_manager(script_location)
        
        async def _make():
            result = await manager.make_migrations(
                message=message,
                autogenerate=autogenerate,
                dry_run=dry_run,
            )
            
            if dry_run:
                changes = result.get("changes", [])
                if changes:
                    typer.echo(f"\n📝 检测到 {len(changes)} 个变更:")
                    for change in changes:
                        typer.echo(f"  - {change['type']}: {change['description']}")
                else:
                    typer.echo("✅ 没有检测到模型变更")
            else:
                typer.echo(f"✅ 迁移文件已生成: {result.get('path', '')}")
                changes = result.get("changes", [])
                if changes:
                    typer.echo(f"📝 包含 {len(changes)} 个变更")
        
        asyncio.run(_make())
    except Exception as e:
        typer.echo(f"❌ 生成迁移失败: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def up(
    revision: str = typer.Option("head", "-r", "--revision", help="目标版本（默认 head）"),
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="干运行（只显示会执行的迁移，不实际执行）"),
) -> None:
    """执行迁移（类似 Django 的 migrate）。
    
    示例:
        aurimyth-migrate up
        aurimyth-migrate up -r "abc123"
        aurimyth-migrate up --dry-run
    """
    try:
        manager = get_manager(script_location)
        
        async def _upgrade():
            await manager.upgrade(revision=revision, dry_run=dry_run)
            if not dry_run:
                typer.echo(f"✅ 迁移已执行到版本: {revision}")
        
        asyncio.run(_upgrade())
    except Exception as e:
        typer.echo(f"❌ 执行迁移失败: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def down(
    revision: str = typer.Argument(..., help="目标版本（如 previous, -1, 或具体版本号）"),
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="干运行（只显示会回滚的迁移，不实际执行）"),
) -> None:
    """回滚迁移。
    
    示例:
        aurimyth-migrate down previous
        aurimyth-migrate down -1
        aurimyth-migrate down abc123 --dry-run
    """
    try:
        manager = get_manager(script_location)
        
        async def _downgrade():
            await manager.downgrade(revision=revision, dry_run=dry_run)
            if not dry_run:
                typer.echo(f"✅ 迁移已回滚到版本: {revision}")
        
        asyncio.run(_downgrade())
    except Exception as e:
        typer.echo(f"❌ 回滚迁移失败: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def status(
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
) -> None:
    """查看迁移状态（类似 Django 的 showmigrations）。
    
    示例:
        aurimyth-migrate status
    """
    try:
        manager = get_manager(script_location)
        
        async def _status():
            status_info = await manager.status()
            
            # 格式化输出
            typer.echo("\n📊 迁移状态:")
            typer.echo(f"  当前版本: {status_info.get('current', 'None')}")
            typer.echo(f"  最新版本: {status_info.get('head', 'None')}")
            
            pending = status_info.get('pending', [])
            applied = status_info.get('applied', [])
            
            if pending:
                typer.echo(f"\n⏳ 待执行迁移 ({len(pending)}):")
                for rev in pending:
                    typer.echo(f"  - {rev}")
            else:
                typer.echo("\n✅ 所有迁移已执行")
            
            if applied:
                typer.echo(f"\n✅ 已执行迁移 ({len(applied)}):")
                for rev in applied:
                    typer.echo(f"  - {rev}")
        
        asyncio.run(_status())
    except Exception as e:
        typer.echo(f"❌ 查看状态失败: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def show(
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
) -> None:
    """显示所有迁移（类似 Django 的 showmigrations）。
    
    示例:
        aurimyth-migrate show
    """
    try:
        manager = get_manager(script_location)
        
        async def _show():
            migrations = await manager.show()
            
            if not migrations:
                typer.echo("📝 没有找到迁移文件")
                return
            
            # 使用 Rich 表格显示
            table = Table(title="📝 所有迁移", show_header=True, header_style="bold magenta")
            table.add_column("版本", style="cyan", width=15)
            table.add_column("父版本", style="yellow", width=15)
            table.add_column("消息", style="green")
            
            for mig in migrations:
                revision = mig.get('revision', '')[:12]
                down_revision = mig.get('down_revision', '')[:12] if mig.get('down_revision') else '-'
                message = mig.get('message', '')
                table.add_row(revision, down_revision, message)
            
            console.print(table)
        
        asyncio.run(_show())
    except Exception as e:
        typer.echo(f"❌ 显示迁移失败: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def check(
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
) -> None:
    """检查迁移（类似 Django 的 check）。
    
    检查迁移文件是否有问题。
    
    示例:
        aurimyth-migrate check
    """
    try:
        manager = get_manager(script_location)
        
        async def _check():
            result = await manager.check()
            
            if result["valid"]:
                typer.echo("✅ 迁移检查通过")
            else:
                typer.echo("❌ 发现迁移问题:")
                for issue in result["issues"]:
                    typer.echo(f"  - {issue}")
            
            if result["warnings"]:
                typer.echo("\n⚠️  警告:")
                for warning in result["warnings"]:
                    typer.echo(f"  - {warning}")
            
            typer.echo("\n📊 统计:")
            typer.echo(f"  迁移总数: {result['revision_count']}")
            typer.echo(f"  Head 数量: {result['head_count']}")
        
        asyncio.run(_check())
    except Exception as e:
        typer.echo(f"❌ 检查失败: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def merge(
    revisions: str = typer.Argument(..., help="要合并的版本（逗号分隔）"),
    message: str | None = typer.Option(None, "-m", "--message", help="合并消息"),
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
) -> None:
    """合并迁移（类似 Django 的迁移合并）。
    
    当有多个分支时，创建合并迁移。
    
    示例:
        aurimyth-migrate merge "abc123,def456"
        aurimyth-migrate merge "abc123,def456" -m "merge branches"
    """
    try:
        manager = get_manager(script_location)
        revision_list = [r.strip() for r in revisions.split(",")]
        
        async def _merge():
            result = await manager.merge(revisions=revision_list, message=message)
            typer.echo(f"✅ 迁移已合并: {result}")
        
        asyncio.run(_merge())
    except Exception as e:
        typer.echo(f"❌ 合并迁移失败: {e}", err=True)
        raise typer.Exit(1) from None


@app.command()
def history(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="显示详细信息"),
    script_location: str | None = typer.Option(None, "--config", help="Alembic 配置文件路径"),
) -> None:
    """显示迁移历史。
    
    示例:
        aurimyth-migrate history
        aurimyth-migrate history --verbose
    """
    try:
        manager = get_manager(script_location)
        
        async def _history():
            await manager.history(verbose=verbose)
        
        asyncio.run(_history())
    except Exception as e:
        typer.echo(f"❌ 显示历史失败: {e}", err=True)
        raise typer.Exit(1) from None


__all__ = [
    "check",
    "down",
    "history",
    "make",
    "merge",
    "show",
    "status",
    "up",
]


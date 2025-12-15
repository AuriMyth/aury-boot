"""文档生成命令。

提供命令行工具用于在现有项目中生成/更新文档：
- aury docs dev         生成/更新 DEVELOPMENT.md
- aury docs cli         生成/更新 CLI.md
- aury docs env         生成/更新 .env.example
- aury docs all         生成/更新所有文档

使用示例：
    aury docs dev                    # 生成开发文档
    aury docs cli                    # 生成 CLI 文档
    aury docs env                    # 生成环境变量示例
    aury docs all                    # 生成所有文档
    aury docs all --force            # 强制覆盖已存在的文件
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
import typer

app = typer.Typer(
    name="docs",
    help="📚 生成/更新项目文档",
    no_args_is_help=True,
)

console = Console()

# 模板目录
TEMPLATES_DIR = Path(__file__).parent / "templates" / "project"


def _detect_project_info(project_dir: Path) -> dict[str, str]:
    """检测项目信息。
    
    从 pyproject.toml 或目录结构中推断项目名称和包名。
    """
    # 尝试从 pyproject.toml 读取
    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                project_name = data.get("project", {}).get("name", "")
                if project_name:
                    # 转换为 snake_case
                    project_name_snake = project_name.replace("-", "_").lower()
                    return {
                        "project_name": project_name,
                        "project_name_snake": project_name_snake,
                        "package_name": project_name_snake,
                        "import_prefix": project_name_snake,
                    }
        except Exception:
            pass
    
    # 尝试从目录名推断
    dir_name = project_dir.name
    project_name_snake = dir_name.replace("-", "_").lower()
    
    # 检查是否有匹配的 Python 包目录
    package_name = project_name_snake
    for candidate in [project_name_snake, "app", "src"]:
        candidate_path = project_dir / candidate
        if candidate_path.is_dir() and (candidate_path / "__init__.py").exists():
            package_name = candidate
            break
    
    return {
        "project_name": dir_name,
        "project_name_snake": project_name_snake,
        "package_name": package_name,
        "import_prefix": package_name,
    }


def _render_template(template_name: str, context: dict[str, str]) -> str:
    """渲染模板。"""
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    
    content = template_path.read_text(encoding="utf-8")
    return content.format(**context)


def _write_file(
    output_path: Path,
    content: str,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """写入文件。
    
    Returns:
        bool: 是否成功写入
    """
    if output_path.exists() and not force:
        console.print(f"[yellow]⚠️  文件已存在，跳过: {output_path}[/yellow]")
        console.print("   使用 --force 覆盖已存在的文件")
        return False
    
    if dry_run:
        console.print(f"[dim]🔍 预览模式，将生成: {output_path}[/dim]")
        return True
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    
    action = "覆盖" if output_path.exists() else "创建"
    console.print(f"[green]✅ {action}: {output_path}[/green]")
    return True


@app.command(name="dev")
def generate_dev_doc(
    project_dir: Path = typer.Argument(
        Path("."),
        help="项目目录路径",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制覆盖已存在的文件",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="预览模式，不实际写入文件",
    ),
) -> None:
    """生成/更新 DEVELOPMENT.md 开发文档。"""
    context = _detect_project_info(project_dir)
    
    console.print(f"[cyan]📚 检测到项目: {context['project_name']}[/cyan]")
    
    try:
        content = _render_template("DEVELOPMENT.md.tpl", context)
        output_path = project_dir / "DEVELOPMENT.md"
        _write_file(output_path, content, force=force, dry_run=dry_run)
    except Exception as e:
        console.print(f"[red]❌ 生成失败: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="cli")
def generate_cli_doc(
    project_dir: Path = typer.Argument(
        Path("."),
        help="项目目录路径",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制覆盖已存在的文件",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="预览模式，不实际写入文件",
    ),
) -> None:
    """生成/更新 CLI.md 命令行文档。"""
    context = _detect_project_info(project_dir)
    
    console.print(f"[cyan]📚 检测到项目: {context['project_name']}[/cyan]")
    
    try:
        content = _render_template("CLI.md.tpl", context)
        output_path = project_dir / "CLI.md"
        _write_file(output_path, content, force=force, dry_run=dry_run)
    except Exception as e:
        console.print(f"[red]❌ 生成失败: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="env")
def generate_env_example(
    project_dir: Path = typer.Argument(
        Path("."),
        help="项目目录路径",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制覆盖已存在的文件",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="预览模式，不实际写入文件",
    ),
) -> None:
    """生成/更新 .env.example 环境变量示例。"""
    context = _detect_project_info(project_dir)
    
    console.print(f"[cyan]📚 检测到项目: {context['project_name']}[/cyan]")
    
    try:
        content = _render_template("env.example.tpl", context)
        output_path = project_dir / ".env.example"
        _write_file(output_path, content, force=force, dry_run=dry_run)
    except Exception as e:
        console.print(f"[red]❌ 生成失败: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="all")
def generate_all_docs(
    project_dir: Path = typer.Argument(
        Path("."),
        help="项目目录路径",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制覆盖已存在的文件",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="预览模式，不实际写入文件",
    ),
) -> None:
    """生成/更新所有文档（DEVELOPMENT.md, CLI.md, .env.example）。"""
    context = _detect_project_info(project_dir)
    
    console.print(f"[cyan]📚 检测到项目: {context['project_name']}[/cyan]")
    console.print()
    
    docs_to_generate = [
        ("DEVELOPMENT.md.tpl", "DEVELOPMENT.md", "开发文档"),
        ("CLI.md.tpl", "CLI.md", "CLI 文档"),
        ("env.example.tpl", ".env.example", "环境变量示例"),
    ]
    
    success_count = 0
    for template_name, output_name, description in docs_to_generate:
        try:
            content = _render_template(template_name, context)
            output_path = project_dir / output_name
            if _write_file(output_path, content, force=force, dry_run=dry_run):
                success_count += 1
        except FileNotFoundError:
            console.print(f"[yellow]⚠️  模板不存在，跳过: {template_name}[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ 生成 {description} 失败: {e}[/red]")
    
    console.print()
    if dry_run:
        console.print(f"[dim]🔍 预览模式完成，将生成 {success_count} 个文件[/dim]")
    else:
        console.print(f"[green]✨ 完成！成功生成 {success_count} 个文档[/green]")


__all__ = ["app"]

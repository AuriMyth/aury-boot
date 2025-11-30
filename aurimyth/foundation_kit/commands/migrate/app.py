"""迁移 CLI 应用定义。

定义 Typer 应用和辅助函数。
"""

from __future__ import annotations

from pathlib import Path

import typer

from aurimyth.foundation_kit.application.migrations import MigrationManager

# 创建 Typer 应用
app = typer.Typer(
    name="migrate",
    help="数据库迁移管理工具（类似 Django 的 migrate 命令）",
    add_completion=False,
)


def get_manager(script_location: str | None = None) -> MigrationManager:
    """获取迁移管理器。
    
    Args:
        script_location: Alembic 配置文件路径
        
    Returns:
        MigrationManager: 迁移管理器实例
    """
    if script_location is None:
        # 默认查找 alembic.ini
        script_location = "alembic.ini"
        if not Path(script_location).exists():
            # 尝试查找项目根目录
            current = Path.cwd()
            for parent in [current, *list(current.parents)]:
                potential = parent / "alembic.ini"
                if potential.exists():
                    script_location = str(potential)
                    break
    
    return MigrationManager(script_location=script_location)


__all__ = [
    "app",
    "get_manager",
]


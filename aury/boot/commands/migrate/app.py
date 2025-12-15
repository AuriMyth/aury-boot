"""迁移 CLI 应用定义。

定义 Typer 应用和辅助函数。
"""

from __future__ import annotations

import typer

from aury.boot.application.config import BaseConfig
from aury.boot.application.migrations import MigrationManager

# 创建 Typer 应用
app = typer.Typer(
    name="migrate",
    help="数据库迁移管理工具（类似 Django 的 migrate 命令）",
    add_completion=False,
)


def get_manager(
    config_override: str | None = None,
) -> MigrationManager:
    """获取迁移管理器。
    
    从应用配置中获取所有必要参数并创建迁移管理器。
    
    Args:
        config_override: 覆盖配置文件路径（可选）
        
    Returns:
        MigrationManager: 迁移管理器实例
    """
    # 加载应用配置
    app_config = BaseConfig()
    
    # 从配置中提取参数
    migration_settings = app_config.migration
    
    # 创建迁移管理器（将配置转换为参数传递）
    return MigrationManager(
        database_url=app_config.database.url,
        config_path=config_override or migration_settings.config_path,
        script_location=migration_settings.script_location,
        model_modules=migration_settings.model_modules,
        auto_create=migration_settings.auto_create,
    )


__all__ = [
    "app",
    "get_manager",
]


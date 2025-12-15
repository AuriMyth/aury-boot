"""统一的迁移配置初始化模块。

这个模块提供单一的数据源来创建迁移配置，被 init 命令和 MigrationManager 共同使用。
"""

from pathlib import Path


def ensure_migration_setup(
    base_path: Path,
    config_path: str,
    script_location: str,
    model_modules: list[str],
) -> None:
    """确保迁移配置和目录存在，不存在则自动创建。
    
    Args:
        base_path: 项目根目录
        config_path: alembic.ini 路径
        script_location: 迁移脚本目录名
        model_modules: 模型模块列表
    """
    script_dir = base_path / script_location
    config_file = base_path / config_path
    
    # 创建迁移脚本目录
    if not script_dir.exists():
        script_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建 versions 目录
        versions_dir = script_dir / "versions"
        versions_dir.mkdir(exist_ok=True)
        
        # 创建 env.py
        env_py = script_dir / "env.py"
        if not env_py.exists():
            env_content = _get_env_py_template(model_modules)
            env_py.write_text(env_content, encoding="utf-8")
        
        # 创建 script.py.mako
        mako_file = script_dir / "script.py.mako"
        if not mako_file.exists():
            mako_content = _get_script_mako_template()
            mako_file.write_text(mako_content, encoding="utf-8")
    
    # 创建 alembic.ini
    if not config_file.exists():
        ini_content = _get_alembic_ini_template(script_location)
        config_file.write_text(ini_content, encoding="utf-8")


def _get_env_py_template(model_modules: list[str]) -> str:
    """获取 env.py 模板（异步版本）。"""
    model_modules_str = repr(model_modules)
    
    return f'''"""Alembic 环境配置（异步）。

由 Aury Boot 自动生成，并改造为全异步模式，
适配 sqlite+aiosqlite / postgresql+asyncpg / mysql+asyncmy 等异步驱动。
"""

from logging.config import fileConfig
from pathlib import Path
import os
import sys

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# 导入模型基类
from aury.boot.domain.models import Base

# Alembic Config 对象
config = context.config

# 解析日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# === 模型加载（基于项目包名自动发现） ===
# 确保项目根目录在 sys.path 中
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from aury.boot.application.migrations import load_all_models
try:
    from aury.boot.commands.config import get_project_config
    _cfg = get_project_config()
    if _cfg.has_package:
        _model_modules = [f"{{_cfg.package}}.models", f"{{_cfg.package}}.**.models"]
    else:
        _model_modules = ["models"]
except Exception:
    _model_modules = {model_modules_str}

# 加载模型，确保 Base.metadata 完整
load_all_models(_model_modules)

# 目标元数据
target_metadata = Base.metadata


def get_url() -> str:
    """获取数据库 URL（优先环境变量，其次 alembic.ini）。"""
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url", "")


def run_migrations_offline() -> None:
    """离线模式运行迁移（不建立实际连接）。"""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    """在同步上下文里执行迁移（由 AsyncConnection.run_sync 调用）。"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {{}})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''


def _get_script_mako_template() -> str:
    """获取 script.py.mako 模板。"""
    return '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''


def _get_alembic_ini_template(script_location: str) -> str:
    """获取 alembic.ini 模板。"""
    return f'''[alembic]
script_location = {script_location}
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
timezone = UTC
truncate_slug_length = 40
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''


__all__ = ["ensure_migration_setup"]

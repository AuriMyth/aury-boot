"""数据库迁移管理。

提供类似 Django 的迁移管理接口，封装 Alembic 命令，并增强功能。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import importlib
import inspect
from pathlib import Path
import pkgutil
from typing import Any

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.domain.models import Base


def load_all_models(model_modules: list[str]) -> None:
    """加载所有模型模块，确保 Alembic 可以检测到它们。
    
    这个函数会导入指定的模块及其所有子模块，确保所有继承自 Base 的模型类
    被正确注册到 SQLAlchemy 的元数据中。必须在 Alembic env.py 中调用此函数。
    
    支持的模式：
    - 精确模块名: "app.models"（既可以是文件 app/models.py，也可以是包 app/models/__init__.py）
    - 单层通配符: "app.*.models" 匹配 app.users.models, app.products.models
    - 递归通配符: "app.**" 递归匹配 app 下所有子模块
    - 混合模式: "app.**.models" 递归匹配所有以 models 结尾的模块
    
    Args:
        model_modules: 模型模块列表或模式，如 ["app.models", "app.**.models"]
        
    示例:
        # 在 alembic/env.py 中
        from aurimyth.foundation_kit.application.migrations import load_all_models
        from aurimyth.foundation_kit.domain.models import Base
        
        # 加载所有模型
        load_all_models(["app.models", "app.**.models"])
        
        # 确保使用 Base.metadata
        target_metadata = Base.metadata
    """
    if not model_modules:
        logger.warning("未配置 model_modules，Alembic 可能无法检测到模型变更")
        return
    
    loaded_count = 0
    
    for module_pattern in model_modules:
        # 检查是否有通配符
        if '*' in module_pattern:
            # 处理通配符模式
            modules = _expand_module_pattern(module_pattern)
        else:
            # 精确模块名
            modules = [module_pattern]
        
        for mod_name in modules:
            try:
                mod = importlib.import_module(mod_name)
                logger.debug(f"已导入模型模块: {mod_name}")
                loaded_count += 1
                
                # 如果是包，递归导入其所有子模块
                if hasattr(mod, '__path__'):
                    _load_package_submodules(mod)
                    
            except ImportError as e:
                logger.debug(f"无法导入模型模块 {mod_name}: {e}")
            except Exception as e:
                logger.debug(f"加载模型模块 {mod_name} 时出错: {e}")
    
    if loaded_count > 0:
        logger.info(f"✅ 已加载 {loaded_count} 个模型模块")
    else:
        logger.warning("⚠️  未加载任何模型模块，Alembic 可能无法检测到模型变更")


def _expand_module_pattern(pattern: str) -> list[str]:
    """根据通配符模式展开模块列表。
    
    支持的模式：
    - app.*.models: 匹配 app 下单层的 models 模块（app.users.models, app.products.models）
    - app.**.models: 递归匹配 app 下所有层的 models 模块
    - app.**: 递归匹配 app 下所有子模块
    
    Args:
        pattern: 包含通配符的模块模式
        
    Returns:
        展开后的模块名列表
    """
    modules = []
    
    if '**' in pattern:
        # 递归通配符：app.**.models 或 app.**
        # 提取基础包名（** 之前的部分）
        parts = pattern.split('**')
        base_pkg = parts[0].rstrip('.')
        suffix = parts[1].lstrip('.')  # models 或空字符串
        
        try:
            pkg = importlib.import_module(base_pkg)
            if hasattr(pkg, '__path__'):
                # 递归遍历所有子模块
                for _, modname, _ in pkgutil.walk_packages(
                    path=pkg.__path__,
                    prefix=f"{base_pkg}.",
                    onerror=lambda x: None,
                ):
                    # 如果有后缀，检查模块名是否以后缀结尾
                    if suffix:
                        if modname.endswith(suffix):
                            modules.append(modname)
                    else:
                        modules.append(modname)
        except ImportError:
            pass
            
    else:
        # 单层通配符：app.*.models
        # 提取基础包和后缀
        parts = pattern.split('*')
        base_pkg = parts[0].rstrip('.')
        suffix = parts[1].lstrip('.')
        
        try:
            pkg = importlib.import_module(base_pkg)
            if hasattr(pkg, '__path__'):
                # 只遍历一层子模块
                for _, modname, _ in pkgutil.iter_modules(pkg.__path__, prefix=f"{base_pkg}."):
                    # 检查是否有后缀部分，如果有则继续尝试导入
                    if suffix:
                        full_name = f"{modname}.{suffix}"
                        try:
                            importlib.import_module(full_name)
                            modules.append(full_name)
                        except ImportError:
                            pass
                    else:
                        modules.append(modname)
        except ImportError:
            pass
    
    return modules


def _load_package_submodules(package_module) -> None:
    """递归加载包内的所有模块。
    
    对于包（目录），这个函数会遍历其所有子模块并导入它们，
    确保其中定义的模型都被 SQLAlchemy 注册到 Base.metadata。
    
    Args:
        package_module: 已导入的包模块对象
    """
    if not hasattr(package_module, '__path__'):
        return
    
    package_name = package_module.__name__
    package_path = Path(package_module.__path__[0])
    
    # 遍历包目录下的所有 .py 文件（不包括 __pycache__）
    for py_file in package_path.glob('*.py'):
        # 跳过 __init__.py 和特殊文件
        if py_file.name.startswith('_'):
            continue
        
        module_name = py_file.stem
        full_module_name = f"{package_name}.{module_name}"
        
        try:
            importlib.import_module(full_module_name)
            logger.debug(f"已加载包中的模块: {full_module_name}")
        except ImportError as e:
            logger.debug(f"无法导入模块 {full_module_name}: {e}")
        except Exception as e:
            logger.debug(f"加载模块 {full_module_name} 时出错: {e}")


class MigrationManager:
    """迁移管理器。
    
    提供类似 Django 的迁移管理接口，并增强功能：
    - 自动检测模型变更
    - 数据迁移支持
    - 迁移前/后钩子
    - 干运行（dry-run）
    - 迁移检查
    - 更好的错误处理
    - 自动创建配置和目录
    
    使用示例:
        manager = MigrationManager(
            config_path="alembic.ini",
            script_location="alembic",
            database_url="sqlite:///./app.db",
            model_modules=["app.models"],
            auto_create=True,
        )
        
        # 生成迁移（自动检测模型变更）
        await manager.make_migrations(message="add user table")
        
        # 执行迁移（带钩子）
        await manager.upgrade()
        
        # 查看状态
        status = await manager.status()
    """
    
    def __init__(
        self,
        database_url: str,
        config_path: str = "alembic.ini",
        script_location: str = "alembic",
        model_modules: list[str] | None = None,
        auto_create: bool = True,
    ) -> None:
        """初始化迁移管理器。
        
        Args:
            database_url: 数据库连接字符串
            config_path: Alembic 配置文件路径
            script_location: Alembic 迁移脚本目录
            model_modules: 模型模块列表（用于自动检测变更）
            auto_create: 是否自动创建配置和目录
        """
        self._database_url = database_url
        self._config_path = Path(config_path)
        self._script_location = script_location
        self._model_modules = model_modules or []
        
        # 自动创建配置和目录
        if auto_create:
            self._ensure_migration_setup()
        
        # 加载 Alembic 配置
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Alembic 配置文件不存在: {config_path}\n"
                f"请设置 auto_create=True 以自动创建配置"
            )
        
        self._alembic_cfg = Config(str(self._config_path))
        self._alembic_cfg.set_main_option("script_location", self._script_location)
        self._alembic_cfg.set_main_option("sqlalchemy.url", self._database_url)
        
        # 迁移钩子
        self._before_upgrade_hooks: list[Callable[[str], None]] = []
        self._after_upgrade_hooks: list[Callable[[str], None]] = []
        self._before_downgrade_hooks: list[Callable[[str], None]] = []
        self._after_downgrade_hooks: list[Callable[[str], None]] = []
        
        logger.debug(f"迁移管理器已初始化: {config_path}")
    
    def _ensure_migration_setup(self) -> None:
        """确保迁移配置和目录存在，不存在则自动创建。"""
        script_dir = Path(self._script_location)
        
        # 创建迁移脚本目录
        if not script_dir.exists():
            logger.info(f"创建迁移脚本目录: {script_dir}")
            script_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建 versions 目录
            versions_dir = script_dir / "versions"
            versions_dir.mkdir(exist_ok=True)
            
            # 创建 env.py
            env_py = script_dir / "env.py"
            if not env_py.exists():
                env_content = self._get_env_py_template()
                env_py.write_text(env_content, encoding="utf-8")
                logger.debug(f"创建 env.py: {env_py}")
            
            # 创建 script.py.mako
            mako_file = script_dir / "script.py.mako"
            if not mako_file.exists():
                mako_content = self._get_script_mako_template()
                mako_file.write_text(mako_content, encoding="utf-8")
                logger.debug(f"创建 script.py.mako: {mako_file}")
        
        # 创建 alembic.ini
        if not self._config_path.exists():
            logger.info(f"创建 Alembic 配置文件: {self._config_path}")
            ini_content = self._get_alembic_ini_template()
            self._config_path.write_text(ini_content, encoding="utf-8")
    
    def _get_alembic_ini_template(self) -> str:
        """获取 alembic.ini 模板。"""
        return f"""# Alembic 配置文件
# 由 AuriMyth Foundation Kit 自动生成

[alembic]
# 迁移脚本目录
script_location = {self._script_location}

# 模板文件
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# 时区
timezone = UTC

# 是否截断长标识符
truncate_slug_length = 40

# 版本路径分隔符
version_path_separator = os

# 数据库连接字符串（运行时动态设置）
sqlalchemy.url = {self._database_url}

[post_write_hooks]
# 格式化工具钩子（可选）
# hooks = black
# black.type = console_scripts
# black.entrypoint = black

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
"""
    
    def _get_env_py_template(self) -> str:
        """获取 env.py 模板。"""
        # 生成模型模块列表的 Python 代码
        model_modules_str = repr(self._model_modules)
        
        load_models_code = f"""# 【重要】加载所有模型，确保 Alembic 可以检测到它们
#
# 动态加载配置的模型模块
# 配置列表: {model_modules_str}
#
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，以便能导入项目模块
# 假设 env.py 位于 <project_root>/alembic/env.py
# resolve() 会解析符号链接，parents[1] 是项目根目录
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from aurimyth.foundation_kit.application.migrations import load_all_models

# 加载模型
load_all_models({model_modules_str})
"""
        
        return f'''"""Alembic 环境配置。

由 AuriMyth Foundation Kit 自动生成。
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 导入模型基类
from aurimyth.foundation_kit.domain.models import Base

# Alembic Config 对象
config = context.config

# 解析日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

{load_models_code}

# 目标元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式运行迁移。
    
    在离线模式下，不需要实际的数据库连接，
    仅生成 SQL 脚本。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移。
    
    在在线模式下，需要实际的数据库连接。
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {{}}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    
    def _get_script_mako_template(self) -> str:
        """获取 script.py.mako 模板。"""
        return '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """升级迁移。"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """回滚迁移。"""
    ${downgrades if downgrades else "pass"}
'''
    
    def register_before_upgrade(self, hook: Callable[[str], None]) -> None:
        """注册升级前钩子。
        
        Args:
            hook: 钩子函数，接收目标版本作为参数
        """
        self._before_upgrade_hooks.append(hook)
    
    def register_after_upgrade(self, hook: Callable[[str], None]) -> None:
        """注册升级后钩子。
        
        Args:
            hook: 钩子函数，接收目标版本作为参数
        """
        self._after_upgrade_hooks.append(hook)
    
    def register_before_downgrade(self, hook: Callable[[str], None]) -> None:
        """注册回滚前钩子。
        
        Args:
            hook: 钩子函数，接收目标版本作为参数
        """
        self._before_downgrade_hooks.append(hook)
    
    def register_after_downgrade(self, hook: Callable[[str], None]) -> None:
        """注册回滚后钩子。
        
        Args:
            hook: 钩子函数，接收目标版本作为参数
        """
        self._after_downgrade_hooks.append(hook)
    
    def _load_models(self) -> set[type[DeclarativeBase]]:
        """加载所有模型（用于自动检测变更）。
        
        Returns:
            set[type[DeclarativeBase]]: 模型类集合
        """
        models: set[type[DeclarativeBase]] = set()
        
        for module_name in self._model_modules:
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, Base)
                        and obj is not Base
                        and not getattr(obj, "__abstract__", False)
                    ):
                        models.add(obj)
                        logger.debug(f"加载模型: {module_name}.{name}")
            except ImportError as e:
                logger.warning(f"无法导入模型模块 {module_name}: {e}")
        
        return models
    
    def _detect_changes(self) -> list[dict[str, Any]]:
        """检测模型变更（类似 Django 的 autodetect）。
        
        Returns:
            list[dict[str, Any]]: 变更列表
        """
        if not self._model_modules:
            return []
        
        try:
            models = self._load_models()
            if not models:
                return []
            
            # 使用传入的数据库 URL
            engine = create_engine(self._database_url)
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                metadata = MetaData()
                metadata.reflect(bind=engine)
                
                # 比较元数据
                diff = compare_metadata(context, Base.metadata)
                
                changes = []
                for change in diff:
                    changes.append({
                        "type": type(change).__name__,
                        "description": str(change),
                    })
                
                return changes
        except Exception as e:
            logger.warning(f"检测模型变更失败: {e}")
            return []
    
    async def check(self) -> dict[str, Any]:
        """检查迁移（类似 Django 的 check）。
        
        检查迁移文件是否有问题，如：
        - 迁移依赖是否正确
        - 是否有冲突
        - 是否有缺失的迁移
        
        Returns:
            dict[str, Any]: 检查结果
        """
        def _check():
            script = ScriptDirectory.from_config(self._alembic_cfg)
            revisions = list(script.walk_revisions())
            
            issues = []
            warnings = []
            
            # 检查是否有孤立的迁移
            revision_map = {rev.revision: rev for rev in revisions}
            for rev in revisions:
                if rev.down_revision and rev.down_revision not in revision_map:
                    issues.append(f"迁移 {rev.revision} 的父版本 {rev.down_revision} 不存在")
            
            # 检查是否有多个 head（冲突）
            heads = script.get_revisions("heads")
            if len(heads) > 1:
                warnings.append(f"发现 {len(heads)} 个 head，可能存在分支，需要合并")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "revision_count": len(revisions),
                "head_count": len(heads),
            }
        
        return await asyncio.to_thread(_check)
    
    async def make_migrations(
        self,
        message: str | None = None,
        autogenerate: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """生成迁移文件（类似 Django 的 makemigrations）。
        
        Args:
            message: 迁移消息
            autogenerate: 是否自动生成（基于模型变更）
            dry_run: 是否干运行（只检测变更，不生成文件）
            
        Returns:
            dict[str, Any]: 生成结果，包含变更信息
        """
        if not message:
            message = "auto migration"
        
        # 检测变更
        changes = []
        if autogenerate and self._model_modules:
            changes = self._detect_changes()
            if changes:
                logger.info(f"检测到 {len(changes)} 个模型变更")
                for change in changes:
                    logger.debug(f"  - {change['type']}: {change['description']}")
        
        if dry_run:
            return {
                "dry_run": True,
                "changes": changes,
                "message": message,
            }
        
        def _make():
            command.revision(
                self._alembic_cfg,
                message=message,
                autogenerate=autogenerate,
            )
        
        await asyncio.to_thread(_make)
        logger.info(f"迁移文件已生成: {message}")
        
        return {
            "dry_run": False,
            "changes": changes,
            "message": message,
            "path": f"{self._script_location}/versions/{message.replace(' ', '_')}.py",
        }
    
    async def upgrade(
        self,
        revision: str = "head",
        dry_run: bool = False,
    ) -> None:
        """执行迁移（类似 Django 的 migrate）。
        
        Args:
            revision: 目标版本（默认 "head" 表示最新版本）
            dry_run: 是否干运行（只显示会执行的迁移，不实际执行）
        """
        if dry_run:
            # 干运行：只显示会执行的迁移
            status_info = await self.status()
            pending = status_info.get("pending", [])
            if pending:
                logger.info(f"干运行：将执行 {len(pending)} 个迁移")
                for rev in pending:
                    logger.info(f"  - {rev}")
            else:
                logger.info("干运行：没有待执行的迁移")
            return
        
        # 执行钩子
        for hook in self._before_upgrade_hooks:
            try:
                hook(revision)
            except Exception as e:
                logger.error(f"升级前钩子执行失败: {e}")
        
        def _upgrade():
            command.upgrade(self._alembic_cfg, revision)
        
        await asyncio.to_thread(_upgrade)
        logger.info(f"迁移已执行到版本: {revision}")
        
        # 执行钩子
        for hook in self._after_upgrade_hooks:
            try:
                hook(revision)
            except Exception as e:
                logger.error(f"升级后钩子执行失败: {e}")
    
    async def downgrade(
        self,
        revision: str,
        dry_run: bool = False,
    ) -> None:
        """回滚迁移。
        
        Args:
            revision: 目标版本（如 "previous", "-1", 或具体版本号）
            dry_run: 是否干运行（只显示会回滚的迁移，不实际执行）
        """
        if dry_run:
            # 干运行：显示会回滚的迁移
            status_info = await self.status()
            current = status_info.get("current")
            if current:
                logger.info(f"干运行：将从 {current} 回滚到 {revision}")
            return
        
        # 执行钩子
        for hook in self._before_downgrade_hooks:
            try:
                hook(revision)
            except Exception as e:
                logger.error(f"回滚前钩子执行失败: {e}")
        
        def _downgrade():
            command.downgrade(self._alembic_cfg, revision)
        
        await asyncio.to_thread(_downgrade)
        logger.info(f"迁移已回滚到版本: {revision}")
        
        # 执行钩子
        for hook in self._after_downgrade_hooks:
            try:
                hook(revision)
            except Exception as e:
                logger.error(f"回滚后钩子执行失败: {e}")
    
    async def status(self) -> dict[str, Any]:
        """查看迁移状态（类似 Django 的 showmigrations）。
        
        Returns:
            dict[str, Any]: 迁移状态信息
        """
        def _get_status():
            script = ScriptDirectory.from_config(self._alembic_cfg)
            
            # 使用传入的数据库 URL
            engine = create_engine(self._database_url)
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
            
            head_rev = script.get_current_head()
            revisions = list(script.walk_revisions())
            
            applied = []
            pending = []
            unapplied = []
            
            # 构建依赖图
            revision_map = {rev.revision: rev for rev in revisions}
            visited = set()
            
            def traverse(rev_id: str | None):
                if not rev_id or rev_id in visited:
                    return
                visited.add(rev_id)
                if rev_id in revision_map:
                    rev = revision_map[rev_id]
                    if rev_id == current_rev:
                        applied.append(rev.revision)
                    elif current_rev:
                        # 检查是否在当前版本之后
                        if rev_id not in [r.revision for r in applied]:
                            pending.append(rev.revision)
                    else:
                        unapplied.append(rev.revision)
                    traverse(rev.down_revision)
            
            # 从 head 开始遍历
            if head_rev:
                traverse(head_rev)
            
            return {
                "current": current_rev,
                "head": head_rev,
                "pending": [r for r in pending if r not in applied],
                "applied": list(applied),
                "unapplied": [r for r in unapplied if r not in applied],
            }
        
        return await asyncio.to_thread(_get_status)
    
    async def show(self) -> list[dict[str, str]]:
        """显示所有迁移（类似 Django 的 showmigrations）。
        
        Returns:
            list[dict[str, str]]: 迁移列表
        """
        def _show():
            script = ScriptDirectory.from_config(self._alembic_cfg)
            revisions = list(script.walk_revisions())
            
            result = []
            for rev in revisions:
                result.append({
                    "revision": rev.revision,
                    "down_revision": rev.down_revision,
                    "message": rev.doc or "",
                    "path": str(rev.path) if hasattr(rev, "path") else "",
                })
            
            return result
        
        return await asyncio.to_thread(_show)
    
    async def history(self, verbose: bool = False) -> list[str]:
        """显示迁移历史。
        
        Args:
            verbose: 是否显示详细信息
            
        Returns:
            list[str]: 迁移历史列表
        """
        def _history():
            command.history(self._alembic_cfg, verbose=verbose)
        
        await asyncio.to_thread(_history)
        return []
    
    async def merge(
        self,
        revisions: list[str],
        message: str | None = None,
    ) -> str:
        """合并迁移（类似 Django 的迁移合并）。
        
        当有多个分支时，创建合并迁移。
        
        Args:
            revisions: 要合并的版本列表
            message: 合并消息
            
        Returns:
            str: 合并后的迁移文件路径
        """
        if not message:
            message = f"merge {', '.join(revisions)}"
        
        def _merge():
            command.merge(
                self._alembic_cfg,
                revisions=revisions,
                message=message,
            )
        
        await asyncio.to_thread(_merge)
        logger.info(f"迁移已合并: {message}")
        return f"{self._script_location}/versions/{message.replace(' ', '_')}.py"


__all__ = [
    "MigrationManager",
    "load_all_models",
]


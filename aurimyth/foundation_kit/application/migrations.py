"""数据库迁移管理。

提供类似 Django 的迁移管理接口，封装 Alembic 命令，并增强功能。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import importlib
import inspect
from pathlib import Path
from typing import Any, Optional

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.core.models import Base


class MigrationManager:
    """迁移管理器。
    
    提供类似 Django 的迁移管理接口，并增强功能：
    - 自动检测模型变更
    - 数据迁移支持
    - 迁移前/后钩子
    - 干运行（dry-run）
    - 迁移检查
    - 更好的错误处理
    
    使用示例:
        manager = MigrationManager()
        
        # 生成迁移（自动检测模型变更）
        await manager.make_migrations(message="add user table")
        
        # 执行迁移（带钩子）
        await manager.upgrade()
        
        # 查看状态
        status = await manager.status()
    """
    
    def __init__(
        self,
        script_location: str = "alembic.ini",
        alembic_dir: str | None = None,
        model_modules: list[str] | None = None,
    ) -> None:
        """初始化迁移管理器。
        
        Args:
            script_location: Alembic 配置文件路径
            alembic_dir: Alembic 脚本目录（可选，默认从配置文件读取）
            model_modules: 模型模块列表（用于自动检测变更，如 ["app.models", "app.domain.models"]）
        """
        self._config_path = Path(script_location)
        if not self._config_path.exists():
            raise FileNotFoundError(f"Alembic 配置文件不存在: {script_location}")
        
        self._alembic_cfg = Config(str(self._config_path))
        if alembic_dir:
            self._alembic_cfg.set_main_option("script_location", alembic_dir)
        
        self._script_location = self._alembic_cfg.get_main_option("script_location", "alembic")
        self._model_modules = model_modules or []
        
        # 迁移钩子
        self._before_upgrade_hooks: list[Callable[[str], None]] = []
        self._after_upgrade_hooks: list[Callable[[str], None]] = []
        self._before_downgrade_hooks: list[Callable[[str], None]] = []
        self._after_downgrade_hooks: list[Callable[[str], None]] = []
        
        logger.debug(f"迁移管理器已初始化: {script_location}")
    
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
            
            # 获取数据库元数据
            database_url = self._alembic_cfg.get_main_option("sqlalchemy.url")
            if not database_url:
                return []
            
            engine = create_engine(database_url)
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
            database_url = self._alembic_cfg.get_main_option("sqlalchemy.url")
            
            if not database_url:
                return {
                    "current": None,
                    "head": None,
                    "pending": [],
                    "applied": [],
                    "unapplied": [],
                }
            
            engine = create_engine(database_url)
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
                "applied": list(applied),  # noqa: C416
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
]

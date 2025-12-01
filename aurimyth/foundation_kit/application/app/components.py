"""默认组件实现。

提供所有内置组件的实现。
"""

from __future__ import annotations

from typing import ClassVar

from fastapi.middleware.cors import CORSMiddleware

from aurimyth.foundation_kit.application.app.base import Component, FoundationApp
from aurimyth.foundation_kit.application.config import BaseConfig
from aurimyth.foundation_kit.application.constants import ComponentName, SchedulerMode, ServiceType
from aurimyth.foundation_kit.application.middleware.logging import RequestLoggingMiddleware
from aurimyth.foundation_kit.application.migrations import MigrationManager
from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.infrastructure.cache import CacheManager
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager
from aurimyth.foundation_kit.infrastructure.scheduler import SchedulerManager
from aurimyth.foundation_kit.infrastructure.tasks import TaskManager


class RequestLoggingComponent(Component):
    """请求日志中间件组件。"""

    name = ComponentName.REQUEST_LOGGING
    enabled = True
    depends_on: ClassVar[list[str]] = []

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """添加请求日志中间件。"""
        app.add_middleware(RequestLoggingMiddleware)
        logger.debug("请求日志中间件已启用")

    async def teardown(self, app: FoundationApp) -> None:
        """无需清理。"""
        pass


class CORSComponent(Component):
    """CORS 中间件组件。"""

    name = ComponentName.CORS
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当配置了 origins 时启用。"""
        return self.enabled and bool(config.cors.origins)

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """添加 CORS 中间件。"""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors.origins,
            allow_credentials=config.cors.allow_credentials,
            allow_methods=config.cors.allow_methods,
            allow_headers=config.cors.allow_headers,
        )
        logger.debug("CORS 中间件已启用")

    async def teardown(self, app: FoundationApp) -> None:
        """无需清理。"""
        pass


class DatabaseComponent(Component):
    """数据库组件。"""

    name = ComponentName.DATABASE
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当配置了数据库 URL 时启用。"""
        return self.enabled and bool(config.database.url)

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化数据库。"""
        try:
            db_manager = DatabaseManager.get_instance()
            if not db_manager._initialized:
                await db_manager.initialize(
                    url=config.database.url,
                    echo=config.database.echo,
                    pool_size=config.database.pool_size,
                    max_overflow=config.database.max_overflow,
                    pool_timeout=config.database.pool_timeout,
                    pool_recycle=config.database.pool_recycle,
                )
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    async def teardown(self, app: FoundationApp) -> None:
        """关闭数据库。"""
        try:
            db_manager = DatabaseManager.get_instance()
            if db_manager._initialized:
                await db_manager.cleanup()
        except Exception as e:
            logger.error(f"数据库关闭失败: {e}")


class CacheComponent(Component):
    """缓存组件。"""

    name = ComponentName.CACHE
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当配置了缓存类型时启用。"""
        return self.enabled and bool(config.cache.cache_type)

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化缓存。"""
        try:
            cache_manager = CacheManager.get_instance()
            if not cache_manager._backend:
                await cache_manager.init_app({
                    "CACHE_TYPE": config.cache.cache_type,
                    "CACHE_REDIS_URL": config.cache.redis_url,
                    "CACHE_MAX_SIZE": config.cache.max_size,
                })
        except Exception as e:
            logger.warning(f"缓存初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭缓存。"""
        try:
            cache_manager = CacheManager.get_instance()
            if cache_manager._backend:
                await cache_manager.cleanup()
        except Exception as e:
            logger.warning(f"缓存关闭失败: {e}")


class TaskComponent(Component):
    """任务队列组件（Worker 模式）。"""

    name = ComponentName.TASK_QUEUE
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当是 Worker 模式且配置了 broker URL 时启用。"""
        return (
            self.enabled
            and config.service.service_type == ServiceType.WORKER.value
            and bool(config.task.broker_url)
        )

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化任务队列。"""
        try:
            from aurimyth.foundation_kit.infrastructure.tasks.constants import TaskRunMode
            
            task_manager = TaskManager.get_instance()
            # 将 application 层的 ServiceType.WORKER 转换为 infrastructure 层的 TaskRunMode.WORKER
            # ServiceType.API 和 ServiceType.SCHEDULER 转换为 TaskRunMode.PRODUCER
            if config.service.service_type == ServiceType.WORKER.value:
                run_mode = TaskRunMode.WORKER
            else:
                run_mode = TaskRunMode.PRODUCER
            
            await task_manager.initialize(
                run_mode=run_mode,
                broker_url=config.task.broker_url,
            )
        except Exception as e:
            logger.warning(f"任务队列初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """无需显式清理。"""
        pass


class SchedulerComponent(Component):
    """调度器组件（嵌入式模式）。"""

    name = ComponentName.SCHEDULER
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当是嵌入式模式时启用。"""
        return self.enabled and config.scheduler.mode == SchedulerMode.EMBEDDED.value

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化调度器。"""
        try:
            scheduler = SchedulerManager.get_instance()
            await scheduler.initialize()

            # 调用应用的注册任务方法
            if hasattr(app, "register_scheduler_jobs"):
                await app.register_scheduler_jobs()

            scheduler.start()
        except Exception as e:
            logger.warning(f"调度器初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭调度器。"""
        try:
            scheduler = SchedulerManager.get_instance()
            if scheduler._scheduler and scheduler._scheduler.running:
                scheduler.shutdown()
        except Exception as e:
            logger.warning(f"调度器关闭失败: {e}")


class MigrationComponent(Component):
    """数据库迁移组件。
    
    自动执行数据库迁移（升级到最新版本）。
    
    配置选项：
    - `ENABLE_AUTO_MIGRATION`：是否启用自动迁移（默认：True）
    - `ALEMBIC_CONFIG_PATH`：Alembic 配置文件路径（默认：alembic.ini）
    - `AUTO_MIGRATE_ON_STARTUP`：应用启动时是否自动执行迁移（默认：True）
    
    使用示例：
        # 在应用启动时自动执行迁移
        app = FoundationApp()
        # MigrationComponent 会在 DatabaseComponent 之后自动执行迁移
    """

    name = ComponentName.MIGRATIONS
    enabled = True
    depends_on: ClassVar[list[str]] = [ComponentName.DATABASE]

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当配置了数据库 URL 时启用。"""
        return self.enabled and bool(config.database.url)

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """执行数据库迁移。
        
        在应用启动时自动执行所有待处理的迁移，升级数据库到最新版本。
        """
        try:
            # 创建迁移管理器
            migration_manager = MigrationManager()
            
            # 检查是否有迁移需要执行
            logger.info("🔄 检查数据库迁移...")
            status = await migration_manager.status()
            
            pending = status.get("pending", [])
            applied = status.get("applied", [])
            
            if pending:
                logger.info("📊 数据库迁移状态：")
                logger.info(f"   已执行: {len(applied)} 个迁移")
                logger.info(f"   待执行: {len(pending)} 个迁移")
                
                # 执行迁移到最新版本
                logger.info("⏳ 执行数据库迁移...")
                await migration_manager.upgrade(revision="head")
                
                logger.info("✅ 数据库迁移完成")
            else:
                logger.info("✅ 数据库已是最新版本，无需迁移")
        except Exception as e:
            logger.error(f"❌ 数据库迁移失败: {e}", exc_info=True)
            raise

    async def teardown(self, app: FoundationApp) -> None:
        """无需清理。"""
        pass


# 设置默认组件
FoundationApp.items = [
    RequestLoggingComponent,
    CORSComponent,
    DatabaseComponent,
    MigrationComponent,
    CacheComponent,
    TaskComponent,
    SchedulerComponent,
]


__all__ = [
    "CORSComponent",
    "CacheComponent",
    "DatabaseComponent",
    "MigrationComponent",
    "RequestLoggingComponent",
    "SchedulerComponent",
    "TaskComponent",
]


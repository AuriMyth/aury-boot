"""默认组件实现。

提供所有内置基础设施组件的实现。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import ClassVar

from aury.boot.application.app.base import Component, FoundationApp
from aury.boot.application.config import BaseConfig
from aury.boot.application.constants import ComponentName, ServiceType
from aury.boot.application.migrations import MigrationManager
from aury.boot.common.logging import logger
from aury.boot.infrastructure.cache import CacheManager
from aury.boot.infrastructure.database import DatabaseManager
from aury.boot.infrastructure.events import EventBusManager
from aury.boot.infrastructure.mq import MQManager
from aury.boot.infrastructure.scheduler import SchedulerManager
from aury.boot.infrastructure.storage import StorageManager
from aury.boot.infrastructure.tasks import TaskManager


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
            if not cache_manager.is_initialized:
                await cache_manager.initialize(
                    backend=config.cache.cache_type,
                    url=config.cache.url,
                    max_size=config.cache.max_size,
                )
        except Exception as e:
            logger.warning(f"缓存初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭缓存。"""
        try:
            cache_manager = CacheManager.get_instance()
            if cache_manager.is_initialized:
                await cache_manager.cleanup()
        except Exception as e:
            logger.warning(f"缓存关闭失败: {e}")


class StorageComponent(Component):
    """对象存储组件。
    
    支持多实例配置，通过环境变量 STORAGE_{INSTANCE}_{FIELD} 配置。
    """

    name = ComponentName.STORAGE
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """当配置了 Storage 实例时启用。"""
        return self.enabled and bool(config.get_storages())

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化存储。"""
        from aury.boot.infrastructure.storage import StorageBackend, StorageConfig
        
        storage_configs = config.get_storages()
        if not storage_configs:
            logger.debug("未配置 Storage 实例，跳过存储初始化")
            return
        
        for name, st_config in storage_configs.items():
            try:
                storage_manager = StorageManager.get_instance(name)
                if not storage_manager.is_initialized:
                    storage_config = StorageConfig(
                        backend=StorageBackend(st_config.backend),
                        access_key_id=st_config.access_key_id,
                        access_key_secret=st_config.access_key_secret,
                        endpoint=st_config.endpoint,
                        region=st_config.region,
                        bucket_name=st_config.bucket_name,
                        base_path=st_config.base_path,
                    )
                    await storage_manager.initialize(storage_config)
            except Exception as e:
                logger.warning(f"存储 [{name}] 初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭所有存储实例。"""
        for name in list(StorageManager._instances.keys()):
            try:
                storage_manager = StorageManager.get_instance(name)
                if storage_manager.is_initialized:
                    await storage_manager.cleanup()
            except Exception as e:
                logger.warning(f"存储 [{name}] 关闭失败: {e}")


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
            from aury.boot.infrastructure.tasks.constants import TaskRunMode
            
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
    """调度器组件。
    
    支持两种任务发现方式：
    1. 配置方式：通过 SCHEDULER_JOB_MODULES 指定要加载的模块
    2. 自动感知：无配置时自动发现 schedules 模块
    
    @scheduler.scheduled_job() 装饰器可以在模块导入时使用，
    任务会被收集到待注册列表，在 start() 时注册并启动。
    """

    name = ComponentName.SCHEDULER
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当是 API 服务且启用调度器时启用。"""
        return (
            self.enabled
            and config.service.service_type == ServiceType.API.value
            and config.scheduler.enabled
        )

    def _autodiscover_schedules(self, app: FoundationApp, config: BaseConfig) -> None:
        """自动发现并加载定时任务模块。
        
        发现策略：
        1. 如果配置了 schedule_modules，直接加载配置的模块
        2. 优先尝试项目包名和服务名：
           - {pyproject.tool.aury.package}.schedules
           - {SERVICE_NAME}.schedules（当 SERVICE_NAME 不是默认值时）
        3. 从 app._caller_module 推断：
           - __main__ / main → 尝试 schedules
           - myapp.main → 尝试 myapp.schedules
        4. 回退：尝试导入 schedules
        """
        modules_to_load: list[str] = []
        
        # 策略 1：配置优先
        if config.scheduler.schedule_modules:
            modules_to_load = list(config.scheduler.schedule_modules)
            logger.debug(f"使用配置的定时任务模块: {modules_to_load}")
        else:
            # 策略 2：项目包名与服务名
            try:
                from aury.boot.commands.config import get_project_config
                cfg = get_project_config()
                if cfg.has_package:
                    modules_to_load.append(f"{cfg.package}.schedules")
            except Exception:
                pass
            
            service_name = (getattr(config.service, "name", None) or "").strip()
            if service_name and service_name not in {"app", "main"}:
                modules_to_load.append(f"{service_name}.schedules")
            
            # 策略 3：从调用者模块推断
            caller = getattr(app, "_caller_module", "__main__")
            if caller in ("__main__", "main"):
                modules_to_load.append("schedules")
            elif "." in caller:
                package = caller.rsplit(".", 1)[0]
                modules_to_load.extend([f"{package}.schedules", "schedules"])
            else:
                modules_to_load.extend([f"{caller}.schedules", "schedules"])
        
        # 去重，保持顺序
        seen = set()
        modules_to_load = [m for m in modules_to_load if not (m in seen or seen.add(m))]
        
        # 加载模块
        for module_name in modules_to_load:
            try:
                module = importlib.import_module(module_name)
                logger.info(f"已自动加载定时任务模块: {module_name}")
                
                # 递归加载包下所有子模块
                if hasattr(module, "__path__"):
                    for _, submodule_name, _ in pkgutil.walk_packages(
                        module.__path__, prefix=f"{module_name}."
                    ):
                        try:
                            importlib.import_module(submodule_name)
                            logger.debug(f"已加载子模块: {submodule_name}")
                        except Exception as e:
                            logger.warning(f"加载子模块失败 ({submodule_name}): {e}")
                
                # 如果成功加载一个，且不是配置模式，就停止
                if not config.scheduler.schedule_modules:
                    break
            except ImportError:
                logger.debug(f"定时任务模块不存在: {module_name}")
            except Exception as e:
                logger.warning(f"加载定时任务模块失败 ({module_name}): {e}")

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """启动调度器。
        
        1. 自动发现并加载定时任务模块
        2. 启动调度器（注册装饰器收集的任务）
        """
        try:
            # 自动发现并加载定时任务模块
            self._autodiscover_schedules(app, config)
            
            # 启动调度器
            scheduler = SchedulerManager.get_instance()
            scheduler.start()
        except Exception as e:
            logger.warning(f"调度器启动失败（非关键）: {e}")

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
            # 创建迁移管理器（从配置读取参数）
            migration_settings = config.migration
            migration_manager = MigrationManager(
                database_url=config.database.url,
                config_path=migration_settings.config_path,
                script_location=migration_settings.script_location,
                model_modules=migration_settings.model_modules,
                auto_create=migration_settings.auto_create,
            )
            
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


class AdminConsoleComponent(Component):
    """管理后台组件（SQLAdmin Admin Console）。

    配置选项（环境变量前缀 ADMIN_ / ADMIN_AUTH_）：
    - ADMIN_ENABLED: 是否启用（默认 False）
    - ADMIN_PATH: 后台路径（默认 /api/admin-console）
    - ADMIN_DATABASE_URL: 同步数据库 URL（可选）
    - ADMIN_AUTH_MODE: basic/bearer/none/custom/jwt
    - ADMIN_AUTH_*: 认证参数

    注意：sqladmin 通常要求同步 SQLAlchemy Engine。
    """

    name = ComponentName.ADMIN_CONSOLE
    enabled = True
    depends_on: ClassVar[list[str]] = [ComponentName.DATABASE]

    def can_enable(self, config: BaseConfig) -> bool:
        return self.enabled and bool(getattr(getattr(config, "admin", None), "enabled", False))

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        try:
            from aury.boot.contrib.admin_console import install_admin_console

            install_admin_console(app, config)
        except ImportError as e:
            logger.error(f"管理后台启用失败：缺少依赖（请安装 aury-boot[admin]）: {e}")
            raise
        except Exception as e:
            logger.error(f"管理后台初始化失败: {e}")
            raise

    async def teardown(self, app: FoundationApp) -> None:
        # SQLAdmin 路由挂载后无需额外 teardown
        pass


class MessageQueueComponent(Component):
    """消息队列组件。
    
    提供统一的消息队列接口，支持多种后端（Redis、RabbitMQ）。
    与 TaskComponent（基于 Dramatiq）的区别：
    - Task: 异步任务处理（API 发送，Worker 执行）
    - MQ: 通用消息队列（生产者/消费者模式，服务间通信）
    """

    name = ComponentName.MESSAGE_QUEUE
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """当配置了 MQ 实例时启用。"""
        return self.enabled and bool(config.get_mqs())

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化消息队列。"""
        from aury.boot.application.config import MQInstanceConfig
        
        # 从多实例配置加载
        mq_configs = config.get_mqs()
        if not mq_configs:
            logger.debug("未配置 MQ 实例，跳过消息队列初始化")
            return
        
        for name, mq_config in mq_configs.items():
            try:
                mq_manager = MQManager.get_instance(name)
                if not mq_manager.is_initialized:
                    await mq_manager.initialize(config=mq_config)
            except Exception as e:
                logger.warning(f"消息队列 [{name}] 初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭所有消息队列实例。"""
        for name in list(MQManager._instances.keys()):
            try:
                mq_manager = MQManager.get_instance(name)
                if mq_manager.is_initialized:
                    await mq_manager.cleanup()
            except Exception as e:
                logger.warning(f"消息队列 [{name}] 关闭失败: {e}")


class EventBusComponent(Component):
    """事件总线组件。
    
    提供发布/订阅模式的事件总线功能，支持多种后端（memory、Redis、RabbitMQ）。
    """

    name = ComponentName.EVENT_BUS
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """当配置了 Event 实例时启用。"""
        return self.enabled and bool(config.get_events())

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化事件总线。"""
        # 从多实例配置加载
        event_configs = config.get_events()
        if not event_configs:
            logger.debug("未配置 Event 实例，跳过事件总线初始化")
            return
        
        for name, event_config in event_configs.items():
            try:
                event_manager = EventBusManager.get_instance(name)
                if not event_manager.is_initialized:
                    await event_manager.initialize(config=event_config)
            except Exception as e:
                logger.warning(f"事件总线 [{name}] 初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭所有事件总线实例。"""
        for name in list(EventBusManager._instances.keys()):
            try:
                event_manager = EventBusManager.get_instance(name)
                if event_manager.is_initialized:
                    await event_manager.cleanup()
            except Exception as e:
                logger.warning(f"事件总线 [{name}] 关闭失败: {e}")


# 设置默认组件
FoundationApp.components = [
    DatabaseComponent,
    MigrationComponent,
    AdminConsoleComponent,
    CacheComponent,
    StorageComponent,
    TaskComponent,
    MessageQueueComponent,
    EventBusComponent,
    SchedulerComponent,
]


__all__ = [
    "AdminConsoleComponent",
    "CacheComponent",
    "DatabaseComponent",
    "EventBusComponent",
    "MessageQueueComponent",
    "MigrationComponent",
    "SchedulerComponent",
    "StorageComponent",
    "TaskComponent",
]


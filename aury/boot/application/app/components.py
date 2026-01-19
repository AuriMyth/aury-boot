"""默认组件实现。

提供所有内置基础设施组件的实现。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import ClassVar

from aury.boot.application.app.base import Component, FoundationApp, Plugin
from aury.boot.application.config import BaseConfig
from aury.boot.application.constants import ComponentName, ServiceType
from aury.boot.application.migrations import MigrationManager
from aury.boot.common.logging import logger
from aury.boot.infrastructure.cache import CacheManager
from aury.boot.infrastructure.channel import ChannelManager
from aury.boot.infrastructure.database import DatabaseManager
from aury.boot.infrastructure.events import EventBusManager
from aury.boot.infrastructure.monitoring.alerting import (
    AlertEventType,
    AlertManager,
    AlertSeverity,
    emit_alert,
)
from aury.boot.infrastructure.monitoring.tracing import (
    TelemetryConfig,
    TelemetryProvider,
    setup_otel_logging,
)
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
                # 在 engine 创建后进行 OTEL instrumentation
                self._instrument_engine(db_manager, config)
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _instrument_engine(self, db_manager: DatabaseManager, config: BaseConfig) -> None:
        """对数据库引擎进行 OTEL instrumentation。"""
        if not config.telemetry.enabled:
            return
        
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            # async engine 需要使用 sync_engine
            SQLAlchemyInstrumentor().instrument(engine=db_manager.engine.sync_engine)
            logger.debug("SQLAlchemy engine instrumentation 已启用")
        except ImportError:
            logger.debug("SQLAlchemy instrumentation 未安装，跳过")
        except Exception as e:
            logger.warning(f"SQLAlchemy engine instrumentation 失败: {e}")

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

    def _build_scheduler_config(self, config: BaseConfig) -> dict:
        """根据配置构建 APScheduler 初始化参数。"""
        scheduler_kwargs: dict = {}
        scheduler_config = config.scheduler
        
        # jobstores: 根据 URL 自动选择存储后端
        if scheduler_config.jobstore_url:
            url = scheduler_config.jobstore_url
            if url.startswith("redis://"):
                try:
                    from apscheduler.jobstores.redis import RedisJobStore
                    scheduler_kwargs["jobstores"] = {
                        "default": RedisJobStore.from_url(url)
                    }
                    logger.info(f"调度器使用 Redis 存储: {url.split('@')[-1]}")
                except ImportError:
                    logger.warning("Redis jobstore 需要安装 redis: pip install redis")
            else:
                # SQLAlchemy 存储 (sqlite/postgresql/mysql)
                try:
                    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
                    scheduler_kwargs["jobstores"] = {
                        "default": SQLAlchemyJobStore(url=url)
                    }
                    logger.info("调度器使用 SQLAlchemy 存储")
                except ImportError:
                    logger.warning("SQLAlchemy jobstore 需要安装 sqlalchemy")
        
        # timezone
        if scheduler_config.timezone:
            scheduler_kwargs["timezone"] = scheduler_config.timezone
        
        # job_defaults
        scheduler_kwargs["job_defaults"] = {
            "coalesce": scheduler_config.coalesce,
            "max_instances": scheduler_config.max_instances,
            "misfire_grace_time": scheduler_config.misfire_grace_time,
        }
        
        return scheduler_kwargs
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """启动调度器。
        
        1. 根据配置初始化调度器（jobstore/timezone/job_defaults）
        2. 自动发现并加载定时任务模块
        3. 启动调度器（注册装饰器收集的任务）
        """
        try:
            # 构建配置
            scheduler_kwargs = self._build_scheduler_config(config)
            
            # 获取/创建调度器实例
            scheduler = SchedulerManager.get_instance("default", **scheduler_kwargs)
            
            # 自动发现并加载定时任务模块
            self._autodiscover_schedules(app, config)
            
            # 启动调度器
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


class ChannelComponent(Component):
    """流式通道组件。
    
    用于 SSE（Server-Sent Events）和实时通信场景，支持 memory 和 redis 后端。
    """

    name = ComponentName.CHANNEL
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """当配置了 Channel 实例时启用。"""
        return self.enabled and bool(config.get_channels())

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化流式通道。"""
        channel_configs = config.get_channels()
        if not channel_configs:
            logger.debug("未配置 Channel 实例，跳过通道初始化")
            return
        
        for name, ch_config in channel_configs.items():
            try:
                channel_manager = ChannelManager.get_instance(name)
                if not channel_manager.is_initialized:
                    await channel_manager.initialize(
                        backend=ch_config.backend,
                        url=ch_config.url,
                    )
            except Exception as e:
                logger.warning(f"通道 [{name}] 初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭所有通道实例。"""
        for name in list(ChannelManager._instances.keys()):
            try:
                channel_manager = ChannelManager.get_instance(name)
                if channel_manager.is_initialized:
                    await channel_manager.cleanup()
            except Exception as e:
                logger.warning(f"通道 [{name}] 关闭失败: {e}")


class TelemetryPlugin(Plugin):
    """OpenTelemetry 插件。
    
    在 app 创建后同步执行，负责：
    - 初始化 TracerProvider
    - 对 FastAPI app 进行 instrumentation
    - 配置 AlertingSpanProcessor 检测慢请求/异常（告警配置从 ALERT__ 读取）
    
    配置方式（环境变量）：
        TELEMETRY__ENABLED=true
        TELEMETRY__TRACES_ENDPOINT=http://jaeger:4317  # 可选
        TELEMETRY__LOGS_ENDPOINT=http://loki:3100      # 可选
        TELEMETRY__METRICS_ENDPOINT=http://prometheus:9090  # 可选
        
        # 告警相关配置从 ALERT__ 读取
        ALERT__ENABLED=true
        ALERT__SLOW_REQUEST_THRESHOLD=1.0
        ALERT__SLOW_SQL_THRESHOLD=0.5
        ALERT__ALERT_ON_SLOW_REQUEST=true
        ALERT__ALERT_ON_SLOW_SQL=true
        ALERT__ALERT_ON_ERROR=true
    """

    name = "telemetry"
    enabled = True

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当 TELEMETRY__ENABLED=true 时启用。"""
        return self.enabled and config.telemetry.enabled

    def install(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化 OpenTelemetry 并对 app 进行 instrumentation。"""
        try:
            # 创建告警回调（调用 alerting 模块，自动应用定制化规则）
            alert_callback = self._create_alert_callback() if config.alert.enabled else None
            
            telemetry_config = TelemetryConfig(
                service_name=config.service.name,
                service_version=config.service.version,
                environment=config.service.environment,
                instrument_fastapi=config.telemetry.instrument_fastapi,
                instrument_sqlalchemy=config.telemetry.instrument_sqlalchemy,
                instrument_httpx=config.telemetry.instrument_httpx,
                # 告警配置全部从 AlertSettings 读取
                alert_enabled=config.alert.enabled,
                slow_request_threshold=config.alert.slow_request_threshold,
                slow_sql_threshold=config.alert.slow_sql_threshold,
                alert_on_slow_request=config.alert.alert_on_slow_request,
                alert_on_slow_sql=config.alert.alert_on_slow_sql,
                alert_on_error=config.alert.alert_on_error,
                alert_callback=alert_callback,
                slow_request_exclude_paths=config.alert.slow_request_exclude_paths,
                traces_endpoint=config.telemetry.traces_endpoint,
                traces_headers=config.telemetry.traces_headers,
                logs_endpoint=config.telemetry.logs_endpoint,
                logs_headers=config.telemetry.logs_headers,
                metrics_endpoint=config.telemetry.metrics_endpoint,
                metrics_headers=config.telemetry.metrics_headers,
                sampling_rate=config.telemetry.sampling_rate,
            )
            
            # 创建并初始化 TelemetryProvider
            provider = TelemetryProvider(telemetry_config)
            success = provider.initialize()
            
            if success:
                # 保存到 app.state 以便 shutdown 时使用
                app.state.telemetry_provider = provider
                
                # 对已创建的 FastAPI app 进行 instrumentation
                provider.instrument_fastapi_app(app)
                
                # 配置 OTLP 日志导出（可选）
                if config.telemetry.logs_endpoint:
                    self._setup_otlp_logging(
                        config.telemetry.logs_endpoint,
                        config.telemetry.logs_headers,
                    )
            else:
                logger.warning("OpenTelemetry 初始化失败（非关键）")
                
        except ImportError as e:
            logger.warning(f"OpenTelemetry 未安装，跳过初始化: {e}")
        except Exception as e:
            logger.warning(f"OpenTelemetry 初始化失败（非关键）: {e}")

    def _create_alert_callback(self):
        """创建告警回调函数。
        
        回调会调用 alerting 模块的 emit_alert，自动应用 YAML 定制化规则。
        """
        # 事件类型映射
        type_mapping = {
            "slow_request": AlertEventType.SLOW_REQUEST,
            "slow_sql": AlertEventType.SLOW_SQL,
            "exception": AlertEventType.EXCEPTION,
            "custom": AlertEventType.CUSTOM,
        }
        
        # 严重级别映射
        severity_mapping = {
            "info": AlertSeverity.INFO,
            "warning": AlertSeverity.WARNING,
            "error": AlertSeverity.ERROR,
            "critical": AlertSeverity.CRITICAL,
        }
        
        async def callback(event_type: str, message: str, **metadata):
            try:
                alert_event_type = type_mapping.get(event_type, AlertEventType.CUSTOM)
                severity_str = metadata.pop("severity", "warning")
                severity = severity_mapping.get(severity_str, AlertSeverity.WARNING)
                
                await emit_alert(
                    alert_event_type,
                    message,
                    severity=severity,
                    **metadata,
                )
            except Exception as e:
                logger.debug(f"发送告警失败: {e}")
        
        return callback
    
    def _setup_otlp_logging(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        """配置 OTLP 日志导出。"""
        try:
            setup_otel_logging(endpoint=endpoint, headers=headers)
        except Exception as e:
            logger.warning(f"OTLP 日志导出配置失败: {e}")

    def uninstall(self, app: FoundationApp) -> None:
        """关闭 OpenTelemetry。"""
        try:
            provider = getattr(app.state, "telemetry_provider", None)
            if provider:
                provider.shutdown()
                logger.info("OpenTelemetry 已关闭")
        except Exception as e:
            logger.warning(f"OpenTelemetry 关闭失败: {e}")


class AlertComponent(Component):
    """告警系统组件。
    
    在 lifespan 启动时异步初始化 AlertManager。
    """

    name = "alert"
    enabled = True
    depends_on: ClassVar[list[str]] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当 ALERT__ENABLED=true 时启用。"""
        return self.enabled and config.alert.enabled

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化告警管理器。"""
        try:
            alert_manager = AlertManager.get_instance()
            if not alert_manager.is_initialized:
                await alert_manager.initialize(
                    enabled=config.alert.enabled,
                    service_name=config.service.name,
                    rules_file=config.alert.rules_file,
                    defaults={
                        "slow_request_threshold": config.alert.slow_request_threshold,
                        "slow_sql_threshold": config.alert.slow_sql_threshold,
                        "aggregate_window": config.alert.aggregate_window,
                        "slow_request_aggregate": config.alert.slow_request_aggregate,
                        "slow_sql_aggregate": config.alert.slow_sql_aggregate,
                        "exception_aggregate": config.alert.exception_aggregate,
                        "suppress_seconds": config.alert.suppress_seconds,
                        "slow_request_exclude_paths": config.alert.slow_request_exclude_paths,
                    },
                    notifiers=config.alert.get_notifiers(),
                )
        except Exception as e:
            logger.warning(f"告警管理器初始化失败（非关键）: {e}")

    async def teardown(self, app: FoundationApp) -> None:
        """无需清理。"""
        pass


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


# 设置默认插件
FoundationApp.plugins = [
    TelemetryPlugin,  # app 创建后立即 instrument
]

# 设置默认组件
FoundationApp.components = [
    AlertComponent,  # 最先初始化告警管理器
    DatabaseComponent,
    MigrationComponent,
    AdminConsoleComponent,
    CacheComponent,
    StorageComponent,
    TaskComponent,
    MessageQueueComponent,
    ChannelComponent,
    EventBusComponent,
    SchedulerComponent,
]


__all__ = [
    "AdminConsoleComponent",
    "AlertComponent",
    "CacheComponent",
    "ChannelComponent",
    "DatabaseComponent",
    "EventBusComponent",
    "MessageQueueComponent",
    "MigrationComponent",
    "SchedulerComponent",
    "StorageComponent",
    "TaskComponent",
    "TelemetryPlugin",
]


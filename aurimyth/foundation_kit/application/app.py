"""Foundation Kit 应用基类。

优雅、抽象、可扩展、不受限的应用框架。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from aurimyth.foundation_kit.application.config import BaseConfig
from aurimyth.foundation_kit.application.constants import ComponentName, SchedulerMode, ServiceType
from aurimyth.foundation_kit.application.interfaces.egress import SuccessResponse
from aurimyth.foundation_kit.application.interfaces.errors import global_exception_handler
from aurimyth.foundation_kit.application.middleware.logging import RequestLoggingMiddleware
from aurimyth.foundation_kit.common.logging import logger, setup_logging
from aurimyth.foundation_kit.infrastructure.cache import CacheManager
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager
from aurimyth.foundation_kit.infrastructure.scheduler import SchedulerManager
from aurimyth.foundation_kit.infrastructure.tasks import TaskManager


class Component(ABC):
    """应用组件基类。

    所有功能单元（中间件、数据库、缓存、任务等）都是 Component。
    支持生命周期管理和依赖声明。

    设计原则：
    - 抽象：统一接口处理所有功能单元
    - 可扩展：用户可以继承或用装饰器定义
    - 不受限：无依赖关系限制，支持任意组合

    使用示例:
        class MyService(Component):
            name = "my_service"
            enabled = True
            depends_on = ["database", "cache"]

            async def setup(self, app: FoundationApp, config: BaseConfig):
                # 初始化逻辑
                pass

            async def teardown(self, app: FoundationApp):
                # 清理逻辑
                pass

        # 或用装饰器
        @app.component(name="my_handler")
        async def setup_handler(app, config):
            pass
    """

    name: str = "component"
    enabled: bool = True
    depends_on: list[str] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """是否可以启用此组件。

        子类可以重写此方法以实现条件化启用。
        默认检查 enabled 属性。

        Args:
            config: 应用配置

        Returns:
            是否启用
        """
        return self.enabled

    @abstractmethod
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """组件启动时调用。

        Args:
            app: 应用实例
            config: 应用配置
        """
        pass

    @abstractmethod
    async def teardown(self, app: FoundationApp) -> None:
        """组件关闭时调用。

        Args:
            app: 应用实例
        """
        pass


class FoundationApp(FastAPI):
    """优雅、抽象、可扩展的应用框架。

    设计特点：
    - 抽象：所有功能单元统一为 Component，无特殊处理
    - 可扩展：只需改类属性，即可添加/移除/替换功能
    - 不受限：无固定的初始化步骤，按依赖关系动态排序

    默认组件（可覆盖）:
        - RequestLoggingComponent
        - CORSComponent
        - DatabaseComponent
        - CacheComponent
        - TaskComponent
        - SchedulerComponent

    使用示例:
        # 基础应用
        app = FoundationApp()

        # 自定义应用
        class MyApp(FoundationApp):
            items = [
                RequestLoggingComponent,
                CORSComponent,
                DatabaseComponent,
                CacheComponent,
                MyCustomComponent,
            ]

        # 或通过装饰器
        @app.component(name="my_service", depends_on=["database"])
        async def setup_my_service(app, config):
            pass
    """

    # 默认组件列表（子类可以覆盖）
    items: list[type[Component] | Component] = []

    def __init__(
        self,
        config: BaseConfig | None = None,
        *,
        title: str = "AuriMyth Service",
        version: str = "1.0.0",
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化应用。

        Args:
            config: 应用配置（可选，默认从环境变量加载）
            title: 应用标题
            version: 应用版本
            description: 应用描述
            **kwargs: 传递给 FastAPI 的其他参数
        """
        # 加载配置
        if config is None:
            config = BaseConfig()
        self._config = config

        # 初始化日志（必须在其他操作之前）
        setup_logging(
            log_level=config.log.level,
            log_file=config.log.file,
        )

        # 初始化组件管理
        self._components: dict[str, Component] = {}
        self._lifecycle_listeners: dict[str, list[Callable]] = {}

        # 创建生命周期管理器
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """应用生命周期管理。"""
            # 启动
            await self._on_startup()
            yield
            # 关闭
            await self._on_shutdown()

        # 调用父类构造函数
        super().__init__(
            title=title,
            version=version,
            description=description,
            lifespan=lifespan,
            **kwargs,
        )

        # 异常处理
        self.add_exception_handler(Exception, global_exception_handler)

        # 注册所有组件
        self._register_components()

        # 设置路由
        self.setup_routes()

    def _register_components(self) -> None:
        """注册所有组件。"""
        for item in self.items:
            # 支持类或实例
            if isinstance(item, type):
                component = item()
            else:
                component = item

            if component.can_enable(self._config):
                self._components[component.name] = component
                logger.debug(f"组件已注册: {component.name}")

    async def _on_startup(self) -> None:
        """启动所有组件。"""
        logger.info("应用启动中...")

        try:
            # 拓扑排序
            sorted_components = self._topological_sort(list(self._components.values()))

            # 启动组件
            for component in sorted_components:
                try:
                    await component.setup(self, self._config)
                    logger.info(f"组件启动成功: {component.name}")
                except Exception as e:
                    logger.error(f"组件启动失败 ({component.name}): {e}")
                    raise

            logger.info("应用启动完成")

        except Exception as e:
            logger.error(f"应用启动异常: {e}")
            raise

    async def _on_shutdown(self) -> None:
        """关闭所有组件。"""
        logger.info("应用关闭中...")

        try:
            # 反序关闭
            sorted_components = self._topological_sort(
                list(self._components.values()),
                reverse=True,
            )

            for component in sorted_components:
                try:
                    await component.teardown(self)
                    logger.info(f"组件关闭成功: {component.name}")
                except Exception as e:
                    logger.warning(f"组件关闭失败 ({component.name}): {e}")

            logger.info("应用关闭完成")

        except Exception as e:
            logger.error(f"应用关闭异常: {e}")

    def _topological_sort(
        self,
        components: list[Component],
        reverse: bool = False,
    ) -> list[Component]:
        """拓扑排序组件。

        按照 depends_on 关系排序，确保依赖先启动。

        Args:
            components: 组件列表
            reverse: 是否反序（用于关闭）

        Returns:
            排序后的组件列表
        """
        # 构建图
        component_map = {comp.name: comp for comp in components}
        visited = set()
        result = []

        def visit(name: str, visiting: set) -> None:
            if name in visited:
                return

            if name in visiting:
                logger.warning(f"检测到循环依赖: {name}")
                return

            visiting.add(name)

            # 访问依赖
            if name in component_map:
                for dep in component_map[name].depends_on:
                    if dep in component_map:
                        visit(dep, visiting)

            visiting.remove(name)
            visited.add(name)

            if name in component_map:
                result.append(component_map[name])

        # 访问所有组件
        for comp in components:
            visit(comp.name, set())

        # 反序用于关闭
        if reverse:
            result.reverse()

        return result

    def setup_routes(self) -> None:
        """设置路由。

        子类可以重写此方法来自定义路由配置。
        """
        # 健康检查端点（默认启用）
        self.setup_health_check()

    def setup_health_check(self) -> None:
        """设置健康检查端点。

        子类可以重写此方法来自定义健康检查逻辑。
        """

        @self.get("/health", tags=["health"])
        async def health_check(request: Request) -> SuccessResponse:
            """健康检查端点。"""
            health_status = {
                "status": "healthy",
                "checks": {},
            }

            # 检查数据库（如果已初始化）
            db_manager = DatabaseManager.get_instance()
            if db_manager._initialized:
                try:
                    await db_manager.health_check()
                    health_status["checks"]["database"] = "ok"
                except Exception as e:
                    health_status["status"] = "unhealthy"
                    health_status["checks"]["database"] = f"error: {str(e)}"

            # 检查缓存（如果已初始化）
            cache_manager = CacheManager.get_instance()
            if cache_manager._backend:
                try:
                    await cache_manager.get("__health_check__", default=None)
                    health_status["checks"]["cache"] = "ok"
                except Exception as e:
                    health_status["checks"]["cache"] = f"error: {str(e)}"

            # 返回状态码
            status_code = (
                status.HTTP_200_OK
                if health_status["status"] == "healthy"
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return JSONResponse(
                content=SuccessResponse(data=health_status).model_dump(),
                status_code=status_code,
            )

    @property
    def config(self) -> BaseConfig:
        """获取应用配置。"""
        return self._config


# ============================================================================
# 默认组件实现
# ============================================================================


class RequestLoggingComponent(Component):
    """请求日志中间件组件。"""

    name = ComponentName.REQUEST_LOGGING
    enabled = True
    depends_on: list[str] = []

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
    depends_on: list[str] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当配置了 allow_origins 时启用。"""
        return self.enabled and bool(config.cors.allow_origins)

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """添加 CORS 中间件。"""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors.allow_origins,
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
    depends_on: list[str] = []

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
                await db_manager.close()
        except Exception as e:
            logger.error(f"数据库关闭失败: {e}")


class CacheComponent(Component):
    """缓存组件。"""

    name = ComponentName.CACHE
    enabled = True
    depends_on: list[str] = []

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
    depends_on: list[str] = []

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当是 Worker 模式且配置了 broker URL 时启用。"""
        return (
            self.enabled
            and config.service.service_type == ServiceType.WORKER
            and bool(config.task.broker_url)
        )

    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化任务队列。"""
        try:
            from aurimyth.foundation_kit.infrastructure.tasks.constants import TaskRunMode
            
            task_manager = TaskManager.get_instance()
            # 将 application 层的 ServiceType.WORKER 转换为 infrastructure 层的 TaskRunMode.WORKER
            # ServiceType.API 和 ServiceType.SCHEDULER 转换为 TaskRunMode.PRODUCER
            if config.service.service_type == ServiceType.WORKER:
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
    depends_on: list[str] = []

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


# 设置默认组件
FoundationApp.items = [
    RequestLoggingComponent,
    CORSComponent,
    DatabaseComponent,
    CacheComponent,
    TaskComponent,
    SchedulerComponent,
]


__all__ = [
    "FoundationApp",
    "Component",
    "RequestLoggingComponent",
    "CORSComponent",
    "DatabaseComponent",
    "CacheComponent",
    "TaskComponent",
    "SchedulerComponent",
]

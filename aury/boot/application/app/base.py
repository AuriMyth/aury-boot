"""应用框架基类。

提供 FoundationApp、Middleware 和 Component 基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
import sys
from typing import Any, ClassVar

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware as StarletteMiddleware

from aury.boot.application.config import BaseConfig
from aury.boot.application.errors import global_exception_handler
from aury.boot.application.interfaces.egress import SuccessResponse
from aury.boot.common.logging import logger, register_log_sink, setup_logging
from aury.boot.infrastructure.cache import CacheManager
from aury.boot.infrastructure.database import DatabaseManager


class Middleware(ABC):
    """HTTP 中间件基类。

    用于处理 HTTP 请求的拦截和处理，如 CORS、请求日志等。
    中间件在应用构造阶段同步注册，在 HTTP 请求处理时执行。

    生命周期：
    1. ``build()`` - 在应用构造阶段（lifespan 之前）同步调用。
       返回 Starlette Middleware 实例，由框架统一注册。

    设计原则：
    - 专注 HTTP 请求处理
    - 同步注册（必须在 lifespan 之前）
    - 按 order 排序执行

    使用示例:
        class MyMiddleware(Middleware):
            name = "my_middleware"
            enabled = True
            order = 10  # 数字小的先执行

            def build(self, config: BaseConfig) -> StarletteMiddleware:
                return StarletteMiddleware(SomeMiddlewareClass, **options)
    """

    name: str = "middleware"
    enabled: bool = True
    order: int = 0  # 执行顺序，数字小的先执行

    def can_enable(self, config: BaseConfig) -> bool:
        """是否可以启用此中间件。

        子类可以重写此方法以实现条件化启用。
        默认检查 enabled 属性。

        Args:
            config: 应用配置

        Returns:
            是否启用
        """
        return self.enabled

    @abstractmethod
    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建中间件实例。

        返回 Starlette Middleware 实例，由框架在构造 FastAPI 时统一注册。

        Args:
            config: 应用配置

        Returns:
            Starlette Middleware 实例
        """
        pass


class Component(ABC):
    """基础设施组件基类。

    用于管理基础设施的生命周期，如数据库、缓存、任务队列等。
    组件在应用启动时异步初始化，在应用关闭时异步清理。

    生命周期：
    1. ``setup()`` - 在应用启动时（lifespan 开始阶段）异步调用。
    2. ``teardown()`` - 在应用关闭时（lifespan 结束阶段）异步调用。

    使用示例:
        class MyService(Component):
            name = "my_service"
            enabled = True
            depends_on = ["database", "cache"]

            async def setup(self, app: FoundationApp, config: BaseConfig):
                # 异步初始化逻辑
                pass

            async def teardown(self, app: FoundationApp):
                # 清理逻辑
                pass
    """

    name: str = "component"
    enabled: bool = True
    depends_on: ClassVar[list[str]] = []

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
        """组件启动时调用（异步，在 lifespan 开始阶段）。

        Args:
            app: 应用实例
            config: 应用配置
        """
        pass

    @abstractmethod
    async def teardown(self, app: FoundationApp) -> None:
        """组件关闭时调用（异步，在 lifespan 结束阶段）。

        用于清理资源。

        Args:
            app: 应用实例
        """
        pass


class FoundationApp(FastAPI):
    """优雅、抽象、可扩展的应用框架。

    设计特点：
    - 分离：中间件和组件分开管理，职责清晰
    - 可扩展：只需改类属性，即可添加/移除/替换功能
    - 不受限：无固定的初始化步骤，组件按依赖关系动态排序

    中间件（Middleware）：
        处理 HTTP 请求拦截，如 CORS、请求日志等。
        在应用构造阶段同步注册，按 order 排序执行。

    组件（Component）：
        管理基础设施生命周期，如数据库、缓存、任务队列等。
        在应用启动时异步初始化，按依赖关系拓扑排序。

    默认中间件（可覆盖）:
        - RequestLoggingMiddleware（请求日志）
        - CORSMiddleware（跨域处理）

    默认组件（可覆盖）:
        - DatabaseComponent（数据库）
        - CacheComponent（缓存）
        - TaskComponent（任务队列）
        - SchedulerComponent（调度器）
        - MigrationComponent（数据库迁移）

    使用示例:
        # 基础应用
        app = FoundationApp()

        # 自定义应用
        class MyApp(FoundationApp):
            middlewares = [
                RequestLoggingMiddleware,
                CORSMiddleware,
            ]
            components = [
                DatabaseComponent,
                CacheComponent,
                MyCustomComponent,
            ]
    """

    # 默认中间件列表（子类可以覆盖）
    middlewares: ClassVar[list[type[Middleware] | Middleware]] = []

    # 默认组件列表（子类可以覆盖）
    components: ClassVar[list[type[Component] | Component]] = []

    def __init__(
        self,
        config: BaseConfig | None = None,
        *,
        title: str = "Aury Service",
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
        
        # 记录调用者模块（用于自动发现 schedules 等模块）
        frame = sys._getframe(1)
        self._caller_module = frame.f_globals.get("__name__", "__main__")

        # 初始化日志（必须在其他操作之前）
        setup_logging(
            log_level=config.log.level,
            log_dir=config.log.dir,
            service_type=config.service.service_type,
            rotation_time=config.log.rotation_time,
            retention_days=config.log.retention_days,
            enable_file_rotation=config.log.enable_file_rotation,
            enable_console=config.log.enable_console,
        )
        
        # 注册 access 日志（HTTP 请求日志）
        register_log_sink("access", filter_key="access")

        # 初始化中间件和组件管理
        self._middlewares: dict[str, Middleware] = {}
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

        # 收集中间件和组件实例并过滤
        self._collect_middlewares()
        self._collect_components()

        # 构建中间件实例列表，传给 FastAPI
        middleware_instances = self._build_middlewares()

        # 调用父类构造函数
        super().__init__(
            title=title,
            version=version,
            description=description,
            lifespan=lifespan,
            middleware=middleware_instances,
            **kwargs,
        )

        # 异常处理
        self.add_exception_handler(Exception, global_exception_handler)

        # 设置路由
        self.setup_routes()

    def _collect_middlewares(self) -> None:
        """收集并实例化所有中间件。

        这一步在 super().__init__() 之前执行，只做实例化和过滤，
        不调用任何需要 app 已完成构造的方法。
        """
        for item in self.middlewares:
            # 支持类或实例
            if isinstance(item, type):
                middleware = item()
            else:
                middleware = item

            if middleware.can_enable(self._config):
                self._middlewares[middleware.name] = middleware
                logger.debug(f"中间件已收集: {middleware.name}")

    def _collect_components(self) -> None:
        """收集并实例化所有组件。

        这一步在 super().__init__() 之前执行，只做实例化和过滤，
        不调用任何需要 app 已完成构造的方法。
        """
        for item in self.components:
            # 支持类或实例
            if isinstance(item, type):
                component = item()
            else:
                component = item

            if component.can_enable(self._config):
                self._components[component.name] = component
                logger.debug(f"组件已收集: {component.name}")

    def _build_middlewares(self) -> list[StarletteMiddleware]:
        """构建所有中间件实例。

        在 super().__init__() 之前调用，返回中间件实例列表传给 FastAPI。
        按 order 升序排序，Starlette 会反向构建栈，最后的最先执行。

        Returns:
            Starlette Middleware 实例列表
        """
        # 按 order 降序排序（Starlette 反向构建，所以降序排列后最小的在最外层）
        sorted_middlewares = sorted(
            self._middlewares.values(),
            key=lambda m: m.order,
            reverse=True,
        )
        result = []
        for middleware in sorted_middlewares:
            instance = middleware.build(self._config)
            result.append(instance)
            logger.debug(f"中间件已构建: {middleware.name}")
        return result

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
            
            # 打印启动横幅和组件状态
            from aury.boot.application.app.startup import (
                collect_component_status,
                print_startup_banner,
            )
            components = collect_component_status()
            print_startup_banner(
                app_name=self.title,
                version=self.version,
                components=components,
            )

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

        使用 Aury 框架的默认健康检查逻辑。
        路径和启用状态可通过 BaseConfig.health_check 配置。

        子类可以重写此方法来自定义健康检查逻辑。
        """
        # 检查是否启用
        if not self._config.health_check.enabled:
            logger.debug("Aury 默认健康检查端点已禁用")
            return

        health_path = self._config.health_check.path

        @self.get(health_path, tags=["health"])
        async def health_check(request: Request) -> SuccessResponse:
            """Aury 框架默认健康检查端点。
            
            检查数据库、缓存等基础设施组件的健康状态。
            注意：此端点与服务自身的健康检查端点独立，可通过配置自定义路径。
            """
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
                    health_status["checks"]["database"] = f"error: {e!s}"

            # 检查缓存（如果已初始化）
            cache_manager = CacheManager.get_instance()
            if cache_manager._backend:
                try:
                    await cache_manager.get("__health_check__", default=None)
                    health_status["checks"]["cache"] = "ok"
                except Exception as e:
                    health_status["checks"]["cache"] = f"error: {e!s}"

            # 返回状态码
            status_code = (
                status.HTTP_200_OK
                if health_status["status"] == "healthy"
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return JSONResponse(
                content=SuccessResponse(data=health_status).model_dump(mode="json"),
                status_code=status_code,
            )
        
        logger.info(f"Aury 默认健康检查端点已注册: {health_path}")

    @property
    def config(self) -> BaseConfig:
        """获取应用配置。"""
        return self._config


__all__ = [
    "Component",
    "Middleware",
]


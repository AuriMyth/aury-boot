"""应用框架基类。

提供 FoundationApp 和 Component 基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, ClassVar

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from aurimyth.foundation_kit.application.config import BaseConfig
from aurimyth.foundation_kit.application.constants import ComponentName
from aurimyth.foundation_kit.application.errors import global_exception_handler
from aurimyth.foundation_kit.application.interfaces.egress import SuccessResponse
from aurimyth.foundation_kit.common.logging import logger, setup_logging
from aurimyth.foundation_kit.infrastructure.cache import CacheManager
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager


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
    """

    # 默认组件列表（子类可以覆盖）
    items: ClassVar[list[type[Component] | Component]] = []

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

        使用 AuriMyth 框架的默认健康检查逻辑。
        路径和启用状态可通过 BaseConfig.health_check 配置。

        子类可以重写此方法来自定义健康检查逻辑。
        """
        # 检查是否启用
        if not self._config.health_check.enabled:
            logger.debug("AuriMyth 默认健康检查端点已禁用")
            return

        health_path = self._config.health_check.path

        @self.get(health_path, tags=["health"])
        async def health_check(request: Request) -> SuccessResponse:
            """AuriMyth 框架默认健康检查端点。
            
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
                content=SuccessResponse(data=health_status).model_dump(),
                status_code=status_code,
            )
        
        logger.info(f"AuriMyth 默认健康检查端点已注册: {health_path}")

    @property
    def config(self) -> BaseConfig:
        """获取应用配置。"""
        return self._config


__all__ = [
    "Component"
]


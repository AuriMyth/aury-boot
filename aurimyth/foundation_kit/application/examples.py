"""FoundationApp Pydantic 集成示例。

演示如何使用 Pydantic 配置定制化组件。
"""

from __future__ import annotations

from pydantic import Field

from aurimyth.foundation_kit.application import (
    Component,
    ComponentConfig,
    FoundationApp,
    LifecycleEvent,
    LifecyclePhase,
)
from aurimyth.foundation_kit.common.logging import logger

# ============================================================================
# 示例 1: 简单的自定义组件配置
# ============================================================================


class MetricsComponentConfig(ComponentConfig):
    """指标收集组件配置。"""

    enabled: bool = True
    sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="采样率（0-1）",
    )
    buffer_size: int = Field(
        default=1000,
        ge=1,
        description="缓冲区大小",
    )
    export_interval: int = Field(
        default=60,
        ge=1,
        description="导出间隔（秒）",
    )


class MetricsComponent(Component):
    """指标收集组件。

    根据 Pydantic 配置自动验证参数。
    """

    name = "metrics"
    order = 5
    config_class = MetricsComponentConfig

    async def setup(self, app: FoundationApp) -> None:
        """启动指标收集。"""
        config = self.get_config(app.config)
        logger.info(
            f"指标组件启动: sample_rate={config.sample_rate}, "
            f"buffer_size={config.buffer_size}"
        )

    async def teardown(self, app: FoundationApp) -> None:
        """关闭指标收集。"""
        logger.info("指标组件关闭")


# ============================================================================
# 示例 2: 带有验证的组件配置
# ============================================================================


class TraceComponentConfig(ComponentConfig):
    """分布式追踪组件配置。"""

    enabled: bool = True
    service_name: str = Field(..., min_length=1, description="服务名称")
    agent_host: str = Field(
        default="localhost",
        description="Jaeger Agent 主机",
    )
    agent_port: int = Field(
        default=6831,
        ge=1,
        le=65535,
        description="Jaeger Agent 端口",
    )


class TraceComponent(Component):
    """分布式追踪组件。

    配置会被 Pydantic 自动验证。
    """

    name = "trace"
    order = 6
    config_class = TraceComponentConfig

    async def setup(self, app: FoundationApp) -> None:
        """初始化分布式追踪。"""
        config = self.get_config(app.config)
        logger.info(
            f"追踪组件启动: service={config.service_name}, "
            f"agent={config.agent_host}:{config.agent_port}"
        )

    async def teardown(self, app: FoundationApp) -> None:
        """关闭分布式追踪。"""
        logger.info("追踪组件关闭")


# ============================================================================
# 示例 3: 最小化应用
# ============================================================================


def create_simple_app() -> FoundationApp:
    """创建最小化应用。

    只需配置，组件会自动启用和验证。
    """
    app = FoundationApp(title="Simple Service")

    # 注册自定义组件
    app.register_component(MetricsComponent())

    return app


# ============================================================================
# 示例 4: 完整应用（带事件监听）
# ============================================================================


def create_full_app() -> FoundationApp:
    """创建完整应用。

    包括事件监听和自定义生命周期钩子。
    """

    class MyApp(FoundationApp):
        """自定义应用。"""

        async def on_startup_custom(self) -> None:
            """自定义启动逻辑。"""
            logger.info("应用特定的初始化")

        async def on_shutdown_custom(self) -> None:
            """自定义关闭逻辑。"""
            logger.info("应用特定的清理")

    app = MyApp(title="Full Service")

    # 注册自定义组件
    app.register_component(MetricsComponent())
    app.register_component(TraceComponent())

    # 订阅生命周期事件
    async def on_startup(event: LifecycleEvent) -> None:
        logger.info(f"应用启动完成，时间戳: {event.timestamp}")

    app.subscribe_lifecycle_event(LifecyclePhase.AFTER_STARTUP, on_startup)

    async def on_shutdown(event: LifecycleEvent) -> None:
        logger.info(f"应用关闭完成，时间戳: {event.timestamp}")

    app.subscribe_lifecycle_event(LifecyclePhase.AFTER_SHUTDOWN, on_shutdown)

    return app


# ============================================================================
# 示例 5: 条件化启用组件
# ============================================================================


class OptionalFeatureConfig(ComponentConfig):
    """可选功能配置。"""

    enabled: bool = False  # 默认禁用
    feature_key: str | None = Field(
        default=None,
        description="功能密钥（需要设置才能启用）",
    )


class OptionalFeatureComponent(Component):
    """可选功能组件。

    只有在配置了 feature_key 时才启用。
    """

    name = "optional_feature"
    order = 50
    config_class = OptionalFeatureConfig

    def should_enable(self, config) -> bool:
        """条件化启用：必须配置 feature_key。"""
        try:
            feature_config = self.get_config(config)
            # 只有在启用且有密钥时才启用
            return feature_config.enabled and bool(feature_config.feature_key)
        except Exception:
            return False

    async def setup(self, app: FoundationApp) -> None:
        """启动可选功能。"""
        config = self.get_config(app.config)
        logger.info(f"可选功能启动: key={config.feature_key}")

    async def teardown(self, app: FoundationApp) -> None:
        """关闭可选功能。"""
        logger.info("可选功能关闭")


# ============================================================================
# 示例 6: 使用示例
# ============================================================================


# ============================================================================
# 示例 7: 中间件注册
# ============================================================================


def create_app_with_middleware() -> FoundationApp:
    """创建带中间件的应用。

    演示三种添加中间件的方式。
    """
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware

    # 自定义中间件
    class CustomMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            logger.info(f"请求: {request.method} {request.url.path}")
            response = await call_next(request)
            logger.info(f"响应状态码: {response.status_code}")
            return response

    # 方式 1: 直接注册（推荐，最简单）
    app = FoundationApp(title="Middleware Service")
    app.register_middleware(CustomMiddleware)

    # 也可以链式调用
    # app.register_middleware(Middleware1).register_middleware(Middleware2)

    return app


class MyAppWithMiddleware(FoundationApp):
    """方式 2: 继承重写 setup_middleware。"""

    def setup_middleware(self) -> None:
        """重写 setup_middleware 添加自定义中间件。"""
        # 调用父类保留默认中间件和已注册的中间件
        super().setup_middleware()

        # 添加自己的中间件
        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware

        class AuthMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # 在这里添加认证逻辑
                request.state.user = "anonymous"
                response = await call_next(request)
                return response

        self.add_middleware(AuthMiddleware)


class MiddlewareComponent(Component):
    """方式 3: 通过组件注册中间件。"""

    name = "middleware"
    order = 0  # 最早启动

    async def setup(self, app: FoundationApp) -> None:
        """在应用启动前注册中间件。"""
        from fastapi import Request
        from starlette.middleware.base import BaseHTTPMiddleware

        class LoggingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                logger.info(f"组件中间件处理: {request.url.path}")
                return await call_next(request)

        # 通过组件注册
        app.register_middleware(LoggingMiddleware)

    async def teardown(self, app: FoundationApp) -> None:
        """应用关闭时的清理逻辑。"""
        pass


if __name__ == "__main__":
    """
    使用示例：

    # 简单应用
    app = create_simple_app()

    # 完整应用
    app = create_full_app()

    # 添加可选功能
    app.register_component(OptionalFeatureComponent())

    # 方式 1: 直接注册中间件（推荐）
    app = create_app_with_middleware()

    # 方式 2: 继承重写 setup_middleware
    app = MyAppWithMiddleware()

    # 方式 3: 通过组件注册中间件
    app = FoundationApp()
    app.register_component(MiddlewareComponent())

    # 注意：需要在 .env 中配置组件配置
    # 例如：
    # METRICS_SAMPLE_RATE=0.5
    # METRICS_BUFFER_SIZE=2000
    # TRACE_SERVICE_NAME=my-service
    # TRACE_AGENT_HOST=jaeger-agent
    # TRACE_AGENT_PORT=6831
    """
    print(__doc__)


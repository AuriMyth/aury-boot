"""Prometheus Metrics 模块。

提供基于 prometheus-fastapi-instrumentator 的 HTTP 指标采集。

使用方式：
    1. 安装依赖: pip install prometheus-fastapi-instrumentator
    2. 配置环境变量: PROMETHEUS_METRICS__ENABLED=true
    3. 访问 /metrics 端点查看指标

主要指标：
    - http_requests_total: HTTP 请求总数
    - http_request_duration_seconds: 请求延迟直方图
    - http_requests_in_progress: 进行中的请求数（活跃连接）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aury.boot.application.app.base import Plugin
from aury.boot.common.logging import logger

if TYPE_CHECKING:
    from aury.boot.application.app.base import FoundationApp
    from aury.boot.application.config import BaseConfig


class PrometheusMetricsPlugin(Plugin):
    """Prometheus Metrics 插件。
    
    在 app 创建后同步执行，负责：
    - 初始化 prometheus-fastapi-instrumentator
    - 配置指标采集选项
    - 暴露 /metrics 端点
    
    配置方式（环境变量）：
        PROMETHEUS_METRICS__ENABLED=true
        PROMETHEUS_METRICS__PATH=/metrics
        PROMETHEUS_METRICS__SHOULD_INSTRUMENT_REQUESTS_INPROGRESS=true
    """

    name = "metrics"
    enabled = True

    def can_enable(self, config: BaseConfig) -> bool:
        """仅当 PROMETHEUS_METRICS__ENABLED=true 时启用。"""
        return self.enabled and config.prometheus_metrics.enabled

    def install(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化 Prometheus Metrics 并暴露端点。"""
        try:
            from prometheus_fastapi_instrumentator import Instrumentator
        except ImportError:
            logger.warning(
                "prometheus-fastapi-instrumentator 未安装，跳过 Metrics 初始化。"
                "请运行: pip install prometheus-fastapi-instrumentator"
            )
            return

        try:
            metrics_config = config.prometheus_metrics
            
            # 创建 Instrumentator 实例
            instrumentator = Instrumentator(
                should_group_status_codes=metrics_config.should_group_status_codes,
                should_ignore_untemplated=metrics_config.should_ignore_untemplated,
                should_group_untemplated=metrics_config.should_group_untemplated,
                should_round_latency_decimals=metrics_config.should_round_latency_decimals,
                should_respect_env_var=metrics_config.should_respect_env_var,
                should_instrument_requests_inprogress=metrics_config.should_instrument_requests_inprogress,
                excluded_handlers=metrics_config.excluded_handlers,
            )
            
            # Instrument app
            instrumentator.instrument(app)
            
            # 暴露 /metrics 端点
            instrumentator.expose(
                app,
                endpoint=metrics_config.path,
                include_in_schema=metrics_config.include_in_schema,
            )
            
            # 保存到 app.state 以便后续访问
            app.state.metrics_instrumentator = instrumentator
            
            logger.info(f"Prometheus Metrics 已启用，端点: {metrics_config.path}")
            
        except Exception as e:
            logger.warning(f"Prometheus Metrics 初始化失败（非关键）: {e}")

    def uninstall(self, app: FoundationApp) -> None:
        """清理 Metrics 资源。"""
        if hasattr(app.state, "metrics_instrumentator"):
            delattr(app.state, "metrics_instrumentator")
            logger.debug("Prometheus Metrics 已清理")


__all__ = ["PrometheusMetricsPlugin"]

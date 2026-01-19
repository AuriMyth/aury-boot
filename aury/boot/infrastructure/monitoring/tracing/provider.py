"""OpenTelemetry TracerProvider 配置和初始化。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

from .processor import AlertingSpanProcessor

# OTel 核心可选依赖
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider as OTelTracerProvider
except ImportError:
    otel_trace = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment, misc]
    OTelTracerProvider = None  # type: ignore[assignment, misc]

# OTel Traces 导出可选依赖
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:
    OTLPSpanExporter = None  # type: ignore[assignment, misc]
    BatchSpanProcessor = None  # type: ignore[assignment, misc]

# OTel Metrics 导出可选依赖
try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
except ImportError:
    otel_metrics = None  # type: ignore[assignment]
    OTLPMetricExporter = None  # type: ignore[assignment, misc]
    MeterProvider = None  # type: ignore[assignment, misc]
    PeriodicExportingMetricReader = None  # type: ignore[assignment, misc]

# OTel Instrumentation 可选依赖
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ImportError:
    FastAPIInstrumentor = None  # type: ignore[assignment, misc]

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
except ImportError:
    SQLAlchemyInstrumentor = None  # type: ignore[assignment, misc]

try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except ImportError:
    HTTPXClientInstrumentor = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import SpanProcessor, TracerProvider


@dataclass
class TelemetryConfig:
    """遍测配置。"""
    
    # 基础配置
    service_name: str = "aury-service"
    service_version: str = ""
    environment: str = "development"
    
    # 启用的 instrumentation
    instrument_fastapi: bool = True
    instrument_sqlalchemy: bool = True
    instrument_httpx: bool = True
    
    # 告警配置
    alert_enabled: bool = True
    slow_request_threshold: float = 1.0  # HTTP 请求慢阈值（秒）
    slow_sql_threshold: float = 0.5  # SQL 查询慢阈值（秒）
    alert_on_slow_request: bool = True  # 是否对慢 HTTP 请求发送告警
    alert_on_slow_sql: bool = True  # 是否对慢 SQL 发送告警
    alert_on_error: bool = True
    alert_callback: Any = None  # 告警回调函数
    slow_request_exclude_paths: list[str] = field(default_factory=list)  # 慢请求排除路径
    
    # OTLP Traces 导出配置
    traces_endpoint: str | None = None
    traces_headers: dict[str, str] = field(default_factory=dict)
    
    # OTLP Logs 导出配置
    logs_endpoint: str | None = None
    logs_headers: dict[str, str] = field(default_factory=dict)
    
    # OTLP Metrics 导出配置
    metrics_endpoint: str | None = None
    metrics_headers: dict[str, str] = field(default_factory=dict)
    
    # 采样配置
    sampling_rate: float = 1.0  # 1.0 = 100%


class TelemetryProvider:
    """遥测提供者。
    
    封装 OpenTelemetry TracerProvider 的配置和初始化逻辑。
    """
    
    def __init__(self, config: TelemetryConfig) -> None:
        """初始化 TelemetryProvider。
        
        Args:
            config: 遥测配置
        """
        self._config = config
        self._provider: "TracerProvider | None" = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """初始化 OpenTelemetry。
        
        Returns:
            bool: 是否成功初始化
        """
        if self._initialized:
            return True
        
        if OTelTracerProvider is None:
            logger.warning("OpenTelemetry 初始化失败（缺少依赖）")
            return False
        
        try:
            # 创建 Resource
            resource = Resource.create({
                "service.name": self._config.service_name,
                "service.version": self._config.service_version,
                "deployment.environment": self._config.environment,
            })
            
            # 创建 TracerProvider
            self._provider = OTelTracerProvider(resource=resource)
            
            # 添加 SpanProcessor
            self._setup_processors()
            
            # 设置为全局 TracerProvider
            otel_trace.set_tracer_provider(self._provider)
            
            # 配置 instrumentation
            self._setup_instrumentations()
            
            self._initialized = True
            logger.info(
                f"OpenTelemetry 初始化完成: "
                f"service={self._config.service_name}, "
                f"alert_enabled={self._config.alert_enabled}"
            )
            return True
        except Exception as e:
            logger.error(f"OpenTelemetry 初始化失败: {e}")
            return False
    
    def shutdown(self) -> None:
        """关闭 OpenTelemetry。"""
        if self._provider:
            try:
                self._provider.shutdown()
                logger.info("OpenTelemetry 已关闭")
            except Exception as e:
                logger.warning(f"OpenTelemetry 关闭失败: {e}")
    
    def _setup_processors(self) -> None:
        """设置 SpanProcessor。"""
        if not self._provider:
            return
        
        # 添加告警处理器
        if self._config.alert_enabled:
            alerting_processor = AlertingSpanProcessor(
                slow_request_threshold=self._config.slow_request_threshold,
                slow_sql_threshold=self._config.slow_sql_threshold,
                alert_on_slow_request=self._config.alert_on_slow_request,
                alert_on_slow_sql=self._config.alert_on_slow_sql,
                alert_on_error=self._config.alert_on_error,
                alert_callback=self._config.alert_callback,
                slow_request_exclude_paths=self._config.slow_request_exclude_paths or None,
            )
            self._provider.add_span_processor(alerting_processor)
            logger.debug("已添加 AlertingSpanProcessor")
        
        # 添加 OTLP Traces 导出器
        if self._config.traces_endpoint:
            self._setup_traces_exporter()
        
        # 添加 OTLP Metrics 导出器
        if self._config.metrics_endpoint:
            self._setup_metrics_exporter()
    
    def _setup_traces_exporter(self) -> None:
        """设置 Traces OTLP 导出器。"""
        if not self._provider or not self._config.traces_endpoint:
            return
        
        if OTLPSpanExporter is None:
            logger.warning("Traces OTLP 导出器未安装，跳过配置")
            return
        
        try:
            exporter = OTLPSpanExporter(
                endpoint=self._config.traces_endpoint,
                headers=self._config.traces_headers or None,
            )
            self._provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"Traces OTLP 导出器已配置: {self._config.traces_endpoint}")
        except Exception as e:
            logger.warning(f"Traces OTLP 导出器配置失败: {e}")
    
    def _setup_metrics_exporter(self) -> None:
        """设置 Metrics OTLP 导出器。"""
        if not self._config.metrics_endpoint:
            return
        
        if OTLPMetricExporter is None:
            logger.warning("Metrics OTLP 导出器未安装，跳过配置")
            return
        
        try:
            resource = Resource.create({
                "service.name": self._config.service_name,
                "service.version": self._config.service_version,
                "deployment.environment": self._config.environment,
            })
            
            exporter = OTLPMetricExporter(
                endpoint=self._config.metrics_endpoint,
                headers=self._config.metrics_headers or None,
            )
            reader = PeriodicExportingMetricReader(exporter)
            meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            otel_metrics.set_meter_provider(meter_provider)
            
            logger.info(f"Metrics OTLP 导出器已配置: {self._config.metrics_endpoint}")
        except Exception as e:
            logger.warning(f"Metrics OTLP 导出器配置失败: {e}")
    
    def _setup_instrumentations(self) -> None:
        """配置自动 instrumentation。
        
        注意：
        - FastAPI instrumentation 需要通过 instrument_fastapi_app() 单独调用。
        - SQLAlchemy instrumentation 需要在 engine 创建后调用（由 DatabaseComponent 处理）。
        """
        enabled = []
        pending = []
        
        # SQLAlchemy instrumentation 需要 engine，在 DatabaseComponent 中处理
        if self._config.instrument_sqlalchemy:
            pending.append("SQLAlchemy")
        
        # HTTPX instrumentation
        if self._config.instrument_httpx:
            if self._instrument_httpx():
                enabled.append("HTTPX")
        
        if enabled:
            logger.info(f"Instrumentation 已启用: {', '.join(enabled)}")
        if pending:
            logger.debug(f"Instrumentation 待启用（需要 engine）: {', '.join(pending)}")
    
    def instrument_fastapi_app(self, app) -> None:
        """对已创建的 FastAPI app 进行 instrumentation。
        
        Args:
            app: FastAPI 应用实例
        """
        if FastAPIInstrumentor is None:
            logger.debug("FastAPI instrumentation 未安装")
            return
        
        if not self._config.instrument_fastapi:
            return
        
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumentation 已启用")
        except Exception as e:
            logger.warning(f"FastAPI instrumentation 配置失败: {e}")
    
    
    def _instrument_httpx(self) -> bool:
        """配置 HTTPX instrumentation。"""
        if HTTPXClientInstrumentor is None:
            logger.debug("HTTPX instrumentation 未安装")
            return False
        
        try:
            HTTPXClientInstrumentor().instrument()
            return True
        except Exception as e:
            logger.warning(f"HTTPX instrumentation 配置失败: {e}")
            return False
    
    def add_processor(self, processor: "SpanProcessor") -> None:
        """添加自定义 SpanProcessor。
        
        Args:
            processor: SpanProcessor 实例
        """
        if self._provider:
            self._provider.add_span_processor(processor)
    
    @property
    def provider(self) -> "TracerProvider | None":
        """获取 TracerProvider 实例。"""
        return self._provider
    
    @property
    def is_initialized(self) -> bool:
        """是否已初始化。"""
        return self._initialized


__all__ = ["TelemetryConfig", "TelemetryProvider"]

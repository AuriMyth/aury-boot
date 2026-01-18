"""OTel Logs 集成。

将 loguru 日志接入 OpenTelemetry，导出到 OTLP（Loki/Elasticsearch 等）。

用法:
    # 在 TelemetryComponent 中自动配置
    TELEMETRY__LOGS_ENDPOINT=http://loki:3100
    
    # 或手动配置:
    setup_otel_logging(endpoint="http://loki:3100")
"""

from __future__ import annotations

import logging

from aury.boot.common.logging import logger

# OTel Logs 可选依赖
try:
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
except ImportError:
    OTLPLogExporter = None  # type: ignore[assignment, misc]


def setup_otel_logging(
    endpoint: str,
    headers: dict[str, str] | None = None,
) -> None:
    """配置 OTel 日志集成。
    
    Args:
        endpoint: OTLP 日志导出端点（如 http://loki:3100）
        headers: OTLP 请求头（可选）
    """
    if OTLPLogExporter is None:
        logger.debug("OTLP 日志导出器未安装")
        return
    
    try:
        # 创建 LoggerProvider
        logger_provider = LoggerProvider()
        set_logger_provider(logger_provider)
        
        # 添加 OTLP 导出器
        exporter = OTLPLogExporter(
            endpoint=endpoint,
            headers=headers or None,
        )
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(exporter)
        )
        
        # 添加标准 logging handler
        logging_handler = LoggingHandler(
            level="DEBUG",
            logger_provider=logger_provider,
        )
        
        # 配置 loguru 转发到标准 logging
        logging.getLogger().addHandler(logging_handler)
        
        logger.info(f"Logs OTLP 导出器已配置: {endpoint}")
    except Exception as e:
        logger.warning(f"OTLP 日志导出配置失败: {e}")


__all__ = [
    "setup_otel_logging",
]

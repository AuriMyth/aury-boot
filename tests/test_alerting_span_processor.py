from __future__ import annotations

import asyncio
import time

import pytest

otel_trace = pytest.importorskip("opentelemetry.trace")
sdk_trace = pytest.importorskip("opentelemetry.sdk.trace")

from aury.boot.infrastructure.monitoring.tracing.processor import AlertingSpanProcessor

SpanProcessor = sdk_trace.SpanProcessor
TracerProvider = sdk_trace.TracerProvider


def test_alerting_span_processor_implements_current_span_processor_protocol() -> None:
    processor = AlertingSpanProcessor()

    assert isinstance(processor, SpanProcessor)
    assert hasattr(processor, "_on_ending")


@pytest.mark.asyncio
async def test_alerting_span_processor_emits_slow_request_alert() -> None:
    events: list[tuple[str, str, dict[str, object]]] = []

    async def alert_callback(event_type: str, message: str, **metadata: object) -> None:
        events.append((event_type, message, metadata))

    provider = TracerProvider()
    provider.add_span_processor(
        AlertingSpanProcessor(
            slow_request_threshold=0.001,
            slow_sql_threshold=1.0,
            alert_callback=alert_callback,
        )
    )
    tracer = provider.get_tracer(__name__)

    with tracer.start_as_current_span("GET /health", kind=otel_trace.SpanKind.SERVER) as span:
        span.set_attribute("http.route", "/health")
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.status_code", 200)
        await asyncio.sleep(0.01)

    await asyncio.sleep(0)
    provider.shutdown()

    assert len(events) == 1
    event_type, message, metadata = events[0]
    assert event_type == "slow_request"
    assert message == "慢 http: GET /health"
    assert metadata["route"] == "/health"
    assert metadata["method"] == "GET"
    assert metadata["status_code"] == 200


def test_alerting_span_processor_does_not_break_span_end_when_callback_is_invalid() -> None:
    provider = TracerProvider()
    provider.add_span_processor(
        AlertingSpanProcessor(
            slow_request_threshold=0.001,
            slow_sql_threshold=1.0,
            alert_callback=object(),  # type: ignore[arg-type]
        )
    )
    tracer = provider.get_tracer(__name__)

    with tracer.start_as_current_span("GET /broken", kind=otel_trace.SpanKind.SERVER) as span:
        span.set_attribute("http.route", "/broken")
        span.set_attribute("http.status_code", 200)
        time.sleep(0.01)

    provider.shutdown()

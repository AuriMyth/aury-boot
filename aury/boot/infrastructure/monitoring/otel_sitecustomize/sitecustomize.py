"""Initialize OTel auto-instrumentation in Python worker processes.

This module is loaded by Python's standard ``sitecustomize`` mechanism when
its containing directory is present on ``PYTHONPATH``. It is intentionally
guarded by Aury-specific environment variables so importing arbitrary Python
tools from the same image does not enable tracing by accident.
"""

from __future__ import annotations

import builtins
import os
import sys


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _should_initialize() -> bool:
    if getattr(builtins, "_aury_otel_sitecustomize_initialized", False):
        return False
    if not _is_truthy(os.environ.get("AURY_OTEL_SITECUSTOMIZE")):
        return False
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return False
    # Prefer Aury's explicit TelemetryPlugin when it is enabled. The plugin runs
    # inside each app worker and avoids double-registering providers.
    return not _is_truthy(os.environ.get("TELEMETRY__ENABLED"))


def _initialize() -> None:
    if not _should_initialize():
        return

    builtins._aury_otel_sitecustomize_initialized = True
    try:
        from opentelemetry.instrumentation.auto_instrumentation import initialize

        initialize()
    except Exception as exc:  # pragma: no cover - startup safety path
        print(
            f"[AURY_OTEL] WARN: OpenTelemetry auto-instrumentation failed: {exc}",
            file=sys.stderr,
        )


_initialize()

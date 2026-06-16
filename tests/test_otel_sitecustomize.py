from __future__ import annotations

import importlib
import os

from aury.boot.infrastructure.monitoring import otel_sitecustomize

server_app = importlib.import_module("aury.boot.commands.server.app")


def test_enable_otel_sitecustomize_injects_pythonpath(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.delenv("TELEMETRY__AUTO_INSTRUMENTATION_ENABLED", raising=False)

    server_app._enable_otel_sitecustomize_if_requested(True)

    paths = os.environ["PYTHONPATH"].split(os.pathsep)
    assert paths[0] == str(otel_sitecustomize.__path__[0])
    assert paths[1] == str(tmp_path)
    assert os.environ["TELEMETRY__AUTO_INSTRUMENTATION_ENABLED"] == "true"


def test_enable_otel_sitecustomize_env_flag(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TELEMETRY__AUTO_INSTRUMENTATION_ENABLED", "true")
    monkeypatch.setenv("PYTHONPATH", "/existing")

    server_app._enable_otel_sitecustomize_if_requested(False)

    paths = os.environ["PYTHONPATH"].split(os.pathsep)
    assert paths[:2] == [str(otel_sitecustomize.__path__[0]), str(tmp_path)]
    assert paths[2:] == ["/existing"]


def test_enable_otel_sitecustomize_noop_when_not_requested(monkeypatch) -> None:
    monkeypatch.delenv("PYTHONPATH", raising=False)
    monkeypatch.delenv("TELEMETRY__AUTO_INSTRUMENTATION_ENABLED", raising=False)

    server_app._enable_otel_sitecustomize_if_requested(False)

    assert "PYTHONPATH" not in os.environ
    assert "TELEMETRY__AUTO_INSTRUMENTATION_ENABLED" not in os.environ

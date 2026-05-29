"""Scheduler Redis Sentinel jobstore tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from aury.boot.application.app.components import SchedulerComponent
from aury.boot.application.config import BaseConfig
import aury.boot.infrastructure.scheduler.jobstores as jobstores_module
import aury.boot.infrastructure.scheduler.jobstores.redis_sentinel as sentinel_jobstore_module
from aury.boot.infrastructure.scheduler.jobstores.redis_sentinel import RedisSentinelJobStore


class FakeSentinel:
    instances: list["FakeSentinel"] = []

    def __init__(self, sentinels, **kwargs) -> None:
        self.sentinels = sentinels
        self.kwargs = kwargs
        self.master_name = None
        self.master_kwargs = None
        self.redis = object()
        self.__class__.instances.append(self)

    def master_for(self, master_name: str, **kwargs):
        self.master_name = master_name
        self.master_kwargs = kwargs
        return self.redis


class FakeSentinelJobStore:
    instances: list["FakeSentinelJobStore"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.__class__.instances.append(self)


def _missing_env(tmp_path: Path) -> Path:
    return tmp_path / "missing.env"


def test_redis_sentinel_jobstore_builds_master_client(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeSentinel.instances.clear()
    monkeypatch.setattr(sentinel_jobstore_module, "Sentinel", FakeSentinel)

    store = RedisSentinelJobStore(
        sentinels=["10.0.0.1:26379", "10.0.0.2:26379"],
        master_name="mymaster",
        redis_username="frontis_redis_rw",
        redis_password="redis-password",
        sentinel_username="sentinel-user",
        sentinel_password="sentinel-password",
        db=14,
        prefix="frontis-workbench:scheduler:",
        socket_timeout=3.0,
        max_connections=50,
    )

    fake_sentinel = FakeSentinel.instances[0]
    assert fake_sentinel.sentinels == [("10.0.0.1", 26379), ("10.0.0.2", 26379)]
    assert fake_sentinel.kwargs["sentinel_kwargs"] == {
        "username": "sentinel-user",
        "password": "sentinel-password",
    }
    assert fake_sentinel.kwargs["socket_timeout"] == 3.0
    assert fake_sentinel.master_name == "mymaster"
    assert fake_sentinel.master_kwargs == {
        "db": 14,
        "socket_timeout": 3.0,
        "max_connections": 50,
        "username": "frontis_redis_rw",
        "password": "redis-password",
    }
    assert store.redis is fake_sentinel.redis
    assert store.jobs_key == "frontis-workbench:scheduler:apscheduler.jobs"
    assert store.run_times_key == "frontis-workbench:scheduler:apscheduler.run_times"


def test_scheduler_component_prefers_sentinel_jobstore(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    FakeSentinelJobStore.instances.clear()
    monkeypatch.setattr(jobstores_module, "RedisSentinelJobStore", FakeSentinelJobStore)
    monkeypatch.setenv("SCHEDULER__JOBSTORE_URL", "redis://plain-redis:6379/4")
    monkeypatch.setenv("SCHEDULER__SENTINEL__ENABLED", "true")
    monkeypatch.setenv("SCHEDULER__SENTINEL__NODES", '["10.0.0.1:26379","10.0.0.2:26379"]')
    monkeypatch.setenv("SCHEDULER__SENTINEL__MASTER_NAME", "mymaster")
    monkeypatch.setenv("SCHEDULER__SENTINEL__USERNAME", "frontis_redis_rw")
    monkeypatch.setenv("SCHEDULER__SENTINEL__DB", "14")
    monkeypatch.setenv("SCHEDULER__SENTINEL__PREFIX", "frontis-workbench:scheduler:")

    config = BaseConfig(_env_file=_missing_env(tmp_path))
    scheduler_kwargs = SchedulerComponent()._build_scheduler_config(config)

    jobstore = scheduler_kwargs["jobstores"]["default"]
    assert jobstore is FakeSentinelJobStore.instances[0]
    assert jobstore.kwargs["sentinels"] == [("10.0.0.1", 26379), ("10.0.0.2", 26379)]
    assert jobstore.kwargs["master_name"] == "mymaster"
    assert jobstore.kwargs["redis_username"] == "frontis_redis_rw"
    assert jobstore.kwargs["db"] == 14
    assert jobstore.kwargs["prefix"] == "frontis-workbench:scheduler:"

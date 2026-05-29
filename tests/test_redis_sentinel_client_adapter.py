"""Redis Sentinel client adapter tests."""

from __future__ import annotations

import pytest

import aury.boot.infrastructure.redis_sentinel as redis_sentinel_module
from aury.boot.infrastructure.redis_sentinel import SentinelRedisClientAdapter


class FakeRedis:
    async def ping(self) -> bool:
        return True


class FakeSentinel:
    instances: list["FakeSentinel"] = []

    def __init__(self, sentinels, **kwargs) -> None:
        self.sentinels = sentinels
        self.kwargs = kwargs
        self.master_name = None
        self.master_kwargs = None
        self.redis = FakeRedis()
        self.__class__.instances.append(self)

    def master_for(self, service_name: str, **kwargs):
        self.master_name = service_name
        self.master_kwargs = kwargs
        return self.redis


@pytest.mark.asyncio
async def test_sentinel_adapter_passes_acl_usernames(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeSentinel.instances.clear()
    monkeypatch.setattr(redis_sentinel_module, "Sentinel", FakeSentinel)

    adapter = SentinelRedisClientAdapter(
        name="test",
        sentinels=[("10.0.0.1", 26379)],
        master_name="mymaster",
        redis_username="frontis_redis_rw",
        redis_password="redis-password",
        sentinel_username="sentinel-user",
        sentinel_password="sentinel-password",
        db=12,
        decode_responses=False,
        socket_timeout=3.0,
        max_connections=50,
    )

    await adapter.initialize()

    fake_sentinel = FakeSentinel.instances[0]
    assert fake_sentinel.kwargs["sentinel_kwargs"] == {
        "username": "sentinel-user",
        "password": "sentinel-password",
    }
    assert fake_sentinel.master_name == "mymaster"
    assert fake_sentinel.master_kwargs["username"] == "frontis_redis_rw"
    assert fake_sentinel.master_kwargs["password"] == "redis-password"

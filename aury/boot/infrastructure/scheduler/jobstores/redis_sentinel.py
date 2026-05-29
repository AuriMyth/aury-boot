"""Redis Sentinel JobStore for APScheduler."""

from __future__ import annotations

from datetime import UTC, datetime
import pickle
from typing import TYPE_CHECKING, Any

from apscheduler.job import Job
from apscheduler.jobstores.base import BaseJobStore, ConflictingIdError, JobLookupError
from apscheduler.util import datetime_to_utc_timestamp, utc_timestamp_to_datetime

from aury.boot.infrastructure.redis_sentinel import parse_sentinel_nodes

try:
    from redis.sentinel import Sentinel
except ImportError as exc:
    raise ImportError("RedisSentinelJobStore requires redis installed: pip install redis") from exc

if TYPE_CHECKING:
    from apscheduler.schedulers.base import BaseScheduler


class RedisSentinelJobStore(BaseJobStore):
    """APScheduler JobStore backed by the Redis Sentinel master node.

    APScheduler job stores are synchronous even when used by AsyncIOScheduler,
    so this store intentionally uses redis-py's synchronous Sentinel client.
    """

    def __init__(
        self,
        *,
        sentinels: list[str] | list[tuple[str, int]],
        master_name: str = "mymaster",
        redis_username: str | None = None,
        redis_password: str | None = None,
        sentinel_username: str | None = None,
        sentinel_password: str | None = None,
        db: int = 0,
        prefix: str = "",
        socket_timeout: float = 5.0,
        max_connections: int = 200,
        jobs_key: str | None = None,
        run_times_key: str | None = None,
        pickle_protocol: int = pickle.HIGHEST_PROTOCOL,
        **connect_args: Any,
    ) -> None:
        super().__init__()
        normalized_sentinels = _normalize_sentinels(sentinels)
        if not normalized_sentinels:
            raise ValueError("sentinels must not be empty")
        if not str(master_name or "").strip():
            raise ValueError("master_name must not be empty")

        key_prefix = str(prefix or "")
        self.jobs_key = jobs_key or f"{key_prefix}apscheduler.jobs"
        self.run_times_key = run_times_key or f"{key_prefix}apscheduler.run_times"
        if not self.jobs_key:
            raise ValueError('The "jobs_key" parameter must not be empty')
        if not self.run_times_key:
            raise ValueError('The "run_times_key" parameter must not be empty')

        self.pickle_protocol = pickle_protocol
        sentinel_kwargs: dict[str, Any] = {}
        if sentinel_username:
            sentinel_kwargs["username"] = sentinel_username
        if sentinel_password:
            sentinel_kwargs["password"] = sentinel_password
        self._sentinel = Sentinel(
            normalized_sentinels,
            sentinel_kwargs=sentinel_kwargs or None,
            socket_timeout=socket_timeout,
            **connect_args,
        )
        redis_kwargs: dict[str, Any] = {
            "db": db,
            "socket_timeout": socket_timeout,
            "max_connections": max_connections,
        }
        if redis_username:
            redis_kwargs["username"] = redis_username
        if redis_password:
            redis_kwargs["password"] = redis_password
        self.redis = self._sentinel.master_for(master_name, **redis_kwargs)

    def lookup_job(self, job_id: str) -> Job | None:
        job_state = self.redis.hget(self.jobs_key, job_id)
        return self._reconstitute_job(job_state) if job_state else None

    def get_due_jobs(self, now: datetime) -> list[Job]:
        timestamp = datetime_to_utc_timestamp(now)
        job_ids = self.redis.zrangebyscore(self.run_times_key, 0, timestamp)
        if job_ids:
            job_states = self.redis.hmget(self.jobs_key, *job_ids)
            return self._reconstitute_jobs(zip(job_ids, job_states, strict=False))
        return []

    def get_next_run_time(self) -> datetime | None:
        next_run_time = self.redis.zrange(self.run_times_key, 0, 0, withscores=True)
        if next_run_time:
            return utc_timestamp_to_datetime(next_run_time[0][1])
        return None

    def get_all_jobs(self) -> list[Job]:
        job_states = self.redis.hgetall(self.jobs_key)
        jobs = self._reconstitute_jobs(job_states.items())
        paused_sort_key = datetime(9999, 12, 31, tzinfo=UTC)
        return sorted(jobs, key=lambda job: job.next_run_time or paused_sort_key)

    def add_job(self, job: Job) -> None:
        if self.redis.hexists(self.jobs_key, job.id):
            raise ConflictingIdError(job.id)
        with self.redis.pipeline() as pipe:
            pipe.hset(self.jobs_key, job.id, pickle.dumps(job.__getstate__(), self.pickle_protocol))
            if job.next_run_time:
                pipe.zadd(self.run_times_key, {job.id: datetime_to_utc_timestamp(job.next_run_time)})
            pipe.execute()

    def update_job(self, job: Job) -> None:
        if not self.redis.hexists(self.jobs_key, job.id):
            raise JobLookupError(job.id)
        with self.redis.pipeline() as pipe:
            pipe.hset(self.jobs_key, job.id, pickle.dumps(job.__getstate__(), self.pickle_protocol))
            if job.next_run_time:
                pipe.zadd(self.run_times_key, {job.id: datetime_to_utc_timestamp(job.next_run_time)})
            else:
                pipe.zrem(self.run_times_key, job.id)
            pipe.execute()

    def remove_job(self, job_id: str) -> None:
        if not self.redis.hexists(self.jobs_key, job_id):
            raise JobLookupError(job_id)
        with self.redis.pipeline() as pipe:
            pipe.hdel(self.jobs_key, job_id)
            pipe.zrem(self.run_times_key, job_id)
            pipe.execute()

    def remove_all_jobs(self) -> None:
        with self.redis.pipeline() as pipe:
            pipe.delete(self.jobs_key)
            pipe.delete(self.run_times_key)
            pipe.execute()

    def shutdown(self) -> None:
        self.redis.close()

    def _reconstitute_job(self, job_state: bytes) -> Job:
        state = pickle.loads(job_state)
        job = Job.__new__(Job)
        job.__setstate__(state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    def _reconstitute_jobs(self, job_states: Any) -> list[Job]:
        jobs = []
        failed_job_ids = []
        for job_id, job_state in job_states:
            try:
                jobs.append(self._reconstitute_job(job_state))
            except Exception:
                self._logger.exception('Unable to restore job "%s" -- removing it', job_id)
                failed_job_ids.append(job_id)
        if failed_job_ids:
            with self.redis.pipeline() as pipe:
                pipe.hdel(self.jobs_key, *failed_job_ids)
                pipe.zrem(self.run_times_key, *failed_job_ids)
                pipe.execute()
        return jobs

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


def _normalize_sentinels(sentinels: list[str] | list[tuple[str, int]]) -> list[tuple[str, int]]:
    if not sentinels:
        return []
    first = sentinels[0]
    if isinstance(first, str):
        return parse_sentinel_nodes(sentinels)  # type: ignore[arg-type]
    return [(str(host), int(port)) for host, port in sentinels]  # type: ignore[misc]

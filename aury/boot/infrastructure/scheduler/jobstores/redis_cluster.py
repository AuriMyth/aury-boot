"""Redis Cluster JobStore for APScheduler.

支持 Redis Cluster 的任务存储，使用 redis-cluster:// URL 格式。

使用示例:
    from aury.boot.infrastructure.scheduler.jobstores import RedisClusterJobStore
    
    # 使用 URL（推荐）
    jobstore = RedisClusterJobStore(
        url="redis-cluster://password@redis-cluster.example.com:6379"
    )
    
    # 使用参数
    jobstore = RedisClusterJobStore(
        host="redis-cluster.example.com",
        port=6379,
        password="password",
    )
    
    scheduler = SchedulerManager.get_instance(
        jobstores={"default": jobstore}
    )
"""

from __future__ import annotations

import pickle
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from apscheduler.job import Job
from apscheduler.jobstores.base import BaseJobStore, ConflictingIdError, JobLookupError
from apscheduler.util import datetime_to_utc_timestamp, utc_timestamp_to_datetime

try:
    from redis.cluster import RedisCluster
except ImportError as exc:
    raise ImportError(
        "RedisClusterJobStore requires redis[cluster] installed: "
        "pip install 'redis[cluster]'"
    ) from exc

if TYPE_CHECKING:
    from apscheduler.schedulers.base import BaseScheduler


class RedisClusterJobStore(BaseJobStore):
    """Redis Cluster 任务存储。
    
    与 APScheduler 的 RedisJobStore 兼容，但使用 RedisCluster 客户端。
    使用 hash tag 确保 jobs_key 和 run_times_key 在同一个 slot。
    
    Args:
        url: Redis Cluster URL，格式: redis-cluster://[password@]host:port
             或标准格式: redis://[password@]host:port（会自动识别为集群）
        jobs_key: 存储任务的 key，默认 "{apscheduler}.jobs"
        run_times_key: 存储运行时间的 key，默认 "{apscheduler}.run_times"
        pickle_protocol: pickle 序列化协议版本
        **connect_args: 传递给 RedisCluster 的其他参数
    """
    
    def __init__(
        self,
        url: str | None = None,
        jobs_key: str = "{apscheduler}.jobs",
        run_times_key: str = "{apscheduler}.run_times",
        pickle_protocol: int = pickle.HIGHEST_PROTOCOL,
        **connect_args: Any,
    ) -> None:
        super().__init__()
        
        if not jobs_key:
            raise ValueError('The "jobs_key" parameter must not be empty')
        if not run_times_key:
            raise ValueError('The "run_times_key" parameter must not be empty')
        
        self.pickle_protocol = pickle_protocol
        self.jobs_key = jobs_key
        self.run_times_key = run_times_key
        
        if url:
            # 解析 URL
            self.redis = self._create_client_from_url(url, **connect_args)
        else:
            # 使用参数直接连接
            self.redis = RedisCluster(**connect_args)
    
    def _create_client_from_url(self, url: str, **kwargs: Any) -> RedisCluster:
        """从 URL 创建 RedisCluster 客户端。
        
        支持格式:
        - redis-cluster://password@host:port （密码在用户名位置）
        - redis-cluster://:password@host:port （标准格式）
        - redis-cluster://username:password@host:port （ACL 模式）
        """
        # 统一转换为 redis:// 格式供解析
        if url.startswith("redis-cluster://"):
            url = url.replace("redis-cluster://", "redis://", 1)
        
        parsed = urlparse(url)
        
        # 提取连接参数
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        username = parsed.username
        password = parsed.password
        
        # 处理 password@host 格式（密码在用户名位置）
        if username and not password:
            password = username
            username = None
        
        # 解析查询参数
        query_params = parse_qs(parsed.query)
        
        # 构建连接参数
        connect_kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            **kwargs,
        }
        
        if username:
            connect_kwargs["username"] = username
        if password:
            connect_kwargs["password"] = password
        
        # 处理常见查询参数
        if "decode_responses" in query_params:
            connect_kwargs["decode_responses"] = query_params["decode_responses"][0].lower() == "true"
        
        return RedisCluster(**connect_kwargs)
    
    def lookup_job(self, job_id: str) -> Job | None:
        """查找任务。"""
        job_state = self.redis.hget(self.jobs_key, job_id)
        return self._reconstitute_job(job_state) if job_state else None
    
    def get_due_jobs(self, now: datetime) -> list[Job]:
        """获取到期的任务。"""
        timestamp = datetime_to_utc_timestamp(now)
        job_ids = self.redis.zrangebyscore(self.run_times_key, 0, timestamp)
        if job_ids:
            job_states = self.redis.hmget(self.jobs_key, *job_ids)
            return self._reconstitute_jobs(zip(job_ids, job_states))
        return []
    
    def get_next_run_time(self) -> datetime | None:
        """获取下次运行时间。"""
        next_run_time = self.redis.zrange(self.run_times_key, 0, 0, withscores=True)
        if next_run_time:
            return utc_timestamp_to_datetime(next_run_time[0][1])
        return None
    
    def get_all_jobs(self) -> list[Job]:
        """获取所有任务。"""
        job_states = self.redis.hgetall(self.jobs_key)
        jobs = self._reconstitute_jobs(job_states.items())
        paused_sort_key = datetime(9999, 12, 31, tzinfo=timezone.utc)
        return sorted(jobs, key=lambda job: job.next_run_time or paused_sort_key)
    
    def add_job(self, job: Job) -> None:
        """添加任务。"""
        if self.redis.hexists(self.jobs_key, job.id):
            raise ConflictingIdError(job.id)
        
        with self.redis.pipeline() as pipe:
            pipe.hset(
                self.jobs_key,
                job.id,
                pickle.dumps(job.__getstate__(), self.pickle_protocol),
            )
            if job.next_run_time:
                pipe.zadd(
                    self.run_times_key,
                    {job.id: datetime_to_utc_timestamp(job.next_run_time)},
                )
            pipe.execute()
    
    def update_job(self, job: Job) -> None:
        """更新任务。"""
        if not self.redis.hexists(self.jobs_key, job.id):
            raise JobLookupError(job.id)
        
        with self.redis.pipeline() as pipe:
            pipe.hset(
                self.jobs_key,
                job.id,
                pickle.dumps(job.__getstate__(), self.pickle_protocol),
            )
            if job.next_run_time:
                pipe.zadd(
                    self.run_times_key,
                    {job.id: datetime_to_utc_timestamp(job.next_run_time)},
                )
            else:
                pipe.zrem(self.run_times_key, job.id)
            pipe.execute()
    
    def remove_job(self, job_id: str) -> None:
        """移除任务。"""
        if not self.redis.hexists(self.jobs_key, job_id):
            raise JobLookupError(job_id)
        
        with self.redis.pipeline() as pipe:
            pipe.hdel(self.jobs_key, job_id)
            pipe.zrem(self.run_times_key, job_id)
            pipe.execute()
    
    def remove_all_jobs(self) -> None:
        """移除所有任务。"""
        with self.redis.pipeline() as pipe:
            pipe.delete(self.jobs_key)
            pipe.delete(self.run_times_key)
            pipe.execute()
    
    def shutdown(self) -> None:
        """关闭连接。"""
        self.redis.close()
    
    def _reconstitute_job(self, job_state: bytes) -> Job:
        """重建任务对象。"""
        state = pickle.loads(job_state)
        job = Job.__new__(Job)
        job.__setstate__(state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job
    
    def _reconstitute_jobs(self, job_states: Any) -> list[Job]:
        """重建多个任务对象。"""
        jobs = []
        failed_job_ids = []
        
        for job_id, job_state in job_states:
            try:
                jobs.append(self._reconstitute_job(job_state))
            except Exception:
                self._logger.exception(
                    'Unable to restore job "%s" -- removing it', job_id
                )
                failed_job_ids.append(job_id)
        
        # 移除无法恢复的任务
        if failed_job_ids:
            with self.redis.pipeline() as pipe:
                pipe.hdel(self.jobs_key, *failed_job_ids)
                pipe.zrem(self.run_times_key, *failed_job_ids)
                pipe.execute()
        
        return jobs
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

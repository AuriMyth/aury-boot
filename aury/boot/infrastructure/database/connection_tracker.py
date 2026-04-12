"""数据库连接追踪器 - 对标 HikariCP leakDetectionThreshold。

用于检测连接泄漏，追踪连接的获取来源代码位置。

功能：
    - 连接 checkout/checkin 事件追踪
    - 记录获取连接时的调用栈
    - 检测持有时间过长的连接
    - 支持多种数据库的系统表查询（PostgreSQL、MySQL、SQLite）

配置项（环境变量前缀 DATABASE__TRACKER__）：
    DATABASE__TRACKER__ENABLED: 是否启用追踪（默认 False，生产环境建议关闭）
    DATABASE__TRACKER__LEAK_DETECTION_THRESHOLD: 泄漏检测阈值（秒），默认 300
    DATABASE__TRACKER__MAX_IDLE_CONNECTIONS: idle 连接数报警阈值
    DATABASE__TRACKER__MAX_TOTAL_CONNECTIONS: 总连接数报警阈值
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
import threading
import time
import traceback
from typing import TYPE_CHECKING, Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.common.logging import logger

if TYPE_CHECKING:
    from sqlalchemy.pool import Pool


@dataclass
class ConnectionTrace:
    """连接追踪信息。"""

    conn_id: int  # 连接标识（id(dbapi_conn)）
    checkout_time: float
    stack_trace: str  # 完整调用栈
    code_location: str  # 简化的代码位置
    checkout_task: str | None = None  # asyncio task name


@dataclass
class PoolWaitEvent:
    """连接池等待事件。"""

    database_name: str
    wait_ms: float
    timestamp: float
    code_location: str
    task_name: str | None = None


class ConnectionTracker:
    """
    连接追踪器单例。

    通过 SQLAlchemy pool 事件追踪每个连接的获取来源。
    类似 HikariCP 的 leakDetectionThreshold 功能。
    """

    _instance: ConnectionTracker | None = None

    def __init__(self, enabled: bool = False, app_package: str = "app") -> None:
        """
        初始化连接追踪器。

        Args:
            enabled: 是否启用追踪
            app_package: 应用包名，用于过滤调用栈（只保留应用代码）
        """
        # conn_id -> ConnectionTrace
        self._traces: dict[int, ConnectionTrace] = {}
        self._enabled = enabled
        self._app_package = app_package
        self._lock = threading.Lock()
        self._pool_wait_samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=2048))
        self._pool_wait_events: dict[str, list[PoolWaitEvent]] = defaultdict(list)
        self._pool_wait_warn_threshold_ms = 50.0
        self._pool_wait_max_events = 50

    @classmethod
    def get_instance(cls) -> ConnectionTracker:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize(cls, enabled: bool = False, app_package: str = "app") -> ConnectionTracker:
        """初始化并返回实例。"""
        cls._instance = cls(enabled=enabled, app_package=app_package)
        return cls._instance

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def pool_wait_warn_threshold_ms(self) -> float:
        return self._pool_wait_warn_threshold_ms

    def _extract_code_location(self, stack: str) -> str:
        """从调用栈提取关键代码位置（过滤掉框架代码）。"""
        lines = stack.strip().split("\n")
        relevant_lines = []
        app_pkg = f"/{self._app_package}/"

        for i, line in enumerate(lines):
            # 只保留应用目录下的代码
            if (
                app_pkg in line
                and "connection_tracker" not in line
                and line.strip().startswith("File")
            ):
                relevant_lines.append(line.strip())
                # 也获取下一行（代码内容）
                if i + 1 < len(lines):
                    relevant_lines.append(lines[i + 1].strip())

        return "\n".join(relevant_lines[-6:]) if relevant_lines else "Unknown"

    def on_checkout(self, dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
        """连接被取出时记录。"""
        if not self._enabled:
            return

        try:
            conn_id = id(dbapi_conn)

            # 获取调用栈
            stack = "".join(traceback.format_stack())
            code_location = self._extract_code_location(stack)

            # 获取当前 asyncio task 名称
            task_name = None
            try:
                task = asyncio.current_task()
                if task:
                    task_name = task.get_name()
            except RuntimeError:
                pass

            self._traces[conn_id] = ConnectionTrace(
                conn_id=conn_id,
                checkout_time=time.time(),
                stack_trace=stack,
                code_location=code_location,
                checkout_task=task_name,
            )
        except Exception as e:
            logger.warning(f"Failed to track connection checkout: {e}")

    def on_checkin(self, dbapi_conn: Any, connection_record: Any) -> None:
        """连接归还时清理。"""
        if not self._enabled:
            return

        try:
            conn_id = id(dbapi_conn)
            self._traces.pop(conn_id, None)
        except Exception:
            pass

    def get_trace(self, conn_id: int) -> ConnectionTrace | None:
        """获取指定连接的追踪信息。"""
        return self._traces.get(conn_id)

    def get_all_traces(self) -> dict[int, ConnectionTrace]:
        """获取所有追踪信息。"""
        return dict(self._traces)

    def record_pool_wait(
        self,
        *,
        database_name: str,
        wait_ms: float,
        stack_trace: str | None = None,
    ) -> None:
        """记录一次连接池等待时间。"""
        if not self._enabled:
            return

        sample = round(wait_ms, 3)
        with self._lock:
            self._pool_wait_samples[database_name].append(sample)

        if sample < self._pool_wait_warn_threshold_ms:
            return

        task_name = None
        try:
            task = asyncio.current_task()
            if task:
                task_name = task.get_name()
        except RuntimeError:
            pass

        event = PoolWaitEvent(
            database_name=database_name,
            wait_ms=sample,
            timestamp=time.time(),
            code_location=self._extract_code_location(stack_trace or ""),
            task_name=task_name,
        )
        with self._lock:
            events = self._pool_wait_events[database_name]
            events.append(event)
            if len(events) > self._pool_wait_max_events:
                del events[0]

    def _percentile(self, values: list[float], percentile: float) -> float | None:
        """计算百分位。"""
        if not values:
            return None
        ordered = sorted(values)
        index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
        return round(ordered[index], 3)

    def _build_pool_wait_summary(self, database_name: str, samples: list[float]) -> dict[str, Any]:
        """构建单库连接池等待汇总。"""
        events = self._pool_wait_events.get(database_name, [])
        if not samples:
            return {
                "database_name": database_name,
                "sample_count": 0,
                "min_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "p99_ms": None,
                "max_ms": None,
                "over_10ms": 0,
                "over_50ms": 0,
                "over_100ms": 0,
                "recent_slow_events": [],
            }

        return {
            "database_name": database_name,
            "sample_count": len(samples),
            "min_ms": round(min(samples), 3),
            "p50_ms": self._percentile(samples, 0.50),
            "p95_ms": self._percentile(samples, 0.95),
            "p99_ms": self._percentile(samples, 0.99),
            "max_ms": round(max(samples), 3),
            "over_10ms": sum(1 for item in samples if item >= 10),
            "over_50ms": sum(1 for item in samples if item >= 50),
            "over_100ms": sum(1 for item in samples if item >= 100),
            "recent_slow_events": [
                {
                    "timestamp": round(item.timestamp, 3),
                    "wait_ms": item.wait_ms,
                    "task_name": item.task_name,
                    "code_location": item.code_location,
                }
                for item in events[-10:]
            ],
        }

    def get_pool_wait_stats(self, database_name: str | None = None) -> dict[str, Any]:
        """获取连接池等待统计。"""
        with self._lock:
            samples_by_db = {
                name: list(values)
                for name, values in self._pool_wait_samples.items()
            }

        if database_name is not None:
            return self._build_pool_wait_summary(
                database_name,
                samples_by_db.get(database_name, []),
            )

        return {
            "databases": {
                name: self._build_pool_wait_summary(name, samples)
                for name, samples in sorted(samples_by_db.items())
            }
        }

    def clear_pool_wait_stats(self) -> None:
        """清空连接池等待统计。"""
        with self._lock:
            self._pool_wait_samples.clear()
            self._pool_wait_events.clear()

    def get_long_held_connections(self, threshold_seconds: float = 300) -> list[dict]:
        """
        获取持有时间过长的连接（疑似泄漏）。

        类似 HikariCP 的 leakDetectionThreshold。

        Args:
            threshold_seconds: 持有时间阈值（秒）

        Returns:
            疑似泄漏的连接列表，包含持有时间和代码位置
        """
        now = time.time()
        result = []
        for conn_id, trace in self._traces.items():
            held_seconds = now - trace.checkout_time
            if held_seconds > threshold_seconds:
                result.append(
                    {
                        "conn_id": conn_id,
                        "held_seconds": held_seconds,
                        "code_location": trace.code_location,
                        "task_name": trace.checkout_task,
                        "full_stack": trace.stack_trace,
                    }
                )
        return result


def setup_connection_tracking(
    pool: Pool,
    enabled: bool = False,
    app_package: str = "app",
    database_name: str = "default",
) -> ConnectionTracker:
    """
    设置连接追踪。

    在应用启动时调用，注册 SQLAlchemy pool 事件。

    Args:
        pool: SQLAlchemy 连接池（sync_engine.pool）
        enabled: 是否启用追踪
        app_package: 应用包名

    Returns:
        ConnectionTracker 实例
    """
    tracker = ConnectionTracker.initialize(enabled=enabled, app_package=app_package)

    if not enabled:
        logger.info("Database connection tracking is disabled")
        return tracker

    event.listen(pool, "checkout", tracker.on_checkout)
    event.listen(pool, "checkin", tracker.on_checkin)
    _setup_pool_wait_tracking(pool, tracker, database_name=database_name)

    logger.info("Database connection tracking enabled (like HikariCP leakDetectionThreshold)")
    return tracker


def _setup_pool_wait_tracking(
    pool: Pool,
    tracker: ConnectionTracker,
    *,
    database_name: str = "default",
) -> None:
    """对 QueuePool 的 _do_get 做轻量计时，统计 checkout 等待。"""
    if getattr(pool, "_aury_pool_wait_tracking_enabled", False):
        return

    original_do_get = getattr(pool, "_do_get", None)
    if original_do_get is None:
        return

    def instrumented_do_get(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return original_do_get(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            stack_trace = None
            if elapsed_ms >= tracker.pool_wait_warn_threshold_ms:
                stack_trace = "".join(traceback.format_stack())
            tracker.record_pool_wait(
                database_name=database_name,
                wait_ms=elapsed_ms,
                stack_trace=stack_trace,
            )

    pool._aury_pool_wait_tracking_enabled = True
    pool._aury_pool_wait_tracking_original_do_get = original_do_get
    pool._do_get = instrumented_do_get


# ==================== 多数据库健康检查 ====================


class DbHealthChecker(ABC):
    """数据库健康检查抽象基类。"""

    @abstractmethod
    async def get_connection_stats(self, session: AsyncSession) -> dict:
        """获取连接统计信息。"""
        pass

    @abstractmethod
    async def get_idle_connections(
        self, session: AsyncSession, idle_threshold_seconds: int = 300
    ) -> list[dict]:
        """获取空闲连接列表。"""
        pass

    @abstractmethod
    async def get_connection_by_id(self, session: AsyncSession, conn_id: Any) -> dict | None:
        """根据连接标识获取连接信息。"""
        pass


class PostgreSQLHealthChecker(DbHealthChecker):
    """PostgreSQL 健康检查实现。"""

    async def get_connection_stats(self, session: AsyncSession) -> dict:
        """获取连接统计信息。"""
        sql = text("""
            SELECT state, COUNT(*) AS count
            FROM pg_stat_activity
            WHERE datname = current_database()
            GROUP BY state
        """)
        result = await session.execute(sql)
        stats = {row.state: row.count for row in result.fetchall()}
        return {
            "total": sum(stats.values()),
            "stats": stats,
        }

    async def get_idle_connections(
        self, session: AsyncSession, idle_threshold_seconds: int = 300
    ) -> list[dict]:
        """获取空闲连接列表。"""
        sql = text(f"""
            SELECT
                pid,
                usename,
                application_name,
                state,
                EXTRACT(EPOCH FROM (NOW() - state_change)) AS idle_seconds,
                EXTRACT(EPOCH FROM (NOW() - backend_start)) AS connection_age_seconds,
                LEFT(query, 300) AS last_query,
                client_addr
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND state = 'idle'
              AND NOW() - state_change > INTERVAL '{idle_threshold_seconds} seconds'
            ORDER BY state_change
            LIMIT 30
        """)
        result = await session.execute(sql)
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_connection_by_id(self, session: AsyncSession, conn_id: Any) -> dict | None:
        """根据 PID 获取连接信息。"""
        sql = text("""
            SELECT
                pid,
                usename,
                application_name,
                state,
                query,
                backend_start,
                state_change
            FROM pg_stat_activity
            WHERE pid = :pid
        """)
        result = await session.execute(sql, {"pid": conn_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None


class MySQLHealthChecker(DbHealthChecker):
    """MySQL 健康检查实现。"""

    async def get_connection_stats(self, session: AsyncSession) -> dict:
        """获取连接统计信息。"""
        sql = text("SHOW STATUS LIKE 'Threads_connected'")
        result = await session.execute(sql)
        row = result.fetchone()
        total = int(row[1]) if row else 0

        # 获取各状态统计
        sql = text("""
            SELECT COMMAND AS state, COUNT(*) AS count
            FROM information_schema.PROCESSLIST
            GROUP BY COMMAND
        """)
        result = await session.execute(sql)
        stats = {row.state: row.count for row in result.fetchall()}

        return {
            "total": total,
            "stats": stats,
        }

    async def get_idle_connections(
        self, session: AsyncSession, idle_threshold_seconds: int = 300
    ) -> list[dict]:
        """获取空闲连接列表。"""
        sql = text(f"""
            SELECT
                ID AS pid,
                USER AS usename,
                HOST AS client_addr,
                DB AS database,
                COMMAND AS state,
                TIME AS idle_seconds,
                LEFT(INFO, 300) AS last_query
            FROM information_schema.PROCESSLIST
            WHERE COMMAND = 'Sleep'
              AND TIME > {idle_threshold_seconds}
            ORDER BY TIME DESC
            LIMIT 30
        """)
        result = await session.execute(sql)
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_connection_by_id(self, session: AsyncSession, conn_id: Any) -> dict | None:
        """根据连接 ID 获取连接信息。"""
        sql = text("""
            SELECT
                ID AS pid,
                USER AS usename,
                HOST AS client_addr,
                DB AS database,
                COMMAND AS state,
                TIME AS idle_seconds,
                INFO AS query
            FROM information_schema.PROCESSLIST
            WHERE ID = :conn_id
        """)
        result = await session.execute(sql, {"conn_id": conn_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None


class SQLiteHealthChecker(DbHealthChecker):
    """SQLite 健康检查实现（功能有限）。"""

    async def get_connection_stats(self, session: AsyncSession) -> dict:
        """SQLite 是单文件数据库，连接统计有限。"""
        return {
            "total": 1,
            "stats": {"active": 1},
            "note": "SQLite is a single-file database with limited connection stats",
        }

    async def get_idle_connections(
        self, session: AsyncSession, idle_threshold_seconds: int = 300
    ) -> list[dict]:
        """SQLite 不支持连接级别的空闲检测。"""
        return []

    async def get_connection_by_id(self, session: AsyncSession, conn_id: Any) -> dict | None:
        """SQLite 不支持按 ID 查询连接。"""
        return None


def get_health_checker(database_url: str) -> DbHealthChecker:
    """
    根据数据库 URL 获取对应的健康检查器。

    Args:
        database_url: 数据库连接 URL

    Returns:
        对应数据库类型的健康检查器
    """
    url_lower = database_url.lower()
    if "postgresql" in url_lower or "postgres" in url_lower:
        return PostgreSQLHealthChecker()
    elif "mysql" in url_lower or "mariadb" in url_lower:
        return MySQLHealthChecker()
    elif "sqlite" in url_lower:
        return SQLiteHealthChecker()
    else:
        # 默认使用 PostgreSQL（最常用）
        logger.warning("Unknown database type in URL, using PostgreSQL health checker")
        return PostgreSQLHealthChecker()


__all__ = [
    "ConnectionTrace",
    "ConnectionTracker",
    "DbHealthChecker",
    "MySQLHealthChecker",
    "PostgreSQLHealthChecker",
    "SQLiteHealthChecker",
    "get_health_checker",
    "setup_connection_tracking",
]

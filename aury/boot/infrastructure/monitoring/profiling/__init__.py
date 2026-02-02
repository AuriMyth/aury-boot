"""Profiling 模块。

提供持续性能分析和问题时刻状态快照功能：
- Pyroscope 集成：持续采样生成火焰图
- 事件循环阻塞检测：检测同步代码阻塞协程

使用方式：
    # 通过配置启用
    PROFILING__ENABLED=true
    PROFILING__PYROSCOPE_ENDPOINT=http://pyroscope:4040
    
    # 事件循环阻塞检测
    PROFILING__BLOCKING_DETECTOR_ENABLED=true
    PROFILING__BLOCKING_THRESHOLD_MS=100
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

# Pyroscope 可选依赖
try:
    import pyroscope
    PYROSCOPE_AVAILABLE = True
except ImportError:
    pyroscope = None  # type: ignore[assignment]
    PYROSCOPE_AVAILABLE = False

# psutil 可选依赖（用于进程资源监控）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    PSUTIL_AVAILABLE = False

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# 配置
# =============================================================================


@dataclass
class ProfilingConfig:
    """Profiling 配置。"""
    
    # Pyroscope 配置
    enabled: bool = False
    pyroscope_endpoint: str | None = None
    pyroscope_auth_token: str | None = None
    service_name: str = "aury-service"
    environment: str = "development"
    
    # 事件循环阻塞检测配置
    blocking_detector_enabled: bool = False
    blocking_check_interval_ms: float = 100
    blocking_threshold_ms: float = 100
    blocking_severe_threshold_ms: float = 500
    blocking_alert_enabled: bool = True
    blocking_alert_cooldown_seconds: float = 60
    blocking_max_history: int = 50
    
    # 滑动窗口统计（秒）
    blocking_stats_window_seconds: float = 300  # 5分钟
    
    # 标签
    tags: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Pyroscope 集成
# =============================================================================


class PyroscopeProfiler:
    """Pyroscope 持续 Profiler。
    
    集成 Grafana Pyroscope 实现持续性能分析和火焰图生成。
    """
    
    def __init__(self, config: ProfilingConfig) -> None:
        self._config = config
        self._initialized = False
    
    def start(self) -> bool:
        """启动 Pyroscope profiling。"""
        if self._initialized:
            return True
        
        if not PYROSCOPE_AVAILABLE:
            logger.warning("Pyroscope 未安装，跳过 profiling 初始化 (pip install pyroscope-io)")
            return False
        
        if not self._config.pyroscope_endpoint:
            logger.warning("Pyroscope endpoint 未配置，跳过初始化")
            return False
        
        try:
            pyroscope.configure(
                application_name=self._config.service_name,
                server_address=self._config.pyroscope_endpoint,
                auth_token=self._config.pyroscope_auth_token or "",
                tags=self._config.tags,
            )
            self._initialized = True
            logger.info(
                f"Pyroscope profiling 已启动 | "
                f"endpoint={self._config.pyroscope_endpoint} "
                f"service={self._config.service_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Pyroscope 初始化失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止 Pyroscope profiling。"""
        if not self._initialized:
            return
        
        try:
            if PYROSCOPE_AVAILABLE:
                pyroscope.shutdown()
            self._initialized = False
            logger.info("Pyroscope profiling 已停止")
        except Exception as e:
            logger.warning(f"Pyroscope 关闭失败: {e}")
    
    @property
    def is_running(self) -> bool:
        """是否正在运行。"""
        return self._initialized


# =============================================================================
# 事件循环阻塞检测
# =============================================================================


@dataclass
class BlockingEvent:
    """阻塞事件记录。"""
    
    timestamp: datetime
    blocked_ms: float
    main_thread_stack: list[dict[str, Any]]  # 最佳堆栈（用户代码优先）
    all_sampled_stacks: list[list[dict[str, Any]]] = field(default_factory=list)  # 所有采样堆栈
    process_stats: dict[str, Any] | None = None


class EventLoopBlockingDetector:
    """事件循环阻塞检测器。
    
    原理：后台线程定期向事件循环投递任务，如果任务执行延迟超过阈值，
    说明事件循环被同步代码阻塞。此时自动捕获主线程调用栈和进程状态。
    
    用于排查：
    - 同步 I/O 阻塞协程
    - CPU 密集型代码阻塞事件循环
    - 死锁或长时间锁等待
    """
    
    def __init__(self, config: ProfilingConfig) -> None:
        self._config = config
        self._running = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._blocking_events: list[BlockingEvent] = []
        self._lock = threading.Lock()
        # 滑动窗口统计：记录时间戳 (timestamp, is_block)
        self._check_history: deque[tuple[float, bool]] = deque()
        self._last_alert_time: float = 0
    
    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """启动阻塞检测。"""
        if self._running:
            return
        
        try:
            self._loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("无法获取事件循环，阻塞检测器未启动")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="blocking-detector",
        )
        self._thread.start()
        logger.info(
            f"事件循环阻塞检测已启动 | "
            f"阈值={self._config.blocking_threshold_ms}ms "
            f"严重阈值={self._config.blocking_severe_threshold_ms}ms"
        )
    
    def stop(self) -> None:
        """停止阻塞检测。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        logger.info("事件循环阻塞检测已停止")
    
    def _monitor_loop(self) -> None:
        """后台监控循环。"""
        while self._running and self._loop:
            try:
                start_time = time.perf_counter()
                future = asyncio.run_coroutine_threadsafe(self._ping(), self._loop)
                
                # 在等待期间连续采样堆栈
                sampled_stacks: list[list[dict[str, Any]]] = []
                sample_interval = 0.01  # 10ms 采样一次
                
                try:
                    # 轮询等待，同时采样堆栈
                    timeout = self._config.blocking_threshold_ms * 10 / 1000
                    deadline = time.perf_counter() + timeout
                    
                    while time.perf_counter() < deadline:
                        try:
                            future.result(timeout=sample_interval)
                            break  # 成功返回
                        except TimeoutError:
                            # 还在等待，采样当前堆栈
                            elapsed = (time.perf_counter() - start_time) * 1000
                            if elapsed > self._config.blocking_threshold_ms * 0.5:  # 超过阈值50%开始采样
                                stack = self._capture_main_thread_stack()
                                if stack and (not sampled_stacks or stack != sampled_stacks[-1]):
                                    sampled_stacks.append(stack)
                    else:
                        # 超时
                        elapsed_ms = (time.perf_counter() - start_time) * 1000
                        self._record_blocking(elapsed_ms, sampled_stacks)
                        self._record_check(is_block=True)
                        time.sleep(self._config.blocking_check_interval_ms / 1000)
                        continue
                
                except Exception:
                    pass
                
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                is_blocked = elapsed_ms > self._config.blocking_threshold_ms
                if is_blocked:
                    self._record_blocking(elapsed_ms, sampled_stacks)
                
                # 记录检查历史（滑动窗口）
                self._record_check(is_blocked)
            except Exception:
                pass  # 事件循环可能已关闭
            
            time.sleep(self._config.blocking_check_interval_ms / 1000)
    
    async def _ping(self) -> None:
        """空操作，用于测量事件循环响应时间。"""
        pass
    
    def _record_blocking(
        self,
        blocked_ms: float,
        sampled_stacks: list[list[dict[str, Any]]] | None = None,
    ) -> None:
        """记录阻塞事件。"""
        
        # 优先使用采样的堆栈（阻塞期间捕获的），否则捕获当前堆栈
        if sampled_stacks:
            # 取用户代码最多的堆栈作为主堆栈
            stack = self._merge_sampled_stacks(sampled_stacks)
            # 去重保留所有不同的堆栈
            unique_stacks = self._dedupe_stacks(sampled_stacks)
        else:
            stack = self._capture_main_thread_stack()
            unique_stacks = [stack] if stack else []
        
        # 获取进程状态
        process_stats = self._capture_process_stats()
        
        event = BlockingEvent(
            timestamp=datetime.now(),
            blocked_ms=round(blocked_ms, 2),
            main_thread_stack=stack,
            all_sampled_stacks=unique_stacks,
            process_stats=process_stats,
        )
        
        with self._lock:
            self._blocking_events.append(event)
            if len(self._blocking_events) > self._config.blocking_max_history:
                self._blocking_events.pop(0)
        
        # 输出日志
        self._log_blocking(event)
        
        # 发送告警
        if self._config.blocking_alert_enabled and self._loop:
            self._maybe_send_alert(event)
    
    def _capture_main_thread_stack(self) -> list[dict[str, Any]]:
        """捕获主线程调用栈。"""
        main_thread_id = threading.main_thread().ident
        if not main_thread_id or main_thread_id not in sys._current_frames():
            return []
        
        frame = sys._current_frames()[main_thread_id]
        stack = []
        
        for filename, lineno, name, line in traceback.extract_stack(frame):
            # 只跳过检测器自身和 frozen 内部代码
            if "<frozen" in filename or "monitoring/profiling" in filename:
                continue
            
            stack.append({
                "file": filename,
                "line": lineno,
                "function": name,
                "code": line,
            })
        
        return stack[-20:]  # 保留最近 20 帧
    
    def _is_user_code(self, filename: str) -> bool:
        """判断是否为用户代码（非标准库/非三方库）。"""
        if not filename:
            return False
        is_stdlib = any(p in filename for p in (
            "/lib/python", "/Lib/Python", "/opt/homebrew/Cellar/python",
            "/.pyenv/", "/Python.framework/"
        ))
        is_site_packages = "site-packages" in filename or "dist-packages" in filename
        return not is_stdlib and not is_site_packages
    
    def _score_stack(self, stack: list[dict[str, Any]]) -> int:
        """评分堆栈：用户代码帧越多分数越高。"""
        return sum(1 for f in stack if self._is_user_code(f.get("file", "")))
    
    def _stack_signature(self, stack: list[dict[str, Any]]) -> str:
        """生成堆栈签名用于去重。"""
        return "|".join(f"{f.get('file', '')}:{f.get('line', '')}" for f in stack[-5:])
    
    def _dedupe_stacks(
        self, stacks: list[list[dict[str, Any]]]
    ) -> list[list[dict[str, Any]]]:
        """去重堆栈，保留唯一的堆栈。"""
        seen: set[str] = set()
        unique: list[list[dict[str, Any]]] = []
        for stack in stacks:
            sig = self._stack_signature(stack)
            if sig not in seen:
                seen.add(sig)
                unique.append(stack)
        return unique
    
    def _merge_sampled_stacks(
        self, sampled_stacks: list[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """合并多次采样的堆栈，返回用户代码最多的。"""
        if not sampled_stacks:
            return []
        return max(sampled_stacks, key=self._score_stack)
    
    def _capture_process_stats(self) -> dict[str, Any] | None:
        """捕获当前进程状态。"""
        if not PSUTIL_AVAILABLE:
            return None
        
        try:
            proc = psutil.Process()
            with proc.oneshot():
                return {
                    "cpu_percent": proc.cpu_percent(),
                    "memory_rss_mb": round(proc.memory_info().rss / 1024**2, 2),
                    "num_threads": proc.num_threads(),
                    "num_fds": proc.num_fds() if hasattr(proc, "num_fds") else None,
                }
        except Exception:
            return None
    
    def _format_stack(self, stack: list[dict[str, Any]], limit: int = 5, highlight_user: bool = True) -> str:
        """格式化调用栈为字符串。"""
        lines = []
        for frame in stack[-limit:]:
            if frame.get("code"):
                filename = frame['file']
                is_user = self._is_user_code(filename)
                # 用户代码加前缀标记
                prefix = "→ " if (highlight_user and is_user) else "  "
                lines.append(f"{prefix}{filename}:{frame['line']} in {frame['function']}")
                lines.append(f"    > {frame['code']}")
        return "\n".join(lines)
    
    def _record_check(self, is_block: bool) -> None:
        """记录一次检查到滑动窗口。"""
        now = time.time()
        with self._lock:
            self._check_history.append((now, is_block))
            # 清理过期数据
            cutoff = now - self._config.blocking_stats_window_seconds
            while self._check_history and self._check_history[0][0] < cutoff:
                self._check_history.popleft()
    
    def _get_window_stats(self) -> tuple[int, int]:
        """获取时间窗口内的统计。
        
        Returns:
            (total_checks, total_blocks)
        """
        now = time.time()
        cutoff = now - self._config.blocking_stats_window_seconds
        total_checks = 0
        total_blocks = 0
        
        with self._lock:
            for ts, is_block in self._check_history:
                if ts >= cutoff:
                    total_checks += 1
                    if is_block:
                        total_blocks += 1
        
        return total_checks, total_blocks
    
    def _log_blocking(self, event: BlockingEvent) -> None:
        """输出阻塞日志。"""
        is_severe = event.blocked_ms >= self._config.blocking_severe_threshold_ms
        log_fn = logger.error if is_severe else logger.warning
        
        # 获取时间窗口统计
        total_checks, total_blocks = self._get_window_stats()
        window_minutes = int(self._config.blocking_stats_window_seconds / 60)
        
        # 格式化进程状态
        stats_str = ""
        if event.process_stats:
            s = event.process_stats
            stats_str = f" | CPU={s.get('cpu_percent', 'N/A')}% RSS={s.get('memory_rss_mb', 'N/A')}MB threads={s.get('num_threads', 'N/A')}"
        
        # 检查是否有用户代码
        has_user_code = self._score_stack(event.main_thread_stack) > 0
        
        # 构建堆栈信息
        stack_lines = []
        
        if has_user_code:
            # 有用户代码，显示主堆栈
            stack_lines.append("调用栈 (→ 标记用户代码):")
            stack_lines.append(self._format_stack(event.main_thread_stack, limit=8))
        else:
            # 没有用户代码，可能是框架内部阻塞
            stack_lines.append("调用栈 (无用户代码，可能是三方库/框架内部阻塞):")
            stack_lines.append(self._format_stack(event.main_thread_stack, limit=5, highlight_user=False))
            
            # 显示所有不同的采样堆栈
            if len(event.all_sampled_stacks) > 1:
                stack_lines.append(f"\n共采样到 {len(event.all_sampled_stacks)} 个不同堆栈:")
                for i, stack in enumerate(event.all_sampled_stacks[:3], 1):  # 最多显示3个
                    if stack != event.main_thread_stack:
                        stack_lines.append(f"--- 采样 #{i} ---")
                        stack_lines.append(self._format_stack(stack, limit=3, highlight_user=False))
        
        log_fn(
            f"事件循环阻塞{'（严重）' if is_severe else ''}: {event.blocked_ms:.0f}ms "
            f"(阈值={self._config.blocking_threshold_ms}ms, "
            f"近{window_minutes}分钟={total_blocks}次, "
            f"阻塞率={total_blocks / max(total_checks, 1) * 100:.2f}%){stats_str}\n"
            + "\n".join(stack_lines)
        )
    
    def _maybe_send_alert(self, event: BlockingEvent) -> None:
        """发送告警（带冷却）。"""
        now = time.time()
        if now - self._last_alert_time < self._config.blocking_alert_cooldown_seconds:
            return
        
        self._last_alert_time = now
        asyncio.run_coroutine_threadsafe(self._send_alert(event), self._loop)
    
    async def _send_alert(self, event: BlockingEvent) -> None:
        """发送告警。"""
        try:
            from aury.boot.infrastructure.monitoring.alerting import (
                AlertEventType,
                AlertSeverity,
                emit_alert,
            )
            
            is_severe = event.blocked_ms >= self._config.blocking_severe_threshold_ms
            severity = AlertSeverity.CRITICAL if is_severe else AlertSeverity.WARNING
            
            # 获取时间窗口统计
            total_checks, total_blocks = self._get_window_stats()
            window_minutes = int(self._config.blocking_stats_window_seconds / 60)
            
            await emit_alert(
                AlertEventType.CUSTOM,
                f"事件循环阻塞{'（严重）' if is_severe else ''}: {event.blocked_ms:.0f}ms",
                severity=severity,
                source="blocking_detector",
                blocked_ms=event.blocked_ms,
                threshold_ms=self._config.blocking_threshold_ms,
                window_minutes=window_minutes,
                total_blocks=total_blocks,
                block_rate=f"{total_blocks / max(total_checks, 1) * 100:.2f}%",
                stacktrace=self._format_stack(event.main_thread_stack),
                process_stats=event.process_stats,
            )
        except Exception as e:
            logger.debug(f"发送阻塞告警失败: {e}")
    
    def get_status(self) -> dict[str, Any]:
        """获取检测状态和历史。"""
        total_checks, total_blocks = self._get_window_stats()
        window_minutes = int(self._config.blocking_stats_window_seconds / 60)
        
        with self._lock:
            events = [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "blocked_ms": e.blocked_ms,
                    "stack": e.main_thread_stack,
                    "process_stats": e.process_stats,
                }
                for e in self._blocking_events
            ]
        
        return {
            "running": self._running,
            "config": {
                "check_interval_ms": self._config.blocking_check_interval_ms,
                "threshold_ms": self._config.blocking_threshold_ms,
                "severe_threshold_ms": self._config.blocking_severe_threshold_ms,
                "alert_enabled": self._config.blocking_alert_enabled,
                "stats_window_seconds": self._config.blocking_stats_window_seconds,
            },
            "stats": {
                "window_minutes": window_minutes,
                "total_checks": total_checks,
                "total_blocks": total_blocks,
                "block_rate_percent": round(
                    total_blocks / max(total_checks, 1) * 100, 2
                ),
            },
            "recent_events": events,
        }
    
    def clear_history(self) -> None:
        """清空阻塞历史。"""
        with self._lock:
            self._blocking_events.clear()
            self._check_history.clear()
    
    @property
    def is_running(self) -> bool:
        """是否正在运行。"""
        return self._running


# =============================================================================
# 统一管理器
# =============================================================================


class ProfilingManager:
    """Profiling 统一管理器。
    
    管理 Pyroscope 和阻塞检测器的生命周期。
    """
    
    _instance: "ProfilingManager | None" = None
    
    def __init__(self) -> None:
        self._config: ProfilingConfig | None = None
        self._pyroscope: PyroscopeProfiler | None = None
        self._blocking_detector: EventLoopBlockingDetector | None = None
    
    @classmethod
    def get_instance(cls) -> "ProfilingManager":
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def configure(self, config: ProfilingConfig) -> None:
        """配置管理器。"""
        self._config = config
        self._pyroscope = PyroscopeProfiler(config)
        self._blocking_detector = EventLoopBlockingDetector(config)
    
    async def start(self) -> None:
        """启动所有 profiling 组件。"""
        if not self._config:
            logger.warning("ProfilingManager 未配置")
            return
        
        # 启动 Pyroscope
        if self._config.enabled and self._pyroscope:
            self._pyroscope.start()
        
        # 启动阻塞检测器
        if self._config.blocking_detector_enabled and self._blocking_detector:
            self._blocking_detector.start()
    
    async def stop(self) -> None:
        """停止所有 profiling 组件。"""
        if self._pyroscope:
            self._pyroscope.stop()
        
        if self._blocking_detector:
            self._blocking_detector.stop()
    
    @property
    def pyroscope(self) -> PyroscopeProfiler | None:
        """获取 Pyroscope profiler。"""
        return self._pyroscope
    
    @property
    def blocking_detector(self) -> EventLoopBlockingDetector | None:
        """获取阻塞检测器。"""
        return self._blocking_detector
    
    def get_status(self) -> dict[str, Any]:
        """获取所有组件状态。"""
        return {
            "pyroscope": {
                "available": PYROSCOPE_AVAILABLE,
                "running": self._pyroscope.is_running if self._pyroscope else False,
            },
            "blocking_detector": (
                self._blocking_detector.get_status()
                if self._blocking_detector
                else {"running": False}
            ),
        }


# 便捷访问
def get_profiling_manager() -> ProfilingManager:
    """获取 ProfilingManager 实例。"""
    return ProfilingManager.get_instance()


__all__ = [
    "BlockingEvent",
    "EventLoopBlockingDetector",
    "ProfilingConfig",
    "ProfilingManager",
    "PyroscopeProfiler",
    "get_profiling_manager",
    "PSUTIL_AVAILABLE",
    "PYROSCOPE_AVAILABLE",
]

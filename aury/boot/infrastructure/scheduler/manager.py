"""任务调度器管理器 - 命名多实例支持。

提供：
- 统一的调度器管理
- 任务注册和启动
- 生命周期管理
- 自动设置日志上下文（调度器任务日志自动写入 scheduler_xxx.log）
- 支持多个命名实例
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger, set_service_context

# 延迟导入 apscheduler（可选依赖）
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    # 创建占位符类型，避免类型检查错误
    if TYPE_CHECKING:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    else:
        AsyncIOScheduler = None
        CronTrigger = None
        IntervalTrigger = None


class SchedulerManager:
    """调度器管理器（命名多实例）。
    
    职责：
    1. 管理调度器实例
    2. 注册任务
    3. 生命周期管理
    4. 支持多个命名实例，如不同业务线的调度器
    
    使用示例:
        # 默认实例
        scheduler = SchedulerManager.get_instance()
        await scheduler.initialize()
        
        # 命名实例
        report_scheduler = SchedulerManager.get_instance("report")
        cleanup_scheduler = SchedulerManager.get_instance("cleanup")
        
        # 注册任务
        scheduler.add_job(
            func=my_task,
            trigger="interval",
            seconds=60
        )
        
        # 启动调度器
        scheduler.start()
    """
    
    _instances: dict[str, SchedulerManager] = {}
    
    def __init__(self, name: str = "default") -> None:
        """初始化调度器管理器。
        
        Args:
            name: 实例名称
        """
        self.name = name
        self._scheduler: AsyncIOScheduler | None = None
        self._initialized: bool = False
        self._pending_jobs: list[dict[str, Any]] = []  # 待注册的任务（装饰器收集）
        self._started: bool = False  # 调度器是否已启动
    
    @classmethod
    def get_instance(cls, name: str = "default") -> SchedulerManager:
        """获取指定名称的实例。
        
        首次获取时会同步初始化调度器实例，使装饰器可以在模块导入时使用。
        
        Args:
            name: 实例名称，默认为 "default"
            
        Returns:
            SchedulerManager: 调度器管理器实例
        """
        if name not in cls._instances:
            if not _APSCHEDULER_AVAILABLE:
                raise ImportError(
                    "apscheduler 未安装。请安装可选依赖: pip install 'aury-boot[scheduler-apscheduler]'"
                )
            instance = cls(name)
            instance._scheduler = AsyncIOScheduler()
            instance._initialized = True
            cls._instances[name] = instance
            logger.debug(f"调度器实例已创建: {name}")
        return cls._instances[name]
    
    @classmethod
    def reset_instance(cls, name: str | None = None) -> None:
        """重置实例（仅用于测试）。
        
        Args:
            name: 要重置的实例名称。如果为 None，则重置所有实例。
            
        注意：调用此方法前应先调用 shutdown() 释放资源。
        """
        if name is None:
            cls._instances.clear()
        elif name in cls._instances:
            del cls._instances[name]
    
    async def initialize(self) -> SchedulerManager:
        """初始化调度器（链式调用）。
        
        调度器现在在 get_instance() 时同步初始化，此方法保留以保持后向兼容。
        
        Returns:
            self: 支持链式调用
        """
        if not self._initialized:
            # 如果还未初始化（理论上不会发生），进行初始化
            if not _APSCHEDULER_AVAILABLE:
                raise ImportError(
                    "apscheduler 未安装。请安装可选依赖: pip install 'aury-boot[scheduler-apscheduler]'"
                )
            self._scheduler = AsyncIOScheduler()
            self._initialized = True
        logger.debug("调度器已就绪")
        return self
    
    @property
    def scheduler(self) -> AsyncIOScheduler:
        """获取调度器实例。"""
        if self._scheduler is None:
            raise RuntimeError("调度器未初始化，请先调用 initialize()")
        return self._scheduler
    
    def add_job(
        self,
        func: Callable,
        trigger: str = "interval",
        *,
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        days: int | None = None,
        cron: str | None = None,
        id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """添加任务。
        
        Args:
            func: 任务函数
            trigger: 触发器类型（interval/cron）
            seconds: 间隔秒数
            minutes: 间隔分钟数
            hours: 间隔小时数
            days: 间隔天数
            cron: Cron表达式（如 "0 0 * * *"）
            id: 任务ID
            **kwargs: 其他参数
        """
        if not self._initialized:
            raise RuntimeError("调度器未初始化")
        
        # 使用函数式编程构建触发器
        def build_interval_trigger() -> IntervalTrigger:
            """构建间隔触发器。"""
            if seconds:
                return IntervalTrigger(seconds=seconds)
            if minutes:
                return IntervalTrigger(minutes=minutes)
            if hours:
                return IntervalTrigger(hours=hours)
            if days:
                return IntervalTrigger(days=days)
            raise ValueError("必须指定间隔时间")
        
        def build_cron_trigger() -> CronTrigger:
            """构建Cron触发器。"""
            if not cron:
                raise ValueError("Cron触发器必须提供cron表达式")
            return CronTrigger.from_crontab(cron)
        
        trigger_builders: dict[str, Callable[[], Any]] = {
            "interval": build_interval_trigger,
            "cron": build_cron_trigger,
        }
        
        builder = trigger_builders.get(trigger)
        if builder is None:
            available = ", ".join(trigger_builders.keys())
            raise ValueError(
                f"不支持的触发器类型: {trigger}。可用类型: {available}"
            )
        
        trigger_obj = builder()
        
        # 包装任务函数，自动设置日志上下文
        wrapped_func = self._wrap_with_context(func)

        # 添加任务
        job_id = id or f"{func.__module__}.{func.__name__}"
        self._scheduler.add_job(
            func=wrapped_func,
            trigger=trigger_obj,
            id=job_id,
            **kwargs,
        )
        
        logger.info(f"任务已注册: {job_id} | 触发器: {trigger}")
    
    def _wrap_with_context(self, func: Callable) -> Callable:
        """包装任务函数，自动设置 scheduler 日志上下文。"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            set_service_context("scheduler")
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            set_service_context("scheduler")
            return func(*args, **kwargs)

        # 根据函数类型选择包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    def remove_job(self, job_id: str) -> None:
        """移除任务。
        
        Args:
            job_id: 任务ID
        """
        if self._scheduler:
            self._scheduler.remove_job(job_id)
            logger.info(f"任务已移除: {job_id}")
    
    def get_jobs(self) -> list:
        """获取所有任务。"""
        if self._scheduler:
            return self._scheduler.get_jobs()
        return []
    
    def get_job(self, job_id: str) -> Any | None:
        """获取单个任务。
        
        Args:
            job_id: 任务ID
            
        Returns:
            任务对象，不存在则返回 None
        """
        if self._scheduler:
            return self._scheduler.get_job(job_id)
        return None
    
    def modify_job(
        self,
        job_id: str,
        *,
        func: Callable | None = None,
        args: tuple | None = None,
        kwargs: dict | None = None,
        name: str | None = None,
        **changes: Any,
    ) -> None:
        """修改任务属性。
        
        Args:
            job_id: 任务ID
            func: 新的任务函数
            args: 新的位置参数
            kwargs: 新的关键字参数
            name: 新的任务名称
            **changes: 其他要修改的属性
        """
        if not self._scheduler:
            raise RuntimeError("调度器未初始化")
        
        modify_kwargs: dict[str, Any] = {**changes}
        if func is not None:
            modify_kwargs["func"] = self._wrap_with_context(func)
        if args is not None:
            modify_kwargs["args"] = args
        if kwargs is not None:
            modify_kwargs["kwargs"] = kwargs
        if name is not None:
            modify_kwargs["name"] = name
        
        self._scheduler.modify_job(job_id, **modify_kwargs)
        logger.info(f"任务已修改: {job_id}")
    
    def reschedule_job(
        self,
        job_id: str,
        trigger: str = "interval",
        *,
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        days: int | None = None,
        cron: str | None = None,
    ) -> None:
        """重新调度任务（修改触发器）。
        
        Args:
            job_id: 任务ID
            trigger: 触发器类型（interval/cron）
            seconds: 间隔秒数
            minutes: 间隔分钟数
            hours: 间隔小时数
            days: 间隔天数
            cron: Cron表达式
        """
        if not self._scheduler:
            raise RuntimeError("调度器未初始化")
        
        # 构建触发器
        if trigger == "interval":
            if seconds:
                trigger_obj = IntervalTrigger(seconds=seconds)
            elif minutes:
                trigger_obj = IntervalTrigger(minutes=minutes)
            elif hours:
                trigger_obj = IntervalTrigger(hours=hours)
            elif days:
                trigger_obj = IntervalTrigger(days=days)
            else:
                raise ValueError("必须指定间隔时间")
        elif trigger == "cron":
            if not cron:
                raise ValueError("Cron触发器必须提供cron表达式")
            trigger_obj = CronTrigger.from_crontab(cron)
        else:
            raise ValueError(f"不支持的触发器类型: {trigger}")
        
        self._scheduler.reschedule_job(job_id, trigger=trigger_obj)
        logger.info(f"任务已重新调度: {job_id} | 触发器: {trigger}")
    
    def pause_job(self, job_id: str) -> None:
        """暂停单个任务。
        
        Args:
            job_id: 任务ID
        """
        if self._scheduler:
            self._scheduler.pause_job(job_id)
            logger.info(f"任务已暂停: {job_id}")
    
    def resume_job(self, job_id: str) -> None:
        """恢复单个任务。
        
        Args:
            job_id: 任务ID
        """
        if self._scheduler:
            self._scheduler.resume_job(job_id)
            logger.info(f"任务已恢复: {job_id}")
    
    def start(self) -> None:
        """启动调度器。
        
        启动时会注册所有通过装饰器收集的待处理任务。
        """
        if not self._initialized:
            raise RuntimeError("调度器未初始化")
        
        if self._scheduler.running:
            logger.warning("调度器已在运行")
            return
        
        # 注册所有待处理的任务
        for job_config in self._pending_jobs:
            self.add_job(**job_config)
        self._pending_jobs.clear()
        
        self._scheduler.start()
        self._started = True
        logger.info("调度器已启动")
    
    def shutdown(self) -> None:
        """关闭调度器。"""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("调度器已关闭")
    
    def pause(self) -> None:
        """暂停调度器。"""
        if self._scheduler:
            self._scheduler.pause()
            logger.info("调度器已暂停")
    
    def resume(self) -> None:
        """恢复调度器。"""
        if self._scheduler:
            self._scheduler.resume()
            logger.info("调度器已恢复")
    
    def scheduled_job(
        self,
        trigger: str = "interval",
        *,
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        days: int | None = None,
        cron: str | None = None,
        id: str | None = None,
        **kwargs: Any,
    ) -> Callable[[Callable], Callable]:
        """任务注册装饰器。
        
        使用示例:
            scheduler = SchedulerManager.get_instance()
            
            @scheduler.scheduled_job("interval", seconds=60)
            async def my_task():
                print("Task executed")
            
            @scheduler.scheduled_job("cron", cron="0 0 * * *")
            async def daily_task():
                print("Daily task")
        
        Args:
            trigger: 触发器类型（interval/cron）
            seconds: 间隔秒数
            minutes: 间隔分钟数
            hours: 间隔小时数
            days: 间隔天数
            cron: Cron表达式
            id: 任务ID
            **kwargs: 其他参数
        
        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            job_config = {
                "func": func,
                "trigger": trigger,
                "seconds": seconds,
                "minutes": minutes,
                "hours": hours,
                "days": days,
                "cron": cron,
                "id": id,
                **kwargs,
            }
            
            if self._started:
                # 调度器已启动，直接注册
                self.add_job(**job_config)
            else:
                # 调度器未启动，加入待注册列表
                self._pending_jobs.append(job_config)
                job_id = id or f"{func.__module__}.{func.__name__}"
                logger.debug(f"任务已加入待注册列表: {job_id}")
            
            return func
        return decorator

    def __repr__(self) -> str:
        """字符串表示。"""
        status = "running" if self._scheduler and self._scheduler.running else "stopped"
        return f"<SchedulerManager status={status}>"


__all__ = [
    "SchedulerManager",
]


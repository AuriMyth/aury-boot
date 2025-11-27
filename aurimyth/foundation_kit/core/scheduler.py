"""任务调度器管理器 - 统一的任务调度接口。

提供：
- 统一的调度器管理
- 任务注册和启动
- 生命周期管理
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from aurimyth.foundation_kit.utils.logging import logger


class SchedulerManager:
    """调度器管理器 - 单例模式。
    
    职责：
    1. 管理调度器实例
    2. 注册任务
    3. 生命周期管理
    
    使用示例:
        scheduler = SchedulerManager.get_instance()
        await scheduler.initialize()
        
        # 注册任务
        scheduler.add_job(
            func=my_task,
            trigger="interval",
            seconds=60
        )
        
        # 启动调度器
        scheduler.start()
    """
    
    _instance: Optional[SchedulerManager] = None
    
    def __init__(self) -> None:
        """私有构造函数。"""
        if SchedulerManager._instance is not None:
            raise RuntimeError("SchedulerManager 是单例类，请使用 get_instance() 获取实例")
        
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._initialized: bool = False
    
    @classmethod
    def get_instance(cls) -> SchedulerManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self) -> None:
        """初始化调度器。"""
        if self._initialized:
            logger.warning("调度器已初始化，跳过")
            return
        
        self._scheduler = AsyncIOScheduler()
        self._initialized = True
        logger.info("调度器初始化完成")
    
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
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        days: Optional[int] = None,
        cron: Optional[str] = None,
        id: Optional[str] = None,
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
        
        # 添加任务
        job_id = id or f"{func.__module__}.{func.__name__}"
        self._scheduler.add_job(
            func=func,
            trigger=trigger_obj,
            id=job_id,
            **kwargs,
        )
        
        logger.info(f"任务已注册: {job_id} | 触发器: {trigger}")
    
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
    
    def start(self) -> None:
        """启动调度器。"""
        if not self._initialized:
            raise RuntimeError("调度器未初始化")
        
        if self._scheduler.running:
            logger.warning("调度器已在运行")
            return
        
        self._scheduler.start()
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
    
    def __repr__(self) -> str:
        """字符串表示。"""
        status = "running" if self._scheduler and self._scheduler.running else "stopped"
        return f"<SchedulerManager status={status}>"


__all__ = [
    "SchedulerManager",
]

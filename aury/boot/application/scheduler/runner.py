"""调度器启动器。

提供调度器独立进程的启动入口。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import signal

from aury.boot.application.config import BaseConfig
from aury.boot.application.constants import ServiceType
from aury.boot.common.logging import logger
from aury.boot.infrastructure.scheduler import SchedulerManager


async def run_scheduler(
    config: BaseConfig | None = None,
    *,
    register_jobs: Callable[[], None] | Callable[[], Awaitable[None]] | None = None,
) -> None:
    """运行调度器进程（独立模式）。
    
    当 SERVICE_TYPE=scheduler 时，使用此函数启动独立的调度器进程。
    
    Args:
        config: 应用配置（可选，默认从环境变量加载）
        register_jobs: 注册任务的回调函数（可选）
    
    使用示例:
        async def setup_jobs():
            scheduler = SchedulerManager.get_instance()
            scheduler.add_job(
                func=my_task,
                trigger="interval",
                seconds=60
            )
        
        if __name__ == "__main__":
            asyncio.run(run_scheduler(register_jobs=setup_jobs))
    """
    # 加载配置
    if config is None:
        config = BaseConfig()
    
    service_config = config.service
    
    # 验证服务类型
    try:
        service_type = ServiceType(service_config.service_type.lower())
    except ValueError as e:
        raise ValueError(f"无效的服务类型: {service_config.service_type}") from e
    
    if service_type != ServiceType.SCHEDULER:
        raise ValueError(
            f"此函数仅用于 SERVICE_TYPE=scheduler，当前类型: {service_config.service_type}"
        )
    
    logger.info("启动调度器进程（独立模式）")
    
    # 初始化调度器
    scheduler_manager = SchedulerManager.get_instance()
    await scheduler_manager.initialize()
    
    # 注册任务
    if register_jobs:
        logger.info("注册定时任务...")
        if asyncio.iscoroutinefunction(register_jobs):
            await register_jobs()
        else:
            register_jobs()
        jobs = scheduler_manager.get_jobs()
        logger.info(f"已注册 {len(jobs)} 个定时任务")
    else:
        logger.warning("未提供任务注册函数，调度器将不执行任何任务")
    
    # 启动调度器
    scheduler_manager.start()
    logger.info("调度器进程已启动，等待任务执行...")
    
    # 设置信号处理，优雅关闭
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在关闭调度器...")
        scheduler_manager.shutdown()
        logger.info("调度器已关闭")
        asyncio.get_event_loop().stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 保持进程运行
    try:
        # 使用 asyncio.Event 保持进程运行
        stop_event = asyncio.Event()
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
        scheduler_manager.shutdown()
        logger.info("调度器已关闭")


def run_scheduler_sync(
    config: BaseConfig | None = None,
    *,
    register_jobs: Callable[[], None] | Callable[[], Awaitable[None]] | None = None,
) -> None:
    """运行调度器进程（同步版本）。
    
    这是 run_scheduler 的同步包装，方便直接调用。
    
    Args:
        config: 应用配置（可选，默认从环境变量加载）
        register_jobs: 注册任务的回调函数（可选）
    """
    asyncio.run(run_scheduler(config=config, register_jobs=register_jobs))


__all__ = [
    "run_scheduler",
    "run_scheduler_sync",
]


# 定时任务（Scheduler）

**文件**: `{package_name}/schedules/__init__.py`

```python
"""定时任务模块。"""

from aury.boot.common.logging import logger
from aury.boot.infrastructure.scheduler import SchedulerManager

scheduler = SchedulerManager.get_instance()


@scheduler.scheduled_job("interval", seconds=60)
async def every_minute():
    """每 60 秒执行。"""
    logger.info("定时任务执行中...")


@scheduler.scheduled_job("cron", hour=0, minute=0)
async def daily_task():
    """每天凌晨执行。"""
    logger.info("每日任务执行中...")


@scheduler.scheduled_job("cron", day_of_week="mon", hour=9)
async def weekly_report():
    """每周一 9 点执行。"""
    logger.info("周报任务执行中...")
```

启用方式：配置 `SCHEDULER_ENABLED=true`，框架自动加载 `{package_name}/schedules/` 模块。

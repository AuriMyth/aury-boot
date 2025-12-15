"""定时任务模块（Scheduler）。

在此文件中定义定时任务，使用 @scheduler.scheduled_job() 装饰器。

框架会自动发现并加载本模块，无需在 main.py 中手动导入。
也可通过 SCHEDULER_SCHEDULE_MODULES 环境变量指定自定义模块。
"""

# from aury.boot.common.logging import logger
# from aury.boot.infrastructure.scheduler import SchedulerManager
#
# scheduler = SchedulerManager.get_instance()
#
#
# @scheduler.scheduled_job("interval", seconds=60)
# async def example_job():
#     """示例定时任务，每 60 秒执行一次。"""
#     logger.info("定时任务执行中...")

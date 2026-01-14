"""定时任务模块（Scheduler）。

在此文件中定义定时任务，使用 @scheduler.scheduled_job() 装饰器。

框架会自动发现并加载本模块，无需在 main.py 中手动导入。
也可通过 SCHEDULER_SCHEDULE_MODULES 环境变量指定自定义模块。

触发器支持两种语法：
- 字符串模式（推荐）：@scheduler.scheduled_job("cron", hour="*", minute=0)
- 原生对象模式：@scheduler.scheduled_job(CronTrigger(hour="*"))
"""

# from aury.boot.common.logging import logger
# from aury.boot.infrastructure.scheduler import SchedulerManager
#
# scheduler = SchedulerManager.get_instance()
#
#
# # === 字符串模式（推荐，简洁）===
# @scheduler.scheduled_job("interval", seconds=60)
# async def example_job():
#     """示例定时任务，每 60 秒执行一次。"""
#     logger.info("定时任务执行中...")
#
#
# @scheduler.scheduled_job("cron", hour="*", minute=0)
# async def hourly_job():
#     """每小时整点执行。"""
#     logger.info("整点任务执行")
#
#
# # === 原生对象模式（完整功能）===
# # from apscheduler.triggers.cron import CronTrigger
# #
# # @scheduler.scheduled_job(CronTrigger.from_crontab("0 2 * * *"))
# # async def daily_job():
# #     """每天凌晨 2 点执行（使用 crontab 表达式）。"""
# #     logger.info("每日任务执行")

# 定时任务（Scheduler）

基于 APScheduler，支持两种触发器语法：字符串模式和原生对象模式。

## 基本用法

**文件**: `{package_name}/schedules/__init__.py`

```python
"""定时任务模块。"""

from aury.boot.common.logging import logger
from aury.boot.infrastructure.scheduler import SchedulerManager

scheduler = SchedulerManager.get_instance()


# === 字符串模式（推荐，简洁）===
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


# === 原生对象模式（完整功能）===
from apscheduler.triggers.cron import CronTrigger

@scheduler.scheduled_job(CronTrigger.from_crontab("0 2 * * *"))
async def crontab_task():
    """每天凌晨 2 点执行（使用 crontab 表达式）。"""
    logger.info("每日任务执行中...")
```

启用方式：配置 `SCHEDULER__ENABLED=true`，框架自动加载 `{package_name}/schedules/` 模块。

## 配置项

```bash
# .env
SCHEDULER__ENABLED=true                          # 是否启用
SCHEDULER__TIMEZONE=Asia/Shanghai                # 时区
SCHEDULER__COALESCE=true                         # 合并错过的任务
SCHEDULER__MAX_INSTANCES=1                       # 同一任务最大并发数
SCHEDULER__MISFIRE_GRACE_TIME=60                 # 错过容忍时间(秒)
SCHEDULER__JOBSTORE_URL=redis://localhost:6379/0 # 分布式存储（可选）
```

## 触发器语法

支持两种语法：

| 语法 | 适用场景 | 示例 |
|------|---------|------|
| 字符串模式 | 日常使用，简洁 | `"cron", hour="*", minute=0` |
| 原生对象 | crontab 表达式、复杂配置 | `CronTrigger.from_crontab("0 * * * *")` |

### cron - 定时触发

```python
# === 字符串模式 ===
# 每天凌晨 2:30
@scheduler.scheduled_job("cron", hour=2, minute=30)

# 每小时整点
@scheduler.scheduled_job("cron", hour="*", minute=0)

# 工作日 9:00
@scheduler.scheduled_job("cron", day_of_week="mon-fri", hour=9)

# 每月 1 号
@scheduler.scheduled_job("cron", day=1, hour=0)

# === 原生对象模式 ===
from apscheduler.triggers.cron import CronTrigger

# 使用 crontab 表达式
@scheduler.scheduled_job(CronTrigger.from_crontab("0 2 * * *"))  # 每天 2:00
```

**cron 参数**：`year`, `month`, `day`, `week`, `day_of_week`, `hour`, `minute`, `second`, `start_date`, `end_date`, `timezone`, `jitter`

### interval - 间隔触发

```python
# === 字符串模式 ===
@scheduler.scheduled_job("interval", seconds=30)   # 每 30 秒
@scheduler.scheduled_job("interval", minutes=5)    # 每 5 分钟
@scheduler.scheduled_job("interval", hours=1)      # 每小时
@scheduler.scheduled_job("interval", days=1)       # 每天

# === 原生对象模式 ===
from apscheduler.triggers.interval import IntervalTrigger

@scheduler.scheduled_job(IntervalTrigger(hours=1, jitter=60))  # 每小时，随机抖动 60 秒
```

**interval 参数**：`weeks`, `days`, `hours`, `minutes`, `seconds`, `start_date`, `end_date`, `timezone`, `jitter`

### DateTrigger - 一次性触发

```python
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta

# 10 秒后执行
scheduler.add_job(my_task, DateTrigger(run_date=datetime.now() + timedelta(seconds=10)))
```

## 条件加载

通过 `enabled` 参数控制任务是否注册：

```python
from config import settings

# 根据配置开关决定是否启用
@scheduler.scheduled_job("cron", hour=2, enabled=settings.ENABLE_REPORT)
async def daily_report():
    """仅在 ENABLE_REPORT=true 时注册。"""
    ...

# 区分环境
@scheduler.scheduled_job("interval", minutes=5, enabled=settings.ENV == "production")
async def prod_only_task():
    """仅生产环境执行。"""
    ...
```

`enabled=False` 时任务不会注册，日志记录：`任务已禁用，跳过注册: xxx`

## 多实例支持

支持不同业务线使用独立的调度器实例：

```python
# 默认实例
scheduler = SchedulerManager.get_instance()

# 命名实例
report_scheduler = SchedulerManager.get_instance("report")
cleanup_scheduler = SchedulerManager.get_instance("cleanup")
```

## 分布式调度

多节点部署时，配置相同的 `SCHEDULER__JOBSTORE_URL`，所有节点共享任务状态：

```bash
# 所有节点使用相同配置
SCHEDULER__JOBSTORE_URL=redis://redis:6379/0
```

APScheduler 自动协调防止重复执行。

### 代码方式配置（高级）

```python
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

scheduler = SchedulerManager.get_instance(
    "distributed",
    jobstores={{"default": RedisJobStore(host="localhost", port=6379)}},
    executors={{"default": AsyncIOExecutor()}},
    job_defaults={{"coalesce": True, "max_instances": 1}},
    timezone="Asia/Shanghai",
)
```

## 任务管理

```python
# 添加任务（字符串模式）
scheduler.add_job(my_task, "cron", hour=2, minute=0, id="my_task")

# 添加任务（原生对象模式）
from apscheduler.triggers.cron import CronTrigger
scheduler.add_job(my_task, CronTrigger(hour=2), id="my_task")

# 获取任务
job = scheduler.get_job("my_task")
jobs = scheduler.get_jobs()

# 暂停/恢复
scheduler.pause_job("my_task")
scheduler.resume_job("my_task")

# 移除
scheduler.remove_job("my_task")

# 重新调度（字符串模式）
scheduler.reschedule_job("my_task", "cron", hour=3)

# 重新调度（原生对象模式）
scheduler.reschedule_job("my_task", CronTrigger(hour=3))
```

## 监听器（高级）

通过底层 APScheduler 实例访问：

```python
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

def job_listener(event):
    if event.exception:
        logger.error(f"任务失败: {{event.job_id}}")
    else:
        logger.info(f"任务完成: {{event.job_id}}")

scheduler.scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
```

## 实践建议

1. **使用明确的 ID**：便于管理和调试
2. **合理设置间隔**：避免太频繁的任务
3. **异常处理**：在任务函数内捕获异常，避免影响调度器
4. **超时保护**：长运行任务使用 `asyncio.wait_for`

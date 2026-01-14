# 15. 定时调度完全指南

请参考 [00-quick-start.md](./00-quick-start.md) 第 15 章的基础用法。

## 触发器语法

框架支持两种触发器语法：

| 语法 | 适用场景 | 示例 |
|------|---------|------|
| 字符串模式 | 日常使用，简洁 | `"cron", hour="*", minute=0` |
| 原生对象 | crontab 表达式、复杂配置 | `CronTrigger.from_crontab("0 * * * *")` |

## 调度器初始化

```python
from aury.boot.infrastructure.scheduler import SchedulerManager

scheduler = SchedulerManager.get_instance()
```

### 带持久化存储的调度器

```python
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

# Redis 持久化
scheduler = SchedulerManager.get_instance(
    "persistent",
    jobstores={"default": RedisJobStore(host="localhost", port=6379)},
)

# SQLAlchemy 数据库存储
scheduler = SchedulerManager.get_instance(
    "db",
    jobstores={"default": SQLAlchemyJobStore(url="sqlite:///jobs.db")},
)

# 完整配置
scheduler = SchedulerManager.get_instance(
    "full",
    jobstores={"default": RedisJobStore(host="localhost")},
    executors={"default": AsyncIOExecutor()},
    job_defaults={"coalesce": True, "max_instances": 3, "misfire_grace_time": 60},
    timezone="Asia/Shanghai",
)
```

## Cron 任务

### 每天定时执行

```python
# 字符串模式（推荐）
scheduler.add_job(daily_report, "cron", hour=2, minute=30, id="daily_report")

# 原生对象模式
from apscheduler.triggers.cron import CronTrigger
scheduler.add_job(daily_report, CronTrigger(hour=2, minute=30), id="daily_report")
```

### 每周执行

```python
# 每周一上午 9 点执行
scheduler.add_job(weekly_summary, "cron", day_of_week="mon", hour=9, id="weekly_summary")
```

### 每月执行

```python
# 每个月的第一天执行
scheduler.add_job(monthly_cleanup, "cron", day=1, hour=0, id="monthly_cleanup")
```

### 工作日执行

```python
# 工作日（周一至周五）每小时执行
scheduler.add_job(check_status, "cron", day_of_week="mon-fri", hour="*", id="workday_check")
```

### 使用 crontab 表达式

```python
# 每天凌晨 2 点执行（仅原生对象模式支持）
from apscheduler.triggers.cron import CronTrigger
scheduler.add_job(daily_task, CronTrigger.from_crontab("0 2 * * *"), id="daily_task")
```

## 间隔任务

### 固定间隔

```python
# 字符串模式（推荐）
scheduler.add_job(heartbeat, "interval", seconds=30, id="heartbeat")
scheduler.add_job(sync_data, "interval", minutes=5, id="sync_data")
scheduler.add_job(hourly_task, "interval", hours=1, id="hourly_task")

# 原生对象模式
from apscheduler.triggers.interval import IntervalTrigger
scheduler.add_job(heartbeat, IntervalTrigger(seconds=30), id="heartbeat")
```

## 一次性任务

### 指定时间执行

```python
from datetime import datetime, timedelta
from apscheduler.triggers.date import DateTrigger

# 10 秒后执行一次
run_time = datetime.now() + timedelta(seconds=10)
scheduler.add_job(delayed_task, DateTrigger(run_date=run_time), id="delayed_task")
```

## 带参数的任务

### 传递参数

```python
async def process_user(user_id: str, action: str = "default"):
    """处理用户"""
    logger.info(f"处理用户 {user_id}，操作: {action}")

# 添加任务，传递参数
scheduler.add_job(
    process_user,
    "cron",
    hour=3,
    args=["user123"],          # 位置参数
    kwargs={"action": "sync"},  # 关键字参数
    id="process_user_sync"
)
```

## 任务管理

### 获取任务

```python
# 获取所有任务
jobs = scheduler.get_jobs()
for job in jobs:
    print(f"任务: {job.id}, 下次执行: {job.next_run_time}")

# 获取单个任务
job = scheduler.get_job("daily_report")
if job:
    print(f"任务 {job.id} 已存在")
```

### 暂停/恢复任务

```python
# 暂停任务
scheduler.pause_job("daily_report")

# 恢复任务
scheduler.resume_job("daily_report")
```

### 删除任务

```python
# 删除单个任务
scheduler.remove_job("daily_report")

# 删除所有任务
scheduler.remove_all_jobs()
```

### 更新任务

```python
# 重新安排任务
scheduler.reschedule_job(
    "daily_report",
    trigger=CronTrigger(hour=3, minute=0),  # 改为凌晨 3 点
)
```

## 常见场景

### 数据同步

```python
@scheduler.scheduled_job(IntervalTrigger(minutes=5))
async def sync_from_external_api():
    """每 5 分钟同步外部数据"""
    try:
        data = await external_api.fetch_updates()
        await db.update_data(data)
        logger.info("数据同步完成")
    except Exception as e:
        logger.error(f"数据同步失败: {e}")

# 或使用 add_job
scheduler.add_job(
    func=sync_from_external_api,
    trigger=IntervalTrigger(minutes=5),
    id="data_sync"
)
```

### 清理过期数据

```python
async def cleanup_expired_records():
    """每天凌晨 2 点清理过期数据"""
    deleted = await db.delete_where(
        "records",
        expire_time__lt=datetime.now()
    )
    logger.info(f"已清理 {deleted} 条过期数据")

scheduler.add_job(
    func=cleanup_expired_records,
    trigger=CronTrigger(hour=2, minute=0),
    id="cleanup_expired"
)
```

### 定期备份

```python
async def backup_database():
    """每天备份数据库"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"
    
    await backup_service.backup(filename)
    logger.info(f"备份完成: {filename}")

scheduler.add_job(
    func=backup_database,
    trigger=CronTrigger(hour=1),  # 每天凌晨 1 点
    id="db_backup"
)
```

### 性能监控

```python
async def collect_metrics():
    """每分钟收集一次性能指标"""
    metrics = await monitor.collect_metrics()
    
    await db.save_metrics(metrics)
    
    if metrics.cpu > 80:
        logger.warning(f"CPU 使用率过高: {metrics.cpu}%")

scheduler.add_job(
    func=collect_metrics,
    trigger=IntervalTrigger(minutes=1),
    id="collect_metrics"
)
```

### 状态检查

```python
async def health_check():
    """每 30 秒检查一次健康状态"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "external_api": await check_external_api(),
    }
    
    all_healthy = all(checks.values())
    
    if not all_healthy:
        logger.error(f"健康检查失败: {checks}")
        await alert_service.send_alert(checks)

scheduler.add_job(
    func=health_check,
    trigger=IntervalTrigger(seconds=30),
    id="health_check"
)
```

## 错误处理

### 异常捕获

```python
async def safe_task():
    """安全的定时任务"""
    try:
        await dangerous_operation()
    except Exception as e:
        logger.error(f"任务执行失败: {e}", exc_info=True)
        # 不重新抛出异常，避免调度器停止

scheduler.add_job(
    func=safe_task,
    trigger=IntervalTrigger(hours=1),
    id="safe_task"
)
```

### 任务超时

```python
import asyncio

async def timeout_protected_task():
    """带超时保护的任务"""
    try:
        await asyncio.wait_for(long_operation(), timeout=300)
    except asyncio.TimeoutError:
        logger.error("任务执行超时")

scheduler.add_job(
    func=timeout_protected_task,
    trigger=CronTrigger(hour=2),
    id="timeout_protected"
)
```

## 配置项

在 `.env` 中配置：

```bash
SCHEDULER__ENABLED=true                          # 是否启用
SCHEDULER__TIMEZONE=Asia/Shanghai                # 时区
SCHEDULER__COALESCE=true                         # 合并错过的任务执行
SCHEDULER__MAX_INSTANCES=1                       # 同一任务最大并发实例数
SCHEDULER__MISFIRE_GRACE_TIME=60                 # 任务错过容忍时间(秒)
SCHEDULER__JOBSTORE_URL=redis://localhost:6379/0 # 分布式存储（可选）
```

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

多节点部署时，配置相同的 `SCHEDULER__JOBSTORE_URL`，所有节点共享任务状态，APScheduler 自动协调防止重复执行。

### 支持的存储后端

- **Redis**：`redis://localhost:6379/0`
- **SQLite**：`sqlite:///jobs.db`
- **PostgreSQL**：`postgresql://user:pass@host/db`
- **MySQL**：`mysql://user:pass@host/db`

### 代码方式配置（高级）

```python
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

scheduler = SchedulerManager.get_instance(
    "distributed",
    jobstores={"default": RedisJobStore(host="localhost", port=6379)},
    executors={"default": AsyncIOExecutor()},
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
    timezone="Asia/Shanghai",
)
```

## 监听器

通过底层 APScheduler 实例访问：

```python
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

def job_listener(event):
    if event.exception:
        logger.error(f"任务失败: {event.job_id}, 异常: {event.exception}")
    else:
        logger.info(f"任务完成: {event.job_id}")

scheduler.scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
```

## 监控和调试

### 查看调度器状态

```python
# 获取所有任务
jobs = scheduler.get_jobs()
logger.info(f"已安排任务数: {len(jobs)}")

for job in jobs:
    logger.info(
        f"任务: {job.id}, "
        f"下次执行: {job.next_run_time}, "
        f"状态: {'暂停' if job.paused else '运行中'}"
    )
```

### 任务执行日志

```python
from aury.boot.common.logging import logger

async def logged_task():
    logger.info("任务开始执行")
    
    try:
        result = await do_work()
        logger.info(f"任务执行成功: {result}")
    except Exception as e:
        logger.error(f"任务执行失败: {e}", exc_info=True)

scheduler.add_job(
    func=logged_task,
    trigger=IntervalTrigger(hours=1),
    id="logged_task"
)
```

## 最佳实践

### 1. 使用明确的 ID

```python
# ✘ 不清楚
scheduler.add_job(func=my_task, trigger=IntervalTrigger(minutes=5))

# ✔ 清楚
scheduler.add_job(
    func=my_task,
    trigger=IntervalTrigger(minutes=5),
    id="sync_user_data",
    name="同步用户数据"
)
```

### 2. 合理设置执行间隔

```python
# ✘ 太频繁
scheduler.add_job(func=heavy_task, trigger=IntervalTrigger(seconds=1))

# ✔ 合理间隔
scheduler.add_job(func=heavy_task, trigger=IntervalTrigger(minutes=5))
```

### 3. 处理任务失败

```python
# ✅ 优雅处理
async def resilient_task():
    try:
        await external_api.call()
    except ConnectionError:
        logger.warning("连接失败，将在下次重试")
    except Exception as e:
        logger.error(f"未预期的错误: {e}")
```

### 4. 避免重复执行

```python
import asyncio

_lock = asyncio.Lock()

async def protected_task():
    """确保同一时刻只有一个任务实例运行"""
    async with _lock:
        if some_condition_is_running:
            logger.info("任务已在运行，跳过本次执行")
            return
        
        await do_work()
```

---

**总结**：定时调度适合执行周期性任务，如数据同步、备份、清理、监控等。使用合理的间隔和错误处理，可以构建稳定的后台任务系统。

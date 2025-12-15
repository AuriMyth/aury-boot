# 15. 定时调度完全指南

请参考 [00-quick-start.md](./00-quick-start.md) 第 15 章的基础用法。

## 调度器初始化

```python
from aury.boot.infrastructure.scheduler.manager import SchedulerManager

scheduler = SchedulerManager.get_instance()
```

## Cron 任务

### 每天定时执行

```python
# 每天凌晨 2 点 30 分执行
scheduler.add_job(
    func=daily_report,
    trigger="cron",
    hour=2,
    minute=30,
    id="daily_report",
    name="每日报告生成"
)
```

### 每周执行

```python
# 每周一上午 9 点执行
scheduler.add_job(
    func=weekly_summary,
    trigger="cron",
    day_of_week="mon",
    hour=9,
    id="weekly_summary"
)
```

### 每月执行

```python
# 每个月的第一天执行
scheduler.add_job(
    func=monthly_cleanup,
    trigger="cron",
    day=1,
    hour=0,
    id="monthly_cleanup"
)
```

### 工作日执行

```python
# 工作日（周一至周五）每小时执行
scheduler.add_job(
    func=check_status,
    trigger="cron",
    day_of_week="mon-fri",
    hour="*",
    id="workday_check"
)
```

## 间隔任务

### 固定间隔

```python
# 每 30 秒执行一次
scheduler.add_job(
    func=heartbeat,
    trigger="interval",
    seconds=30,
    id="heartbeat"
)

# 每 5 分钟执行一次
scheduler.add_job(
    func=sync_data,
    trigger="interval",
    minutes=5,
    id="sync_data"
)

# 每小时执行一次
scheduler.add_job(
    func=hourly_task,
    trigger="interval",
    hours=1,
    id="hourly_task"
)
```

## 一次性任务

### 指定时间执行

```python
from datetime import datetime, timedelta

# 10 秒后执行一次
run_time = datetime.now() + timedelta(seconds=10)
scheduler.add_job(
    func=delayed_task,
    trigger="date",
    run_date=run_time,
    id="delayed_task"
)
```

## 带参数的任务

### 传递参数

```python
async def process_user(user_id: str, action: str = "default"):
    """处理用户"""
    logger.info(f"处理用户 {user_id}，操作: {action}")

# 添加任务，传递参数
scheduler.add_job(
    func=process_user,
    trigger="cron",
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
    trigger="cron",
    hour=3,  # 改为凌晨 3 点
    minute=0
)
```

## 常见场景

### 数据同步

```python
@scheduler.scheduled_job("interval", minutes=5)
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
    trigger="interval",
    minutes=5,
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
    trigger="cron",
    hour=2,
    minute=0,
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
    trigger="cron",
    hour=1,  # 每天凌晨 1 点
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
    trigger="interval",
    minutes=1,
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
    trigger="interval",
    seconds=30,
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
    trigger="interval",
    hours=1,
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
    trigger="cron",
    hour=2,
    id="timeout_protected"
)
```

## 任务配置

在 `.env` 中配置：

```bash
# 调度器模式
SCHEDULER_MODE=embedded  # embedded, standalone, disabled

# 并发执行数
SCHEDULER_MAX_WORKERS=5
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
    trigger="interval",
    hours=1,
    id="logged_task"
)
```

## 最佳实践

### 1. 使用明确的 ID

```python
# ❌ 不清楚
scheduler.add_job(func=my_task, trigger="interval", minutes=5)

# ✅ 清楚
scheduler.add_job(
    func=my_task,
    trigger="interval",
    minutes=5,
    id="sync_user_data",
    name="同步用户数据"
)
```

### 2. 合理设置执行间隔

```python
# ❌ 太频繁
scheduler.add_job(func=heavy_task, trigger="interval", seconds=1)

# ✅ 合理间隔
scheduler.add_job(func=heavy_task, trigger="interval", minutes=5)
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

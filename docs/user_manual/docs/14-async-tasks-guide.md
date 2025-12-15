# 13. 异步任务完整指南

请参考 [00-quick-start.md](./00-quick-start.md) 第 13 章的基础用法。

## 任务定义

### 基础任务

```python
from aury.boot.infrastructure.tasks.manager import TaskManager

tm = TaskManager.get_instance()

@tm.conditional_task(queue_name="default", max_retries=3)
async def send_email(email: str, subject: str, content: str):
    """发送邮件任务"""
    # 模拟发送邮件
    print(f"发送邮件到: {email}")
```

### 任务参数

```python
@tm.conditional_task(
    queue_name="emails",      # 队列名称
    max_retries=5,            # 最大重试次数
    timeout=600,              # 超时时间（秒）
    retry_delay=30,           # 重试延迟（秒）
)
async def process_report(report_id: str, format: str = "pdf"):
    # 处理报告
    pass
```

## 任务调用

### 发送任务（异步）

```python
# 发送任务到队列，不等待结果
task = send_email.send(
    email="user@example.com",
    subject="Hello",
    content="Test message"
)
```

### 延迟执行

```python
import asyncio

# 延迟 30 秒后发送
await asyncio.sleep(30)
send_email.send(email="user@example.com", subject="Hello", content="Message")
```

## 启动 Worker

### 单进程 Worker

```bash
# 启动 worker 处理默认队列
aum worker

# 启动 worker 处理特定队列
aum worker -q emails
```

### 多进程 Worker

```bash
# 启动 8 个并发 worker
aum worker -c 8
```

## 错误处理和重试

### 异常处理

```python
@tm.conditional_task(max_retries=3)
async def risky_task(data: str):
    try:
        # 可能失败的操作
        result = await external_api.call(data)
        return result
    except Exception as e:
        logger.error(f"任务失败: {e}")
        raise  # 重新抛出异常以触发重试
```

### 重试策略

```python
@tm.conditional_task(max_retries=3, retry_delay=60)
async def process_with_backoff(task_id: str):
    """第 1 次重试等待 60 秒，第 2 次等待 120 秒，etc."""
    try:
        await process_data(task_id)
    except TemporaryError:
        # 临时错误会自动重试
        raise
    except PermanentError:
        # 永久错误不重试
        logger.error(f"永久错误: {task_id}")
```

## 常见模式

### 邮件发送

```python
@tm.conditional_task(queue_name="emails", max_retries=3)
async def send_welcome_email(user_id: str):
    user = await db.get_user(user_id)
    if not user:
        return
    
    await email_service.send(
        to=user.email,
        subject="欢迎加入",
        template="welcome"
    )
    logger.info(f"欢迎邮件已发送给 {user.email}")
```

### 数据处理

```python
@tm.conditional_task(queue_name="data", max_retries=2, timeout=3600)
async def generate_report(report_id: str):
    report = await db.get_report(report_id)
    
    # 处理大量数据
    data = await collect_data(report.filters)
    
    # 生成报告
    pdf = await generate_pdf(data)
    
    # 保存报告
    await storage.upload_file(f"reports/{report_id}.pdf", pdf)
    
    # 更新状态
    await db.update_report(report_id, status="completed")
    
    logger.info(f"报告 {report_id} 已生成")
```

### 定时任务集成

```python
from aury.boot.infrastructure.scheduler.manager import SchedulerManager

scheduler = SchedulerManager.get_instance()

@tm.conditional_task(queue_name="batch")
async def daily_cleanup():
    """每天清理过期数据"""
    deleted = await db.delete_expired_records()
    logger.info(f"已清理 {deleted} 条过期数据")

# 在应用启动时注册
scheduler.add_job(
    func=daily_cleanup.send,
    trigger="cron",
    hour=2,  # 每天凌晨 2 点
    id="daily_cleanup"
)
```

### 批量处理

```python
@tm.conditional_task(queue_name="batch", max_retries=2)
async def process_batch(batch_id: str):
    # 获取批次
    batch = await db.get_batch(batch_id)
    items = batch.items
    
    # 批量处理
    results = []
    for item in items:
        result = await process_item(item)
        results.append(result)
    
    # 保存结果
    await db.save_batch_results(batch_id, results)
    logger.info(f"批次 {batch_id} 处理完成，共 {len(results)} 条")
```

## 任务队列配置

在 `.env` 中配置：

```bash
# Redis 任务队列
TASK_BROKER_URL=redis://localhost:6379/0
TASK_QUEUE_NAME=default
TASK_MAX_WORKERS=4
TASK_TIMEOUT=600
```

## 监控和调试

### 任务日志

```python
from aury.boot.common.logging import logger

@tm.conditional_task(max_retries=3)
async def monitored_task(data: str):
    logger.info(f"任务开始: {data}")
    
    try:
        result = await process(data)
        logger.info(f"任务成功: {result}")
        return result
    except Exception as e:
        logger.error(f"任务失败: {e}", exc_info=True)
        raise
```

## 最佳实践

### 1. 任务应该幂等

```python
# ❌ 不幂等 - 多次调用会有问题
@tm.conditional_task()
async def bad_task(user_id: str):
    # 每次调用都会增加金额
    await db.update(f"UPDATE users SET balance = balance + 100 WHERE id = {user_id}")

# ✅ 幂等 - 多次调用结果相同
@tm.conditional_task()
async def good_task(user_id: str, transaction_id: str):
    # 检查事务是否已处理
    if await db.transaction_exists(transaction_id):
        return
    
    # 处理事务
    await db.apply_transaction(user_id, transaction_id, amount=100)
```

### 2. 任务应该快速完成

```python
# ❌ 超时风险
@tm.conditional_task(timeout=300)
async def slow_task():
    result = await very_slow_operation()  # 可能超过 5 分钟
    return result

# ✅ 快速任务
@tm.conditional_task(timeout=300)
async def fast_task():
    # 启动后台任务
    await queue_slow_operation()
    return {"status": "processing"}
```

### 3. 合理使用重试

```python
# 只对临时错误重试
@tm.conditional_task(max_retries=3)
async def smart_retry_task(user_id: str):
    try:
        result = await external_api.fetch(user_id)
        return result
    except ConnectionError:
        # 临时连接错误 - 会重试
        raise
    except NotFoundError:
        # 永久错误 - 不应该重试
        logger.error(f"用户 {user_id} 不存在")
        return None
```

---

**总结**：异步任务适合处理耗时操作（邮件、报告生成、数据处理），充分利用任务队列可以提升应用响应速度，改善用户体验。

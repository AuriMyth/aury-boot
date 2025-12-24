# 异步任务（Dramatiq）

**文件**: `{package_name}/tasks/__init__.py`

```python
"""异步任务模块。"""

from aury.boot.common.logging import logger
from aury.boot.infrastructure.tasks import conditional_task


@conditional_task()
def send_email(to: str, subject: str, body: str):
    """异步发送邮件。"""
    logger.info(f"发送邮件到 {{to}}: {{subject}}")
    # 实际发送逻辑...
    return {{"status": "sent"}}


@conditional_task()
def process_order(order_id: str):
    """异步处理订单。"""
    logger.info(f"处理订单: {{order_id}}")
```

调用方式：

```python
# 异步执行（发送到队列）
send_email.send("user@example.com", "Hello", "World")

# 延迟执行
send_email.send_with_options(args=("user@example.com", "Hello", "World"), delay=60000)  # 60秒后
```

启用方式：
1. 配置 `TASK_BROKER_URL`（如 `redis://localhost:6379/0`）
2. 运行 Worker：`aury worker`

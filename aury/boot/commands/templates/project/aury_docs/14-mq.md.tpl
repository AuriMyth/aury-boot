# 消息队列（MQ）

支持 `redis` 和 `rabbitmq` 后端的消息队列，用于异步任务解耦。

## 14.1 基本用法

```python
from aury.boot.infrastructure.mq import MQManager

# 获取实例
mq = MQManager.get_instance()

# Redis 后端
await mq.initialize(backend="redis", url="redis://localhost:6379/0")

# RabbitMQ 后端
await mq.initialize(backend="rabbitmq", url="amqp://guest:guest@localhost:5672/")
```

## 14.2 生产者

```python
# 发送消息
await mq.publish(
    queue="orders",
    message={{"order_id": "123", "action": "created"}}
)

# 批量发送
await mq.publish_batch(
    queue="orders",
    messages=[
        {{"order_id": "1", "action": "created"}},
        {{"order_id": "2", "action": "updated"}},
    ]
)
```

## 14.3 消费者

**文件**: `{package_name}/workers/order_worker.py`

```python
from aury.boot.infrastructure.mq import MQManager
from aury.boot.common.logging import logger

mq = MQManager.get_instance()


async def process_order(message: dict):
    \"\"\"处理订单消息。\"\"\"
    logger.info(f"处理订单: {{message['order_id']}}")
    # 业务逻辑...


async def start_consumer():
    \"\"\"启动消费者。\"\"\"
    await mq.consume("orders", process_order)


# 带确认的消费
async def process_with_ack(message: dict, ack, nack):
    try:
        await process_order(message)
        await ack()
    except Exception:
        await nack(requeue=True)

await mq.consume("orders", process_with_ack, auto_ack=False)
```

## 14.4 多实例

```python
# 不同用途的 MQ 实例
orders_mq = MQManager.get_instance("orders")
notifications_mq = MQManager.get_instance("notifications")

# 分别初始化
await orders_mq.initialize(backend="rabbitmq", url="amqp://localhost:5672/orders")
await notifications_mq.initialize(backend="redis", url="redis://localhost:6379/5")
```

## 14.5 环境变量

```bash
# 默认实例
MQ_BACKEND=redis
MQ_URL=redis://localhost:6379/0

# 多实例（格式：MQ_{{INSTANCE}}_{{FIELD}}）
MQ_DEFAULT_BACKEND=redis
MQ_DEFAULT_URL=redis://localhost:6379/4
MQ_ORDERS_BACKEND=rabbitmq
MQ_ORDERS_URL=amqp://guest:guest@localhost:5672/
MQ_ORDERS_PREFETCH_COUNT=10
```

## 14.6 与异步任务（Dramatiq）的区别

- **MQ**：轻量级消息传递，适合简单的生产者-消费者模式
- **Dramatiq（TaskManager）**：功能更丰富，支持重试、延迟、优先级等

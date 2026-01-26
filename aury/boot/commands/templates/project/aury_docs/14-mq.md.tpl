# 消息队列（MQ）

支持 `redis`、`redis_stream` 和 `rabbitmq` 后端的消息队列，用于异步任务解耦。

## 14.1 基本用法

```python
from aury.boot.infrastructure.mq import MQManager

# 获取实例
mq = MQManager.get_instance()

# Redis List 后端（简单队列）
await mq.initialize(backend="redis", url="redis://localhost:6379/0")

# Redis Stream 后端（推荐，支持消费者组）
await mq.initialize(backend="redis_stream", url="redis://localhost:6379/0")

# RabbitMQ 后端
await mq.initialize(backend="rabbitmq", url="amqp://guest:guest@localhost:5672/")
```

## 14.2 后端对比

**Redis List (redis)**:
- 简单的 FIFO 队列（LPUSH/BRPOP）
- 适合单消费者场景
- 消息不持久化（除非开启 AOF）

**Redis Stream (redis_stream)** ⭐ 推荐:
- 支持消费者组，多实例可并行消费
- 消息持久化（配合 AOF）
- 支持消息确认（ACK）和重试
- 支持消息回放和历史查询

**RabbitMQ (rabbitmq)**:
- 功能最完整的消息队列
- 支持多种交换机类型
- 适合复杂的消息路由场景

## 14.3 生产者

```python
from aury.boot.infrastructure.mq import MQMessage

# 发送消息
await mq.send(
    queue="orders",
    message={{"order_id": "123", "action": "created"}}
)

# 使用 MQMessage 对象（可设置 headers）
msg = MQMessage(
    body={{"order_id": "123"}},
    headers={{"priority": "high"}}
)
await mq.send("orders", msg)
```

## 14.4 消费者

**文件**: `{package_name}/workers/order_worker.py`

```python
from aury.boot.infrastructure.mq import MQManager, MQMessage
from aury.boot.common.logging import logger

mq = MQManager.get_instance()


async def process_order(message: MQMessage):
    \"\"\"处理订单消息。\"\"\"
    logger.info(f"处理订单: {{message.body}}")
    # 业务逻辑...


async def start_consumer():
    \"\"\"启动消费者。\"\"\"
    # consume 会自动处理 ACK/NACK
    await mq.consume("orders", process_order)
```

## 14.5 Redis Stream 特性

```python
from aury.boot.infrastructure.mq.backends.redis_stream import RedisStreamMQ

# 初始化时指定消费者组
mq = MQManager.get_instance()
await mq.initialize(
    backend="redis_stream",
    url="redis://localhost:6379/0"
)

# 获取底层 RedisStreamMQ 实例使用高级特性
stream_mq: RedisStreamMQ = mq.backend

# 读取所有历史消息（用于重放）
messages = await stream_mq.read_all("orders", count=100)

# 阻塞读取新消息（用于 SSE/实时推送）
messages = await stream_mq.read_blocking(
    "orders",
    last_id="$",  # 从最新消息开始
    count=10,
    block_ms=5000  # 阻塞 5 秒
)

# 裁剪 Stream（保留最新 1000 条）
await stream_mq.trim("orders", maxlen=1000)

# 获取 Stream 信息
info = await stream_mq.stream_info("orders")
```

## 14.6 多实例配置

框架支持命名多实例，适合不同业务场景使用不同的 MQ：

```python
# 代码中使用命名实例
orders_mq = MQManager.get_instance("orders")
notifications_mq = MQManager.get_instance("notifications")

# 分别初始化
await orders_mq.initialize(backend="redis_stream", url="redis://localhost:6379/1")
await notifications_mq.initialize(backend="redis", url="redis://localhost:6379/2")
```

**环境变量配置**（自动初始化）:

```bash
# 单实例配置
MQ__BACKEND=redis_stream
MQ__URL=redis://localhost:6379/0

# 多实例配置（格式：MQ__{{INSTANCE}}__{{FIELD}}）
MQ__DEFAULT__BACKEND=redis_stream
MQ__DEFAULT__URL=redis://localhost:6379/4
MQ__ORDERS__BACKEND=rabbitmq
MQ__ORDERS__URL=amqp://guest:guest@localhost:5672/
```

## 14.7 与异步任务（Dramatiq）的区别

- **MQ**：轻量级消息传递，适合简单的生产者-消费者模式、实时通知、多实例消费
- **Dramatiq（TaskManager）**：功能更丰富，支持重试、延迟、优先级、Actor 模式

选择建议：
- 简单的异步解耦 → MQ (redis_stream)
- 需要重试/延迟/优先级 → Dramatiq
- 多服务实例并行消费 → MQ (redis_stream) 或 RabbitMQ

# 25. 基础设施高级功能

本章介绍 v0.3.x 新增的基础设施模块：客户端管理、流式通道、消息队列和多实例配置。

## 多实例配置

所有基础设施组件均支持多实例配置，格式：`{PREFIX}__{INSTANCE}__{FIELD}`。

### 环境变量格式

```bash
# 数据库多实例
DATABASE__URL=sqlite+aiosqlite:///./dev.db          # 默认实例
DATABASE__DEFAULT__URL=sqlite+aiosqlite:///./dev.db  # 等同于默认
DATABASE__READONLY__URL=postgresql+asyncpg://...      # 只读实例

# 缓存多实例
CACHE__CACHE_TYPE=redis
CACHE__URL=redis://localhost:6379/0
CACHE__SESSION__CACHE_TYPE=redis
CACHE__SESSION__URL=redis://localhost:6379/2

# 流式通道多实例
CHANNEL__BACKEND=memory
CHANNEL__DEFAULT__BACKEND=redis
CHANNEL__DEFAULT__URL=redis://localhost:6379/3
```

### 在代码中使用

```python
from aury.boot.application.config import BaseConfig

config = BaseConfig()

# 获取所有数据库实例配置
db_configs = config.get_database_instances()
# 返回: {"default": DatabaseInstanceConfig(...), "readonly": DatabaseInstanceConfig(...)}

# 获取所有缓存实例配置
cache_configs = config.get_cache_instances()
# 返回: {"default": CacheInstanceConfig(...), "session": CacheInstanceConfig(...)}
```

---

## 客户端管理 (clients)

统一管理外部服务连接，支持多实例。

### Redis 客户端

```python
from aury.boot.infrastructure.clients import RedisClient

# 获取实例（单例模式）
client = RedisClient.get_instance()  # 默认实例
cache_client = RedisClient.get_instance("cache")  # 命名实例

# 配置并初始化
await client.configure(
    url="redis://localhost:6379/0",
    max_connections=10,
    decode_responses=True
).initialize()

# 使用连接
redis = client.connection
await redis.set("key", "value")
value = await redis.get("key")

# 或使用 execute
await client.execute("set", "key", "value")

# 健康检查
is_healthy = await client.health_check()

# 清理
await client.cleanup()
```

### RabbitMQ 客户端

```python
from aury.boot.infrastructure.clients import RabbitMQClient

# 获取实例
client = RabbitMQClient.get_instance()
events_mq = RabbitMQClient.get_instance("events")

# 配置并初始化
await client.configure(
    url="amqp://guest:guest@localhost:5672/",
    heartbeat=60,
    prefetch_count=10
).initialize()

# 获取通道
channel = await client.get_channel()

# 发布消息
from aio_pika import Message
await channel.default_exchange.publish(
    Message(body=b"hello"),
    routing_key="test_queue"
)

# 获取新通道（用于消费者）
consumer_channel = await client.get_channel(new=True)

# 健康检查
is_healthy = await client.health_check()

# 清理
await client.cleanup()
```

---

## 流式通道 (Channel)

用于 SSE（Server-Sent Events）和实时通信场景。

### 核心概念

- **ChannelManager**：管理器，支持命名多实例（如 sse、notification 独立管理）
- **channel 参数**：通道名/Topic，用于区分不同的消息流（如 `user:123`、`order:456`）

### 基本用法

```python
from aury.boot.infrastructure.channel import ChannelManager

# 命名多实例（推荐）- 不同业务场景使用不同实例
sse_channel = ChannelManager.get_instance("sse")
notification_channel = ChannelManager.get_instance("notification")

# Memory 后端（单进程）
await sse_channel.initialize(backend="memory")

# Redis 后端（多进程/分布式）- 需要提供 RedisClient
from aury.boot.infrastructure.clients.redis import RedisClient
redis_client = RedisClient.get_instance()
await redis_client.initialize(url="redis://localhost:6379/0")

await notification_channel.initialize(
    backend="redis",
    redis_client=redis_client
)
```

### 发布和订阅（Topic 管理）

```python
# 发布消息到指定 Topic
await sse_channel.publish("user:123", {"event": "message", "data": "hello"})
await sse_channel.publish("order:456", {"status": "shipped"})

# 订阅指定 Topic
async def sse_endpoint(user_id: str):
    async for message in sse_channel.subscribe(f"user:{user_id}"):
        yield f"data: {json.dumps(message)}\n\n"
```

### 模式订阅（psubscribe）

使用通配符订阅多个通道，适合一个 SSE 连接接收多种事件。

```python
# 订阅空间下所有事件
async for msg in sse_channel.psubscribe(f"space:{space_id}:*"):
    yield msg.to_sse()  # 自动转换为 SSE 格式

# 后端发布不同类型的事件
await sse_channel.publish(f"space:{space_id}:file_analyzed", {...}, event="file_analyzed")
await sse_channel.publish(f"space:{space_id}:comment_added", {...}, event="comment_added")
```

**通配符说明**：
- `*` 匹配任意字符
- `?` 匹配单个字符
- `[seq]` 匹配 seq 中的任意字符
- 示例：`space:123:*` 匹配 `space:123:file_analyzed`、`space:123:comment_added` 等

Redis 后端使用 Redis 原生 `PSUBSCRIBE`，内存后端使用 `fnmatch` 实现。

### FastAPI SSE 示例

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from aury.boot.infrastructure.channel import ChannelManager

router = APIRouter()

# 获取命名实例（在 app 启动时已初始化）
sse_channel = ChannelManager.get_instance("sse")

@router.get("/sse/{user_id}")
async def sse_stream(user_id: str):
    async def event_generator():
        # user_id 作为 Topic，区分不同用户的消息流
        async for message in sse_channel.subscribe(f"user:{user_id}"):
            yield f"data: {json.dumps(message)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/notify/{user_id}")
async def send_notification(user_id: str, message: str):
    await sse_channel.publish(f"user:{user_id}", {"message": message})
    return {"status": "sent"}
```

---

## 消息队列 (MQ)

支持 Redis 和 RabbitMQ 后端的消息队列。

### 配置

```python
from aury.boot.infrastructure.mq import MQManager

# 获取实例
mq = MQManager.get_instance()
orders_mq = MQManager.get_instance("orders")

# Redis 后端
mq.configure(
    backend="redis",
    url="redis://localhost:6379/0",
    max_connections=10
)

# RabbitMQ 后端
mq.configure(
    backend="rabbitmq",
    url="amqp://guest:guest@localhost:5672/",
    prefetch_count=10
)

await mq.initialize()
```

### 生产者

```python
# 发送消息
await mq.publish(
    queue="orders",
    message={"order_id": "123", "action": "created"}
)

# 批量发送
await mq.publish_batch(
    queue="orders",
    messages=[
        {"order_id": "1", "action": "created"},
        {"order_id": "2", "action": "updated"},
    ]
)
```

### 消费者

```python
# 消费消息
async def process_order(message: dict):
    print(f"处理订单: {message['order_id']}")

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

---

## 事件总线 (Events)

重构后的事件总线支持多后端和多实例。

### 配置

```python
from aury.boot.infrastructure.events import EventBusManager

# 获取实例
bus = EventBusManager.get_instance()
domain_bus = EventBusManager.get_instance("domain")

# Memory 后端（单进程）
bus.configure(backend="memory")

# Redis Pub/Sub 后端
bus.configure(
    backend="redis",
    url="redis://localhost:6379/0",
    key_prefix="events:"
)

# RabbitMQ 后端
bus.configure(
    backend="rabbitmq",
    url="amqp://guest:guest@localhost:5672/",
    exchange_name="app.events",
    exchange_type="topic"
)

await bus.initialize()
```

### 定义事件

```python
from aury.boot.infrastructure.events import Event

class OrderCreatedEvent(Event):
    order_id: str
    amount: float
    user_id: str
    
    @property
    def event_name(self) -> str:
        return "order.created"
```

### 发布和订阅

```python
# 订阅事件
@bus.subscribe(OrderCreatedEvent)
async def on_order_created(event: OrderCreatedEvent):
    print(f"订单创建: {event.order_id}")

# 发布事件
await bus.publish(OrderCreatedEvent(
    order_id="123",
    amount=99.99,
    user_id="user_1"
))
```

### 旧 API 兼容

为保持向后兼容，原有的 `EventBus` API 仍可使用：

```python
from aury.boot.infrastructure.events import EventBus

bus = EventBus.get_instance()

@bus.subscribe(OrderCreatedEvent)
async def handler(event):
    pass

await bus.publish(event)
```

---

## 环境变量配置汇总

```bash
# =============================================================================
# 缓存 (CACHE__)
# =============================================================================
CACHE__CACHE_TYPE=redis
CACHE__URL=redis://localhost:6379/0
CACHE__SESSION__CACHE_TYPE=redis
CACHE__SESSION__URL=redis://localhost:6379/2

# =============================================================================
# 流式通道 (CHANNEL__)
# =============================================================================
CHANNEL__BACKEND=memory
CHANNEL__DEFAULT__BACKEND=redis
CHANNEL__DEFAULT__URL=redis://localhost:6379/3
CHANNEL__DEFAULT__KEY_PREFIX=channel:
CHANNEL__DEFAULT__TTL=86400

# =============================================================================
# 消息队列 (MQ__)
# =============================================================================
MQ__BACKEND=redis
MQ__DEFAULT__URL=redis://localhost:6379/4
MQ__ORDERS__BACKEND=rabbitmq
MQ__ORDERS__URL=amqp://guest:guest@localhost:5672/

# =============================================================================
# 事件总线 (EVENT__)
# =============================================================================
EVENT__BACKEND=memory
EVENT__DEFAULT__BACKEND=redis
EVENT__DEFAULT__URL=redis://localhost:6379/5
EVENT__DOMAIN__BACKEND=rabbitmq
EVENT__DOMAIN__URL=amqp://guest:guest@localhost:5672/
EVENT__DOMAIN__EXCHANGE_NAME=domain.events
```

---

## Manager 链式调用

所有 Manager 都支持链式调用：

```python
# 数据库
await DatabaseManager.get_instance().configure(url=...).initialize()

# 缓存
await CacheManager.get_instance().init_app(config).initialize()

# 存储
await StorageManager.get_instance().init(config)

# 调度器
await SchedulerManager.get_instance().initialize()

# 任务队列
await TaskManager.get_instance().initialize()

# Channel
await ChannelManager.get_instance("sse").initialize(backend="memory")

# MQ
await MQManager.get_instance().configure(...).initialize()

# EventBus
await EventBusManager.get_instance().configure(...).initialize()
```

---

## 健康检查

所有组件都支持健康检查，自动集成到 `/api/health` 端点：

```python
# 手动健康检查
is_healthy = await RedisClient.get_instance().health_check()
is_healthy = await RabbitMQClient.get_instance().health_check()
is_healthy = await ChannelManager.get_instance().health_check()
is_healthy = await MQManager.get_instance().health_check()
is_healthy = await EventBusManager.get_instance().health_check()
```

---

**总结**：新的基础设施模块提供了统一的多实例管理、链式配置和健康检查能力，适用于从单体应用到分布式微服务的各种场景。

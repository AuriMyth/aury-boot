# 事件总线（Events）

支持 `memory`、`redis`、`rabbitmq` 后端的事件发布订阅系统。

## 15.1 定义事件

**文件**: `{package_name}/events/__init__.py`

```python
from aury.boot.infrastructure.events import Event


class OrderCreatedEvent(Event):
    \"\"\"订单创建事件。\"\"\"
    order_id: str
    amount: float
    user_id: str
    
    @property
    def event_name(self) -> str:
        return "order.created"


class UserRegisteredEvent(Event):
    \"\"\"用户注册事件。\"\"\"
    user_id: str
    email: str
    
    @property
    def event_name(self) -> str:
        return "user.registered"
```

### 15.1.1 事件初始化

事件类基于 Pydantic BaseModel，支持以下初始化方式：

```python
# 方式 1：关键字参数（推荐）
event = OrderCreatedEvent(
    order_id="order-123",
    amount=99.99,
    user_id="user-456",
)

# 方式 2：字典解包
event = OrderCreatedEvent(**{{
    "order_id": "order-123",
    "amount": 99.99,
    "user_id": "user-456",
}})

# 方式 3：从实体创建
event = OrderCreatedEvent(
    order_id=str(order.id),
    amount=order.amount,
    user_id=str(order.user_id),
)
```

## 15.2 订阅事件

```python
from aury.boot.infrastructure.events import EventBusManager

bus = EventBusManager.get_instance()


@bus.subscribe(OrderCreatedEvent)
async def on_order_created(event: OrderCreatedEvent):
    \"\"\"处理订单创建事件。\"\"\"
    logger.info(f"订单创建: {{event.order_id}}, 金额: {{event.amount}}")
    # 发送通知、更新统计等...


@bus.subscribe(UserRegisteredEvent)
async def send_welcome_email(event: UserRegisteredEvent):
    \"\"\"发送欢迎邮件。\"\"\"
    await email_service.send_welcome(event.email)
```

## 15.3 发布事件

```python
from {package_name}.events import OrderCreatedEvent

@router.post("/orders")
async def create_order(request: OrderCreateRequest):
    # 创建订单
    order = await order_service.create(request)
    
    # 发布事件
    await bus.publish(OrderCreatedEvent(
        order_id=order.id,
        amount=order.amount,
        user_id=order.user_id
    ))
    
    return BaseResponse(code=200, message="订单创建成功", data=order)
```

## 15.4 多实例（EventBusManager）

```python
from aury.boot.infrastructure.events import EventBusManager

# 获取实例
bus = EventBusManager.get_instance()
domain_bus = EventBusManager.get_instance("domain")

# Memory 后端（单进程）
await bus.initialize(backend="memory")

# Redis Pub/Sub 后端
await bus.initialize(
    backend="redis",
    url="redis://localhost:6379/0",
    channel_prefix="events:",
)

# RabbitMQ 后端
await bus.initialize(
    backend="rabbitmq",
    url="amqp://guest:guest@localhost:5672/",
    exchange_name="app.events",
)
```

## 15.5 环境变量

```bash
# 默认实例
EVENT_BACKEND=memory

# 多实例（格式：EVENT_{{INSTANCE}}_{{FIELD}}）
EVENT_DEFAULT_BACKEND=redis
EVENT_DEFAULT_URL=redis://localhost:6379/5
EVENT_DOMAIN_BACKEND=rabbitmq
EVENT_DOMAIN_URL=amqp://guest:guest@localhost:5672/
EVENT_DOMAIN_EXCHANGE_NAME=domain.events
```

## 15.6 最佳实践

1. **事件应该是不可变的** - 使用 Pydantic 的 `frozen=True`
2. **订阅者应该快速完成** - 耗时操作使用任务队列
3. **避免循环事件** - 不要在订阅者中发布相同类型的事件

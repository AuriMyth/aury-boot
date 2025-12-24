# 14. 事件驱动架构详解

请参考 [00-quick-start.md](./00-quick-start.md) 第 14 章的基础用法。

## 事件定义

### 基础事件

```python
from aury.boot.infrastructure.events import Event

class OrderCreatedEvent(Event):
    """订单创建事件"""
    order_id: str
    amount: float
    user_id: str
    
    @property
    def event_name(self) -> str:
        return "order.created"
```

### 事件字段

```python
from datetime import datetime
from pydantic import Field

class OrderUpdatedEvent(Event):
    """订单更新事件"""
    order_id: str
    old_status: str
    new_status: str
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def event_name(self) -> str:
        return "order.updated"
```

## 事件订阅

### 基础订阅

```python
from aury.boot.infrastructure.events.bus import EventBus

bus = EventBus.get_instance()

@bus.subscribe(OrderCreatedEvent)
async def on_order_created(event: OrderCreatedEvent):
    """订单创建时的处理"""
    logger.info(f"订单创建: {event.order_id}, 金额: {event.amount}")
    
    # 发送通知
    await notification_service.notify(
        user_id=event.user_id,
        title="订单已创建",
        message=f"订单金额: ¥{event.amount}"
    )
```

### 多个订阅者

```python
# 订阅者 1: 发送邮件
@bus.subscribe(OrderCreatedEvent)
async def send_order_email(event: OrderCreatedEvent):
    user = await db.get_user(event.user_id)
    await email_service.send(
        to=user.email,
        subject="订单确认",
        template="order_confirmation",
        context={"order": event}
    )

# 订阅者 2: 更新统计
@bus.subscribe(OrderCreatedEvent)
async def update_statistics(event: OrderCreatedEvent):
    await analytics.record_event(
        event_type="order.created",
        amount=event.amount
    )

# 订阅者 3: 触发后续流程
@bus.subscribe(OrderCreatedEvent)
async def trigger_payment(event: OrderCreatedEvent):
    await payment_service.initiate_payment(
        order_id=event.order_id,
        amount=event.amount
    )
```

### 条件订阅

```python
@bus.subscribe(OrderCreatedEvent)
async def process_high_value_orders(event: OrderCreatedEvent):
    # 只处理高价值订单
    if event.amount >= 10000:
        logger.info(f"高价值订单: {event.order_id}")
        await vip_service.process(event.order_id)
```

## 事件发布

### 基础发布

```python
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

### 事件链

```python
# 事件 1: 订单创建
@router.post("/orders")
async def create_order(request: OrderCreateRequest):
    order = await order_service.create(request)
    await bus.publish(OrderCreatedEvent(...))
    return order

# 订阅者发布新事件
@bus.subscribe(OrderCreatedEvent)
async def on_order_created(event: OrderCreatedEvent):
    # 处理订单创建
    await process_order(event.order_id)
    
    # 发布后续事件
    await bus.publish(OrderProcessingStartedEvent(
        order_id=event.order_id,
        started_at=datetime.now()
    ))
```

## 常见模式

### 用户生命周期

```python
class UserRegisteredEvent(Event):
    user_id: str
    email: str
    @property
    def event_name(self) -> str:
        return "user.registered"

class UserActivatedEvent(Event):
    user_id: str
    @property
    def event_name(self) -> str:
        return "user.activated"

# 注册后发送欢迎邮件
@bus.subscribe(UserRegisteredEvent)
async def send_welcome_email(event: UserRegisteredEvent):
    await email_service.send_welcome(event.email)

# 注册后创建用户档案
@bus.subscribe(UserRegisteredEvent)
async def create_profile(event: UserRegisteredEvent):
    await profile_service.create(event.user_id)

# 激活后奖励积分
@bus.subscribe(UserActivatedEvent)
async def award_signup_bonus(event: UserActivatedEvent):
    await points_service.add_points(event.user_id, 100)
```

### 订单状态变更

```python
class PaymentSuccessfulEvent(Event):
    order_id: str
    @property
    def event_name(self) -> str:
        return "payment.successful"

# 支付成功后启动配送
@bus.subscribe(PaymentSuccessfulEvent)
async def start_shipping(event: PaymentSuccessfulEvent):
    await shipping_service.create_shipment(event.order_id)
    await bus.publish(ShippingStartedEvent(order_id=event.order_id))

# 配送完成后留言提醒
class ShippingCompletedEvent(Event):
    order_id: str
    @property
    def event_name(self) -> str:
        return "shipping.completed"

@bus.subscribe(ShippingCompletedEvent)
async def request_review(event: ShippingCompletedEvent):
    order = await db.get_order(event.order_id)
    await notification_service.remind_review(order.user_id, event.order_id)
```

### 库存管理

```python
class ProductSoldEvent(Event):
    product_id: str
    quantity: int
    @property
    def event_name(self) -> str:
        return "product.sold"

# 更新库存
@bus.subscribe(ProductSoldEvent)
async def update_inventory(event: ProductSoldEvent):
    await inventory_service.decrease(event.product_id, event.quantity)

# 库存不足时预警
@bus.subscribe(ProductSoldEvent)
async def check_low_stock(event: ProductSoldEvent):
    stock = await inventory_service.get_stock(event.product_id)
    if stock < 10:
        await alert_service.send_admin_alert(
            f"产品 {event.product_id} 库存不足: {stock}"
        )

# 库存为零时通知
@bus.subscribe(ProductSoldEvent)
async def notify_if_outofstock(event: ProductSoldEvent):
    stock = await inventory_service.get_stock(event.product_id)
    if stock == 0:
        await notification_service.notify_outofstock(event.product_id)
```

## 错误处理

### 异常处理

```python
@bus.subscribe(OrderCreatedEvent)
async def safe_subscriber(event: OrderCreatedEvent):
    try:
        await external_service.process(event)
    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)
        # 记录错误，但不阻塞其他订阅者
```

### 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_fixed

@bus.subscribe(OrderCreatedEvent)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def retry_subscriber(event: OrderCreatedEvent):
    # 自动重试，最多 3 次，间隔 2 秒
    await unreliable_service.process(event)
```

## 事件配置

### 后端类型

事件总线支持三种后端：

- `memory` - 单进程内存（默认，开发用）
- `redis` - Redis Pub/Sub（多进程/分布式）
- `rabbitmq` - RabbitMQ（生产推荐）

### 环境变量

```bash
# 后端类型
EVENT_BACKEND=memory

# Redis 后端
EVENT_BACKEND=redis
EVENT_URL=redis://localhost:6379/0
EVENT_KEY_PREFIX=events:

# RabbitMQ 后端
EVENT_BACKEND=rabbitmq
EVENT_URL=amqp://guest:guest@localhost:5672/
EVENT_EXCHANGE_NAME=aury.events
EVENT_EXCHANGE_TYPE=topic
```

### 多实例配置

支持多实例，环境变量格式：`EVENT_{INSTANCE}_{FIELD}`

```bash
# 默认实例
EVENT_DEFAULT_BACKEND=redis
EVENT_DEFAULT_URL=redis://localhost:6379/5

# domain 实例
EVENT_DOMAIN_BACKEND=rabbitmq
EVENT_DOMAIN_URL=amqp://guest:guest@localhost:5672/
EVENT_DOMAIN_EXCHANGE_NAME=domain.events
```

### 代码中配置（EventBusManager）

```python
from aury.boot.infrastructure.events import EventBusManager

# 获取实例
bus = EventBusManager.get_instance()
domain_bus = EventBusManager.get_instance("domain")

# 配置
bus.configure(
    backend="redis",
    url="redis://localhost:6379/0",
    key_prefix="events:"
)

await bus.initialize()
```

## 监控和调试

### 事件追踪

```python
from aury.boot.common.logging import get_trace_id, logger

@bus.subscribe(OrderCreatedEvent)
async def traced_subscriber(event: OrderCreatedEvent):
    trace_id = get_trace_id()
    logger.info(f"处理事件: {event.event_name}, Trace-ID: {trace_id}")
    
    await process_event(event)
    
    logger.info(f"事件处理完成: {event.event_name}, Trace-ID: {trace_id}")
```

## 最佳实践

### 1. 事件应该是不可变的

```python
# ❌ 不好 - 事件可变
class BadEvent(Event):
    data: dict  # 可以被修改
    
    @property
    def event_name(self) -> str:
        return "bad.event"

# ✅ 好 - 事件不可变
from pydantic import Field

class GoodEvent(Event):
    data: dict = Field(frozen=True)
    
    @property
    def event_name(self) -> str:
        return "good.event"
```

### 2. 订阅者应该快速完成

```python
# ❌ 慢 - 订阅者阻塞
@bus.subscribe(OrderCreatedEvent)
async def slow_subscriber(event: OrderCreatedEvent):
    await very_slow_report_generation(event)

# ✅ 快 - 使用任务队列处理
@bus.subscribe(OrderCreatedEvent)
async def fast_subscriber(event: OrderCreatedEvent):
    # 发送任务到队列
    await task_queue.send(process_report_task, order_id=event.order_id)
```

### 3. 避免循环事件

```python
# ❌ 可能导致循环
@bus.subscribe(OrderCreatedEvent)
async def circular_subscriber(event: OrderCreatedEvent):
    await bus.publish(OrderCreatedEvent(...))  # 发布相同事件

# ✅ 避免循环
@bus.subscribe(OrderCreatedEvent)
async def safe_subscriber(event: OrderCreatedEvent):
    # 发布不同的事件
    await bus.publish(OrderProcessingStartedEvent(order_id=event.order_id))
```

---

**总结**：事件驱动架构可以实现系统解耦，提高可维护性。合理设计事件和订阅者，可以构建灵活、可扩展的微服务系统。

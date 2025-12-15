# 20. 最佳实践完全指南

## 1. 架构设计

### 分层原则

遵循标准的三层架构：

```
API 层 ────→ Service 层 ────→ Repository 层 ────→ Database
           （业务逻辑）     （数据访问）
```

**每层的职责**：

- **API 层**：
  - HTTP 请求处理和参数验证
  - 调用 Service 执行业务逻辑
  - 错误处理和响应格式化
  - 不包含业务逻辑

- **Service 层**：
  - 业务逻辑实现
  - 事务管理
  - 跨 Repository 操作协调
  - 不包含 HTTP 相关代码

- **Repository 层**：
  - 数据访问实现
  - 查询优化
  - 不包含业务逻辑

### 代码示例

```python
# ❌ 反模式：业务逻辑在 API 层
@router.post("/orders")
async def create_order(request: OrderRequest, session=Depends(...)):
    order = await session.query(Order).filter(...).first()
    if order.total > 1000:
        order.discount = 0.1
    order.final_price = order.total * (1 - order.discount)
    session.add(order)
    await session.commit()

# ✅ 正确做法
from aury.boot.application.interfaces.egress import BaseResponse

@router.post("/orders")
async def create_order(
    request: OrderRequest,
    service: OrderService = Depends(get_order_service)
):
    order = await service.create_with_discount(request)
    return BaseResponse(code=200, message="订单创建成功", data=order)

class OrderService:
    def __init__(self, repo: OrderRepository):
        self.repo = repo
    
    async def create_with_discount(self, request: OrderRequest):
        order = await self.repo.create({
            "total": request.total,
            "discount": self.calculate_discount(request.total)
        })
        order.final_price = order.total * (1 - order.discount)
        return order
    
    def calculate_discount(self, total: float) -> float:
        if total > 1000:
            return 0.1
        return 0
```

## 2. 数据库性能

### 避免 N+1 查询

```python
# ❌ N+1 查询问题
users = await repo.list()  # 1 次查询
for user in users:
    posts = await post_repo.list(author_id=user.id)  # N 次查询

# ✅ 使用 selectinload
from sqlalchemy.orm import selectinload
from sqlalchemy import select

stmt = select(User).options(selectinload(User.posts))
result = await session.execute(stmt)
users = result.scalars().all()  # 只需 1-2 次查询
```

### 查询优化清单

- [ ] 使用 `selectinload()` 或 `joinedload()` 处理关系
- [ ] 添加索引到频繁查询的列
- [ ] 使用 `limit` 和 `offset` 分页，避免一次加载所有数据
- [ ] 使用 `only()` 仅查询需要的列
- [ ] 避免在循环中执行查询
- [ ] 使用数据库视图处理复杂查询
- [ ] 启用 `DATABASE_ECHO=false`（生产环境）

### 连接池配置

```bash
# 开发环境
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# 生产环境（根据并发量调整）
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_RECYCLE=3600  # 一小时回收连接
```

## 3. 依赖注入最佳实践

### 依赖单例 vs 作用域

```python
# SINGLETON：数据库连接池、缓存、配置
container.register_singleton(DatabaseManager)
container.register_singleton(CacheManager)
container.register_singleton(BaseConfig)

# SCOPED：数据库会话（每个请求一个）
container.register_scoped(DatabaseSession)

# TRANSIENT：Service（无状态）
container.register_transient(UserService)
container.register_transient(OrderService)
```

### 依赖接口，不依赖实现

```python
# ❌ 不好
class UserService:
    def __init__(self, repo: MySQLUserRepository):
        self.repo = repo

# ✅ 好
class UserService:
    def __init__(self, repo: IUserRepository):  # 依赖接口
        self.repo = repo

# 生产：注入 MySQLUserRepository
# 测试：注入 MockUserRepository
```

## 4. 错误处理

### 使用结构化异常

```python
from aury.boot.application.errors import (
    NotFoundError,
    AlreadyExistsError,
    UnauthorizedError,
    ForbiddenError,
)

# ❌ 使用通用 Exception
raise Exception("用户不存在")

# ✅ 使用具体异常
raise NotFoundError("用户不存在")

# 框架自动转换为：
# {
#   "code": 404,
#   "message": "用户不存在",
#   "error_code": "NOT_FOUND",
#   "timestamp": "..."
# }
```

### 错误代码管理

```python
# 定义错误代码常量
ERROR_USER_NOT_FOUND = "USER_NOT_FOUND"
ERROR_EMAIL_DUPLICATE = "EMAIL_DUPLICATE"
ERROR_PASSWORD_WEAK = "PASSWORD_WEAK"

# 在异常中使用
raise NotFoundError(
    message="用户不存在",
    error_code=ERROR_USER_NOT_FOUND
)
```

## 5. 并发和性能

### 使用异步操作

```python
# ❌ 阻塞操作
response = requests.get("http://api.example.com")  # 阻塞

# ✅ 异步操作
async with aiohttp.ClientSession() as session:
    async with session.get("http://api.example.com") as resp:
        data = await resp.json()
```

### 批量操作

```python
# ❌ 循环创建（N 个数据库操作）
for item in items:
    await repo.create(item)

# ✅ 批量创建（1 个数据库操作）
await repo.bulk_create(items, batch_size=1000)
```

### 缓存策略

```python
# 缓存热数据
@cache.cached(expire=3600, key_prefix="user_profile")
async def get_user_profile(user_id: str):
    return await db.get_user(user_id)

# 缓存列表
@cache.cached(expire=300, key_prefix="user_list")
async def list_active_users():
    return await db.list_users(is_active=True)

# 缓存失效
await cache.delete(f"user_profile:{user_id}")
```

## 6. 日志和监控

### 结构化日志

```python
from aury.boot.common.logging import logger

# ✅ 好的日志
logger.info("用户登录成功", extra={
    "user_id": user.id,
    "ip": request.client.host,
    "user_agent": request.headers.get("user-agent")
})

# ❌ 不好的日志
logger.info(f"User {user.id} logged in from {request.client.host}")
```

### 分布式追踪

```python
from aury.boot.common.logging import get_trace_id, logger

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    trace_id = get_trace_id()
    logger.info(f"获取用户 {user_id}")
    
    # 所有日志自动包含 trace_id
    # 跨服务调用时 trace_id 自动传递
    user = await service.get_user(user_id)
    
    logger.info(f"获取成功")
    return user
```

### 性能监控

```python
from aury.boot.common.logging import log_performance

@log_performance(threshold=0.5)  # 超过 0.5 秒记录警告
async def slow_operation():
    await expensive_query()
```

## 7. 测试最佳实践

### 单元测试

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_get_user():
    # 创建 Mock 仓储
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get.return_value = {"id": "1", "username": "test"}
    
    # 注入 Mock
    service = UserService(mock_repo)
    
    # 测试
    result = await service.get_user("1")
    
    assert result["username"] == "test"
    mock_repo.get.assert_called_once_with("1")
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_create_user_integration(db_session):
    # 使用真实数据库会话
    repo = UserRepository(db_session)
    service = UserService(repo)
    
    # 创建用户
    user = await service.create({
        "username": "testuser",
        "email": "test@example.com"
    })
    
    assert user.id is not None
    assert user.username == "testuser"
```

## 8. 微服务通信

### RPC 调用最佳实践

```python
from aury.boot.application.rpc.client import create_rpc_client

@app.get("/orders/{order_id}")
async def get_order_details(order_id: str):
    # 本地服务
    order = await order_service.get_order(order_id)
    
    # 调用用户服务
    user_client = create_rpc_client(service_name="user-service")
    user = await user_client.get(f"/api/users/{order.user_id}")
    
    # 调用支付服务
    payment_client = create_rpc_client(service_name="payment-service")
    payment = await payment_client.get(f"/api/payments/{order.payment_id}")
    
    return {
        "order": order,
        "user": user.data,
        "payment": payment.data
    }
```

### 服务发现

```bash
# 方式 1：显式映射
RPC_CLIENT_SERVICES={"user-service": "http://10.0.0.5:8000", "payment-service": "http://10.0.0.6:8000"}

# 方式 2：DNS 自动解析（Kubernetes）
# user-service 自动解析到 http://user-service:8000
```

## 9. 部署最佳实践

### 环境隔离

```bash
# 开发环境
LOG_LEVEL=DEBUG
DATABASE_POOL_SIZE=5
CACHE_TYPE=memory

# 生产环境
LOG_LEVEL=INFO
DATABASE_POOL_SIZE=20
CACHE_TYPE=redis
```

### 健康检查

```python
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "database": await check_database(),
        "cache": await check_cache(),
        "timestamp": datetime.utcnow()
    }
```

### 优雅关闭

```python
@app.on_event("shutdown")
async def shutdown_event():
    # 等待现有请求完成
    # 关闭数据库连接
    # 关闭缓存连接
    logger.info("应用已关闭")
```

## 10. 代码审查清单

- [ ] 是否有未处理的异常？
- [ ] 是否避免了 N+1 查询？
- [ ] 是否有内存泄漏（长连接未关闭）？
- [ ] 是否有 SQL 注入风险（使用 ORM 参数化查询）？
- [ ] 是否有竞态条件？
- [ ] 是否有适当的日志和监控？
- [ ] 是否有单元测试？
- [ ] 是否有 API 文档？
- [ ] 是否有性能优化空间？
- [ ] 是否符合命名规范？

## 下一步

- 参考 [05-di-container-complete.md](./05-di-container-complete.md) 优化依赖注入
- 参考 [06-components-detailed.md](./06-components-detailed.md) 优化组件管理
- 参考 [09-database-complete.md](./09-database-complete.md) 优化数据库查询


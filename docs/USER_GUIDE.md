# AuriMyth Foundation Kit 用户开发手册 (User Guide)

欢迎使用 AuriMyth Foundation Kit！这是一款专为构建现代化、高性能微服务而设计的 Python 基础设施框架。本手册将引导你从零开始，逐步掌握如何使用该框架开发生产级应用。

## 目录 (Table of Contents)

1.  [简介 (Introduction)](#1-简介-introduction)
2.  [快速上手 (Quick Start)](#2-快速上手-quick-start)
3.  [项目结构推荐 (Project Structure)](#3-项目结构推荐-project-structure)
4.  [配置详解 (Configuration)](#4-配置详解-configuration)
5.  [应用组件系统 (Application Components)](#5-应用组件系统-application-components)
6.  [HTTP 接口定义 (HTTP Interfaces)](#6-http-接口定义-http-interfaces)
7.  [错误处理系统 (Error Handling)](#7-错误处理系统-error-handling)
8.  [中间件系统 (Middleware)](#8-中间件系统-middleware)
9.  [数据库与模型 (Database & Models)](#9-数据库与模型-database--models)
10. [缓存系统 (Cache System)](#10-缓存系统-cache-system)
11. [异步任务 (Asynchronous Tasks)](#11-异步任务-asynchronous-tasks)
12. [事件驱动 (Event Driven)](#12-事件驱动-event-driven)
13. [定时调度 (Scheduler)](#13-定时调度-scheduler)
14. [RPC 与服务发现 (RPC & Service Discovery)](#14-rpc-与服务发现-rpc--service-discovery)
15. [WebSocket 长连接 (WebSocket)](#15-websocket-长连接-websocket)
16. [对象存储 (Object Storage)](#16-对象存储-object-storage)
17. [国际化 (i18n)](#17-国际化-i18n)
18. [数据库迁移 (Database Migration)](#18-数据库迁移-database-migration)

---

## 1. 简介 (Introduction)

AuriMyth Foundation Kit 不是为了替代 FastAPI，而是作为其**增强层**，提供了构建微服务所需的"电池"：
*   **统一的组件管理**：自动处理数据库、缓存、任务队列的生命周期。
*   **标准化的分层架构**：Domain/Infrastructure 分离，Repository 模式开箱即用。
*   **无痛的微服务能力**：服务发现、RPC 调用、分布式事件总线只需几行配置。

---

## 2. 快速上手 (Quick Start)

### 2.1 安装

推荐使用 [uv](https://github.com/astral-sh/uv) 极速安装：

```bash
# 创建并进入项目目录
uv init my-service
cd my-service

# 安装完整功能包
uv add "aurimyth-foundation-kit[all]"
```

### 2.2 Hello World

创建 `main.py`：

```python
from aurimyth.foundation_kit.application.app.base import FoundationApp
from aurimyth.foundation_kit.application.config import BaseConfig

# 1. 定义配置（继承 BaseConfig）
class AppConfig(BaseConfig):
    pass

# 2. 初始化应用
app = FoundationApp(
    title="Demo Service",
    version="0.1.0",
    config=AppConfig()
)

@app.get("/")
def hello():
    return {"message": "Hello AuriMyth!"}

# 3. 运行 (uvicorn)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

运行服务：
```bash
uv run python main.py
```

---

## 3. 项目结构推荐 (Project Structure)

为了保持代码整洁，推荐遵循以下分层结构：

```
my_service/
├── app/
│   ├── __init__.py
│   ├── api/                # 接口层 (Controllers/Routers)
│   │   └── v1/
│   │       └── users.py
│   ├── config.py           # 配置定义
│   ├── main.py             # 入口文件
│   ├── domain/             # 领域层 (业务核心)
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务逻辑
│   └── infrastructure/     # 基础设施层
│       └── repository/     # 数据访问实现
├── alembic/                # 数据库迁移脚本
├── .env                    # 环境变量配置
└── pyproject.toml
```

---

## 4. 配置详解 (Configuration)

### 4.1 配置架构

框架采用**分层配置**设计：
- **Application 层** (`BaseConfig`): 应用级配置
  - `DatabaseSettings`: 应用使用的数据库配置
  - `CacheSettings`: 缓存配置
  - `ServerSettings`: 服务器配置
  - `ServiceSettings`: 服务类型配置
  - `SchedulerSettings`: 调度器配置
  - 等等...
  
- **Infrastructure 层** (`DatabaseConfig`, `TaskConfig`, `EventConfig`): 内部使用的配置
  - 仅在内部模块中使用（DatabaseManager、TaskManager、EventBus）
  - 应用层不直接依赖

### 4.2 基础环境变量表

| 类别 | 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| **Server** | `SERVER_HOST` | 127.0.0.1 | 监听地址 |
| | `SERVER_PORT` | 8000 | 监听端口 |
| | `SERVER_WORKERS` | 1 | 工作进程数 |
| **Log** | `LOG_LEVEL` | INFO | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| | `LOG_FILE` | (None) | 日志文件路径 |
| **Database** | `DATABASE_URL` | (None) | 数据库连接串 |
| | `DATABASE_ECHO` | False | 是否打印 SQL |
| | `DATABASE_POOL_SIZE` | 5 | 连接池大小 |
| **Cache** | `CACHE_TYPE` | memory | 缓存后端 (memory/redis/memcached) |
| | `CACHE_REDIS_URL` | (None) | Redis 连接串 |
| **Service** | `SERVICE_TYPE` | api | 服务运行模式 (api/worker/scheduler) |
| **Scheduler** | `SCHEDULER_MODE` | embedded | 调度器模式 (embedded/standalone/disabled) |
| **Task** | `TASK_BROKER_URL` | redis://localhost:6379/0 | 任务队列代理 URL |
| **Event** | `EVENT_BROKER_URL` | (None) | 事件总线代理 URL（None 时使用本地模式）|
| **RPC** | `RPC_CLIENT_SERVICES` | {} | 服务地址映射 JSON |

### 4.3 服务类型 (Service Type)

*   `api`: 启动 Web 服务器，处理 HTTP 请求（默认嵌入调度器）。
*   `worker`: 启动任务队列消费者，不处理 HTTP。
*   `scheduler`: 启动独立调度器进程（也可在 `api` 模式下共用）。

### 4.4 调度器模式 (Scheduler Mode)

仅在 `SERVICE_TYPE=api` 时有效：
- `embedded`: 在 API 进程中运行调度器（默认）
- `standalone`: 调度器在独立进程中运行
- `disabled`: 禁用调度器

当 `SERVICE_TYPE=scheduler` 时，会启动一个独立的调度器进程，此配置无效。

### 4.5 自定义配置

```python
from aurimyth.foundation_kit.application.config import BaseConfig
from pydantic import Field

class MyAppConfig(BaseConfig):
    """自定义应用配置"""
    
    # 添加自定义配置项
    custom_field: str = Field(default="value", description="自定义字段")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }
```

---

## 5. 应用组件系统 (Application Components)

### 5.1 什么是组件

组件是框架的**生命周期管理单位**，负责：
- 初始化基础设施（数据库、缓存、任务队列）
- 管理资源的创建和销毁
- 依赖注入和配置

### 5.2 内置组件

框架提供了以下内置组件：

```python
from aurimyth.foundation_kit.application import (
    DatabaseComponent,      # 数据库连接管理
    CacheComponent,         # 缓存系统
    TaskComponent,          # 异步任务队列
    RequestLoggingComponent, # HTTP 请求日志
    SchedulerComponent,     # 定时任务调度器
)

app = FoundationApp(config=MyAppConfig())

# 添加组件 (应用启动时自动初始化)
app.add_component(DatabaseComponent())
app.add_component(CacheComponent())
app.add_component(TaskComponent())
```

### 5.3 创建自定义组件

```python
from aurimyth.foundation_kit.application.app.base import Component

class MyCustomComponent(Component):
    """自定义组件示例"""
    
    async def on_startup(self):
        """应用启动时执行"""
        print("组件启动...")
        # 初始化资源
    
    async def on_shutdown(self):
        """应用关闭时执行"""
        print("组件关闭...")
        # 清理资源
```

---

## 6. HTTP 接口定义 (HTTP Interfaces)

### 6.1 请求模型 (Ingress)

框架提供了标准化的请求模型：

```python
from aurimyth.foundation_kit.application.interfaces.ingress import (
    BaseRequest,
    PaginationRequest,
    ListRequest,
    FilterRequest,
    SortOrder,
)

# 分页请求
class UserListRequest(PaginationRequest):
    """用户列表请求"""
    search: str | None = None  # 搜索关键词
    sort: str = "created_at"   # 排序字段
    order: SortOrder = SortOrder.DESC  # 排序方向

# 使用示例
@router.get("/users")
async def list_users(request: UserListRequest):
    # request.page, request.size, request.skip, request.limit 等属性
    return {"page": request.page, "size": request.size}
```

### 6.2 响应模型 (Egress)

框架提供了标准化的响应模型：

```python
from aurimyth.foundation_kit.application.interfaces.egress import (
    BaseResponse,
    ErrorResponse,
    SuccessResponse,
    PaginationResponse,
    Pagination,
    ResponseBuilder,
)

# 成功响应
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await repo.get(user_id)
    return ResponseBuilder.success("获取用户成功", data=user)

# 分页响应
@router.get("/users")
async def list_users(page: int = 1, size: int = 20):
    total, items = await repo.paginate(page=page, size=size)
    return PaginationResponse(
        code=200,
        message="获取用户列表成功",
        data=Pagination(
            total=total,
            items=items,
            page=page,
            size=size,
        )
    )

# 错误响应
@router.post("/users")
async def create_user(request: CreateUserRequest):
    if not request.email:
        return ResponseBuilder.fail(
            message="邮箱不能为空",
            code=400,
            error_code="INVALID_EMAIL"
        )
    # ...
```

---

## 7. 错误处理系统 (Error Handling)

### 7.1 异常体系

框架提供了结构化的异常体系：

```python
from aurimyth.foundation_kit.application.errors import (
    BaseError,          # 基础错误
    BusinessError,      # 业务错误
    ValidationError,    # 验证错误
    NotFoundError,      # 未找到错误
    AlreadyExistsError, # 已存在错误
    UnauthorizedError,  # 未授权错误
    ForbiddenError,     # 禁止访问错误
    DatabaseError,      # 数据库错误
    VersionConflictError, # 版本冲突错误（乐观锁）
)

# 使用示例
from aurimyth.foundation_kit.application.errors import NotFoundError, AlreadyExistsError

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await repo.get(user_id)
    if not user:
        raise NotFoundError(f"用户 {user_id} 不存在")
    return user

@router.post("/users")
async def create_user(request: CreateUserRequest):
    existing = await repo.get_by(email=request.email)
    if existing:
        raise AlreadyExistsError(f"邮箱 {request.email} 已被使用")
    # ...
```

### 7.2 错误代码管理

```python
from aurimyth.foundation_kit.application.errors import ErrorCode

# 预定义错误代码
ERROR_USER_NOT_FOUND = ErrorCode(
    code="USER_NOT_FOUND",
    message="用户未找到",
    http_status=404,
)

# 使用错误代码抛出异常
raise NotFoundError(
    message="用户不存在",
    error_code=ERROR_USER_NOT_FOUND.code,
    metadata={"user_id": user_id}
)
```

### 7.3 全局错误处理

框架自动处理异常并返回标准化的错误响应：

```json
{
  "code": 404,
  "message": "用户不存在",
  "error_code": "USER_NOT_FOUND",
  "details": {
    "user_id": "123"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## 8. 组件系统 (Components)

框架使用组件系统来管理中间件和其他基础设施。所有内置组件都会在应用启动时自动加载。

### 8.1 内置组件

框架提供了以下内置组件：

| 组件名 | 说明 | 启用条件 |
|--------|------|--------|
| `REQUEST_LOGGING` | 请求日志中间件 | 默认启用 |
| `CORS` | CORS 跨域中间件 | 配置了 origins |
| `DATABASE` | 数据库管理 | 配置了 database.url |
| `CACHE` | 缓存系统 | 配置了 cache.cache_type |
| `TASK_QUEUE` | 任务队列（Worker 模式） | 是 Worker 且配置了 broker_url |
| `SCHEDULER` | 定时调度器（嵌入式模式） | scheduler.mode = EMBEDDED |

### 8.2 请求日志组件

请求日志组件会自动记录所有 HTTP 请求的进入和离开：

```python
# 无需手动配置，组件会自动启用
# 查看日志输出
→ GET /api/v1/users | 客户端: 127.0.0.1 | User-Agent: curl/7.68.0
← GET /api/v1/users | 状态: 200 | 耗时: 0.123s
```

### 8.3 自定义组件

创建自定义组件：

```python
from aurimyth.foundation_kit.application.app.base import Component, FoundationApp
from aurimyth.foundation_kit.application.config import BaseConfig

class CustomComponent(Component):
    """自定义组件。"""
    
    name = "custom"
    enabled = True
    depends_on = []  # 依赖的其他组件名称
    
    def can_enable(self, config: BaseConfig) -> bool:
        """检查是否可以启用。"""
        return self.enabled and bool(config.custom_setting)
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化组件。"""
        # 初始化逻辑
        pass
    
    async def teardown(self, app: FoundationApp) -> None:
        """清理组件资源。"""
        # 清理逻辑
        pass
```

### 8.4 注册自定义组件

**方式一：创建自定义应用类**

```python
from aurimyth.foundation_kit.application.app.base import FoundationApp
from aurimyth.foundation_kit.application.app.components import (
    RequestLoggingComponent,
    CORSComponent,
    DatabaseComponent,
)

class MyApp(FoundationApp):
    """自定义应用。"""
    
    items = [
        RequestLoggingComponent,
        CORSComponent,
        DatabaseComponent,
        CustomComponent,  # 添加自定义组件
    ]

# 使用自定义应用
app = MyApp(config=config)
```

**方式二：动态添加组件实例**

```python
from aurimyth.foundation_kit.application.app.base import FoundationApp

app = FoundationApp(config=config)

# 在应用初始化后，可以直接添加到 items
app.items.append(CustomComponent)
# 然后重新注册组件
app._register_components()
```

### 8.5 中间件装饰器

如果需要在单个路由上记录日志，可以使用装饰器：

```python
from aurimyth.foundation_kit.application.middleware import log_request

@router.get("/users")
@log_request
async def list_users():
    return {"users": []}
```

### 8.6 自定义中间件

创建自定义中间件然后通过组件注册：

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from aurimyth.foundation_kit.application.app.base import Component, FoundationApp
from aurimyth.foundation_kit.application.config import BaseConfig

class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 请求前处理
        response = await call_next(request)
        # 响应后处理
        return response

# 通过组件包装自定义中间件
class CustomMiddlewareComponent(Component):
    name = "custom_middleware"
    enabled = True
    depends_on = []
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        app.add_middleware(CustomMiddleware)
    
    async def teardown(self, app: FoundationApp) -> None:
        pass

# 注册组件
FoundationApp.register_component(CustomMiddlewareComponent)
```

---

## 9. 数据库与模型 (Database & Models)

### 9.1 定义数据模型 (Defining Models)

在 `domain/models` 中定义模型。框架提供了 `Base` 类和跨数据库兼容的 `GUID` 类型。

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from aurimyth.foundation_kit.domain.models.base import Base, GUID
from uuid import uuid4

class User(Base):
    __tablename__ = "users"

    # 推荐使用 GUID 主键，自动兼容 Postgres/MySQL
    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=uuid4)
    
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Base 类已包含 created_at 和 updated_at
```

### 9.2 使用仓储 (Repository)

不要在 API 中直接写 SQL。使用 `BaseRepository` 可以获得标准 CRUD 能力。

```python
# infrastructure/repository/user_repo.py
from aurimyth.foundation_kit.domain.repository.impl import BaseRepository
from my_service.app.domain.models.user import User

class UserRepository(BaseRepository[User]):
    # 继承后直接获得: get, list, create, update, delete 等方法
    
    # 可扩展自定义查询
    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email)
```

### 9.3 分页与高级查询 (Pagination & Advanced Query)

`BaseRepository` 内置了强大的分页支持。

```python
# 在 API 路由中
from aurimyth.foundation_kit.domain.pagination import PaginationParams

@router.get("/users")
async def list_users(
    page: int = 1, 
    size: int = 20,
    repo: UserRepository = Depends(get_user_repo)
):
    # 自动处理分页参数
    params = PaginationParams(page=page, size=size)
    
    # 调用分页方法，支持动态过滤
    # filters 参数会自动匹配 User 模型字段 (如 username="john")
    result = await repo.paginate(
        pagination_params=params,
        username="john"  # 自动添加 WHERE username = 'john'
    )
    
    return result # 返回包含 items, total, page, size 的标准结构
```

### 9.4 事务管理 (Transaction Management)

框架通过 `UnitOfWork` 或依赖注入的 Scope 管理事务。推荐在 Service 层处理事务。

```python
# 自动提交：BaseRepository 的 create/update/delete 默认会 flush，但不 commit
# 需要在请求结束时统一 commit (框架的中间件或 DI 容器会处理)

# 手动事务控制
async with db_manager.session() as session:
    async with session.begin():
        repo = UserRepository(session)
        await repo.create({"username": "u1"})
        await repo.create({"username": "u2"})
    # 退出 block 自动 commit，异常则 rollback
```

---

## 10. 缓存系统 (Cache System)

### 10.1 基本用法

```python
from aurimyth.foundation_kit.infrastructure.cache import CacheManager

cache = CacheManager.get_instance()

# 设置缓存 (过期时间单位：秒)
await cache.set("user:1", {"name": "test"}, expire=300)

# 获取缓存
user = await cache.get("user:1")

# 删除缓存
await cache.delete("user:1")

# 清空所有缓存
await cache.clear()
```

### 10.2 装饰器用法 (推荐)

```python
@cache.cached(expire=60, key_prefix="user_profile")
async def get_user_profile(user_id: str):
    # 这里的返回值会被缓存
    # 缓存 Key 格式: user_profile:module.func:md5(args)
    return await db.get_user(user_id)
```

### 10.3 缓存后端配置

在 `.env` 中配置：
```bash
# 内存缓存（开发环境）
CACHE_TYPE=memory
CACHE_MAX_SIZE=1000

# Redis 缓存（生产环境）
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
```

---

## 11. 异步任务 (Asynchronous Tasks)

### 11.1 定义任务

使用 `conditional_task` 装饰器，这样代码可以在 API 服务（作为生产者）和 Worker 服务（作为消费者）中通用。

```python
from aurimyth.foundation_kit.infrastructure.tasks.manager import TaskManager

tm = TaskManager.get_instance()

@tm.conditional_task(queue_name="default", max_retries=3)
async def send_email_task(email: str, content: str):
    print(f"Sending email to {email}...")
    # 发送逻辑
```

### 11.2 调用任务

```python
# 在 API 接口中调用
send_email_task.send("test@example.com", "Hello!")

# 异步等待结果
result = await send_email_task.send_and_wait("test@example.com", "Hello!")
```

### 11.3 启动 Worker

设置环境变量 `SERVICE_TYPE=worker` 启动应用，框架会自动启动任务监听进程。

---

## 12. 事件驱动 (Event Driven)

### 12.1 定义与订阅

```python
from aurimyth.foundation_kit.infrastructure.events.bus import EventBus
from aurimyth.foundation_kit.infrastructure.events import Event

# 1. 定义事件模型
class OrderCreatedEvent(Event):
    order_id: str
    amount: float
    
    @property
    def event_name(self) -> str:
        return "order.created"

# 2. 订阅事件
bus = EventBus.get_instance()

@bus.subscribe(OrderCreatedEvent)
async def on_order_created(event: OrderCreatedEvent):
    print(f"收到订单创建事件: {event.order_id}")
```

### 12.2 发布事件

```python
await bus.publish(OrderCreatedEvent(order_id="1001", amount=99.9))
```

### 12.3 事件历史记录

```python
# 获取事件历史（本地模式）
history = bus.get_history(event_type=OrderCreatedEvent, limit=100)

# 查询事件（支持分布式模式）
all_events = await bus.query_history(
    event_type=OrderCreatedEvent,
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 31)
)
```

---

## 13. 定时调度 (Scheduler)

```python
from aurimyth.foundation_kit.infrastructure.scheduler.manager import SchedulerManager

scheduler = SchedulerManager.get_instance()

# Cron 任务
scheduler.add_job(
    func=daily_report_task,
    trigger="cron",
    hour=2, minute=30,
    id="daily_report"
)

# 间隔任务
scheduler.add_job(
    func=heartbeat,
    trigger="interval",
    seconds=30
)

# 一次性任务
scheduler.add_job(
    func=cleanup_task,
    trigger="date",
    run_date=datetime(2024, 1, 1, 12, 0),
    id="cleanup_once"
)
```

---

## 14. RPC 与服务发现 (RPC & Service Discovery)

### 14.1 配置服务发现

在 `.env` 中配置：
```bash
# 优先级 1: 显式映射
RPC_CLIENT_SERVICES={"order-service": "http://10.0.0.5:8000"}

# 优先级 2: DNS 自动解析 (默认启用)
# 如果未配置映射，client.get("order-service") 会自动请求 http://order-service
```

### 14.2 发起调用

```python
from aurimyth.foundation_kit.application.rpc.client import create_rpc_client

# 创建客户端 (会自动使用服务发现)
client = create_rpc_client(service_name="order-service")

# 发起请求 (API 风格类似 httpx)
response = await client.get(
    path="/api/v1/orders/123",
    headers={"X-Request-ID": "..."}
)

# 响应处理 (自动检查 status_code)
data = response.data  # 自动解析 JSON data 字段
```

---

## 15. WebSocket 长连接 (WebSocket)

### 15.1 数据库连接管理

在 WebSocket 长连接中，**不能使用 `Depends()` 注入数据库连接**，因为会长期占用连接池。

正确的做法是**按需获取会话**：

```python
from fastapi import APIRouter, WebSocket
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager

router = APIRouter()

@router.websocket("/ws/chat/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    db_manager = DatabaseManager.get_instance()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            # 每次需要数据库操作时才获取会话
            async with db_manager.session() as session:
                repo = MessageRepository(session)
                message = await repo.create({
                    "room_id": room_id,
                    "content": data,
                })
            # 会话自动关闭，连接返回到连接池
            
            # 发送响应
            await websocket.send_json({
                "status": "ok",
                "message_id": message.id
            })
    
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
```

### 15.2 连接池配置

如果频繁需要数据库操作，可以增加连接池大小：

```python
from aurimyth.foundation_kit.application.config import BaseConfig
from aurimyth.foundation_kit.application.config.settings import DatabaseSettings

class AppConfig(BaseConfig):
    database: DatabaseSettings = DatabaseSettings(
        pool_size=50,        # 增加连接池大小
        max_overflow=20,     # 允许溢出连接
        pool_recycle=3600,   # 连接回收时间
    )
```

### 15.3 完整示例：群聊应用

```python
from fastapi import status, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    async def disconnect(self, room_id: str, websocket: WebSocket):
        self.active_connections[room_id].remove(websocket)
    
    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()
db_manager = DatabaseManager.get_instance()

@router.websocket("/ws/chat/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # 每次操作都临时获取会话
            async with db_manager.session() as session:
                message_repo = MessageRepository(session)
                message = await message_repo.create({
                    "room_id": room_id,
                    "content": data,
                })
            
            # 广播给所有客户端
            await manager.broadcast(room_id, {
                "type": "message",
                "content": data,
                "timestamp": message.created_at.isoformat(),
            })
    
    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)
```

### 15.4 缓存策略优化

为了减少数据库查询，可以结合缓存：

```python
from aurimyth.foundation_kit.infrastructure.cache import CacheManager

cache_manager = CacheManager.get_instance()

@router.websocket("/ws/feed/{user_id}")
async def websocket_feed(websocket: WebSocket, user_id: str):
    await websocket.accept()
    
    while True:
        # 先从缓存读
        cached_data = await cache_manager.get(f"feed:{user_id}")
        if cached_data:
            await websocket.send_json(cached_data)
            continue
        
        # 缓存未命中才查询 DB
        async with db_manager.session() as session:
            data = await fetch_feed(session, user_id)
            await cache_manager.set(f"feed:{user_id}", data, expire=60)
            await websocket.send_json(data)
```

**更多详情**，见 [WebSocket 连接管理完整指南](./WEBSOCKET_CONNECTION_MANAGEMENT.md)

---

## 16. 对象存储 (Object Storage)

支持本地存储（开发用）和 S3（生产用）无缝切换。

```python
from aurimyth.foundation_kit.infrastructure.storage.factory import StorageFactory
from aurimyth.foundation_kit.infrastructure.storage.base import StorageFile

# 初始化 (通常在启动时)
storage = await StorageFactory.create(
    "s3", 
    access_key_id="...", 
    access_key_secret="...", 
    bucket_name="my-bucket"
)

# 上传
with open("avatar.png", "rb") as f:
    url = await storage.upload_file(
        StorageFile(data=f, object_name="avatars/user_1.png")
    )

# 下载
content = await storage.download_file("avatars/user_1.png")

# 删除
await storage.delete_file("avatars/user_1.png")
```

---

## 17. 国际化 (i18n)

```python
from aurimyth.foundation_kit.common.i18n.translator import translate, load_translations

# 1. 加载资源
load_translations({
    "zh_CN": {"error.not_found": "资源 {name} 未找到"},
    "en_US": {"error.not_found": "Resource {name} not found"}
})

# 2. 使用
msg = translate("error.not_found", name="User", locale="zh_CN")
# 输出: "资源 User 未找到"
```

---

## 18. 数据库迁移 (Database Migration)

### 17.1 初始化迁移

```bash
# 使用 Alembic 初始化迁移环境
alembic init -t async alembic

# 配置 alembic/env.py
# 指定 SQLAlchemy 引擎和目标数据库
```

### 17.2 创建迁移

```bash
# 自动生成迁移文件
alembic revision --autogenerate -m "Add users table"

# 手动编写迁移
alembic revision -m "Custom migration"
```

### 17.3 执行迁移

```bash
# 升级到最新版本
alembic upgrade head

# 升级到指定版本
alembic upgrade <revision>

# 回滚到上一个版本
alembic downgrade -1
```

---

## 附录：常见问题

### Q: 如何在 API 中注入依赖？

A: 使用 FastAPI 的 `Depends()` 或框架的 DI 容器：

```python
from aurimyth.foundation_kit.infrastructure.di import Container

container = Container()
container.register("db", instance=db_manager)

@router.get("/users")
async def list_users(db = Depends(lambda: container.get("db"))):
    # 使用注入的依赖
    pass
```

### Q: 如何处理大规模数据导入？

A: 使用批量操作 API：

```python
# 批量插入
users_data = [{"username": f"user{i}", "email": f"user{i}@example.com"} for i in range(10000)]
await repo.bulk_create(users_data, batch_size=1000)

# 批量更新
updates = [{"id": user_id, "status": "active"} for user_id in user_ids]
await repo.bulk_update(updates)
```

### Q: 如何实现软删除？

A: 使用 `SoftDeleteModel` 基类：

```python
from aurimyth.foundation_kit.domain.models.base import SoftDeleteModel

class User(SoftDeleteModel):
    __tablename__ = "users"
    username: Mapped[str]
    
# 软删除（保留记录）
await repo.soft_delete(user_id)

# 硬删除（真正删除）
await repo.hard_delete(user_id)

# 查询会自动排除已删除的记录
users = await repo.list()  # 不包含已软删除的记录
```

---

**最后更新**: 2024年1月1日
**版本**: 1.0.0

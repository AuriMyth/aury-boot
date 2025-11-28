# AuriMyth Foundation Kit 开发指南

## 概述

本文档介绍如何使用 `aurimyth-foundation-kit` 作为依赖包来构建应用。Foundation Kit 提供了完整的微服务基础设施组件，包括数据库管理、缓存、任务队列、RPC通信、事件系统等。

## 目录

- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [核心概念](#核心概念)
- [开发规范](#开发规范)
- [模块详解](#模块详解)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 快速开始

### 1. 安装依赖

```bash
# 使用 pip
pip install aurimyth-foundation-kit

# 或使用 uv（推荐）
uv add aurimyth-foundation-kit
```

### 2. 创建应用项目

```bash
# 创建项目目录
mkdir my-service
cd my-service

# 初始化项目
uv init
uv add aurimyth-foundation-kit fastapi uvicorn
```

### 3. 最小应用示例

创建 `main.py`：

```python
"""最小应用示例。"""
from aurimyth.foundation_kit.application import FoundationApp

# 方式1：直接使用 FoundationApp（最简单）
app = FoundationApp(
    title="My Service",
    version="1.0.0",
)

# 添加业务路由
@app.get("/users")
async def get_users():
    """获取用户列表。"""
    return {"users": []}

# 方式2：继承 FoundationApp（推荐，更灵活）
class MyApp(FoundationApp):
    """自定义应用类。"""
    
    # 覆盖默认组件列表
    items = [
        RequestLoggingComponent,
        CORSComponent,
        DatabaseComponent,
        CacheComponent,
    ]
    
    def setup_routes(self):
        """自定义路由配置。"""
        super().setup_routes()
        
        # 添加业务路由
        @self.get("/api/v1/users")
        async def list_users():
            return {"users": []}

app = MyApp()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**FoundationApp 自动提供：**
- ✅ 请求日志中间件（可覆盖）
- ✅ CORS 中间件（可覆盖）
- ✅ 全局异常处理（可覆盖）
- ✅ 数据库初始化/清理（根据配置自动启用）
- ✅ 缓存初始化/清理（根据配置自动启用）
- ✅ 任务队列初始化（Worker 模式，根据配置自动启用）
- ✅ 调度器管理（嵌入式模式，根据配置自动启用）
- ✅ 健康检查端点（可覆盖）

### 4. 运行应用

```bash
# 设置环境变量
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/mydb"
export LOG_LEVEL="INFO"

# 运行应用
python main.py
```

---

## 项目结构

### 推荐的项目结构

```
my-service/
├── pyproject.toml          # 项目配置和依赖
├── README.md               # 项目说明
├── .env                    # 环境变量（不提交到 Git）
├── .env.example            # 环境变量示例
├── alembic.ini             # Alembic 配置
├── alembic/                # 迁移文件目录
│   ├── env.py
│   └── versions/
├── app/                    # 应用代码
│   ├── __init__.py
│   ├── main.py             # FastAPI 应用入口
│   ├── config.py           # 应用配置（继承 BaseConfig）
│   ├── models/             # 领域模型
│   │   ├── __init__.py
│   │   └── user.py
│   ├── repositories/       # 仓储层
│   │   ├── __init__.py
│   │   └── user_repository.py
│   ├── services/           # 服务层
│   │   ├── __init__.py
│   │   └── user_service.py
│   ├── api/                # API 路由
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   └── users.py
│   │   └── dependencies.py
│   ├── events/              # 事件定义
│   │   ├── __init__.py
│   │   └── user_events.py
│   └── tasks/              # 异步任务
│       ├── __init__.py
│       └── user_tasks.py
├── tests/                  # 测试代码
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_repositories.py
│   ├── test_services.py
│   └── test_api.py
└── scripts/                # 脚本
    └── init_db.py
```

---

## 核心概念

### 1. FoundationApp 应用基类

`FoundationApp` 是 Foundation Kit 提供的应用基类，继承自 FastAPI，提供组件化的应用框架。

**设计特点：**
- ✅ **抽象**：所有功能单元统一为 Component，无特殊处理
- ✅ **可扩展**：只需改类属性 `items`，即可添加/移除/替换功能
- ✅ **不受限**：无固定的初始化步骤，按依赖关系动态排序

**使用方式：**

```python
from aurimyth.foundation_kit.application import FoundationApp

# 方式1：直接使用（简单场景）
app = FoundationApp(
    title="My Service",
    version="1.0.0",
)

# 方式2：继承使用（推荐，更灵活）
class MyApp(FoundationApp):
    """自定义应用类。"""
    
    # 覆盖默认组件列表
    items = [
        RequestLoggingComponent,
        CORSComponent,
        DatabaseComponent,
        CacheComponent,
        MyCustomComponent,  # 自定义组件
    ]

app = MyApp()
```

### 2. Component 组件系统

所有功能单元（中间件、数据库、缓存等）都是 Component。

**创建自定义组件：**

```python
from aurimyth.foundation_kit.application import Component, FoundationApp
from aurimyth.foundation_kit.application.constants import ComponentName
from aurimyth.foundation_kit.application.config import BaseConfig

class MyServiceComponent(Component):
    """自定义服务组件。"""
    
    name = "my_service"
    enabled = True
    depends_on = [ComponentName.DATABASE]  # 依赖数据库
    
    def can_enable(self, config: BaseConfig) -> bool:
        """条件化启用。"""
        return self.enabled and config.database.url is not None
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化逻辑。"""
        logger.info("My service started")
        # 初始化资源
    
    async def teardown(self, app: FoundationApp) -> None:
        """清理逻辑。"""
        logger.info("My service stopped")
        # 清理资源
```

**注册组件：**

```python
class MyApp(FoundationApp):
    items = FoundationApp.items + [MyServiceComponent]
```

### 3. 依赖关系

通过 `depends_on` 声明依赖关系，框架自动拓扑排序：

```python
class AuthComponent(Component):
    name = "auth"
    depends_on = [ComponentName.DATABASE]  # 需要数据库先启动

class LogComponent(Component):
    name = "logger"
    depends_on = [ComponentName.AUTH]  # 需要 auth 先启动
```

**启动顺序：** Database → Auth → Logger（自动排序）

### 4. 分层架构

Foundation Kit 采用分层架构设计：

```
┌─────────────────────────────────────┐
│      API Layer (FastAPI)            │  ← 接口层
├─────────────────────────────────────┤
│      Service Layer                  │  ← 业务逻辑层
├─────────────────────────────────────┤
│      Repository Layer               │  ← 数据访问层
├─────────────────────────────────────┤
│      Model Layer                    │  ← 领域模型层
└─────────────────────────────────────┘
```

---

## 开发规范

### 1. 代码组织规范

#### 1.1 模型层（Models）

- 所有模型继承 `BaseModel` 或 `TimestampedModel`
- 模型文件放在 `app/models/` 目录
- 使用 SQLAlchemy ORM 定义

```python
# app/models/user.py
from sqlalchemy import Column, String
from aurimyth.foundation_kit.core.models import TimestampedModel

class User(TimestampedModel):
    """用户模型。"""
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
```

#### 1.2 仓储层（Repositories）

- 所有仓储继承 `BaseRepository`
- 仓储文件放在 `app/repositories/` 目录
- 只负责数据访问，不包含业务逻辑

```python
# app/repositories/user_repository.py
from aurimyth.foundation_kit.core.repository import BaseRepository
from app.models.user import User

class UserRepository(BaseRepository[User]):
    """用户仓储。"""
    
    def __init__(self, session):
        super().__init__(session, User)
    
    async def get_by_username(self, username: str) -> User | None:
        """根据用户名获取用户。"""
        return await self.get_by(username=username)
    
    async def get_by_email(self, email: str) -> User | None:
        """根据邮箱获取用户。"""
        return await self.get_by(email=email)
```

#### 1.3 服务层（Services）

- 所有服务继承 `BaseService`
- 服务文件放在 `app/services/` 目录
- 包含业务逻辑，协调多个 Repository

```python
# app/services/user_service.py
from aurimyth.foundation_kit.core.service import BaseService
from aurimyth.foundation_kit.application.transaction import transactional
from app.repositories.user_repository import UserRepository
from app.models.user import User

class UserService(BaseService):
    """用户服务。"""
    
    def __init__(self, session):
        super().__init__(session)
        self.user_repo = UserRepository(session)
    
    @transactional
    async def create_user(self, data: dict) -> User:
        """创建用户。"""
        # 检查用户名是否已存在
        if await self.user_repo.get_by_username(data["username"]):
            raise ValueError("用户名已存在")
        
        # 创建用户
        return await self.user_repo.create(data)
    
    @transactional
    async def update_user(self, user_id: int, data: dict) -> User:
        """更新用户。"""
        user = await self.user_repo.get(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        return await self.user_repo.update(user, data)
```

#### 1.4 API 层（Routes）

- 使用 FastAPI 定义路由
- API 文件放在 `app/api/` 目录
- 使用 Foundation Kit 的请求/响应模型

```python
# app/api/v1/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from aurimyth.foundation_kit.application.interfaces.ingress import BaseRequest
from aurimyth.foundation_kit.application.interfaces.egress import SuccessResponse, IDResponse
from app.services.user_service import UserService
from app.api.dependencies import get_session, get_user_service

router = APIRouter(prefix="/users", tags=["users"])

class CreateUserRequest(BaseRequest):
    """创建用户请求。"""
    username: str
    email: str
    password: str

@router.post("", response_model=IDResponse)
async def create_user(
    request: CreateUserRequest,
    service: UserService = Depends(get_user_service),
):
    """创建用户。"""
    try:
        user = await service.create_user(request.model_dump())
        return IDResponse(data=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    """获取用户。"""
    user = await service.user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return SuccessResponse(data=user)
```

### 2. 配置管理规范

#### 2.1 继承 BaseConfig

创建应用配置类，继承 `BaseConfig`：

```python
# app/config.py
from aurimyth.foundation_kit.application.config import BaseConfig, BaseSettings

class AppSettings(BaseSettings):
    """应用特定配置。"""
    
    app_name: str = "My Service"
    app_version: str = "1.0.0"
    
    model_config = {
        "env_prefix": "APP_",
        "case_sensitive": False,
    }

class AppConfig(BaseConfig):
    """应用配置。"""
    
    app: AppSettings = BaseSettings(default_factory=AppSettings)
```

#### 2.2 环境变量

使用环境变量配置，支持 `.env` 文件：

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mydb
DATABASE_ECHO=false
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
APP_NAME=My Service
```

### 3. 数据库迁移规范

#### 3.1 初始化 Alembic

```bash
# 初始化 Alembic
alembic init alembic

# 配置 alembic/env.py（参考 Foundation Kit 文档）
```

#### 3.2 生成迁移

```bash
# 生成迁移文件
aurimyth-migrate make -m "add user table"

# 或使用 Python API
from aurimyth.foundation_kit.application.migrations import MigrationManager

manager = MigrationManager()
await manager.make_migrations(message="add user table")
```

#### 3.3 执行迁移

```bash
# 执行迁移
aurimyth-migrate up

# 查看迁移状态
aurimyth-migrate status

# 查看迁移历史
aurimyth-migrate show
```

### 4. 测试规范

#### 4.1 使用测试基类

```python
# tests/test_user_service.py
from aurimyth.foundation_kit.testing import TestCase, Factory
from app.models.user import User
from app.services.user_service import UserService

class UserServiceTest(TestCase):
    """用户服务测试。"""
    
    async def setUp(self):
        """测试前准备。"""
        await self.setup_db()
        self.service = UserService(self.db)
        self.user_factory = Factory(User)
    
    async def test_create_user(self):
        """测试创建用户。"""
        user = await self.service.create_user({
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        })
        assert user.id is not None
        assert user.username == "testuser"
```

#### 4.2 使用测试客户端

```python
# tests/test_api.py
from aurimyth.foundation_kit.testing import TestCase, TestClient
from app.main import app

class UserAPITest(TestCase):
    """用户 API 测试。"""
    
    async def setUp(self):
        """测试前准备。"""
        await self.setup_db()
        self.client = TestClient(app)
    
    async def test_create_user_api(self):
        """测试创建用户 API。"""
        response = self.client.post("/api/v1/users", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        assert response.json()["data"] is not None
```

### 5. 错误处理规范

#### 5.1 使用 Foundation Kit 的异常类

```python
from aurimyth.foundation_kit.application.interfaces.errors import (
    NotFoundError,
    ValidationError,
    AlreadyExistsError,
)

# 在服务中使用
async def get_user(self, user_id: int) -> User:
    """获取用户。"""
    user = await self.user_repo.get(user_id)
    if not user:
        raise NotFoundError(
            message="用户不存在",
            resource="user",
            metadata={"user_id": user_id}
        )
    return user
```

#### 5.2 注册全局异常处理器

`FoundationApp` 已自动注册全局异常处理器，无需手动配置。

### 6. 日志规范

#### 6.1 使用 Foundation Kit 的日志

```python
from aurimyth.foundation_kit.infrastructure.logging import logger

logger.info("用户创建成功", user_id=user.id)
logger.error("用户创建失败", error=str(e))
logger.debug("查询参数", filters=filters)
```

#### 6.2 配置日志

`FoundationApp` 会自动根据配置初始化日志，无需手动配置。

---

## 模块详解

### 1. 数据库管理

#### 1.1 初始化数据库

`DatabaseComponent` 会自动根据配置初始化数据库，无需手动调用。

#### 1.2 获取会话

```python
# 方式1：使用 session_factory
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager

db_manager = DatabaseManager.get_instance()
session = db_manager.session_factory()

# 方式2：使用依赖注入（FastAPI）
async def get_session() -> AsyncSession:
    """获取数据库会话。"""
    db_manager = DatabaseManager.get_instance()
    session = db_manager.session_factory()
    try:
        yield session
    finally:
        await session.close()
```

### 2. 缓存管理

#### 2.1 初始化缓存

`CacheComponent` 会自动根据配置初始化缓存，无需手动调用。

#### 2.2 使用缓存

```python
from aurimyth.foundation_kit.infrastructure.cache import CacheManager

cache_manager = CacheManager.get_instance()

# 获取缓存
value = await cache_manager.get("user:1")

# 设置缓存
await cache_manager.set("user:1", user_data, expire=3600)

# 使用缓存装饰器
@cache_manager.cached(expire=3600)
async def get_user(user_id: int):
    """带缓存的获取用户方法。"""
    return await user_repo.get(user_id)
```

### 3. 任务队列

#### 3.1 配置任务队列

`TaskComponent` 会在 Worker 模式下自动初始化，无需手动调用。

#### 3.2 定义任务

```python
from aurimyth.foundation_kit.infrastructure.tasks import conditional_actor
from aurimyth.foundation_kit.infrastructure.tasks.constants import TaskQueueName

@conditional_actor(queue_name=TaskQueueName.DEFAULT)
async def send_email(to: str, subject: str, body: str):
    """发送邮件任务。
    
    在 Worker 模式下会注册为 actor，在 API 模式下返回 TaskProxy。
    """
    # 发送邮件逻辑
    pass

# 调用任务（API 模式）
await send_email.send(to="user@example.com", subject="Welcome", body="...")
```

### 4. 调度器

#### 4.1 嵌入式调度器（伴随 API 运行）

```python
# app/main.py
class MyApp(FoundationApp):
    items = [
        RequestLoggingComponent,
        CORSComponent,
        DatabaseComponent,
        SchedulerComponent,  # 嵌入式调度器
    ]
    
    async def register_scheduler_jobs(self) -> None:
        """注册定时任务。"""
        from aurimyth.foundation_kit.infrastructure.scheduler import SchedulerManager
        
        scheduler = SchedulerManager.get_instance()
        scheduler.add_job(
            func=cleanup_expired_tokens,
            trigger="cron",
            hour=2  # 每天凌晨2点执行
        )

app = MyApp()
```

#### 4.2 独立调度器（独立 Pod）

```python
# app/scheduler.py
from aurimyth.foundation_kit.application.scheduler import run_scheduler
from aurimyth.foundation_kit.infrastructure.scheduler import SchedulerManager

async def setup_jobs():
    """注册定时任务。"""
    scheduler = SchedulerManager.get_instance()
    
    scheduler.add_job(
        func=cleanup_expired_tokens,
        trigger="cron",
        hour=2
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_scheduler(register_jobs=setup_jobs))
```

### 5. RPC 通信

#### 5.1 创建 RPC 客户端

```python
from aurimyth.foundation_kit.application.rpc import RPCClient

# 创建客户端
user_service_client = RPCClient(
    base_url="http://user-service:8000",
    timeout=30,
)

# 调用远程服务
response = await user_service_client.call(
    method="GET",
    path="/api/v1/users/1"
)
```

#### 5.2 服务注册

```python
from aurimyth.foundation_kit.application.rpc import ServiceRegistry

registry = ServiceRegistry()
registry.register("user-service", "http://user-service:8000")
registry.register("user-service", "http://user-service-2:8000")  # 负载均衡

# 获取服务实例（随机选择）
instance = registry.get_instance("user-service")
```

### 6. 事件系统

#### 6.1 定义事件

```python
# app/events/user_events.py
from aurimyth.foundation_kit.application.events import Event
from pydantic import Field

class UserCreatedEvent(Event):
    """用户创建事件。"""
    user_id: int = Field(description="用户ID")
    username: str = Field(description="用户名")
    
    @property
    def event_name(self) -> str:
        return "user.created"
```

#### 6.2 发布事件

```python
from aurimyth.foundation_kit.application.events import EventBus
from app.events.user_events import UserCreatedEvent

event_bus = EventBus.get_instance()

# 发布事件
await event_bus.publish(UserCreatedEvent(
    user_id=user.id,
    username=user.username,
))
```

#### 6.3 订阅事件

```python
from aurimyth.foundation_kit.application.events import EventBus
from app.events.user_events import UserCreatedEvent

event_bus = EventBus.get_instance()

@event_bus.subscribe(UserCreatedEvent)
async def handle_user_created(event: UserCreatedEvent):
    """处理用户创建事件。"""
    # 发送欢迎邮件
    await send_welcome_email(event.user_id)
```

### 7. 依赖注入

#### 7.1 注册服务

```python
from aurimyth.foundation_kit.application.container import Container, Lifetime

container = Container.get_instance()

# 注册单例服务
container.register_singleton(
    UserRepository,
    UserRepository,
)

# 注册瞬态服务
container.register_transient(
    UserService,
    UserService,
)
```

#### 7.2 解析依赖

```python
# 手动解析
user_service = container.resolve(UserService)

# 在 FastAPI 中使用
from fastapi import Depends

def get_user_service() -> UserService:
    """获取用户服务。"""
    container = Container.get_instance()
    return container.resolve(UserService)

@router.post("/users")
async def create_user(
    service: UserService = Depends(get_user_service),
):
    # 使用 service
    pass
```

### 8. 国际化

#### 8.1 配置翻译

```python
from aurimyth.foundation_kit.i18n import Translator, set_locale

# 设置语言环境
set_locale("zh_CN")

# 使用翻译器
translator = Translator(locale="zh_CN")
message = translator.translate("user.created", name="张三")
```

#### 8.2 日期/数字本地化

```python
from aurimyth.foundation_kit.i18n import Translator

translator = Translator(locale="zh_CN")

# 格式化日期
formatted_date = translator.format_date(datetime.now())

# 格式化数字
formatted_number = translator.format_number(1234.56)
```

---

## 最佳实践

### 1. 服务类型配置

根据运行模式配置 `SERVICE_TYPE`：

```bash
# API 服务（默认）
SERVICE_TYPE=api
SCHEDULER_MODE=embedded  # 或 standalone

# Worker 服务
SERVICE_TYPE=worker

# 独立调度器
SERVICE_TYPE=scheduler
```

### 2. 环境配置

使用 `.env` 文件管理环境变量：

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mydb
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
TASK_BROKER_URL=redis://localhost:6379/1
LOG_LEVEL=INFO
SERVICE_TYPE=api
SCHEDULER_MODE=embedded
```

### 3. 错误处理

统一使用 Foundation Kit 的异常类：

```python
from aurimyth.foundation_kit.application.interfaces.errors import (
    NotFoundError,
    ValidationError,
    AlreadyExistsError,
)

# 在服务中抛出异常
if not user:
    raise NotFoundError(message="用户不存在", resource="user")

# 在 API 中自动处理（通过全局异常处理器）
```

### 4. 事务管理

始终使用 `@transactional` 装饰器：

```python
from aurimyth.foundation_kit.application.transaction import transactional

@transactional
async def create_user_with_profile(data: dict):
    """自动管理事务。"""
    user = await user_repo.create(data["user"])
    profile = await profile_repo.create({
        "user_id": user.id,
        **data["profile"]
    })
    return user, profile
```

### 5. 测试策略

- 使用 `TestCase` 基类，自动处理数据库事务回滚
- 使用 `Factory` 生成测试数据
- 使用 `TestClient` 测试 API

```python
class UserServiceTest(TestCase):
    async def setUp(self):
        await self.setup_db()
        self.service = UserService(self.db)
        self.user_factory = Factory(User)
    
    async def test_create_user(self):
        user = await self.service.create_user({
            "username": "test",
            "email": "test@example.com",
            "password": "password"
        })
        assert user.id is not None
```

### 6. 组件开发

- **使用常量**：组件名称和依赖使用 `ComponentName` 常量
- **声明依赖**：通过 `depends_on` 声明依赖关系
- **条件化启用**：重写 `can_enable()` 而不是硬编码判断
- **错误处理**：在 `setup()` 中处理初始化失败
- **资源清理**：在 `teardown()` 中确保所有资源都被正确释放

---

## 常见问题

### Q1: 如何配置多个数据库？

A: Foundation Kit 目前支持单个数据库连接。如需多个数据库，可以创建多个 `DatabaseManager` 实例，或使用自定义 `DatabaseComponent`。

### Q2: 如何在 Worker 模式下运行任务？

A: 设置 `SERVICE_TYPE=worker`，然后使用 `conditional_actor` 装饰器定义任务。Worker 进程会自动注册并执行任务。

### Q3: 如何自定义异常处理？

A: 实现 `ErrorHandler` 接口，然后注册到 `ErrorHandlerChain`。`FoundationApp` 已自动注册默认的错误处理链。

### Q4: 如何添加自定义缓存后端？

A: 实现 `ICache` 接口，然后使用 `CacheFactory.register()` 注册。

### Q5: 迁移文件应该放在哪里？

A: 放在项目根目录的 `alembic/versions/` 目录下。

### Q6: 如何禁用某个默认组件？

A: 覆盖 `items` 类属性，移除不需要的组件：

```python
class MyApp(FoundationApp):
    items = [
        RequestLoggingComponent,
        CORSComponent,
        DatabaseComponent,
        # 没有 CacheComponent，不会启用缓存
    ]
```

### Q7: 如何替换某个默认组件？

A: 创建同名组件覆盖：

```python
class CustomDatabaseComponent(Component):
    name = ComponentName.DATABASE  # 同名覆盖
    # ...

class MyApp(FoundationApp):
    items = [
        RequestLoggingComponent,
        CORSComponent,
        CustomDatabaseComponent,  # 替换默认的
        CacheComponent,
    ]
```

---

## 参考资源

- [架构设计文档](./ARCHITECTURE.md)
- [Foundation Kit API 文档](./API_REFERENCE.md)
- [Foundation Kit 配置参考](./CONFIG_REFERENCE.md)

---

## 更新日志

- **v0.1.0** (2024-01-01): 初始版本


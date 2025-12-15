# Aury Boot 用户开发手册

欢迎使用 Aury Boot！这是一款专为构建现代化、高性能微服务而设计的 Python 基础设施框架。

## 目录（快速开始）

> 📖 **详细文档**：本目录下还有更详细的技术指南

1. [简介](#1-简介) - 查看详细版：[01-intro-detailed.md](./01-intro-detailed.md)
2. [快速上手（脚手架）](#2-快速上手脚手架) - 查看详细版：[25-scaffold-guide.md](./25-scaffold-guide.md)
3. [快速上手（手动）](#3-快速上手手动) - 查看详细版：[02-installation-guide.md](./02-installation-guide.md)
4. [服务器运行](#4-服务器运行) - 查看详细版：[03-server-deployment.md](./03-server-deployment.md)
5. [项目结构](#5-项目结构) - 查看详细版：[04-project-structure.md](./04-project-structure.md)
6. [配置](#6-配置) - 查看详细版：[05-configuration-advanced.md](./05-configuration-advanced.md)
7. [依赖注入](#7-依赖注入) - 查看详细版：[06-di-container-complete.md](./06-di-container-complete.md)
8. [中间件和组件](#8-中间件和组件) - 查看详细版：[07-middleware-guide.md](./07-middleware-guide.md) / [08-components-detailed.md](./08-components-detailed.md)
9. [HTTP 接口](#9-http-接口) - 查看详细版：[09-http-advanced.md](./09-http-advanced.md) （Ingress/Egress 详解）
10. [错误处理](#10-错误处理) - 查看详细版：[10-error-handling-guide.md](./10-error-handling-guide.md)
11. [事务管理](#11-事务管理) - 查看详细版：[11-transaction-management.md](./11-transaction-management.md)
12. [数据库](#12-数据库) - 查看详细版：[12-database-complete.md](./12-database-complete.md)
13. [缓存](#13-缓存) - 查看详细版：[13-caching-advanced.md](./13-caching-advanced.md)
14. [异步任务](#14-异步任务) - 查看详细版：[14-async-tasks-guide.md](./14-async-tasks-guide.md)
15. [事件驱动](#15-事件驱动) - 查看详细版：[15-events-driven.md](./15-events-driven.md)
16. [定时调度](#16-定时调度) - 查看详细版：[16-scheduler-guide.md](./16-scheduler-guide.md)
17. [RPC 与服务发现](#17-rpc-与服务发现) - 查看详细版：[17-rpc-microservices.md](./17-rpc-microservices.md)
18. [WebSocket](#18-websocket) - 查看详细版：[18-websocket-guide.md](./18-websocket-guide.md)
19. [对象存储](#19-对象存储) - 查看详细版：[19-storage-guide.md](./19-storage-guide.md)
20. [国际化](#20-国际化) - 查看详细版：[20-i18n-guide.md](./20-i18n-guide.md)
21. [数据库迁移](#21-数据库迁移) - 查看详细版：[21-migration-guide.md](./21-migration-guide.md)
22. [日志系统](#22-日志系统) - 查看详细版：[22-logging-complete.md](./22-logging-complete.md)
23. [CLI 命令](#23-cli-命令) - 查看详细版：[24-cli-commands.md](./24-cli-commands.md)
24. [最佳实践](#24-最佳实践) - 查看详细版：[23-best-practices.md](./23-best-practices.md)

---

## 1. 简介

Aury Boot 是 FastAPI 的增强层，提供微服务开发所需的"电池"：

- **统一的组件管理**：生命周期自动管理（数据库、缓存、任务等）
- **标准化架构**：Domain/Infrastructure 分离，Repository 模式
- **微服务能力**：服务发现、RPC、分布式事件总线开箱即用

---

## 2. 快速上手（脚手架）

> 📖 **推荐方式**：使用脚手架快速创建项目，详见 [25-scaffold-guide.md](./25-scaffold-guide.md)

```bash
# 1. 创建项目目录并初始化
mkdir my-service && cd my-service
uv init . --name my_service --no-package --python 3.13

# 2. （可选）配置清华源以加速安装
# 在 pyproject.toml 中添加以下配置
cat >> pyproject.toml << EOF

[tool.uv]
index-url = "https://pypi.tuna.tsinghua.edu.cn/simple"
EOF

# 3. 安装框架
uv add "aury-boot[recommended]"

# 4. 初始化脚手架
aury init                 # 交互式模式（默认），会询问配置选项
aury init -y              # 跳过交互，使用默认配置
aury init my_package      # 使用顶层包结构
aury init --docker        # 同时生成 Docker 配置

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库连接

# 6. 生成 CRUD 代码
aury generate crud user email:str:unique age:int? status:str=active

# 7. 生成并执行数据库迁移
aury migrate make -m "initial"
aury migrate up

# 8. 启动开发服务器
aury server dev
```

> **注意**：`init` 会覆盖 `uv init` 创建的默认 `main.py`，这是正常行为。

访问 http://localhost:8000/docs 查看 API 文档。

### （可选）启用管理后台 Admin Console

框架提供可选的 SQLAdmin 管理后台扩展，默认路径：`/api/admin-console`，适合生产快速搭建后台管理能力。

```bash
# 安装扩展依赖
uv add "aury-boot[admin]"

# 在 .env 中启用并设置 basic 认证
ADMIN_ENABLED=true
ADMIN_PATH=/api/admin-console
ADMIN_AUTH_MODE=basic
ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
ADMIN_AUTH_BASIC_USERNAME=admin
ADMIN_AUTH_BASIC_PASSWORD=change_me
```

启动服务后访问：`http://localhost:8000/api/admin-console`

### 字段语法说明

```bash
# 格式: name:type:modifiers
# 类型: str, text, int, bigint, float, decimal, bool, datetime, date, time, json
# 修饰符: ? (可空), unique, index, =默认值

# 示例
aury generate crud article title:str(200) content:text status:str=draft
aury generate crud product name:str:unique price:decimal stock:int=0

# 交互式模式
aury generate crud user -i
```

---

## 3. 快速上手（手动）

### 安装

```bash
# 推荐：PostgreSQL + Redis + 任务队列 + 调度器
uv add "aury-boot[recommended]"

# 或按需组合
uv add "aury-boot[postgres,redis]"
```

### Hello World

```python
from aury.boot.application.app.base import FoundationApp
from aury.boot.application.config import BaseConfig
from aury.boot.application.server import run_app
from aury.boot.application.interfaces.egress import BaseResponse

class AppConfig(BaseConfig):
    pass

app = FoundationApp(
    title="My Service",
    version="0.1.0",
    config=AppConfig()
)

@app.get("/")
def hello():
    return BaseResponse(code=200, message="Hello", data={"message": "Hello AUM!"})

if __name__ == "__main__":
    run_app(app, host="0.0.0.0", port=8000)
```

### 运行

```bash
# 开发模式（热重载）
aury server dev

# 生产模式（多进程）
aury server prod
```

---

## 4. 服务器运行

### CLI 命令（推荐）

```bash
# 开发模式（热重载）
aury server dev

# 生产模式（多进程）
aury server prod
```

> 📖 **详细配置**：参考 [03-server-deployment.md](./03-server-deployment.md)

---

## 5. 项目结构

```
my_service/
├── main.py                 # 应用入口
├── config.py               # 配置
├── alembic.ini             # Alembic 配置
├── .env.example            # 环境变量模板
├── api/                    # API 路由
│   ├── users.py
│   └── orders.py
├── services/               # 业务逻辑
│   ├── user_service.py
│   └── order_service.py
├── models/                 # 数据模型
│   ├── user.py
│   └── order.py
├── repositories/           # 数据访问
│   ├── user_repository.py
│   └── order_repository.py
├── schemas/                # Pydantic 模型
│   ├── user.py
│   └── order.py
├── migrations/             # 数据库迁移
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/                  # 测试
│   └── conftest.py
├── pyproject.toml
└── README.md
```

**分层说明**：
- `api/`：HTTP 请求处理
- `services/`：业务逻辑
- `models/`：SQLAlchemy 模型
- `repositories/`：数据访问
- `schemas/`：请求/响应序列化

---

## 6. 配置

### 环境变量（.env）

```bash
# 服务器
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb
DATABASE_POOL_SIZE=10

# 缓存
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0

# 任务队列
TASK_BROKER_URL=redis://localhost:6379/0

# 日志
LOG_LEVEL=INFO
LOG_DIR=log
```

### 自定义配置

```python
from aury.boot.application.config import BaseConfig
from pydantic import Field

class MyConfig(BaseConfig):
    my_feature: bool = Field(default=True)
```

> 📖 **详细配置**：参考 [05-configuration-advanced.md](./05-configuration-advanced.md)

---

## 7. 依赖注入

Kit 提供企业级 **DI 容器**

| 生命周期 | 说明 | 场景 |
|---------|------|------|
| **SINGLETON** | 应用生命周期唯一 | 数据库、缓存、配置 |
| **SCOPED** | 请求范围内唯一 | 数据库会话 |
| **TRANSIENT** | 每次创建新实例 | 服务、工具类 |

### 快速开始

```python
from aury.boot.infrastructure.di import Container

container = Container.get_instance()

# 注册
container.register_singleton(DatabaseManager)
container.register_transient(UserService)

# 解析
service = container.resolve(UserService)
```

> 📖 **深入学习**：参考 [06-di-container-complete.md](./06-di-container-complete.md)

---

## 8. 中间件和组件

Kit 将功能单元分为两类：
- **中间件（Middleware）**：处理 HTTP 请求拦截
- **组件（Component）**：管理基础设施生命周期

### 内置中间件

```python
from aury.boot.application.app.middlewares import (
    RequestLoggingMiddleware,  # HTTP 请求日志
    CORSMiddleware,            # CORS 跨域
)
```

### 内置组件

```python
from aury.boot.application.app.components import (
    DatabaseComponent,        # 数据库
    CacheComponent,           # 缓存
    TaskComponent,            # 异步任务
    SchedulerComponent,       # 定时调度
    MigrationComponent,       # 数据库迁移
)
```

### 自定义组件

```python
from aury.boot.application.app.base import Component, FoundationApp

class MyComponent(Component):
    name = "my_component"
    enabled = True
    depends_on = ["cache"]
    
    async def setup(self, app: FoundationApp, config):
        print("初始化...")
    
    async def teardown(self, app: FoundationApp):
        print("清理...")
```

### 注册中间件和组件

```python
class MyApp(FoundationApp):
    middlewares = [
        RequestLoggingMiddleware,
        CORSMiddleware,
    ]
    components = [
        DatabaseComponent,
        CacheComponent,
        MyComponent,
    ]

app = MyApp(config=config)
```

> 📖 **深入学习**：参考 [07-middleware-guide.md](./07-middleware-guide.md) 和 [08-components-detailed.md](./08-components-detailed.md)

---

## 9. HTTP 接口

### 请求模型（Ingress）

```python
from aury.boot.application.interfaces.ingress import (
    BaseRequest,
    PaginationRequest
)
from pydantic import EmailStr, Field

class UserCreateRequest(BaseRequest):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
```

### 统一响应格式（Egress）

```python
from aury.boot.application.interfaces.egress import (
    BaseResponse,
    PaginationResponse,
    Pagination,
)

# 单个资源
return BaseResponse(code=200, message="成功", data=user)

# 列表响应
pagination = Pagination(total=100, items=users, page=1, size=20)
return PaginationResponse(code=200, message="获取成功", data=pagination)
```

### 路由示例

```python
from fastapi import APIRouter, Depends
from aury.boot.infrastructure.di import Container
from aury.boot.application.interfaces.egress import BaseResponse

router = APIRouter()
container = Container.get_instance()

def get_user_service():
    return container.resolve(UserService)

@router.post("/users")
async def create_user(
    request: UserCreateRequest,
    service: UserService = Depends(get_user_service)
):
    user = await service.create(request)
    return BaseResponse(code=200, message="创建成功", data=user)
```

> 📖 **深入学习**：参考 [09-http-advanced.md](./09-http-advanced.md)

---

## 10. 错误处理

### 异常体系与继承规则

```python
from aury.boot.application.errors import (
    BaseError,
    NotFoundError,
    AlreadyExistsError,
    UnauthorizedError,
    ForbiddenError,
)

# ✅ 开发规范：所有服务特定异常都要继承 Foundation Kit 的异常
class MyServiceError(UnauthorizedError):
    """服务特定异常必须继承 Foundation Kit 的异常类。"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, **kwargs)

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await repo.get(user_id)
    if not user:
        # Foundation Kit 全局异常处理器会自动转换为 HTTP 404
        raise NotFoundError(f"用户 {user_id} 不存在")
    return user
```

### 异常继承规则和错误代码

**原则**：
1. 所有异常必须继承 Foundation Kit 的异常类（UnauthorizedError、NotFoundError 等）
2. 所有错误代码必须继承 Foundation Kit 的 `ErrorCode`，在服务范围内定义
3. **不覆盖** Foundation Kit 的错误代码（1xxx-4xxx），服务使用 5xxx+ 范围

```python
# ✅ 正确：定义错误代码枚举，继承 ErrorCode
from aury.boot.application.errors.codes import ErrorCode

class IdentityErrorCode(ErrorCode):
    INVALID_CREDENTIALS = "5001"
    USER_NOT_FOUND = "5101"
    DUPLICATE_USER = "5104"

# ✅ 正确：异常继承 Foundation Kit 的异常
class InvalidCredentialsError(UnauthorizedError):
    def __init__(self, **kwargs):
        metadata = kwargs.pop("metadata", {})
        metadata["error_code"] = IdentityErrorCode.INVALID_CREDENTIALS.value
        super().__init__(message="用户名或密码错误", metadata=metadata, **kwargs)

# ❌ 错误：不继承 Foundation Kit
class MyCustomError(Exception):
    pass

# ❌ 错误：没有调用 super().__init__()
class BadError(NotFoundError):
    self.message = message  # 错！
```

> 📖 **详细规范**：参考 [10-error-handling-guide.md](./10-error-handling-guide.md)

> 📖 **详细说明**：参考 [10-error-handling-guide.md](./10-error-handling-guide.md)

---

## 11. 事务管理

### 推荐方式：装饰器

```python
from aury.boot.domain.transaction import transactional
from sqlalchemy.ext.asyncio import AsyncSession

@transactional
async def create_user_with_profile(session: AsyncSession, name: str):
    repo = UserRepository(session)
    user = await repo.create({"username": name})
    # 自动提交，异常时自动回滚
    return user
```

> 📖 **其他方式**：参考 [11-transaction-management.md](./11-transaction-management.md)

---

## 12. 数据库

### 定义模型

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from aury.boot.domain.models import UUIDAuditableStateModel

class User(UUIDAuditableStateModel):
    """用户模型 - 自动获得 UUID 主键、时间戳和软删除功能"""
    __tablename__ = "users"
    
    # UUIDAuditableStateModel 自动提供：
    # - id: UUID 主键
    # - created_at: 创建时间
    # - updated_at: 更新时间
    # - deleted_at: 软删除时间
    
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
```

### 创建仓储

```python
from aury.boot.domain.repository.impl import BaseRepository

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str):
        return await self.get_by(email=email)
```

### 在 API 中使用

```python
from aury.boot.infrastructure.database import DatabaseManager

db_manager = DatabaseManager.get_instance()

async def get_user_repo(session=Depends(db_manager.get_session)):
    return UserRepository(session)

@router.get("/users/{user_id}")
async def get_user(user_id: str, repo=Depends(get_user_repo)):
    user = await repo.get(user_id)
    if not user:
        raise NotFoundError("用户不存在")
    return BaseResponse(code=200, message="获取成功", data=user)
```

> 📖 **深入学习**：参考 [12-database-complete.md](./12-database-complete.md)

---

## 13. 缓存

### 基本用法

```python
from aury.boot.infrastructure.cache import CacheManager

cache = CacheManager.get_instance()

# 设置
await cache.set("user:1", {"name": "test"}, expire=300)

# 获取
user = await cache.get("user:1")

# 删除
await cache.delete("user:1")
```

> 📖 **详细说明**：参考 [13-caching-advanced.md](./13-caching-advanced.md)

---

## 14. 异步任务

### 定义任务

```python
from aury.boot.infrastructure.tasks.manager import TaskManager

tm = TaskManager.get_instance()

@tm.conditional_task(queue_name="default", max_retries=3)
async def send_email_task(email: str, content: str):
    pass
```

### 调用任务

```python
# 发送
send_email_task.send("test@example.com", "Hello!")
```

> 📖 **详细说明**：参考 [14-async-tasks-guide.md](./14-async-tasks-guide.md)

---

## 15. 事件驱动

### 定义和订阅

```python
from aury.boot.infrastructure.events.bus import EventBus
from aury.boot.infrastructure.events import Event

class OrderCreatedEvent(Event):
    order_id: str
    amount: float
    
    @property
    def event_name(self) -> str:
        return "order.created"

bus = EventBus.get_instance()

@bus.subscribe(OrderCreatedEvent)
async def on_order_created(event: OrderCreatedEvent):
    print(f"订单创建: {event.order_id}")
```

### 发布事件

```python
await bus.publish(OrderCreatedEvent(order_id="1001", amount=99.9))
```

> 📖 **详细说明**：参考 [15-events-driven.md](./15-events-driven.md)

---

## 16. 定时调度

```python
from aury.boot.infrastructure.scheduler.manager import SchedulerManager
from datetime import datetime

scheduler = SchedulerManager.get_instance()

# Cron 任务
scheduler.add_job(
    func=daily_report,
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
```

> 📖 **详细说明**：参考 [16-scheduler-guide.md](./16-scheduler-guide.md)

---

## 17. RPC 与服务发现

### 配置

```bash
# 环境变量
RPC_CLIENT_SERVICES={"order-service": "http://order-service:8000"}
```

### 发起调用

```python
from aury.boot.application.rpc.client import create_rpc_client

client = create_rpc_client(service_name="order-service")
response = await client.get("/api/orders/123")
```

### 自动分布式链路追踪

```python
from aury.boot.common.logging import get_trace_id, logger

trace_id = get_trace_id()
logger.info(f"处理请求 | Trace-ID: {trace_id}")
# RPC 调用会自动添加 X-Trace-ID 请求头
```

> 📖 **详细说明**：参考 [17-rpc-microservices.md](./17-rpc-microservices.md)

---

## 18. WebSocket

### 基本连接

```python
from fastapi import APIRouter, WebSocket
from aury.boot.infrastructure.database import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager.get_instance()

@router.websocket("/ws/chat/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            async with db_manager.session() as session:
                repo = MessageRepository(session)
                await repo.create({"room_id": room_id, "content": data})
            
            await websocket.send_json({"status": "ok"})
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
```

> 📖 **详细说明**：参考 [18-websocket-guide.md](./18-websocket-guide.md)

---

## 19. 对象存储

基于 [aury-sdk-storage](https://github.com/AUMNeo/aury-sdk-storage)，支持 S3 兼容存储和 STS 临时凭证。

```bash
# 安装
uv add "aury-sdk-storage[aws]"
```

```python
from io import BytesIO
from aury.boot.infrastructure.storage import (
    StorageManager, StorageConfig, StorageBackend, StorageFile,
)

# 获取存储管理器（支持命名多实例）
storage = StorageManager.get_instance()

# 初始化（一般由 StorageComponent 自动完成）
await storage.init(StorageConfig(
    backend=StorageBackend.COS,
    bucket_name="my-bucket-1250000000",
    region="ap-guangzhou",
    endpoint="https://cos.ap-guangzhou.myqcloud.com",
    access_key_id="AKIDxxxxx",
    access_key_secret="xxxxx",
))

# 上传
url = await storage.upload_file(
    StorageFile(
        object_name="avatars/user_1.png",
        data=BytesIO(image_bytes),
        content_type="image/png",
    )
)
```

> 📖 **详细说明**：参考 [19-storage-guide.md](./19-storage-guide.md)

---

## 20. 国际化

```python
from aury.boot.common.i18n.translator import translate, load_translations

# 加载翻译
load_translations({
    "zh_CN": {"error.not_found": "资源 {name} 未找到"},
    "en_US": {"error.not_found": "Resource {name} not found"}
})

# 使用
msg = translate("error.not_found", name="User", locale="zh_CN")
```

> 📖 **详细说明**：参考 [20-i18n-guide.md](./20-i18n-guide.md)

---

## 21. 数据库迁移

### 自动迁移（推荐）

应用启动时自动执行迁移：

```python
from aury.boot.application.app.components import MigrationComponent

class MyApp(FoundationApp):
    components = [
        DatabaseComponent,
        MigrationComponent,  # 自动执行迁移
        CacheComponent,
    ]

# 应用启动时自动执行迁移到最新版本
```

### 手动迁移

```bash
# 初始化
alembic init -t async alembic

# 生成迁移
aury migrate make -m "Add users table"

# 执行迁移
aury migrate up

# 查看状态
aury migrate status
```

> 📖 **详细说明**：参考 [21-migration-guide.md](./21-migration-guide.md)

---

## 22. 日志系统

### 环境变量

```bash
LOG_LEVEL=INFO
LOG_DIR=log
LOG_ROTATION_TIME=00:00
LOG_RETENTION_DAYS=7
```

### 使用日志

```python
from aury.boot.common.logging import logger, get_trace_id

logger.info("信息")
logger.warning("警告")
logger.error("错误")

# 自动包含 Trace ID
trace_id = get_trace_id()
logger.info(f"处理请求 | Trace-ID: {trace_id}")
```

> 📖 **详细说明**：参考 [22-logging-complete.md](./22-logging-complete.md)

---

## 23. CLI 命令

### 统一入口

安装后可使用 `aury` 统一命令：

```bash
# 项目初始化（先用 uv 创建项目）
uv init . --name my_service --no-package --python 3.13
uv add "aury-boot[recommended]"
aury init -i              # 交互式模式（推荐）
aury init                 # 默认配置
aury init my_package      # 顶层包结构
aury init --docker        # 包含 Docker 配置

# 代码生成
aury generate crud user

# 服务器
aury server dev
aury server prod

# 数据库迁移
aury migrate make -m "add user"
aury migrate up
aury migrate status

# Shell 补全
aum --install-completion
```

> 📖 **详细说明**：参考 [24-cli-commands.md](./24-cli-commands.md)

---

## 24. 最佳实践

### 使用 Foundation Kit 预定义模型

Foundation Kit 提供多个预定义模型组合，推荐直接使用而不是 `Base`：

```python
from aury.boot.domain.models import (
    UUIDAuditableStateModel,  # 【推荐】UUID主键 + 时间戳 + 软删除
    UUIDModel,                # UUID主键 + 时间戳
    Model,                    # 整数主键 + 时间戳
    FullFeaturedUUIDModel,    # 完整功能：UUID + 时间戳 + 软删除 + 乐观锁
)

# ✅ 推荐：使用 UUIDAuditableStateModel
class Identity(UUIDAuditableStateModel):
    """身份模型 - 自动获得以下字段：
    - id: UUID 主键
    - created_at: 创建时间
    - updated_at: 更新时间  
    - deleted_at: 软删除时间（0 未删除，>0 已删除时间戳）
    """
    __tablename__ = "identity_identities"
    username: Mapped[str] = mapped_column(String(100))

# ❌ 不推荐：直接使用 Base
class BadModel(Base):
    __tablename__ = "bad_model"
    # 需要手动添加 id、created_at 等字段
```

**预定义模型对比**：

| 模型 | UUID 主键 | 时间戳 | 软删除 | 乐观锁 | 用途 |
|------|----------|--------|--------|--------|------|
| **UUIDAuditableStateModel** | ✅ | ✅ | ✅ | ❌ | 【推荐】大多数业务模型 |
| **UUIDModel** | ✅ | ✅ | ❌ | ❌ | 不需要软删除的模型 |
| **Model** | ❌ | ✅ | ❌ | ❌ | 使用整数主键 |
| **FullFeaturedUUIDModel** | ✅ | ✅ | ✅ | ✅ | 需要完整功能的关键业务 |

### 贫血模型 + Repository 模式

推荐使用"贫血模型"设计（只包含字段，无关系定义），所有查询由 Repository 层负责：

```python
# ✅ 模型层（纯数据结构）
class Tenant(UUIDAuditableStateModel):
    __tablename__ = "tenants"
    name: Mapped[str] = mapped_column(String(100))
    # 不定义 relationship，不定义 ForeignKey

# ✅ 仓库层（负责所有查询）
class TenantRepository(BaseRepository[Tenant]):
    async def get_with_members(self, tenant_id: GUID):
        # 显式 join，可控的查询
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        return await self.session.scalar(stmt)
    
    async def list_members(self, tenant_id: GUID):
        # 显式查询成员，避免隐式 N+1
        stmt = select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)
        return await self.session.scalars(stmt)
```

**好处**：
- 模型简洁，易于维护
- 避免隐式查询导致的 N+1 问题
- 查询逻辑集中在 Repository，便于优化
- 完全掌控数据加载策略

### 避免 N+1 查询

```python
from sqlalchemy.orm import selectinload

class UserRepository(BaseRepository[User]):
    async def list_with_orders(self):
        stmt = select(User).options(selectinload(User.orders))
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### Event Bus vs Task Queue

| 特性 | Event Bus | Task Queue |
|------|-----------|-----------|
| 消费者 | 多个 | 单个 |
| 延迟 | 毫秒级 | 秒级 |
| 重试 | 无 | 有 |
| 用途 | 通知、分析 | 数据处理、支付 |

### 依赖管理

```bash
uv init my-service
uv add "aury-boot[recommended]"
uv lock
```

> 📖 **详细说明**：参考 [23-best-practices.md](./23-best-practices.md)

# 4. 项目结构最佳实践

## 推荐的项目结构

使用分层架构（Layered Architecture）：

```
my-service/
├── main.py                  # 应用入口
├── config.py                # 配置定义
├── pyproject.toml           # 项目配置
├── uv.lock                  # 依赖锁定
├── .env                     # 环境变量（开发）
├── .env.example             # 环境变量模板
├── README.md                # 项目说明
│
├── api/                     # API 层
│   └── v1/
│       ├── __init__.py
│       ├── users.py         # 用户相关路由
│       ├── orders.py        # 订单相关路由
│       └── health.py        # 健康检查
│
├── services/                # Service 层（业务逻辑）
│   ├── __init__.py
│   ├── user_service.py
│   ├── order_service.py
│   └── payment_service.py
│
├── models/                  # 数据模型（SQLAlchemy）
│   ├── __init__.py
│   ├── user.py
│   ├── order.py
│   └── base.py              # 基础模型
│
├── repositories/            # Repository 层（数据访问）
│   ├── __init__.py
│   ├── user_repository.py
│   ├── order_repository.py
│   └── base_repository.py
│
├── schemas/                 # Pydantic 模型（请求/响应）
│   ├── __init__.py
│   ├── user.py
│   ├── order.py
│   └── common.py
│
├── exceptions/              # 自定义异常
│   ├── __init__.py
│   └── custom_errors.py
│
├── components/              # 自定义组件
│   ├── __init__.py
│   └── custom_component.py
│
├── utils/                   # 工具函数
│   ├── __init__.py
│   ├── helpers.py
│   └── validators.py
│
├── migrations/              # 数据库迁移（Alembic）
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── logs/                    # 日志目录
│   ├── app.log
│   ├── error.log
│   └── access.log
│
└── tests/                   # 测试
    ├── __init__.py
    ├── conftest.py          # pytest 配置
    ├── test_users.py
    ├── test_orders.py
    └── fixtures.py          # 测试数据
```

## 分层说明

### API 层（api/）

处理 HTTP 请求和响应。

```python
# api/v1/users.py
from fastapi import APIRouter, Depends
from aury.boot.application.interfaces.egress import BaseResponse

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: str, service=Depends(get_user_service)):
    user = await service.get_user(user_id)
    return BaseResponse(code=200, message="成功", data=user)
```

**职责**：
- HTTP 请求解析
- 参数验证
- 调用 Service
- 响应序列化

### Service 层（services/）

处理业务逻辑。

```python
# services/user_service.py
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    
    async def get_user(self, user_id: str) -> User:
        user = await self.repo.get(user_id)
        if not user:
            raise NotFoundError("用户不存在")
        return user
    
    async def create_user(self, data: dict) -> User:
        if await self.repo.get_by_email(data["email"]):
            raise AlreadyExistsError("邮箱已存在")
        return await self.repo.create(data)
```

**职责**：
- 业务逻辑处理
- 事务管理
- 跨 Repository 操作
- 数据验证

### Repository 层（repositories/）

处理数据访问。

```python
# repositories/user_repository.py
from aury.boot.domain.repository.impl import BaseRepository

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.get_by(email=email)
    
    async def list_active(self) -> List[User]:
        return await self.list(is_active=True)
```

**职责**：
- 数据库查询
- CRUD 操作
- 查询优化
- 关系加载

### Models 层（models/）

定义数据模型。推荐使用 Kit 提供的预定义基类。

```python
# models/user.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from aury.boot.domain.models import AuditableStateModel

class User(AuditableStateModel):
    """用户模型。
    
    继承 AuditableStateModel 自动获得：
    - id: int 自增主键
    - created_at: 创建时间
    - updated_at: 更新时间
    - deleted_at: 软删除时间戳
    """
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
```

**职责**：
- SQLAlchemy 模型定义
- 数据库字段映射
- 不推荐定义 relationship（使用贫血模型 + Repository 模式）

### Schemas 层（schemas/）

定义请求/响应模型。

```python
# schemas/user.py
from pydantic import BaseModel, EmailStr

class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    
    class Config:
        from_attributes = True
```

**职责**：
- 请求验证
- 响应序列化
- 文档生成

## 导入组织

### 按包组织

```python
# main.py
from api.v1 import users_router, orders_router
from services import UserService, OrderService
from repositories import UserRepository, OrderRepository
```

### 按功能组织

```python
# services/__init__.py
from .user_service import UserService
from .order_service import OrderService

__all__ = ["UserService", "OrderService"]
```

## 配置管理

### 单一配置文件

```python
# config.py
from aury.boot.application.config import BaseConfig
from pydantic import Field

class AppConfig(BaseConfig):
    app_name: str = Field(default="My Service")
    app_version: str = Field(default="0.1.0")
    
    # 业务配置
    max_retries: int = Field(default=3)
    cache_ttl: int = Field(default=3600)
```

### 在 main.py 中使用

```python
# main.py
from config import AppConfig
from aury.boot.application.app.base import FoundationApp

config = AppConfig()
app = FoundationApp(
    title=config.app_name,
    version=config.app_version,
    config=config
)
```

## 路由组织

### 分模块路由

```python
# main.py
from fastapi import APIRouter
from api.v1 import users, orders, payments

# 创建主路由
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])

# 注册到应用
app.include_router(api_router)
```

### 路由文件结构

```python
# api/v1/users.py
from fastapi import APIRouter, Depends

router = APIRouter()

# 定义路由
@router.get("/{user_id}")
async def get_user(user_id: str):
    pass

@router.post("")
async def create_user(request: UserCreateRequest):
    pass

# 注意：不要在这里创建 APIRouter 的实例
```

## 依赖管理

### 使用工厂函数

```python
# main.py
from aury.boot.infrastructure.di import Container

container = Container.get_instance()

# 注册服务
container.register_singleton(UserRepository)
container.register_transient(UserService)

# 创建工厂函数
def get_user_service() -> UserService:
    return container.resolve(UserService)
```

### 在路由中使用

```python
# api/v1/users.py
from main import get_user_service

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service)
):
    user = await service.get_user(user_id)
    return BaseResponse(code=200, message="成功", data=user)
```

## 异常处理

### 自定义异常

异常必须继承 Foundation Kit 的异常类：

```python
# exceptions/custom_errors.py
from aury.boot.application.errors import (
    NotFoundError,
    UnauthorizedError,
)

class UserNotFoundError(NotFoundError):
    """用户不存在异常。"""
    def __init__(self, user_id: str):
        super().__init__(
            message=f"用户 {user_id} 不存在",
            resource=user_id,
        )

class InvalidCredentialsError(UnauthorizedError):
    """身份验证失败异常。"""
    def __init__(self):
        super().__init__(
            message="用户名或密码错误",
        )
```

### 在服务中使用

```python
# services/user_service.py
from exceptions.custom_errors import UserNotFoundError

async def get_user(self, user_id: str):
    user = await self.repo.get(user_id)
    if not user:
        raise UserNotFoundError(user_id)
    return user
```

## 测试结构

### 测试文件组织

```
tests/
├── conftest.py              # 共享的 fixtures
├── test_users.py            # 用户 API 测试
├── test_orders.py           # 订单 API 测试
├── services/
│   ├── test_user_service.py
│   └── test_order_service.py
└── repositories/
    ├── test_user_repository.py
    └── test_order_repository.py
```

### 基础测试示例

```python
# tests/test_users.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_get_user():
    response = client.get("/api/v1/users/123")
    assert response.status_code == 200
    assert response.json()["code"] == 200
```

## 环境配置

### .env 文件

```bash
# 服务器
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_WORKERS=1

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb

# 缓存
CACHE_TYPE=redis
CACHE_URL=redis://localhost:6379/0

# 日志
LOG_LEVEL=INFO
LOG_DIR=logs
```

### .env.example

提供一个模板文件，供开发者参考：

```bash
cp .env.example .env
```

## 常见问题

### Q: 何时拆分文件？

A: 当文件超过 300 行时，考虑拆分。

### Q: 如何组织大型项目？

A: 按功能域（domain）而不是技术层来组织。

### Q: 如何处理跨模块依赖？

A: 使用 DI 容器和抽象接口。

## 下一步

- 查看 [05-configuration-advanced.md](./05-configuration-advanced.md) 了解高级配置
- 查看 [06-di-container-complete.md](./06-di-container-complete.md) 了解依赖注入



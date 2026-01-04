# 25. 脚手架使用指南

本指南介绍如何使用 Aury Boot 的脚手架快速创建项目和生成代码。

## 快速开始

### 1. 创建新项目

```bash
# 1. 创建项目目录并初始化
mkdir my-service && cd my-service
uv init . --name my_service --no-package --python 3.13

# 2. 安装 Aury Boot
uv add "aury-boot[recommended]"

# 3. 初始化脚手架
aury init                 # 交互式模式（默认），会询问配置选项
aury init -y              # 跳过交互，使用默认配置
aury init my_package      # 使用顶层包结构
aury init --docker        # 同时生成 Docker 配置

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置数据库等

# 5. 启动开发服务器
aury server dev
```

> **注意**：`init` 会覆盖 `uv init` 创建的默认 `main.py`，这是正常行为。

访问 http://localhost:8000 查看效果。

### 2. 生成 CRUD 代码

```bash
# 一键生成完整 CRUD（带字段定义）
aury generate crud user email:str:unique age:int? status:str=active

# 在 main.py 中注册路由
# from api import user
# app.include_router(user.router, prefix="/api/users", tags=["User"])

# 生成数据库迁移
aury migrate make -m "add user table"

# 执行迁移
aury migrate up
```

### 字段语法

```bash
# 格式: name:type:modifiers
# 类型: str, str(100), text, int, bigint, float, decimal, bool, datetime, date, time, json
# 修饰符: ? (可空), unique, index, =默认值

# 更多示例
aury generate crud article title:str(200) content:text status:str=draft
aury generate crud product name:str:unique price:decimal stock:int=0

# 交互式模式
aury generate crud user -i
```

## 交互式模式详解

`aury init` 默认使用交互式模式，会依次询问：

1. **项目结构**
   - 平铺结构：文件直接在项目根目录（简单项目）
   - 顶层包结构：代码在 `my_package/` 目录下（推荐大型项目）

2. **数据库类型**
   - PostgreSQL（推荐生产环境）
   - MySQL
   - SQLite（开发/测试）

3. **缓存类型**
   - 内存缓存（开发用）
   - Redis（生产推荐）

4. **服务模式**
   - `api` - 纯 API 服务
   - `api+scheduler` - API + 内嵌定时任务
   - `full` - API + 定时任务 + 异步任务队列

5. **可选功能**
   - 对象存储（S3/本地）
   - 事件总线
   - 国际化（i18n）

6. **开发工具**（pytest, ruff, mypy）

7. **Docker 配置**（Dockerfile + docker-compose.yml）

配置完成后会显示摘要和推荐的依赖安装命令。

## 项目结构

### 平铺结构（默认）

执行 `aury init` 后：

```
my-service/
├── main.py              # 应用入口
├── config.py            # 配置定义
├── alembic.ini          # Alembic 配置
├── pyproject.toml       # 项目配置（已添加 ruff/pytest/aum 配置）
├── .env.example         # 环境变量模板
├── README.md            # 项目说明
│
├── api/                 # API 层
│   └── __init__.py
│
├── services/            # Service 层（业务逻辑）
│   └── __init__.py
│
├── models/              # Model 层（SQLAlchemy）
│   └── __init__.py
│
├── repositories/        # Repository 层（数据访问）
│   └── __init__.py
│
├── schemas/             # Schema 层（Pydantic）
│   └── __init__.py
│
├── migrations/          # 数据库迁移
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
└── tests/               # 测试
    └── conftest.py
```

### 顶层包结构

执行 `aury init my_package` 后：

```
my-service/
├── my_package/          # 顶层包
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   └── tests/
├── migrations/
├── alembic.ini
├── pyproject.toml
├── .env.example
└── README.md
```

## 分层架构

Aury 采用分层架构，代码生成器会按规范生成代码：

```
┌─────────────────────────────────────────────┐
│                   API 层                     │
│        FastAPI Router / 请求处理            │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│                 Service 层                   │
│             业务逻辑 / 事务管理              │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│               Repository 层                  │
│            数据访问 / CRUD 操作             │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│                 Model 层                     │
│           SQLAlchemy ORM 模型               │
└─────────────────────────────────────────────┘
```

## 代码生成详解

### 生成 Model

```bash
# 基本用法
aury generate model user

# 带字段定义
aury generate model user email:str:unique age:int? status:str=active
```

生成 `models/user.py`：

```python
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from aury.boot.domain.models import AuditableStateModel


class User(AuditableStateModel):
    """User 模型。
    
    继承 AuditableStateModel 自动获得：
    - id: int 自增主键
    - created_at: 创建时间
    - updated_at: 更新时间
    - deleted_at: 软删除时间戳
    """
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(255), default="active")
```

### 生成 Repository

```bash
# 基本用法
aury generate repo user

# 带 unique 字段（自动生成 get_by_xxx 方法）
aury generate repo user email:str:unique
```

生成 `repositories/user_repository.py`：

```python
from aury.boot.domain.repository.impl import BaseRepository

from models.user import User


class UserRepository(BaseRepository[User]):
    """User 仓储。
    
    继承 BaseRepository 自动获得：
    - get(id): 按 ID 获取
    - get_by(**filters): 按条件获取单个
    - list(skip, limit, **filters): 获取列表
    - paginate(params, **filters): 分页获取
    - create(data): 创建
    - update(entity, data): 更新
    - delete(entity, soft=True): 删除
    """
    
    async def get_by_email(self, email: str) -> User | None:
        """按 email 获取。"""
        return await self.get_by(email=email)
```

### 生成 Service

```bash
# 基本用法
aury generate service user

# 带 unique 字段（自动生成重复检测）
aury generate service user email:str:unique
```

生成 `services/user_service.py`：

```python
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.application.errors import AlreadyExistsError, NotFoundError
from aury.boot.domain.service.base import BaseService
from aury.boot.domain.transaction import transactional

from models.user import User
from repositories.user_repository import UserRepository
from schemas.user import UserCreate, UserUpdate


class UserService(BaseService):
    """User 服务。"""
    
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.repo = UserRepository(session, User)
    
    async def get(self, id: str) -> User:
        """获取 User。"""
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"User 不存在", resource=id)
        return entity
    
    @transactional
    async def create(self, data: UserCreate) -> User:
        """创建 User。"""
        # 检查 email 是否已存在（自动生成）
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise AlreadyExistsError(f"User 已存在: {data.email}")
        
        return await self.repo.create(data.model_dump())
    
    # ... 更多方法
```

### 生成 Schema

```bash
aury generate schema user
```

生成 `schemas/user.py`：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """User 基础模型。"""
    
    name: str = Field(..., min_length=1, max_length=100, description="名称")


class UserCreate(UserBase):
    """创建 User 请求。"""
    pass


class UserUpdate(BaseModel):
    """更新 User 请求。"""
    
    name: str | None = Field(None, min_length=1, max_length=100, description="名称")


class UserResponse(UserBase):
    """User 响应。"""
    
    id: str = Field(..., description="ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(from_attributes=True)
```

### 生成 API

```bash
aury generate api user
```

生成 `api/user.py`，包含完整的 CRUD 路由：

- `GET /` - 列表
- `GET /{id}` - 详情
- `POST /` - 创建
- `PUT /{id}` - 更新
- `DELETE /{id}` - 删除

### 一键生成 CRUD

```bash
# 无字段
aury generate crud user

# 带字段定义（推荐）
aury generate crud user email:str:unique age:int? status:str=active

# 交互式
aury generate crud user -i
```

等同于依次执行：

```bash
aury generate model user email:str:unique age:int? status:str=active
aury generate repo user email:str:unique
aury generate service user email:str:unique
aury generate schema user email:str:unique age:int? status:str=active
aury generate api user
```

## 注册路由

生成 API 后，需要在 `main.py` 中注册路由：

```python
# main.py
from api import user

app.include_router(user.router, prefix="/api/users", tags=["User"])
```

## 数据库迁移

生成 Model 后，执行数据库迁移：

```bash
# 生成迁移文件
aury migrate make -m "add user table"

# 执行迁移
aury migrate up

# 查看状态
aury migrate status
```

## 自定义生成的代码

生成的代码是起点，你可以根据需要修改：

### 添加字段

```python
# models/user.py
class User(AuditableStateModel):
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)  # 新增
    age: Mapped[int | None] = mapped_column(nullable=True)  # 新增
```

### 添加自定义查询

```python
# repositories/user_repository.py
class UserRepository(BaseRepository[User]):
    
    async def get_by_email(self, email: str) -> User | None:
        """按邮箱获取。"""
        return await self.get_by(email=email)
    
    async def list_active(self) -> list[User]:
        """获取活跃用户。"""
        return await self.list(is_active=True)
```

### 添加业务逻辑

```python
# services/user_service.py
class UserService(BaseService):
    
    @transactional
    async def register(self, data: UserRegister) -> User:
        """用户注册。"""
        # 检查邮箱
        if await self.repo.get_by_email(data.email):
            raise AlreadyExistsError("邮箱已存在")
        
        # 加密密码
        hashed_password = hash_password(data.password)
        
        # 创建用户
        return await self.repo.create({
            **data.model_dump(exclude={"password"}),
            "password_hash": hashed_password,
        })
```

## 最佳实践

### 1. 命名规范

- Model: `PascalCase`（如 `User`, `UserProfile`）
- 文件: `snake_case`（如 `user.py`, `user_profile.py`）
- 表名: `snake_case` 复数（如 `users`, `user_profiles`）

### 2. 分层职责

- **API 层**：只处理 HTTP 请求/响应，不包含业务逻辑
- **Service 层**：业务逻辑、事务管理、跨 Repository 操作
- **Repository 层**：数据访问、CRUD 操作、查询优化
- **Model 层**：数据结构定义、字段验证

### 3. 错误处理

使用框架提供的异常类：

```python
from aury.boot.application.errors import (
    NotFoundError,
    AlreadyExistsError,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
)
```

### 4. 事务管理

使用 `@transactional` 装饰器：

```python
from aury.boot.domain.transaction import transactional

@transactional
async def create_user_with_profile(self, data):
    user = await self.user_repo.create(data.user)
    profile = await self.profile_repo.create({
        "user_id": user.id,
        **data.profile,
    })
    return user, profile
```

## 常见问题

### Q: 如何覆盖已存在的文件？

使用 `--force` 选项：

```bash
aury generate crud user --force
```

### Q: 如何生成不同类型的主键？

使用 `--base` 选项指定基类：

```bash
# int 主键 + 软删除（默认推荐）
aury generate crud user -b AuditableStateModel

# int 主键 + 时间戳（无软删除）
aury generate crud user -b Model

# int 主键 + 完整功能
aury generate crud user -b FullFeaturedModel

# UUID 主键（如果需要）
aury generate crud user -b UUIDAuditableStateModel
```

可用基类：
- `IDOnlyModel` - 纯 int 主键（无时间戳）
- `UUIDOnlyModel` - 纯 UUID 主键（无时间戳）
- `Model` - int 主键 + 时间戳
- `AuditableStateModel` - int 主键 + 软删除（默认推荐）
- `UUIDModel` - UUID 主键 + 时间戳
- `UUIDAuditableStateModel` - UUID 主键 + 软删除
- `VersionedModel` - int 主键 + 乐观锁
- `VersionedTimestampedModel` - int 主键 + 乐观锁 + 时间戳
- `VersionedUUIDModel` - UUID 主键 + 乐观锁
- `FullFeaturedModel` - int 主键 + 全功能（推荐）
- `FullFeaturedUUIDModel` - UUID 主键 + 全功能

### Q: 如何自定义模板？

目前不支持自定义模板。如有需求，可以：
1. 生成后手动修改
2. 提交 Issue 或 PR

## 下一步

- 查看 [24-cli-commands.md](./24-cli-commands.md) 了解完整命令参考
- 查看 [12-database-complete.md](./12-database-complete.md) 了解数据库操作
- 查看 [11-transaction-management.md](./11-transaction-management.md) 了解事务管理

# {project_name} 开发指南

本文档基于 [AuriMyth Foundation Kit](https://github.com/AuriMythNeo/aurimyth-foundation-kit) 框架。

CLI 命令参考请查看 [CLI.md](./CLI.md)。

---

## 目录结构

```
{project_name}/
├── app/              # 代码包（默认 app，可通过 aum init <pkg> 自定义）
│   ├── models/       # SQLAlchemy ORM 模型
│   ├── repositories/ # 数据访问层
│   ├── services/     # 业务逻辑层
│   ├── schemas/      # Pydantic 请求/响应模型
│   ├── api/          # FastAPI 路由
│   ├── exceptions/   # 业务异常
│   ├── tasks/        # 异步任务（Dramatiq）
│   └── schedules/    # 定时任务（Scheduler）
├── tests/            # 测试
├── migrations/       # 数据库迁移
└── main.py           # 应用入口
```

---

## 1. Model（数据模型）

### 1.1 模型基类选择

框架提供多种预组合基类，按需选择：

| 基类 | 主键 | 时间戳 | 软删除 | 乐观锁 | 场景 |
|------|------|--------|--------|--------|------|
| `Model` | int | ✓ | ✗ | ✗ | 简单实体 |
| `AuditableStateModel` | int | ✓ | ✓ | ✗ | 需软删除 |
| `UUIDModel` | UUID | ✓ | ✗ | ✗ | 分布式 |
| `UUIDAuditableStateModel` | UUID | ✓ | ✓ | ✗ | **推荐** |
| `VersionedModel` | int | ✗ | ✗ | ✓ | 乐观锁 |
| `VersionedUUIDModel` | UUID | ✓ | ✗ | ✓ | UUID+乐观锁 |
| `FullFeaturedUUIDModel` | UUID | ✓ | ✓ | ✓ | 全功能 |

### 1.2 基类自动提供的字段

**IDMixin** (int 主键):
```python
id: Mapped[int]  # 自增主键
```

**UUIDMixin** (UUID 主键):
```python
import uuid
from sqlalchemy.types import Uuid as SQLAlchemyUuid
from sqlalchemy.orm import Mapped, mapped_column

id: Mapped[uuid.UUID] = mapped_column(
    SQLAlchemyUuid(as_uuid=True),  # SQLAlchemy 2.0 自动适配 PG(uuid) 和 MySQL(char(36))
    primary_key=True,
    default=uuid.uuid4,
)
```

> **关于 SQLAlchemyUuid**：
> - 使用 `sqlalchemy.types.Uuid`（导入为 `SQLAlchemyUuid`）而非直接使用 `uuid.UUID`
> - `as_uuid=True` 确保 Python 层面使用 UUID 对象而非字符串
> - 框架会自动适配不同数据库：PostgreSQL 使用原生 UUID 类型，MySQL/SQLite 使用 CHAR(36)
> - 如需手动定义 UUID 字段，请使用 `SQLAlchemyUuid(as_uuid=True)` 而非 `Uuid(as_uuid=True)`

**TimestampMixin** (时间戳):
```python
created_at: Mapped[datetime]  # 创建时间，自动设置
updated_at: Mapped[datetime]  # 更新时间，自动更新
```

**AuditableStateMixin** (软删除):
```python
deleted_at: Mapped[int]  # 删除时间戳，0=未删除，>0=删除时间
# 自动提供：is_deleted 属性、mark_deleted() 方法、restore() 方法
```

> **注意**：使用软删除的模型不要单独使用 `unique=True`，否则删除后再插入相同值会报错。
> 应使用复合唯一索引：`UniqueConstraint("email", "deleted_at", name="uq_users_email_deleted")`

**VersionMixin** (乐观锁):
```python
version: Mapped[int]  # 版本号，自动管理
```

### 1.3 Model 编写示例

**文件**: `app/models/user.py`

```python
"""User 数据模型。"""

from sqlalchemy import String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aurimyth.foundation_kit.domain.models import UUIDAuditableStateModel


class User(UUIDAuditableStateModel):
    """User 模型。

    继承 UUIDAuditableStateModel 自动获得：
    - id: UUID 主键（使用 SQLAlchemyUuid 自动适配数据库）
    - created_at, updated_at: 时间戳
    - deleted_at: 软删除支持
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="用户名")
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="邮箱")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")

    # 软删除模型必须使用复合唯一约束（包含 deleted_at），避免删除后无法插入相同值
    # 注意：复合约束必须使用 __table_args__，这是 SQLAlchemy 的要求
    __table_args__ = (
        UniqueConstraint("email", "deleted_at", name="uq_users_email_deleted"),
    )
```

### 1.4 字段类型映射

| Python 类型 | SQLAlchemy 类型 | 说明 |
|-------------|----------------|------|
| `str` | `String(length)` | 必须指定长度 |
| `int` | `Integer` | 整数 |
| `float` | `Float` | 浮点数 |
| `bool` | `Boolean` | 布尔值 |
| `datetime` | `DateTime(timezone=True)` | 带时区 |
| `date` | `Date` | 日期 |
| `Decimal` | `Numeric(precision, scale)` | 精确小数 |
| `dict`/`list` | `JSON` | JSON 数据 |
| `uuid.UUID` | `SQLAlchemyUuid(as_uuid=True)` | UUID（推荐使用 `from sqlalchemy.types import Uuid as SQLAlchemyUuid`） |

### 1.5 常用字段约束

```python
from sqlalchemy import String, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

class Example(UUIDAuditableStateModel):
    __tablename__ = "examples"
    
    # 可选字段
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # 带默认值
    status: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    
    # 单列索引：直接在 mapped_column 中使用 index=True（推荐）
    code: Mapped[str] = mapped_column(String(50), index=True, comment="编码")
    
    # 单列唯一约束：直接在 mapped_column 中使用 unique=True（仅非软删除模型）
    # 注意：软删除模型不能单独使用 unique=True，必须使用复合唯一约束
    
    # 外键关联
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    category: Mapped["Category"] = relationship(back_populates="examples")
    
    # 复合索引和复合唯一约束：必须使用 __table_args__（SQLAlchemy 要求）
    # 软删除模型必须使用复合唯一约束（包含 deleted_at），避免删除后无法插入相同值
    __table_args__ = (
        Index("ix_examples_status_created", "status", "created_at"),  # 复合索引
        UniqueConstraint("code", "deleted_at", name="uq_examples_code_deleted"),  # 复合唯一约束
    )


# 非软删除模型可以直接使用 unique=True 和 index=True
class Config(UUIDModel):  # UUIDModel 不包含软删除
    __tablename__ = "configs"
    
    # 单列唯一约束：直接在 mapped_column 中使用（推荐）
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="配置键")
    value: Mapped[str] = mapped_column(String(500), comment="配置值")
    
    # 单列索引：直接在 mapped_column 中使用（推荐）
    name: Mapped[str] = mapped_column(String(100), index=True, comment="配置名称")
```

**约束定义最佳实践**：

1. **单列索引**：使用 `index=True` 在 `mapped_column` 中（推荐）
   ```python
   email: Mapped[str] = mapped_column(String(255), index=True)
   ```

2. **单列唯一约束**：
   - 非软删除模型：使用 `unique=True` 在 `mapped_column` 中（推荐）
   - 软删除模型：必须使用复合唯一约束（包含 `deleted_at`）

3. **复合索引/唯一约束**：必须使用 `__table_args__`（SQLAlchemy 要求）
   ```python
   __table_args__ = (
       Index("ix_name", "col1", "col2"),  # 复合索引
       UniqueConstraint("col1", "col2", name="uq_name"),  # 复合唯一约束
   )
   ```

---

## 2. Repository（数据访问层）

### 2.1 Repository 编写示例

**文件**: `app/repositories/user_repository.py`

```python
"""User 数据访问层。"""

from aurimyth.foundation_kit.domain.repository.impl import BaseRepository

from app.models.user import User


class UserRepository(BaseRepository[User]):
    """User 仓储。

    继承 BaseRepository 自动获得：
    - get(id): 按 ID 获取
    - get_by(**filters): 按条件获取单个
    - list(skip, limit, **filters): 获取列表
    - paginate(params, **filters): 分页获取
    - count(**filters): 计数
    - exists(**filters): 是否存在
    - create(data): 创建
    - update(entity, data): 更新
    - delete(entity, soft=True): 删除（默认软删除）
    - batch_create(data_list): 批量创建
    - bulk_insert(data_list): 高性能批量插入
    """

    async def get_by_email(self, email: str) -> User | None:
        """按邮箱查询用户。"""
        return await self.get_by(email=email)

    async def list_active(self, skip: int = 0, limit: int = 100) -> list[User]:
        """获取激活用户列表。"""
        return await self.list(skip=skip, limit=limit, is_active=True)
```

### 2.2 BaseRepository 方法详解

```python
from sqlalchemy.ext.asyncio import AsyncSession

# 初始化（默认 auto_commit=True）
repo = UserRepository(session, User)

# === 查询 ===
user = await repo.get(user_id)                    # 按 ID（支持 int/UUID）
user = await repo.get_by(email="a@b.com")         # 按条件（简单 AND 过滤）
users = await repo.list(skip=0, limit=10)         # 列表
users = await repo.list(is_active=True)           # 带过滤
count = await repo.count(is_active=True)          # 计数
exists = await repo.exists(email="a@b.com")       # 是否存在

# === 分页 ===
from aurimyth.foundation_kit.domain.pagination import PaginationParams, SortParams

result = await repo.paginate(
    pagination_params=PaginationParams(page=1, size=20),
    sort_params=SortParams(sorts=[("created_at", "desc")]),
    is_active=True,
)
# result.items, result.total, result.page, result.size, result.pages

# === 创建 ===
user = await repo.create({{"name": "Alice", "email": "a@b.com"}})
users = await repo.batch_create([{{"name": "A"}}, {{"name": "B"}}])  # 返回实体
await repo.bulk_insert([{{"name": "A"}}, {{"name": "B"}}])           # 高性能，无返回

# === 更新 ===
user = await repo.update(user, {{"name": "Bob"}})

# === 删除 ===
await repo.delete(user)              # 软删除
await repo.delete(user, soft=False)  # 硬删除
await repo.hard_delete(user)         # 硬删除别名
deleted = await repo.delete_by_id(user_id)  # 按 ID 删除
```

#### 2.2.1 Filters 语法（增强）

BaseRepository 的 `get_by/list/paginate/count/exists` 的 `**filters` 支持下列操作符（与 `QueryBuilder.filter` 对齐）：
- `__gt`, `__lt`, `__gte`, `__lte`, `__in`, `__like`, `__ilike`, `__isnull`, `__ne`

示例：

```python
# 模糊匹配 + 范围 + IN + 为空判断（条件之间为 AND 关系）
users = await repo.list(
    name__ilike="%foo%",
    age__gte=18,
    id__in=[u1, u2, u3],
    deleted_at__isnull=True,
)

# 单个实体（不等于）
user = await repo.get_by(status__ne="archived")
```

> 注意：filters 条件之间用 AND 组合；如需 AND/OR/NOT 的复杂组合，请使用 `QueryBuilder`（见 2.4）。

#### 2.2.2 查询全部（limit=None）

`list()` 支持 `limit=None` 返回全部记录（谨慎使用大表）：

```python
all_users = await repo.list(limit=None)                 # 全量
active_all = await repo.list(limit=None, is_active=True)
```

### 2.3 自动提交机制

BaseRepository 支持智能的自动提交机制，优于 Django 的设计：

| 场景 | 行为 |
|------|------|
| 非事务中 + `auto_commit=True` | 写操作后自动 commit |
| 非事务中 + `auto_commit=False` | 只 flush，需手动管理或使用 `.with_commit()` |
| 在事务中（`@transactional` 等） | **永不自动提交**，由事务统一管理 |

```python
# 默认行为：非事务中自动提交
repo = UserRepository(session, User)  # auto_commit=True
await repo.create({{"name": "test"}})  # 自动 commit

# 禁用自动提交
repo = UserRepository(session, User, auto_commit=False)
await repo.create({{"name": "test"}})  # 只 flush，不 commit

# 单次强制提交（auto_commit=False 时）
await repo.with_commit().create({{"name": "test2"}})  # 强制 commit

# 在事务中：无论 auto_commit 是什么，都不会自动提交
@transactional
async def create_with_profile(session: AsyncSession):
    repo = UserRepository(session, User)  # auto_commit=True 但不生效
    user = await repo.create({{"name": "a"}})  # 只 flush
    profile = await profile_repo.create({{"user_id": user.id}})  # 只 flush
    # 事务结束时统一 commit
```

**设计优势**（对比 Django）：
- Django：每个 `save()` 默认独立事务，容易无意识地失去原子性
- Foundation Kit：默认自动提交，但**事务上下文自动接管**，更显式可控

### 2.4 复杂查询示例

```python
async def search_users(
    self, 
    keyword: str | None = None,
    status: int | None = None,
) -> list[User]:
    """复杂搜索。"""
    query = self.query()  # 自动排除软删除
    
    if keyword:
        # 使用 QueryBuilder 的 or_ 与 filter_by 组合复杂条件
        query = query.filter_by(
            query.or_(
                User.name.ilike(f"%{{keyword}}%"),
                User.email.ilike(f"%{{keyword}}%"),
            )
        )
    
    if status is not None:
        # 简单等值可直接使用 filter（支持 **kwargs）
        query = query.filter(status=status)
    
    query = query.order_by("-created_at").limit(100)
    result = await self.session.execute(query.build())
    return list(result.scalars().all())
```

---

## 3. Service（业务逻辑层）

### 3.1 Service 编写示例

**文件**: `app/services/user_service.py`

```python
"""User 业务逻辑层。"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aurimyth.foundation_kit.application.errors import AlreadyExistsError, NotFoundError
from aurimyth.foundation_kit.domain.service.base import BaseService
from aurimyth.foundation_kit.domain.transaction import transactional

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService(BaseService):
    """User 服务。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.repo = UserRepository(session, User)

    async def get(self, id: UUID) -> User:
        """获取 User。"""
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError("User 不存在", resource=id)
        return entity

    async def list(self, skip: int = 0, limit: int = 100) -> list[User]:
        """获取 User 列表。"""
        return await self.repo.list(skip=skip, limit=limit)

    @transactional
    async def create(self, data: UserCreate) -> User:
        """创建 User。"""
        if await self.repo.exists(email=data.email):
            raise AlreadyExistsError(f"邮箱 {{data.email}} 已存在")
        return await self.repo.create(data.model_dump())

    @transactional
    async def update(self, id: UUID, data: UserUpdate) -> User:
        """更新 User。"""
        entity = await self.get(id)
        return await self.repo.update(entity, data.model_dump(exclude_unset=True))

    @transactional
    async def delete(self, id: UUID) -> None:
        """删除 User。"""
        entity = await self.get(id)
        await self.repo.delete(entity)
```

### 3.2 跨 Service 调用（事务共享）

```python
class OrderService(BaseService):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.order_repo = OrderRepository(session, Order)
        # 复用 session 实现事务共享
        self.user_service = UserService(session)
        self.inventory_service = InventoryService(session)
    
    @transactional
    async def create_order(self, data: OrderCreate) -> Order:
        """创建订单（跨 Service 事务）。"""
        user = await self.user_service.get(data.user_id)
        await self.inventory_service.deduct(data.product_id, data.quantity)
        order = await self.order_repo.create(...)
        return order  # 整个流程在同一事务中
```

---

## 4. Schema（Pydantic 模型）

### 4.1 Schema 编写示例

**文件**: `app/schemas/user.py`

```python
"""User Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class UserBase(BaseModel):
    """User 基础模型。"""
    name: str = Field(..., min_length=1, max_length=100, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    is_active: bool = Field(default=True, description="是否激活")


class UserCreate(UserBase):
    """创建 User 请求。"""
    password: str = Field(..., min_length=6, description="密码")


class UserUpdate(BaseModel):
    """更新 User 请求（所有字段可选）。"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """User 响应。"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 4.2 Schema 使用说明

Schema（Pydantic 模型）在框架中扮演三个角色：

1. **请求验证**：验证 API 请求数据（Create/Update）
2. **响应序列化**：将 ORM 模型转换为 JSON 响应（Response）
3. **类型提示**：为 Service 层提供类型安全

**数据流转**：
```
API 请求 → Schema 验证 → Service 处理 → Repository 操作 → ORM Model
                ↓                                              ↓
          model_dump()                            model_validate()
                                                               ↓
                                                      Response Schema → JSON 响应
```

**关键方法**：
- `model_dump()`：将 Schema 转为字典（传给 Repository）
- `model_dump(exclude_unset=True)`：只转换设置过的字段（用于更新）
- `model_validate(orm_obj)`：从 ORM 模型创建 Schema（需要 `from_attributes=True`）

> **重要提示**：不要自定义通用响应 Schema（如 `OkResponse`、`ErrorResponse`）。
> 框架已内置 `BaseResponse` 和 `PaginationResponse`，直接使用即可。
> 异常响应由全局异常处理中间件自动处理，无需手动定义。

### 4.3 常用验证

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class ExampleSchema(BaseModel):
    # 长度限制
    name: str = Field(..., min_length=1, max_length=100)
    
    # 数值范围
    age: int = Field(..., ge=0, le=150)
    price: float = Field(..., gt=0)
    
    # 正则验证
    phone: str = Field(..., pattern=r"^1[3-9]\d{{9}}$")
    
    # 枚举
    status: Literal["active", "inactive", "pending"]
    
    # 字段验证器
    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str) -> str:
        return v.strip()
```

---

## 5. API（路由层）

### 5.1 API 编写示例

**文件**: `app/api/user.py`

```python
"""User API 路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from aurimyth.foundation_kit.application.interfaces.egress import (
    BaseResponse,
    Pagination,
    PaginationResponse,
)
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager

from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/v1/users", tags=["User"])
db_manager = DatabaseManager.get_instance()


async def get_service(
    session: AsyncSession = Depends(db_manager.get_session),
) -> UserService:
    return UserService(session)


@router.get("", response_model=PaginationResponse[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 20,
    service: UserService = Depends(get_service),
) -> PaginationResponse[UserResponse]:
    """获取列表。"""
    items = await service.list(skip=skip, limit=limit)
    return PaginationResponse(
        code=200,
        message="获取成功",
        data=Pagination(
            total=len(items),
            items=[UserResponse.model_validate(item) for item in items],
            page=skip // limit + 1,
            size=limit,
        ),
    )


@router.get("/{{id}}", response_model=BaseResponse[UserResponse])
async def get_user(
    id: UUID,
    service: UserService = Depends(get_service),
) -> BaseResponse[UserResponse]:
    """获取详情。"""
    entity = await service.get(id)
    return BaseResponse(
        code=200,
        message="获取成功",
        data=UserResponse.model_validate(entity),
    )


@router.post("", response_model=BaseResponse[UserResponse])
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_service),
) -> BaseResponse[UserResponse]:
    """创建。"""
    entity = await service.create(data)
    return BaseResponse(
        code=200,
        message="创建成功",
        data=UserResponse.model_validate(entity),
    )


@router.put("/{{id}}", response_model=BaseResponse[UserResponse])
async def update_user(
    id: UUID,
    data: UserUpdate,
    service: UserService = Depends(get_service),
) -> BaseResponse[UserResponse]:
    """更新。"""
    entity = await service.update(id, data)
    return BaseResponse(
        code=200,
        message="更新成功",
        data=UserResponse.model_validate(entity),
    )


@router.delete("/{{id}}", response_model=BaseResponse[None])
async def delete_user(
    id: UUID,
    service: UserService = Depends(get_service),
) -> BaseResponse[None]:
    """删除。"""
    await service.delete(id)
    return BaseResponse(code=200, message="删除成功", data=None)
```

### 5.2 注册路由

```python
from fastapi import FastAPI
from app.api.user import router as user_router

app = FastAPI()
app.include_router(user_router)
```

---

## 核心组件使用

---

## 6. 数据库事务

### 6.1 事务装饰器（推荐）

```python
from aurimyth.foundation_kit.domain.transaction import transactional
from sqlalchemy.ext.asyncio import AsyncSession

# 自动识别 session 参数，自动提交/回滚
@transactional
async def create_user(session: AsyncSession, name: str, email: str):
    """创建用户，自动在事务中执行。"""
    repo = UserRepository(session)
    user = await repo.create({{"name": name, "email": email}})
    # 成功：自动 commit
    # 异常：自动 rollback
    return user

# 在类方法中使用（自动识别 self.session）
class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @transactional
    async def create_with_profile(self, name: str):
        """自动使用 self.session。"""
        user = await self.repo.create({{"name": name}})
        await self.profile_repo.create({{"user_id": user.id}})
        return user
```

### 6.2 事务上下文管理器

```python
from aurimyth.foundation_kit.domain.transaction import transactional_context
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager

db = DatabaseManager.get_instance()

async with db.session() as session:
    async with transactional_context(session):
        repo1 = UserRepository(session)
        repo2 = ProfileRepository(session)
        
        user = await repo1.create({{"name": "Alice"}})
        await repo2.create({{"user_id": user.id}})
        # 自动提交或回滚
```

### 6.3 事务传播（嵌套事务）

框架自动支持嵌套事务，内层事务会复用外层事务：

```python
@transactional
async def outer_operation(session: AsyncSession):
    """外层事务。"""
    repo1 = UserRepository(session)
    user = await repo1.create({{"name": "Alice"}})
    
    # 嵌套调用另一个 @transactional 函数
    result = await inner_operation(session)
    # 不会重复开启事务，复用外层事务
    # 只有外层事务提交时才会真正提交
    
    return user, result

@transactional
async def inner_operation(session: AsyncSession):
    """内层事务，自动复用外层事务。"""
    repo2 = OrderRepository(session)
    return await repo2.create({{"user_id": 1}})
    # 检测到已在事务中，直接执行，不重复提交
```

**传播行为**：
- 如果已在事务中：直接执行，不开启新事务
- 如果不在事务中：开启新事务，自动提交/回滚
- 嵌套事务共享同一个数据库连接和事务上下文

### 6.4 非事务的数据库使用

对于只读操作或不需要事务的场景，可以直接使用 session：

```python
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager

db = DatabaseManager.get_instance()

# 方式 1：使用 session 上下文管理器（推荐）
async with db.session() as session:
    repo = UserRepository(session)
    # 只读操作，不需要事务
    users = await repo.list(skip=0, limit=10)
    user = await repo.get(1)

# 方式 2：在 FastAPI 路由中使用（自动注入）
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/users")
async def list_users(
    session: AsyncSession = Depends(db.get_session),
):
    """只读操作，不需要事务。"""
    repo = UserRepository(session)
    return await repo.list()

# 方式 3：手动控制（需要手动关闭）
session = await db.create_session()
try:
    repo = UserRepository(session)
    users = await repo.list()
finally:
    await session.close()
```

**何时使用非事务**：
- 只读查询（SELECT）
- 不需要原子性的操作
- 性能敏感的场景（避免事务开销）

**何时必须使用事务**：
- 写操作（INSERT/UPDATE/DELETE）
- 需要原子性的多个操作
- 需要回滚的场景

### 6.5 写入不使用事务装饰器

某些场景下，你可能希望在 Service 内不加 `@transactional`，而由上层控制事务边界：

```python
# 场景：Service 内部不加装饰器，由调用方控制事务
class UserWriteService(BaseService):
    async def create_no_tx(self, data: UserCreate) -> User:
        if await self.repo.exists(email=data.email):
            raise AlreadyExistsError(f"邮箱 {{data.email}} 已存在")
        # 只做 flush/refresh，不做 commit
        return await self.repo.create(data.model_dump())


# 调用方显式管理事务边界
async def create_user_flow(session: AsyncSession, data: UserCreate) -> User:
    service = UserWriteService(session)
    try:
        user = await service.create_no_tx(data)
        await session.commit()
        return user
    except Exception:
        await session.rollback()
        raise


# 或使用 transactional_context
from aurimyth.foundation_kit.domain.transaction import transactional_context

async def create_user_flow(session: AsyncSession, data: UserCreate) -> User:
    async with transactional_context(session):
        service = UserWriteService(session)
        return await service.create_no_tx(data)
```

适用场景：
- 一个用例调用多个 Service，统一提交
- 手动控制 commit 时机（分步 flush、条件提交）
- 上层已有事务边界（如作业层）

### 6.6 Savepoints（保存点）

保存点允许在事务中设置回滚点，实现部分回滚而不影响整个事务：

```python
from aurimyth.foundation_kit.domain.transaction import TransactionManager

async def complex_operation(session: AsyncSession):
    """使用保存点实现部分回滚。"""
    tm = TransactionManager(session)
    
    await tm.begin()
    repo = UserRepository(session)
    
    try:
        # 第一步：创建主记录
        user = await repo.create({{"name": "alice"}})
        
        # 创建保存点
        sp_id = await tm.savepoint("before_optional")
        
        try:
            # 第二步：可选操作（可能失败）
            await risky_operation(session)
            # 成功：提交保存点
            await tm.savepoint_commit(sp_id)
        except RiskyOperationError:
            # 失败：回滚到保存点，但 user 创建仍然保留
            await tm.savepoint_rollback(sp_id)
            logger.warning("可选操作失败，已回滚，继续主流程")
        
        # 第三步：继续其他操作（不受保存点回滚影响）
        await repo.update(user.id, {{"status": "active"}})
        
        await tm.commit()
        return user
    except Exception:
        await tm.rollback()
        raise
```

**保存点 API**：
- `savepoint(name)` - 创建保存点，返回保存点 ID
- `savepoint_commit(sp_id)` - 提交保存点（释放保存点，变更生效）
- `savepoint_rollback(sp_id)` - 回滚到保存点（撤销保存点后的变更）

### 6.7 on_commit 回调

注册在事务成功提交后执行的回调函数，适合发送通知、触发后续任务等副作用操作：

```python
from aurimyth.foundation_kit.domain.transaction import transactional, on_commit

@transactional
async def create_order(session: AsyncSession, order_data: dict):
    """创建订单并在提交后发送通知。"""
    repo = OrderRepository(session)
    order = await repo.create(order_data)
    
    # 注册回调：事务成功后执行
    on_commit(lambda: send_order_notification(order.id))
    on_commit(lambda: update_inventory_cache(order.items))
    
    # 如果后续发生异常导致回滚，回调不会执行
    await validate_order(order)
    
    return order
    # 事务 commit 后，所有 on_commit 回调按注册顺序执行
```

**在 TransactionManager 中使用**：

```python
async def manual_with_callback(session: AsyncSession):
    tm = TransactionManager(session)
    
    await tm.begin()
    try:
        user = await create_user(session)
        tm.on_commit(lambda: print(f"用户 {{user.id}} 创建成功"))
        await tm.commit()  # 提交后执行回调
    except Exception:
        await tm.rollback()  # 回滚时回调被清除，不执行
        raise
```

**回调特性**：
- 事务成功 `commit()` 后立即执行
- 事务回滚时，已注册的回调被清除，不执行
- 按注册顺序执行
- 同步和异步函数都支持

### 6.8 SELECT FOR UPDATE（行级锁）

在并发场景下锁定查询的行，防止其他事务修改：

```python
from aurimyth.foundation_kit.domain.repository.query_builder import QueryBuilder

class AccountRepository(BaseRepository[Account]):
    async def get_for_update(self, account_id: str) -> Account | None:
        """获取并锁定账户记录。"""
        qb = QueryBuilder(Account)
        query = qb.filter(Account.id == account_id).for_update().build()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_for_update_nowait(self, account_id: str) -> Account | None:
        """获取并锁定，如果已被锁定则立即失败。"""
        qb = QueryBuilder(Account)
        query = qb.filter(Account.id == account_id).for_update(nowait=True).build()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_for_update_skip_locked(self, ids: list[str]) -> list[Account]:
        """获取并锁定，跳过已被锁定的行。"""
        qb = QueryBuilder(Account)
        query = qb.filter(Account.id.in_(ids)).for_update(skip_locked=True).build()
        result = await self.session.execute(query)
        return list(result.scalars().all())
```

**for_update 参数**：
- `nowait=True` - 如果行已被锁定，立即报错而不是等待
- `skip_locked=True` - 跳过已被锁定的行（常用于队列场景）
- `of=(Column,...)` - 指定锁定的列（用于 JOIN 场景）

**注意**：`nowait` 和 `skip_locked` 互斥，不能同时使用。

### 6.9 事务隔离级别配置

通过环境变量配置数据库的默认事务隔离级别：

```bash
# .env
DATABASE_ISOLATION_LEVEL=REPEATABLE READ
```

**支持的隔离级别**：
- `READ UNCOMMITTED` - 最低隔离，可读未提交数据（脏读）
- `READ COMMITTED` - 只读已提交数据（PostgreSQL/Oracle 默认）
- `REPEATABLE READ` - 可重复读，同一事务内读取结果一致（MySQL 默认）
- `SERIALIZABLE` - 最高隔离，完全串行化执行
- `AUTOCOMMIT` - 每条语句自动提交

**选择建议**：
- 大多数场景：`READ COMMITTED`（平衡性能和一致性）
- 报表/统计查询：`REPEATABLE READ`（保证读取一致性）
- 金融交易：`SERIALIZABLE`（最强一致性，性能较低）

---

## 7. 缓存

```python
from aurimyth.foundation_kit.infrastructure.cache import CacheManager, cached

# 方式 1：装饰器
@cached(ttl=300)  # 缓存 5 分钟
async def get_user(user_id: int):
    ...

# 方式 2：手动操作
cache = CacheManager.get_instance()
await cache.set("key", value, ttl=300)
value = await cache.get("key")
await cache.delete("key")
```

---

## 8. 定时任务（Scheduler）

**文件**: `app/schedules/__init__.py`

```python
"""定时任务模块。"""

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.infrastructure.scheduler import SchedulerManager

scheduler = SchedulerManager.get_instance()


@scheduler.scheduled_job("interval", seconds=60)
async def every_minute():
    """每 60 秒执行。"""
    logger.info("定时任务执行中...")


@scheduler.scheduled_job("cron", hour=0, minute=0)
async def daily_task():
    """每天凌晨执行。"""
    logger.info("每日任务执行中...")


@scheduler.scheduled_job("cron", day_of_week="mon", hour=9)
async def weekly_report():
    """每周一 9 点执行。"""
    logger.info("周报任务执行中...")
```

启用方式：配置 `SCHEDULER_ENABLED=true`，框架自动加载 `app/schedules/` 模块。

---

## 9. 异步任务（Dramatiq）

**文件**: `app/tasks/__init__.py`

```python
"""异步任务模块。"""

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.infrastructure.tasks import conditional_task


@conditional_task
def send_email(to: str, subject: str, body: str):
    """异步发送邮件。"""
    logger.info(f"发送邮件到 {{to}}: {{subject}}")
    # 实际发送逻辑...
    return {{"status": "sent"}}


@conditional_task
def process_order(order_id: str):
    """异步处理订单。"""
    logger.info(f"处理订单: {{order_id}}")
```

调用方式：

```python
# 异步执行（发送到队列）
send_email.send("user@example.com", "Hello", "World")

# 延迟执行
send_email.send_with_options(args=("user@example.com", "Hello", "World"), delay=60000)  # 60秒后
```

启用方式：
1. 配置 `TASK_BROKER_URL`（如 `redis://localhost:6379/0`）
2. 运行 Worker：`aum worker`

---

## 10. 对象存储（基于 aurimyth-storage-sdk）

### 10.1 安装

```bash
# 完整安装（S3/COS/OSS + STS 支持）
uv add "aurimyth-storage-sdk[aws]"
# 或
pip install "aurimyth-storage-sdk[aws]"
```

### 10.2 基本用法（StorageManager）

```python
from io import BytesIO
from aurimyth.foundation_kit.infrastructure.storage import (
    StorageManager, StorageConfig, StorageBackend, StorageFile,
)

# 初始化（一般由 StorageComponent 自动完成，以下仅演示手动调用）
storage = StorageManager.get_instance()
await storage.init(StorageConfig(
    backend=StorageBackend.COS,
    bucket_name="my-bucket-1250000000",
    region="ap-guangzhou",
    endpoint="https://cos.ap-guangzhou.myqcloud.com",
    access_key_id="AKIDxxxxx",
    access_key_secret="xxxxx",
))

# 上传文件（返回 URL）
url = await storage.upload_file(
    StorageFile(
        object_name="user/123/avatar.png",
        data=BytesIO(image_bytes),
        content_type="image/png",
    )
)

# 下载文件
content = await storage.download_file("user/123/avatar.png")

# 获取预签名 URL
url = await storage.get_file_url("user/123/avatar.png", expires_in=3600)

# 检查文件是否存在
exists = await storage.file_exists("user/123/avatar.png")

# 删除文件
await storage.delete_file("user/123/avatar.png")
```

### 10.3 STS 临时凭证（前端直传）

```python
from aurimyth_storage_sdk.sts import (
    STSProviderFactory, ProviderType, STSRequest, ActionType,
)

# 创建腾讯云 STS Provider
provider = STSProviderFactory.create(
    ProviderType.TENCENT,
    secret_id="AKIDxxxxx",
    secret_key="xxxxx",
)

# 签发临时上传凭证
credentials = await provider.get_credentials(
    STSRequest(
        bucket="my-bucket-1250000000",
        region="ap-guangzhou",
        allow_path="user/123/",
        action_type=ActionType.WRITE,
        duration_seconds=900,
    )
)

# 返回给前端
return {{
    "accessKeyId": credentials.access_key_id,
    "secretAccessKey": credentials.secret_access_key,
    "sessionToken": credentials.session_token,
    "expiration": credentials.expiration.isoformat(),
    "bucket": credentials.bucket,
    "region": credentials.region,
    "endpoint": credentials.endpoint,
}}
```

### 10.4 本地存储（开发测试）

```python
from aurimyth.foundation_kit.infrastructure.storage import (
    StorageManager, StorageConfig, StorageBackend, StorageFile,
)

storage = StorageManager.get_instance()
await storage.init(StorageConfig(
    backend=StorageBackend.LOCAL,
    base_path="./dev_storage",
))

url = await storage.upload_file(
    StorageFile(object_name="test.txt", data=b"hello")
)
# url: file:///path/to/dev_storage/default/test.txt
```

---

## 11. 日志

```python
from aurimyth.foundation_kit.common.logging import logger

logger.info("操作成功")
logger.warning("警告信息")
logger.error("错误信息", exc_info=True)

# 绑定上下文
logger.bind(user_id=123).info("用户操作")
```

---

## 12. 管理后台（Admin Console，基于 SQLAdmin）

默认提供可选的 SQLAdmin 后台（组件自动装配）。启用后路径默认为 `/api/admin-console`。

- 组件开关与配置由环境变量控制；启用后框架会在启动时自动挂载后台路由。
- SQLAdmin 通常需要同步 SQLAlchemy Engine；如果你使用的是异步 `DATABASE_URL`，建议单独设置同步的 `ADMIN_DATABASE_URL`（框架也会尝试自动推导常见驱动映射）。

快速启用（.env）

```bash
# 启用与基本路径
ADMIN_ENABLED=true
ADMIN_PATH=/api/admin-console

# 认证（二选一，推荐 basic 或 bearer）
ADMIN_AUTH_MODE=basic
ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
ADMIN_AUTH_BASIC_USERNAME=admin
ADMIN_AUTH_BASIC_PASSWORD=change_me

# 如果使用 bearer
# ADMIN_AUTH_MODE=bearer
# ADMIN_AUTH_SECRET_KEY=CHANGE_ME
# ADMIN_AUTH_BEARER_TOKENS=["token1","token2"]

# 如需显式提供同步数据库 URL（可选）
# ADMIN_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/{project_name_snake}
```

注册后台视图（在 `admin_console.py` 内）

```python
from sqladmin import ModelView
from {project_name_snake}.models.user import User

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email]

# 方式一：声明式（简单）
ADMIN_VIEWS = [UserAdmin]

# 方式二：函数注册（更灵活）
# def register_admin(admin):
#     admin.add_view(UserAdmin)
```

自定义认证（可选，高阶）
- 通过 `ADMIN_AUTH_BACKEND=module:attr` 指定自定义 backend；或在 `admin_console.py` 实现 `register_admin_auth(config)` 返回 SQLAdmin 的 `AuthenticationBackend`。
- 生产环境下必须设置 `ADMIN_AUTH_SECRET_KEY`，不允许 `none` 模式。

访问
- 启动服务后访问：`http://127.0.0.1:8000/api/admin-console`（或你配置的 `ADMIN_PATH`）。

---

## 12. 异常处理

框架提供了统一的异常处理机制，所有异常都会被全局异常处理中间件捕获并转换为标准的 HTTP 响应。

### 12.1 异常处理流程

```
请求 → API 路由 → Service → Repository → 抛出异常
                                              ↓
                              全局异常处理中间件（Middleware）
                                              ↓
                                  转换为 ErrorResponse Schema
                                              ↓
                                       JSON 响应返回客户端
```

**流程说明**：
1. 业务代码抛出异常（如 `NotFoundError`）
2. 框架的全局异常处理中间件自动捕获
3. 根据异常类型转换为对应的 HTTP 状态码和错误响应
4. 返回统一格式的 JSON 错误响应

**响应格式**：
```json
{{
  "code": "NOT_FOUND",
  "message": "用户不存在",
  "data": null
}}
```

### 12.2 内置异常

```python
from aurimyth.foundation_kit.application.errors import (
    BaseError,
    NotFoundError,       # 404
    AlreadyExistsError,  # 409
    ValidationError,     # 422
    UnauthorizedError,   # 401
    ForbiddenError,      # 403
    BusinessError,       # 400
)

# 使用示例
raise NotFoundError("用户不存在", resource=user_id)
raise AlreadyExistsError(f"邮箱 {{email}} 已被注册")
raise UnauthorizedError("未登录或登录已过期")
```

### 12.3 自定义异常

**文件**: `app/exceptions/order.py`

```python
from fastapi import status
from aurimyth.foundation_kit.application.errors import BaseError


# 自定义异常（只需设置类属性）
class OrderError(BaseError):
    default_message = "订单错误"
    default_code = "ORDER_ERROR"
    default_status_code = status.HTTP_400_BAD_REQUEST


class OrderNotFoundError(OrderError):
    default_message = "订单不存在"
    default_code = "ORDER_NOT_FOUND"
    default_status_code = status.HTTP_404_NOT_FOUND


class InsufficientStockError(OrderError):
    default_message = "库存不足"
    default_code = "INSUFFICIENT_STOCK"
    default_status_code = status.HTTP_400_BAD_REQUEST


# 使用
raise OrderNotFoundError()  # 使用默认值
raise OrderError(message="订单ID无效")  # 自定义消息
raise InsufficientStockError(message=f"商品 {{product_id}} 库存不足")
```

### 12.4 异常与 Schema 的关系

异常处理中间件会自动将异常转换为 Schema 响应：

```python
# Service 层抛出异常
raise NotFoundError("用户不存在")

# 中间件捕获并转换为响应
# HTTP 状态码：404
# 响应体：
# {{
#   "code": "NOT_FOUND",
#   "message": "用户不存在",
#   "data": null
# }}
```

**最佳实践**：
- 在 Service 层抛出业务异常，不要在 API 层手动处理
- 使用框架内置异常或自定义异常，不要直接抛出 `Exception`
- 自定义异常继承 `BaseError`，框架会自动处理

---

## 最佳实践

1. **分层架构**：API → Service → Repository → Model
2. **事务管理**：在 Service 层使用 `@transactional`，只读操作可不加
3. **错误处理**：使用框架异常类，全局异常处理器统一处理
4. **配置管理**：使用 `.env` 文件，不提交到版本库
5. **日志记录**：使用框架 logger，支持结构化日志和链路追踪

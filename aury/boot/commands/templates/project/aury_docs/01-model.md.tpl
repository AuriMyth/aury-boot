# Model（数据模型）

## 1.1 模型基类选择

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

## 1.2 基类自动提供的字段

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

## 1.3 Model 编写示例

**文件**: `{package_name}/models/user.py`

```python
"""User 数据模型。"""

from sqlalchemy import String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aury.boot.domain.models import UUIDAuditableStateModel


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

## 1.4 字段类型映射

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

## 1.5 常用字段约束

```python
from sqlalchemy import String, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
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
    
    # 关联字段（不使用数据库外键，通过程序控制关系）
    category_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    
    # 复合索引和复合唯一约束：必须使用 __table_args__（SQLAlchemy 要求）
    # 软删除模型必须使用复合唯一约束（包含 deleted_at），避免删除后无法插入相同值
    __table_args__ = (
        Index("ix_examples_status_created", "status", "created_at"),
        UniqueConstraint("code", "deleted_at", name="uq_examples_code_deleted"),
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
       Index("ix_name", "col1", "col2"),
       UniqueConstraint("col1", "col2", name="uq_name"),
   )
   ```

4. **关联关系**：**不建议使用数据库外键**，通过程序控制关系
   - 便于分库分表、微服务拆分
   - 避免级联操作影响性能
   - 简化数据迁移
   ```python
   # 只存储关联 ID，不使用 ForeignKey
   category_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
   ```

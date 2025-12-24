# Repository（数据访问层）

## 2.1 Repository 编写示例

**文件**: `{package_name}/repositories/user_repository.py`

```python
"""User 数据访问层。"""

from aury.boot.domain.repository.impl import BaseRepository

from {package_name}.models.user import User


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

## 2.2 BaseRepository 方法详解

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
from aury.boot.domain.pagination import PaginationParams, SortParams

result = await repo.paginate(
    pagination_params=PaginationParams(page=1, page_size=20),
    sort_params=SortParams.from_string("-created_at"),
    is_active=True,
)

# PaginationResult 结构：
# - result.items: list[T]      # 数据列表
# - result.total: int          # 总记录数
# - result.page: int           # 当前页码
# - result.page_size: int      # 每页数量
# - result.total_pages: int    # 总页数
# - result.has_next: bool      # 是否有下一页
# - result.has_prev: bool      # 是否有上一页

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

### 2.2.1 Filters 语法（增强）

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

### 2.2.2 排序参数（SortParams）

`SortParams.from_string()` 支持两种语法：

```python
from aury.boot.domain.pagination import SortParams

# 简洁语法："-" 前缀表示降序
sort_params = SortParams.from_string("-created_at")
sort_params = SortParams.from_string("-created_at,priority")  # 多字段

# 完整语法：字段:方向
sort_params = SortParams.from_string("created_at:desc,priority:asc")

# 带字段白名单验证（防止 SQL 注入）
ALLOWED_FIELDS = {{"id", "created_at", "priority", "status"}}
sort_params = SortParams.from_string(
    "-created_at",
    allowed_fields=ALLOWED_FIELDS
)
# 传入非法字段会抛出 ValueError
```

### 2.2.3 查询全部（limit=None）

`list()` 支持 `limit=None` 返回全部记录（谨慎使用大表）：

```python
all_users = await repo.list(limit=None)                 # 全量
active_all = await repo.list(limit=None, is_active=True)
```

## 2.3 自动提交机制

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
- Aury Boot：默认自动提交，但**事务上下文自动接管**，更显式可控

## 2.4 复杂查询示例

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

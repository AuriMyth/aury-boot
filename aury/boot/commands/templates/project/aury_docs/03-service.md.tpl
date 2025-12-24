# Service（业务逻辑层）

## 3.1 Service 编写示例

**文件**: `{package_name}/services/user_service.py`

```python
"""User 业务逻辑层。"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.application.errors import AlreadyExistsError, NotFoundError
from aury.boot.domain.service.base import BaseService
from aury.boot.domain.transaction import transactional

from {package_name}.models.user import User
from {package_name}.repositories.user_repository import UserRepository
from {package_name}.schemas.user import UserCreate, UserUpdate


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

## 3.2 跨 Service 调用（事务共享）

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

## 数据库事务

### 3.3 事务装饰器（推荐）

```python
from aury.boot.domain.transaction import transactional
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

### 3.4 事务上下文管理器

```python
from aury.boot.domain.transaction import transactional_context
from aury.boot.infrastructure.database import DatabaseManager

db = DatabaseManager.get_instance()

async with db.session() as session:
    async with transactional_context(session):
        repo1 = UserRepository(session)
        repo2 = ProfileRepository(session)
        
        user = await repo1.create({{"name": "Alice"}})
        await repo2.create({{"user_id": user.id}})
        # 自动提交或回滚
```

### 3.5 事务传播（嵌套事务）

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

### 3.6 非事务的数据库使用

对于只读操作或不需要事务的场景，可以直接使用 session：

```python
from aury.boot.infrastructure.database import DatabaseManager

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

### 3.7 写入不使用事务装饰器

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
from aury.boot.domain.transaction import transactional_context

async def create_user_flow(session: AsyncSession, data: UserCreate) -> User:
    async with transactional_context(session):
        service = UserWriteService(session)
        return await service.create_no_tx(data)
```

适用场景：
- 一个用例调用多个 Service，统一提交
- 手动控制 commit 时机（分步 flush、条件提交）
- 上层已有事务边界（如作业层）

### 3.8 Savepoints（保存点）

保存点允许在事务中设置回滚点，实现部分回滚而不影响整个事务：

```python
from aury.boot.domain.transaction import TransactionManager

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

### 3.9 on_commit 回调

注册在事务成功提交后执行的回调函数，适合发送通知、触发后续任务等副作用操作：

```python
from aury.boot.domain.transaction import transactional, on_commit

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

### 3.10 SELECT FOR UPDATE（行级锁）

在并发场景下锁定查询的行，防止其他事务修改：

```python
from aury.boot.domain.repository.query_builder import QueryBuilder

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

### 3.11 事务隔离级别配置

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

# 补充：事务管理完全指南

Kit 在 `domain.transaction` 中提供了企业级的事务管理工具。

## Repository 自动提交机制

Foundation Kit 的 Repository 支持智能的自动提交机制，优于 Django 的设计。

### 自动提交行为

| 场景 | 行为 |
|------|------|
| 非事务中 + `auto_commit=True`（默认） | 写操作后自动 commit |
| 非事务中 + `auto_commit=False` | 只 flush，需手动管理或使用 `.with_commit()` |
| 在事务中（`@transactional` 等） | **永不自动提交**，由事务统一管理 |

### 基本用法

```python
from aury.boot.domain.repository.impl import BaseRepository

# 默认行为：非事务中自动提交
repo = UserRepository(session, User)  # auto_commit=True
await repo.create({"name": "test"})  # 自动 commit

# 禁用自动提交
repo = UserRepository(session, User, auto_commit=False)
await repo.create({"name": "test"})  # 只 flush，不 commit

# 单次强制提交（auto_commit=False 时）
await repo.with_commit().create({"name": "test2"})  # 强制 commit
```

### 与事务的配合

```python
from aury.boot.domain.transaction import transactional

# 在事务中：无论 auto_commit 是什么，都不会自动提交
@transactional
async def create_with_profile(session: AsyncSession):
    user_repo = UserRepository(session, User)  # auto_commit=True 但不生效
    profile_repo = ProfileRepository(session, Profile)
    
    user = await user_repo.create({"name": "alice"})  # 只 flush
    await profile_repo.create({"user_id": user.id})  # 只 flush
    # 事务结束时统一 commit
    return user
```

### 设计优势（对比 Django）

- **Django**：每个 `save()` 默认独立事务，容易无意识地失去原子性，需要显式 `atomic()` 包裹
- **Foundation Kit**：默认自动提交，但**事务上下文自动接管**，用户显式开事务 = 显式要原子性

## 事务管理工具

### 1. @transactional 装饰器（最常用）

自动处理事务开启、提交、回滚。

```python
from aury.boot.domain.transaction import transactional
from sqlalchemy.ext.asyncio import AsyncSession

@transactional
async def create_user_with_profile(session: AsyncSession, name: str, email: str):
    """创建用户及相关数据，全部在事务中"""
    user_repo = UserRepository(session)
    user = await user_repo.create({"name": name, "email": email})
    
    profile_repo = ProfileRepository(session)
    await profile_repo.create({"user_id": user.id})
    
    # 成功：自动 commit
    # 异常：自动 rollback
    return user
```

**自动参数识别**：
```python
# 支持多种参数形式
@transactional
async def method1(session: AsyncSession, data):
    """标准参数名"""
    pass

@transactional
async def method2(db: AsyncSession, data):
    """参数名为 db"""
    pass

@transactional
async def method3(self, data):
    """self.session 属性自动识别"""
    pass

# 在类中使用
class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @transactional
    async def create_with_audit(self, data):
        """自动使用 self.session"""
        user = await self.repo.create(data)
        await self.audit_repo.log(f"创建用户: {user.id}")
        return user
```

**自动嵌套处理**：
```python
@transactional
async def outer_operation(session: AsyncSession):
    await repo1.create({...})
    
    # 嵌套调用另一个 @transactional 函数
    result = await inner_operation(session)
    # 不会重复开启事务，复用外层事务
    
    return result

@transactional
async def inner_operation(session: AsyncSession):
    # 检测到已在事务中，直接执行
    return await repo2.create({...})
```

### 2. transactional_context 上下文管理器

更明确的事务边界。

```python
from aury.boot.domain.transaction import transactional_context
from aury.boot.infrastructure.database import DatabaseManager

db_manager = DatabaseManager.get_instance()

async def create_order_full(request: OrderRequest):
    """完整的订单创建过程"""
    async with db_manager.session() as session:
        async with transactional_context(session) as txn_session:
            # 在这个上下文中的所有操作都在事务中
            order_repo = OrderRepository(txn_session)
            order = await order_repo.create({
                "user_id": request.user_id,
                "total": request.total
            })
            
            # 创建订单项
            item_repo = OrderItemRepository(txn_session)
            for item in request.items:
                await item_repo.create({
                    "order_id": order.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity
                })
            
            # 更新库存
            inventory_repo = InventoryRepository(txn_session)
            for item in request.items:
                await inventory_repo.deduct(
                    item.product_id,
                    item.quantity
                )
            
            # 自动 commit，异常则 rollback
            return order
```

**手动控制提交**：
```python
async def operation_with_control(session: AsyncSession):
    async with transactional_context(session, auto_commit=False) as txn_session:
        repo = UserRepository(txn_session)
        user = await repo.create(...)
        
        # 如果需要，可以手动 flush 但不提交
        await txn_session.flush()
        
        # 做一些验证
        if not validate(user):
            # 异常会导致回滚
            raise ValueError("验证失败")
        
        # 最后必须手动提交
        await txn_session.commit()
        return user
```

### 3. TransactionManager 手动控制

更灵活但更冗长的方式。

```python
from aury.boot.domain.transaction import TransactionManager

async def manual_transaction_control(session: AsyncSession):
    """手动控制事务，适合复杂场景"""
    tm = TransactionManager(session)
    
    try:
        await tm.begin()
        
        # 执行操作
        repo = UserRepository(session)
        user = await repo.create({...})
        
        # 验证
        if not user.is_valid():
            raise ValueError("用户无效")
        
        await tm.commit()
        return user
    
    except Exception as e:
        await tm.rollback()
        logger.error(f"事务失败: {e}")
        raise
```

**使用上下文管理器形式**：
```python
async def transaction_context_form(session: AsyncSession):
    """TransactionManager 也支持上下文管理器"""
    tm = TransactionManager(session)
    
    async with tm:  # 自动 commit/rollback
        repo = UserRepository(session)
        user = await repo.create({...})
        return user
```

## 事务特性和用例

### 自动提交和回滚

```python
@transactional
async def create_user(session: AsyncSession, data: dict):
    repo = UserRepository(session)
    
    # 场景 1: 成功
    if len(data["username"]) < 3:
        return None
    
    user = await repo.create(data)
    # 函数返回：自动 commit
    return user

# 调用
try:
    result = await create_user(session, {"username": "john"})
    # result 已持久化到数据库
except Exception as e:
    # 异常时已自动 rollback，数据库中没有中间状态
    pass
```

### 多表操作的一致性

```python
@transactional
async def transfer_money(session: AsyncSession, from_user_id: str, to_user_id: str, amount: float):
    """转账操作：必须两个操作都成功，或都失败"""
    account_repo = AccountRepository(session)
    transaction_repo = TransactionRepository(session)
    
    # 1. 检查余额
    from_account = await account_repo.get(from_user_id)
    if from_account.balance < amount:
        raise InsufficientBalanceError()
    
    # 2. 扣款
    from_account.balance -= amount
    await account_repo.update(from_user_id, {"balance": from_account.balance})
    
    # 3. 加款
    to_account = await account_repo.get(to_user_id)
    to_account.balance += amount
    await account_repo.update(to_user_id, {"balance": to_account.balance})
    
    # 4. 记录交易
    await transaction_repo.create({
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "amount": amount
    })
    
    # 如果第 3、4 步任意一个失败，1、2 步都会回滚
    # 保证账户数据一致
```

### 嵌套事务

```python
@transactional
async def order_creation(session: AsyncSession, order_data):
    """外层事务"""
    order_repo = OrderRepository(session)
    order = await order_repo.create(order_data)
    
    # 调用另一个 @transactional 函数
    await update_inventory(session, order.items)
    # 嵌套函数不会开启新事务，复用外层事务
    
    return order

@transactional
async def update_inventory(session: AsyncSession, items):
    """内层事务（实际复用外层）"""
    inventory_repo = InventoryRepository(session)
    for item in items:
        await inventory_repo.deduct(item.product_id, item.quantity)
```

### Savepoints（保存点）

保存点允许在事务中设置回滚点，实现部分回滚而不影响整个事务。

```python
from aury.boot.domain.transaction import TransactionManager

async def complex_operation(session: AsyncSession):
    """使用保存点实现部分回滚"""
    tm = TransactionManager(session)
    
    await tm.begin()
    repo = UserRepository(session)
    
    try:
        # 第一步：创建主记录
        user = await repo.create({"name": "alice"})
        
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
        await repo.update(user.id, {"status": "active"})
        
        await tm.commit()
        return user
    except Exception as e:
        await tm.rollback()
        raise
```

**保存点 API**：

| 方法 | 描述 |
|------|------|
| `savepoint(name)` | 创建保存点，返回保存点 ID |
| `savepoint_commit(sp_id)` | 提交保存点（释放保存点，变更生效） |
| `savepoint_rollback(sp_id)` | 回滚到保存点（撤销保存点后的变更） |

**典型场景**：
- 批量导入时，某些记录失败不影响其他记录
- 可选的增强操作失败时降级处理
- 复杂业务流程中的检查点

### on_commit 回调

注册在事务成功提交后执行的回调函数，适合发送通知、触发后续任务等副作用操作。

```python
from aury.boot.domain.transaction import transactional, on_commit

@transactional
async def create_order(session: AsyncSession, order_data: dict):
    """创建订单并在提交后发送通知"""
    repo = OrderRepository(session)
    order = await repo.create(order_data)
    
    # 注册回调：事务成功后执行
    on_commit(lambda: send_order_notification(order.id))
    on_commit(lambda: update_inventory_cache(order.items))
    
    # 如果后续发生异常导致回滚，回调不会执行
    await validate_order(order)
    
    return order
    # 事务 commit 后，所有 on_commit 回调按注册顺序执行

def send_order_notification(order_id: str):
    """同步回调"""
    notification_service.send(f"订单 {order_id} 已创建")

async def update_inventory_cache(items: list):
    """异步回调也支持"""
    await cache.invalidate_inventory(items)
```

**在 TransactionManager 中使用**：

```python
from aury.boot.domain.transaction import TransactionManager

async def manual_with_callback(session: AsyncSession):
    tm = TransactionManager(session)
    
    await tm.begin()
    try:
        user = await create_user(session)
        
        # 注册到 TransactionManager
        tm.on_commit(lambda: print(f"用户 {user.id} 创建成功"))
        
        await tm.commit()  # 提交后执行回调
    except Exception:
        await tm.rollback()  # 回滚时回调被清除，不执行
        raise
```

**回调特性**：

| 特性 | 描述 |
|------|------|
| 执行时机 | 事务成功 `commit()` 后立即执行 |
| 回滚行为 | 事务回滚时，已注册的回调被清除，不执行 |
| 执行顺序 | 按注册顺序执行 |
| 支持类型 | 同步函数和异步函数都支持 |

**最佳实践**：
- 回调中不要执行关键业务逻辑（事务已提交，回调失败无法回滚）
- 适合：发送通知、更新缓存、触发异步任务、记录审计日志
- 回调中如有数据库操作，应开启新事务

### 异常处理中的事务

```python
@transactional
async def risky_operation(session: AsyncSession):
    repo = Repository(session)
    
    try:
        result1 = await repo.operation1()
        
        # 这个操作可能失败
        result2 = await risky_external_call()
        
        result3 = await repo.operation3()
        
        # 所有操作都成功：commit
        return result1, result2, result3
    
    except ExternalServiceError as e:
        # 异常时自动回滚
        # 即使 operation1 已经 flush，也会回滚
        logger.error(f"外部服务失败: {e}")
        raise
```

## 事务检查和约束

### 检查是否在事务中

```python
from aury.boot.domain.transaction import ensure_transaction

@router.post("/users")
async def create_user(request: UserCreateRequest, session=Depends(...)):
    # 检查是否在事务中
    if not ensure_transaction(session):
        logger.warning("操作未在事务中进行")
    
    repo = UserRepository(session)
    user = await repo.create(request.dict())
    return BaseResponse(code=200, message="成功", data=user)
```

### 强制要求事务

```python
from aury.boot.domain.transaction import requires_transaction

class UserRepository(BaseRepository[User]):
    """用户仓储"""
    
    @requires_transaction
    async def create_with_validation(self, data: dict):
        """此方法必须在事务中执行"""
        # 如果调用此方法时不在事务中，抛出 TransactionRequiredError
        user = User(**data)
        self.session.add(user)
        await self.session.flush()
        return user

# 使用
@transactional
async def service_method(session: AsyncSession):
    repo = UserRepository(session)
    # 安全：在事务中
    user = await repo.create_with_validation({...})
    return user

# 如果在事务外调用
async def unsafe_call(session: AsyncSession):
    repo = UserRepository(session)
    # ❌ 异常：TransactionRequiredError
    user = await repo.create_with_validation({...})
```

## 性能考虑

### 事务持续时间

```python
# ❌ 不好：事务时间太长
@transactional
async def slow_operation(session: AsyncSession):
    repo = Repository(session)
    await repo.create({...})
    
    # 长时间的外部 API 调用还在事务中
    result = await external_api.call()
    
    await repo.update({...})
    # 整个过程都锁定了数据库资源

# ✅ 好：事务只包含数据库操作
async def optimized_operation(session: AsyncSession):
    # 先做外部调用（不在事务中）
    result = await external_api.call()
    
    # 再在事务中进行数据库操作
    async with transactional_context(session):
        repo = Repository(session)
        await repo.create({...})
        await repo.update({...})
```

### 批量操作

```python
@transactional
async def bulk_create(session: AsyncSession, items: list):
    """创建大量数据"""
    repo = Repository(session)
    
    # 分批创建：降低单个事务的大小
    batch_size = 100
    created = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        for item in batch:
            created_item = await repo.create(item)
            created.append(created_item)
    
    return created
```

## 常见问题

### Q: @transactional 和 transactional_context 的区别？

A:
- `@transactional`：装饰器，自动检测参数，适合函数/方法
- `transactional_context`：上下文管理器，显式事务边界，适合复杂流程

选择建议：
- 简单函数 → 用 `@transactional`
- 复杂流程，多步骤 → 用 `transactional_context`
- 需要手动控制 → 用 `TransactionManager`

### Q: 如何处理嵌套事务中的异常？

A:
```python
@transactional
async def outer(session: AsyncSession):
    await operation1(session)
    
    try:
        await inner(session)
    except SpecificError:
        # 异常被捕获，外层事务继续
        logger.warning("内层操作失败，但继续处理")
    
    # 外层事务最后 commit
    return result

@transactional
async def inner(session: AsyncSession):
    # 如果抛异常，复用的外层事务会 rollback
    await operation2(session)
```

### Q: 如何在异步任务中使用事务？

A:
```python
from aury.boot.infrastructure.tasks.manager import TaskManager
from aury.boot.infrastructure.database import DatabaseManager

tm = TaskManager.get_instance()
db_manager = DatabaseManager.get_instance()

@tm.conditional_task(queue_name="default")
async def background_job(user_id: str):
    """后台任务中的事务"""
    async with db_manager.session() as session:
        async with transactional_context(session):
            # 在后台任务中安全地使用事务
            repo = UserRepository(session)
            user = await repo.get(user_id)
            await repo.update(user_id, {"processed": True})
```

## 下一步

- 查看 [09-database-complete.md](./09-database-complete.md) 了解数据库操作
- 查看 [08-error-handling-guide.md](./08-error-handling-guide.md) 了解异常处理
- 查看 [20-best-practices.md](./20-best-practices.md) 了解架构最佳实践


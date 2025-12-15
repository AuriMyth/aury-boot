# 5. 依赖注入容器 - 完全指南

## 核心概念

### 什么是依赖注入？

依赖注入（DI）是一种设计模式，用于解耦组件间的依赖关系。不是在类内部创建依赖，而是从外部"注入"它们。

### 为什么需要 DI？

```python
# ❌ 没有 DI：硬编码依赖，难以测试
class UserService:
    def __init__(self):
        self.db = Database()  # 硬编码，无法测试
        self.cache = Cache()
    
    async def get_user(self, user_id):
        return await self.db.get(user_id)

# 测试时无法使用 Mock 数据库

# ✅ 使用 DI：依赖从外部注入，易于测试
class UserService:
    def __init__(self, db: IUserRepository, cache: CacheManager):
        self.db = db
        self.cache = cache
    
    async def get_user(self, user_id):
        return await self.db.get(user_id)

# 测试时可以传入 Mock 对象
```

## Container 的生命周期

### SINGLETON（单例）

整个应用生命周期只创建一次。

**何时使用**：
- 数据库连接池（创建成本高，可复用）
- 缓存客户端（Redis、Memcached）
- 配置对象
- 日志管理器

**示例**：

```python
container = Container.get_instance()

# 注册单例
container.register_singleton(DatabaseManager)
container.register_singleton(CacheManager)

# 第一次解析时创建
db1 = container.resolve(DatabaseManager)
# 后续解析返回同一实例
db2 = container.resolve(DatabaseManager)
assert db1 is db2  # True
```

### SCOPED（作用域）

每个作用域内只创建一次，作用域外新建。

**何时使用**：
- 数据库会话（每个请求一个会话）
- 用户上下文（请求级别的用户信息）
- 事务管理器

**示例**：

```python
container.register_scoped(DatabaseSession)

# 作用域 1
with container.create_scope() as scope1:
    session1a = scope1.resolve(DatabaseSession)
    session1b = scope1.resolve(DatabaseSession)
    assert session1a is session1b  # 同一作用域，同一实例

# 作用域 2
with container.create_scope() as scope2:
    session2 = scope2.resolve(DatabaseSession)
    assert session2 is not session1a  # 不同作用域，不同实例
```

### TRANSIENT（瞬时）

每次都创建新实例。

**何时使用**：
- 业务逻辑服务（无状态的服务）
- 数据处理工具
- 临时对象

**示例**：

```python
container.register_transient(UserService)

service1 = container.resolve(UserService)
service2 = container.resolve(UserService)
assert service1 is not service2  # 不同实例
```

## 注册方式详解

### 1. 通过实现类注册

```python
# 最简单的方式
container.register_singleton(UserRepository)

# 等价于：通过类型注解自动解析，创建 UserRepository()
repo = container.resolve(UserRepository)
```

### 2. 通过接口注册（推荐）

实现多态和更好的测试能力。

```python
from abc import ABC, abstractmethod

class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str): ...

class UserRepository(IUserRepository):
    async def get_by_id(self, user_id: str):
        # 实现
        pass

# 注册时使用接口
container.register_singleton(IUserRepository, UserRepository)

# 依赖时使用接口
class UserService:
    def __init__(self, repo: IUserRepository):  # 依赖接口
        self.repo = repo

# 测试时可以注入 Mock 实现
class MockUserRepository(IUserRepository):
    async def get_by_id(self, user_id: str):
        return {"id": user_id, "name": "Mock"}
```

### 3. 通过工厂函数注册

对于需要复杂初始化逻辑的对象。

```python
def create_user_repository(container: Container) -> UserRepository:
    """工厂函数接收容器作为参数"""
    # 手动创建依赖
    session = container.resolve(DatabaseSession)
    config = container.resolve(BaseConfig)
    
    # 自定义初始化
    repo = UserRepository(session)
    repo.set_timeout(config.database.timeout)
    repo.set_pool_size(config.database.pool_size)
    
    return repo

# 注册
container.register(
    UserRepository,
    factory=create_user_repository,
    lifetime=Lifetime.SCOPED
)

# 解析时自动调用工厂函数
repo = container.resolve(UserRepository)
```

### 4. 注册实例

```python
# 直接注册已有的实例
config = BaseConfig()
container.register_instance(BaseConfig, config)

# 解析时返回该实例
same_config = container.resolve(BaseConfig)
assert same_config is config  # True
```

## 自动依赖解析

Kit 的 DI 容器可以**自动检测构造函数参数**并从容器中解析。

### 工作原理

```python
class UserService:
    def __init__(self, repo: UserRepository, cache: CacheManager):
        """
        通过类型注解，容器会自动：
        1. 检测参数 repo 需要 UserRepository
        2. 检测参数 cache 需要 CacheManager
        3. 从容器解析这两个依赖
        4. 创建 UserService 实例并注入
        """
        self.repo = repo
        self.cache = cache

# 注册
container.register_singleton(UserRepository)
container.register_singleton(CacheManager)
container.register_transient(UserService)

# 解析时自动注入所有依赖
service = container.resolve(UserService)
# 等价于：
# service = UserService(
#     repo=container.resolve(UserRepository),
#     cache=container.resolve(CacheManager)
# )
```

### 依赖链

容器自动处理依赖的依赖。

```python
class DatabaseSession:
    def __init__(self, config: BaseConfig):
        self.config = config

class UserRepository:
    def __init__(self, session: DatabaseSession):
        self.session = session

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

# 注册
container.register_instance(BaseConfig, config)
container.register_scoped(DatabaseSession)
container.register_scoped(UserRepository)
container.register_transient(UserService)

# 解析时自动链式依赖
service = container.resolve(UserService)
# 内部执行顺序：
# 1. 解析 UserService，需要 UserRepository
# 2. 解析 UserRepository，需要 DatabaseSession
# 3. 解析 DatabaseSession，需要 BaseConfig
# 4. 返回 BaseConfig 实例
# 5. 创建 DatabaseSession(config)
# 6. 创建 UserRepository(session)
# 7. 创建 UserService(repo)
```

## 作用域管理

### 请求级别的作用域

在 Web 请求中为每个请求创建独立作用域。

```python
from fastapi import APIRouter, Request

router = APIRouter()
container = Container.get_instance()

# 在应用启动时注册
container.register_singleton(UserService)
container.register_scoped(UserRepository)
container.register_scoped(DatabaseSession)

@router.get("/users/{user_id}")
async def get_user(user_id: str, request: Request):
    # 为每个请求创建独立作用域
    with container.create_scope() as scope:
        # 在这个作用域内，SCOPED 服务会被复用
        service = scope.resolve(UserService)
        user = await service.get_user(user_id)
        return user
    # 作用域退出时，所有 SCOPED 资源自动清理
```

### 自动清理

```python
class DatabaseSession:
    def __init__(self):
        self.connection = None
    
    async def connect(self):
        self.connection = await create_db_connection()
    
    async def disconnect(self):
        if self.connection:
            await self.connection.close()

# 在工厂函数中设置清理逻辑
async def create_session(container: Container):
    session = DatabaseSession()
    await session.connect()
    
    # 返回时设置清理回调
    # （实际实现需要在 Scope 中支持 on_exit 钩子）
    
    return session

with container.create_scope() as scope:
    session = scope.resolve(DatabaseSession)
    # 使用 session...
# 退出作用域时自动调用清理
```

## 与 FastAPI Depends 集成

Kit DI 与 FastAPI 的 `Depends()` 完美配合。

```python
from fastapi import APIRouter, Depends
from aury.boot.infrastructure.di import Container

router = APIRouter()
container = Container.get_instance()

# 在应用启动时注册
container.register_singleton(UserService)

# 创建 FastAPI 依赖函数
def get_user_service() -> UserService:
    return container.resolve(UserService)

# 在路由中使用
@router.get("/users")
async def list_users(service: UserService = Depends(get_user_service)):
    """
    FastAPI 流程：
    1. 检测到 Depends(get_user_service)
    2. 调用 get_user_service()
    3. 获得 UserService 实例
    4. 注入到 list_users()
    """
    return await service.list_all()
```

## 常见模式

### 1. 分层注册

```python
def setup_container(config: BaseConfig):
    container = Container.get_instance()
    
    # 配置层
    container.register_instance(BaseConfig, config)
    
    # 基础设施层
    container.register_singleton(DatabaseManager)
    container.register_singleton(CacheManager)
    
    # 数据访问层（SCOPED - 每个请求一个）
    container.register_scoped(UserRepository)
    container.register_scoped(OrderRepository)
    
    # 业务逻辑层（TRANSIENT - 每次创建新的）
    container.register_transient(UserService)
    container.register_transient(OrderService)
```

### 2. 工厂模式组合

```python
def create_user_service(container: Container) -> UserService:
    repo = container.resolve(UserRepository)
    cache = container.resolve(CacheManager)
    logger = container.resolve(Logger)
    return UserService(repo, cache, logger)

container.register(
    UserService,
    factory=create_user_service,
    lifetime=Lifetime.TRANSIENT
)
```

### 3. 测试中的依赖替换

```python
# 测试
def test_user_service():
    # 创建测试容器
    test_container = Container()
    
    # 注册 Mock 实现
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = {"id": "1", "name": "Test"}
    
    test_container.register_instance(UserRepository, mock_repo)
    test_container.register_transient(UserService)
    
    # 测试
    service = test_container.resolve(UserService)
    result = await service.get_user("1")
    
    assert result["name"] == "Test"
    mock_repo.get_by_id.assert_called_once_with("1")
```

## 最佳实践

### ✅ 推荐做法

1. **依赖接口，不依赖实现**
   ```python
   def __init__(self, repo: IUserRepository):  # ✅ 好
       self.repo = repo
   
   def __init__(self, repo: UserRepository):  # ❌ 耦合度高
       self.repo = repo
   ```

2. **在主文件中统一配置**
   ```python
   # main.py
   def setup_di(config: BaseConfig):
       container = Container.get_instance()
       # 所有注册在这里
   
   # 而不是分散在各个模块中
   ```

3. **使用工厂处理复杂初始化**
   ```python
   def create_repo(container: Container):
       # 复杂逻辑在这里
       return UserRepository(...)
   
   # 而不是在服务构造函数中
   ```

4. **为作用域服务提供工厂**
   ```python
   def create_session(db_manager: DatabaseManager):
       return db_manager.get_session()
   
   container.register(
       DatabaseSession,
       factory=create_session,
       lifetime=Lifetime.SCOPED
   )
   ```

### ❌ 避免的做法

1. **硬编码依赖**
   ```python
   class UserService:
       def __init__(self):
           self.repo = UserRepository()  # ❌ 无法测试
   ```

2. **在各处创建容器**
   ```python
   container1 = Container()  # ❌ 新实例
   container2 = Container()  # ❌ 不同实例
   
   container = Container.get_instance()  # ✅ 使用单例
   ```

3. **过度使用 TRANSIENT**
   ```python
   container.register_transient(DatabaseManager)  # ❌ 每次创建新连接
   container.register_singleton(DatabaseManager)  # ✅ 复用连接
   ```

## 与组件系统的集成

DI 容器和组件系统可以协作。

```python
from aury.boot.application.app.base import Component, FoundationApp

class DISetupComponent(Component):
    """在应用启动时初始化 DI 容器"""
    name = "di_setup"
    enabled = True
    depends_on = []
    
    async def setup(self, app: FoundationApp, config: BaseConfig):
        container = Container.get_instance()
        
        # 注册所有依赖
        container.register_instance(BaseConfig, config)
        container.register_singleton(DatabaseManager)
        container.register_scoped(UserRepository)
        container.register_transient(UserService)
        
        logger.info("DI 容器已初始化")
    
    async def teardown(self, app: FoundationApp):
        container = Container.get_instance()
        container.clear()

# 在应用中使用
app = FoundationApp(config=config)
app.add_component(DISetupComponent())
```

## 下一步

- 查看 [06-components-detailed.md](./06-components-detailed.md) 学习组件系统
- 查看 [09-database-complete.md](./09-database-complete.md) 学习数据库集成


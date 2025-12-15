# 8. 组件系统 - 完整指南

## 组件概述

组件（Component）是 Kit 中管理 **基础设施生命周期**的功能单元。与中间件（Middleware）不同，组件专注于数据库、缓存、任务队列等基础设施的初始化和清理。

### 为什么需要组件系统？

```python
# ❌ 传统做法：手动管理生命周期
@app.on_event("startup")
async def startup():
    global db, cache
    db = await init_db()
    cache = await init_cache()

@app.on_event("shutdown")
async def shutdown():
    await db.close()
    await cache.close()

# ✅ 使用组件系统：自动管理
class DatabaseComponent(Component):
    async def setup(self, app, config):
        app.state.db = await init_db()
    async def teardown(self, app):
        await app.state.db.close()

# 清晰、可复用、支持依赖管理
```

## 组件结构

### 基类定义

```python
from aury.boot.application.app.base import Component, FoundationApp
from aury.boot.application.config import BaseConfig
from typing import ClassVar

class Component(ABC):
    name: str                            # 组件唯一标识
    enabled: bool = True                 # 是否启用
    depends_on: ClassVar[list[str]] = [] # 依赖的组件
    
    def can_enable(self, config: BaseConfig) -> bool:
        """条件启用：返回 False 则跳过此组件"""
        return self.enabled
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """应用启动时调用（异步）"""
        pass
    
    async def teardown(self, app: FoundationApp) -> None:
        """应用关闭时调用（异步）"""
        pass
```

### 生命周期

```
应用构造 → 中间件注册 → lifespan 启动
                            ↓
                      组件拓扑排序
                            ↓
                      组件 setup()（按依赖顺序）
                            ↓
                      应用运行中...
                            ↓
                      组件 teardown()（按依赖逆序）
                            ↓
                      lifespan 关闭
```

## 内置组件

### 1. DatabaseComponent

管理数据库连接和连接池。

```python
from aury.boot.application.app.components import DatabaseComponent

class MyApp(FoundationApp):
    components = [
        DatabaseComponent,
    ]

# 自动初始化：
# - 创建异步引擎
# - 建立连接池
# - 创建会话工厂

# 在路由中使用
from aury.boot.infrastructure.database import DatabaseManager

db_manager = DatabaseManager.get_instance()

@app.get("/users")
async def list_users(session=Depends(db_manager.get_session)):
    repo = UserRepository(session)
    return await repo.list()
```

**配置**（.env）：
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
DATABASE_ECHO=false
```

### 2. CacheComponent

管理缓存系统（Redis 或内存）。

```python
from aury.boot.application.app.components import CacheComponent

class MyApp(FoundationApp):
    components = [
        CacheComponent,
    ]

# 根据配置自动选择后端：
# CACHE_TYPE=memory    → 内存缓存（开发）
# CACHE_TYPE=redis     → Redis 缓存（生产）

from aury.boot.infrastructure.cache import CacheManager

cache = CacheManager.get_instance()
await cache.set("key", "value", expire=300)
value = await cache.get("key")
```

**配置**（.env）：
```bash
CACHE_TYPE=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_MAX_SIZE=1000
```

### 3. TaskComponent

管理异步任务队列。

```python
from aury.boot.application.app.components import TaskComponent

class MyApp(FoundationApp):
    components = [
        TaskComponent,
    ]

# 在 API 模式下：作为生产者，提交任务到队列
# 在 Worker 模式下：消费队列中的任务

from aury.boot.infrastructure.tasks import TaskManager

tm = TaskManager.get_instance()

@tm.conditional_task(queue_name="default", max_retries=3)
async def send_email(email: str):
    pass

# 提交任务
send_email.send("user@example.com")
```

**配置**（.env）：
```bash
SERVICE_TYPE=api  # 或 worker
TASK_BROKER_URL=redis://localhost:6379/0
```

### 4. SchedulerComponent

管理定时任务调度。

```python
from aury.boot.application.app.components import SchedulerComponent

class MyApp(FoundationApp):
    components = [
        SchedulerComponent,
    ]

from aury.boot.infrastructure.scheduler import SchedulerManager

scheduler = SchedulerManager.get_instance()

scheduler.add_job(
    func=daily_cleanup,
    trigger="cron",
    hour=2, minute=0
)
```

**配置**（.env）：
```bash
SCHEDULER_MODE=embedded  # 或 standalone
```

### 5. MigrationComponent

自动执行数据库迁移。

```python
from aury.boot.application.app.components import (
    DatabaseComponent,
    MigrationComponent,
)

class MyApp(FoundationApp):
    components = [
        DatabaseComponent,
        MigrationComponent,  # 依赖 DatabaseComponent
    ]

# 应用启动时自动执行迁移到最新版本
# 🔄 检查数据库迁移...
# ✅ 数据库已是最新版本，无需迁移
```

### 6. AdminConsoleComponent（可选）

提供基于 **SQLAdmin** 的管理后台（默认路径：`/api/admin-console`），用于快速搭建生产可用的后台管理能力。

> 依赖：`uv add "aury-boot[admin]"`（需同步数据库驱动）

```python
from aury.boot.application.app.components import AdminConsoleComponent

class MyApp(FoundationApp):
    components = [
        AdminConsoleComponent,
    ]
```

**配置**（.env）：

```bash
ADMIN_ENABLED=true
ADMIN_PATH=/api/admin-console

# SQLAdmin 通常要求同步 Engine；若 DATABASE_URL 是异步驱动，建议显式提供同步 URL
# ADMIN_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/mydb

# 认证（默认推荐 basic 或 bearer）
ADMIN_AUTH_MODE=basic
ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
ADMIN_AUTH_BASIC_USERNAME=admin
ADMIN_AUTH_BASIC_PASSWORD=change_me
```

## 自定义组件

### 基本结构

```python
from aury.boot.application.app.base import Component, FoundationApp
from aury.boot.application.config import BaseConfig
from typing import ClassVar

class MyCustomComponent(Component):
    name = "my_custom"           # 唯一标识
    enabled = True               # 是否启用
    depends_on: ClassVar[list[str]] = ["database"]  # 依赖关系
    
    def can_enable(self, config: BaseConfig) -> bool:
        """条件启用：检查配置决定是否启用"""
        return hasattr(config, 'my_feature_enabled') and config.my_feature_enabled
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """应用启动时调用"""
        print("🚀 初始化...")
        app.state.my_resource = SomeResource()
    
    async def teardown(self, app: FoundationApp) -> None:
        """应用关闭时调用"""
        print("🛑 清理...")
        if hasattr(app.state, 'my_resource'):
            await app.state.my_resource.close()
```

### 实际示例：Redis 连接池

```python
class RedisConnectionComponent(Component):
    name = "redis"
    enabled = True
    depends_on: ClassVar[list[str]] = []
    
    def can_enable(self, config: BaseConfig) -> bool:
        """仅当配置了 Redis 时启用"""
        return bool(getattr(config.cache, 'redis_url', None))
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化 Redis 连接"""
        import redis.asyncio as redis
        
        pool = redis.ConnectionPool.from_url(
            config.cache.redis_url,
            max_connections=50
        )
        app.state.redis_pool = pool
        logger.info(f"✅ Redis 已连接: {config.cache.redis_url}")
    
    async def teardown(self, app: FoundationApp) -> None:
        """关闭 Redis 连接"""
        if hasattr(app.state, 'redis_pool'):
            await app.state.redis_pool.disconnect()
            logger.info("✅ Redis 已断开连接")
```

### 实际示例：外部 API 客户端

```python
import httpx

class ExternalAPIComponent(Component):
    name = "external_api"
    enabled = True
    depends_on: ClassVar[list[str]] = []
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化 HTTP 客户端"""
        app.state.http_client = httpx.AsyncClient(
            base_url=config.external_api_url,
            timeout=30.0,
        )
        logger.info("✅ HTTP 客户端已初始化")
    
    async def teardown(self, app: FoundationApp) -> None:
        """关闭 HTTP 客户端"""
        if hasattr(app.state, 'http_client'):
            await app.state.http_client.aclose()
            logger.info("✅ HTTP 客户端已关闭")
```

## 组件注册

### 方式 1：类属性（推荐）

```python
from aury.boot.application.app.base import FoundationApp
from aury.boot.application.app.components import (
    DatabaseComponent,
    CacheComponent,
)

class MyApp(FoundationApp):
    components = [
        DatabaseComponent,
        CacheComponent,
        MyCustomComponent,  # 自定义组件
    ]

app = MyApp(config=config)
```

### 方式 2：条件注册

```python
class MyApp(FoundationApp):
    components = [
        DatabaseComponent,
    ]
    
    def __init__(self, *args, **kwargs):
        # 根据条件动态添加组件
        if self._config.enable_cache:
            self.components = [
                DatabaseComponent,
                CacheComponent,
            ]
        super().__init__(*args, **kwargs)
```

## 组件依赖管理

### 依赖关系声明

```python
class ComponentA(Component):
    name = "a"
    depends_on: ClassVar[list[str]] = []

class ComponentB(Component):
    name = "b"
    depends_on: ClassVar[list[str]] = ["a"]  # 依赖 A

class ComponentC(Component):
    name = "c"
    depends_on: ClassVar[list[str]] = ["a", "b"]  # 依赖 A 和 B

# 启动顺序：A → B → C
# 关闭顺序：C → B → A（反向）
```

### 循环依赖检测

```python
class ComponentX(Component):
    name = "x"
    depends_on: ClassVar[list[str]] = ["y"]

class ComponentY(Component):
    name = "y"
    depends_on: ClassVar[list[str]] = ["x"]  # 循环依赖！

# 框架会记录警告：
# "检测到循环依赖: x"
```

## 访问其他组件的资源

```python
class DependentComponent(Component):
    name = "dependent"
    depends_on: ClassVar[list[str]] = ["database", "cache"]
    
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        # 通过单例管理器访问资源
        from aury.boot.infrastructure.database import DatabaseManager
        from aury.boot.infrastructure.cache import CacheManager
        
        db_manager = DatabaseManager.get_instance()
        cache_manager = CacheManager.get_instance()
        
        # 使用它们
        app.state.my_service = MyService(db_manager, cache_manager)
```

## 最佳实践

### ✅ 推荐做法

1. **单一职责**
   ```python
   # ✅ 好：每个组件只管理一个资源
   class DatabaseComponent(Component): ...
   class CacheComponent(Component): ...
   
   # ❌ 不好：一个组件管理多个资源
   class InfrastructureComponent(Component):
       async def setup(self, ...):
           app.state.db = ...
           app.state.cache = ...
   ```

2. **明确声明依赖**
   ```python
   # ✅ 好
   depends_on: ClassVar[list[str]] = ["database", "cache"]
   
   # ❌ 不好：实际依赖但未声明
   depends_on: ClassVar[list[str]] = []  # 但 setup 中使用了 database
   ```

3. **条件启用**
   ```python
   # ✅ 好
   def can_enable(self, config):
       return bool(config.database.url)
   
   # ❌ 不好
   def can_enable(self, config):
       return True  # 即使配置不完整也启用
   ```

4. **异常处理**
   ```python
   # ✅ 好
   async def setup(self, app, config):
       try:
           app.state.resource = await init_resource()
           logger.info("Resource initialized")
       except Exception as e:
           logger.error(f"Failed to initialize: {e}")
           raise
   ```

### ❌ 避免的做法

1. **在 setup() 中执行长时间操作**
   - 会导致应用启动缓慢
   - 使用后台任务代替

2. **在 teardown() 中忽略异常**
   - 可能导致资源泄漏
   - 总是捕获并记录异常

3. **组件间直接通信**
   - 应该通过单例管理器或应用状态通信
   - 不要直接依赖其他组件实例

## 下一步

- 查看 [12-database-complete.md](./12-database-complete.md) 了解 DatabaseComponent 详细用法
- 查看 [13-caching-advanced.md](./13-caching-advanced.md) 了解 CacheComponent 详细用法
- 查看 [06-di-container-complete.md](./06-di-container-complete.md) 了解如何与 DI 容器配合

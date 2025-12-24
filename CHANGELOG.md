# Changelog

本文件记录 Aury Boot 的重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)，版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [0.3.1] - 2024-12-25

### Changed
- **Manager API 统一**：所有基础设施 Manager 统一使用 `initialize()` 方法
  - 删除 `DatabaseManager.configure()`，配置参数直接传入 `initialize()`
  - 删除 `CacheManager.init_app()`，统一使用 `initialize()`
  - 重命名 `StorageManager.init()` → `initialize()`
  ```python
  # 统一的初始化方式
  await cache.initialize(backend="redis", url="redis://localhost:6379")
  await storage.initialize(StorageConfig(...))
  await events.initialize(backend="memory")
  ```
- 所有 Manager 新增 `is_initialized` 属性

### Added
- **CacheManager**：新增 `delete_pattern(pattern)` 方法，支持通配符批量删除缓存
- **CacheManager**：新增 `@cache.cache_response()` 装饰器，用于 API 响应缓存
- **SortParams**：新增 `from_string()` 方法，支持 `-field` 和 `field:desc` 语法
- **日志中间件文档**：`RequestLoggingMiddleware` 和 `WebSocketLoggingMiddleware` 添加到 aury_docs
- **AGENTS.md**：新增 Manager API 规范说明

### Fixed
- 修复 `EventBusManager` 文档中错误的 `configure()` API 调用
- 修复 `ChannelManager`、`MQManager` 文档中错误的 `configure()` API 调用
- 修复 `07-cache.md.tpl` 模板变量转义问题 (`{layer}` → `{{layer}}`)
- 修复 `WebSocketLoggingMiddleware` 重复定义问题 (F811)
- 修复 `ContextVar` 使用可变默认值问题 (B039)
- 修复 `startup.py` 中对已删除的 `DatabaseManager._config` 的访问
- 修复类型比较使用 `==` 而非 `is` 的问题 (E721)

### Ruff 配置优化
- 新增 `N806` 到 ignore 列表（函数内类引用变量大写）
- 新增 `_version.py` 到 per-file-ignores（自动生成的版本文件）

---

## [0.3.0] - 2024-12-24

### Added
- **Redis 客户端** (`infrastructure/clients/redis/`)
  - `RedisClient` 多实例管理器
  - 支持连接池、健康检查、URL 脱敏
  ```python
  client = RedisClient.get_instance("cache")
  await client.configure(url="redis://localhost:6379/0").initialize()
  ```

- **RabbitMQ 客户端** (`infrastructure/clients/rabbitmq/`)
  - `RabbitMQClient` 多实例管理器
  - 支持连接、通道、健康检查
  ```python
  mq = RabbitMQClient.get_instance("events")
  await mq.configure(url="amqp://guest:guest@localhost:5672/").initialize()
  ```

- **流式通道** (`infrastructure/channel/`)
  - `ChannelManager` 用于 SSE/实时通信
  - 后端：`memory`（单进程）、`redis`（多进程/分布式）
  ```python
  channel = ChannelManager.get_instance()
  await channel.publish("user:123", {"event": "notification"})
  async for msg in channel.subscribe("user:123"): ...
  ```

- **消息队列** (`infrastructure/mq/`)
  - `MQManager` 多实例消息队列
  - 后端：`redis`、`rabbitmq`
  ```python
  mq = MQManager.get_instance()
  await mq.publish("orders", {"order_id": "123"})
  await mq.consume("orders", handler)
  ```

- **事件总线重构** (`infrastructure/events/`)
  - 新增 `EventBusManager` 多实例支持
  - 新后端：`memory`、`redis`、`rabbitmq`
  - 保留旧 `EventBus` API 兼容

- **多实例配置** (`application/config/multi_instance.py`)
  - 环境变量格式：`{PREFIX}_{INSTANCE}_{FIELD}`
  - 支持 Database、Redis、Cache、Storage、Channel、MQ、Event
  ```bash
  DATABASE_DEFAULT_URL=postgresql+asyncpg://...
  DATABASE_READONLY_URL=postgresql+asyncpg://...
  REDIS_CACHE_URL=redis://localhost:6379/1
  ```

- **启动日志优化** (`application/app/startup.py`)
  - 组件状态打印
  - URL 脱敏（隐藏密码）

- **Manager 链式调用**
  - 所有 Manager 的 `configure()`、`initialize()` 返回 `self`
  ```python
  await DatabaseManager.get_instance().configure(url=...).initialize()
  ```

- 所有 Manager 新增 `reset_instance(name: str | None = None)` 方法

### Changed
- **Storage 模块重构**：移除内置存储实现，改为依赖 `aury-sdk-storage`
  - 安装方式：`pip install "aury-sdk-storage[aws]"` 或 `uv add "aury-sdk-storage[aws]"`
  - `StorageManager` 现在委托给 SDK 的 `IStorage` 实现
  - 移除了 `s3.py`、`sts.py`、`sts_providers/` 等文件
- Manager 单例模式从类变量 `_instance` 改为 `_instances: dict[str, Manager]`
- `DatabaseManager.configure()` 从类方法改为实例方法
- `CacheManager` 的 Redis 后端支持复用 `RedisClient`

### Removed
- 移除内置的 S3/COS/OSS 存储实现（由 `aury-sdk-storage` 替代）
- 移除内置的 STS 临时凭证提供者（由 `aury-sdk-storage` 替代）
- 移除 Events 模块的 Kombu 依赖（新后端不依赖 Kombu）

### Fixed
- 修复项目模板中的 f-string 和 JSON 字典转义问题

---

## [0.0.1] - 2024-12-xx

### Added
- 初始版本发布
- **核心框架**
  - `FoundationApp`：基于 FastAPI 的应用框架
  - `Component` 系统：组件生命周期管理
  - `BaseConfig`：Pydantic 配置管理
- **Domain 层**
  - `BaseRepository`：通用仓储模式实现
  - 预定义模型基类：`Model`、`UUIDModel`、`UUIDAuditableStateModel` 等
  - `@transactional` 装饰器：声明式事务管理
  - `QueryBuilder`：链式查询构建器
- **Infrastructure 层**
  - `DatabaseManager`：异步数据库连接管理
  - `CacheManager`：缓存管理（支持 Redis/Memory）
  - `TaskManager`：异步任务队列（Dramatiq）
  - `SchedulerManager`：定时任务调度（APScheduler）
  - `EventBus`：事件总线
- **Application 层**
  - 内置组件：Database、Cache、Storage、Task、Scheduler、Migration、AdminConsole
  - 标准响应模型：`BaseResponse`、`PaginationResponse`
  - 统一异常处理
- **CLI 工具**
  - `aury init`：项目脚手架
  - `aury generate crud`：CRUD 代码生成
  - `aury server dev/prod`：服务器管理
  - `aury migrate`：数据库迁移
- **文档**
  - 完整的用户手册
  - 项目模板（DEVELOPMENT.md、CLI.md）

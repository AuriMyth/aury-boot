# AuriMyth Foundation Kit 架构设计

## 核心设计哲学

AuriMyth Foundation Kit 采用**组件化 + 依赖声明**的架构，提供优雅、抽象、可扩展、不受限的应用框架。

### 设计原则

1. **抽象**：所有功能单元统一为 Component 接口，无特殊处理
2. **可扩展**：只需改类属性，即可添加/移除/替换功能
3. **不受限**：无固定的初始化步骤，按依赖关系动态排序
4. **约定优于配置**：有配置就启用，没有就不启用
5. **常量分散**：跨模块共享的常量放顶级，模块内常量放模块内

## 整体架构

### 模块分层

```
aurimyth/foundation_kit/
├── constants/              # 框架级常量（仅跨模块共享）
│   ├── service.py         # ServiceType
│   └── scheduler.py       # SchedulerMode
│
├── core/                   # 核心层（业务逻辑基类）
│   ├── models.py          # ORM 模型基类
│   ├── repository.py     # Repository 模式
│   └── service.py         # Service 模式
│
├── infrastructure/         # 基础设施层（技术实现）
│   ├── database/          # 数据库管理
│   ├── cache/             # 缓存管理
│   ├── tasks/             # 任务队列（含 constants.py）
│   ├── scheduler/         # 调度器管理
│   ├── storage/           # 对象存储
│   └── logging.py         # 日志系统
│
├── application/            # 应用层（业务编排）
│   ├── app.py             # FoundationApp（核心）
│   ├── config/            # 配置管理
│   ├── constants.py       # 应用层常量（ComponentName）
│   ├── container.py       # 依赖注入
│   ├── transaction.py     # 事务管理
│   ├── events.py          # 事件系统
│   ├── migrations.py      # 数据库迁移
│   ├── scheduler.py       # 调度器启动器
│   └── interfaces/        # API 接口层
│       ├── errors.py      # 错误处理
│       ├── ingress.py     # 请求模型
│       └── egress.py      # 响应模型
│
├── testing/               # 测试框架
├── i18n/                  # 国际化
└── toolkit/               # 工具包
```

### 常量组织原则

- **顶级 constants/**：仅跨模块共享的常量（ServiceType, SchedulerMode）
- **模块内 constants.py**：模块内使用的常量（ComponentName, TaskQueueName）

## FoundationApp 架构

### 类层次结构

```
FastAPI
  ↓
FoundationApp
  ├─ Component 系统
  │  ├─ 统一接口（Component）
  │  ├─ 依赖声明（depends_on）
  │  ├─ 拓扑排序（自动）
  │  └─ 生命周期管理（setup/teardown）
  │
  ├─ 默认组件（items 类属性）
  │  ├─ RequestLoggingComponent
  │  ├─ CORSComponent
  │  ├─ DatabaseComponent
  │  ├─ CacheComponent
  │  ├─ TaskComponent
  │  └─ SchedulerComponent
  │
  └─ 生命周期管理
     ├─ _on_startup（启动所有组件）
     └─ _on_shutdown（关闭所有组件）
```

### 生命周期流程

#### 应用启动流程

```
1. _register_components() - 注册所有组件
   ↓
2. _topological_sort() - 拓扑排序（按 depends_on）
   ↓
3. 逐个执行 component.setup()
   ↓
4. 应用准备好处理请求
```

#### 应用关闭流程

```
1. _topological_sort(reverse=True) - 逆序排序
   ↓
2. 逐个执行 component.teardown()
   ↓
3. 应用完全关闭
```

## Component 组件系统

### 基础组件类

```python
class Component(ABC):
    """应用组件基类"""
    
    name: str                      # 组件唯一标识（使用 ComponentName 常量）
    enabled: bool = True           # 是否默认启用
    depends_on: list[str] = []    # 依赖的其他组件（使用 ComponentName 常量）
    
    def can_enable(self, config: BaseConfig) -> bool:
        """是否可以启用此组件（可被覆盖）"""
        return self.enabled
    
    @abstractmethod
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """组件启动时调用"""
        pass
    
    @abstractmethod
    async def teardown(self, app: FoundationApp) -> None:
        """组件关闭时调用"""
        pass
```

### 依赖关系管理

- **声明式依赖**：通过 `depends_on` 列表声明依赖关系
- **自动排序**：使用拓扑排序算法自动确定启动顺序
- **循环检测**：自动检测并警告循环依赖

### 默认组件

#### 1. RequestLoggingComponent
- **名称**：`ComponentName.REQUEST_LOGGING`
- **依赖**：无
- **启用条件**：`enabled = True`（总是启用）
- **职责**：添加请求日志中间件

#### 2. CORSComponent
- **名称**：`ComponentName.CORS`
- **依赖**：无
- **启用条件**：`config.cors.allow_origins` 不为空
- **职责**：添加 CORS 中间件

#### 3. DatabaseComponent
- **名称**：`ComponentName.DATABASE`
- **依赖**：无
- **启用条件**：`config.database.url` 不为空
- **职责**：初始化数据库连接池

#### 4. CacheComponent
- **名称**：`ComponentName.CACHE`
- **依赖**：无
- **启用条件**：`config.cache.cache_type` 不为空
- **职责**：初始化缓存后端

#### 5. TaskComponent
- **名称**：`ComponentName.TASK_QUEUE`
- **依赖**：无
- **启用条件**：`service.service_type == WORKER` 且 `task.broker_url` 不为空
- **职责**：初始化任务队列（Worker 模式）

#### 6. SchedulerComponent
- **名称**：`ComponentName.SCHEDULER`
- **依赖**：无
- **启用条件**：`scheduler.mode == EMBEDDED`
- **职责**：初始化调度器（嵌入式模式）

## 核心层（Core）

### 模型基类

- `BaseModel` - 基础模型（无字段）
- `TimestampedModel` - 带时间戳的模型（id, created_at, updated_at, yn）

### Repository 模式

- `IRepository[ModelType]` - 仓储接口
- `BaseRepository[ModelType]` - 仓储基类
- 设计原则：Repository 不执行 commit，只执行 flush；事务由 Service 层管理

### Service 模式

- `BaseService` - 领域服务基类
- 职责：管理数据库会话、协调多个Repository、实现业务逻辑、事务管理

## 基础设施层（Infrastructure）

### 单例模式

所有基础设施管理器都采用单例模式：
- `DatabaseManager.get_instance()`
- `CacheManager.get_instance()`
- `TaskManager.get_instance()`
- `SchedulerManager.get_instance()`

### 数据库管理

- 连接池管理、会话工厂、健康检查

### 缓存管理

- 多后端支持（Redis、Memory、Memcached）、工厂模式、装饰器支持

### 任务队列

- 条件注册（`conditional_actor`）、队列管理、错误处理

### 调度器

- 三种模式：`EMBEDDED`、`STANDALONE`、`DISABLED`
- 独立启动器：`run_scheduler()`

## 应用层（Application）

### 配置管理

使用 `pydantic-settings` 进行分层配置，环境变量前缀：
- `DATABASE_*` - 数据库配置
- `CACHE_*` - 缓存配置
- `SERVICE_*` - 服务配置
- `SCHEDULER_*` - 调度器配置
- `TASK_*` - 任务配置

### 依赖注入

- `Container` - 依赖注入容器（单例模式）
- 支持三种生命周期：`SINGLETON`、`SCOPED`、`TRANSIENT`

### 事务管理

- `@transactional` - 装饰器模式
- `transactional_context` - 上下文管理器模式

### 事件系统

- `EventBus` - 事件总线（单例模式）
- 支持发布/订阅模式，所有事件基于 Pydantic

### 错误处理

责任链模式：
- `BaseErrorHandler` - 自定义异常
- `HTTPExceptionHandler` - FastAPI HTTP 异常
- `ValidationErrorHandler` - Pydantic 验证异常
- `DatabaseErrorHandler` - 数据库异常

## 接口层（Interfaces）

### 请求模型（Ingress）

- `BaseRequest` - 基础请求
- `PaginationRequest` - 分页请求
- `ListRequest` - 列表请求
- `FilterRequest` - 过滤请求

### 响应模型（Egress）

- `BaseResponse[T]` - 基础响应（泛型）
- `SuccessResponse` - 成功响应
- `ErrorResponse` - 错误响应
- `PaginationResponse[T]` - 分页响应

### 错误处理

- `ErrorCode` - 错误代码枚举
- `ErrorDetail` - 错误详情（Pydantic）
- `BaseError` - 基础异常类

## 与 Django/Spring Boot 的对比

| 特性 | Django | Spring Boot | Foundation Kit |
|------|--------|------------|---------------|
| 组件系统 | Apps | Beans | Components |
| 依赖管理 | 手动 | @DependsOn | depends_on（自动排序）|
| 配置驱动 | settings.py | application.properties | BaseConfig |
| 条件启用 | if settings.X | @ConditionalOn* | can_enable() |
| 中间件 | MIDDLEWARE | FilterChain | Component（统一）|
| 生命周期 | AppConfig.ready() | @PostConstruct | setup()/teardown() |

## 总结

AuriMyth Foundation Kit 通过组件化架构和依赖声明机制，提供了一个高度灵活且易于扩展的 FastAPI 应用框架。所有功能单元统一为 Component 接口，通过 `depends_on` 声明依赖关系，框架自动拓扑排序并管理生命周期。

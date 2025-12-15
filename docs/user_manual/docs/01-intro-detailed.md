# 1. 简介 - 深入理解 Aury Boot

## 什么是 Aury Boot？

Aury Boot 是一个**微服务开发框架**，基于 FastAPI，但提供了企业级的基础设施支持。它不是替代 FastAPI，而是在其基础上增加了生产环境必需的功能。

### 框架的核心理念

1. **开箱即用**：提供开发微服务所需的所有"电池"（DI、日志、缓存、任务队列等）
2. **标准化架构**：通过内置的组件系统、仓储模式等，规范代码结构
3. **生产就绪**：分布式追踪、企业级日志、错误处理等功能内置
4. **灵活可扩展**：组件系统允许自定义扩展，DI 容器支持多种生命周期

## 架构层次

```
FastAPI (HTTP 框架)
    ↓
FoundationApp (应用基类)
    ↓
Component System (组件管理)
    ↓
Infrastructure Layer (基础设施层)
├── Database (数据库)
├── Cache (缓存)
├── Task Queue (任务队列)
├── Event Bus (事件总线)
├── Scheduler (定时器)
├── RPC (远程调用)
├── Logging (日志)
└── DI Container (依赖注入)
```

## 为什么需要它？

### 传统 FastAPI 应用的问题

```python
# ❌ 传统做法：手动管理一切
app = FastAPI()

# 需要手动创建和管理
db = None
cache = None
logger = None

@app.on_event("startup")
async def startup():
    global db, cache, logger
    # 手动初始化数据库、缓存、日志...
    # 代码冗长，容易出错

@app.on_event("shutdown")
async def shutdown():
    # 手动清理资源...
    pass

@app.get("/users")
async def list_users():
    # 每个路由中手动注入依赖
    session = db.session()
    # ...
```

### 使用 Foundation Kit 的优势

```python
# ✅ 使用 Kit：统一管理
class AppConfig(BaseConfig):
    pass

app = FoundationApp(config=AppConfig())
# 所有基础设施自动初始化和管理

container = Container.get_instance()
# 统一的 DI 容器

@app.get("/users")
async def list_users(repo: UserRepository = Depends(get_user_repo)):
    # 依赖自动注入，代码清晰
    pass
```

## 核心概念

### 1. 中间件和组件系统

Kit 将功能单元分为两类：

**中间件（Middleware）** - 处理 HTTP 请求拦截：
- `register()` 同步注册
- 按 `order` 排序执行
- 内置：`RequestLoggingMiddleware`、`CORSMiddleware`

**组件（Component）** - 管理基础设施生命周期：
- `setup()` / `teardown()` 异步接口
- 自动依赖管理（`depends_on`）
- 条件启用（`can_enable()`）
- 内置：`DatabaseComponent`、`CacheComponent`、`TaskComponent`、`SchedulerComponent`

### 2. 依赖注入容器（DI Container）

**生命周期管理**：

- **SINGLETON**：整个应用生命周期唯一（如：数据库连接池、缓存客户端）
- **SCOPED**：请求范围内唯一（如：数据库会话、用户上下文）
- **TRANSIENT**：每次都创建新实例（如：业务逻辑服务）

**自动依赖解析**：通过类型注解自动解析依赖关系

### 3. 分层架构

```
API 层 (api/)
  ↓ 依赖
业务逻辑层 (services/)
  ↓ 依赖
数据访问层 (repositories/)
  ↓ 使用
数据模型层 (models/)
```

每一层职责清晰，易于测试和维护。

### 4. 微服务能力

- **RPC 客户端**：跨服务通信
- **服务发现**：DNS 自动解析或显式映射
- **分布式追踪**：Trace ID 自动传递
- **事件总线**：跨服务事件通信

## 与其他框架的对比

| 特性 | FastAPI | Kit | Spring Boot |
|------|---------|-----|------------|
| HTTP 框架 | ✅ | ✅ | ✅ |
| DI 容器 | ❌ | ✅ | ✅ |
| 组件系统 | ❌ | ✅ | ✅ |
| 数据库 ORM | ❌ | ✅ | ✅ |
| 日志系统 | ❌ | ✅ | ✅ |
| 缓存管理 | ❌ | ✅ | ✅ |
| 任务队列 | ❌ | ✅ | ✅ |
| 微服务支持 | ❌ | ✅ | ✅ |
| 学习曲线 | 平缓 | 中等 | 陡峭 |

## 何时使用 Kit？

### ✅ 适合使用

- 构建微服务架构
- 需要分布式追踪和日志
- 项目中有多个独立服务需要通信
- 需要异步任务和定时任务
- 需要标准化的项目结构和代码规范

### ❌ 不适合使用

- 简单的单体应用（比如小工具脚本）
- 不需要任何基础设施支持的 API
- 学习 Python Web 开发的初期阶段

## 性能特性

### 优化点

1. **异步优先**：所有 I/O 操作均为异步
2. **连接池**：数据库、缓存等自动连接池管理
3. **缓存层**：内置多级缓存支持
4. **任务队列**：后台任务异步执行
5. **日志异步写入**：不阻塞业务流程

### 基准数据

在标准硬件上（假设场景）：

- **吞吐量**：~5000 req/s（单个实例，简单 API）
- **延迟**：P99 < 100ms
- **内存占用**：~80-150MB（基础应用）

## 依赖关系

```
aury-boot
├── FastAPI >= 0.122.0
├── SQLAlchemy >= 2.0.44
├── pydantic >= 2.12
├── loguru (日志)
├── uvicorn[standard] (ASGI 服务器)
├── typer (命令行)
├── APScheduler (定时，可选)
├── redis (可选)
├── asyncpg (PostgreSQL 驱动，可选)
└── ...其他基础库
```

## 下一步

- 查看 [02-installation-guide.md](./02-installation-guide.md) 学习安装
- 查看 [03-project-structure.md](./03-project-structure.md) 了解项目结构



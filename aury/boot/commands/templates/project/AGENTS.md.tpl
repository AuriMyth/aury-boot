# AGENTS.md

> 这是给 AI 编程助手阅读的项目上下文文件。根据开发任务类型，阅读下方「开发任务文档索引」中对应的文档。

## 项目概述

- **项目名称**: {project_name}
- **包名**: {package_name}
- **框架**: [Aury Boot](https://github.com/AuriMyth/aury-boot)（基于 FastAPI + SQLAlchemy 2.0 的微服务框架）
- **Python 版本**: >= 3.13
- **包管理**: uv（推荐）或 pip

## 常用命令

```bash
# 开发服务器（热重载）
aury server dev

# 数据库迁移
aury migrate make -m "描述"    # 生成迁移
aury migrate up                # 执行迁移
aury migrate down              # 回滚迁移
aury migrate status            # 查看状态
aury migrate show              # 查看历史

# 测试
pytest
pytest tests/test_xxx.py -v

# 代码检查
ruff check .
mypy {package_name}/
```

> ⚠️ **重要**：数据库迁移文件**必须**使用 `aury migrate make` 命令生成，**禁止**手写迁移文件！

## 项目结构

```
{project_name}/
├── {package_name}/           # 主代码包
│   ├── models/               # SQLAlchemy ORM 模型
│   ├── repositories/         # 数据访问层（Repository 模式）
│   ├── services/             # 业务逻辑层
│   ├── schemas/              # Pydantic 请求/响应模型
│   ├── api/                  # FastAPI 路由
│   ├── exceptions/           # 业务异常
│   ├── tasks/                # 异步任务（Dramatiq）
│   └── schedules/            # 定时任务
├── aury_docs/               # 开发文档（由 aury docs dev 生成）
├── tests/                    # 测试
├── migrations/               # 数据库迁移
└── main.py                   # 应用入口
```

## 重要提醒

> **修改代码前，必须先阅读对应的文档！**
> 
> 框架的 API 可能与常见框架不同，不要猜测。请查看 `aury_docs/` 下对应的文档。

## 开发任务文档索引

根据你要开发的功能类型，**必须阅读**对应的文档：

### CRUD / 数据库相关（最常见）

开发 CRUD 功能时，按顺序阅读以下文档：

1. **[aury_docs/01-model.md](./aury_docs/01-model.md)** - Model 定义规范
   - 基类选择（UUIDAuditableStateModel 等）
   - 字段类型映射
   - 约束定义（软删除模型的复合唯一约束）

2. **[aury_docs/02-repository.md](./aury_docs/02-repository.md)** - Repository 使用
   - BaseRepository API
   - Filters 语法（__gt, __like 等）
   - 自动提交机制

3. **[aury_docs/03-service.md](./aury_docs/03-service.md)** - Service 编写与事务
   - 事务装饰器 @transactional
   - 跨 Service 调用
   - 事务传播 / Savepoints / on_commit 回调
   - SELECT FOR UPDATE

4. **[aury_docs/04-schema.md](./aury_docs/04-schema.md)** - Pydantic Schema
   - 请求/响应模型
   - 常用验证

5. **[aury_docs/05-api.md](./aury_docs/05-api.md)** - API 路由
   - 路由编写示例
   - 依赖注入模式

6. **[aury_docs/06-exception.md](./aury_docs/06-exception.md)** - 异常处理
   - 内置异常
   - 自定义异常

### 异步任务 / 定时任务

- **[aury_docs/08-scheduler.md](./aury_docs/08-scheduler.md)** - 定时任务（APScheduler）
- **[aury_docs/09-tasks.md](./aury_docs/09-tasks.md)** - 异步任务（Dramatiq）

### 基础设施

- **[aury_docs/07-cache.md](./aury_docs/07-cache.md)** - 缓存
- **[aury_docs/10-storage.md](./aury_docs/10-storage.md)** - 对象存储（S3/COS/OSS）
- **[aury_docs/11-logging.md](./aury_docs/11-logging.md)** - 日志
- **[aury_docs/12-admin.md](./aury_docs/12-admin.md)** - 管理后台（SQLAdmin）
- **[aury_docs/13-channel.md](./aury_docs/13-channel.md)** - 流式通道（SSE）
- **[aury_docs/14-mq.md](./aury_docs/14-mq.md)** - 消息队列
- **[aury_docs/15-events.md](./aury_docs/15-events.md)** - 事件总线

### 配置 / CLI / 环境变量

- **[aury_docs/00-overview.md](./aury_docs/00-overview.md)** - 项目概览与最佳实践
- **[aury_docs/99-cli.md](./aury_docs/99-cli.md)** - CLI 命令参考
- **[.env.example](./.env.example)** - 所有可用环境变量

## 代码规范

### Model 规范

- **必须**继承框架预定义基类，**不要**直接继承 `Base`
- **推荐**使用 `UUIDAuditableStateModel`（UUID 主键 + 时间戳 + 软删除）
- 软删除模型**必须**使用复合唯一约束（包含 `deleted_at`），不能单独使用 `unique=True`
- **不建议**使用数据库外键（`ForeignKey`），通过程序控制关系，便于分库分表和微服务拆分

```python
# ✅ 正确
from aury.boot.domain.models import UUIDAuditableStateModel

class User(UUIDAuditableStateModel):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), index=True)
    __table_args__ = (
        UniqueConstraint("email", "deleted_at", name="uq_users_email_deleted"),
    )

# ❌ 错误：直接继承 Base
from aury.boot.domain.models.base import Base
class User(Base): ...
```

### Service 规范

- 写操作**必须**使用 `@transactional` 装饰器
- 只读操作可以不加事务装饰器
- 跨 Service 调用通过共享 session 实现事务共享

```python
from aury.boot.domain.transaction import transactional

class UserService(BaseService):
    @transactional
    async def create(self, data: UserCreate) -> User:
        # 自动事务管理
        return await self.repo.create(data.model_dump())
```

### Manager API 规范

所有基础设施 Manager 统一使用 `initialize()` 方法初始化：

```python
# ✅ 正确
from aury.boot.infrastructure.cache import CacheManager
cache = CacheManager.get_instance()
await cache.initialize(backend="redis", url="redis://localhost:6379")

from aury.boot.infrastructure.storage import StorageManager, StorageConfig
storage = StorageManager.get_instance()
await storage.initialize(StorageConfig(...))

from aury.boot.infrastructure.events import EventBusManager
events = EventBusManager.get_instance()
await events.initialize(backend="memory")

# ❗ 注意：没有 configure() 方法，配置直接传入 initialize()
```

### 异常规范

- **必须**继承框架异常类，**不要**直接继承 `Exception`
- 使用框架内置异常：`NotFoundError`, `AlreadyExistsError`, `UnauthorizedError` 等

```python
# ✅ 正确
from aury.boot.application.errors import NotFoundError
raise NotFoundError("用户不存在", resource=user_id)

# ❌ 错误
raise Exception("用户不存在")
```

### 响应规范

- **不要**自定义通用响应 Schema
- 使用框架内置：`BaseResponse`, `PaginationResponse`

```python
from aury.boot.application.interfaces.egress import BaseResponse
return BaseResponse(code=200, message="成功", data=user)
```

## 禁止操作

- ❌ 不要直接修改 `aury/boot/` 框架代码
- ❌ 不要在 Model 中直接使用 `unique=True`（软删除模型）
- ❌ 不要自定义通用响应 Schema
- ❌ 不要在 Repository 之外直接操作 session
- ❌ 不要提交 `.env` 文件到版本库

## 需要确认的操作

- ⚠️ 添加新的 pip 依赖前请确认
- ⚠️ 修改数据库迁移前请确认
- ⚠️ 删除文件前请确认

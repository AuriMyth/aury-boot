# AuriMyth Foundation Kit 开发规范

## 目录

- [架构层次](#架构层次)
- [依赖关系规则](#依赖关系规则)
- [代码组织规范](#代码组织规范)
- [常量定义规范](#常量定义规范)
- [异常处理规范](#异常处理规范)
- [配置管理规范](#配置管理规范)
- [组件设计规范](#组件设计规范)
- [命名规范](#命名规范)
- [导入规范](#导入规范)
- [类型提示规范](#类型提示规范)

---

## 架构层次

Foundation Kit 采用分层架构，从底层到顶层依次为：

```
common/          # 最基础层（只依赖标准库和第三方基础库）
  ├── exceptions.py      # FoundationError（异常基类）
  ├── logging.py         # 日志系统（纯日志功能，无 HTTP 依赖）
  └── i18n/              # 国际化（翻译、日期/数字本地化）

core/            # 核心层（业务逻辑基础）
  ├── exceptions.py      # CoreException, ModelError, VersionConflictError
  ├── models.py          # ORM 模型基类
  ├── repository.py       # 仓储模式
  └── service.py         # 服务模式

infrastructure/  # 基础设施层（外部依赖实现）
  ├── database/          # 数据库管理
  ├── cache/            # 缓存管理
  ├── storage/          # 对象存储
  ├── tasks/            # 任务队列
  └── scheduler/        # 调度器

application/     # 应用层（API、配置、接口）
  ├── config/           # 配置管理
  ├── constants.py      # 应用层常量（ServiceType, SchedulerMode）
  ├── middleware/      # HTTP 中间件
  ├── interfaces/       # API 接口定义
  ├── app.py           # FoundationApp
  └── ...
```

## 依赖关系规则

### 基本原则

```
application → core → infrastructure → common
```

**规则**：
- ✅ `application` 可以引用所有层
- ✅ `core` 可以引用 `infrastructure` 和 `common`
- ✅ `infrastructure` 可以引用 `common`
- ✅ `common` 不依赖任何层（最底层，只依赖标准库和第三方基础库）

### 禁止的反向依赖

- ❌ `common` 不能引用 `core`、`infrastructure`、`application`
- ❌ `core` 不能引用 `application`
- ❌ `infrastructure` 不能引用 `application`、`core`

### 跨层通信

当需要跨层通信时，应该：
1. **配置传递**：通过参数传递，而不是直接导入
2. **适配层**：在 `application` 层创建适配层，将应用配置转换为基础设施层需要的参数
3. **接口抽象**：使用接口/抽象类定义依赖，而不是具体实现

**示例**：
```python
# ✅ 正确：application 层转换配置
class TaskComponent(Component):
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        from aurimyth.foundation_kit.infrastructure.tasks.constants import TaskRunMode
        
        task_manager = TaskManager.get_instance()
        # 将 application 层的 ServiceType 转换为 infrastructure 层的 TaskRunMode
        if config.service.service_type == ServiceType.WORKER:
            run_mode = TaskRunMode.WORKER
        else:
            run_mode = TaskRunMode.PRODUCER
        
        await task_manager.initialize(run_mode=run_mode, ...)

# ❌ 错误：infrastructure 层直接使用 application 层常量
from aurimyth.foundation_kit.application.constants import ServiceType  # 反向依赖！
```

## 代码组织规范

### 1. Common 层

**职责**：最基础的工具层，不依赖任何业务逻辑

**允许的内容**：
- ✅ 异常基类（`FoundationError`）
- ✅ 日志系统（纯日志功能，无 HTTP 依赖）
- ✅ 国际化（i18n）
- ✅ 通用工具函数（只依赖标准库）

**禁止的内容**：
- ❌ HTTP 框架依赖（FastAPI、Starlette）
- ❌ 业务逻辑依赖
- ❌ 基础设施依赖

**文件组织**：
```
common/
  ├── __init__.py        # 统一导出
  ├── exceptions.py      # 异常基类
  ├── logging.py         # 日志系统
  └── i18n/              # 国际化
      ├── __init__.py
      └── translator.py
```

### 2. Core 层

**职责**：业务逻辑基础，领域模型和仓储

**允许的内容**：
- ✅ ORM 模型基类
- ✅ Repository 接口和实现
- ✅ Service 基类
- ✅ 领域异常（继承 `FoundationError`）

**文件组织**：
```
core/
  ├── __init__.py
  ├── exceptions.py      # CoreException, ModelError, VersionConflictError
  ├── models.py          # BaseModel, TimestampedModel, etc.
  ├── repository.py      # IRepository, BaseRepository
  └── service.py         # BaseService
```

### 3. Infrastructure 层

**职责**：外部依赖的实现，每个组件独立管理

**组织原则**：
- 每个组件（database、cache、tasks 等）都有独立的目录
- 每个组件包含：`manager.py`、`exceptions.py`、`settings.py`、`constants.py`（如果需要）

**文件组织**：
```
infrastructure/
  ├── database/
  │   ├── __init__.py
  │   ├── manager.py      # DatabaseManager
  │   ├── exceptions.py   # DatabaseError, DatabaseConnectionError, etc.
  │   └── settings.py     # DatabaseSettings
  ├── tasks/
  │   ├── __init__.py
  │   ├── manager.py      # TaskManager
  │   ├── exceptions.py   # TaskError, TaskQueueError, etc.
  │   ├── settings.py     # TaskSettings
  │   └── constants.py    # TaskQueueName, TaskRunMode（组件内部常量）
  └── ...
```

**重要原则**：
- ✅ 每个组件可以有**自己的内部常量**（如 `TaskRunMode`）
- ❌ 不能使用 `application` 层的常量（如 `ServiceType`）
- ✅ `application` 层负责将应用配置转换为组件需要的参数

### 4. Application 层

**职责**：应用配置、API 接口、组件编排

**文件组织**：
```
application/
  ├── __init__.py
  ├── constants.py        # ComponentName, ServiceType, SchedulerMode（应用层常量）
  ├── config/
  │   └── settings.py     # BaseConfig, DatabaseSettings, etc.
  ├── middleware/         # HTTP 中间件
  │   └── logging.py      # RequestLoggingMiddleware, log_request
  ├── interfaces/         # API 接口定义
  │   ├── errors.py        # BaseError, ErrorHandler
  │   ├── ingress.py       # 请求模型
  │   └── egress.py        # 响应模型
  └── app.py              # FoundationApp, Component
```

## 常量定义规范

### 1. 应用层常量（`application/constants.py`）

**用途**：应用配置相关的常量，用于组件启用判断

**包含**：
- `ComponentName` - 组件名称枚举
- `ServiceType` - 服务类型（API、WORKER、SCHEDULER）
- `SchedulerMode` - 调度器模式（EMBEDDED、STANDALONE、DISABLED）

**使用场景**：
- `Component.can_enable()` 中判断是否启用组件
- `FoundationApp` 的组件注册逻辑

### 2. Infrastructure 层内部常量

**原则**：每个组件可以有**自己的内部常量**，用于组件内部逻辑

**示例**：
```python
# infrastructure/tasks/constants.py
class TaskRunMode(str, Enum):
    """任务运行模式（任务队列模块内部使用）。"""
    WORKER = "worker"      # 执行者模式
    PRODUCER = "producer"  # 生产者模式

class TaskQueueName(str, Enum):
    """任务队列名称常量。"""
    DEFAULT = "default"
    HIGH_PRIORITY = "high_priority"
```

**重要**：
- ✅ 这些常量只在组件内部使用
- ❌ 不能依赖 `application` 层的常量
- ✅ `application` 层负责转换：`ServiceType.WORKER` → `TaskRunMode.WORKER`

### 3. 常量命名规范

- 使用 `Enum` 类，继承 `str, Enum`
- 枚举值使用大写字母和下划线：`WORKER`, `HIGH_PRIORITY`
- 枚举值字符串使用小写字母和下划线：`"worker"`, `"high_priority"`

## 异常处理规范

### 异常层次结构

```
FoundationError (common/exceptions.py)
  ├── CoreException (core/exceptions.py)
  │   └── ModelError
  │       └── VersionConflictError
  │
  └── Infrastructure 层异常（infrastructure/*/exceptions.py）
      ├── DatabaseError
      ├── CacheError
      ├── StorageError
      ├── TaskError
      └── SchedulerError
```

### 异常定义规范

1. **每个层定义自己的异常**：
   - `common/exceptions.py` - `FoundationError`（最基础）
   - `core/exceptions.py` - `CoreException`, `ModelError`, `VersionConflictError`
   - `infrastructure/*/exceptions.py` - 各组件异常（继承 `FoundationError`）

2. **异常命名**：
   - 使用完整的单词，不使用缩写：`DatabaseError` ✅，`DbError` ❌
   - 以 `Error` 结尾：`ModelError`, `VersionConflictError`

3. **异常继承**：
   - 所有异常都继承 `FoundationError`
   - Infrastructure 层异常直接继承 `FoundationError`（不继承 `CoreException`）

### 异常使用规范

```python
# ✅ 正确：core 层使用自己的异常
from aurimyth.foundation_kit.core.exceptions import VersionConflictError

# ✅ 正确：application 层可以包装 core 层异常
from aurimyth.foundation_kit.core.exceptions import VersionConflictError as CoreVersionConflictError

class VersionConflictError(BaseError):
    @classmethod
    def from_core_exception(cls, exc: CoreVersionConflictError) -> VersionConflictError:
        return cls(...)

# ❌ 错误：core 层不能使用 application 层异常
from aurimyth.foundation_kit.application.interfaces.errors import VersionConflictError  # 反向依赖！
```

## 配置管理规范

### 配置分层

1. **Infrastructure 层配置**：
   - 每个组件有自己的 `settings.py`
   - 使用 `pydantic-settings` 的 `BaseSettings`
   - 环境变量前缀：`DATABASE_*`, `CACHE_*`, `TASK_*`

2. **Application 层配置**：
   - `application/config/settings.py` 继承 infrastructure 层配置
   - 作为适配层，提供统一的配置接口
   - 可以添加应用层特有的配置

**示例**：
```python
# infrastructure/database/settings.py
class DatabaseSettings(BaseSettings):
    url: str
    echo: bool = False
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

# application/config/settings.py
from aurimyth.foundation_kit.infrastructure.database.settings import (
    DatabaseSettings as InfrastructureDatabaseSettings,
)

class DatabaseSettings(InfrastructureDatabaseSettings):
    """应用层数据库配置（适配层）。"""
    pass
```

### 配置使用规范

- ✅ Infrastructure 层组件使用自己的 `settings.py`
- ✅ Application 层使用 `application/config/settings.py`
- ❌ Infrastructure 层不能直接使用 `application/config/settings.py`

## 组件设计规范

### Component 基类

所有功能单元（中间件、数据库、缓存、任务等）都统一为 `Component`：

```python
class Component(ABC):
    name: str  # 组件名称
    enabled: bool = True  # 是否启用
    depends_on: list[str] = []  # 依赖的组件名称
    
    def can_enable(self, config: BaseConfig) -> bool:
        """判断是否启用（基于配置）。"""
        return self.enabled
    
    @abstractmethod
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        """初始化组件。"""
        pass
    
    @abstractmethod
    async def teardown(self, app: FoundationApp) -> None:
        """清理组件。"""
        pass
```

### 组件设计原则

1. **抽象统一**：所有功能单元都是 `Component`，无特殊处理
2. **可扩展**：子类可以覆盖 `items` 列表，添加/移除/替换组件
3. **依赖声明**：通过 `depends_on` 声明依赖，框架自动拓扑排序
4. **配置驱动**：通过 `can_enable()` 基于配置判断是否启用

### 组件转换规范

当 infrastructure 层组件需要 application 层配置时，应该在 `Component.setup()` 中进行转换：

```python
class TaskComponent(Component):
    async def setup(self, app: FoundationApp, config: BaseConfig) -> None:
        from aurimyth.foundation_kit.infrastructure.tasks.constants import TaskRunMode
        
        task_manager = TaskManager.get_instance()
        # 将 application 层的 ServiceType 转换为 infrastructure 层的 TaskRunMode
        if config.service.service_type == ServiceType.WORKER:
            run_mode = TaskRunMode.WORKER
        else:
            run_mode = TaskRunMode.PRODUCER
        
        await task_manager.initialize(run_mode=run_mode, ...)
```

## 命名规范

### 1. 模块和包命名

- 使用小写字母和下划线：`database`, `task_queue`, `request_logging`
- 避免缩写：`database` ✅，`db` ❌

### 2. 类命名

- 使用 `PascalCase`：`DatabaseManager`, `RequestLoggingMiddleware`
- 异常类以 `Error` 结尾：`DatabaseError`, `VersionConflictError`
- 不使用缩写：`DatabaseError` ✅，`DbError` ❌

### 3. 常量命名

- 枚举类使用 `PascalCase`：`ServiceType`, `TaskRunMode`
- 枚举值使用 `UPPER_SNAKE_CASE`：`WORKER`, `HIGH_PRIORITY`
- 枚举值字符串使用 `lower_snake_case`：`"worker"`, `"high_priority"`

### 4. 函数和变量命名

- 使用 `snake_case`：`setup_logging`, `get_instance`
- 布尔值使用 `is_` 或 `has_` 前缀：`is_initialized`, `has_broker`

## 导入规范

### 1. 导入顺序

1. 标准库
2. 第三方库
3. 本地模块（按层次顺序：common → core → infrastructure → application）

```python
from __future__ import annotations

# 标准库
from collections.abc import Callable
from typing import TypeVar

# 第三方库
from loguru import logger
from pydantic import BaseModel

# 本地模块（按层次顺序）
from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.core.exceptions import ModelError
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager
```

### 2. 导入分组

使用空行分隔不同组：
```python
# 标准库
import os
from typing import Any

# 第三方库
from loguru import logger

# 本地模块
from aurimyth.foundation_kit.common.logging import logger
```

### 3. 避免循环导入

- 使用 `TYPE_CHECKING` 延迟导入类型提示
- 在函数内部导入，而不是模块级别

## 类型提示规范

### 1. Python 3.13 语法

使用 Python 3.13 的新语法：

```python
# ✅ 正确（Python 3.13）
def func(items: list[str]) -> dict[str, int]:
    pass

# ❌ 错误（旧语法）
from typing import List, Dict
def func(items: List[str]) -> Dict[str, int]:
    pass
```

### 2. 类型提示要求

- 所有公共函数必须有类型提示
- 使用 `from __future__ import annotations` 启用延迟求值
- 复杂类型使用 `TypeVar` 或 `Generic`

### 3. 可选类型

```python
# ✅ 正确
def func(value: str | None = None) -> None:
    pass

# ❌ 错误
from typing import Optional
def func(value: Optional[str] = None) -> None:
    pass
```

## HTTP 相关代码规范

### 1. HTTP 中间件位置

所有 HTTP 相关的代码（中间件、装饰器）应该在 `application/middleware/` 目录：

```
application/
  └── middleware/
      └── logging.py      # RequestLoggingMiddleware, log_request
```

### 2. Common 层禁止 HTTP 依赖

`common` 层不能包含任何 HTTP 框架依赖：

```python
# ❌ 错误：common 层不能有 HTTP 依赖
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# ✅ 正确：移到 application/middleware/logging.py
```

## 测试规范

### 1. 测试文件位置

测试文件应该在 `testing/` 目录，保持独立模块：

```
testing/
  ├── __init__.py
  ├── base.py          # TestCase
  ├── client.py        # TestClient
  └── factory.py       # Factory
```

### 2. 测试依赖

- `testing/` 可以依赖所有层（用于测试）
- 但不应在 `common` 层中

## 代码质量规范

### 1. Linter 配置

使用 `ruff` 进行代码检查，配置在 `pyproject.toml`：

```toml
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP"]
ignore = []
```

### 2. 代码格式化

- 使用 `ruff format` 进行格式化
- 导入自动排序
- 行长度限制：100 字符

### 3. 文档字符串

- 所有公共类、函数必须有文档字符串
- 使用中文编写文档字符串
- 包含参数说明、返回值说明、使用示例

## 向后兼容性政策

### 核心原则

**禁止向后兼容**：Foundation Kit 不提供任何向后兼容功能。

### 政策说明

1. **不保留旧 API**：
   - 当 API 发生变化时，直接删除旧版本
   - 不提供 `deprecated` 警告或过渡期
   - 不保留 `_old`、`_legacy` 等后缀的函数或类

2. **不兼容旧字段**：
   - 当数据结构发生变化时，直接移除旧字段支持
   - 例如：软删除从 `yn` 字段迁移到 `deleted_at` 字段时，直接删除 `yn` 字段的支持代码

3. **不兼容旧配置**：
   - 当配置格式发生变化时，直接使用新格式
   - 不提供配置迁移工具或兼容层

4. **版本升级策略**：
   - 重大变更通过主版本号（Major Version）升级
   - 用户需要根据变更日志手动升级代码
   - 不提供自动迁移脚本

### 实施要求

- ❌ **禁止**：添加 `@deprecated` 装饰器
- ❌ **禁止**：保留旧函数/类用于兼容
- ❌ **禁止**：在代码中添加 "兼容旧代码" 的注释或逻辑
- ❌ **禁止**：提供配置迁移工具
- ✅ **要求**：直接删除旧代码
- ✅ **要求**：在变更日志中明确说明破坏性变更
- ✅ **要求**：通过版本号明确标识破坏性变更

### 示例

```python
# ❌ 错误：保留向后兼容代码
def _build_base_query(self) -> Select:
    query = select(self._model_class)
    if hasattr(self._model_class, "deleted_at"):
        query = query.where(self._model_class.deleted_at.is_(None))
    elif hasattr(self._model_class, "yn"):  # 兼容旧代码
        query = query.where(self._model_class.yn.is_(True))
    return query

# ✅ 正确：直接使用新实现
def _build_base_query(self) -> Select:
    query = select(self._model_class)
    if hasattr(self._model_class, "deleted_at"):
        query = query.where(self._model_class.deleted_at.is_(None))
    return query
```

## 总结

### 核心原则

1. **分层清晰**：common → core → infrastructure → application
2. **依赖单向**：只能向下依赖，不能向上依赖
3. **配置转换**：application 层负责将应用配置转换为组件参数
4. **组件独立**：infrastructure 层组件使用自己的内部常量和配置
5. **HTTP 隔离**：HTTP 相关代码只在 application 层

### 检查清单

在提交代码前，检查：

- [ ] 是否遵循依赖关系规则？
- [ ] 常量是否放在正确的层？
- [ ] 异常是否继承 `FoundationError`？
- [ ] HTTP 相关代码是否在 `application/middleware/`？
- [ ] 是否使用 Python 3.13 类型提示语法？
- [ ] 是否有完整的文档字符串？
- [ ] 是否通过 `ruff` 检查？
- [ ] **是否包含任何向后兼容代码？**（禁止）
- [ ] **是否包含 `deprecated`、`legacy`、`兼容` 等关键词？**（禁止）


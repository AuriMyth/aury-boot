# 7. 中间件系统 - 完整指南

## 中间件概述

中间件（Middleware）是 Kit 中处理 **HTTP 请求拦截**的功能单元。与组件（Component）不同，中间件专注于请求/响应的处理链。

### 中间件 vs 组件

| 特性 | 中间件（Middleware） | 组件（Component） |
|------|---------------------|------------------|
| **职责** | HTTP 请求处理 | 基础设施生命周期管理 |
| **执行时机** | 每个 HTTP 请求 | 应用启动/关闭 |
| **注册方式** | 同步（应用构造阶段） | 异步（lifespan 阶段） |
| **排序方式** | 按 `order` 属性 | 按 `depends_on` 依赖 |
| **典型场景** | CORS、日志、认证 | 数据库、缓存、任务队列 |

### 为什么分离中间件和组件？

```python
# ❌ 旧设计：混合在一起，职责不清
class MyApp(FoundationApp):
    items = [
        RequestLoggingComponent,  # 实际是中间件
        DatabaseComponent,        # 实际是组件
    ]

# ✅ 新设计：职责分离，清晰明了
class MyApp(FoundationApp):
    middlewares = [
        RequestLoggingMiddleware,  # 中间件
        CORSMiddleware,
    ]
    components = [
        DatabaseComponent,         # 组件
        CacheComponent,
    ]
```

## 中间件结构

### 基类定义

```python
from aury.boot.application.app.base import Middleware
from aury.boot.application.config import BaseConfig
from starlette.middleware import Middleware as StarletteMiddleware

class Middleware(ABC):
    name: str                    # 中间件唯一标识
    enabled: bool = True         # 是否启用
    order: int = 0               # 执行顺序（数字小的先执行）
    
    def can_enable(self, config: BaseConfig) -> bool:
        """条件启用：返回 False 则跳过此中间件"""
        return self.enabled
    
    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建中间件实例，由框架统一注册"""
        pass
```

### 生命周期

```
应用构造 → 中间件 register() → lifespan 启动 → 组件 setup()
                                              ↓
                              HTTP 请求 → 中间件处理链
                                              ↓
                              lifespan 关闭 → 组件 teardown()
```

## 内置中间件

### 1. RequestLoggingMiddleware

HTTP 请求日志中间件，自动记录所有请求的详细信息。

```python
from aury.boot.application.app.middlewares import RequestLoggingMiddleware

class MyApp(FoundationApp):
    middlewares = [
        RequestLoggingMiddleware,
    ]

# 自动记录：
# → GET /api/users | 客户端: 127.0.0.1 | Trace-ID: abc123
# ← GET /api/users | 状态: 200 | 耗时: 0.015s
```

**记录的信息**：
- 请求方法、路径、查询参数
- 客户端 IP、User-Agent
- 响应状态码、耗时
- 链路追踪 ID（X-Trace-ID / X-Request-ID）

**特性**：
- `order = 0`：最先执行，确保记录所有请求
- 自动生成或传递 Trace ID
- 慢请求警告（超过 1 秒）

### 2. CORSMiddleware

CORS 跨域处理中间件。

```python
from aury.boot.application.app.middlewares import CORSMiddleware

class MyApp(FoundationApp):
    middlewares = [
        RequestLoggingMiddleware,
        CORSMiddleware,
    ]

# 配置 CORS（.env 或环境变量）
# CORS_ORIGINS=["http://localhost:3000", "https://example.com"]
# CORS_ALLOW_CREDENTIALS=true
# CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE"]
# CORS_ALLOW_HEADERS=["*"]
```

**特性**：
- `order = 10`：在请求日志之后执行
- 仅当配置了 `origins` 时启用

## 自定义中间件

### 基本结构

```python
from aury.boot.application.app.base import Middleware
from aury.boot.application.config import BaseConfig
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware

class AuthMiddleware(Middleware):
    """认证中间件"""
    
    name = "auth"
    enabled = True
    order = 20  # 在 CORS 之后执行
    
    def can_enable(self, config: BaseConfig) -> bool:
        """仅在配置了认证时启用"""
        return self.enabled and hasattr(config, 'auth_enabled') and config.auth_enabled
    
    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建认证中间件实例"""
        from my_app.auth import JWTAuthBackend
        
        return StarletteMiddleware(
            AuthenticationMiddleware,
            backend=JWTAuthBackend(config.jwt_secret),
        )
```

### 实际示例：请求限流

```python
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware import Middleware as StarletteMiddleware

class RateLimitMiddleware(Middleware):
    """请求限流中间件"""
    
    name = "rate_limit"
    enabled = True
    order = 5  # 在日志之后、CORS 之前
    
    def can_enable(self, config: BaseConfig) -> bool:
        """仅在生产环境启用"""
        return self.enabled and config.env == "production"
    
    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建限流中间件实例"""
        return StarletteMiddleware(SlowAPIMiddleware)
```

### 实际示例：请求 ID 注入

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.requests import Request
import uuid

class RequestIDHTTPMiddleware(BaseHTTPMiddleware):
    """Starlette 原生中间件实现"""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestIDMiddleware(Middleware):
    """请求 ID 中间件"""
    
    name = "request_id"
    enabled = True
    order = 1  # 在日志之后立即执行
    
    def build(self, config: BaseConfig) -> StarletteMiddleware:
        """构建请求 ID 中间件实例"""
        return StarletteMiddleware(RequestIDHTTPMiddleware)
```

## 中间件注册

### 方式 1：类属性（推荐）

```python
from aury.boot.application.app.base import FoundationApp
from aury.boot.application.app.middlewares import (
    RequestLoggingMiddleware,
    CORSMiddleware,
)

class MyApp(FoundationApp):
    middlewares = [
        RequestLoggingMiddleware,
        CORSMiddleware,
        AuthMiddleware,  # 自定义中间件
    ]

app = MyApp(config=config)
```

### 方式 2：条件注册

```python
class MyApp(FoundationApp):
    middlewares = [
        RequestLoggingMiddleware,
    ]
    
    def __init__(self, *args, **kwargs):
        # 在 super().__init__() 之前修改 middlewares
        if some_condition:
            self.middlewares = [
                RequestLoggingMiddleware,
                CORSMiddleware,
            ]
        super().__init__(*args, **kwargs)
```

## 执行顺序

中间件按 `order` 属性排序执行（数字小的先执行）：

```python
class MiddlewareA(Middleware):
    name = "a"
    order = 0

class MiddlewareB(Middleware):
    name = "b"
    order = 10

class MiddlewareC(Middleware):
    name = "c"
    order = 20

# 执行顺序：A → B → C
# 请求处理链：
# Request → A → B → C → Handler → C → B → A → Response
```

**内置中间件的 order**：
- `RequestLoggingMiddleware`: 0
- `CORSMiddleware`: 10

## 最佳实践

### ✅ 推荐做法

1. **合理设置 order**
   ```python
   # ✅ 好：按职责排序
   class LoggingMiddleware(Middleware):
       order = 0   # 最先，记录所有请求
   
   class AuthMiddleware(Middleware):
       order = 20  # 认证
   
   class RateLimitMiddleware(Middleware):
       order = 30  # 限流
   ```

2. **使用 can_enable 进行条件控制**
   ```python
   # ✅ 好：根据配置决定是否启用
   def can_enable(self, config):
       return config.env != "test"
   ```

3. **保持中间件轻量**
   ```python
   # ✅ 好：只做请求处理相关的事
   def build(self, config):
       return StarletteMiddleware(SomeMiddleware)
   ```

### ❌ 避免的做法

1. **在中间件中做基础设施初始化**
   ```python
   # ❌ 不好：这应该是组件的职责
   class BadMiddleware(Middleware):
       def build(self, config):
           init_database()  # 应该用 Component
           return StarletteMiddleware(SomeMiddleware)
   ```

2. **忽略 order 设置**
   ```python
   # ❌ 不好：可能导致执行顺序问题
   class AuthMiddleware(Middleware):
       order = 0  # 认证不应该最先执行
   ```

## 下一步

- 查看 [08-components-detailed.md](./08-components-detailed.md) 了解组件系统
- 查看 [09-http-advanced.md](./09-http-advanced.md) 了解 HTTP 接口高级用法

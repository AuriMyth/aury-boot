# 21. 日志系统完整指南

## 核心概念

框架日志系统基于 loguru，提供：
- **自动链路追踪**：trace_id 自动注入每条日志，无需手动记录
- **服务上下文隔离**：API/Scheduler/Worker 日志自动分离
- **请求上下文注入**：支持注入 user_id 等自定义字段
- **自定义日志文件**：按业务分离日志（如 payment.log, audit.log）

## 基础使用

### 日志记录

```python
from aury.boot.common.logging import logger

# trace_id 自动包含在日志格式中，无需手动记录
logger.debug("调试信息")
logger.info("用户创建成功")
logger.warning("缓存连接缓慢")
logger.error("数据库连接失败")
logger.critical("系统即将崩溃")
```

输出示例：
```
2024-01-15 12:00:00 | INFO | app.service:create_user:42 | abc123 - 用户创建成功
```

### 异常日志

```python
try:
    risky_operation()
except Exception as e:
    # 自动记录 Java 风格堆栈
    logger.exception(f"操作失败: {e}")
```

## HTTP 请求日志

框架内置的 `RequestLoggingMiddleware` 自动记录：

```
# 请求日志（包含查询参数和请求体）
→ POST /api/users | 参数: {'page': '1'} | Body: {"name": "test"} | 客户端: 127.0.0.1 | Trace-ID: abc123

# 响应日志（包含状态码和耗时）
← POST /api/users | 状态: 201 | 耗时: 0.123s | Trace-ID: abc123

# 请求上下文（用户注册的字段）
[REQUEST_CONTEXT] Trace-ID: abc123 | user_id: 123 | tenant_id: 456

# 慢请求警告（超过 1 秒）
慢请求: GET /api/reports | 耗时: 2.345s (超过1秒) | Trace-ID: abc123
```

## 注入用户信息

框架不内置用户系统，但支持注入自定义请求上下文：

### 步骤 1：定义上下文变量

```python
# app/auth/context.py
from contextvars import ContextVar
from aury.boot.common.logging import register_request_context

# 定义上下文变量
_user_id: ContextVar[str] = ContextVar("user_id", default="")
_tenant_id: ContextVar[str] = ContextVar("tenant_id", default="")

def set_user_id(uid: str) -> None:
    _user_id.set(uid)

def set_tenant_id(tid: str) -> None:
    _tenant_id.set(tid)

# 启动时注册（只需一次）
register_request_context("user_id", _user_id.get)
register_request_context("tenant_id", _tenant_id.get)
```

### 步骤 2：创建认证中间件

```python
# app/auth/middleware.py
from aury.boot.application.app import Middleware
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.auth.context import set_user_id, set_tenant_id

class AuthLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 验证用户（你的认证逻辑）
        user = await verify_token(request)
        if user:
            set_user_id(str(user.id))
            set_tenant_id(str(user.tenant_id))
        
        return await call_next(request)

class AuthMiddleware(Middleware):
    name = "auth"
    enabled = True
    order = 50  # 小于 100，在日志中间件之前执行
    
    def build(self, config):
        return StarletteMiddleware(AuthLoggingMiddleware)
```

### 步骤 3：注册中间件

```python
# app/main.py
from aury.boot.application.app import FoundationApp
from aury.boot.application.app.middlewares import (
    RequestLoggingMiddleware,
    CORSMiddleware,
)
from app.auth.middleware import AuthMiddleware

class MyApp(FoundationApp):
    middlewares = [
        AuthMiddleware,           # order=50，先执行
        RequestLoggingMiddleware, # order=100，后执行，此时 user_id 已设置
        CORSMiddleware,
    ]
```

结果：
```
← GET /api/users | 状态: 200 | 耗时: 0.05s | Trace-ID: abc123
[REQUEST_CONTEXT] Trace-ID: abc123 | user_id: 123 | tenant_id: 456
```

## 自定义日志文件

为特定业务创建独立的日志文件：

```python
from aury.boot.common.logging import register_log_sink, logger

# 启动时注册（生成 payment_2024-01-15.log）
register_log_sink("payment", filter_key="payment")
register_log_sink("audit", filter_key="audit")

# 业务代码中使用
logger.bind(payment=True).info(f"支付成功 | 订单: {order_id} | 金额: {amount}")
logger.bind(audit=True).info(f"用户 {user_id} 修改了配置")
```

## 服务上下文隔离

日志自动按服务类型分离：

```
logs/
├── api_info_2024-01-15.log      # API 服务日志
├── api_error_2024-01-15.log
├── scheduler_info_2024-01-15.log # 调度器日志
├── scheduler_error_2024-01-15.log
├── worker_info_2024-01-15.log    # Worker 日志
├── worker_error_2024-01-15.log
└── access_2024-01-15.log         # HTTP 访问日志
```

## 异步任务链路追踪

跨进程任务需要手动传递 trace_id：

```python
from aury.boot.common.logging import get_trace_id, set_trace_id

# 发送任务时传递 trace_id
process_order.send(order_id="123", trace_id=get_trace_id())

# 任务执行时恢复 trace_id
@tm.conditional_task()
async def process_order(order_id: str, trace_id: str | None = None):
    if trace_id:
        set_trace_id(trace_id)
    
    logger.info(f"处理订单: {order_id}")  # 自动包含 trace_id
```

## 性能监控装饰器

```python
from aury.boot.common.logging import log_performance

@log_performance(threshold=1.0)  # 超过 1 秒记录警告
async def slow_operation():
    await heavy_query()
```

## 配置选项

### 环境变量

```bash
LOG_LEVEL=INFO              # 日志级别
LOG_DIR=logs                # 日志目录
LOG_RETENTION_DAYS=7        # 保留天数
LOG_ENABLE_FILE_ROTATION=true
LOG_ENABLE_CONSOLE=true
```

### 程序化配置

```python
from aury.boot.common.logging import setup_logging

setup_logging(
    log_level="INFO",
    log_dir="logs",
    retention_days=7,
    enable_file_rotation=True,
    enable_console=True,
)
```

## 最佳实践

### 1. 不要手动记录 trace_id

```python
# ❌ 错误 - trace_id 已自动包含在日志格式中
trace_id = get_trace_id()
logger.info(f"用户创建 | Trace-ID: {trace_id}")

# ✅ 正确 - 直接记录
logger.info("用户创建")
```

### 2. 使用合适的日志级别

```python
# ❌ 过度 - 循环中每次都记录
for user in users:
    logger.info(f"处理用户: {user.id}")

# ✅ 简洁 - 只记录摘要
logger.info(f"处理 {len(users)} 个用户")
```

### 3. 结构化日志

```python
# ❌ 缺少上下文
logger.error("操作失败")

# ✅ 包含关键信息
logger.error("User.create failed", extra={
    "email": email,
    "error_code": "EMAIL_DUPLICATE"
})
```

## API 参考

```python
from aury.boot.common.logging import (
    logger,                    # 日志实例
    setup_logging,             # 配置日志
    get_trace_id,              # 获取 trace_id
    set_trace_id,              # 设置 trace_id（跨进程任务用）
    register_log_sink,         # 注册自定义日志文件
    register_request_context,  # 注册请求上下文字段
    log_performance,           # 性能监控装饰器
    log_exceptions,            # 异常日志装饰器
)
```

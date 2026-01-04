# 日志

基于 loguru 的日志系统，trace_id 自动注入每条日志，无需手动记录。

## 11.1 基本用法

```python
from aury.boot.common.logging import logger

# trace_id 自动包含在日志格式中，无需手动记录
logger.info("操作成功")
logger.warning("警告信息")
logger.error("错误信息")
logger.exception("异常信息")  # 自动记录堆栈
```

输出示例：
```
2024-01-15 12:00:00 | INFO | app.service:create:42 | abc123 - 操作成功
```

## 11.2 注入用户信息

框架不内置用户系统，但支持注入自定义请求上下文：

```python
# app/auth/context.py
from contextvars import ContextVar
from aury.boot.common.logging import register_request_context

_user_id: ContextVar[str] = ContextVar("user_id", default="")

def set_user_id(uid: str) -> None:
    _user_id.set(uid)

# 启动时注册（只需一次）
register_request_context("user_id", _user_id.get)
```

在认证中间件中设置（order < 100 以在日志中间件前执行）：

```python
class AuthMiddleware(Middleware):
    order = 50  # 在日志中间件(order=100)之前执行
    
    async def dispatch(self, request, call_next):
        user = await verify_token(request)
        if user:
            set_user_id(str(user.id))
        return await call_next(request)
```

结果：
```
← GET /api/users | 状态: 200 | 耗时: 0.05s | Trace-ID: abc123
[REQUEST_CONTEXT] Trace-ID: abc123 | user_id: 123
```

## 11.3 性能监控装饰器

```python
from aury.boot.common.logging import log_performance, log_exceptions

@log_performance(threshold=0.5)  # 超过 0.5 秒记录警告
async def slow_operation():
    ...

@log_exceptions  # 自动记录异常
async def risky_operation():
    ...
```

## 11.4 HTTP 请求日志

框架内置 `RequestLoggingMiddleware` 自动记录：

```
# 请求日志（包含查询参数和请求体）
→ POST /api/users | 参数: {{'page': '1'}} | Body: {{"name": "test"}} | Trace-ID: abc123

# 响应日志（包含状态码和耗时）
← POST /api/users | 状态: 201 | 耗时: 0.123s | Trace-ID: abc123

# 慢请求警告（超过 1 秒）
慢请求: GET /api/reports | 耗时: 2.345s (超过1秒) | Trace-ID: abc123
```

## 11.5 自定义日志文件

为特定业务创建独立的日志文件：

```python
from aury.boot.common.logging import register_log_sink, logger

# 启动时注册（生成 payment_2024-01-15.log）
register_log_sink("payment", filter_key="payment")

# 业务代码中使用
logger.bind(payment=True).info(f"支付成功 | 订单: {{order_id}}")
```

## 11.6 异步任务链路追踪

跨进程任务需要手动传递 trace_id：

```python
from aury.boot.common.logging import get_trace_id, set_trace_id

# 发送任务时传递
process_order.send(order_id="123", trace_id=get_trace_id())

# 任务执行时恢复
@tm.conditional_task()
async def process_order(order_id: str, trace_id: str | None = None):
    if trace_id:
        set_trace_id(trace_id)
    logger.info(f"处理订单: {{order_id}}")  # 自动包含 trace_id
```

## 11.7 服务上下文隔离

日志自动按服务类型分离：

```
logs/
├── api_info_2024-01-15.log      # API 服务日志
├── api_error_2024-01-15.log
├── scheduler_info_2024-01-15.log # 调度器日志
├── worker_info_2024-01-15.log    # Worker 日志
└── access_2024-01-15.log         # HTTP 访问日志
```

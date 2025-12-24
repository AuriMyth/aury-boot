# 日志

基于 loguru 的日志系统，支持结构化日志、链路追踪、性能监控。

## 11.1 基本用法

```python
from aury.boot.common.logging import logger

logger.info("操作成功")
logger.warning("警告信息")
logger.error("错误信息", exc_info=True)

# 绑定上下文
logger.bind(user_id=123).info("用户操作")
```

## 11.2 链路追踪

```python
from aury.boot.common.logging import get_trace_id, set_trace_id

# 自动生成或获取当前 trace_id
trace_id = get_trace_id()

# 手动设置（如从请求头获取）
set_trace_id("abc-123")
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

## 11.4 HTTP 请求日志中间件

```python
from aury.boot.application.middleware.logging import RequestLoggingMiddleware

# 在 FoundationApp 中自动启用，也可手动添加
app.add_middleware(
    RequestLoggingMiddleware,
    log_request_body=True,      # 记录请求体（默认 True）
    max_body_length=2000,       # 请求体最大记录长度
    sensitive_fields={{"password", "token"}},  # 敏感字段脱敏
)
```

日志输出示例：
```
INFO → POST /api/users | 客户端: 127.0.0.1 | Trace-ID: abc-123
INFO ← POST /api/users | 状态: 201 | 耗时: 0.052s | Trace-ID: abc-123
```

## 11.5 WebSocket 日志中间件

```python
from aury.boot.application.middleware.logging import WebSocketLoggingMiddleware

app.add_middleware(
    WebSocketLoggingMiddleware,
    log_messages=False,         # 是否记录消息内容（默认 False，注意性能和敏感数据）
    max_message_length=500,     # 消息内容最大记录长度
)
```

日志输出示例：
```
INFO WS → 连接建立: /ws/chat | 客户端: 127.0.0.1:54321 | Trace-ID: abc-123
INFO WS ← 连接关闭: /ws/chat | 时长: 120.5s | 收/发: 45/32 | Trace-ID: abc-123
```

## 11.6 自定义日志文件

```python
from aury.boot.common.logging import register_log_sink

# 注册 access 日志
register_log_sink("access", filter_key="access")

# 写入 access 日志
logger.bind(access=True).info("GET /api/users 200 0.05s")
```

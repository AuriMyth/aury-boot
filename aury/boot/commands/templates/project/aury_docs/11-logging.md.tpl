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

## 11.4 自定义日志文件

```python
from aury.boot.common.logging import register_log_sink

# 注册 access 日志
register_log_sink("access", filter_key="access")

# 写入 access 日志
logger.bind(access=True).info("GET /api/users 200 0.05s")
```

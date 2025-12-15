# 21. 日志系统完整指南

请参考 [00-quick-start.md](./00-quick-start.md) 第 21 章的快速开始。

## 日志配置

### 环境变量

```bash
# 基础配置
LOG_LEVEL=INFO                          # 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_DIR=log                             # 日志文件目录

# 文件轮转配置
LOG_ROTATION_TIME=00:00                 # 每天定时轮转时间
LOG_ROTATION_SIZE=100 MB                # 基于大小的轮转阈值
LOG_RETENTION_DAYS=7                    # 日志保留天数

# 输出配置
LOG_ENABLE_FILE_ROTATION=true           # 启用文件轮转
LOG_ENABLE_CLASSIFY=true                # 按模块/级别分类
LOG_ENABLE_CONSOLE=true                 # 输出到控制台
```

### 程序化配置

```python
from aury.boot.common.logging import setup_logging

setup_logging(
    log_level="INFO",
    log_dir="log",
    enable_file_rotation=True,
    rotation_time="00:00",
    rotation_size="100 MB",
    retention_days=7,
    enable_classify=True,
    enable_console=True,
)
```

## 基础日志

### 日志级别

```python
from aury.boot.common.logging import logger

# DEBUG - 详细的诊断信息
logger.debug("调试信息")

# INFO - 一般信息
logger.info("应用已启动")

# WARNING - 警告信息
logger.warning("缓存连接缓慢")

# ERROR - 错误信息
logger.error("数据库连接失败")

# CRITICAL - 严重错误
logger.critical("系统即将崩溃")
```

### 带上下文的日志

```python
logger.info("用户登录", extra={"user_id": "123", "ip": "192.168.1.1"})

logger.error("处理失败", extra={
    "request_id": "req_123",
    "retry_count": 3,
    "error_code": "DB_ERROR"
})
```

### 异常日志

```python
try:
    risky_operation()
except Exception as e:
    # 自动记录异常堆栈
    logger.error(f"操作失败: {e}", exc_info=True)
```

## 分布式链路追踪

### 自动 Trace ID

```python
from aury.boot.common.logging import get_trace_id, logger

@router.get("/users/{user_id}")
async def get_user(user_id: str):
    # 自动生成和传递 Trace ID
    trace_id = get_trace_id()
    logger.info(f"获取用户 | Trace-ID: {trace_id}")
    
    user = await db.get_user(user_id)
    logger.info(f"用户已获取 | Trace-ID: {trace_id}")
    
    return user
```

### RPC 调用中的追踪

```python
from aury.boot.application.rpc.client import create_rpc_client

@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    trace_id = get_trace_id()
    logger.info(f"获取订单 | Trace-ID: {trace_id}")
    
    # RPC 调用会自动添加 X-Trace-ID 请求头
    client = create_rpc_client("order-service")
    response = await client.get(f"/api/v1/orders/{order_id}")
    
    logger.info(f"订单已获取 | Trace-ID: {trace_id}")
    
    return response.data
```

### 异步任务中的追踪

```python
from aury.boot.common.logging import set_trace_id, get_trace_id

@tm.conditional_task()
async def process_order(order_id: str, trace_id: str = None):
    """处理订单任务"""
    
    # 设置 Trace ID（保持链路连贯）
    if trace_id:
        set_trace_id(trace_id)
    
    trace_id = get_trace_id()
    logger.info(f"开始处理订单 | Order ID: {order_id} | Trace-ID: {trace_id}")
    
    try:
        await process_payment(order_id)
        await send_notification(order_id)
        logger.info(f"订单处理完成 | Trace-ID: {trace_id}")
    except Exception as e:
        logger.error(f"订单处理失败 | Trace-ID: {trace_id}: {e}", exc_info=True)

# 创建任务时传递 Trace ID
trace_id = get_trace_id()
process_order.send(order_id="order123", trace_id=trace_id)
```

## 性能监控

### 执行时间记录

```python
import time
from aury.boot.common.logging import logger

async def slow_operation():
    start_time = time.time()
    
    try:
        # 执行操作
        result = await db.heavy_query()
        return result
    finally:
        duration = time.time() - start_time
        if duration > 1:  # 超过 1 秒时记录警告
            logger.warning(f"操作耗时过长: {duration:.3f}s")
        else:
            logger.debug(f"操作耗时: {duration:.3f}s")
```

### 装饰器方式

```python
from functools import wraps

def log_performance(threshold: float = 1.0):
    """记录超过阈值的函数执行时间"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                if duration > threshold:
                    logger.warning(
                        f"函数 {func.__name__} 耗时: {duration:.3f}s"
                    )
        return wrapper
    return decorator

@log_performance(threshold=2.0)
async def expensive_operation():
    await asyncio.sleep(3)
```

## 异常日志

### 结构化异常日志

```python
from aury.boot.common.logging import logger

try:
    await external_api.call()
except ConnectionError as e:
    logger.error(
        "API 连接失败",
        exc_info=True,
        extra={
            "error_type": type(e).__name__,
            "retry_count": 3,
            "service": "external_api"
        }
    )
except Exception as e:
    logger.error(f"未知错误: {e}", exc_info=True)
```

### 链接异常

```python
import logging

try:
    try:
        result = await operation1()
    except OperationError as e:
        logger.error(f"操作 1 失败: {e}")
        raise
except Exception as e:
    logger.error(f"最终失败: {e}", exc_info=True)
```

## 日志分类

### 按模块分类

当 `LOG_ENABLE_CLASSIFY=true` 时，日志会自动按模块分类：

```
log/
├── app/
│   ├── api.log          # API 路由日志
│   ├── service.log      # 业务服务日志
│   └── repository.log   # 数据访问日志
├── framework/
│   ├── database.log     # 数据库日志
│   └── cache.log        # 缓存日志
└── system.log           # 系统日志
```

### 按级别分类

```
log/
├── debug/
│   ├── 2024-01-15.log
│   └── 2024-01-16.log
├── info/
├── warning/
├── error/
└── critical/
```

## 实际应用

### API 请求日志

```python
from fastapi import Request
from aury.boot.common.logging import logger, get_trace_id

@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = get_trace_id()
    
    logger.info(
        f"请求来临",
        extra={
            "method": request.method,
            "path": request.url.path,
            "trace_id": trace_id
        }
    )
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        f"请求完成",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration": f"{duration:.3f}s",
            "trace_id": trace_id
        }
    )
    
    return response
```

### 业务操作日志

```python
async def create_order(request: OrderCreateRequest):
    trace_id = get_trace_id()
    
    logger.info(f"开始创建订单 | Trace-ID: {trace_id}")
    
    try:
        # 验证
        logger.debug(f"验证订单数据 | Trace-ID: {trace_id}")
        validate_order(request)
        
        # 创建
        logger.info(f"在数据库中创建订单 | Trace-ID: {trace_id}")
        order = await db.create_order(request)
        
        # 后续处理
        logger.info(f"发送订单确认 | Trace-ID: {trace_id}")
        await notification_service.send_confirmation(order)
        
        logger.info(f"订单创建成功 | Order ID: {order.id} | Trace-ID: {trace_id}")
        return order
    
    except ValidationError as e:
        logger.warning(f"订单验证失败: {e} | Trace-ID: {trace_id}")
        raise
    
    except Exception as e:
        logger.error(
            f"订单创建失败: {e}",
            exc_info=True,
            extra={"trace_id": trace_id}
        )
        raise
```

### 数据库操作日志

```python
class UserRepository(BaseRepository):
    async def get_by_email(self, email: str):
        logger.debug(f"查询用户 by email: {email}")
        
        try:
            user = await self.get_by(email=email)
            
            if user:
                logger.debug(f"用户已找到: {user.id}")
            else:
                logger.debug(f"用户未找到: {email}")
            
            return user
        except Exception as e:
            logger.error(f"数据库查询失败: {e}", exc_info=True)
            raise
```

## 日志查看和分析

### 查看实时日志

```bash
# 查看日志文件
tail -f log/app/info.log

# 过滤特定 Trace ID 的日志
grep "trace_id: abc123" log/app/info.log

# 查看错误日志
tail -f log/error/2024-01-15.log
```

### 日志聚合

```bash
# 使用 ELK Stack
# 1. 配置 Filebeat 收集日志
# 2. 推送到 Elasticsearch
# 3. 在 Kibana 中可视化和分析
```

## 最佳实践

### 1. 使用合适的日志级别

```python
# ❌ 不好 - 所有信息都用 info
logger.info("执行 SQL: SELECT * FROM users")

# ✅ 好 - 详细信息用 debug
logger.debug("执行 SQL: SELECT * FROM users")
logger.info("用户列表已获取")
```

### 2. 不要过度记录

```python
# ❌ 过度 - 每次都记录
for user in users:
    logger.info(f"处理用户: {user.id}")  # 在循环中

# ✅ 好 - 只记录重要信息
logger.info(f"处理 {len(users)} 个用户")
```

### 3. 包含足够的上下文

```python
# ❌ 不好 - 缺少上下文
logger.error("操作失败")

# ✅ 好 - 包含足够上下文
logger.error(
    "创建用户失败",
    extra={
        "email": user.email,
        "error_code": "EMAIL_DUPLICATE"
    }
)
```

### 4. 使用结构化日志

```python
# ✅ 推荐 - 便于日志分析工具解析
logger.info(
    "订单已创建",
    extra={
        "order_id": "order_123",
        "user_id": "user_456",
        "amount": 100,
        "trace_id": "abc123"
    }
)
```

---

**总结**：完善的日志系统对于问题诊断、性能监控和系统审计至关重要。使用分布式链路追踪可以轻松跟踪请求的完整路径，大大提高故障排查效率。

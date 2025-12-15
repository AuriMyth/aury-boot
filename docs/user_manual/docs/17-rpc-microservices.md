# 16. RPC 和微服务通信

请参考 [00-quick-start.md](./00-quick-start.md) 第 16 章的基础用法。

## 服务配置

### 环境变量

```bash
# 配置 RPC 服务
RPC_CLIENT_SERVICES={"order-service": "http://order-service:8000", "user-service": "http://user-service:8001"}

# 超时配置
RPC_CLIENT_TIMEOUT=30

# 重试配置
RPC_CLIENT_RETRIES=3
RPC_CLIENT_RETRY_DELAY=1
```

### 自动 DNS 解析

```bash
# 不配置显式映射，使用 DNS 自动解析
# 直接使用服务名，如 http://order-service
```

## 创建 RPC 客户端

### 基础用法

```python
from aury.boot.application.rpc.client import create_rpc_client

# 创建客户端
client = create_rpc_client(service_name="order-service")

# 发起 GET 请求
response = await client.get("/api/v1/orders/123")
order = response.data

# 发起 POST 请求
response = await client.post(
    "/api/v1/orders",
    json={"user_id": "user123", "amount": 100}
)
new_order = response.data
```

### 请求参数

```python
# 查询参数
response = await client.get(
    "/api/v1/orders",
    params={"page": 1, "size": 10, "status": "pending"}
)

# 请求头
response = await client.get(
    "/api/v1/orders/123",
    headers={"Authorization": "Bearer token"}
)

# 请求体
response = await client.post(
    "/api/v1/orders",
    json={"user_id": "user123", "amount": 100}
)
```

## 常见 HTTP 方法

```python
# GET 请求
response = await client.get("/api/v1/users/123")

# POST 请求
response = await client.post("/api/v1/users", json={"name": "John"})

# PUT 请求
response = await client.put("/api/v1/users/123", json={"name": "Jane"})

# PATCH 请求
response = await client.patch("/api/v1/users/123", json={"status": "active"})

# DELETE 请求
response = await client.delete("/api/v1/users/123")
```

## 错误处理

### 基础错误处理

```python
from aury.boot.application.rpc.exceptions import (
    RPCConnectionError,
    RPCTimeoutError,
    RPCResponseError,
)

try:
    response = await client.get("/api/v1/orders/123")
except RPCTimeoutError:
    logger.error("请求超时，服务响应缓慢")
except RPCConnectionError:
    logger.error("连接失败，服务不可用")
except RPCResponseError as e:
    logger.error(f"服务返回错误: {e.status_code} - {e.message}")
except Exception as e:
    logger.error(f"未知错误: {e}")
```

### 重试机制

```python
import asyncio

async def call_with_retry(client, endpoint: str, max_retries: int = 3):
    """带重试的 RPC 调用"""
    
    for attempt in range(max_retries):
        try:
            return await client.get(endpoint)
        except (RPCConnectionError, RPCTimeoutError):
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                logger.warning(f"重试 {attempt + 1}/{max_retries}，等待 {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                raise
```

## 分布式链路追踪

### 自动追踪

```python
from aury.boot.common.logging import get_trace_id, logger

# RPC 调用会自动添加 X-Trace-ID 请求头
@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    trace_id = get_trace_id()
    logger.info(f"获取订单，Trace-ID: {trace_id}")
    
    # 调用其他服务，自动传递 Trace-ID
    order_client = create_rpc_client("order-service")
    response = await order_client.get(f"/api/v1/orders/{order_id}")
    
    # 下游服务的日志会包含相同的 Trace-ID
    return response
```

### 手动设置 Trace-ID

```python
from aury.boot.common.logging import set_trace_id, get_trace_id

async def process_task(task_id: str, custom_trace_id: str = None):
    """异步任务中使用自定义 Trace-ID"""
    
    # 设置 Trace-ID（可选，通常自动生成）
    if custom_trace_id:
        set_trace_id(custom_trace_id)
    
    trace_id = get_trace_id()
    logger.info(f"处理任务 {task_id}，Trace-ID: {trace_id}")
    
    # 调用服务
    client = create_rpc_client("service-name")
    await client.post("/api/v1/process", json={"task_id": task_id})
```

## 常见场景

### 获取用户信息

```python
async def get_user_with_details(user_id: str):
    """从用户服务获取用户详细信息"""
    
    user_client = create_rpc_client("user-service")
    
    response = await user_client.get(f"/api/v1/users/{user_id}")
    
    if response.code != 200:
        raise NotFoundError(f"用户 {user_id} 不存在")
    
    return response.data
```

### 验证权限

```python
async def verify_permission(user_id: str, resource: str, action: str):
    """调用权限服务验证用户权限"""
    
    auth_client = create_rpc_client("auth-service")
    
    response = await auth_client.post(
        "/api/v1/permissions/verify",
        json={
            "user_id": user_id,
            "resource": resource,
            "action": action
        }
    )
    
    if response.code != 200:
        raise ForbiddenError("没有权限访问该资源")
    
    return response.data
```

### 创建相关资源

```python
async def create_order_with_notification(order_data: dict):
    """创建订单并发送通知"""
    
    order_client = create_rpc_client("order-service")
    notify_client = create_rpc_client("notification-service")
    
    # 1. 创建订单
    order_response = await order_client.post(
        "/api/v1/orders",
        json=order_data
    )
    
    if order_response.code != 200:
        raise Exception("创建订单失败")
    
    order = order_response.data
    
    # 2. 发送通知
    await notify_client.post(
        "/api/v1/notifications/send",
        json={
            "type": "order_created",
            "order_id": order["id"],
            "user_id": order["user_id"]
        }
    )
    
    return order
```

### 聚合多个服务

```python
async def get_user_profile(user_id: str):
    """聚合多个服务数据构建用户档案"""
    
    user_client = create_rpc_client("user-service")
    order_client = create_rpc_client("order-service")
    wallet_client = create_rpc_client("wallet-service")
    
    # 并发调用多个服务
    import asyncio
    
    user_resp, orders_resp, wallet_resp = await asyncio.gather(
        user_client.get(f"/api/v1/users/{user_id}"),
        order_client.get(f"/api/v1/users/{user_id}/orders"),
        wallet_client.get(f"/api/v1/users/{user_id}/wallet"),
        return_exceptions=True
    )
    
    profile = {
        "user": user_resp.data if not isinstance(user_resp, Exception) else None,
        "orders": orders_resp.data if not isinstance(orders_resp, Exception) else [],
        "wallet": wallet_resp.data if not isinstance(wallet_resp, Exception) else None,
    }
    
    return profile
```

## 服务发现

### 显式映射

```bash
# .env 中配置
RPC_CLIENT_SERVICES={"order-service": "http://192.168.1.10:8000", "user-service": "http://192.168.1.11:8001"}
```

### DNS 自动解析

```bash
# 在 Kubernetes 中自动使用 DNS 解析
# 服务名会解析到对应的集群 IP
RPC_CLIENT_SERVICES={}  # 空配置
```

使用时直接使用服务名：

```python
# Kubernetes 中自动解析
client = create_rpc_client("order-service")
# 会解析到 order-service.default.svc.cluster.local
```

## 负载均衡

### 轮询（Round Robin）

```python
# Kit 默认支持
client = create_rpc_client("order-service")
# 如果配置了多个地址，会自动轮询
```

## 监控和调试

### 请求日志

```python
from aury.boot.common.logging import logger

async def logged_rpc_call():
    logger.info("发起 RPC 调用: order-service")
    
    client = create_rpc_client("order-service")
    response = await client.get("/api/v1/orders/123")
    
    logger.info(f"RPC 调用完成，状态码: {response.code}")
```

### 性能监控

```python
import time
from aury.boot.common.logging import logger

async def monitored_rpc_call():
    start_time = time.time()
    
    try:
        client = create_rpc_client("order-service")
        response = await client.get("/api/v1/orders/123")
    finally:
        duration = time.time() - start_time
        logger.info(f"RPC 调用耗时: {duration:.3f}s")
```

## 最佳实践

### 1. 使用超时保护

```python
# ✅ 设置合理的超时
client = create_rpc_client("order-service", timeout=30)
```

### 2. 实现断路器

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_order_service():
    client = create_rpc_client("order-service")
    return await client.get("/api/v1/orders")
```

### 3. 缓存结果

```python
from aury.boot.infrastructure.cache import CacheManager

cache = CacheManager.get_instance()

@cache.cached(expire=300)
async def get_order_cached(order_id: str):
    client = create_rpc_client("order-service")
    response = await client.get(f"/api/v1/orders/{order_id}")
    return response.data
```

### 4. 优雅降级

```python
async def get_order_with_fallback(order_id: str):
    try:
        client = create_rpc_client("order-service")
        response = await client.get(f"/api/v1/orders/{order_id}", timeout=5)
        return response.data
    except Exception as e:
        logger.error(f"调用 order-service 失败: {e}")
        
        # 返回缓存数据或降级方案
        cached_order = await cache.get(f"order:{order_id}")
        if cached_order:
            logger.info("使用缓存数据")
            return cached_order
        
        # 或返回默认值
        return {"id": order_id, "status": "unknown"}
```

---

**总结**：RPC 是微服务间通信的关键。合理使用错误处理、重试机制、链路追踪，可以构建可靠的分布式系统。

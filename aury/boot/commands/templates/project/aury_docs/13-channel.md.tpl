# 流式通道（Channel）

用于 SSE（Server-Sent Events）和实时通信。支持 memory 和 redis 后端。

## 13.1 基本用法

```python
from aury.boot.infrastructure.channel import ChannelManager

# 获取实例
channel = ChannelManager.get_instance()

# 初始化（Memory 后端 - 单进程）
await channel.initialize(backend="memory")

# 初始化（Redis 后端 - 多进程/分布式）
from aury.boot.infrastructure.clients.redis import RedisClient
redis_client = RedisClient.get_instance()
await redis_client.initialize(url="redis://localhost:6379/0")
await channel.initialize(backend="redis", redis_client=redis_client)
```

## 13.2 发布消息

```python
# 发布消息到频道
await channel.publish("user:123", {{"event": "message", "data": "hello"}})

# 发布到多个用户
for user_id in user_ids:
    await channel.publish(f"user:{{user_id}}", notification)
```

## 13.3 SSE 端点示例

**文件**: `{package_name}/api/sse.py`

```python
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from aury.boot.infrastructure.channel import ChannelManager

router = APIRouter(tags=["SSE"])
channel = ChannelManager.get_instance()


@router.get("/sse/{{user_id}}")
async def sse_stream(user_id: str):
    \"\"\"SSE 实时消息流。\"\"\"
    async def event_generator():
        async for message in channel.subscribe(f"user:{{user_id}}"):
            yield f"data: {{json.dumps(message)}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={{"Cache-Control": "no-cache", "Connection": "keep-alive"}}
    )


@router.post("/notify/{{user_id}}")
async def send_notification(user_id: str, message: str):
    \"\"\"发送通知。\"\"\"
    await channel.publish(f"user:{{user_id}}", {{"message": message}})
    return {{"status": "sent"}}
```

## 13.4 多实例

```python
# 不同用途的通道实例
notifications = ChannelManager.get_instance("notifications")
chat = ChannelManager.get_instance("chat")

# 分别初始化
await notifications.initialize(backend="redis", redis_client=redis_client)
await chat.initialize(backend="redis", redis_client=redis_client)
```

## 13.5 环境变量

```bash
# 默认实例
CHANNEL_BACKEND=memory

# 多实例（格式：CHANNEL_{{INSTANCE}}_{{FIELD}}）
CHANNEL_DEFAULT_BACKEND=redis
CHANNEL_DEFAULT_URL=redis://localhost:6379/3
CHANNEL_NOTIFICATIONS_BACKEND=redis
CHANNEL_NOTIFICATIONS_URL=redis://localhost:6379/4
```

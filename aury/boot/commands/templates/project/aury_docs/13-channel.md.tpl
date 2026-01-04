# 流式通道（Channel）

用于 SSE（Server-Sent Events）和实时通信。支持 memory 和 redis 后端。

## 核心概念

- **ChannelManager**：管理器，支持命名多实例（如 sse、notification 独立管理）
- **channel 参数**：通道名/Topic，用于区分不同的消息流（如 `user:123`、`order:456`）

## 13.1 基本用法

```python
from aury.boot.infrastructure.channel import ChannelManager

# 命名多实例（推荐）- 不同业务场景使用不同实例
sse_channel = ChannelManager.get_instance("sse")
notification_channel = ChannelManager.get_instance("notification")

# Memory 后端（单进程）
await sse_channel.initialize(backend="memory")

# Redis 后端（多进程/分布式）
from aury.boot.infrastructure.clients.redis import RedisClient
redis_client = RedisClient.get_instance()
await redis_client.initialize(url="redis://localhost:6379/0")
await notification_channel.initialize(backend="redis", redis_client=redis_client)
```

## 13.2 发布和订阅（Topic 管理）

```python
# 发布消息到指定 Topic
await sse_channel.publish("user:123", {{"event": "message", "data": "hello"}})
await sse_channel.publish("order:456", {{"status": "shipped"}})

# 发布到多个用户
for user_id in user_ids:
    await sse_channel.publish(f"user:{{user_id}}", notification)
```

## 13.3 SSE 端点示例

**文件**: `{package_name}/api/sse.py`

```python
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from aury.boot.infrastructure.channel import ChannelManager

router = APIRouter(tags=["SSE"])

# 获取命名实例（在 app 启动时已初始化）
sse_channel = ChannelManager.get_instance("sse")


@router.get("/sse/{{user_id}}")
async def sse_stream(user_id: str):
    \"\"\"SSE 实时消息流。\"\"\"
    async def event_generator():
        # user_id 作为 Topic，区分不同用户的消息流
        async for message in sse_channel.subscribe(f"user:{{user_id}}"):
            yield f"data: {{json.dumps(message)}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={{"Cache-Control": "no-cache", "Connection": "keep-alive"}}
    )


@router.post("/notify/{{user_id}}")
async def send_notification(user_id: str, message: str):
    \"\"\"\u53d1\u9001\u901a\u77e5\u3002\"\"\"
    await sse_channel.publish(f"user:{{user_id}}", {{"message": message}})
    return {{"status": "sent"}}
```

## 13.4 应用场景示例

```python
# 不同业务场景使用不同的命名实例
sse_channel = ChannelManager.get_instance("sse")           # 前端 SSE 推送
chat_channel = ChannelManager.get_instance("chat")         # 聊天消息
notify_channel = ChannelManager.get_instance("notify")     # 系统通知

# 分别初始化（可使用不同后端）
await sse_channel.initialize(backend="memory")  # 单进程即可
await chat_channel.initialize(backend="redis", redis_client=redis_client)  # 需要跨进程
await notify_channel.initialize(backend="redis", redis_client=redis_client)
```

## 13.5 环境变量

```bash
# 默认实例
CHANNEL__BACKEND=memory

# 多实例（格式：CHANNEL__{{INSTANCE}}__{{FIELD}}）
CHANNEL__DEFAULT__BACKEND=redis
CHANNEL__DEFAULT__URL=redis://localhost:6379/3
CHANNEL__NOTIFICATIONS__BACKEND=redis
CHANNEL__NOTIFICATIONS__URL=redis://localhost:6379/4
```

# 17. WebSocket 长连接完全指南

请参考 [00-quick-start.md](./00-quick-start.md) 第 17 章的基础用法。

## 基本连接

### 简单的 WebSocket 服务器

```python
from fastapi import APIRouter, WebSocket
from aury.boot.infrastructure.database import DatabaseManager
from aury.boot.common.logging import logger

router = APIRouter()
db_manager = DatabaseManager.get_instance()

@router.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    logger.info(f"客户端加入房间: {room_id}")
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            # 保存到数据库
            async with db_manager.session() as session:
                message = Message(
                    room_id=room_id,
                    content=data,
                    created_at=datetime.now()
                )
                session.add(message)
                await session.commit()
            
            # 发送确认
            await websocket.send_json({
                "status": "ok",
                "message_id": message.id
            })
    
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        await websocket.close(code=1011, reason=str(e))
```

## 连接管理

### 多客户端广播

```python
class ConnectionManager:
    """管理所有 WebSocket 连接"""
    
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info(f"客户端已连接到房间 {room_id}")
    
    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
        logger.info(f"客户端已离开房间 {room_id}")
    
    async def broadcast(self, room_id: str, message: dict):
        """广播消息给房间内所有客户端"""
        if room_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"发送消息失败: {e}")
                    disconnected.append(connection)
            
            # 清理断开的连接
            for conn in disconnected:
                self.active_connections[room_id].remove(conn)

manager = ConnectionManager()

@router.websocket("/ws/chat/{room_id}")
async def chat_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # 广播给房间内所有客户端
            await manager.broadcast(room_id, {
                "type": "message",
                "content": data,
                "timestamp": datetime.now().isoformat()
            })
    
    except Exception:
        manager.disconnect(room_id, websocket)
```

## 消息类型

### 结构化消息

```python
from pydantic import BaseModel

class ChatMessage(BaseModel):
    type: str  # "text", "image", "notification"
    content: str
    sender_id: str
    timestamp: datetime

@router.websocket("/ws/advanced/{room_id}")
async def advanced_ws(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # 解析消息
            message = ChatMessage(**data)
            
            # 根据类型处理
            if message.type == "text":
                await handle_text_message(message)
            elif message.type == "image":
                await handle_image_message(message)
            elif message.type == "notification":
                await handle_notification(message)
    
    except Exception as e:
        logger.error(f"处理消息错误: {e}")
        await websocket.close(code=1011)
```

## 实时通知

### 订单状态更新

```python
# 维护用户 ID 到 WebSocket 的映射
user_connections: dict[str, WebSocket] = {}

@router.websocket("/ws/notifications/{user_id}")
async def notifications_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    
    user_connections[user_id] = websocket
    logger.info(f"用户 {user_id} 已连接通知")
    
    try:
        # 保持连接
        while True:
            data = await websocket.receive_text()
            # 可以处理来自客户端的心跳或其他消息
    
    except Exception:
        del user_connections[user_id]
        logger.info(f"用户 {user_id} 已断开通知连接")

# 在其他地方发送通知
async def notify_user(user_id: str, message: dict):
    if user_id in user_connections:
        try:
            await user_connections[user_id].send_json(message)
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            del user_connections[user_id]
```

### 订单状态推送

```python
async def push_order_status(order_id: str, status: str):
    """当订单状态改变时推送给用户"""
    
    order = await db.get_order(order_id)
    if not order:
        return
    
    await notify_user(order.user_id, {
        "type": "order_status_changed",
        "order_id": order_id,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })
```

## 心跳和连接保活

### 客户端心跳

```python
import asyncio

@router.websocket("/ws/with_heartbeat/{room_id}")
async def ws_with_heartbeat(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    async def send_heartbeat():
        """每 30 秒发送一次心跳"""
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "heartbeat"})
        except Exception:
            pass
    
    # 启动心跳任务
    heartbeat_task = asyncio.create_task(send_heartbeat())
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # 处理心跳响应
            if data.get("type") == "pong":
                logger.debug("收到心跳响应")
            else:
                # 处理其他消息
                pass
    
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
    
    finally:
        heartbeat_task.cancel()
```

## 错误处理

### 连接错误

```python
from starlette.websockets import WebSocketState

@router.websocket("/ws/resilient/{room_id}")
async def resilient_ws(websocket: WebSocket, room_id: str):
    try:
        await websocket.accept()
    except Exception as e:
        logger.error(f"接受连接失败: {e}")
        return
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                # 处理消息
            except Exception as e:
                logger.error(f"接收消息错误: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
    
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
```

### 重连机制

```python
# 客户端（JavaScript/TypeScript）应该实现重连
# 当连接断开时，自动重连

# 服务端只需要接受新连接
@router.websocket("/ws/reconnect/{session_id}")
async def ws_with_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    # 可以恢复之前的会话
    session = await db.get_session(session_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            # 处理消息
    except Exception:
        # 关闭连接
        pass
```

## 数据库操作

### 事务处理

```python
@router.websocket("/ws/db/{user_id}")
async def ws_with_db(websocket: WebSocket, user_id: str):
    await websocket.accept()
    db_manager = DatabaseManager.get_instance()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # 使用数据库会话
            async with db_manager.session() as session:
                # 保存消息
                message = Message(
                    user_id=user_id,
                    content=data.get("content"),
                    created_at=datetime.now()
                )
                session.add(message)
                await session.commit()
                
                # 发送确认
                await websocket.send_json({
                    "status": "saved",
                    "message_id": message.id
                })
    
    except Exception as e:
        logger.error(f"数据库错误: {e}")
        await websocket.close(code=1011)
```

## 常见场景

### 实时聊天

```python
manager = ConnectionManager()

@router.websocket("/ws/chat/rooms/{room_id}")
async def chat_room(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    
    try:
        while True:
            message_data = await websocket.receive_json()
            
            message = {
                "type": "chat",
                "room_id": room_id,
                "content": message_data.get("content"),
                "sender": message_data.get("sender"),
                "timestamp": datetime.now().isoformat()
            }
            
            # 广播给房间内所有客户端
            await manager.broadcast(room_id, message)
    
    except Exception:
        manager.disconnect(room_id, websocket)
```

### 实时数据推送

```python
# 数据更新时推送给客户端
@app.on_event("startup")
async def setup_data_pusher():
    """应用启动时设置数据推送任务"""
    
    async def push_data_updates():
        while True:
            try:
                updates = await get_data_updates()
                
                # 推送给所有连接的客户端
                for user_id, ws in user_connections.items():
                    try:
                        await ws.send_json(updates)
                    except Exception:
                        del user_connections[user_id]
                
                await asyncio.sleep(5)  # 每 5 秒推送一次
            
            except Exception as e:
                logger.error(f"推送数据失败: {e}")
    
    asyncio.create_task(push_data_updates())
```

## 性能优化

### 消息批处理

```python
class BatchedConnectionManager:
    def __init__(self, batch_size=10, flush_interval=1):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.message_queue = {}
    
    async def queue_message(self, room_id: str, message: dict):
        if room_id not in self.message_queue:
            self.message_queue[room_id] = []
        
        self.message_queue[room_id].append(message)
        
        # 批量发送
        if len(self.message_queue[room_id]) >= self.batch_size:
            await self.flush(room_id)
    
    async def flush(self, room_id: str):
        if room_id in self.message_queue and self.message_queue[room_id]:
            messages = self.message_queue[room_id]
            # 批量发送
            await manager.broadcast(room_id, {
                "type": "batch",
                "messages": messages
            })
            self.message_queue[room_id] = []
```

---

**总结**：WebSocket 适合实时通信场景，如聊天、通知、数据推送。合理管理连接和处理错误，可以构建稳定的实时系统。

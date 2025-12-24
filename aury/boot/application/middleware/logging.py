"""HTTP 请求日志中间件。

提供 HTTP 相关的日志功能，包括：
- 请求日志中间件（支持链路追踪）
- 请求日志装饰器
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from aury.boot.application.errors import global_exception_handler
from aury.boot.common.logging import logger, set_trace_id


def log_request[T](func: Callable[..., T]) -> Callable[..., T]:
    """请求日志装饰器。
    
    记录请求的详细信息。
    
    使用示例:
        @router.get("/users")
        @log_request
        async def get_users(request: Request):
            return {"users": []}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        request: Request | None = None
        
        # 查找Request对象
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            request = kwargs.get("request")
        
        # 记录请求信息
        if request:
            logger.info(
                f"请求: {request.method} {request.url.path} | "
                f"客户端: {request.client.host if request.client else 'unknown'} | "
                f"查询参数: {dict(request.query_params)}"
            )
        
        try:
            # 执行函数
            start_time = time.time()
            response = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 记录响应信息
            if request:
                logger.info(
                    f"响应: {request.method} {request.url.path} | "
                    f"耗时: {duration:.3f}s"
                )
            
            return response
        except Exception as exc:
            # 记录错误
            if request:
                logger.error(
                    f"错误: {request.method} {request.url.path} | "
                    f"异常: {type(exc).__name__}: {exc}"
                )
            raise
    
    return wrapper


# 请求/响应体最大记录长度
MAX_BODY_LOG_SIZE = 2000
# 不记录 body 的 Content-Type
SKIP_BODY_CONTENT_TYPES = (
    "multipart/form-data",
    "application/octet-stream",
    "image/",
    "audio/",
    "video/",
)


def _truncate_body(body: bytes | None, max_size: int = MAX_BODY_LOG_SIZE) -> str | None:
    """截取请求/响应体用于日志记录。"""
    if not body:
        return None
    try:
        text = body.decode("utf-8")
        if len(text) > max_size:
            return text[:max_size] + f"...(截取，总长{len(text)})"
        return text
    except UnicodeDecodeError:
        return f"<二进制数据 {len(body)} bytes>"


def _should_log_body(content_type: str | None) -> bool:
    """判断是否应该记录 body。"""
    if not content_type:
        return True
    content_type = content_type.lower()
    return all(skip_type not in content_type for skip_type in SKIP_BODY_CONTENT_TYPES)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件（支持链路追踪）。
    
    自动记录所有HTTP请求的详细信息，包括：
    - 请求方法、路径、查询参数、请求体
    - 客户端IP、User-Agent
    - 响应状态码、耗时、响应体
    - 链路追踪 ID（X-Trace-ID / X-Request-ID）
    
    注意：文件上传、二进制数据等不会记录 body 内容。
    
    使用示例:
        from aury.boot.application.middleware.logging import RequestLoggingMiddleware
        
        app.add_middleware(RequestLoggingMiddleware)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求并记录日志。"""
        start_time = time.time()
        
        # 从请求头获取或生成链路追踪 ID
        trace_id = (
            request.headers.get("x-trace-id") or
            request.headers.get("x-request-id") or
            str(uuid.uuid4())
        )
        set_trace_id(trace_id)
        
        # 获取客户端信息
        client_host = request.client.host if request.client else "unknown"
        content_type = request.headers.get("content-type", "")
        
        # 读取请求体
        request_body: bytes | None = None
        request_body_log: str | None = None
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                request_body = await request.body()
                if _should_log_body(content_type):
                    request_body_log = _truncate_body(request_body)
                else:
                    request_body_log = f"<{content_type}, {len(request_body)} bytes>"
            except Exception:
                pass
        
        # 构建请求日志
        request_log = f"→ {request.method} {request.url.path}"
        if request.query_params:
            request_log += f" | 参数: {dict(request.query_params)}"
        if request_body_log:
            request_log += f" | Body: {request_body_log}"
        request_log += f" | 客户端: {client_host} | Trace-ID: {trace_id}"
        
        logger.info(request_log)
        
        # 执行请求
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # 在响应头中添加追踪 ID
            response.headers["x-trace-id"] = trace_id
            
            # 记录响应信息
            status_code = response.status_code
            log_level = "error" if status_code >= 500 else "warning" if status_code >= 400 else "info"
            
            response_log = (
                f"← {request.method} {request.url.path} | "
                f"状态: {status_code} | "
                f"耗时: {duration:.3f}s | "
                f"Trace-ID: {trace_id}"
            )
            logger.log(log_level.upper(), response_log)
            
            # 写入 access 日志（简洁格式）
            logger.bind(access=True).info(
                f"{request.method} {request.url.path} {status_code} {duration:.3f}s"
            )
            
            # 慢请求警告
            if duration > 1.0:
                logger.warning(
                    f"慢请求: {request.method} {request.url.path} | "
                    f"耗时: {duration:.3f}s (超过1秒) | "
                    f"Trace-ID: {trace_id}"
                )
            
            return response
            
        except Exception as exc:
            duration = time.time() - start_time
            # diagnose=True 会自动记录局部变量（request_body_log, client_host, trace_id 等）
            logger.exception(
                f"请求处理失败: {request.method} {request.url.path} | "
                f"耗时: {duration:.3f}s | Trace-ID: {trace_id}"
            )
            # 使用全局异常处理器生成响应，而不是直接抛出异常
            # BaseHTTPMiddleware 中直接 raise 会绕过 FastAPI 的异常处理器
            response = await global_exception_handler(request, exc)
            response.headers["x-trace-id"] = trace_id
            return response


class WebSocketLoggingMiddleware:
    """WebSocket 日志中间件。
    
    记录 WebSocket 连接生命周期和消息收发（可选）。
    
    使用示例:
        from aury.boot.application.middleware.logging import WebSocketLoggingMiddleware
        
        app.add_middleware(WebSocketLoggingMiddleware, log_messages=True)
    """
    
    def __init__(
        self,
        app,
        *,
        log_messages: bool = False,
        max_message_length: int = 500,
    ) -> None:
        """初始化 WebSocket 日志中间件。
        
        Args:
            app: ASGI 应用
            log_messages: 是否记录消息内容（默认 False，注意性能和敏感数据）
            max_message_length: 消息内容最大记录长度
        """
        self.app = app
        self.log_messages = log_messages
        self.max_message_length = max_message_length
    
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return
        
        # 获取或生成 trace_id
        headers = dict(scope.get("headers", []))
        trace_id = (
            headers.get(b"x-trace-id", b"").decode() or
            headers.get(b"x-request-id", b"").decode() or
            str(uuid.uuid4())
        )
        set_trace_id(trace_id)
        
        path = scope.get("path", "/")
        client = scope.get("client")
        client_host = f"{client[0]}:{client[1]}" if client else "unknown"
        
        start_time = time.time()
        message_count = {"sent": 0, "received": 0}
        
        async def logging_receive():
            message = await receive()
            msg_type = message.get("type", "")
            
            if msg_type == "websocket.connect":
                logger.info(
                    f"WS → 连接建立: {path} | "
                    f"客户端: {client_host} | Trace-ID: {trace_id}"
                )
            elif msg_type == "websocket.disconnect":
                duration = time.time() - start_time
                logger.info(
                    f"WS ← 连接关闭: {path} | "
                    f"时长: {duration:.1f}s | "
                    f"收/发: {message_count['received']}/{message_count['sent']} | "
                    f"Trace-ID: {trace_id}"
                )
            elif msg_type == "websocket.receive":
                message_count["received"] += 1
                if self.log_messages:
                    text = message.get("text") or message.get("bytes", b"").decode("utf-8", errors="replace")
                    if len(text) > self.max_message_length:
                        text = text[:self.max_message_length] + "..."
                    logger.debug(f"WS → 收到: {path} | {text}")
            
            return message
        
        async def logging_send(message):
            msg_type = message.get("type", "")
            
            if msg_type == "websocket.send":
                message_count["sent"] += 1
                if self.log_messages:
                    text = message.get("text") or message.get("bytes", b"").decode("utf-8", errors="replace")
                    if len(text) > self.max_message_length:
                        text = text[:self.max_message_length] + "..."
                    logger.debug(f"WS ← 发送: {path} | {text}")
            elif msg_type == "websocket.close":
                code = message.get("code", 1000)
                reason = message.get("reason", "")
                duration = time.time() - start_time
                log_level = "warning" if code != 1000 else "info"
                logger.log(
                    log_level.upper(),
                    f"WS ← 服务关闭: {path} | "
                    f"Code: {code} | 原因: {reason or '正常'} | "
                    f"时长: {duration:.1f}s | Trace-ID: {trace_id}"
                )
            
            await send(message)
        
        try:
            await self.app(scope, logging_receive, logging_send)
        except Exception as exc:
            duration = time.time() - start_time
            logger.exception(
                f"WS ✖ 异常: {path} | "
                f"时长: {duration:.1f}s | "
                f"收/发: {message_count['received']}/{message_count['sent']} | "
                f"Trace-ID: {trace_id}"
            )
            raise


__all__ = [
    "RequestLoggingMiddleware",
    "WebSocketLoggingMiddleware",
    "log_request",
]



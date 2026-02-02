"""HTTP客户端 - 企业级HTTP请求工具。

特性：
- 连接池管理
- 自动重试机制（使用tenacity）
- 请求/响应拦截器
- 超时控制
- 错误处理
- 请求日志

基于 aiohttp 实现，全异步无阻塞。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar

import aiohttp
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from aury.boot.common.logging import logger

T = TypeVar("T")


class RetryConfig(BaseModel):
    """重试配置（Pydantic）。"""
    
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    retry_on_status: list[int] = [500, 502, 503, 504]


class HttpClientConfig(BaseModel):
    """HTTP客户端配置（Pydantic）。"""
    
    base_url: str = ""
    timeout: float = 30.0
    follow_redirects: bool = True
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    retry: RetryConfig | None = None


@dataclass
class HttpRequest:
    """请求对象（用于拦截器）。"""
    
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_data: Any = None
    data: Any = None


@dataclass
class HttpResponse:
    """响应对象（用于拦截器和返回）。"""
    
    status_code: int
    url: str
    headers: dict[str, str]
    text: str
    content: bytes
    elapsed_seconds: float
    
    def json(self) -> Any:
        """解析 JSON 响应。"""
        import json
        return json.loads(self.text)
    
    @property
    def is_success(self) -> bool:
        """是否成功响应。"""
        return 200 <= self.status_code < 400
    
    def raise_for_status(self) -> None:
        """如果状态码表示错误，抛出异常。"""
        if self.status_code >= 400:
            raise HttpStatusError(
                f"HTTP {self.status_code}",
                status_code=self.status_code,
                response=self,
            )


class HttpError(Exception):
    """HTTP 错误基类。"""
    pass


class HttpStatusError(HttpError):
    """HTTP 状态码错误。"""
    
    def __init__(self, message: str, status_code: int, response: HttpResponse) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class HttpTimeoutError(HttpError):
    """HTTP 超时错误。"""
    pass


class HttpNetworkError(HttpError):
    """HTTP 网络错误。"""
    pass


class RequestInterceptor(ABC):
    """请求拦截器接口。"""
    
    @abstractmethod
    async def before_request(self, request: HttpRequest) -> HttpRequest:
        """请求前处理。"""
        pass
    
    @abstractmethod
    async def after_response(self, response: HttpResponse) -> HttpResponse:
        """响应后处理。"""
        pass


class LoggingInterceptor(RequestInterceptor):
    """日志拦截器。"""
    
    async def before_request(self, request: HttpRequest) -> HttpRequest:
        """记录请求日志。"""
        logger.debug(
            f"HTTP请求: {request.method} {request.url} | "
            f"Headers: {request.headers}"
        )
        return request
    
    async def after_response(self, response: HttpResponse) -> HttpResponse:
        """记录响应日志。"""
        logger.debug(
            f"HTTP响应: {response.status_code} {response.url} | "
            f"耗时: {response.elapsed_seconds:.3f}s"
        )
        return response


class HttpClient:
    """企业级HTTP客户端（基于 aiohttp）。
    
    特性：
    - 连接池管理
    - 自动重试（使用tenacity）
    - 拦截器支持
    - 超时控制
    - 错误处理
    - 全异步无阻塞
    
    使用示例:
        # 基础使用
        client = HttpClient(base_url="https://api.example.com")
        response = await client.get("/users")
        
        # 带重试
        config = HttpClientConfig(
            base_url="https://api.example.com",
            retry=RetryConfig(max_retries=3)
        )
        client = HttpClient.from_config(config)
        response = await client.get("/users")
        
        # 添加拦截器
        client.add_interceptor(LoggingInterceptor())
    """
    
    def __init__(
        self,
        base_url: str = "",
        *,
        timeout: float = 30.0,
        follow_redirects: bool = True,
        max_connections: int = 100,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """初始化HTTP客户端。
        
        Args:
            base_url: 基础URL
            timeout: 超时时间（秒）
            follow_redirects: 是否跟随重定向（aiohttp 默认不跟随）
            max_connections: 最大连接数
            retry_config: 重试配置
        """
        self._base_url = base_url.rstrip("/") if base_url else ""
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._follow_redirects = follow_redirects
        self._max_connections = max_connections
        self._retry_config = retry_config or RetryConfig()
        self._interceptors: list[RequestInterceptor] = []
        
        # 创建连接器（连接池）
        self._connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections // 4,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )
        
        # aiohttp 会话（延迟创建）
        self._session: aiohttp.ClientSession | None = None
        
        logger.debug(f"HTTP客户端初始化: base_url={base_url}, timeout={timeout}")
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """确保会话已创建。"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=self._timeout,
            )
        return self._session
    
    @classmethod
    def from_config(cls, config: HttpClientConfig) -> HttpClient:
        """从配置创建客户端。
        
        Args:
            config: 客户端配置
            
        Returns:
            HttpClient: HTTP客户端实例
        """
        return cls(
            base_url=config.base_url,
            timeout=config.timeout,
            follow_redirects=config.follow_redirects,
            max_connections=config.max_connections,
            retry_config=config.retry,
        )
    
    def add_interceptor(self, interceptor: RequestInterceptor) -> None:
        """添加拦截器。
        
        Args:
            interceptor: 拦截器实例
        """
        self._interceptors.append(interceptor)
        logger.debug(f"添加拦截器: {interceptor.__class__.__name__}")
    
    async def _apply_interceptors(
        self,
        request: HttpRequest,
        response: HttpResponse | None = None,
    ) -> tuple[HttpRequest, HttpResponse | None]:
        """应用拦截器。"""
        # 请求前拦截
        for interceptor in self._interceptors:
            request = await interceptor.before_request(request)
        
        # 响应后拦截
        if response:
            for interceptor in self._interceptors:
                response = await interceptor.after_response(response)
        
        return request, response
    
    def _get_retry_decorator(self):
        """动态构建重试装饰器。"""
        return retry(
            stop=stop_after_attempt(self._retry_config.max_retries + 1),
            wait=wait_exponential(
                multiplier=self._retry_config.retry_delay,
                min=self._retry_config.retry_delay,
                max=self._retry_config.retry_delay * (self._retry_config.backoff_factor ** self._retry_config.max_retries),
            ),
            retry=retry_if_exception_type((HttpStatusError, aiohttp.ClientError)),
            reraise=True,
        )
    
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        **kwargs: Any,
    ) -> HttpResponse:
        """发送HTTP请求。
        
        Args:
            method: HTTP方法
            url: 请求URL
            headers: 请求头
            params: 查询参数
            json: JSON数据
            data: 表单数据
            **kwargs: 其他 aiohttp 参数
            
        Returns:
            HttpResponse: 响应对象
            
        Raises:
            HttpError: 请求失败
        """
        # 构建完整URL
        full_url = f"{self._base_url}{url}" if self._base_url else url
        
        # 创建请求对象
        request = HttpRequest(
            method=method,
            url=full_url,
            headers=headers or {},
            params=params,
            json_data=json,
            data=data,
        )
        
        # 应用拦截器（请求前）
        request, _ = await self._apply_interceptors(request)
        
        session = await self._ensure_session()
        
        async def _execute_request() -> HttpResponse:
            start_time = time.perf_counter()
            try:
                async with session.request(
                    method=request.method,
                    url=request.url,
                    headers=request.headers or None,
                    params=request.params,
                    json=request.json_data,
                    data=request.data,
                    allow_redirects=self._follow_redirects,
                    **kwargs,
                ) as resp:
                    elapsed = time.perf_counter() - start_time
                    content = await resp.read()
                    text = content.decode("utf-8", errors="replace")
                    
                    response = HttpResponse(
                        status_code=resp.status,
                        url=str(resp.url),
                        headers=dict(resp.headers),
                        text=text,
                        content=content,
                        elapsed_seconds=elapsed,
                    )
                    
                    # 检查是否需要重试
                    if resp.status in self._retry_config.retry_on_status:
                        logger.warning(f"请求失败，状态码: {resp.status}, 将重试")
                        raise HttpStatusError(
                            f"HTTP {resp.status}",
                            status_code=resp.status,
                            response=response,
                        )
                    
                    return response
                    
            except aiohttp.ClientError as exc:
                elapsed = time.perf_counter() - start_time
                if isinstance(exc, aiohttp.ServerTimeoutError):
                    raise HttpTimeoutError(f"请求超时: {request.url}") from exc
                raise HttpNetworkError(f"网络错误: {exc}") from exc
        
        try:
            # 使用tenacity重试装饰器
            retry_decorator = self._get_retry_decorator()
            response = await retry_decorator(_execute_request)()
            
            # 应用拦截器（响应后）
            _, response = await self._apply_interceptors(request, response)
            
            # 检查状态码
            response.raise_for_status()
            
            return response
        
        except HttpError:
            raise
        except Exception as exc:
            logger.error(
                f"HTTP请求失败: {method} {full_url} | "
                f"错误: {type(exc).__name__}: {exc}"
            )
            raise HttpNetworkError(f"请求失败: {exc}") from exc
    
    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        """GET请求。"""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        """POST请求。"""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs: Any) -> HttpResponse:
        """PUT请求。"""
        return await self.request("PUT", url, **kwargs)
    
    async def patch(self, url: str, **kwargs: Any) -> HttpResponse:
        """PATCH请求。"""
        return await self.request("PATCH", url, **kwargs)
    
    async def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        """DELETE请求。"""
        return await self.request("DELETE", url, **kwargs)
    
    async def head(self, url: str, **kwargs: Any) -> HttpResponse:
        """HEAD请求。"""
        return await self.request("HEAD", url, **kwargs)
    
    async def options(self, url: str, **kwargs: Any) -> HttpResponse:
        """OPTIONS请求。"""
        return await self.request("OPTIONS", url, **kwargs)
    
    async def close(self) -> None:
        """关闭客户端。"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector and not self._connector.closed:
            await self._connector.close()
        logger.debug("HTTP客户端已关闭")
    
    async def __aenter__(self) -> HttpClient:
        """异步上下文管理器入口。"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口。"""
        await self.close()
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<HttpClient base_url={self._base_url} timeout={self._timeout.total}>"


__all__ = [
    "HttpClient",
    "HttpClientConfig",
    "HttpError",
    "HttpNetworkError",
    "HttpRequest",
    "HttpResponse",
    "HttpStatusError",
    "HttpTimeoutError",
    "LoggingInterceptor",
    "RequestInterceptor",
    "RetryConfig",
]


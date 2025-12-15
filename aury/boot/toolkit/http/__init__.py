"""HTTP客户端 - 企业级HTTP请求工具。

特性：
- 连接池管理
- 自动重试机制（使用tenacity）
- 请求/响应拦截器
- 超时控制
- 错误处理
- 请求日志
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

import httpx
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
    retry_on_exceptions: tuple = (httpx.TimeoutException, httpx.NetworkError)


class HttpClientConfig(BaseModel):
    """HTTP客户端配置（Pydantic）。"""
    
    base_url: str = ""
    timeout: float = 30.0
    follow_redirects: bool = True
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    retry: RetryConfig | None = None


class RequestInterceptor(ABC):
    """请求拦截器接口。"""
    
    @abstractmethod
    async def before_request(self, request: httpx.Request) -> httpx.Request:
        """请求前处理。"""
        pass
    
    @abstractmethod
    async def after_response(self, response: httpx.Response) -> httpx.Response:
        """响应后处理。"""
        pass


class LoggingInterceptor(RequestInterceptor):
    """日志拦截器。"""
    
    async def before_request(self, request: httpx.Request) -> httpx.Request:
        """记录请求日志。"""
        logger.debug(
            f"HTTP请求: {request.method} {request.url} | "
            f"Headers: {dict(request.headers)}"
        )
        return request
    
    async def after_response(self, response: httpx.Response) -> httpx.Response:
        """记录响应日志。"""
        logger.debug(
            f"HTTP响应: {response.status_code} {response.url} | "
            f"耗时: {response.elapsed.total_seconds():.3f}s"
        )
        return response


class HttpClient:
    """企业级HTTP客户端。
    
    特性：
    - 连接池管理
    - 自动重试（使用tenacity）
    - 拦截器支持
    - 超时控制
    - 错误处理
    
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
            follow_redirects: 是否跟随重定向
            max_connections: 最大连接数
            retry_config: 重试配置
        """
        self._base_url = base_url
        self._timeout = timeout
        self._follow_redirects = follow_redirects
        self._max_connections = max_connections
        self._retry_config = retry_config or RetryConfig()
        self._interceptors: list[RequestInterceptor] = []
        
        # 创建HTTP客户端（使用连接池）
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=20,
            keepalive_expiry=5.0,
        )
        
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            follow_redirects=follow_redirects,
            limits=limits,
        )
        
        logger.debug(f"HTTP客户端初始化: base_url={base_url}, timeout={timeout}")
    
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
        request: httpx.Request,
        response: httpx.Response | None = None,
    ) -> tuple[httpx.Request, httpx.Response | None]:
        """应用拦截器。"""
        # 请求前拦截
        for interceptor in self._interceptors:
            request = await interceptor.before_request(request)
        
        # 响应后拦截
        if response:
            for interceptor in self._interceptors:
                response = await interceptor.after_response(response)
        
        return request, response
    
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """执行HTTP请求（内部方法，使用tenacity重试）。"""
        response = await self._client.request(method, url, **kwargs)
        
        # 检查状态码是否需要重试
        if response.status_code in self._retry_config.retry_on_status:
            logger.warning(
                f"请求失败，状态码: {response.status_code}, 将重试"
            )
            raise httpx.HTTPStatusError(
                f"HTTP {response.status_code}",
                request=response.request,
                response=response,
            )
        
        return response
    
    def _get_retry_decorator(self):
        """动态构建重试装饰器。"""
        return retry(
            stop=stop_after_attempt(self._retry_config.max_retries + 1),
            wait=wait_exponential(
                multiplier=self._retry_config.retry_delay,
                min=self._retry_config.retry_delay,
                max=self._retry_config.retry_delay * (self._retry_config.backoff_factor ** self._retry_config.max_retries),
            ),
            retry=retry_if_exception_type(*self._retry_config.retry_on_exceptions),
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
        files: Any = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送HTTP请求。
        
        Args:
            method: HTTP方法
            url: 请求URL
            headers: 请求头
            params: 查询参数
            json: JSON数据
            data: 表单数据
            files: 文件
            **kwargs: 其他参数
            
        Returns:
            httpx.Response: 响应对象
            
        Raises:
            httpx.HTTPError: 请求失败
        """
        # 构建完整URL
        full_url = f"{self._base_url}{url}" if self._base_url else url
        
        # 创建请求对象
        request = self._client.build_request(
            method=method,
            url=full_url,
            headers=headers,
            params=params,
            json=json,
            data=data,
            files=files,
            **kwargs,
        )
        
        # 应用拦截器（请求前）
        request, _ = await self._apply_interceptors(request)
        
        try:
            # 使用tenacity重试装饰器
            retry_decorator = self._get_retry_decorator()
            
            @retry_decorator
            async def _execute_request():
                return await self._make_request(
                    method=request.method,
                    url=str(request.url),
                    headers=request.headers,
                    content=request.content,
                    **kwargs,
                )
            
            response = await _execute_request()
            
            # 应用拦截器（响应后）
            _, response = await self._apply_interceptors(request, response)
            
            # 检查状态码
            response.raise_for_status()
            
            return response
        
        except httpx.HTTPError as exc:
            logger.error(
                f"HTTP请求失败: {method} {full_url} | "
                f"错误: {type(exc).__name__}: {exc}"
            )
            raise
    
    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """GET请求。"""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """POST请求。"""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """PUT请求。"""
        return await self.request("PUT", url, **kwargs)
    
    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """PATCH请求。"""
        return await self.request("PATCH", url, **kwargs)
    
    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """DELETE请求。"""
        return await self.request("DELETE", url, **kwargs)
    
    async def head(self, url: str, **kwargs: Any) -> httpx.Response:
        """HEAD请求。"""
        return await self.request("HEAD", url, **kwargs)
    
    async def options(self, url: str, **kwargs: Any) -> httpx.Response:
        """OPTIONS请求。"""
        return await self.request("OPTIONS", url, **kwargs)
    
    async def close(self) -> None:
        """关闭客户端。"""
        await self._client.aclose()
        logger.debug("HTTP客户端已关闭")
    
    async def __aenter__(self) -> HttpClient:
        """异步上下文管理器入口。"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口。"""
        await self.close()
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<HttpClient base_url={self._base_url} timeout={self._timeout}>"


__all__ = [
    "HttpClient",
    "HttpClientConfig",
    "LoggingInterceptor",
    "RequestInterceptor",
    "RetryConfig",
]



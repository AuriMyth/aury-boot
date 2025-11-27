"""RPC客户端实现。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from aurimyth.foundation_kit.rpc.base import BaseRPCClient, RPCError, RPCResponse
from aurimyth.foundation_kit.utils.logging import logger


class RPCClient(BaseRPCClient):
    """RPC客户端实现。

    提供HTTP调用封装，支持自动重试和错误处理。
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        retry_times: int = 3,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """初始化RPC客户端。

        Args:
            base_url: 服务基础URL
            timeout: 超时时间（秒）
            retry_times: 重试次数
            headers: 默认请求头
        """
        super().__init__(base_url, timeout, retry_times, headers)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（懒加载）。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def close(self) -> None:
        """关闭HTTP客户端。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _call(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RPCResponse:
        """执行RPC调用。

        Args:
            method: HTTP方法（GET, POST, PUT, DELETE）
            path: API路径
            data: 请求体数据
            params: URL参数
            headers: 请求头

        Returns:
            RPCResponse: RPC响应

        Raises:
            RPCError: RPC调用失败
        """
        url = self._build_url(path)
        request_headers = self._prepare_headers(headers)

        logger.debug(f"RPC调用: {method} {url}")

        async def _make_request() -> httpx.Response:
            client = await self._get_client()
            return await client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
            )

        # 重试逻辑
        retry_decorator = AsyncRetrying(
            stop=stop_after_attempt(self.retry_times),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
            reraise=True,
        )

        try:
            response = await retry_decorator(_make_request)
            response.raise_for_status()

            # 解析响应
            result = response.json()
            rpc_response = RPCResponse(
                success=result.get("success", True),
                data=result.get("data"),
                message=result.get("message", ""),
                code=result.get("code", "0000"),
                status_code=response.status_code,
            )

            rpc_response.raise_for_status()
            return rpc_response

        except httpx.HTTPStatusError as e:
            logger.error(f"RPC调用失败: {method} {url}, status={e.response.status_code}")
            raise RPCError(
                message=f"HTTP错误: {e.response.status_code}",
                code="HTTP_ERROR",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(f"RPC请求失败: {method} {url}, error={str(e)}")
            raise RPCError(
                message=f"请求失败: {str(e)}",
                code="REQUEST_ERROR",
                status_code=0,
            ) from e
        except Exception as e:
            logger.error(f"RPC调用异常: {method} {url}, error={str(e)}")
            raise RPCError(
                message=f"未知错误: {str(e)}",
                code="UNKNOWN_ERROR",
                status_code=500,
            ) from e

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RPCResponse:
        """GET请求。

        Args:
            path: API路径
            params: URL参数
            headers: 请求头

        Returns:
            RPCResponse: RPC响应
        """
        return await self._call("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RPCResponse:
        """POST请求。

        Args:
            path: API路径
            data: 请求体数据
            headers: 请求头

        Returns:
            RPCResponse: RPC响应
        """
        return await self._call("POST", path, data=data, headers=headers)

    async def put(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> RPCResponse:
        """PUT请求。

        Args:
            path: API路径
            data: 请求体数据
            headers: 请求头

        Returns:
            RPCResponse: RPC响应
        """
        return await self._call("PUT", path, data=data, headers=headers)

    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> RPCResponse:
        """DELETE请求。

        Args:
            path: API路径
            headers: 请求头

        Returns:
            RPCResponse: RPC响应
        """
        return await self._call("DELETE", path, headers=headers)


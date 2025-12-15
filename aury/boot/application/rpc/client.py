"""RPC客户端实现。

基于 toolkit/http 的 HttpClient，提供 RPC 调用封装。
支持链路追踪（Distributed Tracing）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aury.boot.application.rpc.base import BaseRPCClient, RPCError, RPCResponse
from aury.boot.application.rpc.discovery import get_service_discovery
from aury.boot.common.logging import get_trace_id, logger
from aury.boot.toolkit.http import HttpClient

if TYPE_CHECKING:
    from aury.boot.application.config import BaseConfig


class RPCClient(BaseRPCClient):
    """RPC客户端实现（支持链路追踪）。

    基于 toolkit/http 的 HttpClient，提供 RPC 调用封装。
    支持自动重试、错误处理和链路追踪（自动传递追踪ID）。
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        retry_times: int = 3,
        headers: dict[str, str] | None = None,
    ) -> None:
        """初始化RPC客户端。

        Args:
            base_url: 服务基础URL
            timeout: 超时时间（秒）
            retry_times: 重试次数
            headers: 默认请求头
        """
        super().__init__(base_url, timeout, retry_times, headers)
        # 使用 toolkit/http 的 HttpClient
        from aury.boot.toolkit.http import RetryConfig
        
        retry_config = RetryConfig(max_retries=retry_times)
        self._http_client = HttpClient(
            base_url=base_url,
            timeout=float(timeout),
            retry_config=retry_config,
        )
        # 添加默认请求头
        if headers:
            # HttpClient 不支持直接设置默认 headers，需要在每次请求时传递
            self._default_headers = headers
        else:
            self._default_headers = {}

    async def close(self) -> None:
        """关闭HTTP客户端。"""
        await self._http_client.close()

    async def _call(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
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
        # 合并请求头
        request_headers = self._prepare_headers(headers)
        
        # 添加链路追踪 ID
        trace_id = get_trace_id()
        request_headers["x-trace-id"] = trace_id
        request_headers["x-request-id"] = trace_id
        
        logger.debug(
            f"RPC调用开始: {method} {path} | "
            f"Trace-ID: {trace_id}"
        )

        try:
            # 使用 toolkit/http 的 HttpClient
            response = await self._http_client.request(
                method=method,
                url=path,
                json=data,
                params=params,
                headers=request_headers,
            )

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
            
            logger.debug(
                f"RPC调用成功: {method} {path} | "
                f"状态: {response.status_code} | "
                f"Trace-ID: {trace_id}"
            )
            
            return rpc_response

        except Exception as e:
            # HttpClient 已经处理了 HTTP 错误，这里只需要转换为 RPCError
            status_code = getattr(e, "response", None)
            if status_code and hasattr(status_code, "status_code"):
                status_code = status_code.status_code
            else:
                status_code = 500
            
            logger.error(
                f"RPC调用失败: {method} {path} | "
                f"错误: {e!s} | "
                f"Trace-ID: {trace_id}"
            )
            raise RPCError(
                message=f"RPC调用失败: {e!s}",
                code="RPC_ERROR",
                status_code=status_code,
            ) from e

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
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
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
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
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
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
        headers: dict[str, str] | None = None,
    ) -> RPCResponse:
        """DELETE请求。

        Args:
            path: API路径
            headers: 请求头

        Returns:
            RPCResponse: RPC响应
        """
        return await self._call("DELETE", path, headers=headers)


def create_rpc_client(
    service_name: str | None = None,
    base_url: str | None = None,
    timeout: int | None = None,
    retry_times: int | None = None,
    headers: dict[str, str] | None = None,
    config: "BaseConfig | None" = None,
) -> RPCClient:
    """创建 RPC 客户端（支持服务发现）。

    优先使用服务发现解析服务地址，如果未提供 service_name 或 base_url，则使用 base_url。

    Args:
        service_name: 服务名称（用于服务发现）
        base_url: 服务基础URL（如果提供，直接使用，不进行服务发现）
        timeout: 超时时间（秒），如果为 None 则使用配置中的默认值
        retry_times: 重试次数，如果为 None 则使用配置中的默认值
        headers: 默认请求头
        config: 应用配置（可选），用于服务发现和获取默认配置

    Returns:
        RPCClient: RPC 客户端实例

    Raises:
        ValueError: 如果既未提供 service_name 也未提供 base_url

    示例:
        # 使用服务发现（自动从配置/DNS 解析）
        from aury.boot.application.config import BaseConfig
        
        config = BaseConfig()
        client = create_rpc_client(service_name="user-service", config=config)
        response = await client.get("/api/v1/users/1")

        # 直接指定 URL（不使用服务发现）
        client = create_rpc_client(base_url="http://user-service:8000")
        response = await client.get("/api/v1/users/1")
    """
    # 从配置中获取默认值
    if config:
        rpc_client_settings = config.rpc_client
        default_timeout = timeout if timeout is not None else rpc_client_settings.default_timeout
        default_retry_times = retry_times if retry_times is not None else rpc_client_settings.default_retry_times
    else:
        default_timeout = timeout if timeout is not None else 30
        default_retry_times = retry_times if retry_times is not None else 3
    
    if base_url:
        # 直接使用提供的 URL
        return RPCClient(
            base_url=base_url,
            timeout=default_timeout,
            retry_times=default_retry_times,
            headers=headers,
        )
    
    if service_name:
        # 使用服务发现解析
        discovery = get_service_discovery(config)
        resolved_url = discovery.resolve(service_name)
        
        if not resolved_url:
            raise ValueError(
                f"无法解析服务地址: {service_name}。"
                "请检查配置（BaseConfig.rpc_client.services）或确保 DNS 服务发现已启用。"
            )
        
        return RPCClient(
            base_url=resolved_url,
            timeout=default_timeout,
            retry_times=default_retry_times,
            headers=headers,
        )
    
    raise ValueError("必须提供 service_name 或 base_url")


"""HTTP 类第三方接口适配器。

本模块提供 HTTP REST API 类第三方接口的便捷基类，适用于大部分第三方服务
（如支付接口、短信接口、地图API、云服务API等）。

基于 toolkit.http.HttpClient 封装，核心功能：
- 自动管理 HttpClient 生命周期（连接池、重试、超时）
- 统一的请求头处理（认证、签名、trace-id）
- 请求/响应日志和链路追踪
- HTTP 错误转换为 AdapterError
- 自动根据 mode 选择 base_url（生产）或 sandbox_url（沙箱）

如果第三方提供的是 SDK 而非 HTTP API（如微信支付 SDK、阿里云 SDK），
或者使用 gRPC 等非 HTTP 协议，请直接继承 BaseAdapter。

典型第三方接口举例：
- 支付：微信支付、支付宝、Stripe 等
- 短信：阿里云短信、腾讯云短信、Twilio 等
- 云存储：七牛、又拍云、AWS S3 等
- 社交：微信开放平台、企业微信、钉钉等
- 地图：高德、百度、Google Maps 等
"""

from __future__ import annotations

from typing import Any

import httpx

from aury.boot.common.logging import get_trace_id, logger
from aury.boot.toolkit.http import HttpClient, RetryConfig

from .base import BaseAdapter
from .config import AdapterSettings
from .exceptions import AdapterError, AdapterTimeoutError


class HttpAdapter(BaseAdapter):
    """HTTP 类第三方 Adapter 基类。
    
    封装 HttpClient，提供统一的 HTTP 请求方法和错误处理。
    
    核心功能：
    - 自动根据 settings.mode 选择 base_url / sandbox_url
    - 统一的请求头处理（认证、签名、trace-id）
    - 请求/响应日志
    - 超时和重试配置
    - 错误转换为 AdapterError
    
    使用示例:
        class PaymentAdapter(HttpAdapter):
            @adapter_method("create")
            async def create_order(self, amount: int, order_id: str) -> dict:
                return await self._request(
                    "POST", "/v1/charges",
                    json={"amount": amount, "order_id": order_id}
                )
            
            @create_order.mock
            async def create_order_mock(self, amount: int, order_id: str) -> dict:
                return {"success": True, "mock": True, "charge_id": "ch_mock_123"}
            
            # 自定义请求头（如签名）
            def _prepare_headers(self, extra: dict | None = None) -> dict:
                headers = super()._prepare_headers(extra)
                headers["X-Signature"] = self._sign_request(...)
                return headers
    
    Attributes:
        _client: HttpClient 实例（mode 为 real/sandbox 时可用）
    """
    
    def __init__(
        self,
        name: str,
        settings: AdapterSettings,
        *,
        client: HttpClient | None = None,
    ) -> None:
        """初始化 HTTP Adapter。
        
        Args:
            name: Adapter 名称
            settings: 集成配置
            client: 自定义 HttpClient（可选，默认根据配置自动创建）
        """
        super().__init__(name, settings)
        self._client: HttpClient | None = client
        self._owns_client = client is None  # 是否由本类创建（需要自己清理）
    
    # ========== 生命周期 ==========
    
    async def _on_initialize(self) -> None:
        """初始化 HttpClient。"""
        if self._client is not None:
            return
        
        # 只有 real / sandbox 模式需要真实客户端
        if self.settings.mode not in ("real", "sandbox"):
            logger.debug(f"HttpAdapter {self.name} 处于 {self.settings.mode} 模式，跳过 HttpClient 初始化")
            return
        
        effective_url = self.settings.get_effective_url()
        if not effective_url:
            logger.warning(
                f"HttpAdapter {self.name} 未配置 base_url/sandbox_url，"
                f"真实调用可能失败"
            )
            return
        
        # 创建 HttpClient
        retry_config = RetryConfig(max_retries=self.settings.retry_times)
        self._client = HttpClient(
            base_url=effective_url,
            timeout=float(self.settings.timeout),
            retry_config=retry_config,
        )
        
        logger.debug(
            f"HttpAdapter {self.name} 初始化 HttpClient: "
            f"url={effective_url}, timeout={self.settings.timeout}"
        )
    
    async def _on_cleanup(self) -> None:
        """清理 HttpClient。"""
        if self._client and self._owns_client:
            await self._client.close()
            self._client = None
            logger.debug(f"HttpAdapter {self.name} 关闭 HttpClient")
    
    # ========== 请求方法 ==========
    
    def _prepare_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """准备请求头。
        
        默认包含：
        - Content-Type: application/json
        - X-Trace-Id: 链路追踪 ID
        - Authorization: Bearer {api_key}（如果配置了 api_key）
        
        子类可覆盖此方法添加自定义头（如签名）。
        
        Args:
            extra: 额外的请求头
            
        Returns:
            dict: 合并后的请求头
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Trace-Id": get_trace_id(),
        }
        
        # 认证
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        
        # 合并额外头
        if extra:
            headers.update(extra)
        
        return headers
    
    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """发送 HTTP 请求。
        
        这是 HttpGateway 的核心方法，子类的 @operation 方法通常调用此方法。
        
        Args:
            method: HTTP 方法（GET/POST/PUT/DELETE 等）
            path: 请求路径（相对于 base_url）
            headers: 额外请求头（会与默认头合并）
            params: URL 查询参数
            json: JSON 请求体
            data: 表单数据
            files: 上传文件
            **kwargs: 其他 httpx 参数
            
        Returns:
            dict: 响应 JSON
            
        Raises:
            GatewayError: 请求失败
            GatewayTimeoutError: 请求超时
        """
        if self._client is None:
            # 尝试延迟初始化
            await self.initialize()
            if self._client is None:
                raise AdapterError(
                    f"HttpClient 未初始化，请检查 {self.name} 的 base_url 配置",
                    adapter_name=self.name,
                )
        
        merged_headers = self._prepare_headers(headers)
        
        try:
            response = await self._client.request(
                method=method,
                url=path,
                headers=merged_headers,
                params=params,
                json=json,
                data=data,
                files=files,
                **kwargs,
            )
            
            # 尝试解析 JSON
            try:
                return response.json()
            except Exception:
                # 非 JSON 响应，返回包装后的结果
                return {
                    "success": response.is_success,
                    "status_code": response.status_code,
                    "content": response.text,
                }
        
        except httpx.TimeoutException as exc:
            raise AdapterTimeoutError(
                f"请求超时: {method} {path}",
                adapter_name=self.name,
                timeout_seconds=self.settings.timeout,
                cause=exc,
            ) from exc
        
        except httpx.HTTPStatusError as exc:
            # HTTP 错误状态码
            response = exc.response
            try:
                error_data = response.json()
                third_party_code = error_data.get("code") or error_data.get("error_code")
                third_party_message = error_data.get("message") or error_data.get("error")
            except Exception:
                third_party_code = None
                third_party_message = response.text
            
            raise AdapterError(
                f"HTTP 错误: {response.status_code} {method} {path}",
                adapter_name=self.name,
                third_party_code=third_party_code,
                third_party_message=third_party_message,
                cause=exc,
            ) from exc
        
        except Exception as exc:
            raise AdapterError(
                f"请求失败: {method} {path} - {type(exc).__name__}: {exc}",
                adapter_name=self.name,
                cause=exc,
            ) from exc
    
    # ========== 便捷方法 ==========
    
    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """GET 请求。"""
        return await self._request("GET", path, params=params, headers=headers, **kwargs)
    
    async def _post(
        self,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """POST 请求。"""
        return await self._request("POST", path, json=json, data=data, headers=headers, **kwargs)
    
    async def _put(
        self,
        path: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """PUT 请求。"""
        return await self._request("PUT", path, json=json, headers=headers, **kwargs)
    
    async def _patch(
        self,
        path: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """PATCH 请求。"""
        return await self._request("PATCH", path, json=json, headers=headers, **kwargs)
    
    async def _delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """DELETE 请求。"""
        return await self._request("DELETE", path, headers=headers, **kwargs)


__all__ = [
    "HttpAdapter",
]

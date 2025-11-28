"""RPC基类和异常定义。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class RPCError(Exception):
    """RPC调用异常。"""

    def __init__(
        self,
        message: str,
        code: str = "RPC_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """初始化RPC异常。

        Args:
            message: 错误消息
            code: 错误代码
            status_code: HTTP状态码
            details: 错误详情
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message} (status: {self.status_code})"


class RPCResponse(BaseModel):
    """RPC响应模型。"""

    success: bool = True
    data: Any | None = None
    message: str = ""
    code: str = "0000"
    status_code: int = 200

    def raise_for_status(self) -> None:
        """如果响应失败，抛出异常。"""
        if not self.success:
            raise RPCError(
                message=self.message,
                code=self.code,
                status_code=self.status_code,
            )


class BaseRPCClient:
    """RPC客户端基类。

    提供统一的RPC调用接口和错误处理。
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
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_times = retry_times
        self.headers = headers or {}

    def _build_url(self, path: str) -> str:
        """构建完整URL。

        Args:
            path: API路径

        Returns:
            str: 完整URL
        """
        path = path.lstrip("/")
        return f"{self.base_url}/{path}"

    def _prepare_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """准备请求头。

        Args:
            extra_headers: 额外的请求头

        Returns:
            dict[str, str]: 合并后的请求头
        """
        headers = self.headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        return headers


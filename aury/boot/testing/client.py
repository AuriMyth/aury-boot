"""测试客户端。

封装 FastAPI TestClient，提供便捷的测试接口。
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient as FastAPITestClient
from httpx import Response

from aury.boot.common.logging import logger


class TestClient:
    """测试客户端。
    
    封装 FastAPI TestClient，提供便捷的测试接口。
    
    使用示例:
        app = FastAPI()
        client = TestClient(app)
        
        # GET 请求
        response = await client.get("/users", headers={"Authorization": "Bearer token"})
        assert response.status_code == 200
        
        # POST 请求
        response = await client.post("/users", json={"name": "张三"})
        assert response.status_code == 201
        assert response.json()["name"] == "张三"
    """
    
    def __init__(
        self,
        app: FastAPI,
        base_url: str = "http://test",
        headers: dict[str, str] | None = None,
    ) -> None:
        """初始化测试客户端。
        
        Args:
            app: FastAPI 应用实例
            base_url: 基础URL（默认 "http://test"）
            headers: 默认请求头
        """
        self._client = FastAPITestClient(app, base_url=base_url)
        self._default_headers = headers or {}
        logger.debug("测试客户端已创建")
    
    def _prepare_headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """准备请求头。
        
        Args:
            headers: 额外的请求头
            
        Returns:
            dict[str, str]: 合并后的请求头
        """
        merged_headers = self._default_headers.copy()
        if headers:
            merged_headers.update(headers)
        return merged_headers
    
    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """发送 GET 请求。
        
        Args:
            url: 请求URL
            params: URL参数
            headers: 请求头
            
        Returns:
            Response: HTTP响应
        """
        logger.debug(f"GET {url}")
        return self._client.get(url, params=params, headers=self._prepare_headers(headers))
    
    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """发送 POST 请求。
        
        Args:
            url: 请求URL
            json: JSON数据
            data: 表单数据
            headers: 请求头
            
        Returns:
            Response: HTTP响应
        """
        logger.debug(f"POST {url}")
        if json:
            return self._client.post(url, json=json, headers=self._prepare_headers(headers))
        else:
            return self._client.post(url, data=data, headers=self._prepare_headers(headers))
    
    def put(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """发送 PUT 请求。
        
        Args:
            url: 请求URL
            json: JSON数据
            headers: 请求头
            
        Returns:
            Response: HTTP响应
        """
        logger.debug(f"PUT {url}")
        return self._client.put(url, json=json, headers=self._prepare_headers(headers))
    
    def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """发送 DELETE 请求。
        
        Args:
            url: 请求URL
            headers: 请求头
            
        Returns:
            Response: HTTP响应
        """
        logger.debug(f"DELETE {url}")
        return self._client.delete(url, headers=self._prepare_headers(headers))
    
    def patch(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """发送 PATCH 请求。
        
        Args:
            url: 请求URL
            json: JSON数据
            headers: 请求头
            
        Returns:
            Response: HTTP响应
        """
        logger.debug(f"PATCH {url}")
        return self._client.patch(url, json=json, headers=self._prepare_headers(headers))

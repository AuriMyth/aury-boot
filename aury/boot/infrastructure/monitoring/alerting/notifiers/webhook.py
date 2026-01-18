"""通用 Webhook 通知器。

通过 HTTP POST 发送告警到任意 Webhook 端点。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from aury.boot.common.logging import logger

from .base import AlertNotifier

if TYPE_CHECKING:
    from ..events import AlertNotification


class WebhookNotifier(AlertNotifier):
    """通用 Webhook 通知器。
    
    将告警以 JSON 格式 POST 到指定 URL。
    支持自定义请求头。
    
    环境变量配置示例：
        ALERT_NOTIFIER_MYWEBHOOK_TYPE=webhook
        ALERT_NOTIFIER_MYWEBHOOK_URL=https://my-alert-system.com/api/alert
        ALERT_NOTIFIER_MYWEBHOOK_HEADERS={"Authorization": "Bearer xxx"}
    """
    
    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> None:
        """初始化 Webhook 通知器。
        
        Args:
            url: Webhook URL
            headers: 自定义请求头
            timeout: 请求超时时间（秒）
        """
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
    
    @classmethod
    def from_config(cls, config: dict) -> "WebhookNotifier":
        """从配置创建实例。"""
        url = config.get("url")
        if not url:
            raise ValueError("Webhook 通知器配置缺少 url")
        
        # 解析 headers（可能是 JSON 字符串）
        headers = config.get("headers")
        if isinstance(headers, str):
            import json
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                headers = {}
        
        timeout = int(config.get("timeout", 10))
        
        return cls(url=url, headers=headers, timeout=timeout)
    
    def _build_payload(self, notification: "AlertNotification") -> dict[str, Any]:
        """构建请求体。"""
        return {
            "title": notification.title,
            "message": notification.message,
            "severity": notification.severity.value,
            "event_type": notification.event_type.value,
            "source": notification.source,
            "service_name": notification.service_name,
            "count": notification.count,
            "first_timestamp": notification.first_timestamp.isoformat(),
            "last_timestamp": notification.last_timestamp.isoformat(),
            "trace_ids": notification.trace_ids,
            "metadata": notification.metadata,
        }
    
    async def send(self, notification: "AlertNotification") -> bool:
        """发送 Webhook 通知。"""
        try:
            payload = self._build_payload(notification)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.url,
                    json=payload,
                    headers=self.headers,
                )
                
                if response.is_success:
                    logger.debug(f"Webhook 通知发送成功: {notification.title}")
                    return True
                else:
                    logger.error(
                        f"Webhook 通知发送失败: {response.status_code} - {response.text}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Webhook 通知发送异常: {e}")
            return False


__all__ = ["WebhookNotifier"]

"""飞书通知器。

通过飞书机器人 Webhook 发送告警通知。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any

import httpx

from aury.boot.common.logging import logger

from .base import AlertNotifier

if TYPE_CHECKING:
    from ..events import AlertNotification


class FeishuNotifier(AlertNotifier):
    """飞书机器人通知器。
    
    通过飞书自定义机器人 Webhook 发送告警。
    支持签名校验（可选）。
    
    环境变量配置示例：
        ALERT_NOTIFIER_FEISHU_TYPE=feishu
        ALERT_NOTIFIER_FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
        ALERT_NOTIFIER_FEISHU_SECRET=xxx  # 可选，签名密钥
    """
    
    def __init__(self, webhook: str, secret: str | None = None) -> None:
        """初始化飞书通知器。
        
        Args:
            webhook: 飞书机器人 Webhook URL
            secret: 签名密钥（可选）
        """
        self.webhook = webhook
        self.secret = secret
    
    @classmethod
    def from_config(cls, config: dict) -> "FeishuNotifier":
        """从配置创建实例。"""
        webhook = config.get("webhook")
        if not webhook:
            raise ValueError("飞书通知器配置缺少 webhook")
        return cls(webhook=webhook, secret=config.get("secret"))
    
    def _generate_sign(self, timestamp: int) -> str:
        """生成签名。
        
        飞书签名算法：
        sign = base64(hmac-sha256(timestamp + "\\n" + secret, secret))
        """
        if not self.secret:
            return ""
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")
    
    def _build_message(self, notification: "AlertNotification") -> dict[str, Any]:
        """构建飞书消息体。
        
        使用 JSON 2.0 卡片格式，支持完整的 markdown 语法。
        """
        # 颜色映射
        color_map = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "critical": "red",
        }
        color = color_map.get(notification.severity.value, "grey")
        
        # 构建详情列表
        details = []
        
        # 基本信息
        details.append(f"**服务**: {notification.service_name or '未知'}")
        details.append(f"**来源**: {notification.source}")
        details.append(f"**类型**: {notification.event_type.value}")
        
        # 时间信息
        details.append(f"**时间**: {notification.last_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 聚合信息
        if notification.count > 1:
            details.append(f"**触发次数**: {notification.count} 次")
        
        # Trace ID
        if notification.trace_ids:
            trace_str = ", ".join(notification.trace_ids[:3])
            if len(notification.trace_ids) > 3:
                trace_str += f" ... (共{len(notification.trace_ids)}个)"
            details.append(f"**Trace ID**: {trace_str}")
        
        # 元数据（排除 SQL 和堆栈，它们单独处理）
        sql_content: str | None = None
        stacktrace_content: str | None = None
        
        if notification.metadata:
            if "duration" in notification.metadata:
                details.append(f"**耗时**: {notification.metadata['duration']:.3f}s")
            if "endpoint" in notification.metadata:
                details.append(f"**接口**: {notification.metadata['endpoint']}")
            if "error_type" in notification.metadata:
                details.append(f"**错误类型**: {notification.metadata['error_type']}")
            if "error_message" in notification.metadata:
                details.append(f"**错误信息**: {notification.metadata['error_message']}")
            if "task_name" in notification.metadata:
                details.append(f"**任务**: {notification.metadata['task_name']}")
            # SQL 和堆栈单独处理
            if "sql" in notification.metadata:
                sql_content = notification.metadata["sql"]
            if "stacktrace" in notification.metadata:
                stacktrace_content = notification.metadata["stacktrace"]
        
        # 构建卡片元素
        elements: list[dict[str, Any]] = [
            {
                "tag": "markdown",
                "content": notification.message,
            },
            {
                "tag": "hr",
            },
            {
                "tag": "markdown",
                "content": "\n".join(details),
            },
        ]
        
        # 添加 SQL 代码块
        if sql_content:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "markdown",
                "content": f"**SQL**:\n```sql\n{sql_content}\n```",
            })
        
        # 添加堆栈代码块
        if stacktrace_content:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "markdown",
                "content": f"**堆栈**:\n```python\n{stacktrace_content}\n```",
            })
        
        # 构建 JSON 2.0 卡片消息
        card = {
            "msg_type": "interactive",
            "card": {
                "schema": "2.0",
                "config": {
                    "wide_screen_mode": True,
                },
                "header": {
                    "template": color,
                    "title": {
                        "tag": "plain_text",
                        "content": notification.title,
                    },
                },
                "body": {
                    "elements": elements,
                },
            },
        }
        
        return card
    
    async def send(self, notification: "AlertNotification") -> bool:
        """发送飞书通知。"""
        try:
            # 构建消息
            message = self._build_message(notification)
            
            # 添加签名（如果配置了）
            if self.secret:
                timestamp = int(time.time())
                message["timestamp"] = str(timestamp)
                message["sign"] = self._generate_sign(timestamp)
            
            # 发送请求
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self.webhook, json=message)
                result = response.json()
                
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    logger.debug(f"飞书通知发送成功: {notification.title}")
                    return True
                else:
                    logger.error(f"飞书通知发送失败: {result}")
                    return False
        except Exception as e:
            logger.error(f"飞书通知发送异常: {e}")
            return False


__all__ = ["FeishuNotifier"]

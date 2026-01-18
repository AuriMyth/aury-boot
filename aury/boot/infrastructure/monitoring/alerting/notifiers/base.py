"""通知器基类。

定义通知器接口，所有通知器实现都应继承此类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..events import AlertNotification


class AlertNotifier(ABC):
    """告警通知器基类。
    
    所有通知器都应继承此类并实现 send 方法。
    
    示例：
        class MyNotifier(AlertNotifier):
            def __init__(self, api_key: str):
                self.api_key = api_key
            
            @classmethod
            def from_config(cls, config: dict) -> "MyNotifier":
                return cls(api_key=config["api_key"])
            
            async def send(self, notification: AlertNotification) -> bool:
                # 发送通知
                ...
    """
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "AlertNotifier":
        """从配置字典创建通知器实例。
        
        Args:
            config: 配置字典（从环境变量解析）
        
        Returns:
            通知器实例
        """
        ...
    
    @abstractmethod
    async def send(self, notification: "AlertNotification") -> bool:
        """发送告警通知。
        
        Args:
            notification: 告警通知对象
        
        Returns:
            bool: 是否发送成功
        """
        ...


__all__ = ["AlertNotifier"]

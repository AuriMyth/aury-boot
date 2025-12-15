"""事件中间件实现。

提供事件拦截、转换、日志记录等功能。

**架构说明**：
本模块使用通用的 Any 类型而非直接导入 domain.events，保持 infrastructure 层的独立性。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aury.boot.common.logging import logger


class EventMiddleware:
    """事件中间件基类。
    
    可用于实现事件拦截、转换、日志记录等功能。
    注意：这是一个抽象接口，用于扩展事件总线的功能。
    """
    
    async def process(self, event: Any, next_handler: Callable) -> None:
        """处理事件。
        
        Args:
            event: 事件对象
            next_handler: 下一个处理器
        """
        await next_handler(event)


class EventLoggingMiddleware(EventMiddleware):
    """事件日志中间件。
    
    记录事件的详细信息，包括事件处理前后。
    """
    
    async def process(self, event: Any, next_handler: Callable) -> None:
        """记录事件日志。"""
        logger.info(f"[EventMiddleware] 处理事件: {event}")
        await next_handler(event)
        logger.info(f"[EventMiddleware] 事件处理完成: {event}")


__all__ = [
    "EventLoggingMiddleware",
    "EventMiddleware",
]


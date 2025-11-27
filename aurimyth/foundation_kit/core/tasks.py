"""异步任务管理器 - 统一的任务队列接口。

提供：
- 统一的任务队列管理
- 任务注册和执行
- 错误处理和重试
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO

from aurimyth.config import settings
from aurimyth.foundation_kit.utils.logging import logger


class TaskManager:
    """任务管理器 - 单例模式。
    
    职责：
    1. 管理任务队列broker
    2. 注册任务
    3. 任务执行和监控
    
    使用示例:
        task_manager = TaskManager.get_instance()
        await task_manager.initialize()
        
        # 注册任务
        @task_manager.task
        async def send_email(to: str, subject: str):
            # 发送邮件
            pass
        
        # 执行任务
        send_email.send("user@example.com", "Hello")
    """
    
    _instance: Optional[TaskManager] = None
    
    def __init__(self) -> None:
        """私有构造函数。"""
        if TaskManager._instance is not None:
            raise RuntimeError("TaskManager 是单例类，请使用 get_instance() 获取实例")
        
        self._broker: Optional[RedisBroker] = None
        self._initialized: bool = False
    
    @classmethod
    def get_instance(cls) -> TaskManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(
        self,
        broker_url: Optional[str] = None,
        *,
        middleware: Optional[list] = None,
    ) -> None:
        """初始化任务队列。
        
        Args:
            broker_url: Broker连接URL
            middleware: 中间件列表
        """
        if self._initialized:
            logger.warning("任务管理器已初始化，跳过")
            return
        
        url = broker_url or getattr(settings, "TASK_BROKER_URL", None) or settings.redis_url
        if not url:
            logger.warning("未配置任务队列URL，任务功能将被禁用")
            return
        
        try:
            middleware = middleware or [AsyncIO()]
            self._broker = RedisBroker(url=url, middleware=middleware)
            dramatiq.set_broker(self._broker)
            self._initialized = True
            logger.info("任务管理器初始化完成")
        except Exception as exc:
            logger.error(f"任务队列初始化失败: {exc}")
            raise
    
    def task(
        self,
        func: Optional[Callable] = None,
        *,
        actor_name: Optional[str] = None,
        max_retries: int = 3,
        time_limit: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        """任务装饰器。
        
        Args:
            func: 任务函数
            actor_name: Actor名称
            max_retries: 最大重试次数
            time_limit: 时间限制（毫秒）
            **kwargs: 其他参数
            
        使用示例:
            @task_manager.task(max_retries=3)
            async def send_email(to: str, subject: str):
                # 发送邮件
                pass
        """
        def decorator(f: Callable) -> Callable:
            actor = dramatiq.actor(
                f,
                actor_name=actor_name or f.__name__,
                max_retries=max_retries,
                time_limit=time_limit,
                **kwargs,
            )
            logger.debug(f"任务已注册: {actor_name or f.__name__}")
            return actor
        
        if func is None:
            return decorator
        return decorator(func)
    
    @property
    def broker(self) -> Optional[RedisBroker]:
        """获取broker实例。"""
        return self._broker
    
    def is_initialized(self) -> bool:
        """检查是否已初始化。"""
        return self._initialized
    
    async def cleanup(self) -> None:
        """清理资源。"""
        if self._broker:
            # Dramatiq会自动管理broker
            pass
        self._initialized = False
        logger.info("任务管理器已清理")
    
    def __repr__(self) -> str:
        """字符串表示。"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<TaskManager status={status}>"


__all__ = [
    "TaskManager",
]

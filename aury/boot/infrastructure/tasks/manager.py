"""异步任务管理器 - 统一的任务队列接口。

提供：
- 统一的任务队列管理
- 任务注册和执行
- 错误处理和重试
- 条件注册（避免 API 模式下重复注册）
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger
from aury.boot.infrastructure.tasks.config import TaskConfig
from aury.boot.infrastructure.tasks.constants import TaskQueueName, TaskRunMode

# 延迟导入 dramatiq（可选依赖）
try:
    import dramatiq
    from dramatiq import Message
    from dramatiq.middleware import AsyncIO, CurrentMessage, TimeLimit
    _DRAMATIQ_AVAILABLE = True
except ImportError:
    _DRAMATIQ_AVAILABLE = False
    # 创建占位符类型，避免类型检查错误
    if TYPE_CHECKING:
        from dramatiq import Message
        from dramatiq.middleware import AsyncIO, CurrentMessage, TimeLimit
    else:
        Message = None
        AsyncIO = None
        CurrentMessage = None
        TimeLimit = None

# 延迟导入 kombu broker（可选依赖）
try:
    from dramatiq_kombu_broker import KombuBroker
    _KOMBU_BROKER_AVAILABLE = True
except ImportError:
    _KOMBU_BROKER_AVAILABLE = False
    if TYPE_CHECKING:
        from dramatiq_kombu_broker import KombuBroker
    else:
        KombuBroker = None


class TaskProxy:
    """任务代理类，用于在 API 模式下发送消息而不注册任务。
    
    在 API 服务中，我们不希望注册任务（因为 worker 已经注册了），
    但仍然需要能够发送任务消息。TaskProxy 提供了这个功能。
    
    使用示例:
        @conditional_task(queue_name="default")
        def send_email(to: str, subject: str):
            # 在 worker 中执行任务
            # 在 API 中只发送不执行
            pass
        
        # API 模式下发送任务
        send_email.send("user@example.com", "Hello")
    """
    
    def __init__(
        self,
        func: Callable,
        queue_name: str,
        actor_name: str,
        broker: Any,  # RedisBroker | None，但使用 Any 避免类型检查错误
        **actor_kwargs: Any,
    ) -> None:
        """初始化任务代理。
        
        Args:
            func: 任务函数
            queue_name: 队列名称
            actor_name: Actor 名称（完整模块路径）
            broker: Broker 实例
            **actor_kwargs: Actor 参数
        """
        self.func = func
        self.queue_name = queue_name
        self.actor_name = actor_name
        self.actor_kwargs = actor_kwargs
        self._broker = broker
    
    def send(self, *args: Any, **kwargs: Any) -> Message | None:
        """发送任务消息，直接通过 broker 发送，不注册 actor。
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Message | None: 发送的消息对象
        """
        if not self._broker:
            raise RuntimeError("Broker 未初始化，无法发送任务")
        
        # 使用 dramatiq 的 Message 类创建消息
        # actor_name 必须是 worker 中注册的完整函数路径
        message = Message(
            queue_name=self.queue_name,
            actor_name=self.actor_name,
            args=args,
            kwargs=kwargs,
            options={
                "max_retries": self.actor_kwargs.get("max_retries", 0),
                "time_limit": self.actor_kwargs.get("time_limit"),
            },
        )
        
        result = self._broker.enqueue(message)
        logger.debug(f"任务消息已发送: {self.actor_name}")
        return result
    
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """直接调用函数（用于测试等场景）。
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Any: 函数返回值
        """
        return self.func(*args, **kwargs)
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<TaskProxy actor_name={self.actor_name} queue={self.queue_name}>"


class TaskManager:
    """任务管理器（命名多实例）。
    
    职责：
    1. 管理任务队列broker
    2. 注册任务
    3. 任务执行和监控
    4. 支持多个命名实例，如不同的消息队列
    
    使用示例:
        # 默认实例
        task_manager = TaskManager.get_instance()
        await task_manager.initialize()
        
        # 命名实例
        email_tasks = TaskManager.get_instance("email")
        report_tasks = TaskManager.get_instance("report")
        
        # 注册任务
        @task_manager.task
        async def send_email(to: str, subject: str):
            # 发送邮件
            pass
        
        # 执行任务
        send_email.send("user@example.com", "Hello")
    """
    
    _instances: dict[str, TaskManager] = {}
    
    def __init__(self, name: str = "default") -> None:
        """初始化任务管理器。
        
        Args:
            name: 实例名称
        """
        self.name = name
        self._broker: Any = None  # KombuBroker | None
        self._initialized: bool = False
        self._task_config: TaskConfig | None = None
        self._run_mode: TaskRunMode = TaskRunMode.WORKER  # 默认 Worker 模式（调度者）
    
    @classmethod
    def get_instance(cls, name: str = "default") -> TaskManager:
        """获取指定名称的实例。
        
        Args:
            name: 实例名称，默认为 "default"
            
        Returns:
            TaskManager: 任务管理器实例
        """
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]
    
    @classmethod
    def reset_instance(cls, name: str | None = None) -> None:
        """重置实例（仅用于测试）。
        
        Args:
            name: 要重置的实例名称。如果为 None，则重置所有实例。
            
        注意：调用此方法前应先调用 cleanup() 释放资源。
        """
        if name is None:
            cls._instances.clear()
        elif name in cls._instances:
            del cls._instances[name]
    
    async def initialize(
        self,
        task_config: TaskConfig | None = None,
        run_mode: TaskRunMode | str | None = None,
        broker_url: str | None = None,
        *,
        middleware: list | None = None,
    ) -> TaskManager:
        """初始化任务队列（链式调用）。
        
        Args:
            task_config: 任务配置（TaskConfig）
            run_mode: 运行模式（TaskRunMode 或字符串，如 "api", "worker"）
            broker_url: Broker连接URL（可选，优先使用 config）
            middleware: 中间件列表
            
        Returns:
            self: 支持链式调用
        """
        if self._initialized:
            logger.warning("任务管理器已初始化，跳过")
            return self
        
        self._task_config = task_config or TaskConfig()
        
        # 处理 run_mode 参数
        if run_mode is None:
            self._run_mode = TaskRunMode.WORKER  # 默认 Worker 模式（调度者）
        elif isinstance(run_mode, str):
            try:
                self._run_mode = TaskRunMode(run_mode.lower())
            except ValueError:
                logger.warning(f"无效的运行模式: {run_mode}，使用默认值: {TaskRunMode.WORKER.value}")
                self._run_mode = TaskRunMode.WORKER
        else:
            self._run_mode = run_mode
        
        # 获取 broker URL（优先级：参数 > 配置 > 环境变量）
        url = broker_url or self._task_config.broker_url
        if not url:
            logger.warning("未配置任务队列URL，任务功能将被禁用")
            return self
        
        if not _DRAMATIQ_AVAILABLE:
            raise ImportError(
                "dramatiq 未安装。请安装可选依赖: pip install 'aury-boot[queue-dramatiq]'"
            )
        
        if not _KOMBU_BROKER_AVAILABLE:
            raise ImportError(
                "dramatiq-kombu-broker 未安装。请安装可选依赖: pip install 'aury-boot[queue-dramatiq-kombu]'"
            )
        
        try:
            # 使用函数式编程创建默认中间件（如果未提供）
            def create_default_middleware() -> list:
                """创建默认中间件列表。"""
                return [AsyncIO(), CurrentMessage(), TimeLimit()]
            
            middleware_list = middleware if middleware is not None else create_default_middleware()
            
            # 使用 KombuBroker，支持多种后端（Redis、RabbitMQ、SQS 等）
            self._broker = KombuBroker(url=url, middleware=middleware_list)
            dramatiq.set_broker(self._broker)
            self._initialized = True
            logger.info(f"任务管理器初始化完成（使用 Kombu Broker: {url}）")
        except Exception as exc:
            logger.error(f"任务队列初始化失败: {exc}")
            raise
        
        return self
    
    def task(
        self,
        func: Callable | None = None,
        *,
        actor_name: str | None = None,
        max_retries: int = 3,
        time_limit: int | None = None,
        queue_name: str = TaskQueueName.DEFAULT.value,
        **kwargs: Any,
    ) -> Any:
        """任务装饰器（始终注册）。
        
        Args:
            func: 任务函数
            actor_name: Actor名称
            max_retries: 最大重试次数
            time_limit: 时间限制（毫秒）
            queue_name: 队列名称
            **kwargs: 其他参数
            
        使用示例:
            @task_manager.task(max_retries=3)
            async def send_email(to: str, subject: str):
                # 发送邮件
                pass
        """
        if not _DRAMATIQ_AVAILABLE:
            raise ImportError(
                "dramatiq 未安装。请安装可选依赖: pip install 'aury-boot[queue-dramatiq]'"
            )
        
        def decorator(f: Callable) -> Callable:
            actor = dramatiq.actor(
                f,
                actor_name=actor_name or f.__name__,
                max_retries=max_retries,
                time_limit=time_limit,
                queue_name=queue_name,
                **kwargs,
            )
            logger.debug(f"任务已注册: {actor_name or f.__name__}")
            return actor
        
        if func is None:
            return decorator
        return decorator(func)
    
    def conditional_task(
        self,
        func: Callable | None = None,
        *,
        actor_name: str | None = None,
        max_retries: int = 3,
        time_limit: int | None = None,
        queue_name: str = TaskQueueName.DEFAULT.value,
        **kwargs: Any,
    ) -> Any:
        """条件注册的任务装饰器。
        
        根据 SERVICE_TYPE 环境变量决定：
        - worker 模式：正常注册为 actor
        - api 模式：返回 TaskProxy，可以发送消息但不注册
        
        Args:
            func: 任务函数
            actor_name: Actor名称
            max_retries: 最大重试次数
            time_limit: 时间限制（毫秒）
            queue_name: 队列名称
            **kwargs: 其他参数
            
        使用示例:
            @task_manager.conditional_task(max_retries=3)
            async def send_email(to: str, subject: str):
                # 在 worker 中会注册为 actor
                # 在 API 中会返回 TaskProxy
                pass
        """
        if not _DRAMATIQ_AVAILABLE:
            raise ImportError(
                "dramatiq 未安装。请安装可选依赖: pip install 'aury-boot[queue-dramatiq]'"
            )
        
        def decorator(f: Callable) -> Any:
            # 从配置获取运行模式，默认为 API
            run_mode = self._run_mode
            
            if run_mode == TaskRunMode.WORKER:
                # Worker 模式下正常注册（执行者）
                actor = dramatiq.actor(
                    f,
                    actor_name=actor_name or f.__name__,
                    max_retries=max_retries,
                    time_limit=time_limit,
                    queue_name=queue_name,
                    **kwargs,
                )
                logger.debug(f"任务已注册（worker 模式）: {actor_name or f.__name__}")
                return actor
            else:
                # Producer 模式下返回代理对象，不注册但可以发送消息
                # 获取函数的完整模块路径作为 actor_name
                module_name = f.__module__
                func_name = f.__name__
                full_actor_name = actor_name or f"{module_name}.{func_name}"
                
                proxy = TaskProxy(
                    func=f,
                    queue_name=queue_name,
                    actor_name=full_actor_name,
                    broker=self._broker,
                    max_retries=max_retries,
                    time_limit=time_limit,
                    **kwargs,
                )
                logger.debug(f"任务代理已创建（producer 模式）: {full_actor_name}")
                return proxy
        
        if func is None:
            return decorator
        return decorator(func)
    
    @property
    def broker(self) -> Any:  # KombuBroker | None
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


def conditional_task(
    func: Callable | None = None,
    /,
    queue_name: str = TaskQueueName.DEFAULT.value,
    run_mode: TaskRunMode | str | None = None,
    **kwargs: Any,
) -> Callable[[Callable], Any] | Any:
    """条件注册的任务装饰器。
    
    根据运行模式决定行为：
    - worker 模式：正常注册为任务执行者
    - producer 模式：返回 TaskProxy，可发送任务但不注册
    
    支持两种使用方式：
    - @conditional_task      # 无括号
    - @conditional_task()    # 带括号
    
    Args:
        func: 被装饰的函数（无括号调用时自动传入）
        queue_name: 队列名称
        run_mode: 运行模式（TaskRunMode 或字符串），默认为 WORKER
        **kwargs: 其他参数（如 max_retries, time_limit）
    
    使用示例:
        @conditional_task
        def send_email(to: str, subject: str):
            pass
        
        @conditional_task(queue_name="high", max_retries=5)
        def send_sms(phone: str, message: str):
            pass
        
        # 发送任务到队列
        send_email.send("user@example.com", "Hello")
    """
    if not _DRAMATIQ_AVAILABLE:
        raise ImportError(
            "dramatiq 未安装。请安装可选依赖: pip install 'aury-boot[queue-dramatiq]'"
        )
    
    def decorator(f: Callable) -> Any:
        # 处理 run_mode 参数，默认为 WORKER
        if run_mode is None:
            mode = TaskRunMode.WORKER
        elif isinstance(run_mode, str):
            try:
                mode = TaskRunMode(run_mode.lower())
            except ValueError:
                logger.warning(f"无效的运行模式: {run_mode}，使用默认值: {TaskRunMode.WORKER.value}")
                mode = TaskRunMode.WORKER
        else:
            mode = run_mode
        
        if mode == TaskRunMode.WORKER:
            # Worker 模式下正常注册（执行者）
            return dramatiq.actor(queue_name=queue_name, **kwargs)(f)
        else:
            # Producer 模式下返回代理对象，不注册但可以发送消息
            # 获取函数的完整模块路径作为 actor_name
            module_name = f.__module__
            func_name = f.__name__
            full_actor_name = f"{module_name}.{func_name}"
            
            # 获取全局 broker（如果已设置）
            broker = dramatiq.get_broker() if hasattr(dramatiq, "get_broker") else None
            
            return TaskProxy(
                func=f,
                queue_name=queue_name,
                actor_name=full_actor_name,
                broker=broker,
                **kwargs,
            )
    
    # 支持 @conditional_task 和 @conditional_task() 两种写法
    if func is not None:
        return decorator(func)
    return decorator


__all__ = [
    "TaskManager",
    "TaskProxy",
    "conditional_task",
]


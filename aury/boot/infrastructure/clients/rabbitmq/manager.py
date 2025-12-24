"""RabbitMQ 客户端管理器 - 命名多实例模式。

提供统一的 RabbitMQ 连接管理，支持多实例。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aury.boot.common.logging import logger

from .config import RabbitMQConfig

if TYPE_CHECKING:
    from aio_pika import Channel, Connection, RobustConnection


class RabbitMQClient:
    """RabbitMQ 客户端管理器（命名多实例）。
    
    提供统一的 RabbitMQ 连接管理接口，支持：
    - 多实例管理（如 events、tasks 各自独立）
    - 连接和通道管理
    - 健康检查
    - 链式配置
    
    使用示例:
        # 默认实例
        client = RabbitMQClient.get_instance()
        client.configure(url="amqp://guest:guest@localhost:5672/")
        await client.initialize()
        
        # 命名实例
        events_mq = RabbitMQClient.get_instance("events")
        tasks_mq = RabbitMQClient.get_instance("tasks")
        
        # 获取通道
        channel = await client.get_channel()
        await channel.default_exchange.publish(message, routing_key="test")
        
        # 清理
        await client.cleanup()
    """
    
    _instances: dict[str, RabbitMQClient] = {}
    
    def __init__(self, name: str = "default") -> None:
        """初始化 RabbitMQ 客户端管理器。
        
        Args:
            name: 实例名称
        """
        self.name = name
        self._config: RabbitMQConfig | None = None
        self._connection: RobustConnection | None = None
        self._channel: Channel | None = None
        self._initialized: bool = False
    
    @classmethod
    def get_instance(cls, name: str = "default") -> RabbitMQClient:
        """获取指定名称的实例。
        
        Args:
            name: 实例名称，默认为 "default"
            
        Returns:
            RabbitMQClient: RabbitMQ 客户端实例
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
    
    def configure(
        self,
        url: str | None = None,
        *,
        heartbeat: int | None = None,
        connection_timeout: float | None = None,
        blocked_connection_timeout: float | None = None,
        prefetch_count: int | None = None,
        publisher_confirms: bool | None = None,
        config: RabbitMQConfig | None = None,
    ) -> RabbitMQClient:
        """配置 RabbitMQ 客户端（链式调用）。
        
        Args:
            url: AMQP 连接 URL
            heartbeat: 心跳间隔
            connection_timeout: 连接超时
            blocked_connection_timeout: 阻塞连接超时
            prefetch_count: 预取消息数量
            publisher_confirms: 是否启用发布确认
            config: 直接传入 RabbitMQConfig 对象
            
        Returns:
            self: 支持链式调用
        """
        if config:
            self._config = config
        else:
            config_dict = {}
            if url is not None:
                config_dict["url"] = url
            if heartbeat is not None:
                config_dict["heartbeat"] = heartbeat
            if connection_timeout is not None:
                config_dict["connection_timeout"] = connection_timeout
            if blocked_connection_timeout is not None:
                config_dict["blocked_connection_timeout"] = blocked_connection_timeout
            if prefetch_count is not None:
                config_dict["prefetch_count"] = prefetch_count
            if publisher_confirms is not None:
                config_dict["publisher_confirms"] = publisher_confirms
            
            self._config = RabbitMQConfig(**config_dict)
        
        return self
    
    async def initialize(self) -> RabbitMQClient:
        """初始化 RabbitMQ 连接。
        
        Returns:
            self: 支持链式调用
            
        Raises:
            RuntimeError: 未配置时调用
            ConnectionError: 连接失败
        """
        if self._initialized:
            logger.warning(f"RabbitMQ 客户端 [{self.name}] 已初始化，跳过")
            return self
        
        if not self._config:
            raise RuntimeError(
                f"RabbitMQ 客户端 [{self.name}] 未配置，请先调用 configure()"
            )
        
        try:
            import aio_pika
            
            # 创建连接
            self._connection = await aio_pika.connect_robust(
                self._config.url,
                heartbeat=self._config.heartbeat,
                timeout=self._config.connection_timeout,
                blocked_connection_timeout=self._config.blocked_connection_timeout,
            )
            
            # 创建默认通道
            self._channel = await self._connection.channel(
                publisher_confirms=self._config.publisher_confirms
            )
            
            # 设置 QoS
            await self._channel.set_qos(prefetch_count=self._config.prefetch_count)
            
            self._initialized = True
            masked_url = self._mask_url(self._config.url)
            logger.info(f"RabbitMQ 客户端 [{self.name}] 初始化完成: {masked_url}")
            
            return self
        except ImportError:
            raise RuntimeError(
                "需要安装 aio-pika: pip install aio-pika"
            )
        except Exception as e:
            logger.error(f"RabbitMQ 客户端 [{self.name}] 初始化失败: {e}")
            raise
    
    def _mask_url(self, url: str) -> str:
        """URL 脱敏（隐藏密码）。"""
        if "@" in url:
            # amqp://user:password@host:port/ -> amqp://user:***@host:port/
            parts = url.split("@")
            prefix = parts[0]
            suffix = parts[1]
            if ":" in prefix:
                # 找到最后一个冒号（密码前）
                last_colon = prefix.rfind(":")
                scheme_and_user = prefix[:last_colon]
                return f"{scheme_and_user}:***@{suffix}"
        return url
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化。"""
        return self._initialized
    
    @property
    def connection(self) -> Connection:
        """获取 RabbitMQ 连接。
        
        Returns:
            Connection: RabbitMQ 连接实例
            
        Raises:
            RuntimeError: 未初始化时调用
        """
        if not self._connection:
            raise RuntimeError(
                f"RabbitMQ 客户端 [{self.name}] 未初始化，请先调用 initialize()"
            )
        return self._connection
    
    async def get_channel(self, *, new: bool = False) -> Channel:
        """获取 RabbitMQ 通道。
        
        Args:
            new: 是否创建新通道（默认使用共享通道）
            
        Returns:
            Channel: RabbitMQ 通道实例
            
        Raises:
            RuntimeError: 未初始化时调用
        """
        if not self._connection:
            raise RuntimeError(
                f"RabbitMQ 客户端 [{self.name}] 未初始化，请先调用 initialize()"
            )
        
        if new:
            channel = await self._connection.channel(
                publisher_confirms=self._config.publisher_confirms if self._config else True
            )
            if self._config:
                await channel.set_qos(prefetch_count=self._config.prefetch_count)
            return channel
        
        if not self._channel or self._channel.is_closed:
            self._channel = await self._connection.channel(
                publisher_confirms=self._config.publisher_confirms if self._config else True
            )
            if self._config:
                await self._channel.set_qos(prefetch_count=self._config.prefetch_count)
        
        return self._channel
    
    async def health_check(self) -> bool:
        """健康检查。
        
        Returns:
            bool: 连接是否正常
        """
        if not self._connection:
            return False
        
        try:
            return not self._connection.is_closed
        except Exception as e:
            logger.warning(f"RabbitMQ 客户端 [{self.name}] 健康检查失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源，关闭连接。"""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
            logger.debug(f"RabbitMQ 通道 [{self.name}] 已关闭")
        
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info(f"RabbitMQ 客户端 [{self.name}] 已关闭")
        
        self._channel = None
        self._connection = None
        self._initialized = False
    
    def __repr__(self) -> str:
        """字符串表示。"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<RabbitMQClient name={self.name} status={status}>"


__all__ = ["RabbitMQClient"]

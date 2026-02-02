"""Redis 客户端管理器 - 命名多实例模式。

提供统一的 Redis 连接管理，支持多实例。
支持普通 Redis 和 Redis Cluster：
- redis://... - 普通 Redis
- redis-cluster://... - Redis Cluster
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from redis.asyncio import ConnectionPool, Redis

from aury.boot.common.logging import logger

from .config import RedisConfig

if TYPE_CHECKING:
    from redis.asyncio.cluster import RedisCluster


class RedisClient:
    """Redis 客户端管理器（命名多实例）。
    
    提供统一的 Redis 连接管理接口，支持：
    - 多实例管理（如 cache、session、queue 各自独立）
    - 连接池管理
    - 健康检查
    - 链式配置
    
    使用示例:
        # 默认实例
        client = RedisClient.get_instance()
        client.configure(url="redis://localhost:6379/0")
        await client.initialize()
        
        # 命名实例
        cache_redis = RedisClient.get_instance("cache")
        queue_redis = RedisClient.get_instance("queue")
        
        # 获取连接
        redis = client.connection
        await redis.set("key", "value")
        
        # 或直接使用
        await client.execute("set", "key", "value")
    """
    
    _instances: dict[str, RedisClient] = {}
    
    def __init__(self, name: str = "default") -> None:
        """初始化 Redis 客户端管理器。
        
        Args:
            name: 实例名称
        """
        self.name = name
        self._config: RedisConfig | None = None
        self._pool: ConnectionPool | None = None
        self._redis: Redis | RedisCluster | None = None
        self._initialized: bool = False
        self._is_cluster: bool = False
    
    @classmethod
    def get_instance(cls, name: str = "default") -> RedisClient:
        """获取指定名称的实例。
        
        Args:
            name: 实例名称，默认为 "default"
            
        Returns:
            RedisClient: Redis 客户端实例
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
        max_connections: int | None = None,
        socket_timeout: float | None = None,
        socket_connect_timeout: float | None = None,
        retry_on_timeout: bool | None = None,
        health_check_interval: int | None = None,
        decode_responses: bool | None = None,
        config: RedisConfig | None = None,
    ) -> RedisClient:
        """配置 Redis 客户端（链式调用）。
        
        Args:
            url: Redis 连接 URL
            max_connections: 最大连接数
            socket_timeout: 套接字超时
            socket_connect_timeout: 连接超时
            retry_on_timeout: 超时是否重试
            health_check_interval: 健康检查间隔
            decode_responses: 是否解码响应
            config: 直接传入 RedisConfig 对象
            
        Returns:
            self: 支持链式调用
        """
        if config:
            self._config = config
        else:
            # 构建配置
            config_dict = {}
            if url is not None:
                config_dict["url"] = url
            if max_connections is not None:
                config_dict["max_connections"] = max_connections
            if socket_timeout is not None:
                config_dict["socket_timeout"] = socket_timeout
            if socket_connect_timeout is not None:
                config_dict["socket_connect_timeout"] = socket_connect_timeout
            if retry_on_timeout is not None:
                config_dict["retry_on_timeout"] = retry_on_timeout
            if health_check_interval is not None:
                config_dict["health_check_interval"] = health_check_interval
            if decode_responses is not None:
                config_dict["decode_responses"] = decode_responses
            
            self._config = RedisConfig(**config_dict)
        
        return self
    
    async def initialize(self) -> RedisClient:
        """初始化 Redis 连接。
        
        自动检测 URL scheme：
        - redis://... -> 普通 Redis
        - redis-cluster://... -> Redis Cluster
        
        Returns:
            self: 支持链式调用
            
        Raises:
            RuntimeError: 未配置时调用
            ConnectionError: 连接失败
        """
        if self._initialized:
            logger.warning(f"Redis 客户端 [{self.name}] 已初始化，跳过")
            return self
        
        if not self._config:
            raise RuntimeError(
                f"Redis 客户端 [{self.name}] 未配置，请先调用 configure()"
            )
        
        try:
            url = self._config.url
            
            # 自动检测是否为集群模式
            if url.startswith("redis-cluster://"):
                await self._initialize_cluster(url)
            else:
                await self._initialize_standalone(url)
            
            # 验证连接
            await self._redis.ping()
            
            self._initialized = True
            masked_url = self._mask_url(url)
            mode = "Cluster" if self._is_cluster else "Standalone"
            logger.info(f"Redis 客户端 [{self.name}] 初始化完成 ({mode}): {masked_url}")
            
            return self
        except Exception as e:
            logger.error(f"Redis 客户端 [{self.name}] 初始化失败: {e}")
            raise
    
    async def _initialize_standalone(self, url: str) -> None:
        """初始化普通 Redis 连接。"""
        self._pool = ConnectionPool.from_url(
            url,
            max_connections=self._config.max_connections,
            socket_timeout=self._config.socket_timeout,
            socket_connect_timeout=self._config.socket_connect_timeout,
            retry_on_timeout=self._config.retry_on_timeout,
            health_check_interval=self._config.health_check_interval,
            decode_responses=self._config.decode_responses,
        )
        self._redis = Redis(connection_pool=self._pool)
        self._is_cluster = False
    
    async def _initialize_cluster(self, url: str) -> None:
        """初始化 Redis Cluster 连接。
        
        支持 URL 格式:
        - redis-cluster://password@host:port （密码在用户名位置）
        - redis-cluster://:password@host:port （标准格式）
        - redis-cluster://username:password@host:port （ACL 模式）
        """
        from redis.asyncio.cluster import RedisCluster
        
        parsed_url = url.replace("redis-cluster://", "redis://")
        parsed = urlparse(parsed_url)
        
        # 提取认证信息
        username = parsed.username
        password = parsed.password
        
        # 处理 password@host 格式（密码在用户名位置）
        if username and not password:
            password = username
            username = None
        
        # 构建连接参数
        cluster_kwargs: dict = {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 6379,
            "decode_responses": self._config.decode_responses,
            "socket_timeout": self._config.socket_timeout,
            "socket_connect_timeout": self._config.socket_connect_timeout,
            "retry_on_timeout": self._config.retry_on_timeout,
        }
        
        if username:
            cluster_kwargs["username"] = username
        if password:
            cluster_kwargs["password"] = password
        
        self._redis = RedisCluster(**cluster_kwargs)
        self._is_cluster = True
    
    def _mask_url(self, url: str) -> str:
        """URL 脱敏（隐藏密码）。"""
        if "@" in url:
            # redis://:password@host:port/db -> redis://***@host:port/db
            parts = url.split("@")
            prefix = parts[0]
            suffix = parts[1]
            # 隐藏密码部分
            if ":" in prefix:
                scheme_and_user = prefix.rsplit(":", 1)[0]
                return f"{scheme_and_user}:***@{suffix}"
        return url
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化。"""
        return self._initialized
    
    @property
    def is_cluster(self) -> bool:
        """检查是否为集群模式。"""
        return self._is_cluster
    
    @property
    def connection(self) -> Redis | RedisCluster:
        """获取 Redis 连接。
        
        Returns:
            Redis 或 RedisCluster 客户端实例
            
        Raises:
            RuntimeError: 未初始化时调用
        """
        if not self._redis:
            raise RuntimeError(
                f"Redis 客户端 [{self.name}] 未初始化，请先调用 initialize()"
            )
        return self._redis
    
    async def execute(self, command: str, *args, **kwargs):
        """执行 Redis 命令。
        
        Args:
            command: Redis 命令名
            *args: 命令参数
            **kwargs: 命令关键字参数
            
        Returns:
            命令执行结果
        """
        return await self.connection.execute_command(command, *args, **kwargs)
    
    async def health_check(self) -> bool:
        """健康检查。
        
        Returns:
            bool: 连接是否正常
        """
        if not self._redis:
            return False
        
        try:
            await self._redis.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis 客户端 [{self.name}] 健康检查失败: {e}")
            return False
    
    async def cleanup(self) -> None:
        """清理资源，关闭连接。"""
        if self._redis:
            if self._is_cluster:
                await self._redis.aclose()
            else:
                await self._redis.close()
            logger.info(f"Redis 客户端 [{self.name}] 已关闭")
        
        if self._pool:
            await self._pool.disconnect()
        
        self._redis = None
        self._pool = None
        self._initialized = False
        self._is_cluster = False
    
    def __repr__(self) -> str:
        """字符串表示。"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<RedisClient name={self.name} status={status}>"


__all__ = ["RedisClient"]

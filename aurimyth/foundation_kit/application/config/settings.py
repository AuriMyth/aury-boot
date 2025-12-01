"""共享配置基类。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。

注意：Application 层的配置是独立的，不依赖 Infrastructure 层。
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置。
    
    环境变量前缀: DATABASE_
    示例: DATABASE_URL, DATABASE_ECHO, DATABASE_POOL_SIZE
    """
    
    url: str = Field(
        default="sqlite:///./app.db",
        description="数据库连接字符串"
    )
    echo: bool = Field(
        default=False,
        description="是否输出 SQL 语句"
    )
    pool_size: int = Field(
        default=5,
        description="数据库连接池大小"
    )
    max_overflow: int = Field(
        default=10,
        description="连接池最大溢出连接数"
    )
    pool_recycle: int = Field(
        default=3600,
        description="连接回收时间（秒）"
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="是否在获取连接前进行 PING"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        case_sensitive=False,
    )


class CacheSettings(BaseSettings):
    """缓存配置。
    
    环境变量前缀: CACHE_
    示例: CACHE_TYPE, CACHE_REDIS_URL, CACHE_MAX_SIZE
    """
    
    cache_type: str = Field(
        default="memory",
        description="缓存类型"
    )
    redis_url: str | None = Field(
        default=None,
        description="Redis缓存URL"
    )
    max_size: int = Field(
        default=1000,
        description="内存缓存最大大小"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        case_sensitive=False,
    )


class ServerSettings(BaseSettings):
    """服务器配置。
    
    环境变量前缀: SERVER_
    示例: SERVER_HOST, SERVER_PORT, SERVER_RELOAD
    """
    
    host: str = Field(
        default="127.0.0.1",
        description="服务器监听地址"
    )
    port: int = Field(
        default=8000,
        description="服务器监听端口"
    )
    reload: bool = Field(
        default=True,
        description="是否启用热重载"
    )
    workers: int = Field(
        default=1,
        description="工作进程数"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="SERVER_",
        case_sensitive=False,
    )


class CORSSettings(BaseSettings):
    """CORS配置。
    
    环境变量前缀: CORS_
    示例: CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS
    """
    
    origins: list[str] = Field(
        default=["*"],
        description="允许的CORS源"
    )
    allow_credentials: bool = Field(
        default=True,
        description="是否允许CORS凭据"
    )
    allow_methods: list[str] = Field(
        default=["*"],
        description="允许的CORS方法"
    )
    allow_headers: list[str] = Field(
        default=["*"],
        description="允许的CORS头"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        case_sensitive=False,
    )


class LogSettings(BaseSettings):
    """日志配置。
    
    环境变量前缀: LOG_
    示例: LOG_LEVEL, LOG_FILE
    """
    
    level: str = Field(
        default="INFO",
        description="日志级别"
    )
    file: str | None = Field(
        default=None,
        description="日志文件路径（如果不设置则仅输出到控制台）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
    )


class ServiceSettings(BaseSettings):
    """服务配置。
    
    环境变量前缀: SERVICE_
    示例: SERVICE_TYPE
    
    服务类型说明：
    - api: 运行 API 服务（可伴随调度器，根据 SCHEDULER_MODE 决定调度器运行方式）
    - worker: 运行任务队列 Worker（处理异步任务）
    - scheduler: 仅运行调度器进程（独立 pod，只运行定时任务，不运行 API）
    """
    
    service_type: str = Field(
        default="api",
        description="服务类型（api/worker/scheduler）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="SERVICE_",
        case_sensitive=False,
    )


class SchedulerSettings(BaseSettings):
    """调度器配置。
    
    环境变量前缀: SCHEDULER_
    示例: SCHEDULER_MODE
    
    调度器模式说明（仅在 SERVICE_TYPE=api 时有效）：
    - embedded: 在 API 进程中运行调度器（默认）
    - standalone: 调度器在独立进程中运行
    - disabled: 禁用调度器
    
    当 SERVICE_TYPE=scheduler 时，会启动一个独立的调度器进程，此配置无效。
    """
    
    mode: str = Field(
        default="embedded",
        description="调度器运行模式（embedded/standalone/disabled），仅在 SERVICE_TYPE=api 时有效"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="SCHEDULER_",
        case_sensitive=False,
    )


class TaskSettings(BaseSettings):
    """任务队列配置。
    
    环境变量前缀: TASK_
    示例: TASK_BROKER_URL, TASK_MAX_RETRIES
    """
    
    broker_url: str | None = Field(
        default=None,
        description="任务队列代理 URL（如 Redis 或 RabbitMQ）"
    )
    max_retries: int = Field(
        default=3,
        description="最大重试次数"
    )
    timeout: int = Field(
        default=3600,
        description="任务超时时间（秒）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="TASK_",
        case_sensitive=False,
    )


class EventSettings(BaseSettings):
    """事件总线配置。
    
    环境变量前缀: EVENT_
    示例: EVENT_BROKER_URL, EVENT_EXCHANGE_NAME
    """
    
    broker_url: str | None = Field(
        default=None,
        description="事件总线代理 URL（如 RabbitMQ）"
    )
    exchange_name: str = Field(
        default="aurimyth.events",
        description="事件交换机名称"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="EVENT_",
        case_sensitive=False,
    )


class RPCClientSettings(BaseSettings):
    """RPC 客户端调用配置。
    
    用于配置客户端调用其他服务时的行为。
    
    环境变量前缀: RPC_CLIENT_
    示例: RPC_CLIENT_SERVICES, RPC_CLIENT_TIMEOUT, RPC_CLIENT_RETRY_TIMES, RPC_CLIENT_DNS_SCHEME
    """
    
    services: dict[str, str] = Field(
        default_factory=dict,
        description="服务地址映射 {service_name: url}（优先级最高，会覆盖 DNS 解析）"
    )
    default_timeout: int = Field(
        default=30,
        description="默认超时时间（秒）"
    )
    default_retry_times: int = Field(
        default=3,
        description="默认重试次数"
    )
    dns_scheme: str = Field(
        default="http",
        description="DNS 解析使用的协议（http 或 https）"
    )
    dns_port: int = Field(
        default=80,
        description="DNS 解析默认端口"
    )
    use_dns_fallback: bool = Field(
        default=True,
        description="是否在配置中找不到时使用 DNS 解析（K8s/Docker Compose 自动 DNS）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="RPC_CLIENT_",
        case_sensitive=False,
    )


class RPCServiceSettings(BaseSettings):
    """RPC 服务注册配置。
    
    用于配置当前服务注册到服务注册中心时的信息。
    
    环境变量前缀: RPC_SERVICE_
    示例: RPC_SERVICE_NAME, RPC_SERVICE_URL, RPC_SERVICE_HEALTH_CHECK_URL
    """
    
    name: str | None = Field(
        default=None,
        description="服务名称（用于注册）"
    )
    url: str | None = Field(
        default=None,
        description="服务地址（用于注册）"
    )
    health_check_url: str | None = Field(
        default=None,
        description="健康检查 URL（用于注册）"
    )
    auto_register: bool = Field(
        default=False,
        description="是否自动注册到服务注册中心"
    )
    registry_url: str | None = Field(
        default=None,
        description="服务注册中心地址（如果使用外部注册中心）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="RPC_SERVICE_",
        case_sensitive=False,
    )


class HealthCheckSettings(BaseSettings):
    """健康检查配置。
    
    用于配置 AuriMyth 框架的默认健康检查端点。
    注意：此配置仅用于框架内置的健康检查端点，不影响服务自身的健康检查端点。
    
    环境变量前缀: HEALTH_CHECK_
    示例: HEALTH_CHECK_PATH, HEALTH_CHECK_ENABLED
    """
    
    path: str = Field(
        default="/health",
        description="健康检查端点路径（默认: /health）"
    )
    enabled: bool = Field(
        default=True,
        description="是否启用 AuriMyth 默认健康检查端点"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="HEALTH_CHECK_",
        case_sensitive=False,
    )


class BaseConfig(BaseSettings):
    """基础配置类。
    
    所有应用配置的基类，提供通用配置项。
    使用 pydantic-settings 自动从环境变量和 .env 文件加载配置。
    
    注意：Application 层配置完全独立，不依赖 Infrastructure 层。
    """
    
    # 缓存配置
    cache: CacheSettings = Field(default_factory=CacheSettings)
    
    # 服务器配置
    server: ServerSettings = Field(default_factory=ServerSettings)
    
    # CORS配置
    cors: CORSSettings = Field(default_factory=CORSSettings)
    
    # 日志配置
    log: LogSettings = Field(default_factory=LogSettings)
    
    # 服务配置
    service: ServiceSettings = Field(default_factory=ServiceSettings)
    
    # 调度器配置
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    
    # RPC 客户端配置（调用其他服务）
    rpc_client: RPCClientSettings = Field(default_factory=RPCClientSettings)
    
    # RPC 服务配置（当前服务注册）
    rpc_service: RPCServiceSettings = Field(default_factory=RPCServiceSettings)
    
    # 健康检查配置
    health_check: HealthCheckSettings = Field(default_factory=HealthCheckSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境。"""
        return self.log.level.upper() == "ERROR"


__all__ = [
    "BaseConfig",
    "CORSSettings",
    "CacheSettings",
    "HealthCheckSettings",
    "LogSettings",
    "RPCClientSettings",
    "RPCServiceSettings",
    "SchedulerSettings",
    "ServerSettings",
    "ServiceSettings",
]


"""共享配置基类。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。

注意：Application 层的配置是独立的，不依赖 Infrastructure 层。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .multi_instance import MultiInstanceConfigLoader, MultiInstanceSettings


def _load_env_file(env_file: str | Path) -> bool:
    """加载 .env 文件到环境变量。"""
    return load_dotenv(env_file, override=True)


# =============================================================================
# 多实例配置基类
# =============================================================================


class DatabaseInstanceConfig(MultiInstanceSettings):
    """数据库实例配置。
    
    环境变量格式: DATABASE_{INSTANCE}_{FIELD}
    示例:
        DATABASE_DEFAULT_URL=postgresql://main...
        DATABASE_DEFAULT_POOL_SIZE=10
        DATABASE_ANALYTICS_URL=postgresql://analytics...
    """
    
    url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
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
    pool_timeout: int = Field(
        default=30,
        description="获取连接超时时间（秒）"
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="是否在获取连接前进行 PING"
    )


class CacheInstanceConfig(MultiInstanceSettings):
    """缓存实例配置。
    
    环境变量格式: CACHE_{INSTANCE}_{FIELD}
    示例:
        CACHE_DEFAULT_BACKEND=redis
        CACHE_DEFAULT_URL=redis://localhost:6379/0
        CACHE_LOCAL_BACKEND=memory
        CACHE_LOCAL_MAX_SIZE=5000
    """
    
    backend: str = Field(
        default="memory",
        description="缓存后端 (memory/redis/memcached)"
    )
    url: str | None = Field(
        default=None,
        description="缓存服务 URL"
    )
    max_size: int = Field(
        default=1000,
        description="内存缓存最大大小"
    )


class StorageInstanceConfig(MultiInstanceSettings):
    """对象存储实例配置。
    
    环境变量格式: STORAGE_{INSTANCE}_{FIELD}
    示例:
        STORAGE_DEFAULT_BACKEND=s3
        STORAGE_DEFAULT_BUCKET=main-bucket
        STORAGE_BACKUP_BACKEND=local
        STORAGE_BACKUP_BASE_PATH=/backup
    """
    
    backend: Literal["local", "s3", "oss", "cos"] = Field(
        default="local",
        description="存储后端"
    )
    # S3 配置
    access_key_id: str | None = Field(default=None)
    access_key_secret: str | None = Field(default=None)
    endpoint: str | None = Field(default=None)
    region: str | None = Field(default=None)
    bucket_name: str | None = Field(default=None)
    # 本地存储
    base_path: str = Field(default="./storage")


class ChannelInstanceConfig(MultiInstanceSettings):
    """通道实例配置。
    
    环境变量格式: CHANNEL_{INSTANCE}_{FIELD}
    示例:
        CHANNEL_DEFAULT_BACKEND=memory
        CHANNEL_SHARED_BACKEND=redis
        CHANNEL_SHARED_URL=redis://localhost:6379/3
    """
    
    backend: str = Field(
        default="memory",
        description="通道后端 (memory/redis)"
    )
    url: str | None = Field(
        default=None,
        description="Redis URL（当 backend=redis 时需要）"
    )


class MQInstanceConfig(MultiInstanceSettings):
    """消息队列实例配置。
    
    环境变量格式: MQ_{INSTANCE}_{FIELD}
    示例:
        MQ_DEFAULT_BACKEND=redis
        MQ_DEFAULT_URL=redis://localhost:6379/4
    """
    
    backend: str = Field(
        default="redis",
        description="消息队列后端 (redis/rabbitmq)"
    )
    url: str | None = Field(
        default=None,
        description="连接 URL"
    )


class EventInstanceConfig(MultiInstanceSettings):
    """事件总线实例配置。
    
    环境变量格式: EVENT_{INSTANCE}_{FIELD}
    示例:
        EVENT_DEFAULT_BACKEND=memory
        EVENT_DISTRIBUTED_BACKEND=redis
        EVENT_DISTRIBUTED_URL=redis://localhost:6379/5
    """
    
    backend: str = Field(
        default="memory",
        description="事件后端 (memory/redis/rabbitmq)"
    )
    url: str | None = Field(
        default=None,
        description="连接 URL"
    )


# =============================================================================
# 单实例配置
# =============================================================================


class DatabaseSettings(BaseSettings):
    """数据库配置（单实例）。
    
    推荐使用多实例配置: DATABASE_{INSTANCE}_{FIELD}
    """
    
    url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
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
    pool_timeout: int = Field(
        default=30,
        description="获取连接超时时间（秒）"
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
    示例: CACHE_TYPE, CACHE_URL, CACHE_MAX_SIZE
    
    支持的缓存类型：
    - memory: 内存缓存（默认，无需 URL）
    - redis: Redis 缓存（需要设置 CACHE_URL）
    - memcached: Memcached 缓存（需要设置 CACHE_URL）
    """
    
    cache_type: str = Field(
        default="memory",
        description="缓存类型 (memory/redis/memcached)"
    )
    url: str | None = Field(
        default=None,
        description="缓存服务 URL（如 redis://localhost:6379）"
    )
    max_size: int = Field(
        default=1000,
        description="内存缓存最大大小"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="CACHE_",
        case_sensitive=False,
    )


class StorageSettings(BaseSettings):
    """对象存储组件接入配置（Application 层）。

说明：
- Application 层负责从 env/.env 读取配置（快速接入组件）
- Infrastructure 层的 storage 仅接受 Pydantic(BaseModel) 的配置对象，不读取 env

环境变量前缀：STORAGE_
"""

    enabled: bool = Field(default=True, description="是否启用存储组件")

    # 后端类型
    type: Literal["local", "s3", "oss", "cos"] = Field(default="local", description="存储类型")

    # S3/兼容协议通用
    access_key_id: str | None = Field(default=None, description="访问密钥ID")
    access_key_secret: str | None = Field(default=None, description="访问密钥")
    session_token: str | None = Field(default=None, description="会话令牌（STS临时凭证）")
    endpoint: str | None = Field(default=None, description="端点URL（MinIO/私有云等）")
    region: str | None = Field(default=None, description="区域")
    bucket_name: str | None = Field(default=None, description="默认桶名")
    addressing_style: Literal["virtual", "path"] = Field(default="virtual", description="S3寻址风格")

    # S3 AssumeRole（服务端使用；由外部决定何时刷新）
    role_arn: str | None = Field(default=None, description="STS AssumeRole 的角色ARN")
    role_session_name: str = Field(default="aury-storage", description="STS会话名")
    external_id: str | None = Field(default=None, description="STS ExternalId")
    sts_endpoint: str | None = Field(default=None, description="STS端点（可选）")
    sts_region: str | None = Field(default=None, description="STS区域（可选）")
    sts_duration_seconds: int = Field(default=3600, description="AssumeRole DurationSeconds")

    # local
    base_path: str = Field(default="./storage", description="本地存储基础目录")

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        case_sensitive=False,
        extra="ignore",
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
    示例: LOG_LEVEL, LOG_DIR, LOG_ROTATION_TIME, LOG_RETENTION_DAYS
    """
    
    level: str = Field(
        default="INFO",
        description="日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)"
    )
    dir: str | None = Field(
        default=None,
        description="日志文件目录（如果不设置则默认为 './log'）"
    )
    rotation_time: str = Field(
        default="00:00",
        description="日志文件轮转时间 (HH:MM 格式，每天定时轮转)"
    )
    rotation_size: str = Field(
        default="50 MB",
        description="日志文件轮转大小阈值（超过此大小会产生 .1, .2 等后缀文件）"
    )
    retention_days: int = Field(
        default=7,
        description="日志文件保留天数"
    )
    enable_file_rotation: bool = Field(
        default=True,
        description="是否启用日志文件轮转"
    )
    enable_classify: bool = Field(
        default=True,
        description="是否按模块和级别分类日志文件"
    )
    enable_console: bool = Field(
        default=True,
        description="是否输出日志到控制台"
    )
    websocket_log_messages: bool = Field(
        default=False,
        description="是否记录 WebSocket 消息内容（注意性能和敏感数据）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
    )


class ServiceSettings(BaseSettings):
    """服务配置。

    环境变量前缀: SERVICE_
    示例: SERVICE_NAME, SERVICE_TYPE

    服务类型说明：
    - api: 运行 API 服务（SCHEDULER_ENABLED 决定是否同时运行调度器）
    - worker: 运行任务队列 Worker（处理异步任务）

    独立调度器通过 `aury scheduler` 命令运行，不需要配置 SERVICE_TYPE。
    """

    name: str = Field(
        default="app",
        description="服务名称，用于日志目录区分"
    )
    service_type: str = Field(
        default="api",
        description="服务类型（api/worker）"
    )

    model_config = SettingsConfigDict(
        env_prefix="SERVICE_",
        case_sensitive=False,
    )


class SchedulerSettings(BaseSettings):
    """调度器配置。
    
    环境变量前缀: SCHEDULER_
    示例: SCHEDULER_ENABLED, SCHEDULER_SCHEDULE_MODULES
    
    仅在 SERVICE_TYPE=api 时有效：
    - SCHEDULER_ENABLED=true: API 服务同时运行内嵌调度器（默认）
    - SCHEDULER_ENABLED=false: 只运行 API，不启动调度器
    
    独立调度器通过 `aury scheduler` 命令运行，不需要此配置。
    """
    
    enabled: bool = Field(
        default=True,
        description="是否在 API 服务中启用内嵌调度器"
    )
    schedule_modules: list[str] = Field(
        default_factory=list,
        description="定时任务模块列表。为空时自动发现 schedules 模块"
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
        default="aury.events",
        description="事件交换机名称"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="EVENT_",
        case_sensitive=False,
    )


class MessageQueueSettings(BaseSettings):
    """消息队列配置。
    
    环境变量前缀: MQ_
    示例: MQ_BROKER_URL, MQ_DEFAULT_QUEUE, MQ_SERIALIZER
    
    与 Task（任务队列）的区别：
    - Task: 基于 Dramatiq，用于异步任务处理（API + Worker 模式）
    - MQ: 通用消息队列，用于服务间通信、事件驱动架构
    
    支持的后端（通过 Kombu）：
    - Redis: redis://localhost:6379/0
    - RabbitMQ: amqp://guest:guest@localhost:5672//
    - Amazon SQS: sqs://
    """
    
    enabled: bool = Field(
        default=False,
        description="是否启用消息队列组件"
    )
    broker_url: str | None = Field(
        default=None,
        description="消息队列代理 URL"
    )
    default_queue: str = Field(
        default="default",
        description="默认队列名称"
    )
    serializer: str = Field(
        default="json",
        description="序列化方式（json/pickle/msgpack）"
    )
    prefetch_count: int = Field(
        default=1,
        description="预取消息数量"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="MQ_",
        case_sensitive=False,
    )


class MigrationSettings(BaseSettings):
    """数据库迁移配置。
    
    环境变量前缀: MIGRATION_
    示例: MIGRATION_CONFIG_PATH, MIGRATION_SCRIPT_LOCATION, MIGRATION_MODEL_MODULES
    """
    
    config_path: str = Field(
        default="alembic.ini",
        description="Alembic 配置文件路径"
    )
    script_location: str = Field(
        default="migrations",
        description="Alembic 迁移脚本目录"
    )
    model_modules: list[str] = Field(
        default_factory=lambda: [
            "models",
            "app.models",
            "app.**.models",
        ],
        description="模型模块列表（用于自动检测变更）。支持通配符: * 和 **。"
    )
    auto_create: bool = Field(
        default=True,
        description="是否自动创建迁移配置和目录"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="MIGRATION_",
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
    
    用于配置 Aury 框架的默认健康检查端点。
    注意：此配置仅用于框架内置的健康检查端点，不影响服务自身的健康检查端点。
    
    环境变量前缀: HEALTH_CHECK_
    示例: HEALTH_CHECK_PATH, HEALTH_CHECK_ENABLED
    """
    
    path: str = Field(
        default="/api/health",
        description="健康检查端点路径（默认: /api/health）"
    )
    enabled: bool = Field(
        default=True,
        description="是否启用 Aury 默认健康检查端点"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="HEALTH_CHECK_",
        case_sensitive=False,
    )


class AdminAuthSettings(BaseSettings):
    """管理后台认证配置。

    环境变量前缀: ADMIN_AUTH_
    示例: ADMIN_AUTH_MODE, ADMIN_AUTH_SECRET_KEY, ADMIN_AUTH_BASIC_USERNAME

    说明：
    - 内置模式仅保证 basic / bearer 开箱即用
    - jwt/custom 推荐由用户自定义 backend 实现（见 ADMIN_AUTH_BACKEND）
    """

    mode: Literal["none", "basic", "bearer", "jwt", "custom"] = Field(
        default="basic",
        description="认证模式 (none/basic/bearer/jwt/custom)",
    )

    # SQLAdmin AuthenticationBackend 需要 secret_key 用于 session 签名
    secret_key: str | None = Field(
        default=None,
        description="Session 签名密钥（生产环境必须配置）",
    )

    # basic：用户名/密码（用于 SQLAdmin 登录页）
    basic_username: str | None = Field(default=None, description="Basic 登录用户名")
    basic_password: str | None = Field(default=None, description="Basic 登录密码")

    # bearer：token 白名单（支持 Authorization: Bearer <token>，也支持登录页使用 token）
    bearer_tokens: list[str] = Field(default_factory=list, description="Bearer token 白名单")

    # custom/jwt：用户自定义认证后端（动态导入）
    backend: str | None = Field(
        default=None,
        description='自定义认证后端导入路径，如 "yourpkg.admin_auth:backend"',
    )

    model_config = SettingsConfigDict(
        env_prefix="ADMIN_AUTH_",
        case_sensitive=False,
    )


class AdminConsoleSettings(BaseSettings):
    """SQLAdmin 管理后台配置。

    环境变量前缀: ADMIN_
    示例: ADMIN_ENABLED, ADMIN_PATH, ADMIN_DATABASE_URL
    """

    enabled: bool = Field(default=False, description="是否启用管理后台")

    path: str = Field(
        default="/api/admin-console",
        description="管理后台路径（默认 /api/admin-console）",
    )

    # SQLAdmin 目前通常要求同步 SQLAlchemy Engine；此处允许单独指定同步数据库 URL
    database_url: str | None = Field(
        default=None,
        description="管理后台专用数据库连接（同步 URL，可覆盖自动推导）",
    )

    # 显式指定项目侧 admin 模块路径（可选）
    views_module: str | None = Field(
        default=None,
        description="项目侧 admin-console 模块（用于注册 views/auth），如 app.admin_console",
    )

    auth: AdminAuthSettings = Field(default_factory=AdminAuthSettings, description="管理后台认证配置")

    model_config = SettingsConfigDict(
        env_prefix="ADMIN_",
        case_sensitive=False,
    )


class BaseConfig(BaseSettings):
    """基础配置类。
    
    所有应用配置的基类，提供通用配置项。
    初始化时自动从 .env 文件加载环境变量，然后由 pydantic-settings 读取环境变量。
    
    多实例配置:
    框架支持多种组件的多实例配置，使用统一的环境变量格式:
        {PREFIX}_{INSTANCE}_{FIELD}=value
    
    示例:
        DATABASE_DEFAULT_URL=postgresql://main...
        DATABASE_ANALYTICS_URL=postgresql://analytics...
        CACHE_DEFAULT_BACKEND=redis
        CACHE_DEFAULT_URL=redis://localhost:6379/1
        MQ_DEFAULT_URL=redis://localhost:6379/2
        EVENT_DEFAULT_BACKEND=memory
    
    注意：Application 层配置完全独立，不依赖 Infrastructure 层。
    """
    
    # 多实例配置缓存
    _databases: dict[str, DatabaseInstanceConfig] | None = None
    _caches: dict[str, CacheInstanceConfig] | None = None
    _storages: dict[str, StorageInstanceConfig] | None = None
    _channels: dict[str, ChannelInstanceConfig] | None = None
    _mqs: dict[str, MQInstanceConfig] | None = None
    _events: dict[str, EventInstanceConfig] | None = None
    
    def __init__(self, _env_file: str | Path = ".env", **kwargs) -> None:
        """初始化配置。
        
        Args:
            _env_file: .env 文件路径，默认为当前目录下的 .env
            **kwargs: 其他配置参数
        """
        # 在 pydantic-settings 初始化之前加载 .env 文件
        _load_env_file(_env_file)
        super().__init__(**kwargs)
    
    # ========== 服务器与网络 ==========
    # 服务器配置
    server: ServerSettings = Field(default_factory=ServerSettings)
    
    # CORS配置
    cors: CORSSettings = Field(default_factory=CORSSettings)
    
    # 日志配置
    log: LogSettings = Field(default_factory=LogSettings)
    
    # 健康检查配置
    health_check: HealthCheckSettings = Field(default_factory=HealthCheckSettings)

    # 管理后台配置（SQLAdmin）
    admin: AdminConsoleSettings = Field(default_factory=AdminConsoleSettings)
    
    # ========== 数据与缓存 ==========
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    
    # 迁移配置
    migration: MigrationSettings = Field(default_factory=MigrationSettings)
    
    # ========== 服务编排 ==========
    # 服务配置
    service: ServiceSettings = Field(default_factory=ServiceSettings)
    
    # 调度器配置
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    
    # ========== 异步与事件 ==========
    task: TaskSettings = Field(default_factory=TaskSettings)
    event: EventSettings = Field(default_factory=EventSettings)
    
    # ========== 微服务通信 ==========
    # RPC 客户端配置（调用其他服务）
    rpc_client: RPCClientSettings = Field(default_factory=RPCClientSettings)
    
    # RPC 服务配置（当前服务注册）
    rpc_service: RPCServiceSettings = Field(default_factory=RPCServiceSettings)
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )
    
    # ========== 多实例配置访问方法 ==========
    
    def get_databases(self) -> dict[str, DatabaseInstanceConfig]:
        """获取所有数据库实例配置。
        
        从环境变量解析 DATABASE_{INSTANCE}_{FIELD} 格式的配置。
        如果没有配置多实例，返回从单实例配置转换的 default 实例。
        """
        if self._databases is None:
            loader = MultiInstanceConfigLoader("DATABASE", DatabaseInstanceConfig)
            self._databases = loader.load()
            if not self._databases:
                self._databases = {
                    "default": DatabaseInstanceConfig(
                        url=self.database.url,
                        echo=self.database.echo,
                        pool_size=self.database.pool_size,
                        max_overflow=self.database.max_overflow,
                        pool_recycle=self.database.pool_recycle,
                        pool_timeout=self.database.pool_timeout,
                        pool_pre_ping=self.database.pool_pre_ping,
                    )
                }
        return self._databases
    
    def get_caches(self) -> dict[str, CacheInstanceConfig]:
        """获取所有缓存实例配置。
        
        从环境变量解析 CACHE_{INSTANCE}_{FIELD} 格式的配置。
        如果没有配置多实例，返回从单实例配置转换的 default 实例。
        """
        if self._caches is None:
            loader = MultiInstanceConfigLoader("CACHE", CacheInstanceConfig)
            self._caches = loader.load()
            if not self._caches:
                self._caches = {
                    "default": CacheInstanceConfig(
                        backend=self.cache.cache_type,
                        url=self.cache.url,
                        max_size=self.cache.max_size,
                    )
                }
        return self._caches
    
    def get_storages(self) -> dict[str, StorageInstanceConfig]:
        """获取所有存储实例配置。
        
        从环境变量解析 STORAGE_{INSTANCE}_{FIELD} 格式的配置。
        如果没有配置多实例，返回从单实例配置转换的 default 实例。
        """
        if self._storages is None:
            loader = MultiInstanceConfigLoader("STORAGE", StorageInstanceConfig)
            self._storages = loader.load()
            if not self._storages:
                self._storages = {
                    "default": StorageInstanceConfig(
                        backend=self.storage.type,
                        access_key_id=self.storage.access_key_id,
                        access_key_secret=self.storage.access_key_secret,
                        endpoint=self.storage.endpoint,
                        region=self.storage.region,
                        bucket_name=self.storage.bucket_name,
                        base_path=self.storage.base_path,
                    )
                }
        return self._storages
    
    def get_channels(self) -> dict[str, ChannelInstanceConfig]:
        """获取所有通道实例配置。
        
        从环境变量解析 CHANNEL_{INSTANCE}_{FIELD} 格式的配置。
        """
        if self._channels is None:
            loader = MultiInstanceConfigLoader("CHANNEL", ChannelInstanceConfig)
            self._channels = loader.load()
        return self._channels
    
    def get_mqs(self) -> dict[str, MQInstanceConfig]:
        """获取所有消息队列实例配置。
        
        从环境变量解析 MQ_{INSTANCE}_{FIELD} 格式的配置。
        """
        if self._mqs is None:
            loader = MultiInstanceConfigLoader("MQ", MQInstanceConfig)
            self._mqs = loader.load()
        return self._mqs
    
    def get_events(self) -> dict[str, EventInstanceConfig]:
        """获取所有事件总线实例配置。
        
        从环境变量解析 EVENT_{INSTANCE}_{FIELD} 格式的配置。
        如果没有配置多实例，返回从单实例配置转换的 default 实例。
        """
        if self._events is None:
            loader = MultiInstanceConfigLoader("EVENT", EventInstanceConfig)
            self._events = loader.load()
            if not self._events and self.event.broker_url:
                self._events = {
                    "default": EventInstanceConfig(
                        backend="redis" if "redis" in (self.event.broker_url or "") else "rabbitmq",
                        url=self.event.broker_url,
                    )
                }
        return self._events
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境。"""
        return self.log.level.upper() == "ERROR"


__all__ = [
    # 配置类
    "AdminAuthSettings",
    "AdminConsoleSettings",
    "BaseConfig",
    "CORSSettings",
    # 多实例配置类
    "CacheInstanceConfig",
    "CacheSettings",
    "ChannelInstanceConfig",
    "DatabaseInstanceConfig",
    "DatabaseSettings",
    "EventInstanceConfig",
    "EventSettings",
    "HealthCheckSettings",
    "LogSettings",
    "MQInstanceConfig",
    "MessageQueueSettings",
    "MigrationSettings",
    "RPCClientSettings",
    "RPCServiceSettings",
    "SchedulerSettings",
    "ServerSettings",
    "ServiceSettings",
    "StorageInstanceConfig",
    "StorageSettings",
    "TaskSettings",
]


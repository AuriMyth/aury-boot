"""共享配置基类。

提供所有应用共享的基础配置结构。
使用 pydantic-settings 进行分层分级配置管理。

注意：Application 层的配置是独立的，不依赖 Infrastructure 层。
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_env_file(env_file: str | Path) -> bool:
    """加载 .env 文件到环境变量。"""
    return load_dotenv(env_file, override=True)


class DatabaseSettings(BaseSettings):
    """数据库配置。
    
    环境变量前缀: DATABASE_
    示例: DATABASE_URL, DATABASE_ECHO, DATABASE_POOL_SIZE
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
    role_session_name: str = Field(default="aurimyth-storage", description="STS会话名")
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

    独立调度器通过 `aum scheduler` 命令运行，不需要配置 SERVICE_TYPE。
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
    
    独立调度器通过 `aum scheduler` 命令运行，不需要此配置。
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
        default="aurimyth.events",
        description="事件交换机名称"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="EVENT_",
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
    
    用于配置 AuriMyth 框架的默认健康检查端点。
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
        description="是否启用 AuriMyth 默认健康检查端点"
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
    
    注意：Application 层配置完全独立，不依赖 Infrastructure 层。
    """
    
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
    # 数据库配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    
    # 缓存配置
    cache: CacheSettings = Field(default_factory=CacheSettings)

    # 对象存储配置（接入用；storage SDK 本身不读取 env）
    storage: StorageSettings = Field(default_factory=StorageSettings)
    
    # 迁移配置
    migration: MigrationSettings = Field(default_factory=MigrationSettings)
    
    # ========== 服务编排 ==========
    # 服务配置
    service: ServiceSettings = Field(default_factory=ServiceSettings)
    
    # 调度器配置
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    
    # ========== 异步与事件 ==========
    # 任务队列配置
    task: TaskSettings = Field(default_factory=TaskSettings)
    
    # 事件总线配置
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
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境。"""
        return self.log.level.upper() == "ERROR"


__all__ = [
    "AdminAuthSettings",
    "AdminConsoleSettings",
    "BaseConfig",
    "CORSSettings",
    "CacheSettings",
    "DatabaseSettings",
    "EventSettings",
    "HealthCheckSettings",
    "LogSettings",
    "MigrationSettings",
    "RPCClientSettings",
    "RPCServiceSettings",
    "SchedulerSettings",
    "ServerSettings",
    "ServiceSettings",
    "StorageSettings",
    "TaskSettings",
]


# =============================================================================
# {project_name} 环境变量配置
# =============================================================================
# 复制此文件为 .env 并根据实际情况修改
# 所有配置项均有默认值，只需取消注释并修改需要覆盖的项

# =============================================================================
# 服务配置 (SERVICE_)
# =============================================================================
# 服务名称，用于日志目录区分
SERVICE_NAME={project_name_snake}
# 服务类型: api / worker
# SERVICE_TYPE=api

# =============================================================================
# 服务器配置 (SERVER_)
# =============================================================================
# SERVER_HOST=127.0.0.1
# SERVER_PORT=8000
# 工作进程数（生产环境建议设为 CPU 核心数）
# SERVER_WORKERS=1
# 是否启用热重载（生产环境应设为 false）
# SERVER_RELOAD=true

# =============================================================================
# 数据库配置 (DATABASE_)
# =============================================================================
# 支持多实例配置，格式: DATABASE_{{INSTANCE}}_{{FIELD}}
# 默认实例 (default):
# DATABASE_URL=sqlite+aiosqlite:///./dev.db
# DATABASE_DEFAULT_URL=sqlite+aiosqlite:///./dev.db
# PostgreSQL: postgresql+asyncpg://user:pass@localhost:5432/{project_name_snake}
# MySQL: mysql+aiomysql://user:pass@localhost:3306/{project_name_snake}

# 连接池大小
# DATABASE_POOL_SIZE=5
# 连接池最大溢出连接数
# DATABASE_MAX_OVERFLOW=10
# 连接回收时间（秒）
# DATABASE_POOL_RECYCLE=3600
# 获取连接超时时间（秒）
# DATABASE_POOL_TIMEOUT=30
# 是否在获取连接前 PING
# DATABASE_POOL_PRE_PING=true
# 是否输出 SQL 语句（调试用）
# DATABASE_ECHO=false

# 多实例示例 (readonly):
# DATABASE_READONLY_URL=postgresql+asyncpg://user:pass@replica:5432/{project_name_snake}
# DATABASE_READONLY_POOL_SIZE=10

# =============================================================================
# 缓存配置 (CACHE_)
# =============================================================================
# 支持多实例配置，格式: CACHE_{{INSTANCE}}_{{FIELD}}
# 缓存类型: memory / redis / memcached
# CACHE_TYPE=memory
# CACHE_URL=redis://localhost:6379/0
# 内存缓存最大大小
# CACHE_MAX_SIZE=1000
# 默认 TTL（秒）
# CACHE_DEFAULT_TTL=300
#
# 多实例示例 (session):
# CACHE_SESSION_TYPE=redis
# CACHE_SESSION_URL=redis://localhost:6379/2

# =============================================================================
# 日志配置 (LOG_)
# =============================================================================
# 日志级别: DEBUG / INFO / WARNING / ERROR / CRITICAL
# LOG_LEVEL=INFO
# 日志文件目录
# LOG_DIR=logs
# 日志文件轮转时间 (HH:MM 格式)
# LOG_ROTATION_TIME=00:00
# 日志文件轮转大小阈值
# LOG_ROTATION_SIZE=100 MB
# 日志文件保留天数
# LOG_RETENTION_DAYS=7
# 是否启用日志文件轮转
# LOG_ENABLE_FILE_ROTATION=true
# 是否输出日志到控制台
# LOG_ENABLE_CONSOLE=true

# =============================================================================
# 健康检查配置 (HEALTH_CHECK_)
# =============================================================================
# 健康检查端点路径
# HEALTH_CHECK_PATH=/api/health
# 是否启用健康检查端点
# HEALTH_CHECK_ENABLED=true

# =============================================================================
# 管理后台配置 (ADMIN_) - SQLAdmin Admin Console
# =============================================================================
# 是否启用管理后台（生产建议仅内网或配合反向代理）
# ADMIN_ENABLED=false
# 管理后台路径（默认 /api/admin-console，避免与业务 URL 冲突）
# ADMIN_PATH=/api/admin-console
#
# SQLAdmin 通常要求同步 SQLAlchemy Engine：
# - 若 DATABASE_URL 使用的是异步驱动（如 postgresql+asyncpg），建议显式提供同步 URL 覆盖
# ADMIN_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/{project_name_snake}
#
# 可选：显式指定项目侧模块（用于注册 views/auth）
# ADMIN_VIEWS_MODULE={project_name_snake}.admin_console
#
# 认证（默认建议 basic / bearer；jwt/custom 通常需要自定义 backend）
# ADMIN_AUTH_MODE=basic
# ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
#
# basic：登录页用户名/密码
# ADMIN_AUTH_BASIC_USERNAME=admin
# ADMIN_AUTH_BASIC_PASSWORD=change_me
#
# bearer：token 白名单（也支持在登录页输入 token）
# ADMIN_AUTH_BEARER_TOKENS=["change_me_token"]
#
# custom/jwt：自定义认证后端（动态导入）
# ADMIN_AUTH_BACKEND=yourpkg.admin_auth:backend

# =============================================================================
# CORS 配置 (CORS_)
# =============================================================================
# 允许的 CORS 源（生产环境应设置具体域名）
# CORS_ORIGINS=["*"]
# 是否允许 CORS 凭据
# CORS_ALLOW_CREDENTIALS=true
# 允许的 CORS 方法
# CORS_ALLOW_METHODS=["*"]
# 允许的 CORS 头
# CORS_ALLOW_HEADERS=["*"]

# =============================================================================
# 调度器配置 (SCHEDULER_)
# =============================================================================
# 是否在 API 服务中启用内嵌调度器
# SCHEDULER_ENABLED=true
# 定时任务模块列表（为空时自动发现 schedules 模块）
# SCHEDULER_SCHEDULE_MODULES=[]

# =============================================================================
# 任务队列配置 (TASK_)
# =============================================================================
# 任务队列代理 URL（如 Redis 或 RabbitMQ）
# TASK_BROKER_URL=redis://localhost:6379/1
# 最大重试次数
# TASK_MAX_RETRIES=3
# 任务超时时间（秒）
# TASK_TIMEOUT=3600

# =============================================================================
# 流式通道配置 (CHANNEL_) - SSE/实时通信
# =============================================================================
# 支持多实例配置，格式: CHANNEL_{{INSTANCE}}_{{FIELD}}
# 后端类型: memory / redis
# CHANNEL_BACKEND=memory
# CHANNEL_DEFAULT_BACKEND=memory
#
# Redis 后端配置:
# CHANNEL_DEFAULT_BACKEND=redis
# CHANNEL_DEFAULT_URL=redis://localhost:6379/3
# CHANNEL_DEFAULT_KEY_PREFIX=channel:
# CHANNEL_DEFAULT_TTL=86400
#
# 多实例示例 (notifications):
# CHANNEL_NOTIFICATIONS_BACKEND=redis
# CHANNEL_NOTIFICATIONS_URL=redis://localhost:6379/3

# =============================================================================
# 消息队列配置 (MQ_)
# =============================================================================
# 支持多实例配置，格式: MQ_{{INSTANCE}}_{{FIELD}}
# 后端类型: redis / rabbitmq
# MQ_BACKEND=redis
# MQ_DEFAULT_BACKEND=redis
#
# Redis 后端配置:
# MQ_DEFAULT_URL=redis://localhost:6379/4
# MQ_DEFAULT_MAX_CONNECTIONS=10
#
# RabbitMQ 后端配置:
# MQ_DEFAULT_BACKEND=rabbitmq
# MQ_DEFAULT_URL=amqp://guest:guest@localhost:5672/
# MQ_DEFAULT_PREFETCH_COUNT=10
# MQ_DEFAULT_HEARTBEAT=60
#
# 多实例示例 (orders):
# MQ_ORDERS_BACKEND=rabbitmq
# MQ_ORDERS_URL=amqp://guest:guest@localhost:5672/orders

# =============================================================================
# 事件总线配置 (EVENT_)
# =============================================================================
# 支持多实例配置，格式: EVENT_{{INSTANCE}}_{{FIELD}}
# 后端类型: memory / redis / rabbitmq
# EVENT_BACKEND=memory
# EVENT_DEFAULT_BACKEND=memory
#
# Redis Pub/Sub 后端:
# EVENT_DEFAULT_BACKEND=redis
# EVENT_DEFAULT_URL=redis://localhost:6379/5
# EVENT_DEFAULT_KEY_PREFIX=events:
#
# RabbitMQ 后端:
# EVENT_DEFAULT_BACKEND=rabbitmq
# EVENT_DEFAULT_URL=amqp://guest:guest@localhost:5672/
# EVENT_EXCHANGE_NAME=aury.events
# EVENT_DEFAULT_EXCHANGE_TYPE=topic
#
# 多实例示例 (domain):
# EVENT_DOMAIN_BACKEND=rabbitmq
# EVENT_DOMAIN_URL=amqp://guest:guest@localhost:5672/
# EVENT_DOMAIN_EXCHANGE_NAME=domain.events

# =============================================================================
# 数据库迁移配置 (MIGRATION_)
# =============================================================================
# Alembic 配置文件路径
# MIGRATION_CONFIG_PATH=alembic.ini
# Alembic 迁移脚本目录
# MIGRATION_SCRIPT_LOCATION=migrations
# 是否自动创建迁移配置和目录
# MIGRATION_AUTO_CREATE=true

# =============================================================================
# 对象存储配置 (STORAGE_) - 基于 aury-sdk-storage
# =============================================================================
# 是否启用存储组件
# STORAGE_ENABLED=true
# 存储类型: local / s3 / cos / oss
# STORAGE_TYPE=local
#
# 本地存储（开发环境）
# STORAGE_BASE_PATH=./storage
#
# S3/COS/OSS 通用配置
# STORAGE_ACCESS_KEY_ID=AKIDxxxxx
# STORAGE_ACCESS_KEY_SECRET=xxxxx
# STORAGE_SESSION_TOKEN=
# STORAGE_ENDPOINT=https://cos.ap-guangzhou.myqcloud.com
# STORAGE_REGION=ap-guangzhou
# STORAGE_BUCKET_NAME=my-bucket-1250000000
# STORAGE_ADDRESSING_STYLE=virtual
#
# STS AssumeRole（可选，服务端自动刷新凭证）
# STORAGE_ROLE_ARN=
# STORAGE_ROLE_SESSION_NAME=aury-storage
# STORAGE_EXTERNAL_ID=
# STORAGE_STS_ENDPOINT=
# STORAGE_STS_REGION=
# STORAGE_STS_DURATION_SECONDS=3600

# =============================================================================
# RPC 客户端配置 (RPC_CLIENT_)
# =============================================================================
# 服务地址映射 {{service_name: url}}
# RPC_CLIENT_SERVICES={{"user-service": "http://localhost:8001"}}
# 默认超时时间（秒）
# RPC_CLIENT_DEFAULT_TIMEOUT=30
# 默认重试次数
# RPC_CLIENT_DEFAULT_RETRY_TIMES=3
# DNS 解析使用的协议
# RPC_CLIENT_DNS_SCHEME=http
# DNS 解析默认端口
# RPC_CLIENT_DNS_PORT=80
# 是否使用 DNS 回退（K8s/Docker Compose 自动 DNS）
# RPC_CLIENT_USE_DNS_FALLBACK=true

# =============================================================================
# RPC 服务注册配置 (RPC_SERVICE_)
# =============================================================================
# 服务名称（用于注册）
# RPC_SERVICE_NAME={project_name_snake}
# 服务地址（用于注册）
# RPC_SERVICE_URL=http://localhost:8000
# 健康检查 URL（用于注册）
# RPC_SERVICE_HEALTH_CHECK_URL=http://localhost:8000/api/health
# 是否自动注册到服务注册中心
# RPC_SERVICE_AUTO_REGISTER=false

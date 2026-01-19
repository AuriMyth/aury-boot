
# =============================================================================
# 流式通道配置 (CHANNEL__) - SSE/实时通信
# =============================================================================
# 基于 Broadcaster 库，通过 URL scheme 切换后端
# 支持: memory:// | redis://host:port/db | kafka://host:port | postgres://...
#
# 单实例配置:
# CHANNEL__BACKEND=broadcaster
# CHANNEL__URL=memory://
# 分布式: CHANNEL__URL=redis://localhost:6379/3
#
# 多实例配置 (格式: CHANNEL__{{INSTANCE}}__{{FIELD}}):
# CHANNEL__SSE__BACKEND=broadcaster
# CHANNEL__SSE__URL=memory://
# CHANNEL__NOTIFICATION__BACKEND=broadcaster
# CHANNEL__NOTIFICATION__URL=redis://localhost:6379/3

# =============================================================================
# 消息队列配置 (MQ__)
# =============================================================================
# 单实例配置:
# MQ__ENABLED=false
# MQ__BROKER_URL=redis://localhost:6379/4

# 多实例配置 (格式: MQ__{{INSTANCE}}__{{FIELD}}):
# MQ__DEFAULT__BACKEND=redis
# MQ__DEFAULT__URL=redis://localhost:6379/4
# MQ__DEFAULT__MAX_CONNECTIONS=10
#
# RabbitMQ 后端:
# MQ__ORDERS__BACKEND=rabbitmq
# MQ__ORDERS__URL=amqp://guest:guest@localhost:5672/orders
# MQ__ORDERS__PREFETCH_COUNT=10

# =============================================================================
# 事件总线配置 (EVENT__)
# =============================================================================
# 基于 Broadcaster 库，通过 URL scheme 切换后端
# 支持: memory:// | redis://host:port/db | kafka://host:port | postgres://...
# RabbitMQ 需使用 backend=rabbitmq
#
# 单实例配置:
# EVENT__BACKEND=broadcaster
# EVENT__URL=memory://
# 分布式: EVENT__URL=redis://localhost:6379/5
#
# 多实例配置 (格式: EVENT__{{INSTANCE}}__{{FIELD}}):
# EVENT__DEFAULT__BACKEND=broadcaster
# EVENT__DEFAULT__URL=memory://
# EVENT__DISTRIBUTED__BACKEND=broadcaster
# EVENT__DISTRIBUTED__URL=redis://localhost:6379/5
#
# RabbitMQ 后端 (复杂消息场景):
# EVENT__DOMAIN__BACKEND=rabbitmq
# EVENT__DOMAIN__URL=amqp://guest:guest@localhost:5672/
# EVENT__DOMAIN__EXCHANGE_NAME=domain.events

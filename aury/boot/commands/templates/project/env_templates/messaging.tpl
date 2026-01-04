
# =============================================================================
# 流式通道配置 (CHANNEL__) - SSE/实时通信
# =============================================================================
# 多实例配置 (格式: CHANNEL__{{INSTANCE}}__{{FIELD}}):
# CHANNEL__DEFAULT__BACKEND=memory
# CHANNEL__SHARED__BACKEND=redis
# CHANNEL__SHARED__URL=redis://localhost:6379/3
# CHANNEL__SHARED__KEY_PREFIX=channel:
# CHANNEL__SHARED__TTL=86400

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
# 单实例配置:
# EVENT__BROKER_URL=
# EVENT__EXCHANGE_NAME=aury.events

# 多实例配置 (格式: EVENT__{{INSTANCE}}__{{FIELD}}):
# EVENT__DEFAULT__BACKEND=memory
# EVENT__DISTRIBUTED__BACKEND=redis
# EVENT__DISTRIBUTED__URL=redis://localhost:6379/5
# EVENT__DISTRIBUTED__KEY_PREFIX=events:
#
# RabbitMQ 后端:
# EVENT__DOMAIN__BACKEND=rabbitmq
# EVENT__DOMAIN__URL=amqp://guest:guest@localhost:5672/
# EVENT__DOMAIN__EXCHANGE_NAME=domain.events
# EVENT__DOMAIN__EXCHANGE_TYPE=topic

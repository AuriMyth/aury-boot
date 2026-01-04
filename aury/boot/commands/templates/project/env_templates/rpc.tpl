
# =============================================================================
# RPC 客户端配置 (RPC_CLIENT__)
# =============================================================================
# 服务地址映射 {service_name: url}
# RPC_CLIENT__SERVICES={{"user-service": "http://localhost:8001"}}
# 默认超时时间（秒）
# RPC_CLIENT__DEFAULT_TIMEOUT=30
# 默认重试次数
# RPC_CLIENT__DEFAULT_RETRY_TIMES=3
# DNS 解析使用的协议
# RPC_CLIENT__DNS_SCHEME=http
# DNS 解析默认端口
# RPC_CLIENT__DNS_PORT=80
# 是否使用 DNS 回退（K8s/Docker Compose 自动 DNS）
# RPC_CLIENT__USE_DNS_FALLBACK=true

# =============================================================================
# RPC 服务注册配置 (RPC_SERVICE__)
# =============================================================================
# 服务名称（用于注册）
# RPC_SERVICE__NAME={project_name_snake}
# 服务地址（用于注册）
# RPC_SERVICE__URL=http://localhost:8000
# 健康检查 URL（用于注册）
# RPC_SERVICE__HEALTH_CHECK_URL=http://localhost:8000/api/health
# 是否自动注册到服务注册中心
# RPC_SERVICE__AUTO_REGISTER=false

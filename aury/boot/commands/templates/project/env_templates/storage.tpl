
# =============================================================================
# 数据库迁移配置 (MIGRATION__)
# =============================================================================
# Alembic 配置文件路径
# MIGRATION__CONFIG_PATH=alembic.ini
# Alembic 迁移脚本目录
# MIGRATION__SCRIPT_LOCATION=migrations
# 是否自动创建迁移配置和目录
# MIGRATION__AUTO_CREATE=true

# =============================================================================
# 对象存储配置 (STORAGE__) - 基于 aury-sdk-storage
# =============================================================================
# 是否启用存储组件
# STORAGE__ENABLED=true
# 存储类型: local / s3 / cos / oss
# STORAGE__TYPE=local
#
# 本地存储（开发环境）
# STORAGE__BASE_PATH=./storage
#
# S3/COS/OSS 通用配置
# STORAGE__ACCESS_KEY_ID=AKIDxxxxx
# STORAGE__ACCESS_KEY_SECRET=xxxxx
# STORAGE__SESSION_TOKEN=
# STORAGE__ENDPOINT=https://cos.ap-guangzhou.myqcloud.com
# STORAGE__REGION=ap-guangzhou
# STORAGE__BUCKET_NAME=my-bucket-1250000000
# STORAGE__ADDRESSING_STYLE=virtual
#
# STS AssumeRole（可选，服务端自动刷新凭证）
# STORAGE__ROLE_ARN=
# STORAGE__ROLE_SESSION_NAME=aury-storage
# STORAGE__EXTERNAL_ID=
# STORAGE__STS_ENDPOINT=
# STORAGE__STS_REGION=
# STORAGE__STS_DURATION_SECONDS=3600

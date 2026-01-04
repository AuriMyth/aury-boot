
# =============================================================================
# 缓存配置 (CACHE__)
# =============================================================================
# 单实例配置:
# CACHE__CACHE_TYPE=memory
# CACHE__URL=redis://localhost:6379/0
# CACHE__MAX_SIZE=1000

# 多实例配置 (格式: CACHE__{{INSTANCE}}__{{FIELD}}):
# CACHE__DEFAULT__BACKEND=memory
# CACHE__DEFAULT__MAX_SIZE=1000
# CACHE__SESSION__BACKEND=redis
# CACHE__SESSION__URL=redis://localhost:6379/2

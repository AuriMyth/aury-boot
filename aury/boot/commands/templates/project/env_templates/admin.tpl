
# =============================================================================
# 健康检查配置 (HEALTH_CHECK__)
# =============================================================================
# 健康检查端点路径
# HEALTH_CHECK__PATH=/api/health
# 是否启用健康检查端点
# HEALTH_CHECK__ENABLED=true

# =============================================================================
# CORS 配置 (CORS__)
# =============================================================================
# 允许的 CORS 源（生产环境应设置具体域名）
# CORS__ORIGINS=["*"]
# 是否允许 CORS 凭据
# CORS__ALLOW_CREDENTIALS=true
# 允许的 CORS 方法
# CORS__ALLOW_METHODS=["*"]
# 允许的 CORS 头
# CORS__ALLOW_HEADERS=["*"]

# =============================================================================
# 管理后台配置 (ADMIN__) - SQLAdmin Admin Console
# =============================================================================
# 是否启用管理后台（生产建议仅内网或配合反向代理）
# ADMIN__ENABLED=false
# 管理后台路径（默认 /api/admin-console，避免与业务 URL 冲突）
# ADMIN__PATH=/api/admin-console
#
# SQLAdmin 通常要求同步 SQLAlchemy Engine：
# - 若 DATABASE__URL 使用的是异步驱动（如 postgresql+asyncpg），建议显式提供同步 URL 覆盖
# ADMIN__DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/{project_name_snake}
#
# 可选：显式指定项目侧模块（用于注册 views/auth）
# ADMIN__VIEWS_MODULE={project_name_snake}.admin_console
#
# 认证配置 (嵌套格式: ADMIN__AUTH__{{FIELD}})
# ADMIN__AUTH__MODE=basic
# ADMIN__AUTH__SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
#
# basic：登录页用户名/密码
# ADMIN__AUTH__BASIC_USERNAME=admin
# ADMIN__AUTH__BASIC_PASSWORD=change_me
#
# bearer：token 白名单（也支持在登录页输入 token）
# ADMIN__AUTH__BEARER_TOKENS=["change_me_token"]
#
# custom/jwt：自定义认证后端（动态导入）
# ADMIN__AUTH__BACKEND=yourpkg.admin_auth:backend

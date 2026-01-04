
# =============================================================================
# 数据库配置 (DATABASE__)
# =============================================================================
# 单实例配置:
# DATABASE__URL=sqlite+aiosqlite:///./dev.db
# PostgreSQL: postgresql+asyncpg://user:pass@localhost:5432/{project_name_snake}
# MySQL: mysql+aiomysql://user:pass@localhost:3306/{project_name_snake}

# 连接池配置
# DATABASE__POOL_SIZE=5
# DATABASE__MAX_OVERFLOW=10
# DATABASE__POOL_RECYCLE=3600
# DATABASE__POOL_TIMEOUT=30
# DATABASE__POOL_PRE_PING=true
# DATABASE__ECHO=false

# 多实例配置 (格式: DATABASE__{{INSTANCE}}__{{FIELD}}):
# DATABASE__DEFAULT__URL=postgresql+asyncpg://user:pass@localhost:5432/{project_name_snake}
# DATABASE__DEFAULT__POOL_SIZE=5
# DATABASE__READONLY__URL=postgresql+asyncpg://user:pass@replica:5432/{project_name_snake}
# DATABASE__READONLY__POOL_SIZE=10

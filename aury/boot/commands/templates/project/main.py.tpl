"""应用入口。

使用方式：
    # 开发模式
    aury server dev

    # 生产模式
    aury server prod
"""

from aury.boot.application.app.base import FoundationApp

from {import_prefix}api import router as api_router
from {import_prefix}config import AppConfig

# 创建配置
config = AppConfig()

# 创建应用
#
# 框架默认注册端点：
#   - GET /api/health  健康检查（检查数据库/缓存状态）
#
# 可通过环境变量配置：
#   - HEALTH_CHECK_PATH: 健康检查路径（默认 /api/health）
#   - HEALTH_CHECK_ENABLED: 是否启用（默认 true）
#
app = FoundationApp(
    title="{project_name}",
    version="0.1.0",
    description="{project_name} - 基于 Aury Boot",
    config=config,
)

# 注册 API 路由
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

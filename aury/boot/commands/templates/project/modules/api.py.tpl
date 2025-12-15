"""API 路由模块。

路由结构：
    api/
    ├── __init__.py   # 本文件，汇总路由
    ├── user.py       # prefix="/v1/users"
    └── article.py    # prefix="/v1/articles"

main.py 中注册：app.include_router(api_router, prefix="/api")
最终路径：/api/v1/users, /api/v1/articles
"""

from fastapi import APIRouter

router = APIRouter()

# 注册子路由（示例）
# from . import example
# router.include_router(example.router)

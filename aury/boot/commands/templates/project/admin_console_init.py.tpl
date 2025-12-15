"""管理后台（Admin Console）项目侧扩展点。

说明：
- 框架会在启用 ADMIN_ENABLED=true 时自动尝试加载本模块，并调用 register_admin(admin)
- 用于注册 SQLAdmin 的 ModelView（展示/编辑你的业务模型）
- 认证默认推荐使用环境变量（basic/bearer）；如需深度自定义，可在本模块实现 register_admin_auth(config)
  （注意：一旦定义 register_admin_auth，会覆盖内置认证逻辑）
"""

from __future__ import annotations


def register_admin(admin) -> None:
    """注册 SQLAdmin Views。

    你可以在这里添加你的 ModelView：

    ```python
    from sqladmin import ModelView
    from {import_prefix}models.user import User

    class UserAdmin(ModelView, model=User):
        column_list = [User.id, User.email]

    admin.add_view(UserAdmin)
    ```
    """
    # 默认不注册任何 view，避免生成项目缺少模型时报错
    return


# 如需自定义认证（覆盖 basic/bearer），取消注释并实现：
#
# def register_admin_auth(config):
#     from sqladmin.authentication import AuthenticationBackend
#     from starlette.requests import Request
#
#     class MyAuth(AuthenticationBackend):
#         async def login(self, request: Request) -> bool:
#             return False
#
#         async def logout(self, request: Request) -> bool:
#             return True
#
#         async def authenticate(self, request: Request) -> bool:
#             return False
#
#     return MyAuth(secret_key=config.admin.auth.secret_key)



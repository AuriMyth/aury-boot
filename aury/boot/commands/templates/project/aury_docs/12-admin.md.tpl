# 管理后台（Admin Console，基于 SQLAdmin）

默认提供可选的 SQLAdmin 后台（组件自动装配）。启用后路径默认为 `/api/admin-console`。

- 组件开关与配置由环境变量控制；启用后框架会在启动时自动挂载后台路由。
- SQLAdmin 通常需要同步 SQLAlchemy Engine；如果你使用的是异步 `DATABASE_URL`，建议单独设置同步的 `ADMIN_DATABASE_URL`（框架也会尝试自动推导常见驱动映射）。

## 快速启用（.env）

```bash
# 启用与基本路径
ADMIN_ENABLED=true
ADMIN_PATH=/api/admin-console

# 认证（二选一，推荐 basic 或 bearer）
ADMIN_AUTH_MODE=basic
ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
ADMIN_AUTH_BASIC_USERNAME=admin
ADMIN_AUTH_BASIC_PASSWORD=change_me

# 如果使用 bearer
# ADMIN_AUTH_MODE=bearer
# ADMIN_AUTH_SECRET_KEY=CHANGE_ME
# ADMIN_AUTH_BEARER_TOKENS=["token1","token2"]

# 如需显式提供同步数据库 URL（可选）
# ADMIN_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/{project_name}
```

## 注册后台视图

**文件**: `admin_console.py`

```python
from sqladmin import ModelView
from {package_name}.models.user import User

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email]

# 方式一：声明式（简单）
ADMIN_VIEWS = [UserAdmin]

# 方式二：函数注册（更灵活）
# def register_admin(admin):
#     admin.add_view(UserAdmin)
```

## 自定义认证（可选，高阶）

- 通过 `ADMIN_AUTH_BACKEND=module:attr` 指定自定义 backend；或在 `admin_console.py` 实现 `register_admin_auth(config)` 返回 SQLAdmin 的 `AuthenticationBackend`。
- 生产环境下必须设置 `ADMIN_AUTH_SECRET_KEY`，不允许 `none` 模式。

## 访问

启动服务后访问：`http://localhost:8000/api/admin-console`（或你配置的 `ADMIN_PATH`）。

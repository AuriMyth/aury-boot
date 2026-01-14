# {project_name} CLI 命令参考

本文档基于 [Aury Boot](https://github.com/AuriMyth/aury-boot) 框架。

## 服务器命令

```bash
# 开发模式（自动重载）
aury server dev

# 生产模式
aury server prod

# 自定义运行
aury server run --host 0.0.0.0 --port 8000 --workers 4
```

## 代码生成

```bash
# 生成完整 CRUD
aury generate crud user

# 交互式生成（推荐）：逐步选择字段、类型、约束等
aury generate crud user -i
aury generate model user -i

# 单独生成
aury generate model user      # SQLAlchemy 模型
aury generate repo user       # Repository
aury generate service user    # Service
aury generate api user        # API 路由
aury generate schema user     # Pydantic Schema

# 指定字段（非交互式）
aury generate model user --fields "name:str,email:str,age:int"

# 指定模型基类
aury generate model user --base AuditableStateModel      # int主键 + 软删除（推荐）
aury generate model user --base Model                    # int主键 + 时间戳
aury generate model user --base FullFeaturedModel        # int主键 + 全功能
aury generate model user --base UUIDAuditableStateModel  # UUID主键（如需要）
```

## 数据库迁移

```bash
aury migrate make -m "add user table"  # 创建迁移
aury migrate up                        # 执行迁移
aury migrate down                      # 回滚迁移
aury migrate status                    # 查看状态
aury migrate show                      # 查看历史
```

## 调度器和 Worker

```bash
aury scheduler    # 独立运行调度器
aury worker       # 运行 Dramatiq Worker
```

## 包管理

```bash
# 查看所有可用模块
aury pkg list

# 查看预设配置
aury pkg preset
aury pkg preset api              # 查看某个预设详情

# 安装模块
aury pkg install postgres redis  # 安装指定模块
aury pkg install --preset api    # 按预设安装（postgres + redis + admin）
aury pkg install --preset worker # 按预设安装（任务队列 + 调度器）

# 卸载模块
aury pkg remove redis
```

可用预设：
- `minimal` - 本地开发（sqlite）
- `api` - API 服务（postgres + redis + admin）
- `worker` - 后台 Worker（postgres + redis + tasks + rabbitmq + scheduler）
- `full` - 完整功能

## 环境变量配置

所有配置项都可通过环境变量设置，优先级：命令行参数 > 环境变量 > .env 文件 > 默认值

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE__URL` | 数据库连接 URL | `sqlite+aiosqlite:///./dev.db` |
| `CACHE__CACHE_TYPE` | 缓存类型 (memory/redis) | `memory` |
| `CACHE__URL` | Redis URL | - |
| `LOG__LEVEL` | 日志级别 | `INFO` |
| `LOG__DIR` | 日志目录 | `logs` |
| `SCHEDULER__ENABLED` | 启用内嵌调度器 | `true` |
| `TASK__BROKER_URL` | 任务队列 Broker URL | - |

## 管理后台（Admin Console）

框架提供可选的 SQLAdmin 管理后台扩展，默认路径：`/api/admin-console`。

常用环境变量：

|| 变量 | 说明 | 默认值 |
||------|------|--------|
|| `ADMIN__ENABLED` | 是否启用管理后台 | `false` |
|| `ADMIN__PATH` | 管理后台路径 | `/api/admin-console` |
|| `ADMIN__DATABASE_URL` | 管理后台同步数据库 URL（可覆盖自动推导） | - |
|| `ADMIN__AUTH_MODE` | 认证模式（basic/bearer/none/custom/jwt） | `basic` |
|| `ADMIN__AUTH_SECRET_KEY` | session 签名密钥（生产必配） | - |
|| `ADMIN__AUTH_BASIC_USERNAME` | basic 用户名 | - |
|| `ADMIN__AUTH_BASIC_PASSWORD` | basic 密码 | - |
|| `ADMIN__AUTH_BEARER_TOKENS` | bearer token 白名单 | `[]` |
|| `ADMIN__AUTH_BACKEND` | 自定义认证后端导入路径（module:attr） | - |

## 注册 CLI 与扩展命令

### 内置 `aury` 命令如何注册

Aury Boot 安装后会自动注册一个全局命令 `aury`（见框架自身的 `pyproject.toml`）：

```toml
[project.scripts]
aury = "aury.boot.commands:main"
```

- `aury.boot.commands:main` 是 Typer 应用入口，内部通过 `app.add_typer(...)` 注册了 `init/generate/server/scheduler/worker/migrate/docker/docs/pkg` 等子命令。

### 在你自己的项目里注册一个 CLI

如果你希望在自己的服务里有一个独立的 CLI（例如 `{project_name_snake}`），并且复用 Aury Boot 的全部基础命令，可以这样做：

1. 新建模块 `{package_name}/cli.py`：

```python
from typer import Typer
from aury.boot.commands import register_commands

# 创建项目自己的 CLI
app = Typer(name="{project_name_snake}")

# 继承 aury-boot 的所有基础命令
register_commands(app)

# 或者按需关闭某些命令，例如不暴露 docker 命令：
# register_commands(app, include_docker=False)


# 添加你自己的项目命令
@app.command()
async def hello(name: str = "world") -> None:
    """示例：项目自定义命令。"""
    print(f"Hello, {{name}} from {project_name_snake}!")
```

> 注意：这里的 `app` 是 Typer 应用实例，`register_commands` 会把所有内置的 `init/generate/server/...` 等命令挂到你自己的 CLI 下。

2. 在你项目自己的 `pyproject.toml` 中注册脚本入口（**不是框架本身的 pyproject**）：

```toml
[project.scripts]
{project_name_snake} = "{package_name}.cli:app"
```

3. 安装项目后，你就可以使用：

```bash
# 使用项目 CLI 运行 aury-boot 命令
{project_name_snake} init
{project_name_snake} generate crud user -i
{project_name_snake} server dev

# 调用你自定义的命令
{project_name_snake} hello --name dev
```

这样：
- 基础命令仍由 Aury Boot 维护和升级；
- 你的项目可以在自己的命名空间下扩展命令，而不用直接修改框架的 `aury` 命令。

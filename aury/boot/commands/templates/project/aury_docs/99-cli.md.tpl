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
aury generate model user --base UUIDAuditableStateModel  # UUID主键 + 软删除（推荐）
aury generate model user --base UUIDModel                # UUID主键 + 时间戳
aury generate model user --base Model                    # int主键 + 时间戳
aury generate model user --base VersionedUUIDModel       # UUID + 乐观锁 + 时间戳
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

## 环境变量配置

所有配置项都可通过环境变量设置，优先级：命令行参数 > 环境变量 > .env 文件 > 默认值

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 URL | `sqlite+aiosqlite:///./dev.db` |
| `CACHE_TYPE` | 缓存类型 (memory/redis) | `memory` |
| `CACHE_URL` | Redis URL | - |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `LOG_DIR` | 日志目录 | `logs` |
| `SCHEDULER_ENABLED` | 启用内嵌调度器 | `true` |
| `TASK_BROKER_URL` | 任务队列 Broker URL | - |

## 管理后台（Admin Console）

框架提供可选的 SQLAdmin 管理后台扩展，默认路径：`/api/admin-console`。

常用环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ADMIN_ENABLED` | 是否启用管理后台 | `false` |
| `ADMIN_PATH` | 管理后台路径 | `/api/admin-console` |
| `ADMIN_DATABASE_URL` | 管理后台同步数据库 URL（可覆盖自动推导） | - |
| `ADMIN_AUTH_MODE` | 认证模式（basic/bearer/none/custom/jwt） | `basic` |
| `ADMIN_AUTH_SECRET_KEY` | session 签名密钥（生产必配） | - |
| `ADMIN_AUTH_BASIC_USERNAME` | basic 用户名 | - |
| `ADMIN_AUTH_BASIC_PASSWORD` | basic 密码 | - |
| `ADMIN_AUTH_BEARER_TOKENS` | bearer token 白名单 | `[]` |
| `ADMIN_AUTH_BACKEND` | 自定义认证后端导入路径（module:attr） | - |

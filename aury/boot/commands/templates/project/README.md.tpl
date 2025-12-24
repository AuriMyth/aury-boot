# {project_name}

基于 [Aury Boot](https://github.com/AuriMyth/aury-boot) 构建的 API 服务。

## 快速开始

### 安装依赖

```bash
uv sync
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 启动开发服务器

```bash
aury server dev
```

### 管理后台（可选）

默认提供 SQLAdmin 管理后台扩展（默认路径：`/api/admin-console`），适合快速搭建项目的后台管理能力。

1) 安装扩展依赖：

```bash
uv add "aury-boot[admin]"
```

2) 在 `.env` 中启用并配置认证（至少 basic 或 bearer 之一）：

```bash
ADMIN_ENABLED=true
ADMIN_PATH=/api/admin-console
ADMIN_AUTH_MODE=basic
ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET
ADMIN_AUTH_BASIC_USERNAME=admin
ADMIN_AUTH_BASIC_PASSWORD=change_me
```

3) 启动后访问：

- `http://127.0.0.1:8000/api/admin-console`

### 生成代码

```bash
# 生成完整 CRUD（交互式，推荐）
aury generate crud user -i

# 单独生成（添加 -i 参数可交互式配置）
aury generate model user -i     # SQLAlchemy 模型
aury generate repo user        # Repository
aury generate service user     # Service
aury generate api user         # API 路由
aury generate schema user      # Pydantic Schema
```

### 数据库迁移

```bash
# 生成迁移
aury migrate make -m "add user table"

# 执行迁移
aury migrate up

# 查看状态
aury migrate status
```

### 调度器和 Worker

```bash
# 独立运行调度器
aury scheduler

# 运行任务队列 Worker
aury worker
```

## 项目结构

```
{project_name}/
├── main.py              # 应用入口
├── app/                 # 代码包（默认 app，可通过 aury init <pkg> 自定义）
│   ├── config.py        # 配置定义
│   ├── api/             # API 路由
│   ├── services/        # 业务逻辑
│   ├── models/          # SQLAlchemy 模型
│   ├── repositories/    # 数据访问层
│   ├── schemas/         # Pydantic 模型
│   ├── exceptions/      # 自定义异常
│   ├── schedules/       # 定时任务
│   └── tasks/           # 异步任务
├── migrations/          # 数据库迁移
└── tests/               # 测试
```

## 文档

- [AGENTS.md](./AGENTS.md) - AI 编程助手上下文
- [aury_docs/](./aury_docs/) - 开发文档（包含 Model/Service/API 等指南）
- [Aury Boot 文档](https://github.com/AuriMyth/aury-boot)

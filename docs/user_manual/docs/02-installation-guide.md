# 2. 安装指南

## 系统要求

- **Python 版本**：>= 3.13
- **操作系统**：Linux, macOS, Windows
- **包管理工具**：uv（推荐）或 pip

## 安装方式

### 方式 1：使用 uv（推荐）

uv 是一个极速的 Python 包管理工具，比 pip 快 10-100 倍。

**安装 uv**：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**创建新项目**：
```bash
uv init my-service
cd my-service
```

**安装 Kit（从 PyPI）**：
```bash
uv add aury-boot
```

**安装 Kit（从 Git - 开发版本）**：
```bash
uv add git+https://github.com/AuriMyth/aury-boot.git
```

### 方式 2：使用 pip

```bash
# 从 PyPI
pip install aury-boot

# 从 Git
pip install git+https://github.com/AuriMyth/aury-boot.git
```

### 方式 3：本地开发安装

如果你要修改 Kit 的代码：

```bash
# 克隆仓库
git clone https://github.com/AuriMyth/aury-boot.git
cd aury-boot

# 使用 uv 安装到本地可编辑模式
uv sync

# 在你的项目中引用本地路径
# pyproject.toml:
# dependencies = [
#     "aury-boot @ file:///path/to/aury-boot"
# ]
```

## 依赖安装

Foundation Kit 采用模块化的可选依赖设计，按需安装。

### 方式 1：使用 aury pkg 命令（推荐）

`aury pkg` 命令提供了更友好的包管理体验：

```bash
# 查看所有可用模块
aury pkg list

# 查看预设配置
aury pkg preset

# 安装指定模块
aury pkg install postgres redis admin

# 按预设安装
aury pkg install --preset api      # API 服务：postgres + redis + admin
aury pkg install --preset worker   # 后台 Worker：postgres + redis + tasks + rabbitmq + scheduler
aury pkg install --preset full     # 完整功能

# 卸载模块
aury pkg remove redis
```

#### 可用模块

| 分类 | 模块 | 用途 |
|------|------|------|
| 数据库 | postgres | DatabaseManager 使用 PostgreSQL |
| 数据库 | mysql | DatabaseManager 使用 MySQL |
| 数据库 | sqlite | DatabaseManager 使用 SQLite（本地开发推荐） |
| 缓存 | redis | CacheManager Redis 后端 |
| 任务 | tasks | TaskManager 异步任务（Dramatiq） |
| 任务 | rabbitmq | RabbitMQ 消息队列后端（需配合 tasks） |
| 调度 | scheduler | SchedulerManager 定时任务 |
| 管理 | admin | SQLAdmin 管理后台 |
| 存储 | s3 | StorageManager S3 兼容存储 |
| 存储 | storage-cos | StorageManager 腾讯云 COS（原生 SDK） |

#### 预设配置

| 预设 | 说明 | 包含模块 |
|------|------|----------|
| minimal | 本地开发/测试 | sqlite |
| api | API 服务 | postgres, redis, admin |
| worker | 后台 Worker | postgres, redis, tasks, rabbitmq, scheduler |
| full | 完整功能 | 所有模块 |

### 方式 2：直接使用 uv/pip

```bash
# 核心（只有核心框架，不含数据库/缓存等驱动）
uv add aury-boot

# 推荐（PostgreSQL + Redis + 任务队列 + 调度器）
uv add "aury-boot[recommended]"

# 按需组合
uv add "aury-boot[postgres,redis,scheduler]"

# 全部依赖
uv add "aury-boot[all]"
```

### 可选依赖清单（extras）

| 名称 | 说明 | 包含的库 |
|------|------|----------|
| `postgres` | PostgreSQL 数据库 | asyncpg |
| `mysql` | MySQL 数据库 | aiomysql |
| `sqlite` | SQLite 数据库 | aiosqlite |
| `redis` | Redis 缓存 | redis |
| `s3` | S3 对象存储 | aioboto3 |
| `tasks` | 任务队列（Dramatiq + Kombu） | dramatiq, kombu, dramatiq-kombu-broker |
| `rabbitmq` | RabbitMQ 支持（配合 tasks） | amqp |
| `scheduler` | 定时调度 | apscheduler |
| `recommended` | 推荐组合 | postgres + redis + tasks + scheduler |
| `all` | 全部依赖 | 以上所有 |
| `dev` | 开发工具 | pytest, ruff, mypy |
| `docs` | 文档生成 | mkdocs, mkdocs-material |

### 常见组合示例

```bash
# Web API 服务（数据库 + 缓存）
uv add "aury-boot[postgres,redis]"

# 后台任务服务（数据库 + 任务队列 + RabbitMQ）
uv add "aury-boot[postgres,tasks,rabbitmq]"

# 定时任务服务（数据库 + 调度器）
uv add "aury-boot[postgres,scheduler]"

# 完整微服务（推荐）
uv add "aury-boot[recommended]"
```

### 完整 pyproject.toml 示例

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-service"
version = "0.1.0"
description = "My Aury service"
readme = "README.md"
requires-python = ">=3.13"
authors = [
    { name = "Your Name", email = "you@example.com" }
]

dependencies = [
    "aury-boot[recommended]",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0.1",
    "pytest-asyncio>=1.3.0",
    "mypy>=1.19.0",
    "ruff>=0.14.7",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.13"
strict = true
```

## 验证安装

创建 `test_install.py`：

```python
from aury.boot.application.app.base import FoundationApp
from aury.boot.application.config import BaseConfig

class Config(BaseConfig):
    pass

app = FoundationApp(
    title="Test App",
    version="0.1.0",
    config=Config()
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

运行验证：
```bash
uv run python test_install.py
```

访问 http://localhost:8000/health 应该返回 `{"status": "ok"}`

## 常见问题

### Q: 能在 Python 3.12 或更低版本上使用吗？

A: 不行。Kit 使用了 Python 3.13+ 的特性（如类型注解新语法、改进的泛型等）。必须使用 Python 3.13 或更高版本。

### Q: uv 和 pip 有什么区别？

A: uv 更快、更可靠：
- 速度快 10-100 倍
- 自动管理虚拟环境
- 更好的依赖解析
- 内置锁定文件支持

### Q: 如何离线安装？

A: 先在有网的机器上生成 lock 文件：
```bash
uv lock
```

然后离线安装：
```bash
uv sync --frozen
```

### Q: 在 Docker 中安装

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml uv.lock ./

# 安装依赖
RUN /root/.local/bin/uv sync --no-dev

COPY . .

CMD ["uv", "run", "python", "main.py"]
```

## 下一步

- 查看 [03-project-structure.md](./03-project-structure.md) 建立项目结构
- 查看 [02-quick-start.md](../00-quick-start.md) 编写第一个应用



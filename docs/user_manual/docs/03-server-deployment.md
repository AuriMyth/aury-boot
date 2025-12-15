# 3. 服务器运行和部署指南

Kit 提供了两套服务器运行系统：**ApplicationServer 类** 和 **CLI 命令**。

## ApplicationServer 类

基于 uvicorn，提供完整的服务器管理功能。

### 基础使用

```python
from aury.boot.application.app.base import FoundationApp
from aury.boot.application.config import BaseConfig
from aury.boot.application.server import ApplicationServer
from aury.boot.application.interfaces.egress import BaseResponse

class AppConfig(BaseConfig):
    pass

app = FoundationApp(
    title="My Service",
    version="0.1.0",
    config=AppConfig()
)

@app.get("/health")
async def health_check():
    return BaseResponse(code=200, message="Healthy", data={"status": "ok"})

# 运行服务器
if __name__ == "__main__":
    server = ApplicationServer(
        app=app,
        host="0.0.0.0",
        port=8000,
        workers=1,
    )
    server.run()
```

### 常见配置

#### 开发模式（热重载）

```python
server = ApplicationServer(
    app=app,
    host="127.0.0.1",
    port=8000,
    reload=True,              # 启用热重载
    reload_dirs=["./src"],    # 监控目录
    debug=True,               # 调试模式
)
server.run()
```

#### 生产模式（多进程）

```python
import os

server = ApplicationServer(
    app=app,
    host="0.0.0.0",
    port=8000,
    workers=os.cpu_count() or 4,  # 使用 CPU 核心数
    reload=False,
    debug=False,
)
server.run()
```

#### HTTPS 支持

```python
server = ApplicationServer(
    app=app,
    host="0.0.0.0",
    port=443,
    ssl_keyfile="/path/to/key.pem",
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile_password=None,  # 如果密钥有密码
)
server.run()
```

### 事件循环和 HTTP 协议优化

```python
server = ApplicationServer(
    app=app,
    host="0.0.0.0",
    port=8000,
    loop="uvloop",      # 事件循环实现：auto/asyncio/uvloop
    http="httptools",   # HTTP 协议：auto/h11/httptools
)
server.run()
```

**性能对比**：
- `loop="uvloop"` - 比标准 asyncio 快 2-4 倍
- `http="httptools"` - 比 h11 快 3 倍
- 需要额外安装：`pip install uvloop httptools`

### 异步运行

```python
import asyncio
from aury.boot.application.server import ApplicationServer

async def run_server_async():
    server = ApplicationServer(
        app=app,
        host="0.0.0.0",
        port=8000,
    )
    await server.run_async()

# 在异步框架中使用
if __name__ == "__main__":
    asyncio.run(run_server_async())
```

### 获取服务器配置

```python
server = ApplicationServer(
    app=app,
    host="0.0.0.0",
    port=8000,
)

# 获取 uvicorn 配置对象
config = server.get_config()
print(f"监听地址: {config.host}:{config.port}")
print(f"工作进程: {config.workers}")
```

## run_app 快捷函数

简化的运行接口，自动读取环境变量。

### 基础使用

```python
from aury.boot.application.app.base import FoundationApp
from aury.boot.application.server import run_app

app = FoundationApp(title="My Service")

if __name__ == "__main__":
    run_app(app)  # 自动使用环境变量或默认值
```

### 指定参数

```python
run_app(
    app,
    host="0.0.0.0",
    port=8000,
    workers=4,
    reload=False,
    # 其他 ApplicationServer 参数
)
```

### 环境变量支持

```bash
# 设置环境变量
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8000
export SERVER_WORKERS=4
export SERVER_RELOAD=true

# 运行应用
python main.py
```

## CLI 命令

提供了开箱即用的命令行工具。

### 基础命令

**方式 1：直接使用命令（推荐）**

```bash
# 开发服务器（热重载）
aury server dev
# 或使用短别名
aury server dev

# 通用运行命令
aury server run

# 生产服务器（多进程）
aury server prod
```

**方式 2：使用 Python 模块**

```bash
# 开发服务器
uv run aury server dev

# 通用运行
uv run aury server run

# 生产服务器
uv run aury server prod
```

### dev 命令（开发模式）

```bash
# 基础用法
aury server dev

# 指定端口
aury server dev --port 9000

# 指定地址和端口
aury server dev --host 0.0.0.0 --port 9000
```

**特点**：
- 自动启用热重载
- 自动启用调试模式
- 单进程运行
- 推荐用于开发

### run 命令（通用运行）

```bash
# 基础用法
aury server run

# 指定工作进程
aury server run --workers 4

# 启用热重载
aury server run --reload

# 指定热重载监控目录
aury server run --reload --reload-dir src --reload-dir tests

# HTTPS
aury server run \
    --ssl-keyfile key.pem \
    --ssl-certfile cert.pem

# 完整示例
aury server run \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --http httptools \
    --debug
```

**所有选项**：
```
--host              监听地址（默认：127.0.0.1）
--port              监听端口（默认：8000）
--workers           工作进程数（默认：1）
--reload            启用热重载
--reload-dir        热重载监控目录（可指定多个）
--debug             启用调试模式
--loop              事件循环实现（auto/asyncio/uvloop）
--http              HTTP 协议版本（auto/h11/httptools）
--ssl-keyfile       SSL 密钥文件
--ssl-certfile      SSL 证书文件
--no-access-log     禁用访问日志
```

### prod 命令（生产模式）

```bash
# 基础用法（自动使用 CPU 核心数）
aury server prod

# 指定工作进程数
aury server prod --workers 8

# 指定地址和端口
aury server prod --host 0.0.0.0 --port 8000
```

**特点**：
- 自动使用 CPU 核心数作为工作进程数
- 禁用热重载
- 禁用调试模式
- 推荐用于生产环境

## 环境变量配置

所有命令都支持环境变量配置：

```bash
# 共通环境变量
SERVER_HOST=0.0.0.0      # 监听地址
SERVER_PORT=8000         # 监听端口
SERVER_WORKERS=4         # 工作进程数
SERVER_RELOAD=true       # 启用热重载
DEBUG=true               # 调试模式

# 例子：完整配置
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8000
export SERVER_WORKERS=4
export SERVER_RELOAD=false
export DEBUG=false

aury server run
```

## 项目 main.py 结构

### 推荐的 main.py 结构

```python
"""应用入口点。"""

from aury.boot.application.app.base import FoundationApp
from aury.boot.application.config import BaseConfig
from aury.boot.application.server import run_app
from aury.boot.application.app.components import (
    RequestLoggingComponent,
    DatabaseComponent,
    CacheComponent,
)

# ============= 配置 =============

class AppConfig(BaseConfig):
    """应用配置"""
    pass

# ============= 应用创建 =============

def create_app() -> FoundationApp:
    """工厂函数创建应用"""
    config = AppConfig()
    
    app = FoundationApp(
        title="My Service",
        version="0.1.0",
        config=config
    )
    
    # 注册组件
    app.items = [
        RequestLoggingComponent,
        DatabaseComponent,
        CacheComponent,
    ]
    
    # 注册路由
    from api.v1 import users_router
    app.include_router(users_router, prefix="/api/v1")
    
    return app

# ============= 应用实例 =============

app = create_app()

# ============= 启动 =============

if __name__ == "__main__":
    run_app(app)
```

### 使用方式

```bash
# 直接运行
uv run python main.py

# 或使用 CLI 命令（推荐）
aury server dev

# 或指定 uvicorn
uvicorn main:app --reload
```

## Docker 部署

### Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN /root/.local/bin/uv sync --frozen --no-dev

# 复制代码
COPY . .

# 暴露端口
EXPOSE 8000

# 运行应用
CMD ["/root/.local/bin/uv", "run", "aum", "server", "prod"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      SERVER_HOST: 0.0.0.0
      SERVER_PORT: 8000
      SERVER_WORKERS: 4
      DATABASE_URL: postgresql+asyncpg://user:pass@db:5432/mydb
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 运行

```bash
docker-compose up

# 查看日志
docker-compose logs -f app
```

## 性能优化

### 1. 多进程配置

```bash
# 使用 CPU 核心数
aury server prod

# 或指定具体数值
aury server run --workers 8
```

### 2. 事件循环优化

```bash
# uvloop 已通过 uvicorn[standard] 依赖自动安装

# 使用 uvloop
aury server run --loop uvloop --http httptools
```

### 3. 内存管理

```bash
# 监控内存使用
ps aux | grep python

# 限制内存
docker run --memory=1g myapp
```

### 4. 连接池优化

```python
class AppConfig(BaseConfig):
    database: DatabaseSettings = Field(
        default_factory=lambda: DatabaseSettings(
            pool_size=20,           # 连接池大小
            max_overflow=30,        # 超限连接数
            pool_recycle=3600,      # 连接回收时间（秒）
        )
    )
```

## 常见问题

### Q: 如何在生产环境使用 HTTPS？

A: 使用 SSL 证书：
```bash
aury server run \
    --ssl-keyfile /path/to/key.pem \
    --ssl-certfile /path/to/cert.pem
```

### Q: 开发时热重载不工作？

A: 确保：
1. 启用了 `--reload` 标志
2. 修改了代码（不是导入的包）
3. 使用了支持的文件格式

### Q: 如何优化内存使用？

A: 
1. 使用 uvloop：`--loop uvloop`
2. 限制工作进程数
3. 启用连接池回收：`pool_recycle=3600`

### Q: 生产环境用多少工作进程？

A: 通常为 CPU 核心数。`prod` 命令自动计算。

## 下一步

- 查看 [06-components-detailed.md](./06-components-detailed.md) 了解组件系统
- 查看 [09-database-complete.md](./09-database-complete.md) 了解数据库配置
- 查看 [20-best-practices.md](./20-best-practices.md) 了解部署最佳实践


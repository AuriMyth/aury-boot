"""Docker 相关命令。

生成 Docker 配置文件：
- Dockerfile
- docker-compose.yml
- .dockerignore

使用示例：
    aury docker init
    aury docker init --force
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
import typer

from .config import get_project_config

console = Console()

# 创建 docker 子应用
app = typer.Typer(
    name="docker",
    help="Docker 配置文件生成",
    no_args_is_help=True,
)


# ============================================================
# 模板
# ============================================================

DOCKERFILE_TEMPLATE = '''# =============================================================================
# {project_name} Dockerfile
# =============================================================================
# 多阶段构建优化镜像大小

# 基础镜像
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# 构建阶段：安装依赖
# -----------------------------------------------------------------------------
FROM base AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 复制依赖文件
COPY pyproject.toml uv.lock* ./

# 安装依赖到虚拟环境
RUN uv sync --frozen --no-dev --no-install-project

# -----------------------------------------------------------------------------
# 运行阶段
# -----------------------------------------------------------------------------
FROM base AS runtime

# 从 builder 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 设置 PATH
ENV PATH="/app/.venv/bin:$PATH"

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser && \\
    chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# 默认命令
CMD ["aury", "server", "prod"]
'''


DOCKER_COMPOSE_TEMPLATE = '''# =============================================================================
# {project_name} Docker Compose
# =============================================================================
# 服务编排配置

services:
  # ---------------------------------------------------------------------------
  # 基础服务（共享配置）
  # ---------------------------------------------------------------------------
  base: &base
    build:
      context: .
      dockerfile: Dockerfile
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - {project_name_snake}_network

  # ---------------------------------------------------------------------------
  # API 服务
  # ---------------------------------------------------------------------------
  api:
    <<: *base
    container_name: {project_name_snake}_api
    environment:
      - SERVICE_NAME=api
      - SERVICE_TYPE=api
      - SCHEDULER_ENABLED=false  # API 服务不启动内嵌调度器
    ports:
      - "${{API_PORT:-8000}}:8000"
    command: ["aury", "server", "prod"]
    depends_on:
      - redis
      - postgres

  # ---------------------------------------------------------------------------
  # Scheduler 服务（定时任务）
  # ---------------------------------------------------------------------------
  scheduler:
    <<: *base
    container_name: {project_name_snake}_scheduler
    environment:
      - SERVICE_NAME=scheduler
    command: ["aury", "scheduler"]
    depends_on:
      - redis
      - postgres

  # ---------------------------------------------------------------------------
  # Worker 服务（异步任务）
  # ---------------------------------------------------------------------------
  worker:
    <<: *base
    container_name: {project_name_snake}_worker
    environment:
      - SERVICE_NAME=worker
    command: ["aury", "worker", "-c", "8"]
    depends_on:
      - redis
      - postgres

  # ---------------------------------------------------------------------------
  # 基础设施服务
  # ---------------------------------------------------------------------------
  postgres:
    image: postgres:16-alpine
    container_name: {project_name_snake}_postgres
    environment:
      POSTGRES_USER: ${{POSTGRES_USER:-postgres}}
      POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD:-postgres}}
      POSTGRES_DB: ${{POSTGRES_DB:-{project_name_snake}}}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${{POSTGRES_PORT:-5432}}:5432"
    networks:
      - {project_name_snake}_network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: {project_name_snake}_redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "${{REDIS_PORT:-6379}}:6379"
    networks:
      - {project_name_snake}_network
    restart: unless-stopped

# -----------------------------------------------------------------------------
# 网络和卷
# -----------------------------------------------------------------------------
networks:
  {project_name_snake}_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
'''


DOCKERIGNORE_TEMPLATE = '''# =============================================================================
# Docker 忽略文件
# =============================================================================

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/
.eggs/
*.egg-info/
*.egg

# 开发工具
.git/
.gitignore
.idea/
.vscode/
*.swp
*.swo

# 测试
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# 构建
dist/
build/
*.egg-info/

# 文档
docs/
*.md
!README.md

# 本地配置
.env.local
.env.*.local
*.local.yml

# 日志
logs/
*.log

# 缓存
.cache/
.mypy_cache/
.ruff_cache/

# IDE
.idea/
.vscode/
*.sublime-*

# macOS
.DS_Store

# 其他
Makefile
docker-compose.override.yml
'''


# ============================================================
# 命令
# ============================================================


def _to_snake_case(name: str) -> str:
    """转换为 snake_case。"""
    import re
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower().replace("-", "_")


@app.command(name="init")
def docker_init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制覆盖已存在的文件",
    ),
) -> None:
    """生成 Docker 配置文件。

    生成：
    - Dockerfile
    - docker-compose.yml
    - .dockerignore

    示例：
        aury docker init
        aury docker init --force
    """
    base_path = Path.cwd()

    # 获取项目名称
    project_name = base_path.name
    project_name_snake = _to_snake_case(project_name)

    # 读取项目配置，获取包名
    config = get_project_config(base_path)
    package_or_dot = f"{config.package}." if config.has_package else ""

    console.print(Panel.fit(
        f"[bold cyan]🐳 生成 Docker 配置: {project_name}[/bold cyan]",
        border_style="cyan",
    ))

    created_files = []

    # 模板变量
    template_vars = {
        "project_name": project_name,
        "project_name_snake": project_name_snake,
        "package_or_dot": package_or_dot,
    }

    # 生成文件
    files_to_create = [
        ("Dockerfile", DOCKERFILE_TEMPLATE),
        ("docker-compose.yml", DOCKER_COMPOSE_TEMPLATE),
        (".dockerignore", DOCKERIGNORE_TEMPLATE),
    ]

    for file_name, template in files_to_create:
        file_path = base_path / file_name

        if file_path.exists() and not force:
            console.print(f"  [dim]⏭️  {file_name} 已存在，跳过[/dim]")
            continue

        content = template.format(**template_vars)
        file_path.write_text(content, encoding="utf-8")
        created_files.append(file_name)
        console.print(f"  [green]✅ {file_name}[/green]")

    if created_files:
        console.print("\n[bold green]✨ Docker 配置生成完成！[/bold green]\n")
        console.print("[bold]使用方法：[/bold]")
        console.print("  1. 启动所有服务：")
        console.print("     [cyan]docker-compose up -d[/cyan]")
        console.print("  2. 只启动 API：")
        console.print("     [cyan]docker-compose up -d api[/cyan]")
        console.print("  3. 查看日志：")
        console.print("     [cyan]docker-compose logs -f api[/cyan]")
        console.print("  4. 停止服务：")
        console.print("     [cyan]docker-compose down[/cyan]")
    else:
        console.print("\n[dim]所有文件已存在，使用 --force 覆盖[/dim]")


__all__ = ["app"]

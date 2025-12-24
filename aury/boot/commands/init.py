"""项目脚手架初始化命令。

类似 Vue CLI 的交互式项目初始化。

前置条件：
    1. mkdir my-service && cd my-service
    2. uv init . --bare --name my_service
    3. uv venv --python 3.13
    4. uv add "aury-boot[recommended]"

初始化脚手架：
    aury init                    # 交互式初始化
    aury init -r                 # 推荐配置快速初始化
    aury init my_package         # 指定顶层包名
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.tree import Tree
import typer

from .config import ProjectConfig, save_project_config

console = Console()

# 最低 Python 版本要求
MIN_PYTHON_VERSION = (3, 13)


# ============================================================
# 枚举定义
# ============================================================


class ServiceMode(str, Enum):
    """服务运行模式。"""

    API = "api"
    API_SCHEDULER = "api+scheduler"
    FULL = "full"


class CacheType(str, Enum):
    """缓存类型。"""

    MEMORY = "memory"
    REDIS = "redis"


class DatabaseType(str, Enum):
    """数据库类型。"""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


# ============================================================
# 依赖配置
# ============================================================


# 模板目录
TEMPLATES_DIR = Path(__file__).parent / "templates" / "project"
MODULE_TEMPLATES_DIR = TEMPLATES_DIR / "modules"

# 需要创建的目录结构（包内）
DIRECTORIES = [
    "api",
    "services",
    "models",
    "repositories",
    "schemas",
    "exceptions",  # 自定义异常
    "tasks",       # 异步任务（Dramatiq）
    "schedules",   # 定时任务（Scheduler）
]

# Ruff 配置
RUFF_CONFIG = '''
[tool.ruff]
target-version = "py313"
line-length = 120
indent-width = 4
exclude = [
    ".git",
    ".venv",
    "__pycache__",
    "*.pyc",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "*.egg-info",
]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "T20",    # flake8-print
    "RUF",    # Ruff-specific rules
]
ignore = [
    "E501",   # 行长度
    "B008",   # 函数调用中的默认参数
    "B006",   # 可变默认参数
    "T201",   # print 语句
    "RUF001", # 中文标点
    "RUF002", # 中文标点
    "RUF003", # 中文标点
]

[tool.ruff.lint.isort]
known-first-party = ["app", "api", "models", "services", "repositories", "schemas"]
force-sort-within-sections = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
'''

# 开发依赖配置（单独处理，确保总是添加）
DEV_DEPS_CONFIG = '''
[dependency-groups]
dev = [
    "pytest>=9.0.1",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=7.0.0",
    "ruff>=0.14.0",
    "mypy>=1.19.0",
    "watchfiles>=0.24.0",
]
'''


# 模板文件映射（模板名 -> .tpl 文件名）
TEMPLATE_FILE_MAP = {
    "main.py": "main.py.tpl",
    "config.py": "config.py.tpl",
    ".env.example": "env.example.tpl",
    ".gitignore": "gitignore.tpl",
    "README.md": "README.md.tpl",
    "AGENTS.md": "AGENTS.md.tpl",
    "conftest.py": "conftest.py.tpl",
    "admin_console/__init__.py": "admin_console_init.py.tpl",
}

# 模块 __init__.py 模板映射
MODULE_TEMPLATE_MAP = {
    "api": "api.py.tpl",
    "tasks": "tasks.py.tpl",
    "schedules": "schedules.py.tpl",
    "exceptions": "exceptions.py.tpl",
}


def _read_template(name: str) -> str:
    """读取模板文件。"""
    # 先尝试从映射中查找 .tpl 文件
    tpl_name = TEMPLATE_FILE_MAP.get(name)
    if tpl_name:
        template_path = TEMPLATES_DIR / tpl_name
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
    
    # 尝试直接读取
    template_path = TEMPLATES_DIR / name
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    
    # 如果模板文件不存在，抛出错误
    raise FileNotFoundError(f"模板文件不存在: {name} (查找路径: {TEMPLATES_DIR})")


def _read_module_template(module_name: str) -> str:
    """读取模块 __init__.py 模板。"""
    tpl_name = MODULE_TEMPLATE_MAP.get(module_name)
    if tpl_name:
        template_path = MODULE_TEMPLATES_DIR / tpl_name
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
    # 如果模板文件不存在，抛出错误
    raise FileNotFoundError(f"模块模板文件不存在: {module_name} (查找路径: {MODULE_TEMPLATES_DIR})")


# ============================================================
# Admin Console 模块初始化（可复用）
# ============================================================


def init_admin_console_module(
    base_path: Path,
    code_root: Path,
    import_prefix: str,
    *,
    force: bool = False,
    enable_env: bool = True,
) -> dict[str, bool]:
    """初始化 Admin Console 模块到现有项目。

    用于 `aury init`（新项目）和 `aury add admin-console`（已有项目）复用。

    Args:
        base_path: 项目根目录
        code_root: 代码根目录（包根或平铺）
        import_prefix: 导入前缀（如 "app."）
        force: 强制覆盖已有 admin_console/__init__.py
        enable_env: 是否尝试在 .env.example 中开启 ADMIN_* 配置

    Returns:
        dict 包含操作结果:
        - file_created: 文件是否创建成功
        - file_existed: 文件是否已存在（且未覆盖）
        - env_updated: 是否更新了 .env.example
    """
    result = {"file_created": False, "file_existed": False, "env_updated": False}

    # 1) 创建 admin_console/ 包目录和 __init__.py
    admin_pkg = code_root / "admin_console"
    dest = admin_pkg / "__init__.py"
    content = _read_template("admin_console/__init__.py")
    content = content.replace("{import_prefix}", import_prefix)

    if dest.exists() and not force:
        result["file_existed"] = True
    else:
        admin_pkg.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        result["file_created"] = True

    # 2) 尝试在 .env.example 中开启 ADMIN_* 配置
    if enable_env:
        env_example = base_path / ".env.example"
        if env_example.exists():
            try:
                s = env_example.read_text(encoding="utf-8")
                s2 = (
                    s.replace("# ADMIN_ENABLED=false", "ADMIN_ENABLED=true")
                     .replace("# ADMIN_PATH=/api/admin-console", "ADMIN_PATH=/api/admin-console")
                     .replace("# ADMIN_AUTH_MODE=basic", "ADMIN_AUTH_MODE=basic")
                     .replace(
                        "# ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET",
                        "ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET",
                    )
                     .replace("# ADMIN_AUTH_BASIC_USERNAME=admin", "ADMIN_AUTH_BASIC_USERNAME=admin")
                     .replace("# ADMIN_AUTH_BASIC_PASSWORD=change_me", "ADMIN_AUTH_BASIC_PASSWORD=change_me")
                )
                if s2 != s:
                    env_example.write_text(s2, encoding="utf-8")
                    result["env_updated"] = True
            except Exception:
                pass  # 静默失败

    return result


def _create_directory_structure(base_path: Path, package_name: str | None = None) -> list[str]:
    """创建目录结构。

    Args:
        base_path: 项目根目录
        package_name: 顶层包名，None 表示平铺结构

    Returns:
        创建的目录列表
    """
    created = []

    # 确定代码根目录
    if package_name:
        code_root = base_path / package_name
        # 创建顶层包目录
        if not code_root.exists():
            code_root.mkdir(parents=True, exist_ok=True)
            created.append(package_name)
            # 创建顶层 __init__.py
            (code_root / "__init__.py").write_text(
                f'"""顶层包 {package_name}。"""\n', encoding="utf-8"
            )
    else:
        code_root = base_path

    for dir_path in DIRECTORIES:
        full_path = code_root / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
            rel_path = f"{package_name}/{dir_path}" if package_name else dir_path
            created.append(rel_path)
            # 创建 __init__.py
            init_file = full_path / "__init__.py"
            if not init_file.exists():
                # 尝试从外部模板读取
                if dir_path in MODULE_TEMPLATE_MAP:
                    init_file.write_text(_read_module_template(dir_path), encoding="utf-8")
                else:
                    # 普通目录使用简单的 __init__.py
                    init_file.write_text('"""模块初始化。"""\n', encoding="utf-8")
    return created


def _create_file_if_not_exists(path: Path, content: str) -> bool:
    """创建文件（如果不存在）。"""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _append_ruff_config(base_path: Path) -> bool:
    """追加 ruff 配置到 pyproject.toml。"""
    pyproject_path = base_path / "pyproject.toml"
    if not pyproject_path.exists():
        return False
    
    content = pyproject_path.read_text(encoding="utf-8")
    
    # 检查是否已有 ruff 配置
    if "[tool.ruff]" in content:
        return False
    
    content += RUFF_CONFIG
    pyproject_path.write_text(content, encoding="utf-8")
    return True


def _append_dev_deps_config(base_path: Path) -> bool:
    """追加开发依赖配置到 pyproject.toml。"""
    pyproject_path = base_path / "pyproject.toml"
    if not pyproject_path.exists():
        return False
    
    content = pyproject_path.read_text(encoding="utf-8")
    
    # 检查是否已有 dependency-groups 配置
    if "[dependency-groups]" in content:
        return False
    
    content += DEV_DEPS_CONFIG
    pyproject_path.write_text(content, encoding="utf-8")
    return True


def _to_snake_case(name: str) -> str:
    """转换为 snake_case。"""
    import re
    # 处理 PascalCase 和 camelCase
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower().replace("-", "_")


def _init_migrations(base_path: Path, package_name: str | None = None) -> bool:
    """初始化数据库迁移目录和配置。

    Args:
        base_path: 项目根目录
        package_name: 顶层包名，None 表示平铺结构
    
    直接调用 MigrationManager 的创建逻辑，保证单一数据源。
    """
    from aury.boot.application.config.settings import MigrationSettings
    from aury.boot.application.migrations.setup import ensure_migration_setup
    
    migration_config = MigrationSettings()
    migrations_dir = base_path / migration_config.script_location
    
    if migrations_dir.exists():
        return False
    
    # 调用统一的创建函数
    ensure_migration_setup(
        base_path=base_path,
        config_path=migration_config.config_path,
        script_location=migration_config.script_location,
        model_modules=migration_config.model_modules,
    )
    
    return True


# ============================================================
# 环境检查函数
# ============================================================


def _check_python_version() -> bool:
    """检查 Python 版本是否满足最低要求。"""
    return sys.version_info >= MIN_PYTHON_VERSION


# ============================================================
# 交互式配置收集
# ============================================================


def _collect_interactive_config() -> dict:
    """交互式收集项目配置（Vue CLI 风格）。"""
    config = {}

    # 默认包名使用 app（更符合习惯，也更利于 AI/模板稳定生成）
    # 如需平铺结构请输入 "."
    default_pkg = "app"

    console.print(Panel.fit(
        "[bold cyan]🎯 Aury Boot[/bold cyan]\n"
        "[dim]交互式项目初始化[/dim]",
        border_style="cyan",
    ))
    console.print()

    # 1. 项目结构（输入包名或留空）
    console.print("[bold]📦 项目结构[/bold]")
    console.print("  [dim]输入包名使用顶层包结构，. 则使用平铺结构[/dim]")
    package_input = Prompt.ask(
        "包名",
        default=default_pkg,
    )
    # "." 表示平铺结构
    if package_input.strip() == ".":
        config["package_name"] = None
    else:
        config["package_name"] = package_input.strip() or None

    # 2. 数据库类型
    console.print()
    console.print("[bold]🗄️  数据库[/bold]")
    console.print("  [dim]1. PostgreSQL (推荐)[/dim]")
    console.print("  [dim]2. MySQL[/dim]")
    console.print("  [dim]3. SQLite (开发用)[/dim]")
    db_choice = IntPrompt.ask(
        "选择数据库",
        default=1,
        choices=["1", "2", "3"],
    )
    config["database"] = {
        1: "postgresql",
        2: "mysql",
        3: "sqlite",
    }[db_choice]

    # 3. 缓存类型
    console.print()
    console.print("[bold]📦 缓存[/bold]")
    console.print("  [dim]1. Redis (推荐)[/dim]")
    console.print("  [dim]2. 内存缓存 (开发用)[/dim]")
    cache_choice = IntPrompt.ask(
        "选择缓存类型",
        default=1,
        choices=["1", "2"],
    )
    config["cache"] = {
        1: "redis",
        2: "memory",
    }[cache_choice]

    # 4. 服务模式（决定推荐安装的依赖包）
    console.print()
    console.print("[bold]⚙️  服务模式[/bold] [dim](决定推荐安装的依赖)[/dim]")
    console.print("  [dim]1. api           - 纯 API 服务[/dim]")
    console.print("  [dim]2. api+scheduler - API + 定时任务 (APScheduler)[/dim]")
    console.print("  [dim]3. full          - API + 定时任务 + 异步任务队列 (Dramatiq)[/dim]")
    mode_choice = IntPrompt.ask(
        "选择服务模式",
        default=2,
        choices=["1", "2", "3"],
    )
    config["service_mode"] = {
        1: "api",
        2: "api+scheduler",
        3: "full",
    }[mode_choice]

    # 5. 可选功能
    console.print()
    console.print("[bold]📦 可选功能[/bold]")
    features = []

    # 管理后台（Admin Console）
    config["with_admin_console"] = Confirm.ask(
        "  启用管理后台 Admin Console (SQLAdmin)",
        default=True,
    )

    if Confirm.ask("  启用对象存储 (S3/本地)", default=True):
        features.append("storage")

    if Confirm.ask("  启用事件总线", default=False):
        features.append("events")

    if Confirm.ask("  启用国际化 (i18n)", default=False):
        features.append("i18n")

    config["features"] = features

    # 6. 开发工具
    console.print()
    config["with_dev"] = Confirm.ask(
        "[bold]🛠️  安装开发工具[/bold] (pytest, ruff, mypy)",
        default=True,
    )

    # 7. Docker 配置
    console.print()
    config["with_docker"] = Confirm.ask(
        "[bold]🐳 生成 Docker 配置[/bold]",
        default=True,
    )

    return config


def _build_dependency_list(config: dict) -> list[str]:
    """根据配置构建依赖列表。"""
    extras = set()

    # 数据库
    db = config.get("database", "postgresql")
    if db == "postgresql":
        extras.add("postgresql")
    elif db == "mysql":
        extras.add("mysql")

    # 缓存
    if config.get("cache") == "redis":
        extras.add("redis")

    # 服务模式
    mode = config.get("service_mode", "api")
    if mode in ("api+scheduler", "full"):
        extras.add("scheduler")
    if mode == "full":
        extras.add("tasks")

    # 可选功能
    for feature in config.get("features", []):
        extras.add(feature)

    # 管理后台（可选扩展）
    if config.get("with_admin_console", True):
        extras.add("admin")

    # 开发工具
    if config.get("with_dev"):
        extras.add("dev")

    # 构建依赖字符串
    if extras:
        extras_str = ",".join(sorted(extras))
        return [f"aury-boot[{extras_str}]"]
    return ["aury-boot"]


def _show_config_summary(config: dict) -> None:
    """显示配置摘要。"""
    console.print()
    console.print(Panel.fit(
        "[bold]📋 配置摘要[/bold]",
        border_style="blue",
    ))

    items = [
        ("项目名称", config.get("project_name", Path.cwd().name)),
        ("包结构", config.get("package_name") or "平铺结构"),
        ("数据库", config.get("database", "postgresql")),
        ("缓存", config.get("cache", "memory")),
        ("服务模式", config.get("service_mode", "api")),
        ("管理后台", "是" if config.get("with_admin_console", True) else "否"),
        ("可选功能", ", ".join(config.get("features", [])) or "无"),
        ("开发工具", "是" if config.get("with_dev") else "否"),
        ("Docker", "是" if config.get("with_docker") else "否"),
    ]

    for label, value in items:
        console.print(f"  [bold]{label}:[/bold] {value}")

    # 显示依赖
    deps = _build_dependency_list(config)
    console.print(f"  [bold]依赖:[/bold] {deps[0]}")


# ============================================================
# 主命令
# ============================================================


def init(
    package_name: str = typer.Argument(
        None,
        help="顶层包名（默认 app）。如需平铺结构请输入 '.'",
    ),
    no_interactive: bool = typer.Option(
        False,
        "--no-interactive",
        "-y",
        help="跳过交互，使用默认配置",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制覆盖已存在的文件（包括 main.py）",
    ),
    with_docker: bool = typer.Option(
        False,
        "--docker",
        help="同时生成 Docker 配置文件",
    ),
) -> None:
    """初始化 Aury 项目脚手架。

    前置条件（先执行以下命令）：
        mkdir my-service && cd my-service
        uv init . --name my_service --no-package --python 3.13
        uv add "aury-boot[recommended]"

    示例：
        aury init                    # 交互式模式（默认）
        aury init -y                 # 跳过交互，使用默认配置
        aury init my_package         # 顶层包结构
        aury init --docker           # 包含 Docker 配置
        aury init -f                 # 强制覆盖
    """
    base_path = Path.cwd()

    # 检查 pyproject.toml
    if not (base_path / "pyproject.toml").exists():
        console.print("[red]❌ 未找到 pyproject.toml[/red]")
        console.print()
        console.print("[bold]请先执行以下命令：[/bold]")
        console.print("  [cyan]uv init . --name <project_name> --no-package --python 3.13[/cyan]")
        console.print('  [cyan]uv add "aury-boot[recommended]"[/cyan]')
        raise typer.Exit(1)

    # 获取项目名称
    project_name = base_path.name
    project_name_snake = _to_snake_case(project_name)

    # 交互式模式（默认）
    if not no_interactive:
        config = _collect_interactive_config()
        config["project_name"] = project_name  # 使用当前目录名
        package_name_snake = _to_snake_case(config.get("package_name")) if config.get("package_name") else None
        with_docker = config.get("with_docker", False)
        with_admin_console = config.get("with_admin_console", True)

        # 显示配置摘要并确认
        _show_config_summary(config)
        console.print()
        if not Confirm.ask("确认初始化项目", default=True):
            console.print("[yellow]已取消[/yellow]")
            raise typer.Exit(0)

        # 显示推荐的依赖安装命令
        deps = _build_dependency_list(config)
        console.print()
        console.print("[bold]📦 推荐安装的依赖：[/bold]")
        console.print(f"  [cyan]uv add \"{deps[0]}\"[/cyan]")
        console.print()
    else:
        # 非交互模式：默认启用 Admin Console
        with_admin_console = True
        if package_name == ".":
            package_name_snake = None
        elif package_name:
            package_name_snake = _to_snake_case(package_name)
        else:
            package_name_snake = "app"

    # 显示标题
    title = project_name
    if package_name_snake:
        title += f" (包: {package_name_snake})"
    console.print(Panel.fit(
        f"[bold cyan]🚀 初始化 Aury 项目: {title}[/bold cyan]",
        border_style="cyan",
    ))

    # 1. 创建目录结构
    console.print("\n[bold]📁 创建目录结构...[/bold]")
    _create_directory_structure(base_path, package_name_snake)

    # 确定代码目录
    code_root = base_path / package_name_snake if package_name_snake else base_path

    # 2. 生成文件
    console.print("\n[bold]📝 生成文件...[/bold]")

    # main.py 总是覆盖（因为 uv init 会创建默认的）
    # main.py 始终放在根目录，作为入口文件
    files_to_create = [
        (base_path / "main.py", "main.py", True),  # 总是覆盖，放在根目录
        (code_root / "config.py", "config.py", False),
        (base_path / ".env.example", ".env.example", False),
        # 管理后台默认模块（可选）—— 现在是包目录
        (code_root / "admin_console" / "__init__.py", "admin_console/__init__.py", False),
        (base_path / "tests" / "conftest.py", "conftest.py", False),  # tests 放在项目根目录
        (base_path / "README.md", "README.md", True),  # 覆盖 uv init 创建的默认 README
        (base_path / "AGENTS.md", "AGENTS.md", False),  # AI 编程助手上下文
        (base_path / ".gitignore", ".gitignore", False),  # Git 忽略文件
    ]

    import_prefix = f"{package_name_snake}." if package_name_snake else ""
    template_vars = {
        "project_name": project_name,
        "project_name_snake": project_name_snake,
        "import_prefix": import_prefix,
        "package_name": package_name_snake or "",
    }

    for full_path, template_name, always_overwrite in files_to_create:
        # 若禁用管理后台，则跳过生成 admin_console/
        if template_name == "admin_console/__init__.py" and not with_admin_console:
            continue

        rel_path = full_path.relative_to(base_path)
        should_write = always_overwrite or force or not full_path.exists()

        if not should_write:
            console.print(f"  [dim]⏭️  {rel_path} 已存在，跳过[/dim]")
            continue

        content = _read_template(template_name)
        # 临时替换代码块中的字典字面量，避免 str.format() 解析
        import re
        dict_placeholders = {}
        placeholder_counter = [0]  # 使用列表以便在嵌套函数中修改
        
        def protect_dict(match, *, _dict_placeholders=dict_placeholders, _placeholder_counter=placeholder_counter):
            """保护字典字面量，用占位符替换"""
            placeholder = f"__DICT_PLACEHOLDER_{_placeholder_counter[0]}__"
            _dict_placeholders[placeholder] = match.group(0)
            _placeholder_counter[0] += 1
            return placeholder
        
        def process_code_block(match, *, _protect_dict=protect_dict):
            """处理代码块，保护其中的字典字面量"""
            code_content = match.group(1)
            protected_code = re.sub(r'\{"[^"]+":\s*[^}]+\}', _protect_dict, code_content, flags=re.DOTALL)
            return '```python' + protected_code + '```'
        
        # 在代码块中保护字典字面量（匹配 {"key": value} 格式）
        content = re.sub(r'```python(.*?)```', process_code_block, content, flags=re.DOTALL)
        
        # 格式化模板（替换 {project_name} 等占位符）
        # 合并 template_vars 和 dict_placeholders，防止 KeyError
        format_vars = {**template_vars, **dict_placeholders}
        content = content.format(**format_vars)

        # 若启用管理后台，默认在 .env.example 中打开 ADMIN_ENABLED，并给出基础示例
        if template_name == ".env.example" and with_admin_console:
            content = content.replace("# ADMIN_ENABLED=false", "ADMIN_ENABLED=true")
            content = content.replace("# ADMIN_PATH=/api/admin-console", "ADMIN_PATH=/api/admin-console")
            content = content.replace("# ADMIN_AUTH_MODE=basic", "ADMIN_AUTH_MODE=basic")
            content = content.replace(
                "# ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET",
                "ADMIN_AUTH_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET",
            )
            content = content.replace("# ADMIN_AUTH_BASIC_USERNAME=admin", "ADMIN_AUTH_BASIC_USERNAME=admin")
            content = content.replace("# ADMIN_AUTH_BASIC_PASSWORD=change_me", "ADMIN_AUTH_BASIC_PASSWORD=change_me")
        
        # 恢复字典字面量
        for placeholder, original in dict_placeholders.items():
            content = content.replace(placeholder, original)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        console.print(f"  [green]✅ {rel_path}[/green]")

    # 3. 配置 pyproject.toml
    console.print("\n[bold]⚙️  配置 pyproject.toml...[/bold]")

    # 保存 [tool.aury] 配置（包含 package 与 app）
    proj_config = ProjectConfig(package=package_name_snake, app="main:app")
    if save_project_config(proj_config, base_path):
        if package_name_snake:
            console.print(f"  [green]✅ 已保存包配置: [tool.aury] package = \"{package_name_snake}\"[/green]")
        console.print("  [green]✅ 已保存入口配置: [tool.aury] app = \"main:app\"[/green]")

    if _append_ruff_config(base_path):
        console.print("  [green]✅ 已添加 ruff 和 pytest 配置[/green]")
    
    if _append_dev_deps_config(base_path):
        console.print("  [green]✅ 已添加 [dependency-groups] dev 配置[/green]")

    # 4. 初始化数据库迁移
    console.print("\n[bold]📦 初始化数据库迁移...[/bold]")
    if _init_migrations(base_path, package_name_snake):
        console.print("  [green]✅ 已创建 migrations/ 目录和配置[/green]")
    else:
        console.print("  [dim]ℹ️  migrations/ 目录已存在，跳过[/dim]")

    # 5. 生成开发文档 (aury_docs/) - 动态扫描模板目录
    console.print("\n[bold]📚 生成开发文档...[/bold]")
    aury_docs_tpl_dir = TEMPLATES_DIR / "aury_docs"
    aury_docs_dir = base_path / "aury_docs"
    aury_docs_dir.mkdir(parents=True, exist_ok=True)
    docs_count = 0
    if aury_docs_tpl_dir.exists():
        for tpl_path in sorted(aury_docs_tpl_dir.glob("*.md.tpl")):
            output_name = tpl_path.stem  # 去掉 .tpl 后缀，保留 .md
            output_path = aury_docs_dir / output_name
            if output_path.exists() and not force:
                continue
            try:
                content = tpl_path.read_text(encoding="utf-8")
                content = content.format(**template_vars)
                output_path.write_text(content, encoding="utf-8")
                docs_count += 1
            except Exception:
                pass
    console.print(f"  [green]✅ 已生成 {docs_count} 个文档到 aury_docs/[/green]")

    # 6. 生成 Docker 配置
    if with_docker:
        console.print("\n[bold]🐳 生成 Docker 配置...[/bold]")
        from .docker import docker_init
        docker_init(force=force)

    # 7. 显示结果
    console.print("\n")

    tree = Tree(f"[bold cyan]{project_name}/[/bold cyan]")
    tree.add("[dim].env.example[/dim]")
    tree.add("[dim].gitignore[/dim]")
    tree.add("[dim]alembic.ini[/dim]")
    tree.add("[dim]pyproject.toml[/dim]")
    tree.add("[dim]README.md[/dim]")
    tree.add("[dim]AGENTS.md[/dim]")
    tree.add("[blue]aury_docs/[/blue]")
    if with_docker:
        tree.add("[dim]Dockerfile[/dim]")
        tree.add("[dim]docker-compose.yml[/dim]")
        tree.add("[dim].dockerignore[/dim]")

    # tests 目录始终在项目根目录
    tests_branch = tree.add("[blue]tests/[/blue]")
    tests_branch.add("[dim]conftest.py[/dim]")
    
    # main.py 始终在根目录
    tree.add("[green]main.py[/green]")
    
    if package_name_snake:
        pkg_branch = tree.add(f"[bold blue]{package_name_snake}/[/bold blue]")
        pkg_branch.add("[green]config.py[/green]")
        pkg_branch.add("[blue]api/[/blue]")
        pkg_branch.add("[blue]services/[/blue]")
        pkg_branch.add("[blue]models/[/blue]")
        pkg_branch.add("[blue]repositories/[/blue]")
        pkg_branch.add("[blue]schemas/[/blue]")
        pkg_branch.add("[blue]exceptions/[/blue]")
        pkg_branch.add("[blue]tasks/[/blue]")
        pkg_branch.add("[blue]schedules/[/blue]")
    else:
        tree.add("[green]config.py[/green]")
        tree.add("[blue]api/[/blue]")
        tree.add("[blue]services/[/blue]")
        tree.add("[blue]models/[/blue]")
        tree.add("[blue]repositories/[/blue]")
        tree.add("[blue]schemas/[/blue]")
        tree.add("[blue]exceptions/[/blue]")
        tree.add("[blue]tasks/[/blue]")
        tree.add("[blue]schedules/[/blue]")

    migrations_branch = tree.add("[blue]migrations/[/blue]")
    migrations_branch.add("[dim]env.py[/dim]")
    migrations_branch.add("[dim]versions/[/dim]")

    console.print(tree)

    # 下一步提示
    console.print("\n[bold green]✨ 项目初始化完成！[/bold green]\n")
    console.print("[bold]下一步：[/bold]")
    console.print("  1. 安装开发依赖：")
    console.print("     [cyan]uv sync --group dev[/cyan]")
    console.print("     [dim]dev 组包含: pytest, pytest-asyncio, pytest-cov, ruff, mypy, watchfiles（用于稳定热重载）[/dim]")
    console.print("  2. 复制并编辑环境变量：")
    console.print("     [cyan]cp .env.example .env[/cyan]")
    console.print("     [dim]# 编辑 .env 配置数据库连接等[/dim]")
    console.print("  3. 启动开发服务器：")
    console.print("     [cyan]aury server dev[/cyan]")
    console.print("  4. 访问 API 文档：")
    console.print("     [cyan]http://127.0.0.1:8000/docs[/cyan]")
    console.print()
    console.print("[bold]常用命令：[/bold]")
    console.print("  [cyan]aury generate crud user -i[/cyan]  # 生成 CRUD（交互式）")
    console.print("  [cyan]aury generate model user -i[/cyan] # 生成模型（交互式）")
    console.print("  [cyan]aury migrate make -m \"xxx\"[/cyan] # 创建迁移")
    console.print("  [cyan]aury migrate up[/cyan]             # 执行迁移")
    console.print("  [cyan]aury server prod[/cyan]           # 生产模式")
    console.print()
    console.print("[dim]💡 使用 -i 参数可交互式配置字段、类型、约束等[/dim]")
    console.print()
    console.print("[dim]详细文档: https://github.com/AuriMyth/aury-boot[/dim]")


__all__ = ["init", "init_admin_console_module"]

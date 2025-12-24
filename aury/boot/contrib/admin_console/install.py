from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from aury.boot.common.logging import logger

from .auth import BasicAdminAuthBackend, BearerWhitelistAdminAuthBackend
from .discovery import load_project_admin_module
from .utils import import_from_string


def _require_sqladmin():
    try:
        from sqladmin import Admin
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "未安装 sqladmin。请先安装: uv add \"aury-boot[admin]\" 或 uv add sqladmin"
        ) from exc


def _resolve_auth_backend(app: Any, config: Any, module: Any | None):
    """解析 SQLAdmin authentication_backend。

    优先级（与项目现有 autodiscover 风格一致）：
    1) settings: ADMIN_AUTH_BACKEND="module:attr"（完全覆盖）
    2) 项目模块: register_admin_auth(config) -> backend（覆盖内置）
    3) 内置 basic/bearer/none
    """
    admin_cfg = getattr(config, "admin", None)
    auth_cfg = getattr(admin_cfg, "auth", None)

    mode = getattr(auth_cfg, "mode", "basic")
    backend_path = getattr(auth_cfg, "backend", None)
    secret_key = getattr(auth_cfg, "secret_key", None)

    # 生产环境安全约束
    if getattr(config, "is_production", False):
        if mode == "none":
            raise ValueError("生产环境不允许 ADMIN_AUTH_MODE=none，请使用 basic/bearer 或自定义 backend")
        if not secret_key or str(secret_key).strip() in {"CHANGE_ME", "changeme"}:
            raise ValueError("生产环境启用管理后台时必须设置 ADMIN_AUTH_SECRET_KEY（且不能为 CHANGE_ME）")

    # 1) 显式 backend 覆盖
    if backend_path:
        obj = import_from_string(str(backend_path).strip())
        backend = obj(config) if callable(obj) else obj
        if backend is None:
            raise ValueError(f"ADMIN_AUTH_BACKEND={backend_path!r} 返回 None")
        logger.info("管理后台认证：使用 settings 指定的自定义 backend")
        return backend

    # 2) 项目模块覆盖
    if module is not None and hasattr(module, "register_admin_auth"):
        backend = module.register_admin_auth(config)  # type: ignore[attr-defined]
        if backend is None:
            raise ValueError("register_admin_auth(config) 返回 None")
        logger.info("管理后台认证：使用项目模块 register_admin_auth 提供的 backend")
        return backend

    # 3) 内置兜底
    if mode in {"custom", "jwt"}:
        raise ValueError(
            f"ADMIN_AUTH_MODE={mode!r} 需要提供 ADMIN_AUTH_BACKEND 或在项目模块实现 register_admin_auth(config)"
        )

    if mode == "none":
        logger.warning("管理后台认证：已关闭认证（ADMIN_AUTH_MODE=none）")
        return None

    if not secret_key:
        raise ValueError("启用管理后台认证需要设置 ADMIN_AUTH_SECRET_KEY")

    if mode == "basic":
        username = getattr(auth_cfg, "basic_username", None)
        password = getattr(auth_cfg, "basic_password", None)
        if not username or not password:
            raise ValueError("ADMIN_AUTH_MODE=basic 需要设置 ADMIN_AUTH_BASIC_USERNAME/ADMIN_AUTH_BASIC_PASSWORD")
        return BasicAdminAuthBackend(username=username, password=password, secret_key=secret_key)

    if mode == "bearer":
        tokens = list(getattr(auth_cfg, "bearer_tokens", []) or [])
        if not tokens:
            raise ValueError("ADMIN_AUTH_MODE=bearer 需要设置 ADMIN_AUTH_BEARER_TOKENS（token 白名单）")
        return BearerWhitelistAdminAuthBackend(tokens=tokens, secret_key=secret_key)

    raise ValueError(f"未知的 ADMIN_AUTH_MODE: {mode!r}")


def _register_views(admin: Any, module: Any | None) -> None:
    """注册项目侧 views。"""
    if module is None:
        logger.info("管理后台：未发现项目 admin-console 模块，跳过 views 注册")
        return

    if hasattr(module, "register_admin"):
        module.register_admin(admin)  # type: ignore[attr-defined]
        logger.info("管理后台：已通过 register_admin(admin) 注册 views")
        return

    views = getattr(module, "ADMIN_VIEWS", None)
    if views:
        for view_cls in list(views):
            admin.add_view(view_cls)
        logger.info("管理后台：已通过 ADMIN_VIEWS 注册 views")
        return

    logger.info("管理后台：项目模块已加载，但未提供 register_admin/ADMIN_VIEWS，跳过 views 注册")


def install_admin_console(app: Any, config: Any | None = None):
    """安装 SQLAdmin 管理后台到 FastAPI/FoundationApp。

    - 默认路径：/api/admin-console（可通过 ADMIN_PATH 覆盖）
    - 认证：默认 basic/bearer（可通过 ADMIN_AUTH_* 配置，或自定义 backend 覆盖）
    - 视图：可通过项目模块 register_admin(admin) 或 ADMIN_VIEWS 提供
    - 引擎：支持同步或异步 SQLAlchemy Engine（AsyncEngine）

    返回：
        sqladmin.Admin 实例；若未启用（ADMIN_ENABLED=false）返回 None
    """
    _require_sqladmin()
    from sqladmin import Admin

    if config is None:
        from aury.boot.application.config import BaseConfig

        config = BaseConfig()

    admin_cfg = getattr(config, "admin", None)
    if not getattr(admin_cfg, "enabled", False):
        logger.debug("管理后台未启用（ADMIN_ENABLED=false），跳过安装")
        return None

    # 1) 自动发现项目模块（用于 auth/views）
    module = load_project_admin_module(app, config)

    # 2) 解析认证后端（可能为 None）
    auth_backend = _resolve_auth_backend(app, config, module)

    # 3) 构建 Engine（支持同步/异步）
    db_url = getattr(admin_cfg, "database_url", None) or getattr(config.database, "url", "")
    if not db_url:
        raise ValueError("无法确定管理后台数据库 URL：请设置 ADMIN_DATABASE_URL 或 DATABASE_URL")

    def _is_async_url(url: str) -> bool:
        return any(s in url for s in ["+asyncpg", "+aiosqlite", "+aiomysql", "+asyncmy"])

    try:
        if _is_async_url(str(db_url)):
            engine = create_async_engine(str(db_url), future=True)
        else:
            engine = create_engine(str(db_url), future=True)
    except Exception as exc:
        raise RuntimeError(
            "创建管理后台数据库 Engine 失败。请检查 ADMIN_DATABASE_URL/DATABASE_URL 与对应驱动是否可用。"
        ) from exc

    base_url = getattr(admin_cfg, "path", "/api/admin-console")

    # 4) 安装 admin（engine 可为同步或异步）
    admin = Admin(app=app, engine=engine, base_url=base_url, authentication_backend=auth_backend)

    # 5) 注册 views
    _register_views(admin, module)

    logger.info(f"✅ 管理后台已启用：{base_url}")
    return admin



from __future__ import annotations

import importlib


def import_from_string(path: str):
    """从 'module:attr' 动态导入对象。

    与 commands/server 的 app 导入风格保持一致。
    """
    if ":" not in path:
        raise ValueError(f"无效导入路径: {path!r}（应为 'module:attr'）")
    module_path, attr = path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise AttributeError(f"模块 {module_path!r} 中不存在 {attr!r}") from exc


def derive_sync_database_url(database_url: str) -> str:
    """从异步 URL 推导同步 URL（用于 SQLAdmin）。

    说明：
    - sqladmin 通常要求同步 SQLAlchemy Engine（create_engine）
    - 本函数只做最常见的 driver 映射；如需完全自定义请用 ADMIN_DATABASE_URL 覆盖
    """
    # SQLite
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)

    # PostgreSQL
    if database_url.startswith("postgresql+asyncpg://"):
        # 推荐 psycopg（psycopg3）
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

    # MySQL
    if database_url.startswith("mysql+aiomysql://"):
        return database_url.replace("mysql+aiomysql://", "mysql+pymysql://", 1)

    # 其他情况：认为已经是同步 URL
    return database_url



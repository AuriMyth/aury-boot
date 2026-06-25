"""Compatibility hooks for PostgreSQL-compatible database products."""

from __future__ import annotations

import os
import re
from typing import Any

_PRODUCT_MARKERS = ("gaussdb", "opengauss", "kingbase")


def _env_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _compat_mode() -> str:
    mode = _env_value(
        "DATABASE__POSTGRES_COMPAT_MODE",
        "DATABASE_POSTGRES_COMPAT_MODE",
        default="auto",
    ).lower()
    if mode not in {"auto", "off", "force"}:
        return "auto"
    return mode


def _compat_version() -> str:
    return _env_value(
        "DATABASE__POSTGRES_COMPAT_VERSION",
        "DATABASE_POSTGRES_COMPAT_VERSION",
        default="9.6",
    )


def _parse_version(value: str) -> tuple[int, ...]:
    parts = [
        int(part)
        for part in re.split(r"[._-]", str(value or "").strip())
        if part.isdigit()
    ]
    return tuple(parts or [9, 6])


def _is_postgresql_url(database_url: str | None) -> bool:
    normalized = str(database_url or "").strip().lower()
    if not normalized:
        return True
    return normalized.startswith(("postgresql://", "postgresql+", "postgres://", "postgres+"))


def _is_compat_product(version_text: str) -> bool:
    normalized = str(version_text or "").lower()
    return any(marker in normalized for marker in _PRODUCT_MARKERS)


def install_postgres_compat(database_url: str | None = None) -> None:
    """Install SQLAlchemy PostgreSQL dialect compatibility patches.

    Some PostgreSQL-compatible domestic database products return version strings
    such as ``GaussDB(...)`` or ``KingbaseES ...``. SQLAlchemy's PostgreSQL
    dialect can fail during startup because it expects a PostgreSQL-prefixed
    version string. In ``auto`` mode this patch only falls back for known
    compatible products; set ``DATABASE__POSTGRES_COMPAT_MODE=off`` to disable
    it, or ``force`` to always use the configured fallback version.
    """
    mode = _compat_mode()
    if mode == "off" or not _is_postgresql_url(database_url):
        return

    try:
        from sqlalchemy.dialects.postgresql import asyncpg as pg_asyncpg
        from sqlalchemy.dialects.postgresql import base as pg_base
    except Exception:
        return

    for dialect_cls in (pg_base.PGDialect, pg_asyncpg.PGDialect_asyncpg):
        if getattr(dialect_cls, "_aury_postgres_compat_patched", False):
            continue

        original = dialect_cls._get_server_version_info
        dialect_cls._aury_original_get_server_version_info = original

        def patched(self: Any, connection: Any, _original: Any = original) -> tuple[int, ...]:
            try:
                return _original(self, connection)
            except AssertionError:
                current_mode = _compat_mode()
                if current_mode == "off":
                    raise

                version_text = connection.exec_driver_sql("select pg_catalog.version()").scalar()
                if current_mode == "force" or _is_compat_product(str(version_text or "")):
                    return _parse_version(_compat_version())
                raise

        dialect_cls._get_server_version_info = patched
        dialect_cls._aury_postgres_compat_patched = True


__all__ = ["install_postgres_compat"]

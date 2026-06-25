from aury.boot.infrastructure.database import postgres_compat


def test_postgres_compat_parse_version_defaults() -> None:
    assert postgres_compat._parse_version("9.6") == (9, 6)
    assert postgres_compat._parse_version("12.3-compat") == (12, 3)
    assert postgres_compat._parse_version("") == (9, 6)


def test_postgres_compat_detects_known_products() -> None:
    assert postgres_compat._is_compat_product("GaussDB Kernel V500R002")
    assert postgres_compat._is_compat_product("openGauss 5.0")
    assert postgres_compat._is_compat_product("KingbaseES V009R001C010")
    assert not postgres_compat._is_compat_product("PostgreSQL 16.1")


def test_postgres_compat_off_mode_skips_patch(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE__POSTGRES_COMPAT_MODE", "off")
    postgres_compat.install_postgres_compat("postgresql+asyncpg://user:pass@localhost/db")

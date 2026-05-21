from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import Integer, String, create_engine
from sqlalchemy.orm import Mapped, Session, declared_attr, mapped_column
from sqlalchemy.orm.exc import StaleDataError

from aury.boot.domain.exceptions import VersionConflictError
from aury.boot.domain.models import Base, IDMixin, Model, VersionedModel
from aury.boot.domain.repository.impl import BaseRepository
from aury.boot.domain.transaction import _transaction_depth


class VersionedProbe(VersionedModel):
    __tablename__ = "test_repository_versioned_probe"

    name: Mapped[str] = mapped_column(String(50))


class BusinessVersionProbe(Model):
    __tablename__ = "test_repository_business_version_probe"

    name: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(50))


class CustomLockProbe(IDMixin, Base):
    __tablename__ = "test_repository_custom_lock_probe"

    name: Mapped[str] = mapped_column(String(50))
    lock_version: Mapped[int] = mapped_column("revision_no", Integer, default=1, nullable=False)

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:  # noqa: N805
        return {"version_id_col": cls.lock_version}


class FakeAsyncSession:
    def __init__(
        self,
        flush_error: Exception | None = None,
        bulk_update_error: Exception | None = None,
    ) -> None:
        self.flush_error = flush_error
        self.bulk_update_error = bulk_update_error
        self.flushed = False
        self.refreshed = False
        self.committed = False
        self.rolled_back = False
        self.deleted = False
        self.bulk_update_mappings_args: tuple[type, list[dict[str, Any]]] | None = None

    async def flush(self) -> None:
        self.flushed = True
        if self.flush_error is not None:
            raise self.flush_error

    async def refresh(self, _entity: object) -> None:
        self.refreshed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def delete(self, _entity: object) -> None:
        self.deleted = True

    async def run_sync(self, fn: Any) -> Any:
        return fn(self)

    def bulk_update_mappings(self, model_class: type, data_list: list[dict[str, Any]]) -> None:
        self.bulk_update_mappings_args = (model_class, data_list)
        if self.bulk_update_error is not None:
            raise self.bulk_update_error


def test_version_mixin_uses_real_column_and_sqlalchemy_increments_version() -> None:
    assert VersionedProbe.__mapper__.version_id_col is VersionedProbe.__table__.c.version

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[VersionedProbe.__table__])

    with Session(engine) as session:
        row = VersionedProbe(name="initial")
        session.add(row)
        session.commit()

        assert row.version == 1

        row.name = "updated"
        session.commit()

        assert row.version == 2


def test_business_version_field_is_not_mapper_optimistic_lock() -> None:
    assert BusinessVersionProbe.__mapper__.version_id_col is None

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[BusinessVersionProbe.__table__])

    with Session(engine) as session:
        row = BusinessVersionProbe(name="initial", version="1.0.0")
        session.add(row)
        session.commit()

        row.version = "1.0.1"
        session.commit()

        assert row.version == "1.0.1"


def test_sqlalchemy_versioning_detects_concurrent_stale_update() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[VersionedProbe.__table__])

    with Session(engine) as session:
        row = VersionedProbe(name="initial")
        session.add(row)
        session.commit()
        row_id = row.id

    session_a = Session(engine)
    session_b = Session(engine)
    try:
        row_a = session_a.get(VersionedProbe, row_id)
        row_b = session_b.get(VersionedProbe, row_id)
        assert row_a is not None
        assert row_b is not None

        row_a.name = "from-a"
        session_a.commit()

        row_b.name = "from-b"
        with pytest.raises(StaleDataError):
            session_b.commit()
    finally:
        session_a.close()
        session_b.close()


@pytest.mark.asyncio
async def test_repository_allows_business_version_field_update() -> None:
    session = FakeAsyncSession()
    repo = BaseRepository(session, BusinessVersionProbe)  # type: ignore[arg-type]
    row = BusinessVersionProbe(name="initial", version="1.0.0")

    result = await repo.update(row, {"name": "updated", "version": "1.0.1"})

    assert result is row
    assert row.name == "updated"
    assert row.version == "1.0.1"
    assert session.flushed is True
    assert session.refreshed is True
    assert session.committed is True


@pytest.mark.asyncio
async def test_repository_skips_actual_optimistic_lock_key_from_update_data() -> None:
    session = FakeAsyncSession()
    repo = BaseRepository(session, CustomLockProbe)  # type: ignore[arg-type]
    row = CustomLockProbe(name="initial", lock_version=3)

    await repo.update(row, {"name": "updated", "lock_version": 999})

    assert row.name == "updated"
    assert row.lock_version == 3


@pytest.mark.asyncio
async def test_repository_converts_stale_data_error_and_rolls_back_auto_commit_path() -> None:
    session = FakeAsyncSession(flush_error=StaleDataError("stale row"))
    repo = BaseRepository(session, VersionedProbe)  # type: ignore[arg-type]

    with pytest.raises(VersionConflictError):
        await repo.update(VersionedProbe(name="initial"))

    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_repository_leaves_rollback_to_outer_transaction_on_stale_data_error() -> None:
    session = FakeAsyncSession(flush_error=StaleDataError("stale row"))
    repo = BaseRepository(session, VersionedProbe)  # type: ignore[arg-type]
    token = _transaction_depth.set(1)

    try:
        with pytest.raises(VersionConflictError):
            await repo.update(VersionedProbe(name="initial"))
    finally:
        _transaction_depth.reset(token)

    assert session.rolled_back is False


@pytest.mark.asyncio
async def test_repository_delete_converts_stale_data_error_and_rolls_back_auto_commit_path() -> None:
    session = FakeAsyncSession(flush_error=StaleDataError("stale row"))
    repo = BaseRepository(session, VersionedProbe)  # type: ignore[arg-type]

    with pytest.raises(VersionConflictError):
        await repo.delete(VersionedProbe(name="initial"), soft=False)

    assert session.deleted is True
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_repository_bulk_update_requires_version_for_optimistic_lock_model() -> None:
    session = FakeAsyncSession()
    repo = BaseRepository(session, VersionedProbe)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="缺少版本字段: version"):
        await repo.bulk_update([{"id": 1, "name": "updated"}])

    assert session.bulk_update_mappings_args is None


@pytest.mark.asyncio
async def test_repository_bulk_update_allows_business_version_model_without_version_field() -> None:
    session = FakeAsyncSession()
    repo = BaseRepository(session, BusinessVersionProbe)  # type: ignore[arg-type]

    await repo.bulk_update([{"id": 1, "name": "updated"}])

    assert session.bulk_update_mappings_args == (BusinessVersionProbe, [{"id": 1, "name": "updated"}])
    assert session.flushed is True
    assert session.committed is True


@pytest.mark.asyncio
async def test_repository_bulk_update_converts_stale_data_error() -> None:
    session = FakeAsyncSession(bulk_update_error=StaleDataError("stale row"))
    repo = BaseRepository(session, VersionedProbe)  # type: ignore[arg-type]

    with pytest.raises(VersionConflictError):
        await repo.bulk_update([{"id": 1, "name": "updated", "version": 1}])

    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_repository_bulk_update_converts_sqlalchemy_key_error_to_value_error() -> None:
    session = FakeAsyncSession(bulk_update_error=KeyError("version"))
    repo = BaseRepository(session, VersionedProbe)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="批量更新数据缺少字段: version"):
        await repo.bulk_update([{"id": 1, "name": "updated", "version": 1}])


@pytest.mark.asyncio
async def test_repository_bulk_update_uses_custom_optimistic_lock_attribute_key() -> None:
    session = FakeAsyncSession()
    repo = BaseRepository(session, CustomLockProbe)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="缺少版本字段: lock_version"):
        await repo.bulk_update([{"id": 1, "name": "updated", "version": 1}])

    await repo.bulk_update([{"id": 1, "name": "updated", "lock_version": 1}])

    assert session.bulk_update_mappings_args == (
        CustomLockProbe,
        [{"id": 1, "name": "updated", "lock_version": 1}],
    )

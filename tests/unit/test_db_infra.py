"""Unit tests for the behavioral persistence infrastructure.

Runs against a synchronous in-memory SQLite engine only. These tests verify
the portable primitives (naming conventions, mixins, column types, config,
engine factories); product-model behavior is owned by the behavioral model
agent and covered elsewhere.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from smorx_behavior.db.base import Base, metadata
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.db.mixins import TimestampMixin, UUIDPkMixin
from smorx_behavior.db.settings import DEFAULT_DATABASE_URL, DBConfig
from smorx_behavior.db.types import GUID, JSONType, UTCDateTime
from sqlalchemy import ForeignKey, Integer, String, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship


class SampleRecord(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "infra_sample_record"

    external_ref: Mapped[uuid.UUID] = mapped_column(GUID, unique=True)
    payload: Mapped[dict] = mapped_column(JSONType)
    seen_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ParentRow(Base):
    __tablename__ = "infra_parent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))


class ChildRow(Base):
    __tablename__ = "infra_child"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("infra_parent.id"))
    parent: Mapped[ParentRow] = relationship(ParentRow)


def test_base_metadata_naming_convention() -> None:
    for key in ("pk", "ix", "ck", "uq", "fk"):
        assert key in Base.metadata.naming_convention
        assert isinstance(Base.metadata.naming_convention[key], str)
    assert metadata is Base.metadata


def test_uuid_timestamp_json_roundtrip_on_sqlite() -> None:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    ref = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            SampleRecord(
                external_ref=ref,
                payload={"change_id": 184, "tags": ["AUTH-017"]},
                seen_at=datetime.fromisoformat("2026-01-02T03:04:05"),
            )
        )
        session.commit()

    with Session(engine) as session:
        row = session.query(SampleRecord).one()
        assert row.external_ref == ref
        assert isinstance(row.external_ref, uuid.UUID)
        assert row.payload == {"change_id": 184, "tags": ["AUTH-017"]}
        assert isinstance(row.payload, dict)
        assert row.seen_at.tzinfo is not None
        assert row.created_at is not None
        assert row.updated_at is not None


def test_dbconfig_from_env_defaults_to_sqlite(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_MAX_OVERFLOW", raising=False)

    config = DBConfig.from_env()
    assert config.database_url == DEFAULT_DATABASE_URL
    assert config.database_url == "sqlite+aiosqlite:///./smorx.db"
    assert config.pool_size is None
    assert config.max_overflow is None
    assert config.resolved_url() == DEFAULT_DATABASE_URL


def test_sync_engine_creates_tables_and_infers_fks() -> None:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= {
        "infra_sample_record",
        "infra_parent",
        "infra_child",
    }

    fks = inspector.get_foreign_keys("infra_child")
    assert len(fks) == 1
    assert fks[0]["constrained_columns"] == ["parent_id"]
    assert fks[0]["referred_table"] == "infra_parent"
    assert fks[0]["referred_columns"] == ["id"]
    assert fks[0]["name"] == "fk_infra_child_parent_id_infra_parent"

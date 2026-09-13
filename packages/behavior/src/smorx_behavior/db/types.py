"""Portable, dialect-agnostic SQLAlchemy column types."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, TypeDecorator, Uuid

__all__ = ["GUID", "JSONType", "UTCDateTime"]


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware ``DateTime`` that stores UTC on every backend.

    On SQLite (no native timezone support) naive datetimes are coerced to
    UTC on bind and re-attached as UTC on result. On capable backends the
    timezone-aware column type is used and values are normalized to UTC.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


GUID = Uuid


# Generic JSON: dialect-agnostic; JSONB / backend-specific variants are a
# deliberate, documented follow-up for PostgreSQL.
JSONType = JSON

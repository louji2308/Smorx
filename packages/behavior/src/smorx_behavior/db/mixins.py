"""Shared declarative mixins for primary keys and timestamps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from smorx_behavior.db.types import GUID, UTCDateTime


class UUIDPkMixin:
    """GUID primary key, portable across integer-only and native-UUID backends."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """UTC creation/update timestamps.

    ``created_at`` is server-defaulted and immutable by contract; the
    ``updated_at`` column refreshes on every UPDATE via ``onupdate``. Safe on
    SQLite in-memory ``create_all`` with no external extension required.
    """

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )


__all__ = ["TimestampMixin", "UUIDPkMixin"]

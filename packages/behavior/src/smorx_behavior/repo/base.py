"""Generic read/write persistence helpers over the real behavioral models.

Phase 2 (implementation plan step 2.5, deliverable "repository/data access
layer"). Every helper is ORM-contract driven: it targets the declarative
models exported by ``smorx_behavior.models`` and never bypasses the mapped
columns or relationships.

Destructive operations are policy-gated (AGENTS.md section 13: "destructive
operations must be policy-controlled"). :func:`delete` therefore raises
unless the caller explicitly opts in with ``allow_destructive=True``.

Evidence rows are recorded through ``smorx_behavior.evidence.service`` (the
canonical content-addressed entry point). :func:`ensure_evidence` is the
no-dependency fallback kept here so seeds and tooling stay functional before
or without that service; it adds nothing the service does not already own.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from smorx_behavior.models import Evidence

ModelT = TypeVar("ModelT")

__all__ = [
    "count",
    "delete",
    "digest",
    "ensure_evidence",
    "get",
    "get_or_create",
    "list_",
    "query",
    "save",
]


def digest(*parts: str) -> str:
    """Return a deterministic SHA-256 hex digest of the joined ``parts``."""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def save(session: Session, instance: Any) -> Any:
    """Persist ``instance`` (add + flush) and return it."""
    session.add(instance)
    session.flush()
    return instance


def get(session: Session, model: type[ModelT], key: Any) -> ModelT | None:
    """Return the ``model`` row addressed by primary key ``key`` or ``None``."""
    return session.get(model, key)


def list_(
    session: Session,
    model: type[ModelT],
    *,
    order_by: tuple[Any, ...] | None = None,
    limit: int | None = None,
    **filters: Any,
) -> list[ModelT]:
    """Return rows matching every equality ``filters`` in stable order.

    ``None`` filter values expand to ``IS NULL``. Ordering defaults to the
    primary key so results are reproducible across runs.
    """
    statement = select(model)
    for name, value in filters.items():
        column = getattr(model, name)
        statement = statement.where(column.is_(None) if value is None else column == value)
    if order_by is None:
        order_by = (cast(Any, model).id,)
    statement = statement.order_by(*order_by)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def query(
    session: Session,
    model: type[ModelT],
    *criteria: Any,
    order_by: tuple[Any, ...] | None = None,
    limit: int | None = None,
) -> list[ModelT]:
    """Return rows matching the raw ``criteria`` in stable order."""
    statement = select(model).where(*criteria)
    if order_by is None:
        order_by = (cast(Any, model).id,)
    statement = statement.order_by(*order_by)
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def count(session: Session, model: type[ModelT], **filters: Any) -> int:
    """Return the number of ``model`` rows matching the equality ``filters``."""
    statement = select(func.count()).select_from(model)
    for name, value in filters.items():
        column = getattr(model, name)
        statement = statement.where(column.is_(None) if value is None else column == value)
    return int(session.scalar(statement))


def get_or_create(
    session: Session,
    model: type[ModelT],
    key: Any,
    defaults: Mapping[str, Any] | None = None,
) -> tuple[ModelT, bool]:
    """Return ``(row, created)`` for the deterministic primary key ``key``.

    When the row already exists the existing instance is returned unchanged
    (safe for idempotent deterministic seeds). Otherwise a row with ``id ==
    key`` and ``defaults`` is inserted.
    """
    existing = session.get(model, key)
    if existing is not None:
        return existing, False
    instance = cast(Any, model)(id=key, **(defaults or {}))
    session.add(instance)
    session.flush()
    return instance, True


def delete(session: Session, instance: Any, *, allow_destructive: bool = False) -> None:
    """Delete ``instance``; destructive deletion is policy-blocked by default.

    Raises ``RuntimeError`` unless ``allow_destructive=True`` is passed
    explicitly. The guard exists so accidental destructive operations cannot
    silently reach the database (AGENTS.md section 13).
    """
    if not allow_destructive:
        raise RuntimeError(
            "destructive delete is policy-blocked (AGENTS.md section 13); "
            "pass allow_destructive=True to override"
        )
    session.delete(instance)
    session.flush()


def ensure_evidence(session: Session, *, content_hash: str, **fields: Any) -> Evidence:
    """Return the evidence row for ``content_hash``, creating it if absent.

    Content-addressed and idempotent: the unique ``Evidence.hash`` constraint
    means a given digest maps to exactly one row. This is the fallback path;
    ``smorx_behavior.evidence.service.record_evidence`` is the canonical
    entry point and is preferred whenever it is importable.
    """
    existing = session.scalar(select(Evidence).where(Evidence.hash == content_hash))
    if existing is not None:
        return existing
    row = Evidence(hash=content_hash, **fields)
    session.add(row)
    session.flush()
    return row

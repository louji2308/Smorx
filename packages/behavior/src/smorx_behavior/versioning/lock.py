"""Lock enforcement for immutable-reference objects (implementation plan 2.5, ADR-0005).

A locked object is an immutable reference. Normal operations must never mutate a
locked row in place: the only legal way to reach a different state is to create
a new identity (see ``smorx_behavior.versioning.service.bump``). Unlocking is
NOT a normal operation — the controlled ``force_set`` escape hatch exists only
for tests and documented repair procedures and emits a loud warning.

Locked state is carried by the existing ``locked`` boolean column
(``ImmutableObjectMixin`` / inline declarations); a true value marks an
immutable reference. Models that carry only ``version`` (``Ghost``,
``IntentItem``, ``BehavioralDelta``, ``RepairPackage``) have no lock column and
are by definition never locked.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

__all__ = [
    "VersionLockedError",
    "VersioningError",
    "assert_not_locked",
    "force_set",
    "is_locked",
    "lock",
]

#: A locked object may never be unlocked through normal operations (ADR-0005 I9).
LOCKED_STATE = True


class VersioningError(Exception):
    """Base error for the version/lock policy service."""


class VersionLockedError(VersioningError):
    """Raised when an operation mutates or is attempted on a locked object.

    Args:
        name: ORM model class name (e.g. ``"Certificate"``).
        key: the object's immutable identity (its ``id``).
        message: optional human-readable detail.
    """

    def __init__(self, name: str, key: Any, *, message: str | None = None) -> None:
        self.name = name
        self.key = key
        self.message = message or (
            f"{name}(id={key}) is locked and immutable; create a new version "
            "instead of mutating it in place"
        )
        super().__init__(self.message)


def _has_column(obj: Any, name: str) -> bool:
    table = getattr(obj, "__table__", None)
    return table is not None and name in table.c


def is_locked(obj: Any) -> bool:
    """Return ``True`` when ``obj`` carries an immutable lock.

    Models without a ``locked`` column are never locked. An unflushed new
    object (attribute still ``None``) is treated as unlocked.
    """
    if not _has_column(obj, "locked"):
        return False
    return bool(getattr(obj, "locked", False))


def assert_not_locked(obj: Any) -> None:
    """Raise :class:`VersionLockedError` when ``obj`` is locked, else return.

    This is the guard every in-place mutation must pass before touching a row.
    """
    if is_locked(obj):
        raise VersionLockedError(type(obj).__name__, getattr(obj, "id", None))


def lock(session: Session, obj: Any) -> Any:
    """Permanently lock ``obj`` (``locked=True``) and flush.

    Idempotent: locking an already-locked object is a no-op and never raises.
    There is no normal unlock path once an object is locked.
    """
    if not _has_column(obj, "locked"):
        raise VersioningError(f"{type(obj).__name__} has no 'locked' column and cannot be locked")
    if not is_locked(obj):
        obj.locked = LOCKED_STATE
        session.add(obj)
        session.flush()
    return obj


def force_set(
    session: Session,
    obj: Any,
    *,
    locked: bool | None = None,
    version: int | None = None,
) -> Any:
    """Controlled repair/test-only state override.

    WARNING: bypasses the immutability contract and may unlock a locked object
    or rewrite its version. Intended exclusively for tests and documented
    repair procedures. Raises :class:`VersioningError` when ``version < 1``.
    """
    if locked is None and version is None:
        return obj
    warnings.warn(
        "force_set() bypasses the ADR-0005 immutability contract; tests/repair use ONLY",
        UserWarning,
        stacklevel=2,
    )
    if locked is not None:
        if not _has_column(obj, "locked"):
            raise VersioningError(
                f"{type(obj).__name__} has no 'locked' column; force_set(locked=...) cannot apply"
            )
        obj.locked = bool(locked)  # the only sanctioned path that may unlock
    if version is not None:
        if not _has_column(obj, "version"):
            raise VersioningError(
                f"{type(obj).__name__} has no 'version' column; force_set(version=...) cannot apply"
            )
        if version < 1:
            raise VersioningError(f"version must be an int >= 1, got {version!r}")
        obj.version = int(version)
    session.add(obj)
    session.flush()
    return obj

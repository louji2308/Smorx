"""Version/lock policy service for the behavioral model (implementation plan 2.5, ADR-0005).

Semantics (ADR-0005): an object is immutable once locked. Bumping the version of
a LOCKED object MUST NOT mutate history — it creates a NEW row (new ``id``) that
inherits the parent's data, with ``version + 1``, an explicit parent reference,
and ``locked=False`` on the fresh identity. The historical row is never touched.
Version numbers are plain ints, kept ``>= 1``, and increment by exactly ``1``
across a lineage.

Documented bump rule (deterministic, one rule):

* **LOCKED object** -> a new identity row:
  - ``id`` is freshly generated (never reused).
  - every non-special column value is copied from the parent.
  - ``version = parent.version + 1``.
  - ``locked = False`` (the new version must be judged and locked on its own).
  - unique, non-primary-key string identity columns are re-bound as
    ``f"{base}@{version}"`` (mirroring ``smorx_contracts.versioning.immutable_key``;
    a trailing ``@<int>`` suffix already present is stripped first so repeated
    bumps keep the same base identity, e.g. ``cert-AUTH-017 -> cert-AUTH-017@2 ->
    cert-AUTH-017@3``).
  - the parent reference is recorded in the new row (see below).
* **UNLOCKED object** -> version is bumped **in place** (``obj.version += 1``) and
  the identity is retained. No parent reference is recorded because no new
  identity is created; the supplied ``note`` is ignored on this path.

Parent-reference recording — no schema change. Deterministic per model family:

1. If the model has a JSON dict column (first match in ``PARENT_JSON_FIELDS``,
   e.g. Certificate ``payload``, VerificationPlan ``strategy``, SemanticImpact
   ``scope``, Ghost ``payload``), the parent reference is stored under the
   reserved JSON key ``PARENT_RESERVED_KEY`` (``"__version_parent__"``) as
   ``{"id": "<parent id>", "version": <parent version>[, "note": ...]}``.
2. Else, if the model has a text/string column (first match in
   ``PARENT_TEXT_FIELDS``, e.g. Task ``description``, Probe...), a structural
   marker ``[version_parent:<parent id>;from_version:<parent version>]`` is
   appended to that field (a free-text ``note:<note>`` line is appended when a
   note is supplied). The marker is the ONLY parsed structure; ``get_lineage``
   reads the last marker in the field.
3. If neither a JSON dict column nor a text column exists (currently true for no
   versioned model; e.g. ``Claim`` would qualify only if a text field existed),
   bump raises :class:`~smorx_behavior.versioning.lock.VersioningError` because
   the parent reference cannot be preserved — history would be lost.

These constants are public so callers can inspect/override the canonical fields
without touching the schema.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String, Uuid

from smorx_behavior.versioning.lock import (
    VersioningError,
    is_locked,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

__all__ = [
    "MAX_LINEAGE_HOPS",
    "PARENT_JSON_FIELDS",
    "PARENT_RESERVED_KEY",
    "PARENT_TEXT_FIELDS",
    "TEXT_MARKER_RE",
    "bump",
    "get_lineage",
    "parent_storage",
    "snapshot",
]

#: JSON dict columns preferred, in order, for storing the parent reference.
PARENT_JSON_FIELDS: tuple[str, ...] = (
    "payload",
    "meta",
    "scope",
    "strategy",
    "verification_contract",
    "content",
    "environment",
    "inputs",
    "outputs",
    "plan",
    "token_usage",
    "machine_result",
)

#: Text/string columns preferred, in order, when no JSON dict column exists.
PARENT_TEXT_FIELDS: tuple[str, ...] = (
    "description",
    "summary",
    "provenance",
    "rationale",
    "message",
    "source",
    "source_ref",
    "created_by",
    "enforced_by",
    "owning_module",
    "note",
    "method",
    "expected",
    "statement",
    "rule",
    "title",
    "name",
)

#: Reserved JSON key carrying the parent reference inside the JSON dict field.
PARENT_RESERVED_KEY: str = "__version_parent__"

#: Structural text marker; ``get_lineage`` reads the LAST occurrence.
TEXT_MARKER_RE: re.Pattern[str] = re.compile(
    r"\[version_parent:([0-9a-fA-F-]{36});from_version:(\d+)\]"
)

#: Anti-runaway walk bound for lineage traversal (worse case is 1000 hops).
MAX_LINEAGE_HOPS: int = 1000

#: Columns never copied to a new identity (identity/versioned/timestamp columns).
_COPY_EXCLUDED: frozenset[str] = frozenset({"id", "version", "locked", "created_at", "updated_at"})

_VERSION_SUFFIX_RE = re.compile(r"@\d+$")


def _column_python_family(col: Any) -> str | None:
    """Return ``"json_dict"``, ``"uuid"``, ``"str"``, or ``None`` for a column.

    The classification drives both copy semantics and the parent-ref store, and
    stays dialect-agnostic (works on the in-memory SQLite test engine and on
    PostgreSQL later).
    """
    if isinstance(col.type, JSON):
        return "json_dict"
    if isinstance(col.type, Uuid):
        return "uuid"
    if isinstance(col.type, String):
        return "str"
    return None


def parent_storage(obj: Any) -> tuple[str, str] | None:
    """Return the canonical parent-ref store for ``obj``'s model as
    ``("json", fieldname)``, ``("text", fieldname)``, or ``None``.

    The result is guaranteed deterministic for a given model class. This is the
    single source of truth shared by ``bump`` and ``get_lineage``.
    """
    table = getattr(obj, "__table__", None)
    if table is None:
        return None
    for field in PARENT_JSON_FIELDS:
        if field in table.c and _column_python_family(table.c[field]) == "json_dict":
            return ("json", field)
    for field in PARENT_TEXT_FIELDS:
        if field in table.c and _column_python_family(table.c[field]) == "str":
            return ("text", field)
    return None


def _read_parent_ref(obj: Any) -> dict[str, Any] | None:
    """Return the immediate parent reference recorded on ``obj`` (or ``None``)."""
    storage = parent_storage(obj)
    if storage is None:
        return None
    kind, field = storage
    if kind == "json":
        data = getattr(obj, field, None) or {}
        ref = data.get(PARENT_RESERVED_KEY)
        return dict(ref) if isinstance(ref, dict) else None
    text = getattr(obj, field, None) or ""
    matches = TEXT_MARKER_RE.findall(str(text))
    if not matches:
        return None
    parent_id, parent_version = matches[-1]
    return {"id": parent_id, "version": int(parent_version)}


def _strip_version_suffix(value: str) -> str:
    """Strip a trailing ``@<int>`` identity suffix, if present (``key@2 -> key``)."""
    return _VERSION_SUFFIX_RE.sub("", value)


def _clone_row(parent: Any, new_version: int) -> Any:
    """Build a fresh, transient instance inheriting ``parent``'s column data."""
    cls = type(parent)
    new_obj = cls()
    for col in parent.__table__.columns:
        name = col.name
        if name in _COPY_EXCLUDED:
            continue
        value = getattr(parent, name, None)
        if value is None:
            continue  # carry the model default; never force a null over a default
        family = _column_python_family(col)
        if isinstance(value, (list, dict)):
            value = copy.deepcopy(value)
        if col.unique and family == "str":
            # Unique identity columns must not collide: bind to the new version.
            value = f"{_strip_version_suffix(str(value))}@{new_version}"
        setattr(new_obj, name, value)
    if "version" in parent.__table__.c:
        new_obj.version = int(new_version)
    if "locked" in parent.__table__.c:
        new_obj.locked = False
    return new_obj


def _record_parent_ref(new_obj: Any, parent: Any, note: str | None) -> None:
    """Store the parent reference on ``new_obj`` (decided by ``parent_storage``)."""
    storage = parent_storage(new_obj)
    if storage is None:
        raise VersioningError(
            f"{type(new_obj).__name__} has neither a JSON dict column ("
            f"{', '.join(PARENT_JSON_FIELDS[:4])!r}...) nor a text column "
            f"({', '.join(PARENT_TEXT_FIELDS[:4])!r}...); cannot preserve the "
            "parent reference — refusing to create a version identity"
        )
    kind, field = storage
    parent_id = str(parent.id)
    parent_version = int(parent.version)
    if kind == "json":
        data = dict(getattr(new_obj, field, None) or {})
        record: dict[str, Any] = {"id": parent_id, "version": parent_version}
        if note:
            record["note"] = note
        data[PARENT_RESERVED_KEY] = record
        setattr(new_obj, field, data)
        return
    marker = f"[version_parent:{parent_id};from_version:{parent_version}]"
    current = getattr(new_obj, field, None)
    text = marker if not current else f"{current}\n{marker}"
    if note:
        text = f"{text}\nnote:{note}"
    setattr(new_obj, field, text)


def _bump_in_place(session: Session, obj: Any) -> Any:
    """Documented unlocked rule: mutate the identity in place, version + 1."""
    obj.version = int(obj.version) + 1
    session.add(obj)
    session.flush()
    return obj


def _bump_new_identity(session: Session, obj: Any, note: str | None) -> Any:
    """Documented locked rule: create a new identity; the old row never changes."""
    if getattr(obj, "id", None) is None:
        session.flush()  # parent must have an identity before it can be referenced
    new_object = _clone_row(obj, int(obj.version) + 1)
    _record_parent_ref(new_object, obj, note=note)
    session.add(new_object)
    session.flush()
    return new_object


def bump(session: Session, obj: Any, *, note: str | None = None) -> Any:
    """Return the next version of ``obj`` per the documented deterministic rule.

    * LOCKED -> a new identity row (new ``id``, ``version + 1``, parent ref
      recorded, historical row untouched). The return value is the NEW object.
    * UNLOCKED -> ``obj`` itself with ``version`` incremented by 1 in place
      (same identity; ``note`` is ignored on this path).

    Raises :class:`~smorx_behavior.versioning.lock.VersioningError` when the
    object has no ``version`` column or its version is ``< 1``.
    """
    table = getattr(obj, "__table__", None)
    if table is None or "version" not in table.c:
        raise VersioningError(f"{type(obj).__name__} has no 'version' column")
    version = int(obj.version)
    if version < 1:
        raise VersioningError(
            f"version must stay >= 1; {type(obj).__name__}(id={getattr(obj, 'id', None)}) "
            f"has version {version}"
        )
    if is_locked(obj):
        return _bump_new_identity(session, obj, note)
    return _bump_in_place(session, obj)


def snapshot(obj: Any) -> dict[str, Any]:
    """Return a JSON-serializable, current-state copy of ``obj``'s columns.

    Intended for rollback/evidence captures. UUIDs serialize to their string
    form, ``datetime``/``date`` values to ISO-8601 strings, and every dict/list
    is recursively normalized. The result is guaranteed to survive a
    ``json.loads(json.dumps(...))`` round-trip.
    """
    if getattr(obj, "__table__", None) is None:
        raise VersioningError("snapshot() requires an ORM-mapped object")
    raw: dict[str, Any] = {col.name: getattr(obj, col.name, None) for col in obj.__table__.columns}
    raw["_type"] = type(obj).__name__
    try:
        return json.loads(json.dumps(raw, default=_json_default))
    except TypeError as exc:
        raise VersioningError(f"cannot snapshot {type(obj).__name__}: {exc}") from exc


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"not JSON-serializable: {value!r}")


def _normalize_id(value: Any) -> Any:
    """Coerce a recorded parent id back to the model's id type."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return value


def get_lineage(session: Session, model: type, start_id: Any) -> list[Any]:
    """Return the lineage ids from oldest to newest in ``[oldest, ..., start_id]``.

    Walks the recorded parent references (JSON reserved key or text marker)
    created by :func:`bump`, starting at ``start_id``. Guarantees:

    * every returned id exists in the table (else :class:`VersioningError`);
    * the walk is bounded by :data:`MAX_LINEAGE_HOPS`;
    * a cycle (corrupt lineage) raises :class:`VersioningError` instead of
      looping forever.
    """
    ids: list[Any] = []
    seen: set[Any] = set()
    current_id = _normalize_id(start_id)
    hops = 0
    while current_id is not None:
        if current_id in seen:
            raise VersioningError(
                f"cycle detected in {model.__name__} lineage at {current_id}; "
                "parent references are corrupt"
            )
        seen.add(current_id)
        row = session.get(model, current_id)
        if row is None:
            raise VersioningError(
                f"{model.__name__} row {current_id} referenced by a lineage but does not exist"
            )
        ids.append(current_id)
        ref = _read_parent_ref(row)
        current_id = _normalize_id(ref["id"]) if ref else None
        hops += 1
        if hops > MAX_LINEAGE_HOPS:
            raise VersioningError(
                f"lineage exceeds {MAX_LINEAGE_HOPS} hops from {start_id}; refusing to walk further"
            )
    ids.reverse()
    return ids

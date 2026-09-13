"""Version/lock policy service for the behavioral data model (plan 2.5, ADR-0005).

Three layers:

* :mod:`smorx_behavior.versioning.lock` — lock-state enforcement
  (``is_locked``, ``assert_not_locked``, ``lock``, the controlled test/repair
  ``force_set``, and the ``VersioningError`` / ``VersionLockedError`` types).
* :mod:`smorx_behavior.versioning.service` — version policy (``bump``,
  ``snapshot``, ``get_lineage``) plus the documented parent-reference storage
  constants.

Semantics in one sentence: once ``locked=True`` an object is an immutable
reference; bumping it creates a NEW row (new identity, ``version + 1``, parent
reference recorded) and never mutates the historical row. Unlocked bumps are
in-place (``version += 1``). See ``service.py`` for the full documented rule.
"""

from __future__ import annotations

from smorx_behavior.versioning.lock import (
    LOCKED_STATE,
    VersioningError,
    VersionLockedError,
    assert_not_locked,
    force_set,
    is_locked,
    lock,
)
from smorx_behavior.versioning.service import (
    MAX_LINEAGE_HOPS,
    PARENT_JSON_FIELDS,
    PARENT_RESERVED_KEY,
    PARENT_TEXT_FIELDS,
    TEXT_MARKER_RE,
    bump,
    get_lineage,
    parent_storage,
    snapshot,
)

__all__ = [
    "LOCKED_STATE",
    "MAX_LINEAGE_HOPS",
    "PARENT_JSON_FIELDS",
    "PARENT_RESERVED_KEY",
    "PARENT_TEXT_FIELDS",
    "TEXT_MARKER_RE",
    "VersionLockedError",
    "VersioningError",
    "assert_not_locked",
    "bump",
    "force_set",
    "get_lineage",
    "is_locked",
    "lock",
    "parent_storage",
    "snapshot",
]

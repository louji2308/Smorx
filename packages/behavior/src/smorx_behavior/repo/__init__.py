"""Repository / data-access layer for the behavioral persistence backend.

Phase 2 (implementation plan step 2.5): generic persistence helpers plus
purpose-specific catalog queries over the real ``smorx_behavior.models``
entities. Reads/writes stay ORM-contract driven; destructive operations are
policy-gated by default.
"""

from __future__ import annotations

from smorx_behavior.repo import base, catalog
from smorx_behavior.repo.base import (
    count,
    delete,
    digest,
    ensure_evidence,
    get,
    get_or_create,
    list_,
    query,
    save,
)
from smorx_behavior.repo.catalog import (
    certificate_for_change,
    evidence_for_change,
    lifecycle,
    memory_for_change,
    tasks_for_change,
)

__all__ = [
    "base",
    "catalog",
    "certificate_for_change",
    "count",
    "delete",
    "digest",
    "ensure_evidence",
    "evidence_for_change",
    "get",
    "get_or_create",
    "lifecycle",
    "list_",
    "memory_for_change",
    "query",
    "save",
    "tasks_for_change",
]

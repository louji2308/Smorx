"""Deterministic event chaining for the workflow runtime.

Every workflow, reliability, and failure-injection event is bound to a run
and carries a recomputable ``hash`` so a persisted chain can be replayed and
validated without trusting stored state (AGENTS.md sections 12/40).  Events
are chained over::

    entity_type | entity_id | event_type | sequence | canonical payload

``occurred_at`` is deliberately excluded so recomputation is stable across
persists and reloads.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from smorx_behavior.models import ConsequentialEvent
from smorx_behavior.repo.base import digest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

__all__ = [
    "canonical_payload",
    "event_digest",
    "next_sequence",
]


def canonical_payload(payload: dict[str, Any] | None) -> str:
    """Return a stable canonical JSON string for ``payload``.

    ``sort_keys`` makes the digest independent of insertion order;
    ``default=str`` folds UUIDs, datetimes, and enums deterministically.
    """
    return json.dumps(
        payload or {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def event_digest(event: ConsequentialEvent) -> str:
    """Return the deterministic chaining digest for ``event``.

    The digest covers the event identity plus its sequence and canonical
    payload, excluding ``occurred_at`` (see module docstring).
    """
    raw_entity_id = getattr(event, "entity_id", None)
    entity_id = str(raw_entity_id) if raw_entity_id is not None else ""
    sequence = int(getattr(event, "sequence", 0) or 0)
    return digest(
        getattr(event, "entity_type", ""),
        entity_id,
        getattr(event, "event_type", ""),
        str(sequence),
        canonical_payload(getattr(event, "payload", None)),
    )


def next_sequence(
    session: Session,
    *,
    run_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
) -> int:
    """Return the next event sequence for ``run_id`` (default) or ``task_id``.

    Only one scope may be given.  Sequences restart at 1 for a fresh run so a
    reconstruction produces the same ordering.
    """
    statement = select(func.count()).select_from(ConsequentialEvent)
    if (run_id is None) == (task_id is None):
        raise ValueError("exactly one of run_id or task_id must be provided")
    if run_id is not None:
        statement = statement.where(ConsequentialEvent.run_id == run_id)
    else:
        statement = statement.where(ConsequentialEvent.task_id == task_id)
    current = int(session.scalar(statement) or 0)
    return current + 1

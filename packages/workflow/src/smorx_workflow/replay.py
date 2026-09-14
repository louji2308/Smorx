"""Workflow replay from the stored evidence and event graph (12.4).

Replays the journey of a task from its persisted ``ConsequentialEvent``
rows and bound ``Evidence``, producing a structured timeline of stages.
This module is a **consumer** of the event and evidence graphs; it never
mutates the database.

Contracts enforced:

* ``replay_from_evidence_graph`` reads only from the database and always
  returns a complete :class:`ReplayResult`, even when the event graph is
  empty or partially filled.
* Stages appear in deterministic order (sorted by ``occurred_at``, then
  ``sequence``, then ``id``).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from smorx_behavior.evidence.service import evidence_for_task
from smorx_behavior.models import ConsequentialEvent, EventKind, Run
from sqlalchemy import select
from sqlalchemy.orm import Session

from smorx_workflow.chaining import event_digest
from smorx_workflow.orchestrate import DEFAULT_PHASES

__all__ = [
    "ReplayResult",
    "ordered_events",
    "replay_from_evidence_graph",
]

_PHASE_POSITIONS: dict[str, int] = {name: i for i, name in enumerate(DEFAULT_PHASES)}
_PHASE_SET: frozenset[str] = frozenset(DEFAULT_PHASES)

# Canonical stage order; events not in this list go to an "unclassified" bucket.
_STAGE_ORDER: list[str] = [
    EventKind.TASK_RECEIVED.value,
    EventKind.REPOSITORY_INSPECTED.value,
    EventKind.PLAN_GENERATED.value,
    EventKind.SANDBOX_CREATED.value,
    EventKind.ACTION_EXECUTED.value,
    EventKind.FAILURE_CLASSIFIED.value,
    EventKind.PATCH_GENERATED.value,
    EventKind.EVIDENCE_RECORDED.value,
    EventKind.REVERIFICATION.value,
    EventKind.VERIFICATION_RUN.value,
    EventKind.BEHAVIORAL_DELTA.value,
    EventKind.INTENT_ALIGNMENT.value,
    EventKind.REPAIR.value,
    EventKind.CERTIFICATION.value,
    EventKind.MERGE.value,
    EventKind.MEMORY_UPDATE.value,
    EventKind.BLOCKED.value,
]


def _stage_key(event_type: str) -> int:
    """Return the canonical ordering index for ``event_type``."""
    try:
        return _STAGE_ORDER.index(event_type)
    except ValueError:
        return len(_STAGE_ORDER)


@dataclass
class ReplayEvent:
    """One replayed event from the graph."""

    event_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    event_type: str
    occurred_at: datetime | None
    actor: str | None
    payload: dict[str, Any]
    provenance: str | None


@dataclass
class ReplayStage:
    """A grouped stage in the replayed journey."""

    stage: str
    events: list[ReplayEvent] = field(default_factory=list)


@dataclass
class ReplayResult:
    """Full replay result from the evidence and event graph."""

    task_id: uuid.UUID
    stages: list[ReplayStage] = field(default_factory=list)
    evidence_count: int = 0
    event_count: int = 0
    replayable: bool = True
    blocked_stages: list[str] = field(default_factory=list)
    hash_chain_valid: bool = True
    first_mismatch: str | None = None
    replayed_phases: list[str] = field(default_factory=list)
    evidence_hashes: list[str] = field(default_factory=list)
    blocked_events: list[dict[str, Any]] = field(default_factory=list)
    blocked_reason: str | None = None


def ordered_events(session: Session, run: Run) -> list[ConsequentialEvent]:
    """Return run-scoped events ordered by (sequence, occurred_at, id).

    Selects ``ConsequentialEvent`` rows where ``run_id == run.id``,
    ordered by ``sequence`` ascending, ``occurred_at`` ascending (nulls
    last), then ``id`` ascending.
    """
    return list(
        session.scalars(
            select(ConsequentialEvent)
            .where(ConsequentialEvent.run_id == run.id)
            .order_by(
                ConsequentialEvent.sequence.asc(),
                ConsequentialEvent.occurred_at.asc().nullslast(),
                ConsequentialEvent.id.asc(),
            )
        )
    )


def replay_from_evidence_graph(
    session: Session,
    *,
    run: Run | None = None,
    task_id: uuid.UUID | None = None,
    expected_hashes: list[str] | None = None,
) -> ReplayResult:
    """Replay the journey of a run (or task) from its stored event and evidence graph.

    Returns a structured :class:`ReplayResult` with stages in canonical order,
    evidence count, event count, hash-chain validity, and a list of stages
    that contain BLOCKED events (if any).
    """
    if run is None and task_id is None:
        raise ValueError("at least one of run or task_id is required")

    if run is not None:
        resolved_task_id: uuid.UUID = run.task_id
    else:
        assert task_id is not None
        resolved_task_id = task_id

    # Event ordering for display / stages
    if run is not None:
        display_events = ordered_events(session, run)
    else:
        display_events = list(
            session.scalars(
                select(ConsequentialEvent)
                .where(ConsequentialEvent.task_id == task_id)
                .order_by(
                    ConsequentialEvent.occurred_at.asc().nullslast(),
                    ConsequentialEvent.sequence.asc(),
                    ConsequentialEvent.id.asc(),
                )
            )
        )

    evidence_rows = evidence_for_task(session, resolved_task_id)

    stages_by_type: dict[str, ReplayStage] = {}
    blocked_stages: list[str] = []

    for event in display_events:
        if event.event_type not in stages_by_type:
            stages_by_type[event.event_type] = ReplayStage(stage=event.event_type)
        replay_event = ReplayEvent(
            event_id=event.id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            actor=event.actor,
            payload=dict(event.payload) if event.payload else {},
            provenance=event.provenance,
        )
        stages_by_type[event.event_type].events.append(replay_event)

        if event.event_type == EventKind.BLOCKED.value:
            reason = (event.payload or {}).get("reason", "unknown")
            blocked_label = f"{event.event_type}:{reason}"
            if blocked_label not in blocked_stages:
                blocked_stages.append(blocked_label)

    sorted_stages = sorted(stages_by_type.values(), key=lambda s: _stage_key(s.stage))

    # Hash chain validation — run-scoped chain events with sequence > 0
    if run is not None:
        chain_events = ordered_events(session, run)
    else:
        chain_events = list(
            session.scalars(
                select(ConsequentialEvent)
                .where(ConsequentialEvent.task_id == task_id)
                .order_by(
                    ConsequentialEvent.occurred_at.asc().nullslast(),
                    ConsequentialEvent.sequence.asc(),
                    ConsequentialEvent.id.asc(),
                )
            )
        )
    chain_events = [e for e in chain_events if (e.sequence or 0) > 0]

    hash_chain_valid = True
    first_mismatch: str | None = None

    if not chain_events:
        first_mismatch = "no chained events"
    else:
        prev_seq: int | None = None
        for event in chain_events:
            if not event.hash:
                hash_chain_valid = False
                first_mismatch = "missing stored hash"
                break
            recomputed = event_digest(event)
            if recomputed != event.hash:
                hash_chain_valid = False
                first_mismatch = f"stored/recomputed mismatch at sequence {event.sequence}"
                break
            if prev_seq is not None and event.sequence <= prev_seq:
                hash_chain_valid = False
                first_mismatch = f"sequence ordering violated at sequence {event.sequence}"
                break
            prev_seq = event.sequence

    # Evidence hashes
    ev_hashes = sorted({ev.hash for ev in evidence_rows if ev.hash})

    # Expected hashes check (does not override chain validity)
    if expected_hashes is not None and expected_hashes != ev_hashes and first_mismatch is None:
        first_mismatch = "evidence digest mismatch"

    # Replayable: chain valid AND evidence match AND chain is non-empty
    replayable = (
        hash_chain_valid
        and (expected_hashes is None or expected_hashes == ev_hashes)
        and len(chain_events) > 0
    )

    # Replay phases (ordered by DEFAULT_PHASES index)
    phase_list: list[str] = []
    for event in chain_events:
        phase = (event.payload or {}).get("phase")
        if phase in _PHASE_SET:
            phase_list.append(phase)
    phase_list.sort(key=lambda p: _PHASE_POSITIONS[p])

    # Blocked events
    blocked_evts: list[dict[str, Any]] = []
    blocked_reason: str | None = None
    for event in chain_events:
        payload = event.payload or {}
        if payload.get("blocked") is True or event.event_type == EventKind.BLOCKED.value:
            blocked_evts.append(
                {
                    "event_type": event.event_type,
                    "sequence": event.sequence,
                    "phase": payload.get("phase"),
                    "payload": dict(payload),
                    "blocked_reason": payload.get("reason"),
                }
            )
    if blocked_evts:
        blocked_reason = blocked_evts[-1].get("blocked_reason")

    return ReplayResult(
        task_id=resolved_task_id,
        stages=sorted_stages,
        evidence_count=len(evidence_rows),
        event_count=len(display_events),
        replayable=replayable,
        blocked_stages=blocked_stages,
        hash_chain_valid=hash_chain_valid,
        first_mismatch=first_mismatch,
        replayed_phases=phase_list,
        evidence_hashes=ev_hashes,
        blocked_events=blocked_evts,
        blocked_reason=blocked_reason,
    )

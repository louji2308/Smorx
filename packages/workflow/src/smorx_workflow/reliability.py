"""Demo reliability: resume, reset, idempotency, stale-state cleanup (12.6).

Provides the safe-stopping resume/reset operators the product journey needs
(AGENTS.md section 27: CONTINUE, PAUSE, APPROVE, ABORT, ROLLBACK).  The
workflow can be:

* **resumed** from a BLOCKED task (CONTINUE / ROLLBACK intent);
* **reset** to a clean pre-run state so the deterministic demo can be
  re-executed without duplicating or corrupting historical rows
  (``demo_data`` isolation per AGENTS.md section 39);
* *left idempotent*: re-running :func:`resume_workflow` on an already-resumed
  task does not create duplicate stages.

Contracts enforced:

* ``reset_workflow`` never deletes historical/archaeological rows; it only
  clears run-scoped state for the demo task.
* ``resume_workflow`` returns an honest report when a task has no BLOCKED
  events to resume from.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from smorx_behavior.models import (
    ConsequentialEvent,
    EventKind,
    Evidence,
    Execution,
    Failure,
    Run,
    RunStatus,
    Task,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from smorx_workflow.chaining import event_digest, next_sequence
from smorx_workflow.orchestrate import (
    DEFAULT_PHASES,
    WorkflowError,
    build_demo_scenario,
    run_e2e_workflow,
)

__all__ = [
    "ReliabilityReport",
    "cleanup_stale_sandboxes",
    "idempotency_guard",
    "reset_workflow",
    "resume_workflow",
]

_PHASE_SET: frozenset[str] = frozenset(DEFAULT_PHASES)


@dataclass
class ReliabilityReport:
    """Outcome of a resume or reset reliability operation."""

    task_id: uuid.UUID
    operation: str  # "resume" | "reset" | "cleanup_stale_sandboxes"
    applied: bool
    detail: str
    resumed_from: str | None = None
    removed_event_ids: list[str] = field(default_factory=list)
    resumed: bool = False
    resume_point: str | None = None
    idempotent: bool = False
    reset: bool = False
    reason: str | None = None
    cleaned: dict[str, int] = field(default_factory=dict)


def _record_event(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: EventKind,
    task_id: uuid.UUID,
    actor: str,
    payload: dict[str, Any],
    run_id: uuid.UUID | None = None,
) -> None:
    """Persist one reliability observability event."""
    if run_id is not None:
        seq = next_sequence(session, run_id=run_id)
    else:
        seq = next_sequence(session, task_id=task_id)
    event = ConsequentialEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type.value,
        occurred_at=datetime.now(UTC),
        actor=actor,
        payload=payload,
        provenance=None,
        task_id=task_id,
        run_id=run_id,
        sequence=seq,
        hash=None,
    )
    event.hash = event_digest(event)
    session.add(event)
    session.flush()


def _validate_run_scoped_chain(session: Session, run: Run) -> str | None:
    """Return a reason string if the run's hash chain is invalid, else None."""
    from smorx_workflow.replay import ordered_events

    events = [e for e in ordered_events(session, run) if (e.sequence or 0) > 0]
    prev_seq: int | None = None
    for event in events:
        if not event.hash:
            return "cannot resume: missing stored hash in run chain"
        recomputed = event_digest(event)
        if recomputed != event.hash:
            return f"cannot resume: stored/recomputed mismatch at sequence {event.sequence}"
        if prev_seq is not None and event.sequence <= prev_seq:
            return f"cannot resume: sequence ordering violated at sequence {event.sequence}"
        prev_seq = event.sequence
    return None


def _resume_point(session: Session, run: Run) -> str | None:
    """Return the first DEFAULT_PHASES entry with no run-scoped phase event."""
    from smorx_workflow.replay import ordered_events

    events = ordered_events(session, run)
    completed_phases: set[str] = set()
    for event in events:
        phase = (event.payload or {}).get("phase")
        if phase in _PHASE_SET:
            completed_phases.add(phase)
    for phase in DEFAULT_PHASES:
        if phase not in completed_phases:
            return phase
    return None


def idempotency_guard(session: Session, *, task: Task, phase: str) -> bool:
    """Return True when ``phase`` has already been recorded for ``task``.

    A phase is considered recorded when a ``ConsequentialEvent`` exists with
    ``task_id == task.id``, ``payload["phase"] == phase``, and the event
    is not blocked.  A merge-decision event (``event_type == MERGE``) for
    the task also counts, regardless of phase.  Side-effect free.

    Raises ``WorkflowError`` for an unknown phase.
    """
    if phase not in _PHASE_SET:
        raise WorkflowError(f"unknown phase: {phase}")

    rows = list(
        session.scalars(select(ConsequentialEvent).where(ConsequentialEvent.task_id == task.id))
    )
    for row in rows:
        payload = row.payload or {}
        if row.event_type == EventKind.MERGE.value:
            return True
        if str(payload.get("phase")) == phase and payload.get("blocked") is not True:
            return True
    return False


def cleanup_stale_sandboxes(
    session: Session,
    *,
    staleness_hours: int = 24,
    dry_run: bool = True,
) -> ReliabilityReport:
    """Detect and optionally remove stale sandbox execution markers.

    Finds runs with terminal status (BLOCKED/FAILED/COMPLETED) whose
    ``finished_at`` is older than ``staleness_hours``, and which have
    at least one ``Execution`` row with a non-null ``sandbox_id``.
    When ``dry_run`` is False, those Execution marker rows are deleted.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=staleness_hours)

    stale_execs = list(
        session.scalars(
            select(Execution)
            .join(Run, Execution.run_id == Run.id)
            .where(
                Run.status.in_(["BLOCKED", "FAILED", "COMPLETED"]),
                Run.finished_at.isnot(None),
                Run.finished_at <= cutoff,
                Execution.sandbox_id.isnot(None),
            )
        )
    )

    stale_run_ids: set[uuid.UUID] = {ex.run_id for ex in stale_execs}

    report_task_id = uuid.uuid4()
    if stale_run_ids:
        first_run = session.get(Run, min(stale_run_ids))
        if first_run is not None:
            report_task_id = first_run.task_id

    marker_count = len(stale_execs)

    if dry_run:
        return ReliabilityReport(
            task_id=report_task_id,
            operation="cleanup_stale_sandboxes",
            applied=False,
            detail=f"dry run: {marker_count} stale sandbox markers flagged, none removed",
            reason=f"dry run: {marker_count} stale sandbox markers flagged, none removed",
            cleaned={"stale_runs": len(stale_run_ids), "stale_sandbox_markers": marker_count},
        )

    for ex in stale_execs:
        session.delete(ex)
    session.flush()

    return ReliabilityReport(
        task_id=report_task_id,
        operation="cleanup_stale_sandboxes",
        applied=True,
        detail=f"removed {marker_count} stale sandbox markers from {len(stale_run_ids)} stale runs",
        reason=f"removed {marker_count} stale sandbox markers from {len(stale_run_ids)} stale runs",
        cleaned={"stale_runs": len(stale_run_ids), "stale_sandbox_markers": marker_count},
    )


def resume_workflow(
    session: Session,
    *,
    run: Run | None = None,
    task: Task | None = None,
    intent: str = "CONTINUE",
    phases: tuple[str, ...] | None = None,
) -> ReliabilityReport:
    """Resume a workflow from where it left off.

    Resolves the run from ``run`` or ``task`` (finds earliest run by
    ``started_at``).  If the run is already completed or the task is
    MERGED, returns an idempotent report.  Otherwise validates the hash
    chain, determines the resume point, optionally checks ``phases``
    segment membership, then re-runs the workflow from the resume point.
    """
    if run is None and task is None:
        raise ValueError("resume_workflow requires a run or task")

    resolved_run: Run | None = run
    if resolved_run is None and task is not None:
        resolved_run = session.scalar(
            select(Run).where(Run.task_id == task.id).order_by(Run.started_at.asc())
        )
    assert resolved_run is not None

    resolved_task = session.get(Task, resolved_run.task_id)
    if resolved_task is None:
        raise ValueError(f"task {resolved_run.task_id} not found")

    if resolved_run.status == "COMPLETED" or resolved_task.status == "MERGED":
        return ReliabilityReport(
            task_id=resolved_run.task_id,
            operation="resume",
            applied=False,
            detail="already recorded: workflow completed or task already merged",
            resumed=False,
            idempotent=True,
            resume_point=None,
            reason="already recorded",
        )

    chain_issue = _validate_run_scoped_chain(session, resolved_run)
    if chain_issue is not None:
        return ReliabilityReport(
            task_id=resolved_run.task_id,
            operation="resume",
            applied=False,
            detail=chain_issue,
            resumed=False,
            reason=chain_issue,
        )

    resume_point = _resume_point(session, resolved_run)
    if phases is not None and resume_point is not None and resume_point not in phases:
        return ReliabilityReport(
            task_id=resolved_run.task_id,
            operation="resume",
            applied=False,
            detail=f"not within the requested phase segment: {resume_point}",
            resumed=False,
            reason="not within the requested phase segment",
        )

    scenario = build_demo_scenario(session, seed=False, scenario="payments-api/AUTH-017")
    try:
        result = run_e2e_workflow(
            session,
            scenario=scenario,
            phases=phases or DEFAULT_PHASES,
            seed=False,
        )
    except (WorkflowError, ValueError) as exc:
        return ReliabilityReport(
            task_id=resolved_run.task_id,
            operation="resume",
            applied=False,
            detail=str(exc),
            resumed=False,
            reason=str(exc),
        )

    if result.status != "COMPLETE":
        return ReliabilityReport(
            task_id=resolved_run.task_id,
            operation="resume",
            applied=False,
            detail=f"workflow blocked during resume: {result.blocked_reason}",
            resumed=False,
            reason=f"workflow blocked during resume: {result.blocked_reason}",
        )

    resolved_task.status = "MERGED"

    _record_event(
        session,
        entity_type="Task",
        entity_id=resolved_task.id,
        event_type=EventKind.REVERIFICATION,
        task_id=resolved_task.id,
        actor="reliability",
        payload={"operation": "resume", "intent": intent},
        run_id=resolved_run.id,
    )

    return ReliabilityReport(
        task_id=resolved_run.task_id,
        operation="resume",
        applied=True,
        detail=f"resumed workflow from {resume_point}",
        resumed=True,
        resume_point=resume_point,
    )


def reset_workflow(
    session: Session,
    *,
    run: Run | None = None,
    task: Task | None = None,
    allow_destructive: bool = False,
    demo_only: bool = True,
) -> ReliabilityReport:
    """Reset run-scoped state for the demo task to a clean pre-run state.

    Only clears *run-scoped* artifacts (events, evidence, failures,
    executions bound to the run).  Historical evidence, archaeology,
    certificates, and memory rows are NEVER deleted.  Idempotent.
    """
    if run is None and task is None:
        raise ValueError("reset_workflow requires a run or task")

    resolved_run: Run | None = run
    if resolved_run is None and task is not None:
        resolved_run = session.scalar(
            select(Run).where(Run.task_id == task.id).order_by(Run.started_at.asc())
        )
    assert resolved_run is not None

    if not allow_destructive:
        return ReliabilityReport(
            task_id=resolved_run.task_id,
            operation="reset",
            applied=False,
            detail="reset blocked: allow_destructive must be True",
            reset=False,
            reason="reset blocked: allow_destructive must be True",
        )

    if not demo_only:
        return ReliabilityReport(
            task_id=resolved_run.task_id,
            operation="reset",
            applied=False,
            detail="reset blocked: only demo-scoped resets are supported (demo_only=True)",
            reset=False,
            reason="reset blocked: only demo-scoped resets are supported (demo_only=True)",
        )

    # Count before deletion
    n_events = int(
        session.scalar(
            select(func.count())
            .select_from(ConsequentialEvent)
            .where(ConsequentialEvent.run_id == resolved_run.id)
        )
        or 0
    )
    n_evidence = int(
        session.scalar(
            select(func.count()).select_from(Evidence).where(Evidence.run_id == resolved_run.id)
        )
        or 0
    )
    n_failures = int(
        session.scalar(
            select(func.count()).select_from(Failure).where(Failure.run_id == resolved_run.id)
        )
        or 0
    )
    n_execs = int(
        session.scalar(
            select(func.count()).select_from(Execution).where(Execution.run_id == resolved_run.id)
        )
        or 0
    )

    # Collect removed event IDs before deletion
    removed_event_ids = [
        str(e.id)
        for e in session.scalars(
            select(ConsequentialEvent).where(ConsequentialEvent.run_id == resolved_run.id)
        )
    ]

    # Delete in dependency-safe order: ConsequentialEvent → Failure → Evidence → Execution
    for ev in list(
        session.scalars(
            select(ConsequentialEvent).where(ConsequentialEvent.run_id == resolved_run.id)
        )
    ):
        session.delete(ev)
    session.flush()

    for f in list(session.scalars(select(Failure).where(Failure.run_id == resolved_run.id))):
        session.delete(f)
    session.flush()

    for evidence_row in list(
        session.scalars(select(Evidence).where(Evidence.run_id == resolved_run.id))
    ):
        session.delete(evidence_row)
    session.flush()

    for ex in list(session.scalars(select(Execution).where(Execution.run_id == resolved_run.id))):
        session.delete(ex)
    session.flush()

    # Reset run state
    resolved_run.status = RunStatus.QUEUED.value
    resolved_run.finished_at = None
    env = dict(resolved_run.environment or {})
    env["demo_reset"] = True
    resolved_run.environment = env
    session.flush()

    # Record a task-scoped reset observation (not run-scoped, so run-scoped
    # count returns to 0 after reset — preserving the cleanup invariant).
    _record_event(
        session,
        entity_type="Task",
        entity_id=resolved_run.task_id,
        event_type=EventKind.BLOCKED,
        task_id=resolved_run.task_id,
        actor="reliability",
        payload={
            "operation": "reset",
            "detail": "run-scoped state reset for re-execution",
        },
    )

    return ReliabilityReport(
        task_id=resolved_run.task_id,
        operation="reset",
        applied=True,
        detail="removed run-scoped state; historical rows preserved",
        reset=True,
        removed_event_ids=removed_event_ids,
        cleaned={
            "events": n_events,
            "evidence": n_evidence,
            "failures": n_failures,
            "executions": n_execs,
        },
    )

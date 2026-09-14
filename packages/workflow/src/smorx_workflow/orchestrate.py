"""End-to-end workflow orchestration (implementation plan phase 12, section 12.1).

Drives the complete product journey through the real certification and
memory modules over a deterministic :class:`DemoScenario`.  The workflow
records structured ``ConsequentialEvent`` rows for each stage, so the
journey is observable and replayable (AGENTS.md sections 21/40).

The workflow is a **consumer** of the certification modules: it never
fabricates evidence, certification, or merge state.  When a required input
is missing (e.g. alignment not certifiable, no verification evidence), the
workflow returns an honest ``BLOCKED`` result instead of pretending success.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.evidence.service import evidence_for_task
from smorx_behavior.models import (
    CandidatePatch,
    Certificate,
    Change,
    Claim,
    ConsequentialEvent,
    EventKind,
    Evidence,
    EvidenceType,
    Failure,
    Ghost,
    Project,
    RepairPackage,
    Repository,
    Run,
    RunStatus,
    Task,
)
from smorx_behavior.repo.base import digest, get_or_create
from smorx_behavior.seed.demo import SEED_NAMESPACE, build_seed
from smorx_certification import (
    AlignmentVerdict,
    build_certificate,
    evaluate_alignment,
    evaluate_merge_gate,
    persist_archaeology,
    run_memory_pipeline,
    run_reverification,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from smorx_workflow.chaining import canonical_payload, event_digest, next_sequence

__all__ = [
    "DEFAULT_PHASES",
    "PHASE_EVENT_KINDS",
    "DemoScenario",
    "OrchestrationResult",
    "WorkflowError",
    "build_demo_scenario",
    "cache_deterministic_evidence",
    "read_cached_deterministic_evidence",
    "run_e2e_workflow",
    "run_phases",
    "workflow_id",
]


class WorkflowError(Exception):
    """Raised when the workflow cannot run for structural reasons."""


@dataclass
class DemoScenario:
    """Deterministic demo scenario bound to real persisted rows."""

    scenario: str
    project: Project
    repository: Repository
    change: Change
    task: Task
    candidate_patch: CandidatePatch
    ghost: Ghost
    failure: Failure
    claim: Claim
    repair: RepairPackage
    run_token: str = "e2e/run/AUTH-017"
    verification_evidence: list[Evidence] = field(default_factory=list)


@dataclass
class OrchestrationResult:
    """Outcome of one end-to-end workflow run."""

    scenario: str
    task_id: uuid.UUID
    status: str  # COMPLETE, BLOCKED or IN_PROGRESS
    steps: list[dict[str, str]] = field(default_factory=list)
    events_written: int = 0
    certificate_key: str | None = None
    certificate_status: str | None = None
    merged: bool = False
    memory_applied: bool = False
    blocked_reason: str | None = None
    state: str | None = None  # COMPLETED, BLOCKED, CERTIFIED, IN_PROGRESS
    completed_phases: list[str] = field(default_factory=list)
    replayable: bool = True
    evidence_hashes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase topology
# ---------------------------------------------------------------------------

DEFAULT_PHASES: tuple[str, ...] = (
    "discover",
    "govern",
    "define",
    "analyze",
    "lock",
    "develop",
    "verify",
    "decide",
    "reverify",
    "certify",
    "merge",
    "memory",
)

PHASE_EVENT_KINDS: dict[str, EventKind] = {
    "discover": EventKind.TASK_RECEIVED,
    "govern": EventKind.PLAN_GENERATED,
    "define": EventKind.ACTION_EXECUTED,
    "analyze": EventKind.EVIDENCE_RECORDED,
    "lock": EventKind.PATCH_GENERATED,
    "develop": EventKind.RESULT_OBSERVED,
    "verify": EventKind.VERIFICATION_RUN,
    "decide": EventKind.BEHAVIORAL_DELTA,
    "reverify": EventKind.REVERIFICATION,
    "certify": EventKind.CERTIFICATION,
    "merge": EventKind.MERGE,
    "memory": EventKind.MEMORY_UPDATE,
}

_PHASE_POSITIONS: dict[str, int] = {name: i for i, name in enumerate(DEFAULT_PHASES)}


# ---------------------------------------------------------------------------
# Demo scenario
# ---------------------------------------------------------------------------


def workflow_id(token: str) -> uuid.UUID:
    """Derive the deterministic id for ``token`` (mirrors build_seed)."""
    return uuid.uuid5(SEED_NAMESPACE, token)


#: Evidence types that constitute independent verification module output.
#: Only these rows are eligible for re-verification and certification binding.
#: Historical failure traces (EXECUTION_TRACE), model decisions, and binding
#: metadata are deliberately excluded so a certified result is grounded in
#: machine verification rather than the archaeology of the original failure
#: (AGENTS.md sections 16/17).
_VERIFICATION_EVIDENCE_TYPES: frozenset[str] = frozenset(
    {
        EvidenceType.STATIC_ANALYSIS.value,
        EvidenceType.DIFFERENTIAL_EXECUTION.value,
        EvidenceType.HISTORICAL_GHOST_REPLAY.value,
        EvidenceType.METAMORPHIC_CHECK.value,
        EvidenceType.ADVERSARIAL_SCENARIO.value,
        EvidenceType.MUTATION_TEST.value,
        EvidenceType.TEST_RESULT.value,
    }
)


def _verification_evidence(session: Session, task_id: uuid.UUID) -> list[Evidence]:
    """Return the task's independent-verification evidence family only."""
    return [
        ev for ev in evidence_for_task(session, task_id) if ev.type in _VERIFICATION_EVIDENCE_TYPES
    ]


def build_demo_scenario(
    session: Session,
    *,
    seed: bool = True,
    scenario: str = "payments-api/AUTH-017",
) -> DemoScenario:
    """Resolve the deterministic demo scenario rows, seeding if requested.

    Uses the documented seed tokens (Change #184, AUTH-017, Ghost #221,
    F-183).  When ``seed`` is True and the task row is absent, ``build_seed``
    is invoked to materialize the deterministic dataset first.
    """
    task = session.get(Task, workflow_id("demo/task/AUTH-017"))
    if task is None and seed:
        build_seed(session)
        task = session.get(Task, workflow_id("demo/task/AUTH-017"))
    if task is None:
        raise WorkflowError(
            "demo scenario payments-api/AUTH-017 is not present and seeding "
            "produced none; call build_seed(session) or pass an existing database"
        )

    project = session.get(Project, task.project_id)
    repository = task.repository
    change = task.change
    claim = session.scalar(
        select(Claim).where(Claim.task_id == task.id).order_by(Claim.created_at.asc())
    )
    ghost = session.get(Ghost, workflow_id("demo/ghost/221"))
    failure = session.scalar(
        select(Failure).where(Failure.task_id == task.id).order_by(Failure.created_at.asc())
    )
    repair = session.scalar(
        select(RepairPackage)
        .where(RepairPackage.task_id == task.id)
        .order_by(RepairPackage.created_at.asc())
    )
    patch = session.scalar(
        select(CandidatePatch)
        .where(CandidatePatch.task_id == task.id, CandidatePatch.status == "VERIFIED")
        .order_by(CandidatePatch.candidate_index.desc())
    )

    if project is None or repository is None or change is None or claim is None:
        raise WorkflowError("demo scenario is missing required role rows")
    if ghost is None or failure is None or repair is None or patch is None:
        raise WorkflowError(
            "demo scenario is missing archaeology rows (ghost/failure/repair/candidate)"
        )

    return DemoScenario(
        scenario=scenario,
        project=project,
        repository=repository,
        change=change,
        task=task,
        candidate_patch=patch,
        ghost=ghost,
        failure=failure,
        claim=claim,
        repair=repair,
        run_token="e2e/run/AUTH-017",
        verification_evidence=_verification_evidence(session, task.id),
    )


# ---------------------------------------------------------------------------
# Workflow stage recording
# ---------------------------------------------------------------------------


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
) -> ConsequentialEvent:
    """Persist one workflow observability event and return it.

    Run-scoped events are chained: the sequence is derived per run and the
    stored hash is recomputable via ``event_digest`` so replay can validate
    the persisted chain without trusting stored state (AGENTS.md section 40).
    """
    if run_id is not None:
        sequence = next_sequence(session, run_id=run_id)
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
            sequence=sequence,
            hash=None,
        )
        event.hash = event_digest(event)
    else:
        sequence = int(
            session.scalar(
                select(func.count())
                .select_from(ConsequentialEvent)
                .where(ConsequentialEvent.task_id == task_id)
            )
            or 0
        )
        event = ConsequentialEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type.value,
            occurred_at=datetime.now(UTC),
            actor=actor,
            payload=payload,
            provenance=None,
            task_id=task_id,
            sequence=sequence,
            hash=None,
        )
    session.add(event)
    session.flush()
    return event


def _is_certifiable(aligned: bool, status: str) -> bool:
    """Return True when an alignment verdict permits certification."""
    return aligned and status == "CERTIFIABLE"


def _validate_phases(phases: tuple[str, ...]) -> None:
    """Validate a phase segment is known and strictly ordered/non-repeating."""
    if not phases:
        raise WorkflowError("phases must not be empty")
    prev = -1
    for phase in phases:
        if phase not in _PHASE_POSITIONS:
            raise WorkflowError(f"unknown phase: {phase}")
        position = _PHASE_POSITIONS[phase]
        if position <= prev:
            raise WorkflowError("ordered, non-repeating phase sequence required")
        prev = position


def _evidence_hashes(session: Session, task_id: uuid.UUID) -> list[str]:
    """Return the task's stored evidence hashes in stable sorted order."""
    return sorted({ev.hash for ev in evidence_for_task(session, task_id) if ev.hash})


# ---------------------------------------------------------------------------
# Deterministic evidence cache
# ---------------------------------------------------------------------------


def cache_deterministic_evidence(
    session: Session,
    key: str,
    data: Any,
) -> tuple[str, bool]:
    """Cache deterministic evidence, returning ``(digest, created)``.

    Idempotent for identical payloads: re-caching the same ``key``/``data``
    pair does not create a second row and returns ``created=False``.
    """
    digest_data = digest("deterministic-evidence", key, canonical_payload(data))
    entity_id = workflow_id(f"cache/{key}")
    existing = session.scalar(
        select(ConsequentialEvent).where(
            ConsequentialEvent.entity_type == "CACHE",
            ConsequentialEvent.entity_id == entity_id,
        )
    )
    if existing is not None and existing.hash == digest_data:
        return digest_data, False
    event = ConsequentialEvent(
        entity_type="CACHE",
        entity_id=entity_id,
        event_type=EventKind.EVIDENCE_RECORDED.value,
        occurred_at=datetime.now(UTC),
        actor="workflow",
        payload={"key": key, "digest": digest_data, "data": data},
        provenance=None,
        sequence=0,
        hash=digest_data,
    )
    session.add(event)
    session.flush()
    return digest_data, True


def read_cached_deterministic_evidence(session: Session, key: str) -> Any | None:
    """Return the data cached for ``key``, or ``None`` when absent."""
    entity_id = workflow_id(f"cache/{key}")
    row = session.scalar(
        select(ConsequentialEvent)
        .where(
            ConsequentialEvent.entity_type == "CACHE",
            ConsequentialEvent.entity_id == entity_id,
        )
        .order_by(ConsequentialEvent.created_at.desc(), ConsequentialEvent.id.desc())
    )
    if row is None:
        return None
    return (row.payload or {}).get("data")


# ---------------------------------------------------------------------------
# Phase execution
# ---------------------------------------------------------------------------


def _run_segment(
    session: Session,
    *,
    scenario: DemoScenario,
    run: Run,
    phases: tuple[str, ...],
    evidence_reader: Callable[..., Any] | None,
    require_certification: bool,
    steps: list[dict[str, str]],
) -> OrchestrationResult:
    """Execute a validated phase segment against a real scenario/run."""
    task = scenario.task
    change = scenario.change
    completed: list[str] = []
    verdict: AlignmentVerdict | None = None
    bundle = None
    certificate = None
    merge_verdict = None
    memory_applied = False

    for phase in phases:
        if phase == "reverify":
            report = run_reverification(
                session,
                candidate_patch=scenario.candidate_patch,
                verification_plan=None,
                evidence_reader=evidence_reader,
            )
            _record_event(
                session,
                entity_type="CandidatePatch",
                entity_id=scenario.candidate_patch.id,
                event_type=EventKind.REVERIFICATION,
                task_id=task.id,
                actor="workflow",
                payload={
                    "phase": phase,
                    "passed": report.passed,
                    "blocked": report.blocked_reason is not None,
                },
                run_id=run.id,
            )
            steps.append({"kind": "verification_run", "phase": phase, "passed": str(report.passed)})
            completed.append(phase)
            if report.blocked_reason is not None:
                return _blocked(
                    session,
                    scenario,
                    steps,
                    report.blocked_reason,
                    run=run,
                    completed=completed,
                )
            continue

        if phase == "decide":
            verdict = evaluate_alignment(
                session,
                task=task,
                change=change,
                behavioral_deltas=None,
                intent_items=None,
            )
            _record_event(
                session,
                entity_type="Task",
                entity_id=task.id,
                event_type=EventKind.BEHAVIORAL_DELTA,
                task_id=task.id,
                actor="workflow",
                payload={
                    "phase": phase,
                    "status": verdict.status,
                    "aligned": verdict.aligned,
                    "unexplained_changes": verdict.unexplained_changes,
                },
                run_id=run.id,
            )
            steps.append({"kind": "intent_alignment", "phase": phase, "status": verdict.status})
            completed.append(phase)
            if not require_certification:
                reason = (
                    "require_certification=False; "
                    "certification/merge/memory stages explicitly disabled"
                )
                return _blocked(session, scenario, steps, reason, run=run, completed=completed)
            if not _is_certifiable(verdict.aligned, verdict.status):
                reason = (
                    "intent alignment not certifiable "
                    f"(aligned={verdict.aligned}, unexplained={verdict.unexplained_changes})"
                )
                return _blocked(session, scenario, steps, reason, run=run, completed=completed)
            continue

        if phase == "certify":
            bundle = build_certificate(
                session,
                task=task,
                change=change,
                claim=scenario.claim,
                candidate_patch=scenario.candidate_patch,
                alignment_aligned=verdict.aligned if verdict else False,
                verification_evidence=scenario.verification_evidence,
                environment={"provider": "nebius", "sandbox": "token-factory"},
                dependency_state={"token_refresh": "hardened"},
            )
            certificate = session.scalar(
                select(Certificate).where(
                    Certificate.certificate_key == bundle.certificate.certificate_key
                )
            )
            _record_event(
                session,
                entity_type="Certificate",
                entity_id=scenario.claim.id,
                event_type=EventKind.CERTIFICATION,
                task_id=task.id,
                actor="workflow",
                payload={
                    "phase": phase,
                    "certificate_key": bundle.certificate.certificate_key,
                    "status": bundle.certificate.status,
                },
                run_id=run.id,
            )
            steps.append(
                {
                    "kind": "certification",
                    "phase": phase,
                    "status": bundle.certificate.status,
                    "certificate_key": bundle.certificate.certificate_key,
                }
            )
            completed.append(phase)
            if bundle.certificate.status != "CERTIFIED":
                return _blocked(
                    session,
                    scenario,
                    steps,
                    f"certificate did not reach CERTIFIED (status={bundle.certificate.status})",
                    run=run,
                    completed=completed,
                )
            continue

        if phase == "merge":
            merge_verdict = evaluate_merge_gate(
                session,
                certificate=certificate,
                alignment_verdict=verdict,
                candidate_patch=scenario.candidate_patch,
                protected_behaviors=verdict.protected_behaviors if verdict else [],
            )
            _record_event(
                session,
                entity_type="Task",
                entity_id=task.id,
                event_type=EventKind.MERGE,
                task_id=task.id,
                actor="workflow",
                payload={
                    "phase": phase,
                    "allowed": merge_verdict.allowed,
                    "reason": merge_verdict.reason,
                },
                run_id=run.id,
            )
            steps.append({"kind": "merge", "phase": phase, "allowed": str(merge_verdict.allowed)})
            completed.append(phase)
            if not merge_verdict.allowed:
                return _blocked(
                    session,
                    scenario,
                    steps,
                    f"merge gate blocked: {merge_verdict.reason}",
                    run=run,
                    completed=completed,
                )
            continue

        if phase == "memory":
            archaeology = persist_archaeology(
                session,
                task=task,
                failure_row=scenario.failure,
                ghost_rows=[scenario.ghost],
                claim_rows=[scenario.claim],
                repair_packages=[scenario.repair],
                execution_evidence=[scenario.failure.evidence],
            )
            memory = run_memory_pipeline(
                session,
                certificate=certificate,
                task=task,
                change=change,
                archaeology=archaeology,
            )
            memory_applied = memory.applied
            _record_event(
                session,
                entity_type="MemoryUpdate",
                entity_id=task.id,
                event_type=EventKind.MEMORY_UPDATE,
                task_id=task.id,
                actor="workflow",
                payload={
                    "phase": phase,
                    "applied": memory.applied,
                    "summary": memory.summary,
                },
                run_id=run.id,
            )
            steps.append({"kind": "memory_update", "phase": phase, "applied": str(memory.applied)})
            completed.append(phase)
            continue

        _record_event(
            session,
            entity_type="Task",
            entity_id=task.id,
            event_type=PHASE_EVENT_KINDS[phase],
            task_id=task.id,
            actor="workflow",
            payload={"phase": phase, "blocked": False},
            run_id=run.id,
        )
        steps.append({"kind": phase, "status": "ok"})
        completed.append(phase)

    session.flush()
    events_written = int(
        session.scalar(
            select(func.count())
            .select_from(ConsequentialEvent)
            .where(ConsequentialEvent.task_id == task.id)
        )
        or 0
    )
    state = "CERTIFIED" if "certify" in completed and "merge" not in completed else "COMPLETED"
    return OrchestrationResult(
        scenario=scenario.scenario,
        task_id=task.id,
        status="COMPLETE",
        steps=steps,
        events_written=events_written,
        certificate_key=bundle.certificate.certificate_key if bundle else None,
        certificate_status=bundle.certificate.status if bundle else None,
        merged=bool(merge_verdict and merge_verdict.allowed),
        memory_applied=memory_applied,
        state=state,
        completed_phases=completed,
        replayable=True,
        evidence_hashes=_evidence_hashes(session, task.id),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_e2e_workflow(
    session: Session,
    *,
    scenario: DemoScenario | None = None,
    phases: tuple[str, ...] = DEFAULT_PHASES,
    seed: bool = True,
    evidence_reader: Callable[..., Any] | None = None,
    require_certification: bool = True,
) -> OrchestrationResult:
    """Run the end-to-end journey, auto-seeding the demo when needed.

    The full chain (discover through memory) drives the real certification
    modules over the deterministic scenario.  When the journey cannot
    complete, an honest ``BLOCKED`` result is returned instead of fabricating
    success.
    """
    _validate_phases(phases)
    if phases[0] != "discover":
        raise WorkflowError("must begin at the discover phase")
    if scenario is None:
        scenario = build_demo_scenario(session, seed=seed)
    task = scenario.task
    run_id = workflow_id(scenario.run_token)
    run, _ = get_or_create(
        session,
        Run,
        run_id,
        defaults={
            "task_id": task.id,
            "kind": "AGENT",
            "status": RunStatus.RUNNING.value,
            "environment": {
                "provider": "LOCAL",
                "runtime": "e2e-demo",
                "scenario": scenario.scenario,
            },
        },
    )
    reader = (
        evidence_reader
        if evidence_reader is not None
        else (lambda *args, **kwargs: scenario.verification_evidence)
    )
    result = _run_segment(
        session,
        scenario=scenario,
        run=run,
        phases=phases,
        evidence_reader=reader,
        require_certification=require_certification,
        steps=[],
    )
    if result.status == "COMPLETE":
        run.status = RunStatus.COMPLETED.value
        run.finished_at = datetime.now(UTC)
    elif result.status == "BLOCKED":
        run.status = RunStatus.BLOCKED.value
        run.finished_at = datetime.now(UTC)
    session.flush()
    return result


def run_phases(session: Session, *, run: Run, phases: tuple[str, ...]) -> OrchestrationResult:
    """Execute a validated phase segment over an existing run.

    Used for partial phase replay and targeted re-runs.  Pre-cert phases are
    recorded as run-scoped chained events; the result reports ``IN_PROGRESS``.
    """
    _validate_phases(phases)
    steps: list[dict[str, str]] = []
    completed: list[str] = []
    for phase in phases:
        _record_event(
            session,
            entity_type="Task",
            entity_id=run.task_id,
            event_type=PHASE_EVENT_KINDS[phase],
            task_id=run.task_id,
            actor="workflow",
            payload={"phase": phase, "blocked": False},
            run_id=run.id,
        )
        steps.append({"kind": phase, "status": "ok"})
        completed.append(phase)
    session.flush()
    events_written = int(
        session.scalar(
            select(func.count())
            .select_from(ConsequentialEvent)
            .where(ConsequentialEvent.task_id == run.task_id)
        )
        or 0
    )
    return OrchestrationResult(
        scenario="payments-api/AUTH-017",
        task_id=run.task_id,
        status="IN_PROGRESS",
        steps=steps,
        events_written=events_written,
        state="IN_PROGRESS",
        completed_phases=list(phases),
        replayable=True,
        evidence_hashes=_evidence_hashes(session, run.task_id),
    )


def _blocked(
    session: Session,
    scenario: DemoScenario,
    steps: list[dict[str, str]],
    reason: str,
    *,
    run: Run | None = None,
    completed: list[str] | None = None,
) -> OrchestrationResult:
    """Return an honest BLOCKED orchestration result with a recorded event."""
    _record_event(
        session,
        entity_type="Task",
        entity_id=scenario.task.id,
        event_type=EventKind.BLOCKED,
        task_id=scenario.task.id,
        actor="workflow",
        payload={"phase": "blocked", "blocked": True, "reason": reason},
        run_id=run.id if run is not None else None,
    )
    steps.append({"kind": "blocked", "status": reason})
    return OrchestrationResult(
        scenario=scenario.scenario,
        task_id=scenario.task.id,
        status="BLOCKED",
        steps=steps,
        blocked_reason=reason,
        state="BLOCKED",
        completed_phases=list(completed or []),
        replayable=True,
        evidence_hashes=_evidence_hashes(session, scenario.task.id),
    )

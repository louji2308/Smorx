"""Failure injection for workflow reliability testing (12.5).

Injects one of the documented failure classes into a workflow run so the
engine can be validated against real failure handling, bounded iteration,
and no-progress detection (AGENTS.md section 14).

The injection is **explicit** and **scoped**: it records real, attributable
execution/failure/evidence rows and a typed :class:`InjectionResult` (never a
fabricated success), and it always records an observable ``FAILURE_CLASSIFIED``
or ``BLOCKED`` event so the injected failure is part of the evidence chain
rather than a hidden simulation.

All rows are created through deterministic primary keys derived from a
run/mode/phase token, so re-injecting the same failure for the same run is
idempotent: the same execution, failure, evidence, and event rows are returned
and never duplicated.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from smorx_behavior.models import (
    ConsequentialEvent,
    EventKind,
    EvidenceType,
    Execution,
    Failure,
    FailureKind,
    Run,
    RunStatus,
    Severity,
    Task,
)
from smorx_behavior.repo.base import digest, ensure_evidence, get_or_create
from sqlalchemy import select
from sqlalchemy.orm import Session

from smorx_workflow.chaining import event_digest, next_sequence
from smorx_workflow.orchestrate import workflow_id

__all__ = [
    "FailureInjectionMode",
    "InjectedFailure",
    "InjectionResult",
    "inject_failure",
]


class FailureInjectionMode(Enum):
    """Failure classes the workflow can be exercised against (AGENTS §14)."""

    SYNTAX_BUILD = "SYNTAX_BUILD"
    UNIT_TEST = "UNIT_TEST"
    INTEGRATION = "INTEGRATION"
    TIMEOUT = "TIMEOUT"
    TOOL_FAILURE = "TOOL_FAILURE"
    POLICY_BLOCK = "POLICY_BLOCK"
    AMBIGUOUS_RESULT = "AMBIGUOUS_RESULT"
    NO_PROGRESS = "NO_PROGRESS"
    TEST_FAILURE = "TEST_FAILURE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


_MODE_KIND: dict[str, str] = {
    "SYNTAX_BUILD": FailureKind.F1_SYNTAX_BUILD.value,
    "UNIT_TEST": FailureKind.F2_UNIT_TEST.value,
    "TEST_FAILURE": FailureKind.F2_UNIT_TEST.value,
    "INTEGRATION": FailureKind.F3_INTEGRATION.value,
    "TIMEOUT": FailureKind.F5_TIMEOUT.value,
    "TOOL_FAILURE": FailureKind.F7_TOOL.value,
    "POLICY_BLOCK": FailureKind.F10_SAFETY_POLICY_BLOCK.value,
    "AMBIGUOUS_RESULT": FailureKind.F8_AMBIGUOUS_RESULT.value,
    "CONFLICTING_EVIDENCE": FailureKind.F8_AMBIGUOUS_RESULT.value,
    "NO_PROGRESS": FailureKind.F8_AMBIGUOUS_RESULT.value,
}


@dataclass
class InjectedFailure(Exception):
    """Typed failure injected into a workflow step.

    Carries the classification, a stable ``failure_id``, an optional
    ``evidence_ref``, and the step at which the failure was injected.
    """

    classification: str
    detail: str
    failure_id: str = field(default_factory=lambda: f"F-INJ-{uuid.uuid4().hex[:8]}")
    evidence_ref: str | None = None
    step: str | None = None

    def __str__(self) -> str:
        return (
            f"{self.classification}: {self.detail} "
            f"(failure_id={self.failure_id}, step={self.step or 'n/a'})"
        )


@dataclass
class InjectionResult:
    """Observable outcome of one failure injection."""

    mode: str
    classified: str
    message: str
    phase: str | None = None
    evidence_count: int = 0
    failure_count: int = 0
    blocked: bool = False


def _resolve_run(session: Session, *, task: Task | None, run: Run | None) -> Run:
    """Return the run scoping the injection, resolving or creating one."""
    if run is not None:
        return run
    if task is None:
        raise ValueError("inject_failure requires a task or run to scope the failure")
    most_recent = session.scalars(
        select(Run).where(Run.task_id == task.id).order_by(Run.started_at.desc())
    ).first()
    if most_recent is not None:
        return most_recent
    row, _ = get_or_create(
        session,
        Run,
        workflow_id(f"fault-run/{task.id}"),
        {
            "task_id": task.id,
            "kind": "AGENT",
            "status": RunStatus.QUEUED.value,
            "environment": {"provider": "LOCAL", "runtime": "in-memory-sqlite"},
        },
    )
    return row


def _record_event(
    session: Session,
    *,
    token: str,
    run: Run,
    task_id: Any,
    event_type: EventKind,
    payload: dict[str, Any],
) -> ConsequentialEvent:
    """Persist one idempotent, run-bound failure-injection event."""
    event_id = workflow_id(f"event/{token}")
    row, created = get_or_create(
        session,
        ConsequentialEvent,
        event_id,
        {
            "entity_type": "Run",
            "entity_id": event_id,
            "event_type": event_type.value,
            "occurred_at": datetime.now(UTC),
            "actor": "failure-injection",
            "payload": payload,
            "provenance": None,
            "task_id": task_id,
            "run_id": run.id,
            "sequence": next_sequence(session, run_id=run.id),
        },
    )
    if created:
        row.hash = event_digest(row)
    return row


def inject_failure(
    session: Session,
    *,
    task: Task | None = None,
    run: Run | None = None,
    mode: FailureInjectionMode | str,
    phase: str | None = None,
    verification_case: Any | None = None,
    detail: str | None = None,
) -> InjectionResult:
    """Inject one real, idempotent failure into ``run`` and return its outcome.

    ``mode`` may be a :class:`FailureInjectionMode` or its ``.value`` string.
    Rows are scoped to ``run`` (resolved from ``task`` when omitted) and keyed
    by deterministic ids derived from a run/mode/phase token, so repeated
    injection of the same failure never duplicates execution, failure,
    evidence, or event rows.  ``POLICY_BLOCK`` and ``NO_PROGRESS`` record a
    blocked event and write no execution rows; ``NO_PROGRESS`` records the
    three-failure no-progress fingerprint.
    """
    normalized = FailureInjectionMode(mode)
    target_run = _resolve_run(session, task=task, run=run)
    classified = _MODE_KIND[normalized.value]
    token = f"fault/{target_run.id}/{normalized.value}/{phase or 'n/a'}"
    task_id = target_run.task_id
    now = datetime.now(UTC)

    event_payload: dict[str, Any] = {
        "classification": classified,
        "mode": normalized.value,
        "injected": True,
        "blocked": False,
        "phase": phase,
    }
    verification_case_id: Any = None
    verification_ref: str | None = None
    if verification_case is not None:
        verification_case_id = getattr(verification_case, "id", None)
        verification_ref = None if verification_case_id is None else str(verification_case_id)
        if verification_ref is not None:
            event_payload["verification_case"] = verification_ref

    if normalized in {
        FailureInjectionMode.SYNTAX_BUILD,
        FailureInjectionMode.UNIT_TEST,
        FailureInjectionMode.TEST_FAILURE,
        FailureInjectionMode.INTEGRATION,
        FailureInjectionMode.TOOL_FAILURE,
    }:
        exec_id = workflow_id(f"exec/{token}")
        exec_row, _ = get_or_create(
            session,
            Execution,
            exec_id,
            {
                "run_id": target_run.id,
                "kind": "TEST",
                "status": "FAILED",
                "exit_code": 1,
                "sandbox_id": f"sandbox-{normalized.value}-{phase}",
                "machine_result": {"exit_code": 1, "passed": False},
                "command": f"pytest {phase or 'test'}",
                "started_at": now,
                "finished_at": now,
            },
        )
        evidence = ensure_evidence(
            session,
            content_hash=digest("injected-failure", token),
            task_id=task_id,
            run_id=target_run.id,
            execution_id=exec_row.id,
            type=EvidenceType.TEST_RESULT.value,
            source="failure-injection",
            machine_result={"passed": False, "exit_code": 1},
            occurred_at=now,
        )
        failure_row, _ = get_or_create(
            session,
            Failure,
            workflow_id(f"failure/{token}"),
            {
                "execution_id": exec_row.id,
                "task_id": task_id,
                "run_id": target_run.id,
                "evidence_id": evidence.id,
                "classification": classified,
                "message": detail or f"injected {normalized.value}",
                "severity": Severity.HIGH.value,
                "iteration": 1,
                "occurred_at": now,
            },
        )
        _record_event(
            session,
            token=token,
            run=target_run,
            task_id=task_id,
            event_type=EventKind.FAILURE_CLASSIFIED,
            payload=event_payload,
        )
        return InjectionResult(
            mode=normalized.value,
            classified=classified,
            message=failure_row.message,
            phase=phase,
            evidence_count=1,
            failure_count=1,
        )

    if normalized is FailureInjectionMode.TIMEOUT:
        exec_row, _ = get_or_create(
            session,
            Execution,
            workflow_id(f"exec/{token}"),
            {
                "run_id": target_run.id,
                "kind": "TEST",
                "status": "BLOCKED",
                "exit_code": None,
                "sandbox_id": f"sandbox-{normalized.value}",
                "machine_result": {"timeout": True},
                "command": f"{phase or 'test'} step exceeded its time budget",
                "started_at": now,
                "finished_at": now,
            },
        )
        failure_row, _ = get_or_create(
            session,
            Failure,
            workflow_id(f"failure/{token}"),
            {
                "execution_id": exec_row.id,
                "task_id": task_id,
                "run_id": target_run.id,
                "classification": classified,
                "message": detail or f"injected {normalized.value}",
                "severity": Severity.HIGH.value,
                "iteration": 1,
                "occurred_at": now,
            },
        )
        _record_event(
            session,
            token=token,
            run=target_run,
            task_id=task_id,
            event_type=EventKind.FAILURE_CLASSIFIED,
            payload=event_payload,
        )
        return InjectionResult(
            mode=normalized.value,
            classified=classified,
            message=failure_row.message,
            phase=phase,
            failure_count=1,
        )

    if normalized is FailureInjectionMode.POLICY_BLOCK:
        reason = f"injected POLICY_BLOCK at {phase or 'n/a'}"
        payload = {
            "blocked": True,
            "reason": reason,
            "classification": classified,
            "mode": normalized.value,
            "phase": phase,
        }
        if verification_ref is not None:
            payload["verification_case"] = verification_ref
        _record_event(
            session,
            token=token,
            run=target_run,
            task_id=task_id,
            event_type=EventKind.BLOCKED,
            payload=payload,
        )
        return InjectionResult(
            mode=normalized.value,
            classified=classified,
            message=reason,
            phase=phase,
            blocked=True,
        )

    if normalized is FailureInjectionMode.CONFLICTING_EVIDENCE:
        evidence_fields: dict[str, Any] = {"type": EvidenceType.TEST_RESULT.value}
        if verification_case_id is not None:
            evidence_fields["verification_case_id"] = verification_case_id
        ensure_evidence(
            session,
            content_hash=digest("injected-failure", token, "passed"),
            task_id=task_id,
            run_id=target_run.id,
            source="failure-injection",
            machine_result={"passed": True, "exit_code": 0},
            occurred_at=now,
            **evidence_fields,
        )
        failed_evidence = ensure_evidence(
            session,
            content_hash=digest("injected-failure", token, "failed"),
            task_id=task_id,
            run_id=target_run.id,
            source="failure-injection",
            machine_result={"passed": False, "exit_code": 1},
            occurred_at=now,
            **evidence_fields,
        )
        failure_row, _ = get_or_create(
            session,
            Failure,
            workflow_id(f"failure/{token}"),
            {
                "task_id": task_id,
                "run_id": target_run.id,
                "evidence_id": failed_evidence.id,
                "classification": classified,
                "message": detail or f"injected {normalized.value}",
                "severity": Severity.HIGH.value,
                "iteration": 1,
                "occurred_at": now,
            },
        )
        _record_event(
            session,
            token=token,
            run=target_run,
            task_id=task_id,
            event_type=EventKind.FAILURE_CLASSIFIED,
            payload=event_payload,
        )
        return InjectionResult(
            mode=normalized.value,
            classified=classified,
            message=failure_row.message,
            phase=phase,
            evidence_count=2,
            failure_count=1,
        )

    if normalized is FailureInjectionMode.AMBIGUOUS_RESULT:
        evidence = ensure_evidence(
            session,
            content_hash=digest("injected-failure", token),
            task_id=task_id,
            run_id=target_run.id,
            type=EvidenceType.TEST_RESULT.value,
            source="failure-injection",
            machine_result={"result": "ambiguous", "exit_code": None},
            occurred_at=now,
        )
        failure_row, _ = get_or_create(
            session,
            Failure,
            workflow_id(f"failure/{token}"),
            {
                "task_id": task_id,
                "run_id": target_run.id,
                "evidence_id": evidence.id,
                "classification": classified,
                "message": detail or f"injected {normalized.value}",
                "severity": Severity.HIGH.value,
                "iteration": 1,
                "occurred_at": now,
            },
        )
        _record_event(
            session,
            token=token,
            run=target_run,
            task_id=task_id,
            event_type=EventKind.FAILURE_CLASSIFIED,
            payload=event_payload,
        )
        return InjectionResult(
            mode=normalized.value,
            classified=classified,
            message=failure_row.message,
            phase=phase,
            evidence_count=1,
            failure_count=1,
        )

    if normalized is FailureInjectionMode.NO_PROGRESS:
        for iteration in (1, 2, 3):
            get_or_create(
                session,
                Failure,
                workflow_id(f"failure/{token}/{iteration}"),
                {
                    "task_id": task_id,
                    "run_id": target_run.id,
                    "classification": classified,
                    "message": detail or "no-progress",
                    "severity": Severity.HIGH.value,
                    "iteration": iteration,
                    "occurred_at": now,
                },
            )
        reason = "no-progress detected: 3 consecutive equivalent failures"
        payload = {
            "blocked": True,
            "reason": reason,
            "classification": classified,
            "mode": normalized.value,
            "phase": phase,
        }
        if verification_ref is not None:
            payload["verification_case"] = verification_ref
        _record_event(
            session,
            token=token,
            run=target_run,
            task_id=task_id,
            event_type=EventKind.BLOCKED,
            payload=payload,
        )
        return InjectionResult(
            mode=normalized.value,
            classified=classified,
            message=reason,
            phase=phase,
            failure_count=3,
            blocked=True,
        )

    raise ValueError(f"unhandled failure injection mode: {normalized.value!r}")

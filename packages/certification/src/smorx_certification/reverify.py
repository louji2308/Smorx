"""Independent re-verification of a candidate patch (implementation plan phase 11, section 11.1).

Re-verification runs independent verification modules against the target
candidate patch under locked conditions.  The ``evidence_reader`` is a port —
a caller-supplied callable that returns evidence rows produced by the
verification layer.  This design lets re-verification work before or after the
Phase 9/10 verification modules land.

Contracts enforced:

* ``run_reverification`` never fabricates evidence.  If the reader returns
  zero eligible rows the result is honest **BLOCKED** (passed=False), not
  a invented success.
* Every eligible evidence row must carry an integer ``exit_code`` in its
  ``machine_result`` dict.  A row with no ``exit_code`` is ineligible and
  does not contribute to the pass/fail decision.
* ``passed`` is ``True`` only when at least one eligible row exists and
  every eligible row has ``exit_code == 0``.
* ``candidate_patch.status`` is promoted to ``VERIFIED`` on pass and
  demoted to ``FAILED`` only when a definitive failure is observed.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.models import (
    CandidatePatch,
    ConsequentialEvent,
    EventKind,
    Evidence,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

__all__ = [
    "ReVerificationReport",
    "ReVerificationResult",
    "run_reverification",
]


@dataclass
class ReVerificationResult:
    """Outcome of verifying a single evidence row."""

    evidence_id: uuid.UUID
    exit_code: int | None
    passed: bool
    eligible: bool
    detail: str


@dataclass
class ReVerificationReport:
    """Aggregated outcome of the independent re-verification run."""

    candidate_patch_id: uuid.UUID
    before_status: str
    after_status: str
    passed: bool
    blocked_reason: str | None
    results: list[ReVerificationResult] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Defensive port invocation helpers
# ---------------------------------------------------------------------------


def _invoke_reader(
    evidence_reader: Any,
    session: Session,
    verification_plan: Any,
    candidate_patch: CandidatePatch,
) -> list[Evidence]:
    """Invoke the evidence_reader port defensively across plausible signatures."""
    for attempt in (
        lambda: evidence_reader(
            session, verification_plan=verification_plan, candidate_patch=candidate_patch
        ),
        lambda: evidence_reader(
            session=session,
            verification_plan=verification_plan,
            candidate_patch=candidate_patch,
        ),
        lambda: evidence_reader(verification_plan, candidate_patch, session=session),
    ):
        try:
            result = attempt()
            if result is None:
                return []
            return list(result)
        except TypeError:
            continue
    return []


def _record_event(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: EventKind,
    task_id: uuid.UUID,
    actor: str,
    payload: dict[str, Any],
) -> None:
    """Persist one re-verification observability event."""
    sequence = int(
        session.scalar(
            select(func.count())
            .select_from(ConsequentialEvent)
            .where(ConsequentialEvent.task_id == task_id)
        )
        or 0
    )
    session.add(
        ConsequentialEvent(
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
    )
    session.flush()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_reverification(
    session: Session,
    *,
    candidate_patch: CandidatePatch | None,
    verification_plan: Any,
    evidence_reader: Callable[..., Any] | None,
) -> ReVerificationReport:
    """Run independent re-verification on the candidate patch (11.1).

    The ``evidence_reader`` port is the source of machine-authoritative
    verification evidence.  A ``None`` or empty return produces an honest
    **BLOCKED** result.

    Raises ``ValueError`` when ``candidate_patch`` or ``evidence_reader``
    are ``None``.
    """
    if candidate_patch is None:
        raise ValueError("run_reverification requires a candidate_patch; candidate_patch is None")
    if evidence_reader is None:
        raise ValueError(
            "run_reverification requires an evidence_reader port; evidence_reader is None"
        )

    before_status: str = candidate_patch.status
    task = candidate_patch.task

    raw_evidence = _invoke_reader(evidence_reader, session, verification_plan, candidate_patch)

    if not raw_evidence:
        blocked_reason = (
            "re-verification blocked: evidence_reader returned no evidence rows "
            "(verification modules not landed or no eligible evidence produced)"
        )
        if task is not None:
            _record_event(
                session,
                entity_type="CandidatePatch",
                entity_id=candidate_patch.id,
                event_type=EventKind.REVERIFICATION,
                task_id=task.id,
                actor="re-verification",
                payload={
                    "before_status": before_status,
                    "after_status": before_status,
                    "passed": False,
                    "blocked": True,
                },
            )
        session.flush()
        return ReVerificationReport(
            candidate_patch_id=candidate_patch.id,
            before_status=before_status,
            after_status=before_status,
            passed=False,
            blocked_reason=blocked_reason,
            results=[],
            evidence_ids=[],
        )

    results: list[ReVerificationResult] = []
    evidence_ids: list[str] = []

    for ev in raw_evidence:
        ev_id: uuid.UUID = ev.id
        evidence_ids.append(str(ev_id))
        machine_result: dict[str, Any] = (
            ev.machine_result if isinstance(ev.machine_result, dict) else {}
        )
        exit_code: int | None = machine_result.get("exit_code")

        if exit_code is None:
            results.append(
                ReVerificationResult(
                    evidence_id=ev_id,
                    exit_code=None,
                    passed=False,
                    eligible=False,
                    detail=f"evidence {ev_id}: no exit_code in machine_result (ineligible)",
                )
            )
            continue

        ev_passed = exit_code == 0
        results.append(
            ReVerificationResult(
                evidence_id=ev_id,
                exit_code=exit_code,
                passed=ev_passed,
                eligible=True,
                detail=f"evidence {ev_id}: exit_code={exit_code}",
            )
        )

    eligible_results = [r for r in results if r.eligible]
    all_pass = all(r.passed for r in eligible_results) if eligible_results else False
    passed = len(eligible_results) > 0 and all_pass

    if passed:
        after_status = "VERIFIED"
    elif any(not r.passed for r in eligible_results):
        after_status = "FAILED"
    else:
        after_status = before_status

    candidate_patch.status = after_status

    if task is not None:
        _record_event(
            session,
            entity_type="CandidatePatch",
            entity_id=candidate_patch.id,
            event_type=EventKind.REVERIFICATION,
            task_id=task.id,
            actor="re-verification",
            payload={
                "before_status": before_status,
                "after_status": after_status,
                "passed": passed,
                "eligible_count": len(eligible_results),
                "total_count": len(results),
            },
        )
    session.flush()

    return ReVerificationReport(
        candidate_patch_id=candidate_patch.id,
        before_status=before_status,
        after_status=after_status,
        passed=passed,
        blocked_reason=None,
        results=results,
        evidence_ids=evidence_ids,
    )

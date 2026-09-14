"""Phase 10 — Evidence-bound repair loop.

Structures the next Candidate Patch (#2+) from a REPAIR_REQUIRED certification
decision.  Never certifies.  Never mutates Candidate Patch #1.  Preserves
historical failure (F-183 / Ghost).

The loop produces bounded, evidence-structured repair iterations.
Re-verification is Phase 11's responsibility (§10.5-10.6).
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from smorx_behavior.models.enums import RepairStatus
from smorx_develop.bounds import BoundsExhaustedError, LoopBounds, LoopBoundsController
from smorx_verification.contracts import ClaimAssessment, VerificationResult

from smorx_delta.repair import RepairPackageRecord, build_repair_package

if TYPE_CHECKING:
    from smorx_delta.decision import CertificationDecision
    from smorx_delta.deltas import BehavioralDeltaRecord
    from smorx_delta.intent import IntentAlignmentRecord

__all__ = [
    "RepairIteration",
    "RepairLoopResult",
    "run_repair_loop",
]

_UNAUTHORIZED_OUTCOME = (
    "candidate patches must be re-verified; no repeat of the observed divergence is acceptable"
)


@dataclass(frozen=True)
class RepairIteration:
    """One bounded repair iteration.  Never marked PASSED/CERTIFIED."""

    iteration: int
    repair: RepairPackageRecord
    candidate_index: int
    status: str
    started_at: str
    finished_at: str
    outcome: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict."""
        return {
            "iteration": self.iteration,
            "repair": self.repair.as_dict(),
            "candidate_index": self.candidate_index,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "outcome": self.outcome,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class RepairLoopResult:
    """Terminal result of the evidence-bound repair loop.

    Never certifies.  ``allow_continue`` is ``True`` only when at least one
    iteration ran without a bound exhaust.
    """

    decision_code: str
    candidate_patch_id: str
    iterations: tuple[RepairIteration, ...]
    allow_continue: bool

    blocked_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict."""
        return {
            "decision_code": self.decision_code,
            "candidate_patch_id": self.candidate_patch_id,
            "iterations": [it.as_dict() for it in self.iterations],
            "blocked_reason": self.blocked_reason,
            "allow_continue": self.allow_continue,
        }


def _find_affected_claim(
    deltas: Sequence[BehavioralDeltaRecord],
    alignments: Sequence[IntentAlignmentRecord],
    claims: dict[str, ClaimAssessment],
) -> str | None:
    """Return the first claim_id needing repair, or ``None``.

    Matches the first delta/alignment pair that is unauthorized (delta
    ``authorized is False``), pending (delta intent_alignment or alignment
    status PENDING), or whose claim is CONTRADICTING in the verification wave.
    """
    delta_by_claim: dict[str, BehavioralDeltaRecord] = {}
    for d in deltas:
        key = str(d.claim_id)
        if key not in delta_by_claim:
            delta_by_claim[key] = d

    alignment_by_claim: dict[str, IntentAlignmentRecord] = {}
    for a in alignments:
        key = str(a.claim_id)
        if key not in alignment_by_claim:
            alignment_by_claim[key] = a

    all_claims = dict.fromkeys(list(delta_by_claim.keys()) + list(alignment_by_claim.keys()))

    for claim_id in all_claims:
        delta = delta_by_claim.get(claim_id)
        alignment = alignment_by_claim.get(claim_id)

        if delta is not None and delta.authorized is False:
            return claim_id
        if delta is not None and delta.intent_alignment == "PENDING":
            return claim_id
        if alignment is not None and alignment.status == "PENDING":
            return claim_id
        if claims.get(claim_id) is ClaimAssessment.CONTRADICTING:
            return claim_id

    return None


def _gather_evidence_ids(
    verification_result: VerificationResult,
    affected_claim_id: str,
) -> tuple[str, ...]:
    """Collect evidence record IDs whose ``claim_id`` matches the affected claim."""
    ids: list[str] = []
    for record in verification_result.evidence:
        if str(record.claim_id) == affected_claim_id:
            ids.append(str(record.evidence_id))
    return tuple(ids)


def _derive_repair_text(
    affected_claim_id: str,
    verification_result: VerificationResult,
) -> tuple[str, str]:
    """Derive *expected_behavior* and *observed_behavior* from verification evidence.

    Expected behavior comes from the claim's SUPPORTING evidence summary;
    when no summary exists the protected behavior is preserved by definition.
    Observed behavior comes from the CONTRADICTING evidence.
    """
    expected = "protected behavior must be preserved"
    observed = "verification detected contradicting evidence"

    for contradiction in verification_result.contradictions:
        if str(contradiction.claim_id) != affected_claim_id:
            continue
        if contradiction.supporting:
            expected = (
                f"expected behavior must satisfy claim {affected_claim_id}; "
                f"supporting types: {', '.join(contradiction.supporting)}"
            )
        parts: list[str] = []
        if contradiction.contradicting:
            parts.append(f"contradicting types: {', '.join(contradiction.contradicting)}")
        if contradiction.detail:
            parts.append(contradiction.detail)
        if parts:
            observed = f"claim {affected_claim_id} — {'; '.join(parts)}"
        break

    return expected, observed


def _safe_uuid(value: str) -> uuid.UUID | None:
    """Parse a string as UUID; return ``None`` on failure."""
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _persist_repair_package(
    *,
    session: Any,
    repair_record: RepairPackageRecord,
    task_id: str,
    change_id: str,
    iteration_num: int,
) -> None:
    """Persist a new Candidate Patch and RepairPackage row when a session is given.

    The original Candidate Patch #1 is never mutated (AGENTS.md §15).
    Historical failure rows are never deleted or overwritten (AGENTS.md §8, §15);
    the repair package binds ``failure_id`` so the history stays traversable.
    """
    from smorx_behavior.models.entities import CandidatePatch, RepairPackage
    from smorx_behavior.repo.base import save

    change_uuid = uuid.UUID(change_id)
    task_uuid = uuid.UUID(task_id)

    new_candidate = CandidatePatch(
        change_id=change_uuid,
        task_id=task_uuid,
        status="PROPOSED",
        candidate_index=iteration_num + 1,
        patch_ref=f"repair_loop:{iteration_num}",
        summary=repair_record.expected_behavior,
    )
    save(session, new_candidate)

    failure_uuid = _safe_uuid(repair_record.failure_id)
    evidence_uuid = (
        _safe_uuid(repair_record.evidence_ids[0]) if repair_record.evidence_ids else None
    )
    started_at = datetime.fromisoformat(repair_record.created_at)
    finished_at = datetime.now(UTC)

    package_row = RepairPackage(
        failure_id=failure_uuid,
        task_id=task_uuid,
        candidate_patch_id=new_candidate.id,
        evidence_id=evidence_uuid,
        attempt=iteration_num,
        iteration=iteration_num,
        description=repair_record.observed_behavior,
        patch_ref=f"repair_loop:{iteration_num}",
        status=RepairStatus.CREATED.value,
        started_at=started_at,
        finished_at=finished_at,
    )
    save(session, package_row)


async def run_repair_loop(
    *,
    decision: CertificationDecision,
    change_id: str,
    candidate_patch_id: str,
    task_id: str,
    verification_result: VerificationResult,
    deltas: Sequence[BehavioralDeltaRecord],
    alignments: Sequence[IntentAlignmentRecord],
    bounds: LoopBounds | None = None,
    session: Any = None,
) -> RepairLoopResult:
    """Execute the evidence-bound repair loop (Phase 10.4-10.6).

    This loop *structures* the next candidate; it never certifies Candidate
    Patch #1 or any repair candidate.  Original candidate patch is never
    mutated (AGENTS.md §15).  Historical failure is never deleted.

    Re-verification is Phase 11's responsibility.
    """
    await asyncio.sleep(0)

    code_value = str(decision.code.value) if hasattr(decision.code, "value") else str(decision.code)

    if code_value != "REPAIR_REQUIRED":
        return RepairLoopResult(
            decision_code=code_value,
            candidate_patch_id=candidate_patch_id,
            iterations=(),
            allow_continue=False,
            blocked_reason="repair loop requires a REPAIR_REQUIRED certification decision",
        )

    effective_bounds = bounds or LoopBounds()
    controller = LoopBoundsController(effective_bounds)
    iterations: list[RepairIteration] = []
    allow_continue = False
    blocked_reason = ""

    for _attempt in range(1, effective_bounds.max_iterations + 1):
        try:
            controller.check()
        except BoundsExhaustedError as exc:
            blocked_reason = f"loop bound exhausted: {exc.bound} — {exc}"
            break

        started = datetime.now(UTC).isoformat()

        affected_claim_id = _find_affected_claim(deltas, alignments, verification_result.claims)
        if affected_claim_id is None:
            blocked_reason = "no unauthorized or contradicting claims found; nothing to repair"
            break

        evidence_ids = _gather_evidence_ids(verification_result, affected_claim_id)
        if not evidence_ids:
            blocked_reason = (
                f"no verification evidence for affected claim {affected_claim_id}; "
                "repair package schema requires minItems 1 evidence_ids"
            )
            break

        expected_behavior, observed_behavior = _derive_repair_text(
            affected_claim_id, verification_result
        )

        repair_record = build_repair_package(
            failure_id=f"F-{affected_claim_id}",
            affected_claim_id=affected_claim_id,
            expected_behavior=expected_behavior,
            observed_behavior=observed_behavior,
            evidence_ids=evidence_ids,
            required_outcome=_UNAUTHORIZED_OUTCOME,
        )

        controller.record_repair()

        signature = f"{affected_claim_id}:{len(evidence_ids)}:{observed_behavior}"
        no_progress = controller.record_execution_signature(signature)

        iteration_num = controller.record_iteration()
        candidate_index = iteration_num + 1
        finished = datetime.now(UTC).isoformat()
        outcome = "NO_PROGRESS" if no_progress else "PROCEED"

        if session is not None:
            _persist_repair_package(
                session=session,
                repair_record=repair_record,
                task_id=task_id,
                change_id=change_id,
                iteration_num=iteration_num,
            )

        iterations.append(
            RepairIteration(
                iteration=iteration_num,
                repair=repair_record,
                candidate_index=candidate_index,
                status=RepairStatus.CREATED.value,
                started_at=started,
                finished_at=finished,
                outcome=outcome,
                notes=(
                    "no-progress detected; identical repair signature repeated"
                    if no_progress
                    else (
                        "repair candidate structured; re-verification is Phase 11's responsibility"
                    )
                ),
            )
        )
        allow_continue = True

        if no_progress:
            blocked_reason = (
                f"no-progress threshold reached at iteration {iteration_num}; "
                "repair signatures are materially equivalent"
            )
            break

    return RepairLoopResult(
        decision_code=code_value,
        candidate_patch_id=candidate_patch_id,
        iterations=tuple(iterations),
        allow_continue=allow_continue,
        blocked_reason=blocked_reason,
    )

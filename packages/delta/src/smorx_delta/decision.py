"""Phase 10 — Certification-readiness decision engine.

This is the "decide" layer, deliberately NOT the "certify" layer (certification
is Phase 11 and is out of scope here). The engine consumes the COMPLETED Phase
9 verification result plus the computed behavioral deltas and intent
alignments, and emits an evidence-grounded decision:

- ELIGIBLE_TO_CONTINUE  — verification completed, no contradictions, all
  modules passed, and every observed change is authorized by the locked intent
  ledger. Only this state ever sets ``allow_merge``.
- REPAIR_REQUIRED       — a claim is contradicting/conflicting, evidence is
  missing for a change, authorization is pending/unavailable, or a module
  failed.
- BLOCKED               — the verification wave was not completed.
- INSUFFICIENT_EVIDENCE — the wave completed but produced no evidence.

``allow_merge`` is True ONLY in rule ELIGIBLE_TO_CONTINUE; nothing else ever
authorizes a merge (AGENTS.md §10, §18, §19).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from smorx_verification.contracts import ClaimAssessment, ModuleStatus, VerificationResult

from smorx_delta.deltas import BehavioralDeltaRecord
from smorx_delta.intent import IntentAlignmentRecord

__all__ = [
    "CertificationDecision",
    "DecisionCode",
    "decide_certification",
]

_HIGH_ASSESSMENTS: frozenset[str] = frozenset(
    {ClaimAssessment.CONTRADICTING.value, ClaimAssessment.CONFLICTING.value}
)

_CHANGED_CLASSIFICATIONS: frozenset[str] = frozenset({"ALTERED", "ADDED", "REMOVED"})


class DecisionCode(StrEnum):
    ELIGIBLE_TO_CONTINUE = "ELIGIBLE_TO_CONTINUE"
    REPAIR_REQUIRED = "REPAIR_REQUIRED"
    BLOCKED = "BLOCKED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class CertificationDecision:
    """An evidence-grounded decision; the inputs make it explainable."""

    code: DecisionCode
    candidate_id: str
    change_id: str
    run_id: str
    summary: str
    gates: tuple[str, ...] = ()
    allow_merge: bool = False
    reason_failures: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "candidate_id": self.candidate_id,
            "change_id": self.change_id,
            "run_id": self.run_id,
            "summary": self.summary,
            "gates": list(self.gates),
            "allow_merge": self.allow_merge,
            "reason_failures": list(self.reason_failures),
        }


def _append(gates: list[str], label: str) -> list[str]:
    if label not in gates:
        gates.append(label)
    return gates


def decide_certification(
    *,
    verification_result: VerificationResult,
    deltas: Sequence[BehavioralDeltaRecord],
    alignments: Sequence[IntentAlignmentRecord],
) -> CertificationDecision:
    """Evaluate the decision gates deterministically against real evidence."""
    gates: list[str] = []
    reason_failures: list[str] = []
    candidate_id = str(verification_result.candidate_id)
    change_id = str(verification_result.change_id)
    run_id = verification_result.run_id or ""

    alignment_by_claim = {alignment.claim_id: alignment for alignment in alignments}

    if verification_result.state != "COMPLETED":
        gates.append(f"PHASE9_STATE={verification_result.state}")
        reason_failures.append("verification wave must be COMPLETED before deciding")
        return CertificationDecision(
            code=DecisionCode.BLOCKED,
            candidate_id=candidate_id,
            change_id=change_id,
            run_id=run_id,
            summary="blocked: verification wave did not complete",
            gates=tuple(gates),
            allow_merge=False,
            reason_failures=tuple(reason_failures),
        )

    gates.append("PHASE9_STATE=COMPLETED")

    if not verification_result.evidence:
        gates.append("EVIDENCE=none")
        return CertificationDecision(
            code=DecisionCode.INSUFFICIENT_EVIDENCE,
            candidate_id=candidate_id,
            change_id=change_id,
            run_id=run_id,
            summary="insufficient evidence: completed verification produced no records",
            gates=tuple(gates),
            allow_merge=False,
            reason_failures=("no evidence records",),
        )
    gates.append(f"EVIDENCE={len(verification_result.evidence)}")

    for claim_key, assessment in verification_result.claims.items():
        if assessment in _HIGH_ASSESSMENTS:
            gates.append(f"CLAIM:{claim_key}:{assessment}")
            reason_failures.append(f"claim {claim_key} has {assessment} evidence")

    for module in verification_result.modules:
        if module.status == ModuleStatus.FAILED:
            gates.append(f"MODULE:{module.module_type.value}:FAILED")
            reason_failures.append(f"verification module {module.module_type.value} failed")

    for delta in deltas:
        alignment = alignment_by_claim.get(delta.claim_id)
        if delta.classification == "UNEXPLAINED":
            gates.append(f"DELTA:{delta.claim_id}:UNEXPLAINED")
            reason_failures.append(f"delta for claim {delta.claim_id} is unexplained")
        elif delta.classification in _CHANGED_CLASSIFICATIONS:
            if alignment is None or alignment.verdict in {"PENDING", "UNEXPLAINED"}:
                gates.append(f"INTENT:{delta.claim_id}:UNVERIFIED")
                reason_failures.append(f"change for claim {delta.claim_id} is not yet authorized")
            elif alignment.verdict == "UNAUTHORIZED":
                gates.append(f"INTENT:{delta.claim_id}:UNAUTHORIZED")
                reason_failures.append(f"change for claim {delta.claim_id} is unauthorized")

    all_modules_clean = all(
        module.status in (ModuleStatus.PASSED, ModuleStatus.SKIPPED)
        for module in verification_result.modules
        if verification_result.modules
    )
    contradiction_free = not any(
        assessment in _HIGH_ASSESSMENTS for assessment in verification_result.claims.values()
    )
    all_changes_authorized = True
    for delta in deltas:
        if delta.classification == "UNEXPLAINED":
            all_changes_authorized = False
        elif delta.classification in _CHANGED_CLASSIFICATIONS:
            alignment = alignment_by_claim.get(delta.claim_id)
            if alignment is None or alignment.verdict != "AUTHORIZED":
                all_changes_authorized = False

    if gates and reason_failures:
        return CertificationDecision(
            code=DecisionCode.REPAIR_REQUIRED,
            candidate_id=candidate_id,
            change_id=change_id,
            run_id=run_id,
            summary=(
                f"{len(reason_failures)} gate(s) unresolved; candidate requires repair "
                "and re-verification before it may continue"
            ),
            gates=tuple(gates),
            allow_merge=False,
            reason_failures=tuple(reason_failures),
        )

    if all_modules_clean and contradiction_free and all_changes_authorized:
        return CertificationDecision(
            code=DecisionCode.ELIGIBLE_TO_CONTINUE,
            candidate_id=candidate_id,
            change_id=change_id,
            run_id=run_id,
            summary="verification completed with no unresolved gates; candidate may "
            "continue to independent certification",
            gates=tuple(gates),
            allow_merge=True,
            reason_failures=(),
        )

    gates.append("UNRESOLVED")
    return CertificationDecision(
        code=DecisionCode.BLOCKED,
        candidate_id=candidate_id,
        change_id=change_id,
        run_id=run_id,
        summary="blocked: decision gates unresolved without a repair path",
        gates=tuple(gates),
        allow_merge=False,
        reason_failures=tuple(reason_failures) if reason_failures else ("unresolved gates",),
    )

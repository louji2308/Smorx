"""Phase 10 — the Phase 9 -> Phase 10 handoff barrier.

The single entry point Phase 10 uses to consume a :class:`VerificationResult`.
Before ANY decision (delta, intent, repair eligibility) may be computed, the
verification wave must be COMPLETED: the verifier's own evidence is what makes
a claim actionable by the decision engine. A BLOCKED or INSUFFICIENT_EVIDENCE
wave stops the pipeline here rather than letting confidence substitute for
evidence (AGENTS.md §10, §16, §17).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from smorx_verification.contracts import VerificationResult

__all__ = [
    "HandoffBarrierError",
    "VerificationHandoff",
    "admit_verification_result",
]

_CONSUMED_CONTRACT = "VERIFICATION_RESULT_V1"


class HandoffBarrierError(Exception):
    """Raised when Phase 10 attempts to decide without a completed verification."""


@dataclass(frozen=True)
class VerificationHandoff:
    """The admitted verification evidence a Phase 10 decision may cite."""

    verification_result: VerificationResult
    admitted_at: str
    decision_allowed: bool

    @property
    def evidence_record_ids(self) -> tuple[str, ...]:
        return tuple(str(record.evidence_id) for record in self.verification_result.evidence)

    def as_dict(self) -> dict[str, Any]:
        return {
            "admitted_at": self.admitted_at,
            "decision_allowed": self.decision_allowed,
            "run_id": self.verification_result.run_id,
            "state": self.verification_result.state,
            "evidence_record_ids": list(self.evidence_record_ids),
            "contradictions": [
                contradiction.as_dict() for contradiction in self.verification_result.contradictions
            ],
        }


def admit_verification_result(
    result: VerificationResult,
    *,
    admitted_at: str | None = None,
) -> VerificationHandoff:
    """Admit a verification result for the decision stage (Phase 9 gate).

    Only ``state == COMPLETED`` crosses the barrier. Any other terminal state
    (BLOCKED, INSUFFICIENT_EVIDENCE) raises :class:`HandoffBarrierError` with
    the exact state named so the caller can route to repair or stop.
    """
    if result.state != "COMPLETED":
        raise HandoffBarrierError(
            "verification wave must be COMPLETED before a Phase 10 decision; "
            f"got state={result.state!r}"
        )
    if result.run_id is None or not str(result.run_id):
        raise HandoffBarrierError("verification result requires a run_id")
    if result.contract != _CONSUMED_CONTRACT:
        raise HandoffBarrierError(
            f"unexpected verification contract {result.contract!r}; expected {_CONSUMED_CONTRACT!r}"
        )
    admitted_at = admitted_at or datetime.now(UTC).isoformat()
    return VerificationHandoff(
        verification_result=result,
        admitted_at=admitted_at,
        decision_allowed=True,
    )


def require_candidate_id(result: VerificationResult, candidate_id: str) -> None:
    """Bind the decision to the exact candidate the verification described."""
    if result.candidate_id != candidate_id:
        raise HandoffBarrierError(
            f"verification was run for {result.candidate_id!r}, not {candidate_id!r}"
        )

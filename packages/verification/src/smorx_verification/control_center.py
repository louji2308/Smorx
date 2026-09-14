"""Phase 9.10 — verification control center.

Presents the completed verification wave to the UI as a derived read model:
module states, evidence counts, claim-level verdicts, and the trust state the
Verify/Decide tabs in the web shell render. Everything shown is derived from the
real :class:`VerificationResult` — no hardcoded "green" values (AGENTS.md §20).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from smorx_verification.contracts import VerificationResult

__all__ = ["ControlCenterModel"]


@dataclass(frozen=True)
class ControlCenterModel:
    """Immutable read model summarizing one verification run for the UI."""

    result: VerificationResult
    overall_passed: bool = field(default=False)

    @classmethod
    def build(cls, result: VerificationResult) -> ControlCenterModel:
        """Derive the model from a real run result (never from mock state)."""
        return cls(result=result, overall_passed=result.state == "COMPLETED")

    @property
    def module_states(self) -> dict[str, str]:
        return {module.module_type.value: module.status.value for module in self.result.modules}

    @property
    def evidence_count(self) -> int:
        return len(self.result.evidence)

    @property
    def claim_verdicts(self) -> dict[str, str]:
        return {key: value.value for key, value in self.result.claims.items()}

    @property
    def trust_boundary(self) -> str:
        return "VERIFIER_INDEPENDENT" if self.overall_passed else "VERIFICATION_INCOMPLETE"

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.result.state,
            "summary": self.result.summary,
            "overall_passed": self.overall_passed,
            "trust_boundary": self.trust_boundary,
            "modules": self.module_states,
            "evidence_count": self.evidence_count,
            "claims": self.claim_verdicts,
            "contradictions": [
                {
                    "claim_id": str(contradiction.claim_id),
                    "supporting": list(contradiction.supporting),
                    "contradicting": list(contradiction.contradicting),
                    "detail": contradiction.detail,
                }
                for contradiction in self.result.contradictions
            ],
            "run": {
                "run_id": self.result.run_id,
                "plan_version": self.result.plan_version,
                "candidate_id": self.result.candidate_id,
                "timestamp": self.result.timestamp.isoformat(),
            },
        }

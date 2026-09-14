"""Phase 9 — verification module context.

One context per verification wave: the trusted verifier identity, the claims
under investigation, the candidate (and baseline) workspaces, the evidence
collector, module settings, and the loop bounds the modules must honor. Every
module reads this context; none of them may mutate the candidate (the trust
boundary is enforced by ``smorx_verification.boundary``).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from smorx_develop.bounds import LoopBounds

from smorx_verification.boundary import VerificationActor
from smorx_verification.evidence import EvidenceCollector

__all__ = ["ModuleContext"]


@dataclass(frozen=True)
class ModuleContext:
    """Everything one verification module needs to act and emit evidence."""

    actor: VerificationActor
    claim_ids: tuple[uuid.UUID, ...]
    candidate_root: str
    verification_case_id: uuid.UUID | None = None
    baseline_root: str | None = None
    collector: EvidenceCollector | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    bounds: LoopBounds = field(default_factory=LoopBounds)

    def require_collector(self) -> EvidenceCollector:
        """Return the collector or fail fast (modules must emit evidence)."""
        if self.collector is None:
            raise ValueError("verification module requires an EvidenceCollector to emit evidence")
        return self.collector

    def as_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor.as_dict(),
            "claim_ids": [str(claim_id) for claim_id in self.claim_ids],
            "candidate_root": self.candidate_root,
            "baseline_root": self.baseline_root,
            "verification_case_id": str(self.verification_case_id)
            if self.verification_case_id
            else None,
            "settings": dict(self.settings),
            "bounds": self.bounds.as_dict(),
        }

"""Phase 9.9 — claim evidence fusion.

Evidence is normalized and fused at the claim level (never into one opaque
score). Every evidence record contributes a deterministic supporting /
contradicting signal to its claim; the fused verdict for a claim is the
project vocabulary: SUPPORTING / CONTRADICTING / INSUFFICIENT / CONFLICTING.
Contradictions are surfaced individually so the Phase-9/Phase-10 seam stays
explainable (AGENTS.md §17, §24, §41).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from smorx_verification.contracts import (
    ClaimAssessment,
    Contradiction,
    EvidenceRecord,
    ModuleStatus,
    classify_claim,
)

__all__ = ["AddressedEvidence", "fuse_claim_evidence"]

# Authority weights per evidence type (domain of this project's six modules).
_AUTHORITY: dict[str, float] = {
    "STATIC_ANALYSIS": 0.4,
    "DIFFERENTIAL_EXECUTION": 0.9,
    "HISTORICAL_GHOST_REPLAY": 1.0,
    "METAMORPHIC_CHECK": 0.7,
    "ADVERSARIAL_SCENARIO": 1.0,
    "MUTATION_TEST": 0.5,
}

_HIGH_SEVERITIES: frozenset[str] = frozenset({"HIGH", "CRITICAL"})


@dataclass(frozen=True)
class AddressedEvidence:
    """A single evidence record's fused signal for one claim."""

    evidence_id: uuid.UUID
    claim_id: uuid.UUID
    evidence_type: str
    authority: float
    supports: bool
    confidence: float
    provenance: str
    source: str
    severity: str
    exit_code: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": str(self.evidence_id),
            "claim_id": str(self.claim_id),
            "evidence_type": self.evidence_type,
            "authority": round(self.authority, 3),
            "supports": self.supports,
            "confidence": round(self.confidence, 3),
            "provenance": self.provenance,
            "source": self.source,
            "severity": self.severity,
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True)
class _ClaimFusion:
    addressed: list[AddressedEvidence] = field(default_factory=list)

    @property
    def supporting(self) -> int:
        return sum(1 for item in self.addressed if item.supports)

    @property
    def contradicting(self) -> int:
        return sum(1 for item in self.addressed if not item.supports)


def _classify_signal(record: EvidenceRecord) -> tuple[bool, float]:
    """Deterministically decide whether a record supports or contradicts.

    Signals:
    - an ineligible/module-failed record never supports (defensive weight).
    - non-zero exit code -> contradiction.
    - HIGH/CRITICAL severity -> contradiction.
    - otherwise -> supports, confidence scaled by authority and compliance.
    """
    if record.module_status == "INELIGIBLE:NO_CLAIM_BINDING":
        return False, 0.0
    if record.exit_code != 0 or record.severity in _HIGH_SEVERITIES:
        return False, _AUTHORITY.get(str(record.evidence_type), 0.5)
    authority = _AUTHORITY.get(str(record.evidence_type), 0.5)
    confidence = min(1.0, authority + (0.1 if record.module_status == "ELIGIBLE" else 0.0))
    return True, confidence


def fuse_claim_evidence(
    records: tuple[EvidenceRecord, ...],
    *,
    claim_ids: tuple[uuid.UUID, ...],
) -> tuple[dict[str, ClaimAssessment], tuple[AddressedEvidence, ...], tuple[Contradiction, ...]]:
    """Fuse all records into per-claim verdicts.

    Returns ``(verdicts, addressed, contradictions)`` where ``verdicts`` maps
    claim id -> ClaimAssessment and ``contradictions`` records every claim that
    received both supporting and contradicting signals.
    """
    clubs: dict[uuid.UUID, _ClaimFusion] = {claim_id: _ClaimFusion() for claim_id in claim_ids}
    for record in records:
        club = clubs.setdefault(record.claim_id, _ClaimFusion())
        supports, confidence = _classify_signal(record)
        club.addressed.append(
            AddressedEvidence(
                evidence_id=record.evidence_id,
                claim_id=record.claim_id,
                evidence_type=str(record.evidence_type),
                authority=_AUTHORITY.get(str(record.evidence_type), 0.5),
                supports=supports,
                confidence=confidence,
                provenance=record.provenance,
                source=record.source,
                severity=record.severity,
                exit_code=record.exit_code,
            )
        )

    verdicts: dict[str, ClaimAssessment] = {}
    contradictions: list[Contradiction] = []
    for claim_id, club in clubs.items():
        verdict = classify_claim(
            supporting=club.supporting,
            contradicting=club.contradicting,
        )
        verdicts[str(claim_id)] = verdict
        if club.supporting and club.contradicting:
            contradictions.append(
                Contradiction(
                    claim_id=claim_id,
                    supporting=tuple(
                        item.evidence_type for item in club.addressed if item.supports
                    ),
                    contradicting=tuple(
                        item.evidence_type for item in club.addressed if not item.supports
                    ),
                    detail="claim received both supporting and contradicting evidence",
                )
            )

    addressed = tuple(item for club in clubs.values() for item in club.addressed)
    return verdicts, addressed, tuple(contradictions)


def modules_passed(modules: tuple[Any, ...]) -> bool:
    """True only when every executed module reached a terminal non-failed state.

    A module that is SKIPPED (no applicable input) is not a failure; a module
    in FAILED or BLOCKED state means verification did not cleanly support the
    candidate.
    """
    return all(module.status in (ModuleStatus.PASSED, ModuleStatus.SKIPPED) for module in modules)

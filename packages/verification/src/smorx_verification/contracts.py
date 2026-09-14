"""Phase 9 — shared verification contracts.

The immutable, machine-readable shapes produced by the verification wave and
consumed by claim fusion (Phase 9) and behavioral-delta/intent work (Phase 10).
Each module emits its OWN evidence (``EvidenceRecord``); a module never returns
one opaque score. The completed wave is summarized in a ``VerificationResult``
whose state must be ``COMPLETED`` before any Phase-10 decision may run (the
cross-session contract / AGENTS.md §17).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar

__all__ = [
    "ClaimAssessment",
    "Contradiction",
    "EvidenceRecord",
    "ModuleOutcome",
    "ModuleStatus",
    "ModuleType",
    "VerificationResult",
    "classify_claim",
    "now_utc",
]


def now_utc() -> datetime:
    """Current UTC timestamp (single clock for the verification wave)."""
    return datetime.now(UTC)


class ModuleType(StrEnum):
    """The six verification-module modalities (locked verification-plan enum)."""

    STATIC_ANALYSIS = "STATIC_ANALYSIS"
    DIFFERENTIAL_EXECUTION = "DIFFERENTIAL_EXECUTION"
    HISTORICAL_GHOST_REPLAY = "HISTORICAL_GHOST_REPLAY"
    METAMORPHIC_CHECK = "METAMORPHIC_CHECK"
    ADVERSARIAL_SCENARIO = "ADVERSARIAL_SCENARIO"
    MUTATION_TEST = "MUTATION_TEST"


class ModuleStatus(StrEnum):
    """Lifecycle of one independent verification module."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class ClaimAssessment(StrEnum):
    """Claim-level verdict produced by the fusion engine (step 9.10)."""

    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"


@dataclass(frozen=True)
class EvidenceRecord:
    """One evidence object emitted by exactly one verification module.

    ``machine_result`` always carries the raw machine observation (exit code,
    stdout tail, duration). Every record is persisted through the behavioral
    evidence service so the claim chain stays real and traversable.
    """

    evidence_type: ModuleType | str
    claim_id: uuid.UUID
    source: str
    provenance: str
    artifact: str
    machine_result: dict[str, Any]
    exit_code: int
    severity: str  # INFO | LOW | MEDIUM | HIGH | CRITICAL
    timestamp: datetime = field(default_factory=now_utc)
    evidence_id: uuid.UUID = field(default_factory=uuid.uuid4)
    module_status: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": str(self.evidence_id),
            "evidence_type": self.evidence_type.value
            if isinstance(self.evidence_type, ModuleType)
            else str(self.evidence_type),
            "claim_id": str(self.claim_id),
            "source": self.source,
            "provenance": self.provenance,
            "artifact": self.artifact,
            "exit_code": self.exit_code,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "module_status": self.module_status,
            "machine_result": dict(self.machine_result),
        }


@dataclass(frozen=True)
class ModuleOutcome:
    """Per-module result: status plus the module's OWN evidence."""

    module_type: ModuleType
    status: ModuleStatus
    summary: str
    evidence: tuple[EvidenceRecord, ...] = ()
    findings: tuple[str, ...] = ()
    duration_seconds: float = 0.0
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_type": self.module_type.value,
            "status": self.status.value,
            "summary": self.summary,
            "evidence_count": len(self.evidence),
            "findings": list(self.findings),
            "duration_seconds": round(self.duration_seconds, 3),
            "error": self.error,
        }


@dataclass(frozen=True)
class Contradiction:
    """A single conflicting-evidence observation (step 9.9/phase testing)."""

    claim_id: uuid.UUID
    supporting: tuple[str, ...]  # evidence types supporting the claim
    contradicting: tuple[str, ...]  # evidence types contradicting the claim
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": str(self.claim_id),
            "supporting": list(self.supporting),
            "contradicting": list(self.contradicting),
            "detail": self.detail,
        }


def classify_claim(
    *,
    supporting: int,
    contradicting: int,
    warnings: int = 0,
) -> ClaimAssessment:
    """Deterministic claim classification from fused evidence counts.

    Rules (step 9.10): any contradicting evidence makes the claim
    CONTRADICTING; no evidence at all is INSUFFICIENT; both supporting and
    contradicting evidence is CONFLICTING; otherwise SUPPORTING when at least
    one supporting record exists.
    """
    if contradicting and supporting:
        return ClaimAssessment.CONFLICTING
    if contradicting:
        return ClaimAssessment.CONTRADICTING
    if supporting == 0 and warnings == 0:
        return ClaimAssessment.INSUFFICIENT
    return ClaimAssessment.SUPPORTING


@dataclass(frozen=True)
class VerificationResult:
    """The completed verification wave — the Phase 9 → Phase 10 contract.

    ``state == COMPLETED`` is the only state Phase 10 may consume for a final
    decision; anything else means the candidate's truth has not been
    established and delta/intent must not proceed to authorization.
    """

    candidate_id: str
    verification_plan_id: uuid.UUID
    plan_version: int
    run_id: str
    change_id: uuid.UUID
    task_id: uuid.UUID
    modules: tuple[ModuleOutcome, ...]
    evidence: tuple[EvidenceRecord, ...]
    claims: dict[str, ClaimAssessment]  # claim_id -> fused verdict
    contradictions: tuple[Contradiction, ...]
    state: str  # COMPLETED | BLOCKED | INSUFFICIENT_EVIDENCE
    summary: str = ""
    timestamp: datetime = field(default_factory=now_utc)

    _CONTRACT: ClassVar[str] = "VERIFICATION_RESULT_V1"

    @property
    def contract(self) -> str:
        """The stable cross-session contract identifier."""
        return self._CONTRACT

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": self._CONTRACT,
            "candidate_id": self.candidate_id,
            "verification_plan_id": str(self.verification_plan_id),
            "plan_version": self.plan_version,
            "run_id": self.run_id,
            "change_id": str(self.change_id),
            "task_id": str(self.task_id),
            "state": self.state,
            "modules": [module.as_dict() for module in self.modules],
            "evidence": [record.as_dict() for record in self.evidence],
            "claims": {key: value.value for key, value in self.claims.items()},
            "contradictions": [contradiction.as_dict() for contradiction in self.contradictions],
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }

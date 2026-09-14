"""Phase 10 — behavioral delta computation.

This module evaluates the observed behavioral deltas for every claim of a
completed verification wave (ADDED/REMOVED/ALTERED/UNCHANGED/UNEXPLAINED) and
always defers any authorization judgment: each record reports
``intent_alignment=PENDING`` and ``authorized=None``. It evaluates the observed
deltas against the verification evidence and the intent-alignment gate — it
never authorizes by itself; authorization is decided downstream by the
intent-alignment module and the human gate. Persistence is performed by the
integration layer, never here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.models.enums import IntentAlignmentStatus
from smorx_verification.contracts import (
    ClaimAssessment,
    EvidenceRecord,
    VerificationResult,
)
from sqlalchemy.orm import Session

__all__ = [
    "BehavioralDeltaRecord",
    "compute_behavioral_deltas",
]

_DELTA_VERSION = "1.0.0"
_ALIGNMENT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "smorx:behavioral-delta")
_CRITICAL_SEVERITIES = frozenset({"HIGH", "CRITICAL"})
_CONTRADICTING_ASSESSMENTS = (ClaimAssessment.CONTRADICTING, ClaimAssessment.CONFLICTING)
_UNEXPLAINED = "UNEXPLAINED"
_ALTERED = "ALTERED"
_ADDED = "ADDED"
_REMOVED = "REMOVED"
_UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class BehavioralDeltaRecord:
    """One observed behavioral delta for a single claim.

    Never carries an authorization decision: ``intent_alignment`` reports the
    deferred state (PENDING) and ``authorized`` is ``None`` until the
    intent-alignment gate decides. ``version`` defaults hold the schema version
    and are declared last so every non-default column may be passed
    positionally.
    """

    id: str
    change_id: str
    candidate_patch_id: str
    classification: str
    claim_id: str
    intent_alignment: str
    authorized: bool | None
    observed_at: str
    version: str = _DELTA_VERSION
    evidence_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "change_id": self.change_id,
            "candidate_patch_id": self.candidate_patch_id,
            "classification": self.classification,
            "claim_id": self.claim_id,
            "authorized": self.authorized,
            "intent_alignment": self.intent_alignment,
            "observed_at": self.observed_at,
            "evidence_ids": list(self.evidence_ids),
        }


def _claim_evidence(
    verification_result: VerificationResult, claim_id: str
) -> tuple[EvidenceRecord, ...]:
    """All evidence records naming ``claim_id`` (deduplicated by evidence id)."""
    records: dict[str, EvidenceRecord] = {}
    for record in verification_result.evidence:
        if str(record.claim_id) == claim_id:
            records[str(record.evidence_id)] = record
    for outcome in verification_result.modules:
        for record in outcome.evidence:
            if str(record.claim_id) == claim_id:
                records[str(record.evidence_id)] = record
    return tuple(records.values())


def _evidence_ids(evidence: tuple[EvidenceRecord, ...]) -> tuple[str, ...]:
    return tuple(sorted(str(record.evidence_id) for record in evidence))


def _claim_assessment(
    verification_result: VerificationResult, claim_id: str
) -> ClaimAssessment | None:
    claims = verification_result.claims
    direct = claims.get(claim_id)
    if direct is not None:
        return direct
    for key in claims:
        if str(key) == claim_id:
            return claims[key]
    return None


def _is_contradicting(
    verification_result: VerificationResult,
    claim_id: str,
    evidence: tuple[EvidenceRecord, ...],
) -> bool:
    for record in evidence:
        if record.severity.upper() in _CRITICAL_SEVERITIES:
            return True
        if record.exit_code != 0:
            return True
    return _claim_assessment(verification_result, claim_id) in _CONTRADICTING_ASSESSMENTS


def _classify_delta(
    *,
    claim_id: str,
    verification_result: VerificationResult,
    baseline_claim_ids: frozenset[str],
    candidates_claim_ids: frozenset[str],
) -> tuple[str, tuple[str, ...]]:
    evidence = _claim_evidence(verification_result, claim_id)
    if not evidence:
        return _UNEXPLAINED, ()
    if _is_contradicting(verification_result, claim_id, evidence):
        return _ALTERED, _evidence_ids(evidence)
    if claim_id in candidates_claim_ids and claim_id not in baseline_claim_ids:
        return _ADDED, _evidence_ids(evidence)
    if claim_id in baseline_claim_ids and claim_id not in candidates_claim_ids:
        return _REMOVED, _evidence_ids(evidence)
    return _UNCHANGED, _evidence_ids(evidence)


def _record_id(
    *,
    change_id: str,
    candidate_patch_id: str,
    claim_id: str,
    classification: str,
) -> str:
    return str(
        uuid.uuid5(
            _ALIGNMENT_NAMESPACE,
            f"{change_id}|{candidate_patch_id}|{claim_id}|{classification}",
        )
    )


def compute_behavioral_deltas(
    *,
    session: Session,
    change_id: str,
    candidate_patch_id: str,
    claim_ids: tuple[str, ...],
    verification_result: VerificationResult,
    baseline_claim_ids: frozenset[str] = frozenset(),
    candidates_claim_ids: frozenset[str] = frozenset(),
) -> tuple[BehavioralDeltaRecord, ...]:
    """Compute one deterministic delta record per claim, ordered by claim id.

    One record is returned per claim in ``claim_ids`` (sorted ascending), each
    deferred to the intent-alignment gate. ``session`` is accepted for contract
    symmetry only — nothing is persisted from this module (persistence happens
    at integration). An empty ``claim_ids`` yields an empty tuple.
    """
    observed_at = datetime.now(UTC).isoformat()
    records: list[BehavioralDeltaRecord] = []
    for claim_id in sorted(claim_ids):
        classification, evidence_ids = _classify_delta(
            claim_id=claim_id,
            verification_result=verification_result,
            baseline_claim_ids=baseline_claim_ids,
            candidates_claim_ids=candidates_claim_ids,
        )
        records.append(
            BehavioralDeltaRecord(
                id=_record_id(
                    change_id=change_id,
                    candidate_patch_id=candidate_patch_id,
                    claim_id=claim_id,
                    classification=classification,
                ),
                change_id=change_id,
                candidate_patch_id=candidate_patch_id,
                classification=classification,
                claim_id=claim_id,
                intent_alignment=IntentAlignmentStatus.PENDING.value,
                authorized=None,
                observed_at=observed_at,
                evidence_ids=evidence_ids,
            )
        )
    return tuple(records)

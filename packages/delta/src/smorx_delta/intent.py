"""Phase 10 — intent alignment evaluation.

This module evaluates each observed behavioral delta against the LOCKED intent
ledger items and emits an authorization *recommendation* grounded in that
evidence. It never authorizes by itself: it reports ALIGNED/AUTHORIZED only
when the delta's claim is covered by a ledger item, MISALIGNED/UNAUTHORIZED
when it is not, and PENDING/UNEXPLAINED when no evidence supports a judgment.
Authorization is a human/integration act that consumes these records.
Persistence is performed by the integration layer, never here.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from smorx_behavior.models.enums import IntentAlignmentStatus, IntentKind
from smorx_verification.contracts import VerificationResult
from sqlalchemy.orm import Session

from smorx_delta.deltas import BehavioralDeltaRecord

__all__ = [
    "IntentAlignmentRecord",
    "evaluate_intent_alignment",
]

_ALIGNMENT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "smorx:intent-alignment")
_KNOWN_KINDS = frozenset(
    {
        IntentKind.REQUIREMENT.value,
        IntentKind.CONSTRAINT.value,
        IntentKind.ACCEPTANCE_CRITERION.value,
    }
)
_CHANGED_CLASSIFICATIONS = frozenset({"ALTERED", "ADDED", "REMOVED"})
_VERDICT_AUTHORIZED = "AUTHORIZED"
_VERDICT_UNAUTHORIZED = "UNAUTHORIZED"
_VERDICT_UNEXPLAINED = "UNEXPLAINED"
_SCORE_CONSTRAINT = 0.9
_SCORE_REQUIREMENT = 0.8
_SCORE_UNAUTHORIZED = 0.0
_SCORE_UNCHANGED = 1.0
_SCORE_UNEXPLAINED = 0.0
_RATIONALE_UNAUTHORIZED = "observed change is not covered by any locked intent ledger item"
_RATIONALE_UNCHANGED = "no behavioral change observed; nothing to authorize"
_RATIONALE_UNEXPLAINED = "no evidence to support authorization judgment"


@dataclass(frozen=True)
class IntentAlignmentRecord:
    """One authorization recommendation for a single claim.

    The record binds the claim to the first matching LOCKED intent ledger item
    (or an empty ``intent_item_id`` when none matched) together with the verdict
    score. It never performs authorization — it only evaluates the observed
    delta against the locked ledger.
    """

    id: str
    intent_item_id: str
    claim_id: str
    status: str
    verdict: str
    rationale: str
    score: float
    evidence_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "intent_item_id": self.intent_item_id,
            "claim_id": self.claim_id,
            "status": self.status,
            "verdict": self.verdict,
            "rationale": self.rationale,
            "score": self.score,
            "evidence_ids": list(self.evidence_ids),
        }


def _scope_texts(item: object) -> tuple[str, ...]:
    """Authorization-scope text of an intent item (defensive on columns)."""
    parts: list[str] = []
    for attribute in ("statement", "behaviors", "targets", "behavior", "target"):
        value = getattr(item, attribute, None)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list | tuple):
            parts.extend(entry for entry in value if isinstance(entry, str))
    return tuple(parts)


def _mentions_claim(item: object, claim_id: str) -> bool:
    needle = claim_id.lower()
    if not needle:
        return False
    return any(needle in text.lower() for text in _scope_texts(item) if text)


def _kind(item: object) -> str:
    raw = getattr(item, "kind", None)
    if raw is None:
        return ""
    return raw.value if isinstance(raw, IntentKind) else str(raw)


def _item_id(item: object) -> str:
    raw = getattr(item, "id", None)
    return "" if raw is None else str(raw)


def _statement(item: object) -> str:
    raw = getattr(item, "statement", None)
    return "" if raw is None else str(raw)


def _first_matching_intent_item(claim_id: str, intent_items: Sequence[object]) -> object | None:
    for item in intent_items:
        if _kind(item) in _KNOWN_KINDS and _mentions_claim(item, claim_id):
            return item
    return None


def _constraint_rationale(item: object) -> str:
    return f"covered by CONSTRAINT intent item {_item_id(item)}: {_statement(item)}"


def _requirement_rationale(item: object) -> str:
    return f"covered by {_kind(item)} intent item {_item_id(item)}: {_statement(item)}"


def _record(
    delta: BehavioralDeltaRecord,
    *,
    intent_item_id: str,
    status: IntentAlignmentStatus,
    verdict: str,
    rationale: str,
    score: float,
) -> IntentAlignmentRecord:
    return IntentAlignmentRecord(
        id=str(uuid.uuid5(_ALIGNMENT_NAMESPACE, f"{delta.claim_id}|{intent_item_id}|{verdict}")),
        intent_item_id=intent_item_id,
        claim_id=delta.claim_id,
        status=status.value,
        verdict=verdict,
        rationale=rationale,
        score=score,
        evidence_ids=delta.evidence_ids,
    )


def _align_delta(
    delta: BehavioralDeltaRecord, intent_items: Sequence[object]
) -> IntentAlignmentRecord:
    if delta.classification == "UNCHANGED":
        return _record(
            delta,
            intent_item_id="",
            status=IntentAlignmentStatus.ALIGNED,
            verdict=_VERDICT_AUTHORIZED,
            rationale=_RATIONALE_UNCHANGED,
            score=_SCORE_UNCHANGED,
        )
    if delta.classification == "UNEXPLAINED":
        return _record(
            delta,
            intent_item_id="",
            status=IntentAlignmentStatus.PENDING,
            verdict=_VERDICT_UNEXPLAINED,
            rationale=_RATIONALE_UNEXPLAINED,
            score=_SCORE_UNEXPLAINED,
        )
    if delta.classification in _CHANGED_CLASSIFICATIONS:
        matched = _first_matching_intent_item(delta.claim_id, intent_items)
        if matched is None:
            return _record(
                delta,
                intent_item_id="",
                status=IntentAlignmentStatus.MISALIGNED,
                verdict=_VERDICT_UNAUTHORIZED,
                rationale=_RATIONALE_UNAUTHORIZED,
                score=_SCORE_UNAUTHORIZED,
            )
        if _kind(matched) == IntentKind.CONSTRAINT.value:
            return _record(
                delta,
                intent_item_id=_item_id(matched),
                status=IntentAlignmentStatus.ALIGNED,
                verdict=_VERDICT_AUTHORIZED,
                rationale=_constraint_rationale(matched),
                score=_SCORE_CONSTRAINT,
            )
        return _record(
            delta,
            intent_item_id=_item_id(matched),
            status=IntentAlignmentStatus.ALIGNED,
            verdict=_VERDICT_AUTHORIZED,
            rationale=_requirement_rationale(matched),
            score=_SCORE_REQUIREMENT,
        )
    return _record(
        delta,
        intent_item_id="",
        status=IntentAlignmentStatus.PENDING,
        verdict=_VERDICT_UNEXPLAINED,
        rationale="unexpected delta classification; authorization cannot be evaluated",
        score=_SCORE_UNEXPLAINED,
    )


def evaluate_intent_alignment(
    *,
    session: Session,
    verification_result: VerificationResult,
    deltas: Sequence[BehavioralDeltaRecord],
    intent_items: Sequence[object],
) -> tuple[IntentAlignmentRecord, ...]:
    """Evaluate the observed deltas against the LOCKED intent ledger.

    One ``IntentAlignmentRecord`` is returned per delta (claim), in the input
    order. Changed deltas that overlap a ledger item are recommended as
    authorized; changed deltas without coverage are MISALIGNED; unchanged and
    unexplained deltas never carry a positive authorization decision by
    themselves. ``session`` and ``verification_result`` are accepted for
    contract symmetry — nothing is persisted or decided beyond the evidence in
    the deltas. Empty ``deltas`` yields an empty tuple.
    """
    return tuple(_align_delta(delta, intent_items) for delta in deltas)

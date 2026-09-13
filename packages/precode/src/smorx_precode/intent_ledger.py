"""Phase 7.3/7.4 — Intent Ledger, constitutional constraints, and the lock.

Owns the structured Intent Ledger (IntentLedger + IntentItem rows) and the
constitutional constraint resolution against the real Behavioral
Constitution tables from Phase 2.

Immutability rules (master prompt §7.4, AGENTS.md §9, I9):

- an IntentLedger starts ``locked=False`` with ``version=1``;
- :func:`lock_intent_ledger` flips it to ``LOCKED`` exactly once — the lock
  is permanent and idempotent;
- mutation of a locked ledger raises :class:`IntentLedgerLockedError`;
- a genuine contract change goes through :func:`bump` (new identity, new
  version, historical row preserved) — never a silent in-place rewrite.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from smorx_behavior.models import Constitution, ConstitutionClaim, IntentItem, IntentLedger
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning.lock import (
    VersioningError,
    VersionLockedError,
)
from smorx_behavior.versioning.lock import (
    lock as versioning_lock,
)
from smorx_behavior.versioning.service import bump
from sqlalchemy.orm import Session

from smorx_precode.intent_compiler import compile_intent

__all__ = [
    "ConstitutionMapperError",
    "ConstraintResolution",
    "IntentLedgerError",
    "IntentLedgerLockedError",
    "IntentLedgerRef",
    "build_intent_ledger",
    "bump_intent_ledger",
    "get_intent_ledger",
    "lock_intent_ledger",
    "resolve_constraints",
]


class IntentLedgerError(Exception):
    """Base error for Intent Ledger failures."""


class IntentLedgerLockedError(IntentLedgerError):
    """Raised on any attempt to mutate a LOCKED Intent Ledger in place."""


class ConstitutionMapperError(IntentLedgerError):
    """Raised when constitutional constraint resolution fails."""


@dataclass(frozen=True)
class IntentLedgerRef:
    """Stable reference to the persisted ledger returned to callers."""

    intent_ledger_id: uuid.UUID
    project_id: uuid.UUID
    task_id: uuid.UUID | None
    version: int
    locked: bool
    status: str
    intent_item_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class ConstraintResolution:
    """Result of mapping request intent onto the Behavioral Constitution."""

    intent_ledger_id: uuid.UUID
    constitution_id: uuid.UUID
    constitution_version: int
    constitution_locked: bool
    protected_claim_ids: tuple[uuid.UUID, ...]
    matched_claim_ids: tuple[uuid.UUID, ...]
    conflicting_claim_ids: tuple[uuid.UUID, ...]
    risk_notes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent_ledger_id": str(self.intent_ledger_id),
            "constitution_id": str(self.constitution_id),
            "constitution_version": self.constitution_version,
            "constitution_locked": self.constitution_locked,
            "protected_claim_ids": [str(i) for i in self.protected_claim_ids],
            "matched_claim_ids": [str(i) for i in self.matched_claim_ids],
            "conflicting_claim_ids": [str(i) for i in self.conflicting_claim_ids],
            "risk_notes": list(self.risk_notes),
        }


def build_intent_ledger(
    session: Session,
    *,
    project_id: uuid.UUID,
    task_id: uuid.UUID | None,
    objective: str,
    statements: list[dict[str, str]],
    acceptance_criteria: list[str],
    authority: str = "HUMAN",
    created_by: str | None = None,
) -> IntentLedgerRef:
    """Compile intent statements and persist the structured Intent Ledger.

    Compilation (5 distinct dimensions) is delegated to
    :func:`smorx_precode.intent_compiler.compile_intent`, so ambiguity and
    dimension rules stay in exactly one place.
    """
    intents = compile_intent(
        objective=objective, statements=statements, acceptance_criteria=acceptance_criteria
    )

    ledger = IntentLedger(
        project_id=project_id,
        task_id=task_id,
        title=objective[:300],
        source=authority,
        status="PROPOSED",
        owner_scope="USER_INTENT",
        created_by=created_by,
        version=1,
        locked=False,
    )
    repo_base.save(session, ledger)

    item_ids: list[uuid.UUID] = []
    for intent in intents:
        item = IntentItem(
            intent_ledger_id=ledger.id,
            task_id=task_id,
            statement=intent.description,
            kind=intent.intent_type,
            priority="NORMAL",
            status="PENDING",
            authorized=False,
        )
        repo_base.save(session, item)
        item_ids.append(item.id)

    return IntentLedgerRef(
        intent_ledger_id=ledger.id,
        project_id=project_id,
        task_id=task_id,
        version=ledger.version,
        locked=ledger.locked,
        status=ledger.status,
        intent_item_ids=tuple(item_ids),
    )


def get_intent_ledger(session: Session, intent_ledger_id: uuid.UUID) -> IntentLedgerRef:
    """Load a ledger reference, raising when the ledger does not exist."""
    ledger = repo_base.get(session, IntentLedger, intent_ledger_id)
    if ledger is None:
        raise IntentLedgerError(f"unknown intent_ledger_id {intent_ledger_id}")
    items = repo_base.list_(session, IntentItem, intent_ledger_id=ledger.id)
    return IntentLedgerRef(
        intent_ledger_id=ledger.id,
        project_id=ledger.project_id,
        task_id=ledger.task_id,
        version=ledger.version,
        locked=ledger.locked,
        status=ledger.status,
        intent_item_ids=tuple(item.id for item in items),
    )


def lock_intent_ledger(session: Session, intent_ledger_id: uuid.UUID) -> IntentLedgerRef:
    """Flip the ledger to LOCKED exactly once; idempotent afterwards.

    Confirmation requirement (§7.4): the caller asserts that a human
    confirmed the ledger before locking. Items are marked authorized at
    lock time — authorization is granted by the explicit lock action, not
    silently during construction.
    """
    ledger = repo_base.get(session, IntentLedger, intent_ledger_id)
    if ledger is None:
        raise IntentLedgerError(f"unknown intent_ledger_id {intent_ledger_id}")
    if not ledger.locked:
        versioning_lock(session, ledger)
        ledger.status = "LOCKED"
        items = repo_base.list_(session, IntentItem, intent_ledger_id=ledger.id)
        for item in items:
            item.status = "CONFIRMED"
            item.authorized = True
        session.flush()
    return get_intent_ledger(session, ledger.id)


def bump_intent_ledger(
    session: Session, intent_ledger_id: uuid.UUID, *, note: str | None = None
) -> IntentLedgerRef:
    """Create the next version of the ledger (new identity) per ADR-0005.

    This is the ONLY sanctioned path for changing a locked ledger's
    contract: a new row with ``version+1`` and a parent reference, the
    historical row untouched (I8/I9).
    """
    ledger = repo_base.get(session, IntentLedger, intent_ledger_id)
    if ledger is None:
        raise IntentLedgerError(f"unknown intent_ledger_id {intent_ledger_id}")
    try:
        bumped = bump(session, ledger, note=note or "intent revision")
    except VersionLockedError as exc:  # pragma: no cover - bump handles locks
        raise IntentLedgerLockedError(str(exc)) from exc
    except VersioningError as exc:
        raise IntentLedgerError(str(exc)) from exc
    return get_intent_ledger(session, bumped.id)


def resolve_constraints(
    session: Session,
    *,
    intent_ledger_id: uuid.UUID,
    constitution_id: uuid.UUID,
) -> ConstraintResolution:
    """Map the ledger's intent items onto protected constitution claims.

    Historical behavior is evidence, not automatically human intent — so
    matches are surfaced as ``matched_claim_ids`` (constraints the coding
    agent must respect) and REPLACE conflicts as ``conflicting_claim_ids``
    plus ``risk_notes``. Nothing here silently authorizes destruction of a
    protected claim; Phase 8's barrier consumes this resolution verbatim.
    """
    ledger = repo_base.get(session, IntentLedger, intent_ledger_id)
    if ledger is None:
        raise IntentLedgerError(f"unknown intent_ledger_id {intent_ledger_id}")
    constitution = repo_base.get(session, Constitution, constitution_id)
    if constitution is None:
        raise ConstitutionMapperError(f"unknown constitution_id {constitution_id}")
    if not constitution.locked:
        raise ConstitutionMapperError(
            f"constitution {constitution_id} is not locked; resolve_constraints "
            "requires a locked Behavioral Constitution"
        )

    claims = repo_base.list_(session, ConstitutionClaim, constitution_id=constitution.id)
    items = repo_base.list_(session, IntentItem, intent_ledger_id=ledger.id)

    def _terms(text: str) -> set[str]:
        return {word for word in text.lower().split() if len(word) > 3}

    item_terms = {item.id: _terms(item.statement) for item in items}
    matched: list[uuid.UUID] = []
    conflicts: list[uuid.UUID] = []
    notes: list[str] = []
    for claim in claims:
        claim_terms = _terms(claim.rule or "")
        if not claim_terms:
            continue
        hits = [
            item.id for item in items if item_terms[item.id] and claim_terms & item_terms[item.id]
        ]
        if not hits:
            continue
        matched.append(claim.id)
        replace_hits = [i for i in hits if items_by_id(items)[i].kind == "REPLACE"]
        if replace_hits:
            conflicts.append(claim.id)
            for item_id in replace_hits:
                notes.append(
                    f"REPLACE intent item {item_id} overlaps protected claim "
                    f"{claim.id} [{claim.category}/{claim.severity}]: "
                    f"{(claim.rule or '')[:80]}; explicit human authorization "
                    "required before the coding agent may touch it"
                )
    return ConstraintResolution(
        intent_ledger_id=ledger.id,
        constitution_id=constitution.id,
        constitution_version=constitution.version,
        constitution_locked=constitution.locked,
        protected_claim_ids=tuple(claim.id for claim in claims),
        matched_claim_ids=tuple(matched),
        conflicting_claim_ids=tuple(conflicts),
        risk_notes=tuple(notes),
    )


def items_by_id(items: list[IntentItem]) -> dict[uuid.UUID, IntentItem]:
    """Index items by id (small helper kept deterministic for resolution)."""
    return {item.id: item for item in items}

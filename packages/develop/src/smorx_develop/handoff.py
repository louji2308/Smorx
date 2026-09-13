"""Phase 8.1 — Pre-Coding Handoff.

The Coding Agent's runtime receives the immutable Phase 7 context
(:class:`smorx_precode.lock_gate.PreCodingContext`) verbatim. The received
versions must be exact: :func:`pre_coding_handoff` rejects stale or
mismatched context instead of continuing anyway (master prompt §8.1, §8).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from smorx_precode.lock_gate import PreCodingContext
from sqlalchemy.orm import Session

__all__ = ["HandoffError", "HandoffRecord", "pre_coding_handoff"]


class HandoffError(Exception):
    """Raised when the handoff is stale, mismatched, or unauthorized."""


@dataclass(frozen=True)
class HandoffRecord:
    """What Phase 8 actually received, bound to exact Phase 7 identities."""

    handoff_id: uuid.UUID
    context_id: uuid.UUID
    task_id: uuid.UUID
    change_id: uuid.UUID
    intent_ledger_id: uuid.UUID
    verification_plan_id: uuid.UUID
    intent_version: int
    constitution_version: int
    impact_map_version: int
    verification_plan_version: int
    lock_state: str
    received_at: datetime
    context: PreCodingContext

    def as_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": str(self.handoff_id),
            "context_id": str(self.context_id),
            "task_id": str(self.task_id),
            "change_id": str(self.change_id),
            "intent_ledger_id": str(self.intent_ledger_id),
            "verification_plan_id": str(self.verification_plan_id),
            "intent_version": self.intent_version,
            "impact_map_version": self.impact_map_version,
            "verification_plan_version": self.verification_plan_version,
            "lock_state": self.lock_state,
            "received_at": self.received_at.isoformat(),
        }


def pre_coding_handoff(
    session: Session,
    *,
    context: PreCodingContext,
    expected_lock_state: str = "LOCKED",
) -> HandoffRecord:
    """Receive the Phase 7 context and bind it to Phase 8's execution identity.

    Rules:
    - the context must be a real :class:`PreCodingContext` (no manual
      reconstruction from prose, §7);
    - ``lock_state`` must be exactly ``expected_lock_state`` (default
      LOCKED) — a BLOCKED context is never accepted;
    - stale-context protection (§8): the context's intent ledger and
      verification plan must still be LOCKED in the database and at the
      same versions; if Phase 7 created a new version, the old context is
      rejected.
    """
    if not isinstance(context, PreCodingContext):
        raise HandoffError(
            "handoff requires a real PreCodingContext object; no manual "
            "reconstruction from prose is accepted"
        )
    if context.lock_state != expected_lock_state:
        raise HandoffError(
            f"context lock_state is {context.lock_state!r}, expected "
            f"{expected_lock_state!r}; a blocked context is never accepted"
        )

    # Stale-context protection: re-read the persisted objects and compare
    # exact identity + version, AND verify the object has not been
    # superseded by a newer version in its lineage (§8: referencing v1
    # must not silently continue once v2 exists).
    from smorx_behavior.models import IntentLedger, VerificationPlan
    from smorx_behavior.repo import base as repo_base

    def _successor_id(model: type, object_id) -> object | None:
        """Return the id of the object whose parent-ref points at ``object_id``.

        Bumping a LOCKED object preserves the historical row, so a stale v1
        context still finds its row locked at the same version. Supersession
        is detectable only forward: the successor carries a parent reference.
        """
        from smorx_behavior.versioning.service import PARENT_RESERVED_KEY, parent_storage

        storage = parent_storage(model())
        if storage is None:
            return None
        kind, field = storage
        candidates: list[Any] = repo_base.list_(session, model)
        for candidate in candidates:
            if kind == "json":
                data = getattr(candidate, field, None) or {}
                ref = data.get(PARENT_RESERVED_KEY) if isinstance(data, dict) else None
                if isinstance(ref, dict) and str(ref.get("id")) == str(object_id):
                    return candidate.id
            else:
                text = str(getattr(candidate, field, None) or "")
                if f"[version_parent:{object_id};" in text:
                    return candidate.id
        return None

    ledger = repo_base.get(session, IntentLedger, context.intent_ledger_id)
    if ledger is None:
        raise HandoffError(
            f"intent ledger {context.intent_ledger_id} no longer exists; context is stale"
        )
    if not ledger.locked:
        raise HandoffError(
            f"intent ledger {context.intent_ledger_id} is no longer locked; context is stale"
        )
    if ledger.version != context.intent_version:
        raise HandoffError(
            f"stale context: intent ledger version moved "
            f"{context.intent_version} -> {ledger.version}"
        )
    superseding_ledger = _successor_id(IntentLedger, ledger.id)
    if superseding_ledger is not None:
        raise HandoffError(
            f"stale context: intent ledger {ledger.id} (v{ledger.version}) has been "
            f"superseded by {superseding_ledger}; create a new pre-coding context "
            "for the current version"
        )

    plan = repo_base.get(session, VerificationPlan, context.verification_plan_id)
    if plan is None:
        raise HandoffError(
            f"verification plan {context.verification_plan_id} no longer exists; context is stale"
        )
    if not plan.locked:
        raise HandoffError(
            f"verification plan {context.verification_plan_id} is no longer locked; "
            "context is stale"
        )
    if plan.version != context.verification_plan_version:
        raise HandoffError(
            "stale context: verification plan version moved "
            f"{context.verification_plan_version} -> {plan.version}"
        )
    superseding_plan = _successor_id(VerificationPlan, plan.id)
    if superseding_plan is not None:
        raise HandoffError(
            f"stale context: verification plan {plan.id} (v{plan.version}) has been "
            f"superseded by {superseding_plan}"
        )
    if plan.task_id is not None and plan.task_id != context.task_id:
        raise HandoffError(
            f"context task mismatch: plan is bound to task {plan.task_id}, "
            f"context carries {context.task_id}"
        )

    return HandoffRecord(
        handoff_id=uuid.uuid4(),
        context_id=context.context_id,
        task_id=context.task_id,
        change_id=context.change_id,
        intent_ledger_id=context.intent_ledger_id,
        verification_plan_id=context.verification_plan_id,
        intent_version=context.intent_version,
        constitution_version=context.constitution_version,
        impact_map_version=context.impact_map_version,
        verification_plan_version=context.verification_plan_version,
        lock_state=context.lock_state,
        received_at=datetime.now(UTC),
        context=context,
    )

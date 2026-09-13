"""Phase 8.2 — The Execution Barrier.

The official architectural gate before the Coding Agent may act on a real
change (master prompt §8.2):

    VALID HUMAN REQUEST
    + VALID INTENT LEDGER (LOCKED)
    + VALID CONSTITUTIONAL CONSTRAINTS
    + VALID SEMANTIC IMPACT MAP (LOCKED)
    + VALID VERIFICATION PLAN (LOCKED)
    + VERSIONS COMPATIBLE
    = CODING AGENT MAY START

If ANY condition fails: BLOCK. Do not \"continue anyway\". This module is
the enforcement point; the Coding Agent loop refuses to enter EXECUTING
without a PASS verdict from :func:`evaluate_barrier` for the same handoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from smorx_behavior.models import IntentLedger, SemanticImpact, VerificationPlan
from smorx_behavior.repo import base as repo_base
from smorx_precode.lock_gate import PreCodingContext
from sqlalchemy.orm import Session

from smorx_develop.handoff import HandoffError, HandoffRecord, pre_coding_handoff

__all__ = ["BarrierError", "BarrierVerdict", "ExecutionBarrier"]


class BarrierError(Exception):
    """Raised when the barrier itself cannot be evaluated (bad inputs)."""


@dataclass(frozen=True)
class BarrierVerdict:
    """Barrier outcome with every failed condition named."""

    state: str  # PASS | BLOCKED
    handoff: HandoffRecord | None
    failed_conditions: tuple[str, ...]

    @property
    def allowed(self) -> bool:
        return self.state == "PASS"

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "failed_conditions": list(self.failed_conditions),
            "handoff_id": str(self.handoff.handoff_id) if self.handoff else None,
        }


class ExecutionBarrier:
    """Replayable gate object guarding the Coding Agent's execution state."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def evaluate(
        self,
        *,
        context: PreCodingContext,
        authorized: bool = False,
    ) -> BarrierVerdict:
        """Run every barrier condition; return PASS only when all hold.

        ``authorized`` is the explicit human/authority flag for this
        execution (task authorization is an input, never inferred).
        """
        failed: list[str] = []

        try:
            handoff = pre_coding_handoff(self._session, context=context)
        except HandoffError as exc:
            return BarrierVerdict(
                state="BLOCKED", handoff=None, failed_conditions=(f"handoff invalid: {exc}",)
            )

        # Condition checks — every failure is recorded, evaluation continues
        # so the operator sees the full condition set at once.
        ledger = repo_base.get(self._session, IntentLedger, handoff.intent_ledger_id)
        if ledger is None:
            failed.append("intent ledger does not exist")
        elif not ledger.locked:
            failed.append("intent is not locked")

        constitution_version = handoff.constitution_version
        if constitution_version < 1:
            failed.append("constitution context does not exist")

        impact_rows = repo_base.list_(self._session, SemanticImpact, task_id=handoff.task_id)
        if not impact_rows:
            failed.append("semantic impact map does not exist")
        elif not impact_rows[0].locked:
            failed.append("semantic impact map is not locked")
        elif impact_rows[0].version != handoff.impact_map_version:
            failed.append(
                "impact map version mismatch: context carries "
                f"{handoff.impact_map_version}, persisted is {impact_rows[0].version}"
            )

        plan = repo_base.get(self._session, VerificationPlan, handoff.verification_plan_id)
        if plan is None:
            failed.append("verification plan does not exist")
        elif not plan.locked:
            failed.append("verification plan is not locked")
        elif plan.version != handoff.verification_plan_version:
            failed.append(
                "verification plan version mismatch: context carries "
                f"{handoff.verification_plan_version}, persisted is {plan.version}"
            )

        if not authorized:
            failed.append(
                "task is not authorized for execution; an explicit authorization "
                "flag is required (no implicit execution)"
            )

        if failed:
            return BarrierVerdict(state="BLOCKED", handoff=handoff, failed_conditions=tuple(failed))
        return BarrierVerdict(state="PASS", handoff=handoff, failed_conditions=())

    def require_pass(self, *, context: PreCodingContext, authorized: bool = False) -> HandoffRecord:
        """Return the handoff only on PASS; raise :class:`BarrierError` otherwise.

        The Coding Agent loop calls this before entering EXECUTING; the
        raised error is the hard stop (§8.2: do not continue anyway).
        """
        verdict = self.evaluate(context=context, authorized=authorized)
        if not verdict.allowed:
            raise BarrierError("execution barrier BLOCKED: " + "; ".join(verdict.failed_conditions))
        assert verdict.handoff is not None
        return verdict.handoff

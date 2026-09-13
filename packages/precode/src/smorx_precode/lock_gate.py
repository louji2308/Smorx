"""Phase 7.7 — Pre-Coding Context and the lock gate.

Produces ONE complete pre-coding context object (master prompt §7.7):

    Human Request + Intent Ledger + Behavioral Constitution
    + Semantic Impact Map + Verification Plan

and validates every component before locking. The gate is the official
architectural barrier (§7.9): the Coding Agent may start ONLY when the
context validates with all required locked state — otherwise the gate
returns a BLOCKED verdict carrying every failed requirement by name.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from smorx_behavior.models import Constitution
from smorx_behavior.repo import base as repo_base
from sqlalchemy.orm import Session

from smorx_precode.change_definition import ChangeDefinition, get_change_definition
from smorx_precode.impact import (
    SemanticImpactError,
    SemanticImpactMap,
    get_semantic_impact,
)
from smorx_precode.intent_ledger import (
    ConstraintResolution,
    IntentLedgerError,
    IntentLedgerRef,
    get_intent_ledger,
    resolve_constraints,
)
from smorx_precode.verification_plan import (
    VerificationPlanError,
    VerificationPlanRef,
    get_verification_plan,
)

__all__ = [
    "PreCodingContext",
    "PreCodingGateError",
    "PreCodingGateVerdict",
    "pre_coding_gate",
]


class PreCodingGateError(Exception):
    """Raised when the gate itself cannot run (missing rows, bad ids)."""


@dataclass(frozen=True)
class PreCodingContext:
    """The immutable, machine-readable handoff object for Phase 8.

    ``context_id`` plus the exact versions form the stale-context identity
    that Phase 8 must consume verbatim (cross-session handoff, §7).
    """

    context_id: uuid.UUID
    task_id: uuid.UUID
    change_id: uuid.UUID
    repository_slug: str
    intent_ledger_id: uuid.UUID
    constitution_id: uuid.UUID
    semantic_impact_id: uuid.UUID
    verification_plan_id: uuid.UUID
    intent_version: int
    constitution_version: int
    impact_map_version: int
    verification_plan_version: int
    lock_state: str  # BLOCKED | LOCKED
    locked_objects: tuple[str, ...]
    created_at: datetime
    definition: ChangeDefinition
    resolution: ConstraintResolution
    impact_map: SemanticImpactMap
    plan: VerificationPlanRef

    def as_dict(self) -> dict[str, Any]:
        return {
            "context_id": str(self.context_id),
            "task_id": str(self.task_id),
            "change_id": str(self.change_id),
            "repository": self.repository_slug,
            "intent_version": self.intent_version,
            "constitution_version": self.constitution_version,
            "impact_map_version": self.impact_map_version,
            "verification_plan_version": self.verification_plan_version,
            "lock_state": self.lock_state,
            "locked_objects": list(self.locked_objects),
            "created_at": self.created_at.isoformat(),
            "definition": self.definition.as_dict(),
            "constraints": self.resolution.as_dict(),
            "impact_map": self.impact_map.as_dict(),
            "verification_plan": self.plan.as_dict(),
        }


@dataclass(frozen=True)
class PreCodingGateVerdict:
    """Gate outcome with every failed requirement named (never 'looks good')."""

    state: str  # PASS | BLOCKED
    context: PreCodingContext | None
    failed_requirements: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "failed_requirements": list(self.failed_requirements),
            "context": self.context.as_dict() if self.context else None,
        }


def _load_plan_for_task(session: Session, task_id: uuid.UUID) -> VerificationPlanRef:
    from smorx_behavior.models import VerificationPlan

    rows = repo_base.list_(session, VerificationPlan, task_id=task_id)
    if not rows:
        raise VerificationPlanError(f"no verification plan exists for task {task_id}")
    return get_verification_plan(session, rows[0].id)


def _collect_components(
    session: Session,
    *,
    task_id: uuid.UUID,
    intent_ledger_id: uuid.UUID,
    constitution_id: uuid.UUID,
) -> tuple[
    ChangeDefinition | None,
    IntentLedgerRef | None,
    ConstraintResolution | None,
    SemanticImpactMap | None,
    VerificationPlanRef | None,
    list[str],
]:
    """Load every component, naming each failure instead of failing fast."""
    failed: list[str] = []
    definition: ChangeDefinition | None = None
    ledger_ref: IntentLedgerRef | None = None
    resolution: ConstraintResolution | None = None
    impact_map: SemanticImpactMap | None = None
    plan: VerificationPlanRef | None = None
    constitution_locked_ok = False

    try:
        definition = get_change_definition(session, task_id)
    except Exception as exc:
        failed.append(f"change definition invalid: {exc}")

    try:
        ledger_ref = get_intent_ledger(session, intent_ledger_id)
        if ledger_ref.task_id is not None and ledger_ref.task_id != task_id:
            failed.append(
                f"intent ledger {intent_ledger_id} is bound to task "
                f"{ledger_ref.task_id}, not {task_id}"
            )
    except IntentLedgerError as exc:
        failed.append(f"intent ledger invalid: {exc}")

    try:
        impact_map = get_semantic_impact(session, task_id)
    except SemanticImpactError as exc:
        failed.append(f"semantic impact map invalid: {exc}")

    try:
        plan = _load_plan_for_task(session, task_id)
    except VerificationPlanError as exc:
        failed.append(f"verification plan invalid: {exc}")

    if constitution_id is None or constitution_id == uuid.UUID(int=0):
        failed.append("constitution_id is required")
    else:
        constitution = repo_base.get(session, Constitution, constitution_id)
        if constitution is None:
            failed.append(f"constitution {constitution_id} is unknown")
        elif not constitution.locked:
            failed.append(f"constitution {constitution_id} is not locked")
        else:
            constitution_locked_ok = True

    if (
        plan is not None
        and plan.intent_ledger_id is not None
        and plan.intent_ledger_id != intent_ledger_id
    ):
        failed.append(
            f"verification plan {plan.verification_plan_id} references intent ledger "
            f"{plan.intent_ledger_id}, not {intent_ledger_id}"
        )

    if ledger_ref is not None and constitution_locked_ok:
        try:
            resolution = resolve_constraints(
                session, intent_ledger_id=intent_ledger_id, constitution_id=constitution_id
            )
        except IntentLedgerError as exc:
            failed.append(f"constitutional constraint resolution failed: {exc}")

    return definition, ledger_ref, resolution, impact_map, plan, failed


def _build_context(
    *,
    task_id: uuid.UUID,
    change_id: uuid.UUID,
    constitution_id: uuid.UUID,
    definition: ChangeDefinition,
    ledger_ref: IntentLedgerRef,
    resolution: ConstraintResolution,
    impact_map: SemanticImpactMap,
    plan: VerificationPlanRef,
) -> PreCodingContext:
    locked_objects: list[str] = []
    if ledger_ref.locked:
        locked_objects.append(f"intent_ledger:{ledger_ref.intent_ledger_id}")
    if impact_map.locked:
        locked_objects.append(f"semantic_impact:{impact_map.semantic_impact_id}")
    if plan.locked:
        locked_objects.append(f"verification_plan:{plan.verification_plan_id}")
    lock_state = "LOCKED" if len(locked_objects) == 3 else "BLOCKED"
    return PreCodingContext(
        context_id=uuid.uuid4(),
        task_id=task_id,
        change_id=change_id,
        repository_slug=definition.repository_name,
        intent_ledger_id=ledger_ref.intent_ledger_id,
        constitution_id=constitution_id,
        semantic_impact_id=impact_map.semantic_impact_id,
        verification_plan_id=plan.verification_plan_id,
        intent_version=ledger_ref.version,
        constitution_version=resolution.constitution_version,
        impact_map_version=impact_map.version,
        verification_plan_version=plan.version,
        lock_state=lock_state,
        locked_objects=tuple(locked_objects),
        created_at=datetime.now(UTC),
        definition=definition,
        resolution=resolution,
        impact_map=impact_map,
        plan=plan,
    )


def pre_coding_gate(
    session: Session,
    *,
    task_id: uuid.UUID,
    intent_ledger_id: uuid.UUID,
    constitution_id: uuid.UUID,
) -> PreCodingGateVerdict:
    """Validate the complete pre-coding context; return PASS or BLOCKED.

    PASS requires: a valid change definition, a LOCKED intent ledger bound
    to the task, a LOCKED constitution, a LOCKED impact map for the task,
    and a LOCKED verification plan for the task whose intent-ledger
    reference matches. Any other combination is BLOCKED with every failed
    requirement listed.
    """
    definition, ledger_ref, resolution, impact_map, plan, failed = _collect_components(
        session,
        task_id=task_id,
        intent_ledger_id=intent_ledger_id,
        constitution_id=constitution_id,
    )

    context: PreCodingContext | None = None
    if (
        definition is not None
        and ledger_ref is not None
        and resolution is not None
        and impact_map is not None
        and plan is not None
    ):
        try:
            context = _build_context(
                task_id=task_id,
                change_id=plan.change_id,  # the plan is validated bound to this task
                constitution_id=constitution_id,
                definition=definition,
                ledger_ref=ledger_ref,
                resolution=resolution,
                impact_map=impact_map,
                plan=plan,
            )
        except Exception as exc:
            failed.append(f"pre-coding context could not be assembled: {exc}")

    if failed:
        return PreCodingGateVerdict(
            state="BLOCKED", context=context, failed_requirements=tuple(failed)
        )

    assert context is not None
    if context.lock_state != "LOCKED":
        missing = sorted(
            {"intent_ledger", "semantic_impact", "verification_plan"}
            - {obj.split(":", 1)[0] for obj in context.locked_objects}
        )
        return PreCodingGateVerdict(
            state="BLOCKED",
            context=context,
            failed_requirements=(tuple(f"required object not locked: {name}" for name in missing)),
        )
    return PreCodingGateVerdict(state="PASS", context=context, failed_requirements=())

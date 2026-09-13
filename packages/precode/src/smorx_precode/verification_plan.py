"""Phase 7.6/7.7 — Verification Plan and its immutable lock.

Generates the verification contract BEFORE coding begins and persists it in
the real ``VerificationPlan`` / ``VerificationCase`` entities.

Coverage rule (master prompt §7.6): the plan must map verification
requirements onto affected behaviors. Every case must target at least one
affected behavior, and every affected behavior must be covered by at least
one case — a plan that fails either rule is rejected, not softened.

The lock rule (§7.7): the plan becomes immutable before the Coding Agent is
invoked. :func:`lock_verification_plan` flips the plan (and its cases) to
LOCKED exactly once; afterwards in-place mutation raises via the versioning
layer, and genuine changes create a new version (I9).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from smorx_behavior.models import VerificationCase, VerificationPlan
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning.lock import lock as versioning_lock
from sqlalchemy.orm import Session

__all__ = [
    "VerificationCaseSpec",
    "VerificationPlanError",
    "VerificationPlanRef",
    "build_verification_plan",
    "get_verification_plan",
    "lock_verification_plan",
]


class VerificationPlanError(Exception):
    """Base error for verification-plan failures."""


@dataclass(frozen=True)
class VerificationCaseSpec:
    """A requested verification case mapped onto affected behaviors."""

    name: str
    kind: str
    behaviors: tuple[str, ...]
    description: str = ""
    method: str = ""
    expected: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "behaviors": list(self.behaviors),
            "description": self.description,
            "method": self.method,
            "expected": self.expected,
        }


@dataclass(frozen=True)
class VerificationPlanRef:
    """Stable machine-readable view of the persisted plan."""

    verification_plan_id: uuid.UUID
    change_id: uuid.UUID
    task_id: uuid.UUID | None
    intent_ledger_id: uuid.UUID | None
    title: str
    version: int
    locked: bool
    status: str
    cases: tuple[VerificationCaseSpec, ...]
    coverage: dict[str, tuple[str, ...]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "verification_plan_id": str(self.verification_plan_id),
            "change_id": str(self.change_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "intent_ledger_id": str(self.intent_ledger_id) if self.intent_ledger_id else None,
            "title": self.title,
            "version": self.version,
            "locked": self.locked,
            "status": self.status,
            "cases": [case.as_dict() for case in self.cases],
            "coverage": {behavior: list(cases) for behavior, cases in self.coverage.items()},
        }


_CASE_KINDS: frozenset[str] = frozenset(
    {
        "UNIT_TEST",
        "INTEGRATION_TEST",
        "REGRESSION_CHECK",
        "BEHAVIORAL_CHECK",
        "SECURITY_CHECK",
        "PERFORMANCE_CHECK",
        "RUNTIME_INVESTIGATION",
        "ADVERSARIAL_CASE",
    }
)


def _validate(
    affected_behaviors: list[str], cases: list[VerificationCaseSpec]
) -> dict[str, tuple[str, ...]]:
    if not affected_behaviors:
        raise VerificationPlanError(
            "verification plan requires at least one affected behavior to cover"
        )
    if not cases:
        raise VerificationPlanError("verification plan requires at least one case")
    behavior_set = set(affected_behaviors)
    coverage: dict[str, list[str]] = {behavior: [] for behavior in affected_behaviors}
    seen_names: set[str] = set()
    for case in cases:
        if not case.name.strip():
            raise VerificationPlanError("verification case name must be non-empty")
        if case.name in seen_names:
            raise VerificationPlanError(f"duplicate verification case name {case.name!r}")
        seen_names.add(case.name)
        if case.kind not in _CASE_KINDS:
            raise VerificationPlanError(
                f"unknown case kind {case.kind!r}; expected one of {sorted(_CASE_KINDS)}"
            )
        targets = set(case.behaviors)
        if not targets:
            raise VerificationPlanError(
                f"case {case.name!r} targets no behavior; every case must map to "
                "at least one affected behavior"
            )
        unknown = targets - behavior_set
        if unknown:
            raise VerificationPlanError(
                f"case {case.name!r} targets behaviors outside the impact map: {sorted(unknown)}"
            )
        for behavior in case.behaviors:
            coverage[behavior].append(case.name)
    uncovered = [b for b, names in coverage.items() if not names]
    if uncovered:
        raise VerificationPlanError(
            "uncovered affected behaviors (every affected behavior needs at "
            f"least one case): {sorted(uncovered)}"
        )
    return {behavior: tuple(names) for behavior, names in coverage.items()}


def build_verification_plan(
    session: Session,
    *,
    change_id: uuid.UUID,
    task_id: uuid.UUID,
    intent_ledger_id: uuid.UUID | None,
    title: str,
    affected_behaviors: list[str],
    cases: list[VerificationCaseSpec],
    created_by: str | None = None,
) -> VerificationPlanRef:
    """Validate coverage and persist the plan plus its cases (status DRAFT)."""
    coverage = _validate(affected_behaviors, cases)

    plan = VerificationPlan(
        change_id=change_id,
        task_id=task_id,
        intent_ledger_id=intent_ledger_id,
        title=title[:300],
        strategy={
            "affected_behaviors": list(affected_behaviors),
            "coverage": {behavior: list(names) for behavior, names in coverage.items()},
            "case_count": len(cases),
        },
        verification_contract={"cases": [case.as_dict() for case in cases]},
        status="DRAFT",
        owner_scope="VERIFICATION_CONTRACT",
        created_by=created_by,
        version=1,
        locked=False,
    )
    repo_base.save(session, plan)

    for case in cases:
        repo_base.save(
            session,
            VerificationCase(
                verification_plan_id=plan.id,
                change_id=change_id,
                name=case.name[:200],
                kind=case.kind,
                description=case.description or None,
                method=case.method or None,
                expected=case.expected or None,
                status="PENDING",
                independent=True,
                owning_module="smorx_precode.verification_plan",
                version=1,
                locked=False,
            ),
        )

    return VerificationPlanRef(
        verification_plan_id=plan.id,
        change_id=change_id,
        task_id=task_id,
        intent_ledger_id=intent_ledger_id,
        title=plan.title,
        version=plan.version,
        locked=plan.locked,
        status=plan.status,
        cases=tuple(cases),
        coverage=dict(coverage),
    )


def _ref_from_row(plan: VerificationPlan, case_rows: list[VerificationCase]) -> VerificationPlanRef:
    strategy = plan.strategy or {}
    coverage = {
        behavior: tuple(names) for behavior, names in (strategy.get("coverage") or {}).items()
    }
    cases = tuple(
        VerificationCaseSpec(
            name=row.name,
            kind=row.kind,
            behaviors=tuple(
                behavior
                for behavior, names in (strategy.get("coverage") or {}).items()
                if row.name in names
            ),
            description=row.description or "",
            method=row.method or "",
            expected=row.expected or "",
        )
        for row in case_rows
    )
    return VerificationPlanRef(
        verification_plan_id=plan.id,
        change_id=plan.change_id,
        task_id=plan.task_id,
        intent_ledger_id=plan.intent_ledger_id,
        title=plan.title,
        version=plan.version,
        locked=plan.locked,
        status=plan.status,
        cases=cases,
        coverage=coverage,
    )


def get_verification_plan(session: Session, verification_plan_id: uuid.UUID) -> VerificationPlanRef:
    """Load a plan view, raising when the plan does not exist."""
    plan = repo_base.get(session, VerificationPlan, verification_plan_id)
    if plan is None:
        raise VerificationPlanError(f"unknown verification_plan_id {verification_plan_id}")
    case_rows = repo_base.list_(session, VerificationCase, verification_plan_id=plan.id)
    return _ref_from_row(plan, case_rows)


def lock_verification_plan(
    session: Session, verification_plan_id: uuid.UUID
) -> VerificationPlanRef:
    """Lock the plan and all of its cases; the lock is permanent (I9, §7.7)."""
    plan = repo_base.get(session, VerificationPlan, verification_plan_id)
    if plan is None:
        raise VerificationPlanError(f"unknown verification_plan_id {verification_plan_id}")
    if not plan.locked:
        versioning_lock(session, plan)
        plan.status = "LOCKED"
        case_rows = repo_base.list_(session, VerificationCase, verification_plan_id=plan.id)
        for row in case_rows:
            if not row.locked:
                versioning_lock(session, row)
        session.flush()
    case_rows = repo_base.list_(session, VerificationCase, verification_plan_id=plan.id)
    return _ref_from_row(plan, case_rows)

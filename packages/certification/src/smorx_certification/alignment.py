"""Final intent alignment evaluation (implementation plan phase 11, section 11.2).

Evaluates whether the observed behavioral deltas are fully covered by the
authorized intent ledger and the protected behaviors are accounted for.
This module is a **pure evaluator** — it does not create
:class:`IntentAlignment` rows, preserving ownership boundaries with the
verification and merge-gate modules.

Contracts enforced:

* ``CERTIFIABLE`` requires ``unexplained_changes == 0`` **and**
  ``critical_unauthorized_changes == 0`` (AGENTS.md sections 10/16/18).
* ``unexplained_changes`` counts behavioral deltas whose metric cannot be
  matched to any authorized intent item statement.
* ``critical_unauthorized_changes`` counts unexplained deltas whose
  category is security-relevant or whose linked behavior is protected.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from smorx_behavior.models import (
    BehavioralDelta,
    IntentAlignment,
    IntentAlignmentStatus,
    IntentItem,
    Task,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

__all__ = ["AlignmentVerdict", "evaluate_alignment"]

# Categories that are inherently security/authorization-sensitive.
_SECURITY_CATEGORIES: frozenset[str] = frozenset(
    {"SECURITY", "AUTHORIZATION", "AUTH", "IDENTITY", "PRIVACY", "INTEGRITY"}
)

# Metric substring tokens that imply security/protected relevance.
_SECURITY_TOKENS: frozenset[str] = frozenset(
    {
        "token",
        "auth",
        "tenant",
        "permission",
        "password",
        "secret",
        "signing",
        "signature",
        "rotation",
        "forged",
        "refresh",
        "session",
        "credential",
    }
)


@dataclass
class AlignmentVerdict:
    """Outcome of the final intent-alignment evaluation."""

    aligned: bool
    status: str  # CERTIFIABLE or NON_CERTIFIABLE
    unexplained_changes: int
    critical_unauthorized_changes: int
    protected_behaviors: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------


def _metric_tokens(metric: str | None) -> set[str]:
    """Return normalized lowercase word tokens with length >= 3 from ``metric``."""
    if not metric:
        return set()
    return {
        word.lower()
        for word in metric.replace("_", " ").replace("-", " ").split()
        if len(word) >= 3
    }


def _is_security_relevant(delta: BehavioralDelta, behavior_protected: bool) -> bool:
    """Return True when the delta is inherently security-sensitive."""
    category = (delta.category or "").upper()
    if category in _SECURITY_CATEGORIES:
        return True
    if behavior_protected:
        return True
    tokens = _metric_tokens(delta.metric)
    return bool(tokens & _SECURITY_TOKENS)


def _delta_explained_by_intent(
    delta: BehavioralDelta,
    intent_statements: set[str],
    metric_lower: str,
) -> bool:
    """Return True when an authorized intent statement covers the delta's metric."""
    for statement in intent_statements:
        statement_lower = statement.lower()
        if metric_lower and len(metric_lower) >= 3 and metric_lower in statement_lower:
            return True
        if metric_lower:
            for token in metric_lower.replace("_", " ").replace("-", " ").split():
                if len(token) >= 3 and token in statement_lower:
                    return True
    return False


def _is_protected_behavior_id(delta: BehavioralDelta) -> bool:
    """Return True when the delta's linked behavior appears protected."""
    if delta.behavior is None:
        return False
    return bool(delta.behavior.protected)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_alignment(
    session: Session,
    *,
    task: Task | None,
    change: Any,
    behavioral_deltas: Sequence[BehavioralDelta] | None = None,
    intent_items: Sequence[IntentItem] | None = None,
) -> AlignmentVerdict:
    """Evaluate whether the observed deltas align with authorized intent (11.2).

    When ``behavioral_deltas`` or ``intent_items`` are ``None`` they are
    queried from the database by ``task`` and ``change`` respectively.

    Returns an :class:`AlignmentVerdict` — never creates or mutates any row.
    """
    if task is None:
        return AlignmentVerdict(
            aligned=False,
            status="NON_CERTIFIABLE",
            unexplained_changes=0,
            critical_unauthorized_changes=0,
            protected_behaviors=[],
            reasons=["task is None; alignment cannot be evaluated"],
        )

    if behavioral_deltas is None:
        deltas = list(
            session.scalars(
                select(BehavioralDelta).where(
                    BehavioralDelta.task_id == task.id,
                    BehavioralDelta.observed.is_(True),
                )
            )
        )
    else:
        deltas = [d for d in behavioral_deltas if d.observed]

    if intent_items is None:
        authorized_items = list(
            session.scalars(
                select(IntentItem).where(
                    IntentItem.task_id == task.id,
                    IntentItem.authorized.is_(True),
                )
            )
        )
    else:
        authorized_items = [i for i in intent_items if i.authorized]

    intent_statements: set[str] = {item.statement for item in authorized_items if item.statement}

    # Check for existing ALIGNED intent alignment linked to this task
    aligned_exists = bool(
        session.scalar(
            select(IntentAlignment.id)
            .where(
                IntentAlignment.task_id == task.id,
                IntentAlignment.status == IntentAlignmentStatus.ALIGNED.value,
            )
            .limit(1)
        )
    )

    unexplained = 0
    critical_unauthorized = 0
    protected_ids: list[str] = []
    reasons: list[str] = []

    for delta in deltas:
        metric = (delta.metric or "").lower()
        covered = _delta_explained_by_intent(delta, intent_statements, metric)

        if not covered:
            unexplained += 1
            reasons.append(
                f"delta {delta.id} metric={delta.metric!r} not covered by any authorized intent"
            )

        is_protected = _is_protected_behavior_id(delta)
        if is_protected and delta.behavior is not None:
            protected_ids.append(str(delta.behavior_id))

        if not covered and _is_security_relevant(delta, is_protected):
            critical_unauthorized += 1
            reasons.append(
                f"delta {delta.id} metric={delta.metric!r} is security-critical and unauthorized"
            )

    if aligned_exists:
        reasons.append("existing ALIGNED intent alignment found for this task")

    aligned = unexplained == 0 and critical_unauthorized == 0
    status = "CERTIFIABLE" if aligned else "NON_CERTIFIABLE"

    return AlignmentVerdict(
        aligned=aligned,
        status=status,
        unexplained_changes=unexplained,
        critical_unauthorized_changes=critical_unauthorized,
        protected_behaviors=protected_ids,
        reasons=reasons,
    )

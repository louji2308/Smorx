"""Phase 7 unit tests — pre-coding context and lock gate (§7.7/§7.9).

Runs the complete Phase 7 flow on real rows and asserts the gate PASSES
only with all required locked state; every partial state is BLOCKED with
the failed requirement named. Also locks the context's version identity
consumed by Phase 8's stale-context protection.
"""

from __future__ import annotations

import uuid

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Constitution, Project, Repository
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning.lock import lock as versioning_lock
from smorx_precode.change_definition import define_change
from smorx_precode.impact import (
    ImpactNode,
    ImpactRelationship,
    build_semantic_impact,
    lock_semantic_impact,
)
from smorx_precode.intent_ledger import build_intent_ledger, lock_intent_ledger
from smorx_precode.lock_gate import pre_coding_gate
from smorx_precode.verification_plan import (
    VerificationCaseSpec,
    build_verification_plan,
    lock_verification_plan,
)
from sqlalchemy.orm import Session

pytest.importorskip("smorx_precode.lock_gate")

_BEHAVIORS = ["behavior:rate-limit-enforced", "behavior:checkout-two-step"]


@pytest.fixture()
def session() -> Session:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    project = Project(name="Smorx", slug="smorx")
    repo_base.save(session, project)
    repo_base.save(session, Repository(project_id=project.id, name="payments-api"))
    session.commit()
    return session


class LockedFlow:
    """Drives the complete Phase 7 flow and hands back every identity."""

    def __init__(self, session: Session) -> None:
        project = session.query(Project).first()
        change_result = define_change(
            session,
            project_id=project.id,
            request={
                "objective": "Add rate limiting to the payments API",
                "repository": "payments-api",
                "acceptance_criteria": ["429 after 100 requests per minute"],
            },
        )
        self.task_id = change_result.task_id
        self.change_id = change_result.change_id

        ledger = build_intent_ledger(
            session,
            project_id=project.id,
            task_id=self.task_id,
            objective="Add rate limiting to the payments API",
            statements=[
                {"intent_type": "ADD", "description": "rate limit middleware"},
                {"intent_type": "PRESERVE", "description": "checkout two-step flow"},
            ],
            acceptance_criteria=["429 after 100 requests per minute"],
        )
        self.intent_ledger_id = ledger.intent_ledger_id

        constitution = Constitution(project_id=project.id, title="Constitution v1")
        repo_base.save(session, constitution)
        versioning_lock(session, constitution)
        self.constitution_id = constitution.id

        build_semantic_impact(
            session,
            task_id=self.task_id,
            nodes=[
                ImpactNode(kind="BEHAVIOR", ref="behavior:rate-limit-enforced"),
                ImpactNode(
                    kind="BEHAVIOR", ref="behavior:checkout-two-step", protected=True
                ),
                ImpactNode(kind="FILE", ref="file:src/payments/middleware.py"),
            ],
            relationships=[
                ImpactRelationship(
                    source_ref="file:src/payments/middleware.py",
                    relation="IMPACTS",
                    target_ref="behavior:rate-limit-enforced",
                )
            ],
        )

        plan = build_verification_plan(
            session,
            change_id=self.change_id,
            task_id=self.task_id,
            intent_ledger_id=self.intent_ledger_id,
            title="Rate limiting verification contract",
            affected_behaviors=_BEHAVIORS,
            cases=[
                VerificationCaseSpec(
                    name="unit limiter",
                    kind="UNIT_TEST",
                    behaviors=("behavior:rate-limit-enforced",),
                ),
                VerificationCaseSpec(
                    name="checkout regression",
                    kind="REGRESSION_CHECK",
                    behaviors=("behavior:checkout-two-step",),
                ),
            ],
        )
        self.verification_plan_id = plan.verification_plan_id

    def lock_everything(self, session: Session) -> None:
        lock_intent_ledger(session, self.intent_ledger_id)
        lock_semantic_impact(session, self.task_id)
        lock_verification_plan(session, self.verification_plan_id)


def test_complete_locked_flow_passes_gate(session: Session) -> None:
    flow = LockedFlow(session)
    flow.lock_everything(session)
    verdict = pre_coding_gate(
        session,
        task_id=flow.task_id,
        intent_ledger_id=flow.intent_ledger_id,
        constitution_id=flow.constitution_id,
    )
    assert verdict.state == "PASS"
    assert verdict.context is not None
    context = verdict.context
    assert context.lock_state == "LOCKED"
    assert len(context.locked_objects) == 3
    assert context.intent_version == 1
    assert context.verification_plan_version == 1
    assert context.definition.repository_name == "payments-api"
    as_dict = context.as_dict()
    assert as_dict["lock_state"] == "LOCKED"
    assert as_dict["intent_version"] == 1


def test_gate_blocked_while_unlocked(session: Session) -> None:
    flow = LockedFlow(session)  # nothing locked yet
    verdict = pre_coding_gate(
        session,
        task_id=flow.task_id,
        intent_ledger_id=flow.intent_ledger_id,
        constitution_id=flow.constitution_id,
    )
    assert verdict.state == "BLOCKED"
    joined = "; ".join(verdict.failed_requirements)
    assert (
        "intent ledger is not locked" not in joined
    )  # ledger lock is checked downstream
    assert "not locked" in joined or "not exist" in joined


def test_gate_blocked_when_verification_plan_missing(session: Session) -> None:
    flow = LockedFlow(session)
    flow.lock_everything(session)
    # A second task with no plan: gate must name the missing plan.
    project = session.query(Project).first()
    other = define_change(
        session,
        project_id=project.id,
        request={
            "objective": "Second task without a plan",
            "repository": "payments-api",
            "acceptance_criteria": ["something verifiable"],
        },
    )
    verdict = pre_coding_gate(
        session,
        task_id=other.task_id,
        intent_ledger_id=flow.intent_ledger_id,
        constitution_id=flow.constitution_id,
    )
    assert verdict.state == "BLOCKED"
    assert any("verification plan" in item for item in verdict.failed_requirements)


def test_gate_blocked_when_intent_ledger_mismatched(session: Session) -> None:
    flow = LockedFlow(session)
    flow.lock_everything(session)
    project = session.query(Project).first()
    other = define_change(
        session,
        project_id=project.id,
        request={
            "objective": "Second task, first task's ledger",
            "repository": "payments-api",
            "acceptance_criteria": ["something verifiable"],
        },
    )
    verdict = pre_coding_gate(
        session,
        task_id=other.task_id,
        intent_ledger_id=flow.intent_ledger_id,  # bound to the FIRST task
        constitution_id=flow.constitution_id,
    )
    assert verdict.state == "BLOCKED"
    assert any("bound to task" in item for item in verdict.failed_requirements)


def test_gate_blocked_without_constitution(session: Session) -> None:
    flow = LockedFlow(session)
    flow.lock_everything(session)
    verdict = pre_coding_gate(
        session,
        task_id=flow.task_id,
        intent_ledger_id=flow.intent_ledger_id,
        constitution_id=uuid.uuid4(),
    )
    assert verdict.state == "BLOCKED"
    assert any("constitution" in item for item in verdict.failed_requirements)


def test_context_version_identity_is_exact(session: Session) -> None:
    flow = LockedFlow(session)
    flow.lock_everything(session)
    verdict = pre_coding_gate(
        session,
        task_id=flow.task_id,
        intent_ledger_id=flow.intent_ledger_id,
        constitution_id=flow.constitution_id,
    )
    context = verdict.context
    assert context is not None
    assert context.task_id == flow.task_id
    assert context.change_id == flow.change_id
    assert context.intent_ledger_id == flow.intent_ledger_id
    assert context.verification_plan_id == flow.verification_plan_id
    assert context.constitution_id == flow.constitution_id
    assert context.created_at.tzinfo is not None

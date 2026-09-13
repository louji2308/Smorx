"""Phase 7 adversarial tests — master prompt §12 scenarios touching Phase 7.

Scenario coverage here:
- 1  incomplete human request -> rejected;
- 2  ambiguous intent -> rejected;
- 3  conflicting constitutional constraint -> surfaced as conflict + risk note;
- 4  locked intent mutation -> blocked (I9);
- 5  locked verification-plan mutation -> blocked (I9);
- 12 build-failure style invalid pre-coding context -> gate BLOCKED.

The gate's job is to make scenario 20 (Coding Agent requested before the
Phase 7 lock) impossible; the Phase 8 barrier suite proves that end to end.
"""

from __future__ import annotations

import uuid

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import (
    Constitution,
    ConstitutionClaim,
    Project,
    Repository,
    VerificationCase,
)
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning import VersionLockedError, assert_not_locked
from smorx_precode.change_definition import TaskDefinitionError, define_change
from smorx_precode.intent_compiler import AmbiguityError, compile_intent
from smorx_precode.intent_ledger import (
    ConstitutionMapperError,
    build_intent_ledger,
    lock_intent_ledger,
    resolve_constraints,
)
from smorx_precode.verification_plan import (
    VerificationCaseSpec,
    build_verification_plan,
    lock_verification_plan,
)
from sqlalchemy.orm import Session

pytest.importorskip("smorx_precode.intent_ledger")


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


def _change(session: Session, objective: str = "Add rate limiting to the payments API"):
    project = session.query(Project).first()
    return define_change(
        session,
        project_id=project.id,
        request={
            "objective": objective,
            "repository": "payments-api",
            "acceptance_criteria": ["429 after 100 requests per minute"],
        },
    )


def test_scenario_1_incomplete_human_request_rejected(session: Session) -> None:
    with pytest.raises(TaskDefinitionError) as excinfo:
        define_change(
            session,
            project_id=session.query(Project).first().id,
            request={"objective": "make it better"},  # no repository, no criteria
        )
    assert set(excinfo.value.missing) >= {"repository", "acceptance_criteria"}


def test_scenario_2_ambiguous_intent_rejected() -> None:
    with pytest.raises(AmbiguityError):
        compile_intent(
            objective="Fix the payments flow somehow",
            statements=[
                {"intent_type": "ADD", "description": "handle errors as needed"}
            ],
        )


def test_scenario_3_conflicting_constitutional_constraint_surfaced(
    session: Session,
) -> None:
    change = _change(session)
    project = session.query(Project).first()
    ledger = build_intent_ledger(
        session,
        project_id=project.id,
        task_id=change.task_id,
        objective="Add rate limiting to the payments API",
        statements=[
            {"intent_type": "REPLACE", "description": "replace the auth token cache"},
        ],
        acceptance_criteria=["429 after 100 requests per minute"],
    )
    constitution = Constitution(project_id=project.id, title="C1")
    repo_base.save(session, constitution)
    repo_base.save(
        session,
        ConstitutionClaim(
            constitution_id=constitution.id,
            category="SECURITY",
            rule="auth token cache must be audited before replacement",
            severity="CRITICAL",
        ),
    )
    from smorx_behavior.versioning.lock import lock as versioning_lock

    versioning_lock(session, constitution)
    resolution = resolve_constraints(
        session,
        intent_ledger_id=ledger.intent_ledger_id,
        constitution_id=constitution.id,
    )
    assert resolution.conflicting_claim_ids, "REPLACE vs protected claim must conflict"
    assert any("explicit human authorization" in note for note in resolution.risk_notes)


def test_scenario_4_locked_intent_mutation_blocked(session: Session) -> None:
    change = _change(session)
    project = session.query(Project).first()
    ledger = build_intent_ledger(
        session,
        project_id=project.id,
        task_id=change.task_id,
        objective="Add rate limiting",
        statements=[{"intent_type": "ADD", "description": "rate limit middleware"}],
        acceptance_criteria=["429 after 100 rpm"],
    )
    lock_intent_ledger(session, ledger.intent_ledger_id)
    from smorx_behavior.models import IntentLedger

    row = repo_base.get(session, IntentLedger, ledger.intent_ledger_id)
    with pytest.raises(VersionLockedError):
        assert_not_locked(row)  # any ORM-level mutation path is guarded


def test_scenario_5_locked_verification_plan_mutation_blocked(session: Session) -> None:
    change = _change(session)
    plan = build_verification_plan(
        session,
        change_id=change.change_id,
        task_id=change.task_id,
        intent_ledger_id=None,
        title="contract",
        affected_behaviors=["behavior:rate-limit"],
        cases=[
            VerificationCaseSpec(
                name="c1", kind="UNIT_TEST", behaviors=("behavior:rate-limit",)
            )
        ],
    )
    lock_verification_plan(session, plan.verification_plan_id)
    from smorx_behavior.models import VerificationPlan

    row = repo_base.get(session, VerificationPlan, plan.verification_plan_id)
    with pytest.raises(VersionLockedError):
        assert_not_locked(row)
    case_rows = repo_base.list_(session, VerificationCase, verification_plan_id=row.id)
    for case_row in case_rows:
        with pytest.raises(VersionLockedError):
            assert_not_locked(case_row)


def test_scenario_12_invalid_preceding_context_rejected(session: Session) -> None:
    """A ledger for a task with no impact map/plan cannot resolve cleanly."""
    change = _change(session)
    project = session.query(Project).first()
    ledger = build_intent_ledger(
        session,
        project_id=project.id,
        task_id=change.task_id,
        objective="Add rate limiting",
        statements=[{"intent_type": "ADD", "description": "middleware"}],
        acceptance_criteria=["429"],
    )
    # No constitution exists at all.
    with pytest.raises(ConstitutionMapperError):
        resolve_constraints(
            session,
            intent_ledger_id=ledger.intent_ledger_id,
            constitution_id=uuid.uuid4(),
        )


def test_empty_statement_ledger_rejected(session: Session) -> None:
    change = _change(session)
    project = session.query(Project).first()
    with pytest.raises(Exception):  # noqa: B017 - IntentCompilerError by contract
        build_intent_ledger(
            session,
            project_id=project.id,
            task_id=change.task_id,
            objective="Add rate limiting",
            statements=[{"intent_type": "ADD", "description": "  "}],
            acceptance_criteria=["429"],
        )

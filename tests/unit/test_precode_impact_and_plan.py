"""Phase 7 unit tests — semantic impact map (§7.5) and verification plan (§7.6/§7.7).

Impact covers: structured nodes/relationships validation; rejection of a
bare file list without behaviors; unknown kinds/relations/endpoints
rejected; lock permanence. Plan covers: bidirectional coverage validation
(every case maps to a behavior, every behavior is covered); duplicate and
unknown-kind rejection; plan+case lock; plan view round trip.
"""

from __future__ import annotations

import uuid

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Project, Repository
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning import VersionLockedError, assert_not_locked
from smorx_precode.change_definition import define_change
from smorx_precode.impact import (
    ImpactNode,
    ImpactRelationship,
    SemanticImpactError,
    build_semantic_impact,
    get_semantic_impact,
    lock_semantic_impact,
)
from smorx_precode.verification_plan import (
    VerificationCaseSpec,
    VerificationPlanError,
    build_verification_plan,
    get_verification_plan,
    lock_verification_plan,
)
from sqlalchemy.orm import Session

pytest.importorskip("smorx_precode.impact")


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


def _task_id(session: Session) -> uuid.UUID:
    project = session.query(Project).first()
    result = define_change(
        session,
        project_id=project.id,
        request={
            "objective": "Add rate limiting to the payments API",
            "repository": "payments-api",
            "acceptance_criteria": ["429 after 100 requests per minute"],
        },
    )
    return result.task_id


_NODES = [
    ImpactNode(kind="BEHAVIOR", ref="behavior:rate-limit-enforced"),
    ImpactNode(kind="BEHAVIOR", ref="behavior:checkout-two-step", protected=True),
    ImpactNode(kind="COMPONENT", ref="component:payments.middleware"),
    ImpactNode(kind="FILE", ref="file:src/payments/middleware.py"),
    ImpactNode(kind="GHOST", ref="ghost:221", note="historical auth failure"),
]
_RELS = [
    ImpactRelationship(
        source_ref="component:payments.middleware",
        relation="IMPACTS",
        target_ref="behavior:rate-limit-enforced",
        rationale="middleware enforces the limiter",
    ),
    ImpactRelationship(
        source_ref="behavior:rate-limit-enforced",
        relation="HISTORY_FOR",
        target_ref="ghost:221",
        rationale="same request path as failure F-183",
    ),
]


class TestSemanticImpact:
    def test_build_and_round_trip(self, session: Session) -> None:
        task_id = _task_id(session)
        built = build_semantic_impact(
            session, task_id=task_id, nodes=list(_NODES), relationships=list(_RELS)
        )
        assert built.impacted_refs({"BEHAVIOR"}) == (
            "behavior:rate-limit-enforced",
            "behavior:checkout-two-step",
        )
        assert built.protected_refs() == ("behavior:checkout-two-step",)

        view = get_semantic_impact(session, task_id)
        assert view.semantic_impact_id == built.semantic_impact_id
        assert len(view.nodes) == 5
        assert len(view.relationships) == 2

    def test_bare_file_list_rejected(self, session: Session) -> None:
        task_id = _task_id(session)
        with pytest.raises(SemanticImpactError) as excinfo:
            build_semantic_impact(
                session,
                task_id=task_id,
                nodes=[
                    ImpactNode(kind="FILE", ref="a.py"),
                    ImpactNode(kind="FILE", ref="b.py"),
                ],
                relationships=[],
            )
        assert "not an impact map" in str(excinfo.value)

    def test_unknown_kind_and_duplicate_rejected(self, session: Session) -> None:
        task_id = _task_id(session)
        with pytest.raises(SemanticImpactError):
            build_semantic_impact(
                session,
                task_id=task_id,
                nodes=[ImpactNode(kind="MODULE", ref="x")],
                relationships=[],
            )
        with pytest.raises(SemanticImpactError):
            build_semantic_impact(
                session,
                task_id=task_id,
                nodes=[
                    ImpactNode(kind="BEHAVIOR", ref="b1"),
                    ImpactNode(kind="BEHAVIOR", ref="b1"),
                ],
                relationships=[],
            )

    def test_relationship_to_unknown_node_rejected(self, session: Session) -> None:
        task_id = _task_id(session)
        with pytest.raises(SemanticImpactError) as excinfo:
            build_semantic_impact(
                session,
                task_id=task_id,
                nodes=[ImpactNode(kind="BEHAVIOR", ref="b1")],
                relationships=[
                    ImpactRelationship(
                        source_ref="b1", relation="IMPACTS", target_ref="ghost:999"
                    )
                ],
            )
        assert "unknown node" in str(excinfo.value)

    def test_lock_is_permanent(self, session: Session) -> None:
        task_id = _task_id(session)
        build_semantic_impact(
            session, task_id=task_id, nodes=list(_NODES), relationships=list(_RELS)
        )
        locked = lock_semantic_impact(session, task_id)
        assert locked.locked is True
        assert locked.status == "LOCKED"
        from smorx_behavior.models import SemanticImpact

        row = repo_base.get(session, SemanticImpact, locked.semantic_impact_id)
        with pytest.raises(VersionLockedError):
            assert_not_locked(row)
        again = lock_semantic_impact(session, task_id)
        assert again.version == locked.version

    def test_missing_map_raises(self, session: Session) -> None:
        with pytest.raises(SemanticImpactError):
            get_semantic_impact(session, uuid.uuid4())


class TestVerificationPlan:
    def _cases(self) -> list[VerificationCaseSpec]:
        return [
            VerificationCaseSpec(
                name="unit limiter math",
                kind="UNIT_TEST",
                behaviors=("behavior:rate-limit-enforced",),
                method="pytest tests/unit/test_limiter.py",
            ),
            VerificationCaseSpec(
                name="checkout regression",
                kind="REGRESSION_CHECK",
                behaviors=("behavior:checkout-two-step",),
                method="pytest tests/integration/test_checkout.py",
            ),
            VerificationCaseSpec(
                name="ghost replay 221",
                kind="BEHAVIORAL_CHECK",
                behaviors=(
                    "behavior:rate-limit-enforced",
                    "behavior:checkout-two-step",
                ),
            ),
        ]

    def test_build_and_round_trip(self, session: Session) -> None:
        task_id = _task_id(session)
        from smorx_behavior.models import Change

        change = session.query(Change).first()
        built = build_verification_plan(
            session,
            change_id=change.id,
            task_id=task_id,
            intent_ledger_id=None,
            title="Rate limiting verification contract",
            affected_behaviors=[
                "behavior:rate-limit-enforced",
                "behavior:checkout-two-step",
            ],
            cases=self._cases(),
        )
        assert built.locked is False
        assert built.coverage["behavior:rate-limit-enforced"] == (
            "unit limiter math",
            "ghost replay 221",
        )
        view = get_verification_plan(session, built.verification_plan_id)
        assert len(view.cases) == 3

    def test_uncovered_behavior_rejected(self, session: Session) -> None:
        task_id = _task_id(session)
        from smorx_behavior.models import Change

        change = session.query(Change).first()
        with pytest.raises(VerificationPlanError) as excinfo:
            build_verification_plan(
                session,
                change_id=change.id,
                task_id=task_id,
                intent_ledger_id=None,
                title="incomplete",
                affected_behaviors=[
                    "behavior:rate-limit-enforced",
                    "behavior:uncovered",
                ],
                cases=[
                    VerificationCaseSpec(
                        name="only one",
                        kind="UNIT_TEST",
                        behaviors=("behavior:rate-limit-enforced",),
                    )
                ],
            )
        assert "uncovered" in str(excinfo.value)

    def test_case_targeting_unknown_behavior_rejected(self, session: Session) -> None:
        from smorx_behavior.models import Change

        _task_id(session)
        change = session.query(Change).first()
        with pytest.raises(VerificationPlanError) as excinfo:
            build_verification_plan(
                session,
                change_id=change.id,
                task_id=_task_id(session),
                intent_ledger_id=None,
                title="wrong target",
                affected_behaviors=["behavior:rate-limit-enforced"],
                cases=[
                    VerificationCaseSpec(
                        name="c1", kind="UNIT_TEST", behaviors=("behavior:elsewhere",)
                    )
                ],
            )
        assert "outside the impact map" in str(excinfo.value)

    def test_duplicate_names_and_unknown_kinds_rejected(self, session: Session) -> None:
        from smorx_behavior.models import Change

        _task_id(session)
        change = session.query(Change).first()
        assert change is not None
        base_kwargs = {
            "change_id": change.id,
            "task_id": _task_id(session),
            "intent_ledger_id": None,
            "affected_behaviors": ["behavior:rate-limit-enforced"],
        }
        with pytest.raises(VerificationPlanError):
            build_verification_plan(
                session,
                title="dup",
                cases=[
                    VerificationCaseSpec(
                        name="c1",
                        kind="UNIT_TEST",
                        behaviors=("behavior:rate-limit-enforced",),
                    ),
                    VerificationCaseSpec(
                        name="c1",
                        kind="UNIT_TEST",
                        behaviors=("behavior:rate-limit-enforced",),
                    ),
                ],
                **base_kwargs,
            )
        with pytest.raises(VerificationPlanError):
            build_verification_plan(
                session,
                title="bad kind",
                cases=[
                    VerificationCaseSpec(
                        name="c1",
                        kind="VIBES",
                        behaviors=("behavior:rate-limit-enforced",),
                    )
                ],
                **base_kwargs,
            )

    def test_lock_covers_plan_and_cases(self, session: Session) -> None:
        from smorx_behavior.models import Change, VerificationCase, VerificationPlan

        _task_id(session)
        change = session.query(Change).first()
        built = build_verification_plan(
            session,
            change_id=change.id,
            task_id=_task_id(session),
            intent_ledger_id=None,
            title="lock me",
            affected_behaviors=["behavior:rate-limit-enforced"],
            cases=[
                VerificationCaseSpec(
                    name="c1",
                    kind="UNIT_TEST",
                    behaviors=("behavior:rate-limit-enforced",),
                )
            ],
        )
        locked = lock_verification_plan(session, built.verification_plan_id)
        assert locked.locked is True
        assert locked.status == "LOCKED"
        plan_row = repo_base.get(session, VerificationPlan, built.verification_plan_id)
        with pytest.raises(VersionLockedError):
            assert_not_locked(plan_row)
        case_rows = repo_base.list_(
            session, VerificationCase, verification_plan_id=plan_row.id
        )
        assert case_rows and all(row.locked for row in case_rows)

    def test_unknown_plan_raises(self, session: Session) -> None:
        with pytest.raises(VerificationPlanError):
            get_verification_plan(session, uuid.uuid4())

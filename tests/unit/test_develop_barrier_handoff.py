"""Phase 8 unit tests — handoff (§8.1) and execution barrier (§8.2).

Covers: handoff of a real locked PASS context; rejection of BLOCKED
contexts, non-context objects, and stale contexts (version moved);
barrier BLOCK on unauthorized execution; barrier PASS on the full locked
state with explicit authorization; and master-prompt §12 scenario 20 —
the Coding Agent requested before the Phase 7 lock MUST be rejected.
"""

from __future__ import annotations

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Project, Repository
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning.lock import lock as versioning_lock
from smorx_develop.agent import CodingAgentLoop
from smorx_develop.barrier import BarrierError, ExecutionBarrier
from smorx_develop.bounds import LoopBounds
from smorx_develop.handoff import HandoffError, pre_coding_handoff
from smorx_precode.change_definition import define_change
from smorx_precode.impact import (
    ImpactNode,
    build_semantic_impact,
    lock_semantic_impact,
)
from smorx_precode.intent_ledger import (
    build_intent_ledger,
    bump_intent_ledger,
    lock_intent_ledger,
)
from smorx_precode.lock_gate import pre_coding_gate
from smorx_precode.verification_plan import (
    VerificationCaseSpec,
    build_verification_plan,
    lock_verification_plan,
)
from sqlalchemy.orm import Session

pytest.importorskip("smorx_develop.barrier")


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


from smorx_behavior.models import Constitution


def _locked_pass_context(session: Session):
    project = session.query(Project).first()
    change = define_change(
        session,
        project_id=project.id,
        request={
            "objective": "Add rate limiting to the payments API",
            "repository": "payments-api",
            "acceptance_criteria": ["429 after 100 requests per minute"],
        },
    )
    ledger = build_intent_ledger(
        session,
        project_id=project.id,
        task_id=change.task_id,
        objective="Add rate limiting",
        statements=[{"intent_type": "ADD", "description": "rate limit middleware"}],
        acceptance_criteria=["429 after 100 requests per minute"],
    )
    constitution = Constitution(project_id=project.id, title="C1")
    repo_base.save(session, constitution)
    versioning_lock(session, constitution)
    build_semantic_impact(
        session,
        task_id=change.task_id,
        nodes=[ImpactNode(kind="BEHAVIOR", ref="behavior:rate-limit")],
        relationships=[],
    )
    plan = build_verification_plan(
        session,
        change_id=change.change_id,
        task_id=change.task_id,
        intent_ledger_id=ledger.intent_ledger_id,
        title="contract",
        affected_behaviors=["behavior:rate-limit"],
        cases=[
            VerificationCaseSpec(
                name="c1", kind="UNIT_TEST", behaviors=("behavior:rate-limit",)
            )
        ],
    )
    lock_intent_ledger(session, ledger.intent_ledger_id)
    lock_semantic_impact(session, change.task_id)
    lock_verification_plan(session, plan.verification_plan_id)
    verdict = pre_coding_gate(
        session,
        task_id=change.task_id,
        intent_ledger_id=ledger.intent_ledger_id,
        constitution_id=constitution.id,
    )
    assert verdict.state == "PASS", verdict.failed_requirements
    return verdict.context


def test_handoff_accepts_exact_locked_context(session: Session) -> None:
    context = _locked_pass_context(session)
    record = pre_coding_handoff(session, context=context)
    assert record.context_id == context.context_id
    assert record.intent_version == context.intent_version
    assert record.verification_plan_version == context.verification_plan_version
    assert record.lock_state == "LOCKED"


def test_handoff_rejects_non_context_object(session: Session) -> None:
    with pytest.raises(HandoffError) as excinfo:
        pre_coding_handoff(session, context={"lock_state": "LOCKED"})  # type: ignore[arg-type]
    assert "no manual reconstruction" in str(excinfo.value)


def test_handoff_rejects_stale_context_after_version_bump(session: Session) -> None:
    context = _locked_pass_context(session)
    bump_intent_ledger(session, context.intent_ledger_id, note="intent v2")
    with pytest.raises(HandoffError) as excinfo:
        pre_coding_handoff(session, context=context)
    # The bumped (locked) row keeps its identity, so staleness is detected
    # via supersession: a successor version exists in the lineage.
    assert "stale context" in str(excinfo.value)
    assert "superseded" in str(excinfo.value)


def test_barrier_blocks_without_authorization(session: Session) -> None:
    context = _locked_pass_context(session)
    barrier = ExecutionBarrier(session=session)
    verdict = barrier.evaluate(context=context, authorized=False)
    assert verdict.state == "BLOCKED"
    assert any("not authorized" in item for item in verdict.failed_conditions)


def test_barrier_passes_with_locked_context_and_authorization(session: Session) -> None:
    context = _locked_pass_context(session)
    barrier = ExecutionBarrier(session=session)
    verdict = barrier.evaluate(context=context, authorized=True)
    assert verdict.state == "PASS", verdict.failed_conditions
    record = barrier.require_pass(context=context, authorized=True)
    # Each evaluation mints its own handoff record; identity is the context.
    assert record.context_id == verdict.handoff.context_id


def test_require_pass_raises_barrier_error_on_blocked(session: Session) -> None:
    context = _locked_pass_context(session)
    # Invalidate: bump the plan so the context is stale -> handoff fails.
    from smorx_behavior.models import VerificationPlan
    from smorx_behavior.versioning.service import bump

    plan_row = repo_base.get(session, VerificationPlan, context.verification_plan_id)
    assert plan_row is not None
    row = bump(session, plan_row, note="plan v2")
    row.locked = False  # a re-opened (unlocked) plan must also block
    session.flush()
    barrier = ExecutionBarrier(session=session)
    with pytest.raises(BarrierError) as excinfo:
        barrier.require_pass(context=context, authorized=True)
    assert "BLOCKED" in str(excinfo.value)


def test_scenario_20_coding_agent_before_lock_rejected(session: Session) -> None:
    """§12 case 20: the loop MUST refuse to act without the Phase 7 lock."""
    # Build the pre-coding objects but DO NOT lock them.
    project = session.query(Project).first()
    change = define_change(
        session,
        project_id=project.id,
        request={
            "objective": "Add rate limiting to the payments API",
            "repository": "payments-api",
            "acceptance_criteria": ["429 after 100 requests per minute"],
        },
    )
    ledger = build_intent_ledger(
        session,
        project_id=project.id,
        task_id=change.task_id,
        objective="Add rate limiting",
        statements=[{"intent_type": "ADD", "description": "rate limit middleware"}],
        acceptance_criteria=["429 after 100 requests per minute"],
    )
    build_semantic_impact(
        session,
        task_id=change.task_id,
        nodes=[ImpactNode(kind="BEHAVIOR", ref="behavior:rate-limit")],
        relationships=[],
    )
    build_verification_plan(
        session,
        change_id=change.change_id,
        task_id=change.task_id,
        intent_ledger_id=ledger.intent_ledger_id,
        title="contract",
        affected_behaviors=["behavior:rate-limit"],
        cases=[
            VerificationCaseSpec(
                name="c1", kind="UNIT_TEST", behaviors=("behavior:rate-limit",)
            )
        ],
    )
    verdict = pre_coding_gate(
        session,
        task_id=change.task_id,
        intent_ledger_id=ledger.intent_ledger_id,
        constitution_id=None,  # type: ignore[arg-type]
    )
    assert verdict.state == "BLOCKED"
    context = verdict.context
    # With the constitution missing the gate cannot even assemble a
    # context; the barrier must still refuse execution below.
    if context is not None:
        assert context.lock_state == "BLOCKED"

    # The coding loop must refuse: barrier BLOCKED -> POLICY_STOP, no work.
    import asyncio
    import tempfile

    from smorx_develop.sandbox import DevelopmentSandbox

    async def _scenario() -> None:
        with tempfile.TemporaryDirectory() as source:
            sandbox = await DevelopmentSandbox.create(source_root=source)
            loop = CodingAgentLoop(sandbox=sandbox, bounds=LoopBounds(max_iterations=2))
            from smorx_develop.plan import build_development_plan

            dev_plan = build_development_plan(
                interpretation="i",
                affected_components=["c"],
                affected_files=["src.py"],
                implementation_strategy="s",
                tests_to_run=[
                    f'"{__import__("sys").executable.replace(__import__("os").sep, "/")}" -c "print(1)"'
                ],
                completion_criteria=["done"],
            )

            async def decider(view):  # pragma: no cover - must never be called
                raise AssertionError("decider must not run before the lock")

            barrier = ExecutionBarrier(session=session)
            result = await loop.run(
                plan=dev_plan,
                context=context,
                barrier=barrier,
                authorized=True,  # even authorized, the lock state blocks
                decider=decider,
            )
            assert result.final_state == "BLOCKED"
            assert result.termination.kind == "POLICY_STOP"
            assert "BLOCKED" in result.termination.detail
            assert result.executions == ()  # nothing executed
            assert result.mutations == ()  # nothing mutated
            await sandbox.destroy()

    asyncio.run(_scenario())

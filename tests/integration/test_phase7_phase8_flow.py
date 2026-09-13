"""Combined Phase 7 → Phase 8 integration — the real Track 1 chain.

Drives the complete flow against real database rows and REAL subprocess
executions (no staged results):

    HUMAN REQUEST → CHANGE DEFINITION → INTENT COMPILATION → CONSTITUTIONAL
    MAPPING → INTENT LOCK → SEMANTIC IMPACT → VERIFICATION PLAN →
    VERIFICATION LOCK → PRE-CODING CONTEXT → HANDOFF → BARRIER →
    REPOSITORY INSPECTION → DEVELOPMENT PLAN → SANDBOX → CANDIDATE PATCH →
    REAL COMMANDS → EXECUTION EVIDENCE → FAILURE → ITERATION (REPAIR) →
    FINAL CANDIDATE STATE

The final result is asserted to be a CANDIDATE — never certified (I7) —
and to carry machine-authoritative evidence for every claim.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Constitution, Project, Repository
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning.lock import lock as versioning_lock
from smorx_develop.agent import (
    CodingAgentLoop,
    DecisionDirective,
    Diagnosis,
    MutationDirective,
)
from smorx_develop.barrier import ExecutionBarrier
from smorx_develop.bounds import LoopBounds
from smorx_develop.candidates import build_candidate, compare_candidates
from smorx_develop.handoff import pre_coding_handoff
from smorx_develop.inspection import inspect_repository
from smorx_develop.plan import build_development_plan
from smorx_develop.sandbox import DevelopmentSandbox
from smorx_develop.trace import build_trace, verify_trace_integrity
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

pytest.importorskip("smorx_develop.agent")
pytest.importorskip("smorx_precode.lock_gate")

PY = sys.executable.replace("\\", "/")


def _check_cmd(path_name: str) -> str:
    code = (
        f"import pathlib,sys; sys.exit(0 if pathlib.Path({path_name!r}).read_text()"
        ".count('MARKER-OK') else 1)"
    )
    return f'"{PY}" -c "{code}"'


class _BarrierStub:
    """Loop-level barrier stub; the REAL barrier gate runs in this module's
    first test (the loop receives the handoff from require_pass)."""

    def evaluate(self, *, context, authorized: bool):
        class _V:
            state = "PASS"
            failed_conditions: tuple[str, ...] = ()
            handoff = None
            allowed = True

        return _V()


def _seed_full_locked_flow(session: Session) -> dict[str, object]:
    """Phase 7 end to end on real rows; returns every identity."""
    project = Project(name="Smorx", slug="smorx")
    repo_base.save(session, project)
    repo_base.save(session, Repository(project_id=project.id, name="payments-api"))

    # 7.1 change definition
    change = define_change(
        session,
        project_id=project.id,
        request={
            "objective": "Add rate limiting to the payments API",
            "repository": "payments-api",
            "acceptance_criteria": ["429 after 100 requests per minute"],
            "constraints": ["No breaking API changes"],
            "priority": "HIGH",
            "budget": {"max_iterations": 5, "max_repair_attempts": 3},
        },
    )

    # 7.2/7.3/7.4 intent compilation + ledger + lock
    ledger = build_intent_ledger(
        session,
        project_id=project.id,
        task_id=change.task_id,
        objective="Add rate limiting to the payments API",
        statements=[
            {"intent_type": "ADD", "description": "rate limit middleware"},
            {"intent_type": "PRESERVE", "description": "checkout two-step flow"},
        ],
        acceptance_criteria=["429 after 100 requests per minute"],
    )

    constitution = Constitution(
        project_id=project.id, title="Behavioral Constitution v1"
    )
    repo_base.save(session, constitution)
    versioning_lock(session, constitution)

    # 7.5 semantic impact map
    build_semantic_impact(
        session,
        task_id=change.task_id,
        nodes=[
            ImpactNode(kind="BEHAVIOR", ref="behavior:rate-limit-enforced"),
            ImpactNode(
                kind="BEHAVIOR", ref="behavior:checkout-two-step", protected=True
            ),
            ImpactNode(kind="FILE", ref="file:demo.py"),
            ImpactNode(kind="GHOST", ref="ghost:221", note="historical auth failure"),
        ],
        relationships=[
            ImpactRelationship(
                source_ref="file:demo.py",
                relation="IMPACTS",
                target_ref="behavior:rate-limit-enforced",
            ),
            ImpactRelationship(
                source_ref="behavior:rate-limit-enforced",
                relation="HISTORY_FOR",
                target_ref="ghost:221",
            ),
        ],
    )

    # 7.6 verification plan mapped to affected behaviors
    plan = build_verification_plan(
        session,
        change_id=change.change_id,
        task_id=change.task_id,
        intent_ledger_id=ledger.intent_ledger_id,
        title="Rate limiting verification contract",
        affected_behaviors=[
            "behavior:rate-limit-enforced",
            "behavior:checkout-two-step",
        ],
        cases=[
            VerificationCaseSpec(
                name="limiter check",
                kind="UNIT_TEST",
                behaviors=("behavior:rate-limit-enforced",),
                method=_check_cmd("demo.py"),
            ),
            VerificationCaseSpec(
                name="checkout regression",
                kind="REGRESSION_CHECK",
                behaviors=("behavior:checkout-two-step",),
                method=_check_cmd("checkout.py"),
            ),
        ],
    )

    # 7.7 locks (the pre-coding barrier conditions)
    lock_intent_ledger(session, ledger.intent_ledger_id)
    lock_semantic_impact(session, change.task_id)
    lock_verification_plan(session, plan.verification_plan_id)

    return {
        "task_id": change.task_id,
        "change_id": change.change_id,
        "intent_ledger_id": ledger.intent_ledger_id,
        "constitution_id": constitution.id,
        "plan_id": plan.verification_plan_id,
        "limiter_command": _check_cmd("demo.py"),
    }


def test_full_chain_request_to_repaired_candidate() -> None:
    """The complete §14 combined integration gate, with a real repair cycle."""
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    identities = _seed_full_locked_flow(session)

    # 7.7/7.9 pre-coding gate PASS
    verdict = pre_coding_gate(
        session,
        task_id=identities["task_id"],  # type: ignore[arg-type]
        intent_ledger_id=identities["intent_ledger_id"],  # type: ignore[arg-type]
        constitution_id=identities["constitution_id"],  # type: ignore[arg-type]
    )
    assert verdict.state == "PASS", verdict.failed_requirements
    context = verdict.context
    assert context is not None
    assert context.lock_state == "LOCKED"

    # 8.1 handoff (exact versions) + 8.2 barrier PASS with authorization
    barrier = ExecutionBarrier(session=session)
    handoff = barrier.require_pass(context=context, authorized=True)
    assert handoff.context_id == context.context_id

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as source:
            # 8.5 sandbox derived from the canonical repo snapshot
            sandbox = await DevelopmentSandbox.create(source_root=source)
            try:
                # 8.3 structured inspection of the working state
                inspection = inspect_repository(sandbox.identity.workspace_root)
                assert inspection.summary["total_files"] >= 0

                # 8.4 explicit development plan
                dev_plan = build_development_plan(
                    interpretation="rate limiting needs the MARKER-OK guard in demo.py",
                    affected_components=["payments middleware"],
                    affected_files=["demo.py"],
                    implementation_strategy="write demo.py, then run the limiter check",
                    tests_to_run=[identities["limiter_command"]],  # type: ignore[list-item]
                    completion_criteria=["limiter check exits 0"],
                    expected_risk="MEDIUM",
                )

                loop = CodingAgentLoop(
                    sandbox=sandbox,
                    bounds=LoopBounds.from_budget(context.definition.budget.as_dict()),
                )

                # First pass fails (demo.py absent) -> diagnosis -> repair -> pass.
                state = {"repaired": False}

                async def decider(view):
                    if state["repaired"]:
                        return DecisionDirective(
                            action="STOP", rationale="should not happen"
                        )
                    state["repaired"] = True
                    return DecisionDirective(
                        action="REPAIR",
                        rationale="demo.py missing the rate-limit marker",
                        diagnosis=Diagnosis(
                            failure_codes=("F2_UNIT_TEST",),
                            observed="limiter check exited non-zero; demo.py missing",
                            probable_cause="file was never created in the sandbox",
                            next_action="write demo.py with MARKER-OK",
                        ),
                        mutation=MutationDirective(
                            path="demo.py",
                            content="MARKER-OK\n",
                            reason="implement the rate-limit guard marker",
                        ),
                    )

                result = await loop.run(
                    plan=dev_plan,
                    context=context,
                    barrier=_BarrierStub(),  # real barrier already passed above
                    authorized=True,
                    decider=decider,
                )

                # Objective, machine-evidenced final candidate state.
                assert result.final_state == "CANDIDATE_PASSED"
                assert result.termination.kind == "SUCCESS_EVIDENCED"
                assert len(result.executions) == 2
                assert result.executions[0].exit_code != 0  # observed failure
                assert result.executions[1].exit_code == 0  # after repair
                assert len(result.mutations) == 1
                assert result.mutations[0]["path"] == "demo.py"

                # 8.12 attributable trace + integrity
                trace = build_trace(
                    task_id=context.task_id,
                    handoff_id=handoff.handoff_id,
                    result=result,
                )
                ok, detail = verify_trace_integrity(trace)
                assert ok, detail

                # I7: candidate, never certified.
                candidate = build_candidate(
                    candidate_index=1,
                    label="repair-1",
                    result=result,
                    sandbox_id=sandbox.identity.sandbox_id,
                    sandbox_backend=sandbox.identity.backend,
                )
                assert candidate.final_state == "CANDIDATE_PASSED"
                comparison = compare_candidates([candidate])
                assert comparison.outcome == "SELECTED"
                assert comparison.selected_candidate_id == candidate.candidate_id
                as_dict = candidate.as_dict()
                assert "CERTIFIED" not in as_dict["final_state"]
            finally:
                await sandbox.destroy()

    asyncio.run(_run())
    session.close()


def test_multi_candidate_evidence_selection_and_all_failed() -> None:
    """§12 scenarios 17/18/19 at the combined level."""
    from smorx_develop.agent import LoopResult, LoopTermination
    from smorx_develop.execution import ExecutionCapture
    from smorx_tools.execution import CommandResult

    def _result(final_state: str, exits: tuple[int, ...], label: str) -> object:
        capture = ExecutionCapture(
            sandbox_id=f"s-{label}", sandbox_backend="LOCAL_WORKSPACE"
        )
        for exit_code in exits:
            capture.record(
                kind="UNIT_TEST",
                command=("pytest",),
                result=CommandResult(
                    exit_code=exit_code,
                    stdout="" if exit_code == 0 else "1 failed",
                    stderr="",
                    duration_seconds=0.1 * (1 + exit_code),
                    timed_out=False,
                    command_name="pytest",
                ),
            )
        return LoopResult(
            loop_id=f"loop-{label}",
            final_state=final_state,
            termination=LoopTermination(
                kind="SUCCESS_EVIDENCED"
                if final_state == "CANDIDATE_PASSED"
                else "STOP_REQUESTED",
                detail="integration fixture",
            ),
            iterations=1,
            decisions=(),
            executions=capture.records,
            mutations=(),
            checkpoints=(),
        )

    # 17: A beats B on completion evidence.
    a = build_candidate(
        candidate_index=1,
        label="A",
        result=_result("CANDIDATE_PASSED", (0,), "a"),
        sandbox_id="s-a",
        sandbox_backend="LOCAL_WORKSPACE",
    )
    b = build_candidate(
        candidate_index=2,
        label="B",
        result=_result("CANDIDATE_FAILED", (1,), "b"),
        sandbox_id="s-b",
        sandbox_backend="LOCAL_WORKSPACE",
    )
    assert compare_candidates([a, b]).selected_candidate_id == a.candidate_id

    # 18: B beats A when B completes and A does not.
    b_pass = build_candidate(
        candidate_index=2,
        label="B-pass",
        result=_result("CANDIDATE_PASSED", (0,), "b-pass"),
        sandbox_id="s-b-pass",
        sandbox_backend="LOCAL_WORKSPACE",
    )
    a_fail = build_candidate(
        candidate_index=1,
        label="A2",
        result=_result("CANDIDATE_FAILED", (1,), "a2"),
        sandbox_id="s-a2",
        sandbox_backend="LOCAL_WORKSPACE",
    )
    assert (
        compare_candidates([a_fail, b_pass]).selected_candidate_id
        == b_pass.candidate_id
    )

    # 19: all candidates fail -> no selection, BLOCKED outcome.
    all_failed = compare_candidates([a_fail, b])
    assert all_failed.outcome == "ALL_FAILED"
    assert all_failed.selected_candidate_id is None


def test_stale_context_blocked_at_combined_level() -> None:
    """§8 stale-context protection across the real handoff + barrier."""
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    identities = _seed_full_locked_flow(session)

    verdict = pre_coding_gate(
        session,
        task_id=identities["task_id"],  # type: ignore[arg-type]
        intent_ledger_id=identities["intent_ledger_id"],  # type: ignore[arg-type]
        constitution_id=identities["constitution_id"],  # type: ignore[arg-type]
    )
    assert verdict.state == "PASS"
    context = verdict.context
    assert context is not None

    # Phase 7 creates Intent v2 after the context was minted.
    from smorx_precode.intent_ledger import bump_intent_ledger

    bump_intent_ledger(session, context.intent_ledger_id, note="intent v2")

    # Phase 8 must refuse the v1 context at handoff AND at the barrier.
    with pytest.raises(Exception) as excinfo:
        pre_coding_handoff(session, context=context)
    assert "superseded" in str(excinfo.value)

    barrier = ExecutionBarrier(session=session)
    barrier_verdict = barrier.evaluate(context=context, authorized=True)
    assert barrier_verdict.state == "BLOCKED"
    assert any("superseded" in item for item in barrier_verdict.failed_conditions)
    session.close()

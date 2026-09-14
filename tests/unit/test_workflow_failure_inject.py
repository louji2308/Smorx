"""Unit tests for Phase 12 adversarial failure injection (implementation plan
section 12.5/12.6).

Covers the full mode/classification matrix, POLICY_BLOCK's policy-gated
event path, CONFLICTING_EVIDENCE dual evidence rows, NO_PROGRESS fingerprint
and triple-failure chain, unrelated-task isolation, and idempotent
re-injection row stability.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from smorx_behavior.models import (
    ConsequentialEvent,
    Evidence,
    Execution,
    Failure,
    FailureKind,
    VerificationCase,
    VerificationPlan,
)
from smorx_workflow.failure_inject import (
    FailureInjectionMode,
    inject_failure,
)
from smorx_workflow.orchestrate import workflow_id
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from workflow_helpers import (
    build_auth017,
    make_engine,
    make_run,
    make_session,
    make_task,
)

_MODE_KIND = {
    FailureInjectionMode.SYNTAX_BUILD: FailureKind.F1_SYNTAX_BUILD,
    FailureInjectionMode.UNIT_TEST: FailureKind.F2_UNIT_TEST,
    FailureInjectionMode.TEST_FAILURE: FailureKind.F2_UNIT_TEST,
    FailureInjectionMode.INTEGRATION: FailureKind.F3_INTEGRATION,
    FailureInjectionMode.TIMEOUT: FailureKind.F5_TIMEOUT,
    FailureInjectionMode.TOOL_FAILURE: FailureKind.F7_TOOL,
    FailureInjectionMode.AMBIGUOUS_RESULT: FailureKind.F8_AMBIGUOUS_RESULT,
    FailureInjectionMode.CONFLICTING_EVIDENCE: FailureKind.F8_AMBIGUOUS_RESULT,
    FailureInjectionMode.NO_PROGRESS: FailureKind.F8_AMBIGUOUS_RESULT,
    FailureInjectionMode.POLICY_BLOCK: FailureKind.F10_SAFETY_POLICY_BLOCK,
}


def _count(session: Session, model: Any, **filters: Any) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(model)
            .where(*[getattr(model, k) == v for k, v in filters.items()])
        )
    )


def _get_task_run(session: Session) -> tuple[Any, Any]:
    ctx = build_auth017(session)
    task = make_task(session, project=ctx["project"], change=ctx["change"])
    run = make_run(session, task)
    return task, run


def _make_verification_context(
    session: Session, task: Any, change: Any
) -> VerificationCase:
    plan = VerificationPlan(
        change_id=change.id,
        task_id=task.id,
        title="AUTH-017 verification contract (test)",
        strategy={},
        verification_contract={},
        status="LOCKED",
        owner_scope="VERIFICATION_CONTRACT",
        locked=True,
    )
    session.add(plan)
    session.flush()
    case = VerificationCase(
        verification_plan_id=plan.id,
        change_id=change.id,
        name="ghost-221",
        kind="TEST_RESULT",
        status="PENDING",
        independent=True,
        owning_module="ghost_replay",
    )
    session.add(case)
    session.flush()
    return case


@pytest.fixture()
def engine() -> Any:
    return make_engine()


@pytest.fixture()
def session(engine: Any) -> Iterator[Session]:
    with make_session(engine) as sess:
        yield sess


def test_all_modes_map_to_correct_classification(session: Session) -> None:
    task, run = _get_task_run(session)
    for mode in FailureInjectionMode:
        result = inject_failure(session, task=task, run=run, mode=mode, phase="verify")
        assert result.mode == mode.value
        assert result.classified == _MODE_KIND[mode].value


def test_test_failure_records_execution_failure_and_evidence(session: Session) -> None:
    task, run = _get_task_run(session)
    inject_failure(session, task=task, run=run, mode="TEST_FAILURE", phase="verify")

    assert _count(session, Failure, run_id=run.id) == 1
    assert _count(session, Execution, run_id=run.id) == 1
    assert _count(session, Evidence, run_id=run.id) == 1
    assert _count(session, ConsequentialEvent, run_id=run.id) == 1

    failure = session.scalars(select(Failure).where(Failure.run_id == run.id)).first()
    assert failure is not None
    assert failure.classification == FailureKind.F2_UNIT_TEST.value

    exec_row = session.scalars(
        select(Execution).where(Execution.run_id == run.id)
    ).first()
    assert exec_row is not None
    assert exec_row.exit_code == 1
    assert exec_row.status == "FAILED"

    event = session.scalars(
        select(ConsequentialEvent).where(ConsequentialEvent.run_id == run.id)
    ).first()
    assert event is not None
    assert event.payload.get("blocked") is not True


def test_policy_block_creates_event_and_no_execution(session: Session) -> None:
    task, run = _get_task_run(session)
    result = inject_failure(
        session, task=task, run=run, mode="POLICY_BLOCK", phase="develop"
    )

    assert _count(session, Execution, run_id=run.id) == 0
    assert _count(session, Failure, run_id=run.id) == 0
    assert result.classified == FailureKind.F10_SAFETY_POLICY_BLOCK.value
    assert "injected POLICY_BLOCK" in result.message

    events = session.scalars(
        select(ConsequentialEvent).where(ConsequentialEvent.run_id == run.id)
    ).all()
    blocked = [e for e in events if (e.payload or {}).get("blocked") is True]
    assert len(blocked) == 1


def test_conflicting_evidence_records_two_opposite_evidence_rows(
    session: Session,
) -> None:
    task, run = _get_task_run(session)
    case = _make_verification_context(session, task, task.change)

    inject_failure(
        session,
        task=task,
        run=run,
        mode="CONFLICTING_EVIDENCE",
        phase="verify",
        verification_case=case,
    )

    evidence_rows = session.scalars(
        select(Evidence).where(Evidence.run_id == run.id)
    ).all()
    assert len(evidence_rows) >= 2
    machine_results = [row.machine_result for row in evidence_rows]
    verdicts = [mr.get("passed") for mr in machine_results if "passed" in mr]
    assert True in verdicts
    assert False in verdicts


def test_no_progress_creates_triple_failure_and_fingerprint(session: Session) -> None:
    task, run = _get_task_run(session)
    inject_failure(session, task=task, run=run, mode="NO_PROGRESS", phase="verify")

    failures = session.scalars(select(Failure).where(Failure.run_id == run.id)).all()
    assert len(failures) == 3
    for failure in failures:
        assert failure.classification == FailureKind.F8_AMBIGUOUS_RESULT.value

    events = session.scalars(
        select(ConsequentialEvent).where(ConsequentialEvent.run_id == run.id)
    ).all()
    blocked = [e for e in events if (e.payload or {}).get("blocked") is True]
    assert len(blocked) == 1
    assert "no-progress" in (blocked[0].payload or {}).get("reason", "")


def test_unrelated_task_isolation(session: Session) -> None:
    ctx = build_auth017(session)
    task_a = make_task(session, project=ctx["project"], change=ctx["change"])
    run_a = make_run(session, task_a)

    # Create second task and run directly to avoid duplicate slug
    from smorx_behavior.models import Run as RunModel
    from smorx_behavior.models import RunStatus, Task

    task_b = Task(
        project_id=ctx["project"].id,
        repository_id=ctx["change"].repository_id,
        change_id=ctx["change"].id,
        title="isolation-guard",
        status="CREATED",
        priority="NORMAL",
        acceptance_criteria=[],
    )
    session.add(task_b)
    session.flush()
    run_b_token = f"e2e/run/isolation/{task_b.id}"
    run_b = RunModel(
        id=workflow_id(run_b_token),
        task_id=task_b.id,
        kind="AGENT",
        status=RunStatus.RUNNING.value,
        environment={"provider": "LOCAL", "runtime": "in-memory-sqlite"},
    )
    session.add(run_b)
    session.flush()

    inject_failure(session, task=task_a, run=run_a, mode="TEST_FAILURE", phase="verify")
    assert _count(session, Failure, run_id=run_a.id) == 1
    assert _count(session, Failure, run_id=run_b.id) == 0


def test_idempotent_re_injection_stabilizes_failure_count(session: Session) -> None:
    task, run = _get_task_run(session)
    first = inject_failure(
        session, task=task, run=run, mode="TEST_FAILURE", phase="verify"
    )
    second = inject_failure(
        session, task=task, run=run, mode="TEST_FAILURE", phase="verify"
    )

    assert first.evidence_count == second.evidence_count
    assert first.failure_count == second.failure_count
    assert _count(session, Execution, run_id=run.id) == 1
    assert _count(session, Failure, run_id=run.id) == 1


def test_timeout_creates_blocked_execution(session: Session) -> None:
    task, run = _get_task_run(session)
    result = inject_failure(session, task=task, run=run, mode="TIMEOUT", phase="verify")
    assert result.classified == FailureKind.F5_TIMEOUT.value

    exec_row = session.scalars(
        select(Execution).where(Execution.run_id == run.id)
    ).first()
    assert exec_row is not None
    assert exec_row.status == "BLOCKED"


def test_all_modes_record_event(session: Session) -> None:
    task, run = _get_task_run(session)
    for mode in FailureInjectionMode:
        inject_failure(session, task=task, run=run, mode=mode, phase="verify")

    events = session.scalars(
        select(ConsequentialEvent).where(ConsequentialEvent.run_id == run.id)
    ).all()
    assert len(events) == len(FailureInjectionMode)
    for event in events:
        assert event.hash is not None

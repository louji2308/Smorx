"""Unit tests for Phase 12 reliability controls (implementation plan section 12.3).

Covers idempotency guard, resume-from-reverify, hash-chain refusal, scope
refusal, reset policy gate and scope, and stale sandbox dry-run / delete.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from smorx_behavior.models import (
    ConsequentialEvent,
    Evidence,
    Execution,
    Failure,
    Run,
    RunStatus,
    VerificationStatus,
)
from smorx_workflow.orchestrate import (
    WorkflowError,
    run_e2e_workflow,
    workflow_id,
)
from smorx_workflow.reliability import (
    cleanup_stale_sandboxes,
    idempotency_guard,
    reset_workflow,
    resume_workflow,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from workflow_helpers import (
    build_auth017,
    make_engine,
    make_run,
    make_session,
    make_task,
)


def _count(session: Session, model: Any, **filters: Any) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(model)
            .where(*[getattr(model, k) == v for k, v in filters.items()])
        )
    )


@pytest.fixture()
def engine() -> Any:
    return make_engine()


@pytest.fixture()
def session(engine: Any) -> Iterator[Session]:
    with make_session(engine) as sess:
        yield sess


def _partial_run(session: Session) -> tuple[Run, Any]:
    result = run_e2e_workflow(session, require_certification=False)
    run = session.scalar(select(Run).where(Run.id == workflow_id("e2e/run/AUTH-017")))
    assert run is not None
    return run, result


def test_idempotency_guard_true_for_completed_phases(session: Session) -> None:
    run, _ = _partial_run(session)
    task = run.task

    assert idempotency_guard(session, task=task, phase="discover") is True
    assert idempotency_guard(session, task=task, phase="decide") is True


def test_idempotency_guard_false_for_not_reached_or_blocked(session: Session) -> None:
    run, _ = _partial_run(session)
    task = run.task

    assert idempotency_guard(session, task=task, phase="reverify") is False
    assert idempotency_guard(session, task=task, phase="merge") is False


def test_idempotency_guard_raises_on_unknown_phase(session: Session) -> None:
    run, _ = _partial_run(session)
    task = run.task

    with pytest.raises(WorkflowError, match="unknown phase"):
        idempotency_guard(session, task=task, phase="bogus")


def test_resume_continues_from_reverify(session: Session) -> None:
    run, _ = _partial_run(session)

    resume = resume_workflow(session, run=run)
    assert resume.resumed is True
    assert resume.resume_point == "reverify"
    assert resume.idempotent is False
    assert resume.reset is False

    task = run.task
    assert task.status == "MERGED"

    event_phases = [
        event.payload.get("phase")
        for event in session.scalars(
            select(ConsequentialEvent).where(ConsequentialEvent.run_id == run.id)
        ).all()
        if event.sequence > 0
    ]
    assert "merge" in event_phases


def test_resume_reports_idempotent_when_already_completed(session: Session) -> None:
    run, _ = _partial_run(session)
    resume_workflow(session, run=run)

    second = resume_workflow(session, run=run)
    assert second.resumed is False
    assert second.idempotent is True
    assert second.resume_point is None
    assert "already recorded" in (second.reason or "")


def test_resume_refuses_tampered_chain(session: Session) -> None:
    run, _ = _partial_run(session)
    events = [
        e
        for e in session.scalars(
            select(ConsequentialEvent).where(ConsequentialEvent.run_id == run.id)
        ).all()
        if e.sequence > 0
    ]
    assert events
    events[0].hash = None
    session.flush()

    report = resume_workflow(session, run=run)
    assert report.resumed is False
    assert "cannot resume" in (report.reason or "")


def test_resume_refuses_when_target_outside_segment(session: Session) -> None:
    run, _ = _partial_run(session)
    report = resume_workflow(session, run=run, phases=("discover",))
    assert report.resumed is False
    assert "not within the requested phase segment" in (report.reason or "")


def test_reset_refuses_without_allow_destructive(session: Session) -> None:
    run, _ = _partial_run(session)
    report = reset_workflow(session, run=run)
    assert report.reset is False
    assert "allow_destructive" in (report.reason or "")


def test_reset_deletes_only_run_scoped_rows(session: Session) -> None:
    run, _ = _partial_run(session)
    task = run.task
    change = task.change
    project = task.project

    pre_evidence = _count(session, Evidence, run_id=run.id)
    pre_failure = _count(session, Failure, run_id=run.id)
    pre_event = _count(session, ConsequentialEvent, run_id=run.id)
    assert pre_event > 0

    report = reset_workflow(session, run=run, allow_destructive=True)
    assert report.reset is True
    assert report.cleaned["events"] == pre_event
    assert report.cleaned["evidence"] == pre_evidence
    assert report.cleaned["failures"] == pre_failure

    assert _count(session, Evidence, run_id=run.id) == 0
    assert _count(session, Failure, run_id=run.id) == 0
    assert _count(session, Execution, run_id=run.id) == 0
    assert _count(session, ConsequentialEvent, run_id=run.id) == 0

    assert run.status == RunStatus.QUEUED.value
    assert run.finished_at is None
    assert run.environment["demo_reset"] is True

    assert session.get(type(project), project.id) is not None
    assert session.get(type(task), task.id) is not None
    assert session.get(type(change), change.id) is not None


def test_cleanup_stale_sandboxes_dry_run_returns_counts(session: Session) -> None:
    ctx = build_auth017(session)
    task = make_task(session, project=ctx["project"], change=ctx["change"])
    run = make_run(session, task)
    run.status = RunStatus.BLOCKED.value
    run.finished_at = datetime.now(UTC) - timedelta(hours=50)
    execution = Execution(
        run_id=run.id,
        sandbox_id="stale-sandbox",
        kind="TEST",
        command="pytest -q",
        cwd="/workspace",
        exit_code=1,
        stdout="",
        stderr="",
        status=VerificationStatus.BLOCKED.value,
        finished_at=datetime.now(UTC) - timedelta(hours=50),
        environment={"provider": "LOCAL"},
        machine_result={},
    )
    session.add(execution)
    session.flush()

    report = cleanup_stale_sandboxes(session, staleness_hours=24, dry_run=True)
    assert report.cleaned["stale_runs"] == 1
    assert report.cleaned["stale_sandbox_markers"] == 1
    assert session.get(Execution, execution.id) is not None
    assert "dry run" in (report.reason or "")


def test_cleanup_stale_sandboxes_deletes_markers(session: Session) -> None:
    ctx = build_auth017(session)
    task = make_task(session, project=ctx["project"], change=ctx["change"])
    run = make_run(session, task)
    run.status = RunStatus.BLOCKED.value
    run.finished_at = datetime.now(UTC) - timedelta(hours=50)
    execution = Execution(
        run_id=run.id,
        sandbox_id="stale-sandbox",
        kind="TEST",
        command="pytest -q",
        cwd="/workspace",
        exit_code=1,
        stdout="",
        stderr="",
        status=VerificationStatus.BLOCKED.value,
        finished_at=datetime.now(UTC) - timedelta(hours=50),
        environment={"provider": "LOCAL"},
        machine_result={},
    )
    session.add(execution)
    session.flush()
    run_id = run.id

    report = cleanup_stale_sandboxes(session, staleness_hours=24, dry_run=False)
    assert session.get(Execution, execution.id) is None
    assert report.cleaned["stale_sandbox_markers"] == 1
    assert session.get(Run, run_id) is not None
    assert "removed" in (report.reason or "")

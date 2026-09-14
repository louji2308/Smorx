"""Unit tests for Phase 12 state replay (implementation plan section 12.4).

Covers valid-chain replay of a recorded run, evidence digest matching,
tamper detection (mutated payload / missing hash), expected-hash mismatch,
blocked-event surface, and the empty-run edge case.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from smorx_behavior.models import Run, Task
from smorx_workflow.orchestrate import DEFAULT_PHASES, run_e2e_workflow, workflow_id
from smorx_workflow.replay import (
    ordered_events,
    replay_from_evidence_graph,
)
from sqlalchemy import select
from sqlalchemy.orm import Session
from workflow_helpers import (
    build_auth017,
    make_engine,
    make_run,
    make_session,
    make_task,
)


@pytest.fixture()
def engine() -> Any:
    return make_engine()


@pytest.fixture()
def session(engine: Any) -> Iterator[Session]:
    with make_session(engine) as sess:
        yield sess


def _recorded_full_chain(session: Session) -> tuple[Run, Any]:
    """Run the full chain and return the run row and result."""
    result = run_e2e_workflow(session)
    run = session.scalar(select(Run).where(Run.id == workflow_id("e2e/run/AUTH-017")))
    assert run is not None
    return run, result


def _recorded_partial_run(session: Session) -> tuple[Run, Any]:
    """Record a deterministic partial run that stops at the reverify block."""
    result = run_e2e_workflow(session, require_certification=False)
    run = session.scalar(select(Run).where(Run.id == workflow_id("e2e/run/AUTH-017")))
    assert run is not None
    return run, result


def test_valid_full_chain_replay(session: Session) -> None:
    run, result = _recorded_full_chain(session)
    replay = replay_from_evidence_graph(session, run=run)

    assert replay.hash_chain_valid is True
    assert replay.first_mismatch is None
    assert replay.replayed_phases == list(DEFAULT_PHASES)
    assert replay.evidence_hashes == result.evidence_hashes


def test_valid_blocked_chain_replays_partial_phases(session: Session) -> None:
    """A BLOCKED run replays exactly the completed pre-block phases."""
    run, result = _recorded_partial_run(session)
    replay = replay_from_evidence_graph(session, run=run)

    assert replay.hash_chain_valid is True
    assert replay.first_mismatch is None
    assert replay.replayed_phases == list(DEFAULT_PHASES[:8])
    assert replay.replayed_phases == result.completed_phases


def test_replay_matches_expected_evidence_hashes(session: Session) -> None:
    run, result = _recorded_full_chain(session)
    replay = replay_from_evidence_graph(
        session, run=run, expected_hashes=result.evidence_hashes
    )

    assert replay.hash_chain_valid is True
    assert replay.first_mismatch is None


def test_replay_rejects_evidence_expected_mismatch(session: Session) -> None:
    run, _result = _recorded_full_chain(session)
    replay = replay_from_evidence_graph(session, run=run, expected_hashes=["deadbeef"])

    assert replay.hash_chain_valid is True
    assert replay.first_mismatch is not None
    assert "evidence digest" in replay.first_mismatch
    assert replay.replayable is False


def test_replay_detects_tampered_payload(session: Session) -> None:
    run, _result = _recorded_partial_run(session)
    events = ordered_events(session, run)
    assert events
    tampered = events[2]
    payload = dict(tampered.payload or {})
    payload["phase"] = "tampered"
    tampered.payload = payload

    replay = replay_from_evidence_graph(session, run=run)
    assert replay.replayable is False
    assert replay.hash_chain_valid is False
    assert replay.first_mismatch is not None
    assert str(replay.first_mismatch).startswith(
        "stored/recomputed mismatch at sequence"
    )


def test_replay_detects_missing_hash(session: Session) -> None:
    run, _result = _recorded_partial_run(session)
    events = ordered_events(session, run)
    assert events
    events[1].hash = None

    replay = replay_from_evidence_graph(session, run=run)
    assert replay.replayable is False
    assert replay.hash_chain_valid is False
    assert replay.first_mismatch == "missing stored hash"


def test_replay_surfaces_blocked_events(session: Session) -> None:
    run, result = _recorded_partial_run(session)
    replay = replay_from_evidence_graph(session, run=run)

    assert replay.blocked_events
    assert replay.blocked_reason == result.blocked_reason
    assert replay.blocked_events[0]["payload"]["blocked"] is True


def test_replay_empty_run_is_not_replayable(session: Session) -> None:
    ctx = build_auth017(session)
    task = make_task(session, project=ctx["project"], change=ctx["change"])
    run = make_run(session, task)

    replay = replay_from_evidence_graph(session, run=run)
    assert replay.replayable is False
    assert replay.hash_chain_valid is True
    assert "no chained events" in (replay.first_mismatch or "")


def test_ordered_events_return_ascending_sequence(session: Session) -> None:
    run, _result = _recorded_partial_run(session)
    events = ordered_events(session, run)
    sequences = [event.sequence for event in events]
    assert sequences == sorted(sequences)
    assert sequences[0] == 1
    assert all(sequence > 0 for sequence in sequences)


def test_run_scoped_events_are_isolated(session: Session) -> None:
    """Events from one run are not visible to another run's ordered_events."""
    run, _ = _recorded_partial_run(session)

    # Create a second empty run for a different task (no slug conflict with seed)
    from smorx_behavior.models import Run as RunModel
    from smorx_behavior.models import RunStatus

    seed_task = session.scalar(select(Task).limit(1))
    assert seed_task is not None
    task2 = Task(
        project_id=seed_task.project_id,
        repository_id=seed_task.repository_id,
        change_id=seed_task.change_id,
        title="isolation-guard",
        status="CREATED",
        priority="NORMAL",
        acceptance_criteria=[],
    )
    session.add(task2)
    session.flush()
    assert task2.id != run.task_id
    run2 = RunModel(
        task_id=task2.id,
        kind="AGENT",
        status=RunStatus.RUNNING.value,
        environment={"provider": "LOCAL"},
    )
    session.add(run2)
    session.flush()

    events_run1 = ordered_events(session, run)
    events_run2 = ordered_events(session, run2)
    assert len(events_run1) > 0
    assert len(events_run2) == 0

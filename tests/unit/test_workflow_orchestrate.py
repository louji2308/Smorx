"""Unit tests for the Phase 12 E2E orchestration driver (implementation plan
section 12.1).

Covers the canonical chain order over real ORM rows, honest degradation to
BLOCKED when certification is disabled or evidence is missing, full-chain
completion with seed-based evidence and real certification, cross-session
determinism, deterministic-evidence caching, and contract violations
(missing governing project / non-subsequence phase segments).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from smorx_behavior.models import (
    Certificate,
    CertificateStatus,
    ConsequentialEvent,
    MemoryUpdate,
    Run,
    RunStatus,
)
from smorx_workflow.orchestrate import (
    DEFAULT_PHASES,
    WorkflowError,
    cache_deterministic_evidence,
    read_cached_deterministic_evidence,
    run_e2e_workflow,
    run_phases,
    workflow_id,
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

EXPECTED_PARTIAL = list(DEFAULT_PHASES[:8])


@pytest.fixture()
def engine() -> Any:
    return make_engine()


@pytest.fixture()
def session(engine: Any) -> Iterator[Session]:
    with make_session(engine) as sess:
        yield sess


def _ctx(session: Session) -> dict[str, Any]:
    """AUTH-017 governing graph (project, repo, change #184, behaviors, ghost)."""
    return build_auth017(session)


def _run(session: Session, **kwargs: Any) -> Any:
    return run_e2e_workflow(session, **kwargs)


def test_full_chain_completes_with_default_reader(session: Session) -> None:
    result = _run(session)

    assert result.state == "COMPLETED"
    assert result.completed_phases == list(DEFAULT_PHASES)
    assert result.evidence_hashes
    assert result.blocked_reason is None
    assert result.replayable is True

    run = session.scalar(select(Run).where(Run.id == workflow_id("e2e/run/AUTH-017")))
    assert run is not None
    assert run.status == RunStatus.COMPLETED.value

    task = run.task
    assert task.status == "MERGED"

    certificate = session.scalar(
        select(Certificate).where(Certificate.task_id == task.id)
    )
    assert certificate is not None
    assert certificate.status == CertificateStatus.CERTIFIED.value

    memory = session.scalar(select(MemoryUpdate).where(MemoryUpdate.task_id == task.id))
    assert memory is not None
    assert memory.applied is True


def test_no_certification_blocks_after_decide(session: Session) -> None:
    result = _run(session, require_certification=False)

    assert result.state == "BLOCKED"
    assert result.blocked_reason is not None
    assert "require_certification=False" in result.blocked_reason
    assert result.completed_phases == EXPECTED_PARTIAL

    run = session.scalar(select(Run).where(Run.id == workflow_id("e2e/run/AUTH-017")))
    assert run is not None
    assert run.status == RunStatus.BLOCKED.value


def test_empty_reader_blocks_at_reverify(session: Session) -> None:
    result = _run(session, evidence_reader=lambda *a, **k: [])

    assert result.state == "BLOCKED"
    assert result.completed_phases == list(DEFAULT_PHASES[:9])
    assert result.blocked_reason is not None
    assert "re-verification" in result.blocked_reason.lower()

    run = session.scalar(select(Run).where(Run.id == workflow_id("e2e/run/AUTH-017")))
    assert run is not None
    assert run.status == RunStatus.BLOCKED.value


def test_empty_reader_records_reverify_event(session: Session) -> None:
    _run(session, evidence_reader=lambda *a, **k: [])

    events = session.scalars(
        select(ConsequentialEvent).where(
            ConsequentialEvent.run_id == workflow_id("e2e/run/AUTH-017")
        )
    ).all()
    reverify = [e for e in events if (e.payload or {}).get("phase") == "reverify"]
    assert len(reverify) == 1
    assert (reverify[0].payload or {}).get("blocked") is True


def test_evidence_deterministic_across_sessions() -> None:
    first_engine = make_engine()
    second_engine = make_engine()
    with make_session(first_engine) as one:
        r1 = run_e2e_workflow(one, require_certification=False)
    with make_session(second_engine) as two:
        r2 = run_e2e_workflow(two, require_certification=False)

    assert r1.evidence_hashes == r2.evidence_hashes
    assert r1.completed_phases == r2.completed_phases
    assert r1.blocked_reason == r2.blocked_reason


def test_deterministic_evidence_cache_round_trip(session: Session) -> None:
    key = "verify-contract/AUTH-017"
    first_digest, first_created = cache_deterministic_evidence(
        session, key, {"change": 184}
    )
    second_digest, second_created = cache_deterministic_evidence(
        session, key, {"change": 184}
    )

    assert first_digest == second_digest
    assert first_created is True
    assert second_created is False
    assert read_cached_deterministic_evidence(session, key) == {"change": 184}
    assert read_cached_deterministic_evidence(session, "missing-key") is None

    cached_rows = session.scalar(
        select(func.count())
        .select_from(ConsequentialEvent)
        .where(
            ConsequentialEvent.entity_type == "CACHE",
            ConsequentialEvent.entity_id == workflow_id(f"cache/{key}"),
        )
    )
    assert cached_rows == 1


def test_phase_subsequence_contract(session: Session) -> None:
    ctx = _ctx(session)
    task = make_task(session, project=ctx["project"], change=ctx["change"])
    run = make_run(session, task)

    with pytest.raises(WorkflowError, match="must begin at the discover phase"):
        run_e2e_workflow(session, phases=("govern",))

    with pytest.raises(WorkflowError, match="ordered, non-repeating"):
        run_phases(session, run=run, phases=("develop", "discover"))

    with pytest.raises(WorkflowError, match="unknown phase"):
        run_phases(session, run=run, phases=("bogus",))


def test_run_phases_segment_produces_in_progress_state(session: Session) -> None:
    ctx = _ctx(session)
    task = make_task(session, project=ctx["project"], change=ctx["change"])
    run = make_run(session, task)

    result = run_phases(session, run=run, phases=("discover", "govern"))
    assert result.state == "IN_PROGRESS"
    assert result.completed_phases == ["discover", "govern"]
    assert result.replayable is True

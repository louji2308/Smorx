"""Integration tests: the full Phase 2 lifecycle seed -> query back.

Phase 2 exit gate: "the full lifecycle can be represented and queried without
losing ownership, version, provenance, or historical evidence." These tests
seed the deterministic demo scenario and traverse it back through the real
models and the repo/catalog layers, verifying that every tested node is
owned by its parent and that re-seeding is deterministic and idempotent.

Self-contained: synchronous in-memory SQLite (``create_sync_engine`` +
``StaticPool`` + ``create_all``), no dependency on other test modules.
"""

from __future__ import annotations

import uuid

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import (
    AgentRun,
    Certificate,
    Change,
    Claim,
    Failure,
    FailureKind,
    Ghost,
    MemoryUpdate,
    Project,
    Run,
    Task,
)
from smorx_behavior.repo import catalog
from smorx_behavior.repo.base import get
from smorx_behavior.seed.demo import build_seed
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.fixture()
def engine() -> object:
    eng = create_sync_engine("sqlite:///:memory:")
    event.listen(
        eng,
        "connect",
        lambda raw_conn, _: raw_conn.execute("PRAGMA foreign_keys=ON"),
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: object) -> Session:
    with Session(engine) as sess:
        yield sess


def test_seed_resolves_required_scenario_tokens(session: Session) -> None:
    report = build_seed(session)

    change = get(session, Change, report.change_id)
    assert change is not None
    assert change.external_id == "184"

    task = get(session, Task, report.task_id)
    assert task is not None
    assert "AUTH-017" in task.title

    ghost = get(session, Ghost, report.ghost_id)
    assert ghost is not None
    assert ghost.name == "Ghost #221"

    failure = get(session, Failure, report.failure_id)
    assert failure is not None
    assert "F-183" in failure.message
    assert failure.classification == FailureKind.F3_INTEGRATION

    tokens = report.key_tokens()
    assert tokens["change"] == "184"
    assert tokens["task"] == "AUTH-017"
    assert tokens["ghost"] == "Ghost #221"
    assert tokens["failure"] == "F-183"


def test_lifecycle_chain_deterministic_ids(session: Session) -> None:
    report = build_seed(session)

    for value in (
        report.project_id,
        report.repository_id,
        report.change_id,
        report.task_id,
        report.run_id,
        report.agent_run_id,
        report.ghost_id,
        report.failure_id,
        report.claim_id,
        report.delta_id,
        report.certificate_id,
        report.memory_update_id,
        *report.subagent_run_ids,
    ):
        assert isinstance(value, uuid.UUID)

    assert len(set(report.subagent_run_ids)) == 3
    assert len(report.evidence_hashes) == 6
    assert all(len(h) == 64 for h in report.evidence_hashes)
    assert report.evidence_backend.startswith("smorx_behavior.evidence")


def test_lifecycle_graph_ownership_intact(session: Session) -> None:
    report = build_seed(session)
    graph = catalog.lifecycle(session, change_id=report.change_id)

    assert [p.id for p in graph["projects"]] == [report.project_id]
    assert [r.id for r in graph["repositories"]] == [report.repository_id]
    assert [c.id for c in graph["changes"]] == [report.change_id]

    change = graph["changes"][0]
    assert change.repository.id == report.repository_id
    assert change.repository.project.id == report.project_id

    tasks = graph["tasks"]
    assert [t.id for t in tasks] == [report.task_id]
    task = tasks[0]
    assert task.project_id == report.project_id
    assert task.repository_id == report.repository_id
    assert task.change_id == report.change_id

    runs = graph["runs"]
    assert [r.id for r in runs] == [report.run_id]
    assert runs[0].task_id == report.task_id

    agent_runs = graph["agent_runs"]
    assert [a.id for a in agent_runs] == [report.agent_run_id]
    assert agent_runs[0].run_id == report.run_id

    subagents = graph["subagent_runs"]
    assert {s.id for s in subagents} == set(report.subagent_run_ids)
    assert all(s.agent_run_id == report.agent_run_id for s in subagents)
    names = {s.name for s in subagents}
    assert "Failure Archaeology Agent" in names
    assert "Independent Verification Agent" in names
    assert "Certification Agent" in names

    evidence = graph["evidence"]
    assert {e.id for e in evidence} == set(report.evidence_ids)
    for ev in evidence:
        assert len(ev.hash) == 64

    claims = graph["claims"]
    assert [c.id for c in claims] == [report.claim_id]
    assert claims[0].task_id == report.task_id

    deltas = graph["behavioral_deltas"]
    assert [d.id for d in deltas] == [report.delta_id]
    assert deltas[0].change_id == report.change_id
    assert deltas[0].certificate_id == report.certificate_id

    certificates = graph["certificates"]
    assert [c.id for c in certificates] == [report.certificate_id]

    memories = graph["memory_updates"]
    assert [m.id for m in memories] == [report.memory_update_id]
    assert memories[0].certificate_id == report.certificate_id
    assert memories[0].task_id == report.task_id


def test_catalog_purpose_queries(session: Session) -> None:
    report = build_seed(session)

    tasks = catalog.tasks_for_change(session, report.change_id)
    assert [t.id for t in tasks] == [report.task_id]

    evidence = catalog.evidence_for_change(session, report.change_id)
    assert {e.id for e in evidence} == set(report.evidence_ids)

    certificates = catalog.certificate_for_change(session, report.change_id)
    assert [c.id for c in certificates] == [report.certificate_id]

    memories = catalog.memory_for_change(session, report.change_id)
    assert [m.id for m in memories] == [report.memory_update_id]


def test_orm_navigation_chain(session: Session) -> None:
    report = build_seed(session)

    project = get(session, Project, report.project_id)
    assert project is not None
    assert project.repositories[0].id == report.repository_id
    assert project.repositories[0].changes[0].id == report.change_id
    assert project.repositories[0].changes[0].tasks[0].id == report.task_id

    task = get(session, Task, report.task_id)
    assert task is not None
    assert task.runs[0].id == report.run_id
    assert task.runs[0].agent_runs[0].id == report.agent_run_id
    assert task.runs[0].agent_runs[0].subagent_runs[0].id == report.subagent_run_ids[0]

    claim = get(session, Claim, report.claim_id)
    assert claim is not None
    assert {ev.id for ev in claim.evidence_items} <= set(report.evidence_ids)
    assert claim.behavioral_deltas[0].id == report.delta_id

    certificate = get(session, Certificate, report.certificate_id)
    assert certificate is not None
    assert certificate.behavioral_deltas[0].id == report.delta_id
    assert certificate.memory_updates[0].id == report.memory_update_id

    memory = get(session, MemoryUpdate, report.memory_update_id)
    assert memory is not None
    assert memory.certificate.id == report.certificate_id

    agent_run = get(session, AgentRun, report.agent_run_id)
    assert agent_run is not None
    assert len(agent_run.subagent_runs) == 3

    run = get(session, Run, report.run_id)
    assert run is not None
    assert run.agent_runs[0].id == report.agent_run_id
    assert {exec_.run_id for exec_ in run.executions} == {report.run_id}


def test_seed_deterministic_and_idempotent(session: Session) -> None:
    report_first = build_seed(session)
    report_second = build_seed(session)

    assert report_first == report_second
    assert report_first.change_id == report_second.change_id
    assert report_first.task_id == report_second.task_id
    assert report_first.ghost_id == report_second.ghost_id
    assert report_first.failure_id == report_second.failure_id
    assert report_first.evidence_ids == report_second.evidence_ids
    assert report_first.evidence_hashes == report_second.evidence_hashes


def test_seed_deterministic_across_fresh_databases() -> None:
    reports = []
    for _ in range(2):
        eng = create_sync_engine("sqlite:///:memory:")
        Base.metadata.create_all(eng)
        with Session(eng) as sess:
            reports.append(build_seed(sess))

    first, second = reports
    for attr in (
        "project_id",
        "repository_id",
        "change_id",
        "task_id",
        "run_id",
        "agent_run_id",
        "behavior_id",
        "ghost_id",
        "failure_id",
        "claim_id",
        "delta_id",
        "certificate_id",
        "memory_update_id",
    ):
        assert getattr(first, attr) == getattr(second, attr), attr
    assert first.subagent_run_ids == second.subagent_run_ids
    assert first.evidence_hashes == second.evidence_hashes

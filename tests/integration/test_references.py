"""Integration tests: FK/reference integrity, historical preservation via
versioning, evidence dedup at the integration level, and the repo-layer
destructive-operation policy.

These are the Phase 2 "foreign-key/reference tests", "historical preservation
tests", and "evidence deduplication tests" run against the real tables in a
synchronous in-memory SQLite database with foreign keys enforced.

Self-contained: no dependency on other test modules; uses the real
``smorx_behavior.evidence`` and ``smorx_behavior.versioning`` services that
the parallel agents published.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.evidence.service import compute_content_hash, record_evidence
from smorx_behavior.models import (
    Change,
    Evidence,
    EvidenceType,
    Project,
    Repository,
    Task,
    TaskStatus,
    VerificationPlan,
)
from smorx_behavior.repo.base import delete, digest, get, save
from smorx_behavior.versioning.lock import is_locked, lock
from smorx_behavior.versioning.service import bump, get_lineage
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

FIXED_AT = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)


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


def test_dangling_foreign_key_rejected(session: Session) -> None:
    orphan = Task(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="orphan task without a project",
        status=TaskStatus.CREATED.value,
    )
    session.add(orphan)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

    project = Project(name="Valid Project", slug="valid-project")
    session.add(project)
    session.flush()
    attached = Task(
        project_id=project.id,
        title="valid task",
        status=TaskStatus.CREATED.value,
    )
    save(session, attached)
    session.commit()
    assert get(session, Task, attached.id).project_id == project.id


def test_delete_is_policy_blocked_by_default(session: Session) -> None:
    project = Project(name="Delete Guard", slug="delete-guard")
    save(session, project)
    session.commit()

    with pytest.raises(RuntimeError):
        delete(session, project)

    delete(session, project, allow_destructive=True)
    session.commit()
    assert get(session, Project, project.id) is None


def test_history_preserved_bump_locked_object(session: Session) -> None:
    project = Project(name="Ver", slug="ver-history")
    save(session, project)
    repository = Repository(project=project, name="ver-repo")
    save(session, repository)
    change = Change(repository=repository, external_id="184", title="history check")
    save(session, change)
    session.commit()

    plan = VerificationPlan(
        change=change,
        title="locked verification plan",
        strategy={"modules": ["static_analysis"]},
        verification_contract={"cases": ["v1"]},
        version=1,
        locked=False,
    )
    save(session, plan)
    session.commit()

    assert plan.version == 1
    assert plan.locked is False

    lock(session, plan)
    session.commit()
    assert is_locked(plan) is True

    next_version = bump(session, plan, note="reissued verification contract")
    session.commit()

    assert next_version.id != plan.id
    assert next_version.version == 2
    assert is_locked(next_version) is False

    original = get(session, VerificationPlan, plan.id)
    assert original is not None
    assert original.version == 1
    assert original.locked is True

    lineage = get_lineage(session, VerificationPlan, next_version.id)
    assert lineage == [plan.id, next_version.id]


def test_evidence_dedup_idempotent_via_service(session: Session) -> None:
    content_hash = digest("integ/evidence/report-184", "0")

    first = record_evidence(
        session,
        evidence_type=EvidenceType.TEST_RESULT,
        occurred_at=FIXED_AT,
        source="sandbox-run-1",
        provenance="execution://integ/run/1",
        artifact="reports/report-184.json",
        machine_result={"exit_code": 0, "tests_passed": 42},
        content_hash=content_hash,
    )
    session.commit()
    first_id = first.id

    second = record_evidence(
        session,
        evidence_type=EvidenceType.TEST_RESULT,
        occurred_at=FIXED_AT,
        source="sandbox-run-2",
        provenance="execution://integ/run/2",
        artifact="reports/report-184.json",
        machine_result={"exit_code": 0, "tests_passed": 42},
        content_hash=content_hash,
    )
    session.commit()

    assert second.id == first_id
    count = session.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.hash == content_hash)
    )
    assert count == 1


def test_evidence_unique_hash_constraint_rejects_duplicates(session: Session) -> None:
    content_hash = digest("integ/evidence/duplicate", "1")

    legit = record_evidence(
        session,
        evidence_type=EvidenceType.STATIC_ANALYSIS,
        occurred_at=FIXED_AT,
        source="analyzer",
        provenance="verify://integ/case/1",
        artifact="report.json",
        machine_result={"exit_code": 0, "findings": []},
        content_hash=content_hash,
    )
    session.commit()

    bypass = Evidence(
        id=uuid.uuid4(),
        type=EvidenceType.STATIC_ANALYSIS,
        source="raw-insert",
        provenance="verify://integ/case/raw",
        machine_result={"exit_code": 0, "findings": []},
        hash=content_hash,
    )
    session.add(bypass)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    assert get(session, Evidence, legit.id) is not None


def test_evidence_hash_is_deterministic_across_equivalent_payloads() -> None:
    kwargs_a = {
        "evidence_type": EvidenceType.TEST_RESULT,
        "occurred_at": FIXED_AT,
        "source": "tests/test_auth.py",
        "provenance": "execution://run/7",
        "artifact": "reports/auth-017.json",
        "machine_result": {"exit_code": 0, "tests_passed": 42},
    }
    kwargs_b = dict(kwargs_a)
    assert compute_content_hash(**kwargs_a) == compute_content_hash(**kwargs_b)
    assert len(compute_content_hash(**kwargs_a)) == 64

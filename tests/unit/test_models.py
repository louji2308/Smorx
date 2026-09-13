"""Unit tests for the behavioral entity model.

Phase 2 (implementation plan steps 2.1-2.4): verifies the 31 declarative
entities against ``smorx_behavior.db.base.Base.metadata`` on an in-memory
SQLite engine only. No settings/engine module is used, so these tests are
dialect-portable and DB-credential-free.

The module-level ``importorskip`` guards are intentional: the parallel
``smorx_behavior.db`` package is still being built. If any fixed contract
name is not yet published, these tests skip instead of crashing collection.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

models = pytest.importorskip("smorx_behavior.models")
pytest.importorskip("smorx_behavior.db.base")

EXPECTED_MODELS = (
    "Project",
    "Repository",
    "Change",
    "Task",
    "Run",
    "AgentRun",
    "SubagentRun",
    "Behavior",
    "Invariant",
    "Incident",
    "Dependency",
    "RiskZone",
    "Ghost",
    "Evidence",
    "Claim",
    "Constitution",
    "ConstitutionClaim",
    "IntentLedger",
    "IntentItem",
    "SemanticImpact",
    "VerificationPlan",
    "VerificationCase",
    "CandidatePatch",
    "Execution",
    "Failure",
    "BehavioralDelta",
    "IntentAlignment",
    "RepairPackage",
    "Certificate",
    "MemoryUpdate",
    "ConsequentialEvent",
)

EXPECTED_TABLES = {
    "projects",
    "repositories",
    "changes",
    "tasks",
    "runs",
    "agent_runs",
    "subagent_runs",
    "behaviors",
    "invariants",
    "incidents",
    "dependencies",
    "risk_zones",
    "ghosts",
    "evidence",
    "claims",
    "constitutions",
    "constitution_claims",
    "intent_ledgers",
    "intent_items",
    "semantic_impacts",
    "verification_plans",
    "verification_cases",
    "candidate_patches",
    "executions",
    "failures",
    "behavioral_deltas",
    "intent_alignments",
    "repair_packages",
    "certificates",
    "memory_updates",
    "consequential_events",
}


@pytest.fixture()
def engine() -> object:
    eng = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: object) -> Session:
    with Session(engine) as sess:
        yield sess


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_all_31_models_exist_and_subclass_base() -> None:
    for name in EXPECTED_MODELS:
        assert hasattr(models, name), f"missing model class {name}"
        cls = getattr(models, name)
        assert isinstance(cls, type), f"{name} is not a class"
        assert issubclass(cls, models.Base), f"{name} does not inherit Base"


def test_all_tables_registered_on_base_metadata() -> None:
    assert EXPECTED_TABLES <= set(models.Base.metadata.tables)


def test_create_all_schema_succeeds_with_naming_convention(engine: object) -> None:
    tables = {name: table for name, table in models.Base.metadata.tables.items() if name in EXPECTED_TABLES}
    assert set(tables) == EXPECTED_TABLES
    for table in tables.values():
        for constraint in list(table.constraints) + list(table.indexes):
            assert constraint.name, f"unnamed constraint/index on {table.name}"


def test_version_lock_columns_present_on_immutable_tables() -> None:
    for name in ("Certificate", "Claim", "IntentLedger", "VerificationPlan", "Constitution"):
        cls = getattr(models, name)
        columns = cls.__table__.columns
        assert "version" in columns, name
        assert "locked" in columns, name


def test_evidence_identity_columns() -> None:
    cols = models.Evidence.__table__.columns
    for col in ("type", "occurred_at", "source", "provenance", "task_id", "run_id", "artifact", "machine_result", "hash"):
        assert col in cols, col
    assert cols["hash"].unique is True
    assert cols["id"].primary_key is True


def _seed_lifecycle_chain(session: Session) -> dict[str, object]:
    project = models.Project(name="Payments API", slug="payments-api")
    repository = models.Repository(
        project=project,
        name="smorx/payments-api",
        url="https://example.test/payments-api",
        default_branch="main",
    )
    change = models.Change(
        repository=repository,
        external_id="184",
        title="AUTH flow hardening",
        status="OPEN",
        commit_sha=_sha256_hex("commit-184")[:40],
    )
    task = models.Task(
        project=project,
        repository=repository,
        change=change,
        title="Fix AUTH-017 insufficient checks in token refresh",
        status="EXECUTING",
        priority="HIGH",
    )
    run = models.Run(task=task, kind="AGENT", status="RUNNING")
    agent_run = models.AgentRun(
        run=run,
        role="ORCHESTRATOR",
        model="nemotron",
        status="RUNNING",
        state="EXECUTING",
    )
    claim = models.Claim(task=task, statement="Token refresh now rejects forged AUTH-017 requests")
    evidence = models.Evidence(
        task=task,
        run=run,
        agent_run=agent_run,
        claim=claim,
        type="TEST_RESULT",
        occurred_at=datetime.now(UTC),
        source="tests/test_auth.py",
        provenance="execution:run/exec-42 -> claim-payload",
        artifact="artifacts/auth-017/pytest-report.json",
        machine_result={"tests_passed": 42, "tests_failed": 0, "exit_code": 0},
        hash=_sha256_hex("tests/test_auth.py:42-passed"),
    )
    delta = models.BehavioralDelta(
        task=task,
        change=change,
        claim=claim,
        metric="failed_requests",
        baseline_value="3",
        candidate_value="0",
        direction="DECREASED",
        category="SECURITY",
        observed=True,
        description="AUTH-017 failure path no longer reachable.",
    )
    certificate = models.Certificate(
        task=task,
        claim=claim,
        certificate_key=_sha256_hex("cert/184/AUTH-017")[:64],
        status="CERTIFIED",
        issued_at=datetime.now(UTC),
        evidence_hash=evidence.hash,
    )
    delta.certificate = certificate
    session.add_all(
        [project, repository, change, task, run, agent_run, claim, evidence, delta, certificate]
    )
    session.commit()
    return {
        "project": project,
        "repository": repository,
        "change": change,
        "task": task,
        "run": run,
        "agent_run": agent_run,
        "claim": claim,
        "evidence": evidence,
        "delta": delta,
        "certificate": certificate,
    }


def test_lifecycle_chain_navigation(engine: object) -> None:
    with Session(engine) as session:
        rows = _seed_lifecycle_chain(session)
        expected = {key: row.id for key, row in rows.items() if key != "project"}

    with Session(engine) as session:
        project = session.scalar(select(models.Project).where(models.Project.slug == "payments-api"))
        assert project is not None
        assert project.repositories[0].id == expected["repository"]
        assert project.repositories[0].changes[0].id == expected["change"]
        assert project.repositories[0].changes[0].tasks[0].id == expected["task"]
        task = session.scalar(select(models.Task).where(models.Task.id == expected["task"]))
        assert task is not None
        assert task.runs[0].id == expected["run"]
        assert task.runs[0].agent_runs[0].id == expected["agent_run"]
        agent_run = session.scalar(select(models.AgentRun).where(models.AgentRun.id == expected["agent_run"]))
        assert agent_run is not None
        assert agent_run.evidence_items[0].id == expected["evidence"]
        evidence = session.scalar(select(models.Evidence).where(models.Evidence.id == expected["evidence"]))
        assert evidence is not None
        assert evidence.claim.id == expected["claim"]
        assert evidence.claim.task.id == expected["task"]
        claim = session.scalar(select(models.Claim).where(models.Claim.id == expected["claim"]))
        assert claim is not None
        assert claim.behavioral_deltas[0].id == expected["delta"]
        delta = session.scalar(select(models.BehavioralDelta).where(models.BehavioralDelta.id == expected["delta"]))
        assert delta is not None
        assert delta.certificate.id == expected["certificate"]
        certificate = session.scalar(select(models.Certificate).where(models.Certificate.id == expected["certificate"]))
        assert certificate is not None
        assert certificate.behavioral_deltas[0].claim.statement == "Token refresh now rejects forged AUTH-017 requests"
        assert certificate.evidence_hash == _sha256_hex("tests/test_auth.py:42-passed")


def test_evidence_identity_and_hash_uniqueness(engine: object) -> None:
    with Session(engine) as session:
        first = models.Evidence(
            source="sandbox-run-1",
            artifact="report-1.json",
            machine_result={"exit_code": 0},
            hash=_sha256_hex("artifact/report-1.json"),
        )
        second = models.Evidence(
            source="sandbox-run-2",
            artifact="report-2.json",
            machine_result={"exit_code": 1},
            hash=_sha256_hex("artifact/report-2.json"),
        )
        session.add_all([first, second])
        session.commit()
        first_id, second_id = first.id, second.id
        first_hash, second_hash = first.hash, second.hash

    assert first_id != second_id
    assert isinstance(first_id, uuid.UUID)
    assert isinstance(second_id, uuid.UUID)
    for digest in (first_hash, second_hash):
        assert len(digest) == 64
        assert digest == _sha256_hex(
            "artifact/report-1.json" if digest == first_hash else "artifact/report-2.json"
        )

    assert first_hash == _sha256_hex("artifact/report-1.json")

    with Session(engine) as session:
        duplicate = models.Evidence(
            source="sandbox-run-3",
            artifact="report-1.json",
            machine_result={"exit_code": 0},
            hash=first_hash,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()


def test_consequential_event_insert_and_read(engine: object) -> None:
    with Session(engine) as session:
        project = models.Project(name="Trace Project", slug="trace-project")
        change = models.Change(
            repository=models.Repository(project=project, name="trace-repo"),
            external_id="184",
            title="AUTH flow hardening",
        )
        session.add_all([project, change])
        session.commit()
        change_id = change.id

    with Session(engine) as session:
        event = models.ConsequentialEvent(
            entity_type="Change",
            entity_id=change_id,
            event_type="PLAN_GENERATED",
            occurred_at=datetime.now(UTC),
            actor="nemotron",
            payload={"phase": "2.1", "decision": "plan-payload"},
            provenance="trace://run/7/event/11",
            sequence=1,
        )
        session.add(event)
        session.commit()
        event_id = event.id

    with Session(engine) as session:
        fetched = session.scalar(select(models.ConsequentialEvent).where(models.ConsequentialEvent.id == event_id))
        assert fetched is not None
        assert fetched.entity_type == "Change"
        assert fetched.entity_id == change_id
        assert fetched.event_type == "PLAN_GENERATED"
        assert fetched.actor == "nemotron"
        assert fetched.payload == {"phase": "2.1", "decision": "plan-payload"}
        assert fetched.provenance == "trace://run/7/event/11"
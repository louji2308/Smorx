"""Unit tests for the evidence/provenance service layer (phase 2, step 2.2).

Covers content-addressed deduplication, the claim-support eligibility gate,
ordered evidence lookups, lineage traversal, and the certificate binding map
over the real ``smorx_behavior.models`` ORM entities on a synchronous
in-memory SQLite engine (``create_sync_engine`` + ``StaticPool`` + ``create_all``).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.evidence.provenance import (
    certificate_traversal,
    claim_evidence_chain,
    evidence_to_certificate_path,
    provenance_path,
)
from smorx_behavior.evidence.service import (
    compute_content_hash,
    eligibility,
    evidence_by_hash,
    evidence_for_claim,
    evidence_for_task,
    record_evidence,
)
from smorx_behavior.models import (
    AgentRun,
    Base,
    BehavioralDelta,
    Certificate,
    Change,
    Claim,
    Evidence,
    EvidenceType,
    MemoryUpdate,
    Project,
    Repository,
    Run,
    SubagentRun,
    Task,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

FIXED_AT = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)


@pytest.fixture()
def engine() -> object:
    eng = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: object) -> Session:
    with Session(engine) as sess:
        yield sess


def _seed_context(session: Session) -> dict[str, object]:
    project = Project(name="Payments API", slug="payments-api")
    repository = Repository(project=project, name="payments-api")
    change = Change(
        repository=repository, external_id="184", title="AUTH flow hardening"
    )
    task = Task(
        project=project,
        repository=repository,
        change=change,
        title="Fix AUTH-017 insufficient checks in token refresh",
        status="EXECUTING",
    )
    session.add_all([project, repository, change, task])
    session.flush()
    return {
        "project": project,
        "repository": repository,
        "change": change,
        "task": task,
    }


def _test_result_kwargs() -> dict[str, object]:
    return {
        "evidence_type": EvidenceType.TEST_RESULT,
        "occurred_at": FIXED_AT,
        "source": "tests/test_auth.py",
        "provenance": "execution://run/7",
        "artifact": "reports/auth-017.json",
        "machine_result": {"exit_code": 0, "tests_passed": 42, "stdout": "42 passed"},
    }


def test_record_evidence_deduplicates_by_content_hash(session: Session) -> None:
    kwargs = _test_result_kwargs()

    first = record_evidence(session, **kwargs)
    second = record_evidence(session, **kwargs)
    digest = first.hash
    assert digest == compute_content_hash(**kwargs)
    assert len(digest) == 64
    assert first.id == second.id
    assert first is second
    session.commit()
    first_id = first.id

    after_commit = record_evidence(session, **kwargs)
    session.commit()
    assert after_commit.id == first_id

    count = session.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.hash == digest)
    )
    assert count == 1


def test_record_evidence_explicit_hash_is_idempotent_even_for_different_payload(
    session: Session,
) -> None:
    content = {
        "evidence_type": "STATIC_ANALYSIS",
        "occurred_at": FIXED_AT,
        "source": "analyzer",
        "provenance": "verify://case/1",
        "artifact": "report.json",
        "machine_result": {"exit_code": 0, "findings": ["none"]},
    }
    digest = compute_content_hash(**content)

    first = record_evidence(session, content_hash=digest, **content)
    session.commit()

    again = record_evidence(
        session,
        evidence_type="STATIC_ANALYSIS",
        occurred_at=FIXED_AT,
        source="analyzer",
        provenance="verify://case/1",
        artifact="report.json",
        machine_result={"exit_code": 1, "findings": ["none"]},
        content_hash=digest,
    )
    assert again.id == first.id

    count = session.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.hash == digest)
    )
    assert count == 1


def test_eligibility_requires_exit_code_provenance_and_binding() -> None:
    passing = Evidence(
        type="TEST_RESULT",
        provenance="execution://run/7",
        machine_result={"exit_code": 0},
        hash="0" * 64,
        claim_id=uuid.uuid4(),
    )
    eligible, reasons = eligibility(passing)
    assert eligible is True
    assert reasons == []

    no_exit_code = Evidence(
        type="TEST_RESULT",
        provenance="execution://run/7",
        machine_result={"stdout": "output only"},
        hash="1" * 64,
        claim_id=uuid.uuid4(),
    )
    eligible, reasons = eligibility(no_exit_code)
    assert eligible is False
    assert "machine_result has no exit_code" in reasons

    empty_provenance = Evidence(
        type="TEST_RESULT",
        provenance="   ",
        machine_result={"exit_code": 0},
        hash="2" * 64,
        claim_id=uuid.uuid4(),
    )
    eligible, reasons = eligibility(empty_provenance)
    assert eligible is False
    assert "provenance is empty" in reasons

    no_binding = Evidence(
        type="TEST_RESULT",
        provenance="execution://run/7",
        machine_result={"exit_code": 0},
        hash="3" * 64,
    )
    eligible, reasons = eligibility(no_binding)
    assert eligible is False
    assert "no claim_id or verification_case_id binding" in reasons

    verification_case_binding = Evidence(
        type="TEST_RESULT",
        provenance="execution://run/7",
        machine_result={"exit_code": 0},
        hash="4" * 64,
        verification_case_id=uuid.uuid4(),
    )
    eligible, reasons = eligibility(verification_case_binding)
    assert eligible is True
    assert reasons == []


def test_evidence_lookup_by_hash_task_and_claim(session: Session) -> None:
    ctx = _seed_context(session)
    task = ctx["task"]
    assert isinstance(task, Task)

    ev1 = record_evidence(
        session,
        evidence_type=EvidenceType.TEST_RESULT,
        occurred_at=FIXED_AT,
        source="tests/test_auth.py",
        provenance="execution://run/7",
        artifact="a.json",
        machine_result={"exit_code": 0, "tests_passed": 42},
        task_id=task.id,
    )
    ev2 = record_evidence(
        session,
        evidence_type=EvidenceType.STATIC_ANALYSIS,
        occurred_at=FIXED_AT,
        source="analyzer",
        provenance="verify://case/1",
        artifact="b.json",
        machine_result={"exit_code": 0},
        task_id=task.id,
    )
    session.commit()

    claim = Claim(
        task=task, statement="Token refresh now rejects forged AUTH-017 requests"
    )
    session.add(claim)
    session.commit()

    ev3 = record_evidence(
        session,
        evidence_type=EvidenceType.METAMORPHIC_CHECK,
        occurred_at=FIXED_AT,
        source="verify",
        provenance="verify://case/9",
        artifact="c.json",
        machine_result={"exit_code": 0},
        claim_id=claim.id,
        task_id=task.id,
    )
    session.commit()

    assert evidence_by_hash(session, ev1.hash) is not None
    assert evidence_by_hash(session, ev1.hash).id == ev1.id
    assert evidence_by_hash(session, "f" * 64) is None

    task_rows = evidence_for_task(session, task.id)
    assert {row.id for row in task_rows} == {ev1.id, ev2.id, ev3.id}
    assert task_rows == sorted(task_rows, key=lambda e: (e.created_at, e.id))

    claim_rows = evidence_for_claim(session, claim.id)
    assert [row.id for row in claim_rows] == [ev3.id]


def test_provenance_path_returns_ordered_lineage(session: Session) -> None:
    ctx = _seed_context(session)
    task = ctx["task"]
    assert isinstance(task, Task)

    run = Run(task=task, kind="AGENT", status="RUNNING")
    agent_run = AgentRun(
        run=run,
        role="ORCHESTRATOR",
        model="nemotron",
        status="RUNNING",
        state="EXECUTING",
    )
    subagent_run = SubagentRun(agent_run=agent_run, name="verify")
    session.add_all([run, agent_run, subagent_run])
    session.commit()

    evidence = record_evidence(
        session,
        evidence_type=EvidenceType.EXECUTION_TRACE,
        occurred_at=FIXED_AT,
        source="nebius-sandbox-1",
        provenance="execution://run/7",
        artifact="trace.json",
        machine_result={"exit_code": 0, "stdout": "ok", "duration_ms": 42},
        task_id=task.id,
        run_id=run.id,
        agent_run_id=agent_run.id,
        subagent_run_id=subagent_run.id,
    )
    session.commit()

    path = provenance_path(evidence)
    assert path["ids"] == [
        evidence.id,
        task.id,
        run.id,
        agent_run.id,
        subagent_run.id,
    ]
    assert [node["kind"] for node in path["nodes"]] == [
        "evidence",
        "task",
        "run",
        "agent_run",
        "subagent_run",
    ]


def test_claim_evidence_chain_and_certificate_traversal(session: Session) -> None:
    ctx = _seed_context(session)
    task = ctx["task"]
    project = ctx["project"]
    assert isinstance(task, Task)
    assert isinstance(project, Project)

    claim = Claim(
        task=task,
        statement="Token refresh now rejects forged AUTH-017 requests",
        status="SUPPORTED",
    )
    session.add(claim)
    session.commit()

    ev1 = record_evidence(
        session,
        evidence_type=EvidenceType.DIFFERENTIAL_EXECUTION,
        occurred_at=FIXED_AT,
        source="verify",
        provenance="verify://case/12",
        artifact="v12.json",
        machine_result={"exit_code": 0},
        claim_id=claim.id,
        task_id=task.id,
    )
    ev2 = record_evidence(
        session,
        evidence_type=EvidenceType.ADVERSARIAL_SCENARIO,
        occurred_at=FIXED_AT,
        source="verify",
        provenance="verify://case/14",
        artifact="v14.json",
        machine_result={"exit_code": 1},
        claim_id=claim.id,
        task_id=task.id,
    )
    session.commit()

    delta = BehavioralDelta(
        metric="failed_requests",
        baseline_value="3",
        candidate_value="0",
        direction="DECREASED",
        category="SECURITY",
        observed=True,
        description="AUTH-017 failure path no longer reachable.",
    )
    certificate = Certificate(
        certificate_key="cert_" + "0" * 58,
        status="CERTIFIED",
        evidence_hash=ev1.hash,
        issued_at=FIXED_AT,
    )
    memory_update = MemoryUpdate(
        project=project,
        kind="BEHAVIORAL_MEMORY",
        summary="AUTH-017 refresh hardening learned.",
        content={"change": 184},
        applied=True,
    )
    session.add_all([delta, certificate, memory_update])
    session.flush()
    delta.task = task
    delta.claim = claim
    delta.evidence = ev1
    delta.certificate = certificate
    certificate.task = task
    certificate.claim = claim
    memory_update.certificate = certificate
    memory_update.task = task
    memory_update.evidence = ev1
    session.commit()

    chain = claim_evidence_chain(claim)
    assert {row.id for row in chain} == {ev1.id, ev2.id}
    assert chain == sorted(chain, key=lambda e: (e.created_at, e.id))
    assert all(row.claim_id == claim.id for row in chain)

    path = evidence_to_certificate_path(ev1)
    assert path["verdict"] == "CERTIFIED"
    assert [step["kind"] for step in path["steps"]] == [
        "evidence",
        "claim",
        "behavioral_delta",
        "certificate",
    ]
    assert path["steps"][2]["direction"] == "DECREASED"
    assert path["steps"][3]["status"] == "CERTIFIED"

    unlinked = record_evidence(
        session,
        evidence_type=EvidenceType.RUNTIME_OBSERVATION,
        occurred_at=FIXED_AT,
        source="sandbox-2",
        provenance="execution://run/9",
        artifact="observations.json",
        machine_result={"exit_code": 0},
    )
    session.commit()
    unlinked_path = evidence_to_certificate_path(unlinked)
    assert unlinked_path["verdict"] == "UNLINKED"
    assert [step["kind"] for step in unlinked_path["steps"]] == ["evidence"]

    binding = certificate_traversal(certificate)
    assert set(binding.keys()) == {
        "certificate",
        "claim",
        "deltas",
        "evidence",
        "memory_updates",
    }
    assert binding["certificate"]["certificate_key"] == certificate.certificate_key
    assert binding["certificate"]["status"] == "CERTIFIED"
    assert binding["claim"]["id"] == str(claim.id)
    assert binding["claim"]["statement"] == claim.statement
    assert {item["id"] for item in binding["evidence"]} == {
        str(ev1.id),
        str(ev2.id),
    }
    assert binding["evidence"][0]["hash"] in {ev1.hash, ev2.hash}
    assert [item["id"] for item in binding["deltas"]] == [str(delta.id)]
    assert binding["deltas"][0]["direction"] == "DECREASED"
    assert [item["id"] for item in binding["memory_updates"]] == [str(memory_update.id)]
    assert binding["memory_updates"][0]["kind"] == "BEHAVIORAL_MEMORY"

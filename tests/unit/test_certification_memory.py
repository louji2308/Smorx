"""Unit tests for the continuous memory pipeline (implementation plan phase 11,
section 11.8).

Covers the post-certification guard, the CERTIFICATION + FAILURE_ARCHAEOLOGY
memory updates (with preserved F-183 content, delta direction, certificate
key and a future_context note), idempotent get-or-create semantics,
``memory_for_task`` ordering, applied flags, observability events, the
``MemoryPipeline`` facade and the missing-certificate guard.  Every row is
built manually -- no dependency on the seed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.evidence.service import record_evidence
from smorx_behavior.models import (
    Base,
    Behavior,
    BehavioralDelta,
    CandidatePatch,
    Certificate,
    CertificateStatus,
    Change,
    Claim,
    ConsequentialEvent,
    EventKind,
    EvidenceType,
    Failure,
    FailureKind,
    Ghost,
    IntentAlignment,
    IntentAlignmentStatus,
    IntentItem,
    IntentLedger,
    MemoryKind,
    MemoryUpdate,
    Project,
    RepairPackage,
    RepairStatus,
    Repository,
    Severity,
    Task,
)
from smorx_behavior.repo.base import digest
from smorx_certification.archaeology import persist_archaeology
from smorx_certification.memory import (
    MemoryPipeline,
    memory_for_task,
    run_memory_pipeline,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

T0 = datetime(2026, 9, 13, 12, 0, 0, tzinfo=UTC)


@pytest.fixture()
def engine() -> object:
    eng = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: object) -> Session:
    with Session(engine) as sess:
        yield sess


def _ctx(
    session: Session, *, certificate_status: str = "CERTIFIED"
) -> dict[str, object]:
    """Build the AUTH-017 memory fixture graph and return key rows."""
    project = Project(name="Payments API", slug="payments-api")
    repository = Repository(project=project, name="smorx/payments-api")
    change = Change(
        repository=repository,
        external_id="184",
        title="AUTH-017 token refresh hardening",
        status="VERIFIED",
    )
    task = Task(
        project=project,
        repository=repository,
        change=change,
        title="AUTH-017 - token refresh must reject forged requests",
        status="VERIFIED",
    )
    behavior = Behavior(
        repository=repository,
        origin_change=change,
        name="auth token refresh",
        category="SECURITY",
        protected=True,
    )
    session.add_all([project, repository, change, task, behavior])
    session.flush()

    intent_ledger = IntentLedger(
        project=project, task=task, title="AUTH-017 ledger", status="SATISFIED"
    )
    session.add(intent_ledger)
    session.flush()
    intent_item = IntentItem(
        intent_ledger=intent_ledger,
        task=task,
        statement="token refresh MUST reject forged tokens",
        kind="CONSTRAINT",
        status="SATISFIED",
        authorized=True,
    )
    session.add(intent_item)
    session.flush()

    ghost = Ghost(
        repository=repository,
        behavior=behavior,
        source_change=change,
        name="Ghost #221",
        status="PASSED",
        payload={"scenario": "forged_refresh_rotation"},
    )
    session.add(ghost)
    session.flush()

    claim = Claim(
        task=task,
        statement="Token refresh rejects forged AUTH-017 requests",
        status="VERIFIED",
    )
    session.add(claim)
    session.flush()

    evidence_failure = record_evidence(
        session,
        evidence_type=EvidenceType.EXECUTION_TRACE,
        occurred_at=T0,
        source="nebius-sandbox",
        provenance="execution://run/1 -> failure F-183",
        artifact="trace.json",
        machine_result={"exit_code": 1, "failure": "F-183"},
        task_id=task.id,
    )
    evidence_test = record_evidence(
        session,
        evidence_type=EvidenceType.TEST_RESULT,
        occurred_at=T0,
        source="tests/test_auth.py",
        provenance="execution://run/2 -> claim",
        artifact="test.json",
        machine_result={"exit_code": 0, "tests_passed": 42},
        task_id=task.id,
        claim_id=claim.id,
    )
    evidence_binding = record_evidence(
        session,
        evidence_type=EvidenceType.CERTIFICATE_BINDING,
        occurred_at=T0,
        source="certification",
        provenance="certify://cert-binding <- claim",
        artifact="binding.json",
        machine_result={"ok": True, "exit_code": 0},
        task_id=task.id,
        claim_id=claim.id,
    )

    patch_1 = CandidatePatch(
        change=change,
        task=task,
        summary="Candidate #1: naive trust; F-183 observed",
        status="FAILED",
        candidate_index=1,
    )
    patch_2 = CandidatePatch(
        change=change,
        task=task,
        summary="Candidate #2: verifies signature and issuer",
        status="VERIFIED",
        candidate_index=2,
    )
    session.add_all([patch_1, patch_2])
    session.flush()

    failure = Failure(
        execution_id=None,
        task=task,
        run_id=None,
        candidate_patch=patch_1,
        evidence=evidence_failure,
        classification=FailureKind.F3_INTEGRATION.value,
        message="F-183: forged refresh token accepted; tenant claim trusted",
        probable_cause="candidate trusted payload claims without verifying signature",
        next_action="repair: verify signature and issuer before tenant wiring",
        severity=Severity.HIGH.value,
        iteration=1,
        resolved=True,
    )
    session.add(failure)
    session.flush()

    repair = RepairPackage(
        failure=failure,
        task=task,
        candidate_patch=patch_2,
        evidence=evidence_test,
        attempt=1,
        iteration=1,
        status=RepairStatus.REVERIFIED.value,
    )
    session.add(repair)
    session.flush()

    delta = BehavioralDelta(
        task=task,
        change=change,
        claim=claim,
        behavior=behavior,
        metric="forged_token_acceptance_rate",
        baseline_value="3/100",
        candidate_value="0/100",
        direction="DECREASED",
        category="SECURITY",
        observed=True,
    )
    alignment = IntentAlignment(
        intent_item=intent_item,
        task=task,
        claim=claim,
        change=change,
        status=IntentAlignmentStatus.ALIGNED.value,
        verdict="AUTHORIZED",
        score=0.99,
    )
    session.add_all([delta, alignment])
    session.flush()

    certificate_key = digest("test/cert/AUTH-017")[:64]
    certificate = Certificate(
        task=task,
        project=project,
        claim=claim,
        intent_alignment=alignment,
        certificate_key=certificate_key,
        status=certificate_status,
        evidence_hash=evidence_test.hash,
        issued_at=T0,
    )
    session.add(certificate)
    session.flush()
    delta.certificate = certificate
    session.flush()

    session.commit()
    return {
        "project": project,
        "task": task,
        "change": change,
        "ghost": ghost,
        "claim": claim,
        "failure": failure,
        "repair": repair,
        "patch_1": patch_1,
        "patch_2": patch_2,
        "evidence_failure": evidence_failure,
        "evidence_test": evidence_test,
        "evidence_binding": evidence_binding,
        "behavior": behavior,
        "certificate": certificate,
    }


def _archaeology(session: Session, ctx: dict[str, object]):
    return persist_archaeology(
        session,
        task=ctx["task"],
        failure_row=ctx["failure"],
        ghost_rows=[ctx["ghost"]],
        claim_rows=[ctx["claim"]],
        repair_packages=[ctx["repair"]],
        execution_evidence=[ctx["evidence_failure"]],
    )


def test_pipeline_refuses_non_certified_certificate(session: Session) -> None:
    ctx = _ctx(session, certificate_status=CertificateStatus.DRAFT.value)
    archaeology = _archaeology(session, ctx)

    result = run_memory_pipeline(
        session,
        certificate=ctx["certificate"],
        task=ctx["task"],
        change=ctx["change"],
        archaeology=archaeology,
    )
    session.flush()

    assert result.applied is False
    assert result.memory_update_ids == []
    assert "blocked" in result.summary
    assert result.certificate_id == ctx["certificate"].id

    cert_count = session.scalar(
        select(func.count())
        .select_from(MemoryUpdate)
        .where(
            MemoryUpdate.task_id == ctx["task"].id,
            MemoryUpdate.kind == MemoryKind.CERTIFICATION.value,
        )
    )
    assert cert_count == 0

    archaeology_row = (
        session.scalars(
            select(MemoryUpdate).where(
                MemoryUpdate.kind == MemoryKind.FAILURE_ARCHAEOLOGY.value,
                MemoryUpdate.task_id == ctx["task"].id,
            )
        )
    ).first()
    assert archaeology_row is not None
    assert archaeology_row.applied is False


def test_pipeline_creates_certification_and_archaeology_updates(
    session: Session,
) -> None:
    ctx = _ctx(session)
    archaeology = _archaeology(session, ctx)

    result = run_memory_pipeline(
        session,
        certificate=ctx["certificate"],
        task=ctx["task"],
        change=ctx["change"],
        archaeology=archaeology,
    )
    session.flush()

    assert result.applied is True
    assert len(result.memory_update_ids) == 2

    rows = list(
        session.scalars(
            select(MemoryUpdate)
            .where(MemoryUpdate.task_id == ctx["task"].id)
            .order_by(MemoryUpdate.created_at.asc(), MemoryUpdate.id.asc())
        )
    )
    assert len(rows) == 2
    kinds = {row.kind for row in rows}
    assert MemoryKind.CERTIFICATION.value in kinds
    assert MemoryKind.FAILURE_ARCHAEOLOGY.value in kinds

    certification = next(
        row for row in rows if row.kind == MemoryKind.CERTIFICATION.value
    )
    content = certification.content
    assert content["certificate_key"] == ctx["certificate"].certificate_key
    assert content["failure_code"] == "F-183"
    assert str(ctx["ghost"].id) in content["ghost_replay"]
    assert content["delta"]["metric"] == "forged_token_acceptance_rate"
    assert content["delta"]["direction"] == "DECREASED"
    assert "future_context" in content
    assert "F-183" in content["future_context"]
    assert content["certificate_status"] == "CERTIFIED"
    assert content["change"] == str(ctx["change"].id)

    archaeology_row = next(
        row for row in rows if row.kind == MemoryKind.FAILURE_ARCHAEOLOGY.value
    )
    assert archaeology_row.content["failure_code"] == "F-183"
    assert archaeology_row.content["message"] == ctx["failure"].message

    assert all(row.applied is True for row in rows)
    assert certification.evidence_id == ctx["evidence_binding"].id


def test_pipeline_is_idempotent(session: Session) -> None:
    ctx = _ctx(session)
    archaeology = _archaeology(session, ctx)

    first = run_memory_pipeline(
        session,
        certificate=ctx["certificate"],
        task=ctx["task"],
        change=ctx["change"],
        archaeology=archaeology,
    )
    session.flush()
    second = run_memory_pipeline(
        session,
        certificate=ctx["certificate"],
        task=ctx["task"],
        change=ctx["change"],
        archaeology=archaeology,
    )
    session.flush()

    assert first.memory_update_ids == second.memory_update_ids
    assert first.applied is True and second.applied is True

    count = session.scalar(
        select(func.count())
        .select_from(MemoryUpdate)
        .where(MemoryUpdate.task_id == ctx["task"].id)
    )
    assert count == 2


def test_pipeline_applies_existing_archaeology_summary(session: Session) -> None:
    ctx = _ctx(session)
    archaeology = _archaeology(session, ctx)
    session.flush()

    before = (
        session.scalars(
            select(MemoryUpdate).where(
                MemoryUpdate.kind == MemoryKind.FAILURE_ARCHAEOLOGY.value,
                MemoryUpdate.task_id == ctx["task"].id,
            )
        )
    ).first()
    assert before is not None
    assert before.applied is False

    run_memory_pipeline(
        session,
        certificate=ctx["certificate"],
        task=ctx["task"],
        change=ctx["change"],
        archaeology=archaeology,
    )
    session.flush()

    after = (
        session.scalars(
            select(MemoryUpdate).where(
                MemoryUpdate.kind == MemoryKind.FAILURE_ARCHAEOLOGY.value,
                MemoryUpdate.task_id == ctx["task"].id,
            )
        )
    ).first()
    assert after is not None
    assert after.applied is True


def test_memory_for_task_returns_ordered_rows(session: Session) -> None:
    ctx = _ctx(session)
    archaeology = _archaeology(session, ctx)
    run_memory_pipeline(
        session,
        certificate=ctx["certificate"],
        task=ctx["task"],
        change=ctx["change"],
        archaeology=archaeology,
    )
    session.flush()

    rows = memory_for_task(session, ctx["task"])
    assert len(rows) == 2
    assert rows == sorted(rows, key=lambda row: (row.created_at, row.id))


def test_pipeline_records_memory_update_events(session: Session) -> None:
    ctx = _ctx(session)
    archaeology = _archaeology(session, ctx)
    run_memory_pipeline(
        session,
        certificate=ctx["certificate"],
        task=ctx["task"],
        change=ctx["change"],
        archaeology=archaeology,
    )
    session.flush()

    events = list(
        session.scalars(
            select(ConsequentialEvent).where(
                ConsequentialEvent.task_id == ctx["task"].id,
                ConsequentialEvent.event_type == EventKind.MEMORY_UPDATE.value,
            )
        )
    )
    assert len(events) == 2
    assert all(e.entity_type == "MemoryUpdate" for e in events)
    payloads = {e.payload.get("kind") for e in events}
    assert MemoryKind.CERTIFICATION.value in payloads
    assert MemoryKind.FAILURE_ARCHAEOLOGY.value in payloads
    assert all(e.payload.get("applied") is True for e in events)


def test_pipeline_raises_without_certificate(session: Session) -> None:
    ctx = _ctx(session)
    archaeology = _archaeology(session, ctx)
    with pytest.raises(ValueError, match="requires a real Certificate"):
        run_memory_pipeline(
            session,
            certificate=None,
            task=ctx["task"],
            change=ctx["change"],
            archaeology=archaeology,
        )


def test_memory_pipeline_facade(session: Session) -> None:
    ctx = _ctx(session)
    archaeology = _archaeology(session, ctx)

    pipeline = MemoryPipeline(session)
    result = pipeline.run(
        certificate=ctx["certificate"],
        task=ctx["task"],
        archaeology=archaeology,
    )

    assert result.applied is True
    assert len(result.memory_update_ids) == 2

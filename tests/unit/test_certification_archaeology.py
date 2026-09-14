"""Unit tests for failure archaeology (implementation plan phase 11, section 11.4).

Covers read-only preservation of the original failure history, honest gap
reporting for missing references, linking of Ghost/Claim/RepairPackage/Evidence
rows, observability events (FAILURE_CLASSIFIED, REPAIR, REVERIFICATION), the
unapplied FAILURE_ARCHAEOLOGY memory summary, and the missing-failure guard.
Uses the deterministic demo scenario tokens (F-183, Ghost #221) for fixture
familiarity but builds every row manually with no dependency on the seed.
"""

from __future__ import annotations

import uuid
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
from smorx_certification.archaeology import (
    archaeology_memory_key,
    persist_archaeology,
)
from sqlalchemy import select
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


def _ctx(session: Session) -> dict[str, object]:
    """Build the AUTH-017 archaeology fixture graph and return key rows."""
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
    evidence_decision = record_evidence(
        session,
        evidence_type=EvidenceType.MODEL_DECISION,
        occurred_at=T0,
        source="nemotron",
        provenance="model://orchestrator/decision-3",
        artifact="decision.json",
        machine_result={"decision": "repair required for F-183"},
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
    evidence_ghost = record_evidence(
        session,
        evidence_type=EvidenceType.HISTORICAL_GHOST_REPLAY,
        occurred_at=T0,
        source="verify",
        provenance="verify://ghost-221 -> claim",
        artifact="ghost.json",
        machine_result={"exit_code": 0},
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
        evidence=evidence_decision,
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

    certificate = Certificate(
        task=task,
        project=project,
        claim=claim,
        intent_alignment=alignment,
        certificate_key=digest("test/cert/AUTH-017")[:64],
        status="CERTIFIED",
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
        "evidence_decision": evidence_decision,
        "evidence_test": evidence_test,
        "evidence_ghost": evidence_ghost,
        "evidence_binding": evidence_binding,
        "behavior": behavior,
        "certificate": certificate,
    }


def test_persist_archaeology_preserves_original_failure_history(
    session: Session,
) -> None:
    ctx = _ctx(session)
    failure = ctx["failure"]
    assert isinstance(failure, Failure)

    original_message = failure.message
    original_classification = failure.classification
    original_cause = failure.probable_cause
    original_action = failure.next_action
    original_severity = failure.severity
    original_resolved = failure.resolved

    persist_archaeology(
        session,
        task=ctx["task"],
        failure_row=failure,
        ghost_rows=[ctx["ghost"]],
        claim_rows=[ctx["claim"]],
        repair_packages=[ctx["repair"]],
        execution_evidence=[ctx["evidence_failure"], ctx["evidence_decision"]],
    )
    session.flush()

    assert failure.message == original_message
    assert failure.classification == original_classification
    assert failure.probable_cause == original_cause
    assert failure.next_action == original_action
    assert failure.severity == original_severity
    assert failure.resolved == original_resolved


def test_persist_archaeology_links_ghost_claims_repairs_evidence(
    session: Session,
) -> None:
    ctx = _ctx(session)
    record = persist_archaeology(
        session,
        task=ctx["task"],
        failure_row=ctx["failure"],
        ghost_rows=[ctx["ghost"]],
        claim_rows=[ctx["claim"]],
        repair_packages=[ctx["repair"]],
        execution_evidence=[ctx["evidence_failure"], ctx["evidence_decision"]],
    )
    session.flush()

    assert record.failure_id == ctx["failure"].id
    assert record.failure_code == "F-183"
    assert record.classification == FailureKind.F3_INTEGRATION.value
    assert record.ghost_ids == [str(ctx["ghost"].id)]
    assert record.claim_ids == [str(ctx["claim"].id)]
    assert record.repair_package_ids == [str(ctx["repair"].id)]

    evidence_ids = set(record.evidence_ids)
    assert str(ctx["evidence_failure"].id) in evidence_ids
    assert str(ctx["evidence_decision"].id) in evidence_ids
    assert str(ctx["failure"].evidence_id) in evidence_ids

    verification_ids = set(record.verification_evidence_ids)
    assert str(ctx["evidence_test"].id) in verification_ids
    assert str(ctx["evidence_ghost"].id) in verification_ids
    assert str(ctx["evidence_binding"].id) in verification_ids

    d = record.to_dict()
    assert d["failure_code"] == "F-183"
    assert d["resolved"] is True
    assert d["gaps"] == {}


def test_persist_archaeology_reports_missing_references_as_gaps(
    session: Session,
) -> None:
    ctx = _ctx(session)
    phantom_ghost = uuid.uuid4()
    phantom_evidence = uuid.uuid4()

    record = persist_archaeology(
        session,
        task=ctx["task"],
        failure_row=ctx["failure"],
        ghost_rows=[phantom_ghost],
        claim_rows=[],
        repair_packages=[],
        execution_evidence=[phantom_evidence],
    )
    session.flush()

    assert record.ghost_ids == []
    assert str(phantom_ghost) in record.gaps.get("ghost_ids", [])
    assert str(phantom_evidence) in record.gaps.get("evidence_ids", [])
    assert str(phantom_evidence) not in record.evidence_ids


def test_persist_archaeology_records_observability_events(session: Session) -> None:
    ctx = _ctx(session)
    persist_archaeology(
        session,
        task=ctx["task"],
        failure_row=ctx["failure"],
        ghost_rows=[ctx["ghost"]],
        claim_rows=[ctx["claim"]],
        repair_packages=[ctx["repair"]],
        execution_evidence=[ctx["evidence_failure"], ctx["evidence_decision"]],
    )
    session.flush()

    events = list(
        session.scalars(
            select(ConsequentialEvent)
            .where(
                ConsequentialEvent.task_id == ctx["task"].id,
                ConsequentialEvent.entity_id == ctx["failure"].id,
                ConsequentialEvent.entity_type == "Failure",
            )
            .order_by(ConsequentialEvent.sequence.asc())
        )
    )
    event_types = {e.event_type for e in events}
    assert EventKind.FAILURE_CLASSIFIED.value in event_types
    assert EventKind.REPAIR.value in event_types
    assert EventKind.REVERIFICATION.value in event_types
    assert all(e.entity_type == "Failure" for e in events)
    assert all(e.entity_id == ctx["failure"].id for e in events)


def test_persist_archaeology_raises_when_failure_missing(session: Session) -> None:
    ctx = _ctx(session)
    with pytest.raises(ValueError, match="failure_row is None"):
        persist_archaeology(
            session,
            task=ctx["task"],
            failure_row=None,
            ghost_rows=[],
            claim_rows=[],
            repair_packages=[],
            execution_evidence=[],
        )


def test_persist_archaeology_writes_unapplied_memory_summary(session: Session) -> None:
    ctx = _ctx(session)
    record = persist_archaeology(
        session,
        task=ctx["task"],
        failure_row=ctx["failure"],
        ghost_rows=[ctx["ghost"]],
        claim_rows=[ctx["claim"]],
        repair_packages=[ctx["repair"]],
        execution_evidence=[ctx["evidence_failure"]],
    )
    session.flush()

    row = (
        session.scalars(
            select(MemoryUpdate).where(
                MemoryUpdate.kind == MemoryKind.FAILURE_ARCHAEOLOGY.value,
                MemoryUpdate.task_id == ctx["task"].id,
            )
        )
    ).first()
    assert row is not None
    assert row.applied is False
    assert row.content["failure_code"] == "F-183"
    assert row.content["resolved"] is True
    assert str(ctx["ghost"].id) in row.content["ghost_ids"]
    assert row.memory_ref == archaeology_memory_key(record)

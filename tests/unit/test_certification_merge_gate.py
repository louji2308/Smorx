"""Unit tests for the merge authorization gate (implementation plan phase 11,
section 11.7).

Every row is built manually and the certificate is rebound against the real
``smorx_certification.integrity`` module so the gate's PASS path is verified
end to end (real ``verify_certificate_integrity``, real canonical payload,
real integrity hash).  The "modules unavailable" case is exercised by halting
the integrity import (``None`` in ``sys.modules``), which is the documented
CPython mechanism for an unimplementable/missing module -- the gate must
degrade to ``allowed=False`` instead of raising.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import (
    Behavior,
    BehavioralDelta,
    CandidatePatch,
    Certificate,
    Change,
    Claim,
    ConsequentialEvent,
    EventKind,
    Evidence,
    EvidenceType,
    IntentAlignment,
    IntentAlignmentStatus,
    IntentItem,
    IntentLedger,
    Project,
    Repository,
    Task,
    TaskStatus,
)
from smorx_behavior.repo.base import digest
from smorx_certification.integrity import (
    canonical_certificate_payload,
    compute_integrity_hash,
)
from smorx_certification.merge_gate import (
    MergeGateVerdict,
    evaluate_merge_gate,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

INTEGRITY_MODULE = "smorx_certification.integrity"


class _AlignmentVerdict:
    """Minimal stand-in for the alignment module's verdict object."""

    def __init__(
        self,
        *,
        aligned: bool = True,
        status: str = "CERTIFIABLE",
        protected_behaviors: list[str] | None = None,
    ) -> None:
        self.aligned = aligned
        self.status = status
        self.protected_behaviors = list(protected_behaviors or [])


@pytest.fixture()
def engine() -> Any:
    eng = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: Any) -> Iterator[Session]:
    with Session(engine) as sess:
        yield sess


def _rebind_certificate_integrity(session: Session, certificate: Certificate) -> None:
    """Recompute the certificate's canonical payload, hash, and key so the real
    integrity verifier accepts it."""
    canonical = canonical_certificate_payload(session, certificate)
    certificate.payload = dict(canonical)
    certificate.evidence_hash = compute_integrity_hash(canonical)
    assert certificate.task_id is not None
    assert certificate.claim_id is not None
    certificate.certificate_key = digest(
        "certificate", str(certificate.task_id), str(certificate.claim_id)
    )[:64]
    session.flush()


def _ctx(
    session: Session,
    *,
    candidate_status: str = "VERIFIED",
    certificate_status: str = "CERTIFIED",
    intent_authorized: bool = True,
) -> dict[str, Any]:
    """Build the AUTH-017 merge-gate fixture graph and return key rows."""
    project = Project(name="Payments API", slug="payments-api")
    repository = Repository(project=project, name="smorx/payments-api")
    change = Change(
        repository=repository,
        external_id="184",
        commit_sha="a1b2c3d4e5f6",
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
        signature="auth/token/refresh",
    )
    session.add_all([project, repository, change, task, behavior])
    session.flush()

    intent_ledger = IntentLedger(
        project=project, task=task, title="AUTH-017 ledger", status="SATISFIED"
    )
    intent_item = IntentItem(
        intent_ledger=intent_ledger,
        task=task,
        statement="token refresh MUST reject forged tokens",
        kind="CONSTRAINT",
        status="SATISFIED",
        authorized=intent_authorized,
    )
    claim = Claim(
        task=task,
        statement="Token refresh rejects forged AUTH-017 requests",
        status="VERIFIED",
    )
    session.add_all([intent_ledger, intent_item, claim])
    session.flush()

    evidence = Evidence(
        task_id=task.id,
        claim_id=claim.id,
        type=EvidenceType.TEST_RESULT.value,
        source="pytest",
        artifact="artifacts/auth-017/report.json",
        provenance="verify://ghost-221 -> claim",
        machine_result={"tests_passed": 42, "tests_failed": 0, "exit_code": 0},
        hash=digest("test/evidence/AUTH-017")[:64],
    )
    session.add(evidence)
    session.flush()

    alignment = IntentAlignment(
        intent_item=intent_item,
        task=task,
        claim=claim,
        change=change,
        status=IntentAlignmentStatus.ALIGNED.value,
        verdict="AUTHORIZED",
        score=0.99,
    )
    session.add(alignment)
    session.flush()

    delta = BehavioralDelta(
        task=task,
        change=change,
        claim=claim,
        behavior=behavior,
        evidence=evidence,
        metric="forged_token_acceptance_rate",
        baseline_value="3 failures / 100 attempts",
        candidate_value="0 / 100",
        magnitude=3.0,
        direction="DECREASED",
        category="SECURITY",
        description="Forged refresh tokens rejected after repair.",
        observed=True,
        owner_scope="OBSERVED_DIFFERENCE",
    )
    session.add(delta)
    session.flush()

    certificate = Certificate(
        task=task,
        project=project,
        claim=claim,
        certificate_key=digest("test/cert/AUTH-017")[:64],
        status=certificate_status,
        owner_scope="CERTIFICATION",
        payload={},
    )
    session.add(certificate)
    session.flush()

    delta.certificate = certificate
    session.flush()

    candidate = CandidatePatch(
        change=change,
        task=task,
        summary="Candidate #2: verifies signature and issuer",
        status=candidate_status,
        candidate_index=2,
    )
    session.add(candidate)
    session.flush()

    _rebind_certificate_integrity(session, certificate)

    session.commit()
    return {
        "project": project,
        "task": task,
        "change": change,
        "behavior": behavior,
        "certificate": certificate,
        "candidate": candidate,
        "alignment": alignment,
    }


_UNSET = object()


def _verdict(
    session: Session,
    ctx: dict[str, Any],
    *,
    alignment: _AlignmentVerdict | None = None,
    protected_behaviors: list[Any] | None = None,
    certificate: Certificate | None = _UNSET,  # type: ignore[assignment]
    candidate: CandidatePatch | None = None,
) -> MergeGateVerdict:
    return evaluate_merge_gate(
        session,
        certificate=(ctx["certificate"] if certificate is _UNSET else certificate),
        alignment_verdict=alignment or _AlignmentVerdict(),
        candidate_patch=ctx["candidate"] if candidate is None else candidate,
        protected_behaviors=(
            protected_behaviors
            if protected_behaviors is not None
            else [ctx["behavior"].id]
        ),
    )


def test_merge_gate_denies_missing_certificate(session: Session) -> None:
    ctx = _ctx(session)

    verdict = _verdict(session, ctx, certificate=None)

    assert verdict.allowed is False
    assert verdict.reason == "no certificate"
    assert verdict.allowed is not True
    assert ctx["task"].status == "VERIFIED"
    assert ctx["change"].status == "VERIFIED"
    assert _merge_events(session, ctx["task"].id) == []


def test_merge_gate_denies_failed_candidate(session: Session) -> None:
    ctx = _ctx(session, candidate_status="FAILED")

    verdict = _verdict(session, ctx)

    assert verdict.allowed is False
    assert verdict.checks["candidate_verified"] is False
    assert verdict.checks["certificate_certified"] is True
    assert ctx["task"].status == "VERIFIED"
    assert _merge_events(session, ctx["task"].id) == []


def test_merge_gate_denies_when_integrity_modules_unavailable(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _ctx(session)
    monkeypatch.setitem(sys.modules, INTEGRITY_MODULE, None)

    verdict = _verdict(session, ctx)

    assert verdict.allowed is False
    assert verdict.reason == "certification modules unavailable"
    assert verdict.checks["integrity_intact"] is False
    assert ctx["task"].status == "VERIFIED"
    assert _merge_events(session, ctx["task"].id) == []


def test_merge_gate_passes_and_performs_merge_transition(session: Session) -> None:
    ctx = _ctx(session)

    verdict = _verdict(session, ctx)

    assert verdict.allowed is True
    assert all(verdict.checks.values())
    assert ctx["task"].status == TaskStatus.MERGED.value
    assert ctx["change"].status == "MERGED"
    events = _merge_events(session, ctx["task"].id)
    assert len(events) == 1
    event = events[0]
    assert event.entity_type == "Task"
    assert event.entity_id == ctx["task"].id
    assert event.payload["certificate_key"] == ctx["certificate"].certificate_key
    assert event.payload["change_status"] == "MERGED"


def test_merge_gate_denies_when_integrity_tampered(session: Session) -> None:
    ctx = _ctx(session)
    payload = dict(ctx["certificate"].payload)
    payload["change"] = {"id": "tampered", "title": "forged refresh accepted"}
    ctx["certificate"].payload = payload
    session.flush()

    verdict = _verdict(session, ctx)

    assert verdict.allowed is False
    assert verdict.checks["integrity_intact"] is False
    assert verdict.checks["certificate_certified"] is True
    assert ctx["task"].status == "VERIFIED"
    assert _merge_events(session, ctx["task"].id) == []


def test_merge_gate_denies_when_alignment_not_certifiable(session: Session) -> None:
    ctx = _ctx(session)

    not_aligned = _verdict(session, ctx, alignment=_AlignmentVerdict(aligned=False))
    assert not_aligned.allowed is False
    assert not_aligned.checks["alignment_certifiable"] is False

    non_certifiable = _verdict(
        session, ctx, alignment=_AlignmentVerdict(status="NON_CERTIFIABLE")
    )
    assert non_certifiable.allowed is False
    assert non_certifiable.checks["alignment_certifiable"] is False

    assert ctx["task"].status == "VERIFIED"
    assert _merge_events(session, ctx["task"].id) == []


def test_merge_gate_denies_when_protected_behavior_not_authorized(
    session: Session,
) -> None:
    ctx = _ctx(session, intent_authorized=False)

    verdict = _verdict(session, ctx)

    assert verdict.allowed is False
    assert verdict.checks["protected_authorized"] is False
    assert verdict.checks["certificate_certified"] is True
    assert ctx["task"].status == "VERIFIED"
    assert _merge_events(session, ctx["task"].id) == []


def test_merge_gate_denies_when_behavior_not_covered_by_alignment_verdict(
    session: Session,
) -> None:
    ctx = _ctx(session)
    other_behavior = uuid.uuid4()

    verdict = _verdict(
        session,
        ctx,
        alignment=_AlignmentVerdict(protected_behaviors=[str(other_behavior)]),
    )

    assert verdict.allowed is False
    assert verdict.checks["protected_authorized"] is False
    assert ctx["task"].status == "VERIFIED"
    assert _merge_events(session, ctx["task"].id) == []


def test_merge_gate_no_mutation_on_deny(session: Session) -> None:
    ctx = _ctx(session, candidate_status="FAILED")

    before_task = ctx["task"].status
    before_change = ctx["change"].status
    _verdict(session, ctx)
    session.flush()

    assert ctx["task"].status == before_task
    assert ctx["change"].status == before_change
    assert _merge_events(session, ctx["task"].id) == []


def _merge_events(session: Session, task_id: uuid.UUID) -> list[ConsequentialEvent]:
    return list(
        session.scalars(
            select(ConsequentialEvent).where(
                ConsequentialEvent.task_id == task_id,
                ConsequentialEvent.event_type == EventKind.MERGE.value,
            )
        )
    )

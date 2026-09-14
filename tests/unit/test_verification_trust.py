"""Pure-data and trust tests for the phase-9 verification package.

Covers the immutable contracts (claim classification, evidence records,
verification result), the trust boundary, evidence collection persistence,
claim-evidence fusion, the control-center read model, and the adversarial
registry contract. These tests never exercise real subprocess execution.
"""

from __future__ import annotations

import uuid

import pytest
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.evidence.service import eligibility
from smorx_behavior.models import Base, Evidence
from smorx_verification.adversarial import ADVERSARIAL_CASES
from smorx_verification.boundary import (
    TrustBoundaryError,
    VerificationActor,
    authorize_verification_actor,
    guard_candidate_mutation,
)
from smorx_verification.contracts import (
    ClaimAssessment,
    Contradiction,
    EvidenceRecord,
    ModuleOutcome,
    ModuleStatus,
    ModuleType,
    VerificationResult,
    classify_claim,
)
from smorx_verification.control_center import ControlCenterModel
from smorx_verification.evidence import EvidenceCollector
from smorx_verification.fusion import fuse_claim_evidence, modules_passed
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture()
def engine() -> object:
    eng = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: object) -> Session:
    with Session(engine) as sess:
        yield sess


def test_classify_claim_truth_table() -> None:
    assert classify_claim(supporting=0, contradicting=0) == ClaimAssessment.INSUFFICIENT
    assert classify_claim(supporting=1, contradicting=0) == ClaimAssessment.SUPPORTING
    assert (
        classify_claim(supporting=0, contradicting=1) == ClaimAssessment.CONTRADICTING
    )
    assert classify_claim(supporting=1, contradicting=1) == ClaimAssessment.CONFLICTING
    assert (
        classify_claim(supporting=2, contradicting=1, warnings=1)
        == ClaimAssessment.CONFLICTING
    )


def test_classify_claim_warnings_without_evidence_is_supporting() -> None:
    assert (
        classify_claim(supporting=0, contradicting=0, warnings=1)
        == ClaimAssessment.SUPPORTING
    )


def test_evidence_record_as_dict_contract() -> None:
    claim_id = uuid.uuid4()
    record = EvidenceRecord(
        evidence_type=ModuleType.STATIC_ANALYSIS,
        claim_id=claim_id,
        source="analyzer",
        provenance="verify://case/7",
        artifact="report.json",
        machine_result={"exit_code": 0, "findings": []},
        exit_code=0,
        severity="INFO",
        module_status="ELIGIBLE",
    )
    data = record.as_dict()
    assert data["evidence_type"] == "STATIC_ANALYSIS"
    assert isinstance(data["evidence_type"], str)
    assert data["claim_id"] == str(claim_id)
    assert data["machine_result"] == {"exit_code": 0, "findings": []}
    assert data["module_status"] == "ELIGIBLE"
    assert data["evidence_id"] == str(record.evidence_id)
    assert data["provenance"] == "verify://case/7"
    assert data["exit_code"] == 0
    assert data["severity"] == "INFO"


def test_evidence_record_as_dict_with_plain_string_type() -> None:
    record = EvidenceRecord(
        evidence_type="ADVERSARIAL_SCENARIO",
        claim_id=uuid.uuid4(),
        source="verify",
        provenance="verify://case/22",
        artifact="ADV-22",
        machine_result={"exit_code": 0},
        exit_code=0,
        severity="INFO",
        module_status="ELIGIBLE",
    )
    assert record.as_dict()["evidence_type"] == "ADVERSARIAL_SCENARIO"


def test_authorize_verification_actor_distinct_ids() -> None:
    actor = authorize_verification_actor(
        actor_run_id="VERIFIER-RUN-1", source_agent_run_id="CODING-RUN-1"
    )
    assert isinstance(actor, VerificationActor)
    assert actor.actor_run_id == "VERIFIER-RUN-1"
    assert actor.source_agent_run_id == "CODING-RUN-1"
    assert actor.role == "INDEPENDENT_VERIFIER"


def test_authorize_verification_actor_rejects_empty_run_id() -> None:
    with pytest.raises(TrustBoundaryError):
        authorize_verification_actor(actor_run_id="   ", source_agent_run_id=None)


def test_authorize_verification_actor_rejects_source_inheritance() -> None:
    with pytest.raises(TrustBoundaryError, match="never inherits coding authority"):
        authorize_verification_actor(actor_run_id="RUN-X", source_agent_run_id="RUN-X")


def test_guard_candidate_mutation_blocks_unauthorized() -> None:
    actor = authorize_verification_actor(
        actor_run_id="VERIFIER-RUN-1", source_agent_run_id="CODING-RUN-1"
    )
    with pytest.raises(TrustBoundaryError, match="without authorization"):
        guard_candidate_mutation(candidate_id="CAND-9", authorized=False, actor=actor)


def test_guard_candidate_mutation_passes_when_authorized() -> None:
    actor = authorize_verification_actor(
        actor_run_id="VERIFIER-RUN-1", source_agent_run_id="CODING-RUN-1"
    )
    assert (
        guard_candidate_mutation(candidate_id="CAND-9", authorized=True, actor=actor)
        is None
    )


def test_evidence_collector_emit_persists_eligible_record(session: Session) -> None:
    claim_id = uuid.uuid4()
    run_id = uuid.uuid4()
    collector = EvidenceCollector(
        session=session, run_id=str(run_id), source="verifier"
    )
    record = collector.emit(
        module_type=ModuleType.STATIC_ANALYSIS,
        claim_id=claim_id,
        source="smorx_verification.static_analysis",
        provenance="verify://case/7",
        machine_result={"exit_code": 0, "findings": []},
        exit_code=0,
        severity="INFO",
    )
    assert record.module_status == "ELIGIBLE"
    assert len(collector.records) == 1
    assert collector.records[0] is record

    row = session.scalar(select(Evidence).where(Evidence.id == record.evidence_id))
    assert row is not None
    assert row.claim_id == claim_id
    assert row.provenance == "verify://case/7"
    assert row.machine_result["exit_code"] == 0
    admissible, reasons = eligibility(row)
    assert admissible is True
    assert reasons == []


def test_evidence_collector_emit_without_claim_binding_is_ineligible() -> None:
    orphan = Evidence(
        type="STATIC_ANALYSIS",
        provenance="verify://case/7",
        machine_result={"exit_code": 0},
        hash="ab" * 32,
    )
    admissible, reasons = eligibility(orphan)
    assert admissible is False
    assert "no claim_id or verification_case_id binding" in reasons


def _record(
    claim_id: uuid.UUID,
    *,
    evidence_type: ModuleType = ModuleType.DIFFERENTIAL_EXECUTION,
    exit_code: int = 0,
    severity: str = "INFO",
    module_status: str = "ELIGIBLE",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_type=evidence_type,
        claim_id=claim_id,
        source="verify",
        provenance="verify://case/1",
        artifact="",
        machine_result={"exit_code": exit_code},
        exit_code=exit_code,
        severity=severity,
        module_status=module_status,
    )


def test_fusion_high_severity_contradicts() -> None:
    claim_id = uuid.uuid4()
    verdicts, addressed, contradictions = fuse_claim_evidence(
        (_record(claim_id, severity="HIGH"),), claim_ids=(claim_id,)
    )
    assert verdicts[str(claim_id)] == ClaimAssessment.CONTRADICTING
    assert len(contradictions) == 0
    assert addressed[0].supports is False


def test_fusion_nonzero_exit_contradicts() -> None:
    claim_id = uuid.uuid4()
    verdicts, addressed, _contradictions = fuse_claim_evidence(
        (_record(claim_id, exit_code=1),), claim_ids=(claim_id,)
    )
    assert verdicts[str(claim_id)] == ClaimAssessment.CONTRADICTING
    assert addressed[0].supports is False


def test_fusion_clean_record_supports() -> None:
    claim_id = uuid.uuid4()
    verdicts, addressed, contradictions = fuse_claim_evidence(
        (_record(claim_id),), claim_ids=(claim_id,)
    )
    assert verdicts[str(claim_id)] == ClaimAssessment.SUPPORTING
    assert len(contradictions) == 0
    assert addressed[0].supports is True
    assert addressed[0].confidence > 0.0


def test_fusion_no_records_is_insufficient() -> None:
    claim_id = uuid.uuid4()
    verdicts, addressed, contradictions = fuse_claim_evidence((), claim_ids=(claim_id,))
    assert verdicts[str(claim_id)] == ClaimAssessment.INSUFFICIENT
    assert addressed == ()
    assert contradictions == ()


def test_fusion_supporting_and_contradicting_conflicts() -> None:
    claim_id = uuid.uuid4()
    verdicts, _addressed, contradictions = fuse_claim_evidence(
        (
            _record(
                claim_id,
                evidence_type=ModuleType.DIFFERENTIAL_EXECUTION,
                exit_code=0,
                severity="INFO",
            ),
            _record(
                claim_id,
                evidence_type=ModuleType.HISTORICAL_GHOST_REPLAY,
                exit_code=0,
                severity="CRITICAL",
            ),
        ),
        claim_ids=(claim_id,),
    )
    assert verdicts[str(claim_id)] == ClaimAssessment.CONFLICTING
    assert len(contradictions) == 1
    contradiction = contradictions[0]
    assert contradiction.claim_id == claim_id
    assert contradiction.supporting == ("DIFFERENTIAL_EXECUTION",)
    assert contradiction.contradicting == ("HISTORICAL_GHOST_REPLAY",)


def test_fusion_ineligible_no_claim_binding_contributes_no_support() -> None:
    claim_id = uuid.uuid4()
    verdicts, addressed, contradictions = fuse_claim_evidence(
        (
            _record(
                claim_id,
                evidence_type=ModuleType.METAMORPHIC_CHECK,
                exit_code=0,
                severity="INFO",
                module_status="INELIGIBLE:NO_CLAIM_BINDING",
            ),
        ),
        claim_ids=(claim_id,),
    )
    assert addressed[0].supports is False
    assert addressed[0].confidence == 0.0
    assert verdicts[str(claim_id)] != ClaimAssessment.SUPPORTING
    assert contradictions == ()


def _outcome(status: ModuleStatus) -> ModuleOutcome:
    return ModuleOutcome(
        module_type=ModuleType.STATIC_ANALYSIS, status=status, summary=""
    )


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ((ModuleStatus.PASSED, ModuleStatus.PASSED), True),
        ((ModuleStatus.PASSED, ModuleStatus.SKIPPED), True),
        ((ModuleStatus.SKIPPED,), True),
        ((ModuleStatus.PASSED, ModuleStatus.FAILED), False),
        ((ModuleStatus.PASSED, ModuleStatus.BLOCKED), False),
        ((ModuleStatus.FAILED,), False),
        ((ModuleStatus.BLOCKED,), False),
    ],
)
def test_modules_passed_matrix(
    statuses: tuple[ModuleStatus, ...], expected: bool
) -> None:
    assert modules_passed(tuple(_outcome(status) for status in statuses)) is expected


def _build_result(*, state: str) -> VerificationResult:
    claim_id = uuid.uuid4()
    record = EvidenceRecord(
        evidence_type=ModuleType.ADVERSARIAL_SCENARIO,
        claim_id=claim_id,
        source="verify",
        provenance="verify://case/ADV-22",
        artifact="ADV-22",
        machine_result={"exit_code": 0, "verdict": "BLOCKED"},
        exit_code=0,
        severity="INFO",
        module_status="ELIGIBLE",
    )
    return VerificationResult(
        candidate_id="CAND-1",
        verification_plan_id=uuid.uuid4(),
        plan_version=3,
        run_id="RUN-1",
        change_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        modules=(_outcome(ModuleStatus.PASSED),),
        evidence=(record,),
        claims={str(claim_id): ClaimAssessment.SUPPORTING},
        contradictions=(
            Contradiction(
                claim_id=claim_id,
                supporting=("ADVERSARIAL_SCENARIO",),
                contradicting=("DIFFERENTIAL_EXECUTION",),
                detail="tension observed",
            ),
        ),
        state=state,
    )


def test_control_center_completed_is_independent() -> None:
    result = _build_result(state="COMPLETED")
    model = ControlCenterModel.build(result)
    assert model.overall_passed is True
    assert model.trust_boundary == "VERIFIER_INDEPENDENT"
    assert model.evidence_count == 1
    assert model.module_states == {"STATIC_ANALYSIS": "PASSED"}

    claim_id = result.evidence[0].claim_id
    assert model.claim_verdicts == {str(claim_id): "SUPPORTING"}

    data = model.as_dict()
    assert data["state"] == "COMPLETED"
    assert data["overall_passed"] is True
    assert data["trust_boundary"] == "VERIFIER_INDEPENDENT"
    assert data["claims"] == {str(claim_id): "SUPPORTING"}
    assert data["contradictions"][0]["claim_id"] == str(claim_id)
    assert data["contradictions"][0]["supporting"] == ["ADVERSARIAL_SCENARIO"]
    assert data["contradictions"][0]["contradicting"] == ["DIFFERENTIAL_EXECUTION"]
    assert data["evidence_count"] == 1
    assert data["run"]["candidate_id"] == "CAND-1"


@pytest.mark.parametrize("state", ["BLOCKED", "INSUFFICIENT_EVIDENCE"])
def test_control_center_non_completed_is_incomplete(state: str) -> None:
    model = ControlCenterModel.build(_build_result(state=state))
    assert model.overall_passed is False
    assert model.trust_boundary == "VERIFICATION_INCOMPLETE"
    assert model.as_dict()["overall_passed"] is False
    assert model.as_dict()["trust_boundary"] == "VERIFICATION_INCOMPLETE"


def test_adversarial_registry_contract() -> None:
    assert len(ADVERSARIAL_CASES) == 22
    ids = {case["case_id"] for case in ADVERSARIAL_CASES}
    assert ids == {f"ADV-{index:02d}" for index in range(1, 23)}
    must_block_ids = {
        case["case_id"] for case in ADVERSARIAL_CASES if case["must_block"]
    }
    assert must_block_ids == {
        "ADV-08",
        "ADV-13",
        "ADV-14",
        "ADV-15",
        "ADV-16",
        "ADV-20",
        "ADV-22",
    }
    for case in ADVERSARIAL_CASES:
        assert set(case) == {"case_id", "kind", "title", "must_block", "details"}
        assert isinstance(case["case_id"], str)
        assert isinstance(case["kind"], str)
        assert isinstance(case["title"], str)
        assert isinstance(case["must_block"], bool)
        assert isinstance(case["details"], str)

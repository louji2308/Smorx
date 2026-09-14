from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import CandidatePatch, RepairPackage
from smorx_behavior.models.enums import IntentKind
from smorx_behavior.repo import base as repo_base
from smorx_delta.decision import (
    CertificationDecision,
    DecisionCode,
    decide_certification,
)
from smorx_delta.deltas import BehavioralDeltaRecord, compute_behavioral_deltas
from smorx_delta.handoff import (
    HandoffBarrierError,
    admit_verification_result,
    require_candidate_id,
)
from smorx_delta.intent import IntentAlignmentRecord, evaluate_intent_alignment
from smorx_delta.repair import RepairPlanError, build_repair_package
from smorx_delta.repair_loop import RepairLoopResult, run_repair_loop
from smorx_develop.bounds import LoopBounds
from smorx_verification.contracts import (
    ClaimAssessment,
    Contradiction,
    EvidenceRecord,
    ModuleOutcome,
    ModuleStatus,
    ModuleType,
    VerificationResult,
)
from sqlalchemy.orm import Session


def _claim_id() -> uuid.UUID:
    return uuid.uuid4()


def _evidence(
    claim_id: uuid.UUID,
    *,
    severity: str = "LOW",
    exit_code: int = 0,
    evidence_id: uuid.UUID | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_type=ModuleType.STATIC_ANALYSIS,
        claim_id=claim_id,
        source="static_analysis",
        provenance="provenance:static",
        artifact="compileall",
        machine_result={"exit_code": exit_code},
        exit_code=exit_code,
        severity=severity,
        evidence_id=evidence_id or uuid.uuid4(),
    )


def _result(
    *,
    claims: dict[str, ClaimAssessment] | None = None,
    evidence: tuple[EvidenceRecord, ...] = (),
    modules: tuple[ModuleOutcome, ...] = (),
    contradictions: tuple[Contradiction, ...] = (),
    state: str = "COMPLETED",
    candidate_id: str = "cand-1",
    run_id: str = "run-1",
) -> VerificationResult:
    return VerificationResult(
        candidate_id=candidate_id,
        verification_plan_id=uuid.uuid4(),
        plan_version=1,
        run_id=run_id,
        change_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        modules=modules,
        evidence=evidence,
        claims=claims or {},
        contradictions=contradictions,
        state=state,
    )


def _delta(
    claim_id: uuid.UUID,
    classification: str,
    *,
    intent_alignment: str = "PENDING",
    authorized: bool | None = None,
    evidence_ids: tuple[str, ...] = (),
) -> BehavioralDeltaRecord:
    return BehavioralDeltaRecord(
        id=uuid.uuid4().hex,
        change_id=uuid.uuid4().hex,
        candidate_patch_id=uuid.uuid4().hex,
        classification=classification,
        claim_id=str(claim_id),
        intent_alignment=intent_alignment,
        authorized=authorized,
        observed_at="2026-01-01T00:00:00+00:00",
        evidence_ids=evidence_ids,
    )


def _intent_stub(kind: IntentKind, item_id: str, statement: str) -> SimpleNamespace:
    return SimpleNamespace(kind=kind, id=item_id, statement=statement)


def _repair_decision() -> CertificationDecision:
    return CertificationDecision(
        code=DecisionCode.REPAIR_REQUIRED,
        candidate_id="cand-1",
        change_id="change-1",
        run_id="run-1",
        summary="repair required",
        allow_merge=False,
    )


def _repair_io() -> tuple[
    VerificationResult,
    tuple[BehavioralDeltaRecord, ...],
    tuple[IntentAlignmentRecord, ...],
]:
    claim = _claim_id()
    cid = str(claim)
    evidence = _evidence(claim, severity="HIGH", exit_code=1)
    result = _result(
        claims={cid: ClaimAssessment.CONTRADICTING},
        evidence=(evidence,),
        contradictions=(
            Contradiction(
                claim_id=claim,
                supporting=("STATIC_ANALYSIS",),
                contradicting=("HISTORICAL_GHOST_REPLAY",),
                detail="regression still reproduces",
            ),
        ),
    )
    deltas = compute_behavioral_deltas(
        session=None,
        change_id="change-1",
        candidate_patch_id="patch-1",
        claim_ids=(cid,),
        verification_result=result,
        baseline_claim_ids=frozenset(),
        candidates_claim_ids=frozenset({cid}),
    )
    alignments = evaluate_intent_alignment(
        session=None,
        verification_result=result,
        deltas=deltas,
        intent_items=(),
    )
    return result, deltas, alignments


def _run_repair(
    *,
    decision: CertificationDecision | None = None,
    bounds: LoopBounds | None = None,
) -> RepairLoopResult:
    result, deltas, alignments = _repair_io()
    return asyncio.run(
        run_repair_loop(
            decision=decision or _repair_decision(),
            change_id="change-1",
            candidate_patch_id="patch-1",
            task_id="task-1",
            verification_result=result,
            deltas=deltas,
            alignments=alignments,
            bounds=bounds,
        )
    )


def test_handoff_admits_completed_verification() -> None:
    claim = _claim_id()
    result = _result(
        claims={str(claim): ClaimAssessment.SUPPORTING},
        evidence=(_evidence(claim),),
    )
    handoff = admit_verification_result(result, admitted_at="2026-01-01T00:00:00+00:00")
    assert handoff.decision_allowed is True
    assert handoff.admitted_at == "2026-01-01T00:00:00+00:00"
    assert handoff.evidence_record_ids == (str(result.evidence[0].evidence_id),)
    assert handoff.as_dict()["decision_allowed"] is True


def test_handoff_rejects_non_completed_states_by_name() -> None:
    for state in ("BLOCKED", "INSUFFICIENT_EVIDENCE"):
        result = _result(state=state, evidence=(_evidence(_claim_id()),))
        with pytest.raises(HandoffBarrierError) as excinfo:
            admit_verification_result(result)
        assert state in str(excinfo.value)


def test_handoff_rejects_missing_run_id_and_wrong_contract() -> None:
    with pytest.raises(HandoffBarrierError) as excinfo:
        admit_verification_result(_result(run_id=""))
    assert "run_id" in str(excinfo.value)

    stub = SimpleNamespace(
        state="COMPLETED",
        run_id="run-1",
        contract="WRONG_CONTRACT",
        evidence=(),
        contradictions=(),
        candidate_id="cand-1",
    )
    with pytest.raises(HandoffBarrierError) as excinfo:
        admit_verification_result(stub)
    assert "WRONG_CONTRACT" in str(excinfo.value)


def test_require_candidate_id_mismatch_raises() -> None:
    result = _result(candidate_id="cand-A")
    with pytest.raises(HandoffBarrierError) as excinfo:
        require_candidate_id(result, "cand-B")
    assert "cand-A" in str(excinfo.value) and "cand-B" in str(excinfo.value)


def test_deltas_classify_every_claim_deterministically() -> None:
    a, b, c, d, e = (_claim_id() for _ in range(5))
    ev_a = _evidence(a)
    ev_b = _evidence(b, severity="HIGH")
    ev_d = _evidence(d)
    ev_e = _evidence(e)
    result = _result(
        claims={
            str(a): ClaimAssessment.SUPPORTING,
            str(b): ClaimAssessment.CONTRADICTING,
            str(c): ClaimAssessment.INSUFFICIENT,
            str(d): ClaimAssessment.SUPPORTING,
            str(e): ClaimAssessment.SUPPORTING,
        },
        evidence=(ev_a, ev_b, ev_d, ev_e),
    )
    claim_ids = (str(a), str(b), str(c), str(d), str(e))
    baseline = frozenset({str(a), str(e)})
    candidates = frozenset({str(a), str(d)})
    first = compute_behavioral_deltas(
        session=None,
        change_id="change-1",
        candidate_patch_id="patch-1",
        claim_ids=claim_ids,
        verification_result=result,
        baseline_claim_ids=baseline,
        candidates_claim_ids=candidates,
    )
    second = compute_behavioral_deltas(
        session=None,
        change_id="change-1",
        candidate_patch_id="patch-1",
        claim_ids=claim_ids,
        verification_result=result,
        baseline_claim_ids=baseline,
        candidates_claim_ids=candidates,
    )
    by_claim = {record.claim_id: record for record in first}
    assert by_claim[str(a)].classification == "UNCHANGED"
    assert by_claim[str(b)].classification == "ALTERED"
    assert by_claim[str(c)].classification == "UNEXPLAINED"
    assert by_claim[str(c)].evidence_ids == ()
    assert by_claim[str(d)].classification == "ADDED"
    assert by_claim[str(e)].classification == "REMOVED"
    assert by_claim[str(b)].evidence_ids == (str(ev_b.evidence_id),)
    assert [record.id for record in first] == [record.id for record in second]
    assert tuple(record.claim_id for record in first) == tuple(sorted(claim_ids))
    for record in first:
        assert record.intent_alignment == "PENDING"
        assert record.authorized is None


def test_intent_alignment_applies_every_rule_and_keeps_order() -> None:
    claim_a, claim_b, claim_c, claim_u, claim_x = (_claim_id() for _ in range(5))
    unchanged = _delta(claim_u, "UNCHANGED")
    unexplained = _delta(claim_x, "UNEXPLAINED")
    altered_a = _delta(claim_a, "ALTERED")
    added_b = _delta(claim_b, "ADDED")
    removed_c = _delta(claim_c, "REMOVED")
    items = (
        _intent_stub(
            IntentKind.CONSTRAINT, "ii-c", f"constraint covers claim {claim_a}"
        ),
        _intent_stub(
            IntentKind.REQUIREMENT, "ii-r", f"requirement covers claim {claim_b}"
        ),
    )
    result = _result()
    alignments = evaluate_intent_alignment(
        session=None,
        verification_result=result,
        deltas=(unchanged, unexplained, altered_a, added_b, removed_c),
        intent_items=items,
    )

    assert [record.claim_id for record in alignments] == [
        str(claim_u),
        str(claim_x),
        str(claim_a),
        str(claim_b),
        str(claim_c),
    ]

    assert alignments[0].status == "ALIGNED"
    assert alignments[0].verdict == "AUTHORIZED"
    assert alignments[0].score == 1.0
    assert alignments[0].intent_item_id == ""

    assert alignments[1].status == "PENDING"
    assert alignments[1].verdict == "UNEXPLAINED"
    assert alignments[1].score == 0.0

    assert alignments[2].status == "ALIGNED"
    assert alignments[2].verdict == "AUTHORIZED"
    assert alignments[2].score == 0.9
    assert alignments[2].intent_item_id == "ii-c"

    assert alignments[3].status == "ALIGNED"
    assert alignments[3].verdict == "AUTHORIZED"
    assert alignments[3].score == 0.8
    assert alignments[3].intent_item_id == "ii-r"

    assert alignments[4].status == "MISALIGNED"
    assert alignments[4].verdict == "UNAUTHORIZED"
    assert alignments[4].score == 0.0
    assert alignments[4].intent_item_id == ""


def test_decision_blocked_when_state_not_completed() -> None:
    claim = _claim_id()
    result = _result(
        state="BLOCKED",
        claims={str(claim): ClaimAssessment.SUPPORTING},
        evidence=(_evidence(claim),),
    )
    decision = decide_certification(
        verification_result=result, deltas=(), alignments=()
    )
    assert decision.code == DecisionCode.BLOCKED
    assert decision.allow_merge is False


def test_decision_insufficient_evidence_when_none() -> None:
    decision = decide_certification(
        verification_result=_result(),
        deltas=(),
        alignments=(),
    )
    assert decision.code == DecisionCode.INSUFFICIENT_EVIDENCE
    assert decision.allow_merge is False


def test_decision_eligible_to_continue_when_clean() -> None:
    claim = _claim_id()
    cid = str(claim)
    result = _result(
        claims={cid: ClaimAssessment.SUPPORTING},
        evidence=(_evidence(claim),),
        modules=(
            ModuleOutcome(
                module_type=ModuleType.STATIC_ANALYSIS,
                status=ModuleStatus.PASSED,
                summary="ok",
            ),
        ),
    )
    deltas = compute_behavioral_deltas(
        session=None,
        change_id="change-1",
        candidate_patch_id="patch-1",
        claim_ids=(cid,),
        verification_result=result,
        baseline_claim_ids=frozenset({cid}),
        candidates_claim_ids=frozenset({cid}),
    )
    alignments = evaluate_intent_alignment(
        session=None,
        verification_result=result,
        deltas=deltas,
        intent_items=(),
    )
    decision = decide_certification(
        verification_result=result,
        deltas=deltas,
        alignments=alignments,
    )
    assert decision.code == DecisionCode.ELIGIBLE_TO_CONTINUE
    assert decision.allow_merge is True


def test_decision_repair_for_unexplained_delta() -> None:
    claim = _claim_id()
    other = _claim_id()
    result = _result(
        claims={str(other): ClaimAssessment.SUPPORTING},
        evidence=(_evidence(other),),
    )
    deltas = (_delta(claim, "UNEXPLAINED"), _delta(other, "UNCHANGED"))
    alignments = evaluate_intent_alignment(
        session=None,
        verification_result=result,
        deltas=deltas,
        intent_items=(),
    )
    decision = decide_certification(
        verification_result=result,
        deltas=deltas,
        alignments=alignments,
    )
    assert decision.code == DecisionCode.REPAIR_REQUIRED
    assert decision.allow_merge is False
    assert any("unexplained" in failure for failure in decision.reason_failures)


def test_decision_repair_for_contradicting_claim() -> None:
    claim = _claim_id()
    cid = str(claim)
    result = _result(
        claims={cid: ClaimAssessment.CONTRADICTING},
        evidence=(_evidence(claim, severity="HIGH"),),
    )
    decision = decide_certification(
        verification_result=result, deltas=(), alignments=()
    )
    assert decision.code == DecisionCode.REPAIR_REQUIRED
    assert decision.allow_merge is False


def test_decision_repair_for_unauthorized_alignment() -> None:
    claim = _claim_id()
    cid = str(claim)
    result = _result(
        claims={cid: ClaimAssessment.SUPPORTING},
        evidence=(_evidence(claim),),
    )
    deltas = (_delta(claim, "ADDED"),)
    alignments = evaluate_intent_alignment(
        session=None,
        verification_result=result,
        deltas=deltas,
        intent_items=(),
    )
    decision = decide_certification(
        verification_result=result,
        deltas=deltas,
        alignments=alignments,
    )
    assert decision.code == DecisionCode.REPAIR_REQUIRED
    assert decision.allow_merge is False
    assert any("unauthorized" in failure for failure in decision.reason_failures)


def test_decision_repair_for_failed_module() -> None:
    claim = _claim_id()
    cid = str(claim)
    result = _result(
        claims={cid: ClaimAssessment.SUPPORTING},
        evidence=(_evidence(claim),),
        modules=(
            ModuleOutcome(
                module_type=ModuleType.HISTORICAL_GHOST_REPLAY,
                status=ModuleStatus.FAILED,
                summary="regression reproduced",
            ),
        ),
    )
    deltas = compute_behavioral_deltas(
        session=None,
        change_id="change-1",
        candidate_patch_id="patch-1",
        claim_ids=(cid,),
        verification_result=result,
        baseline_claim_ids=frozenset({cid}),
        candidates_claim_ids=frozenset({cid}),
    )
    alignments = evaluate_intent_alignment(
        session=None,
        verification_result=result,
        deltas=deltas,
        intent_items=(),
    )
    decision = decide_certification(
        verification_result=result,
        deltas=deltas,
        alignments=alignments,
    )
    assert decision.code == DecisionCode.REPAIR_REQUIRED
    assert decision.allow_merge is False
    assert any("module" in failure for failure in decision.reason_failures)


def test_decision_allow_merge_only_for_eligible() -> None:
    blocked_claim = _claim_id()
    blocked = _result(
        state="BLOCKED",
        claims={str(blocked_claim): ClaimAssessment.SUPPORTING},
        evidence=(_evidence(blocked_claim),),
    )
    insufficient = _result()

    clean_claim = _claim_id()
    clean_cid = str(clean_claim)
    clean = _result(
        claims={clean_cid: ClaimAssessment.SUPPORTING},
        evidence=(_evidence(clean_claim),),
        modules=(
            ModuleOutcome(
                module_type=ModuleType.STATIC_ANALYSIS,
                status=ModuleStatus.PASSED,
                summary="ok",
            ),
        ),
    )
    clean_deltas = compute_behavioral_deltas(
        session=None,
        change_id="change-1",
        candidate_patch_id="patch-1",
        claim_ids=(clean_cid,),
        verification_result=clean,
        baseline_claim_ids=frozenset({clean_cid}),
        candidates_claim_ids=frozenset({clean_cid}),
    )
    clean_alignments = evaluate_intent_alignment(
        session=None,
        verification_result=clean,
        deltas=clean_deltas,
        intent_items=(),
    )

    contradicting_claim = _claim_id()
    contradicting = _result(
        claims={str(contradicting_claim): ClaimAssessment.CONTRADICTING},
        evidence=(_evidence(contradicting_claim, severity="HIGH"),),
    )

    decisions = [
        decide_certification(verification_result=blocked, deltas=(), alignments=()),
        decide_certification(
            verification_result=insufficient, deltas=(), alignments=()
        ),
        decide_certification(
            verification_result=clean,
            deltas=clean_deltas,
            alignments=clean_alignments,
        ),
        decide_certification(
            verification_result=contradicting,
            deltas=(),
            alignments=(),
        ),
    ]
    for decision in decisions:
        if decision.code == DecisionCode.ELIGIBLE_TO_CONTINUE:
            assert decision.allow_merge is True
        else:
            assert decision.allow_merge is False


def test_repair_package_builds_valid_record() -> None:
    evidence_id = str(uuid.uuid4())
    package = build_repair_package(
        failure_id="F-183",
        affected_claim_id="claim-1",
        expected_behavior="protected behavior must be preserved",
        observed_behavior="regression reproduced",
        evidence_ids=(evidence_id,),
        required_outcome="re-verify before merge",
        suspected_path="src/app.py",
        acceptance_criteria=("no REGRESSION marker",),
        constraints=("no API breaking change",),
    )
    assert package.failure_id == "F-183"
    assert package.affected_claim_id == "claim-1"
    assert package.evidence_ids == (evidence_id,)
    assert package.required_outcome == "re-verify before merge"
    assert package.suspected_path == "src/app.py"
    assert package.as_dict()["version"] == "1.0.0"
    assert package.id


def test_repair_package_rejects_invalid_inputs() -> None:
    with pytest.raises(RepairPlanError):
        build_repair_package(
            failure_id="f",
            affected_claim_id="c",
            expected_behavior="e",
            observed_behavior="o",
            evidence_ids=(),
            required_outcome="r",
        )
    with pytest.raises(RepairPlanError):
        build_repair_package(
            failure_id="f",
            affected_claim_id="c",
            expected_behavior="e",
            observed_behavior="o",
            evidence_ids=("e1",),
            required_outcome="",
        )
    with pytest.raises(RepairPlanError):
        build_repair_package(
            failure_id="f",
            affected_claim_id="",
            expected_behavior="e",
            observed_behavior="o",
            evidence_ids=("e1",),
            required_outcome="r",
        )


def test_repair_loop_skips_when_not_repair_required() -> None:
    decision = CertificationDecision(
        code=DecisionCode.ELIGIBLE_TO_CONTINUE,
        candidate_id="cand-1",
        change_id="change-1",
        run_id="run-1",
        summary="clean",
        allow_merge=True,
    )
    result = _result()
    loop_result = asyncio.run(
        run_repair_loop(
            decision=decision,
            change_id="change-1",
            candidate_patch_id="patch-1",
            task_id="task-1",
            verification_result=result,
            deltas=(),
            alignments=(),
        )
    )
    assert loop_result.iterations == ()
    assert loop_result.allow_continue is False


def test_repair_loop_structures_evidence_bound_iteration() -> None:
    loop_result = _run_repair()
    assert loop_result.iterations
    for iteration in loop_result.iterations:
        assert iteration.candidate_index >= 2
        assert iteration.status == "CREATED"
        assert iteration.repair.evidence_ids
    assert loop_result.allow_continue is True


def test_repair_loop_persists_repair_candidates_leaving_index_1_untouched() -> None:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        change_id = uuid.uuid4()
        task_id = uuid.uuid4()
        original = repo_base.save(
            session,
            CandidatePatch(
                change_id=change_id,
                task_id=task_id,
                status="PROPOSED",
                candidate_index=1,
                patch_ref="manual-1",
                summary="candidate patch 1",
            ),
        )

        claim = _claim_id()
        cid = str(claim)
        evidence = _evidence(claim, severity="HIGH", exit_code=1)
        result = _result(
            claims={cid: ClaimAssessment.CONTRADICTING},
            evidence=(evidence,),
        )
        deltas = compute_behavioral_deltas(
            session=session,
            change_id=str(change_id),
            candidate_patch_id=str(original.id),
            claim_ids=(cid,),
            verification_result=result,
            baseline_claim_ids=frozenset(),
            candidates_claim_ids=frozenset({cid}),
        )
        alignments = evaluate_intent_alignment(
            session=session,
            verification_result=result,
            deltas=deltas,
            intent_items=(),
        )
        loop_result = asyncio.run(
            run_repair_loop(
                decision=_repair_decision(),
                change_id=str(change_id),
                candidate_patch_id=str(original.id),
                task_id=str(task_id),
                verification_result=result,
                deltas=deltas,
                alignments=alignments,
                session=session,
            )
        )
        assert loop_result.iterations

        original_row = session.get(CandidatePatch, original.id)
        assert original_row is not None
        assert original_row.candidate_index == 1
        assert original_row.patch_ref == "manual-1"
        assert original_row.status == "PROPOSED"

        rows = repo_base.list_(session, CandidatePatch)
        for row in rows:
            assert "CERTIFIED" not in (row.status or "")
        new_candidates = [row for row in rows if row.candidate_index >= 2]
        assert new_candidates
        for row in new_candidates:
            assert row.patch_ref and row.patch_ref.startswith("repair_loop:")
            assert row.status == "PROPOSED"

        repair_rows = repo_base.list_(session, RepairPackage)
        assert repair_rows
        for row in repair_rows:
            assert row.status == "CREATED"
            assert row.candidate_patch_id is not None


def test_repair_loop_respects_max_iterations_bound() -> None:
    loop_result = _run_repair(bounds=LoopBounds(max_iterations=1))
    assert len(loop_result.iterations) == 1
    assert loop_result.iterations[0].iteration == 1


def test_repair_loop_stops_on_no_progress() -> None:
    first = _run_repair()
    second = _run_repair()
    for loop_result in (first, second):
        assert len(loop_result.iterations) == 2
        assert "no-progress" in loop_result.blocked_reason
        assert loop_result.iterations[-1].outcome == "NO_PROGRESS"

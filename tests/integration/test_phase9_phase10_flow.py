"""Phase 9 → Phase 10 integration — the real verification-to-decision chain.

Drives the track-1 evidence chain against real database rows and REAL
subprocess executions (no staged results, AGENTS.md section 3):

    CANDIDATE PATCH → VERIFICATION WAVE (six real modules) → EVIDENCE
    PERSISTENCE → HANDOFF → BEHAVIORAL DELTAS → INTENT ALIGNMENT →
    CERTIFICATION DECISION → REPAIR LOOP (persisted repair candidates)

Two journeys are exercised end to end:

  * a clean candidate → COMPLETED wave → evidence rows → eligible-to-continue
    decision with ``allow_merge=True``;
  * a regression probe → real HIGH/contradicting evidence → repair-required
    decision → the evidence-bound repair loop persists repair candidates
    without ever certifying (I7) or mutating Candidate Patch #1
    (AGENTS.md section 15).

Documented boundary observation: every verification module binds its evidence
to the first claim of the wave (``ctx.claim_ids[0]``); a second claim receives
no evidence and is fused INSUFFICIENT / classified UNEXPLAINED when included
in the delta set. The eligible path therefore computes deltas for the
evidence-eligible claim only (task-sanctioned adjustment).
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import uuid
from pathlib import Path

from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.evidence.service import evidence_for_claim
from smorx_behavior.models import (
    CandidatePatch,
    Change,
    Claim,
    Evidence,
    IntentItem,
    IntentLedger,
    Project,
    RepairPackage,
    Repository,
    Task,
)
from smorx_behavior.models.enums import IntentKind
from smorx_behavior.repo import base as repo_base
from smorx_delta.decision import DecisionCode, decide_certification
from smorx_delta.deltas import compute_behavioral_deltas
from smorx_delta.handoff import admit_verification_result, require_candidate_id
from smorx_delta.intent import evaluate_intent_alignment
from smorx_delta.repair_loop import run_repair_loop
from smorx_precode.verification_plan import VerificationCaseSpec, VerificationPlanRef
from smorx_verification.boundary import VerificationActor
from smorx_verification.contracts import (
    ClaimAssessment,
    ModuleStatus,
)
from smorx_verification.runner import VerificationRunConfig, run_verification_wave
from sqlalchemy.orm import Session

PY = sys.executable


def _wave_settings(*, regression: bool) -> dict[str, object]:
    """Module settings that replay the ghost probe for real in every module."""
    probe_old = "REGRESSION" if regression else "42"
    probe_new = "FIXED" if regression else "7"
    expected = "REGRESSION reproduced" if regression else "42"
    return {
        "ghost_replay": {
            "scenarios": [
                {
                    "scenario_id": "ghost-221",
                    "title": "historical auth failure",
                    "regression_marker": "REGRESSION",
                    "args": [PY, "ghost_probe.py"],
                }
            ]
        },
        "differential": {
            "probes": [{"name": "contract_probe", "args": [PY, "-c", "print(42)"]}]
        },
        "metamorphic": {
            "checks": [
                {
                    "check_id": "meta-invariants",
                    "title": "contract invariants",
                    "args": [PY, "-c", "print(42)"],
                    "variants": [[PY, "-c", "print(42)"]],
                }
            ]
        },
        "mutation": {
            "expected_stdout": expected,
            "mutations": [
                {
                    "mutation_id": "MUT-GHOST",
                    "target": "ghost_probe.py",
                    "old": probe_old,
                    "new": probe_new,
                }
            ],
        },
    }


def _write_workspace(root: Path, *, probe_line: str) -> None:
    (root / "ghost_probe.py").write_text(probe_line, encoding="utf-8")
    (root / "demo.py").write_text(
        "def main() -> None:\n    print(42)\n\n\nif __name__ == '__main__':\n    main()\n",
        encoding="utf-8",
    )


def _seed(session: Session) -> dict[str, object]:
    project = repo_base.save(session, Project(name="Smorx", slug="smorx"))
    repository = repo_base.save(
        session, Repository(project_id=project.id, name="research-repo")
    )
    change = repo_base.save(
        session,
        Change(
            repository_id=repository.id,
            title="preserve the verified contract behavior",
            status="OPEN",
        ),
    )
    task = repo_base.save(
        session,
        Task(
            project_id=project.id,
            repository_id=repository.id,
            change_id=change.id,
            title="preserve the verified contract behavior",
        ),
    )
    claim1 = repo_base.save(
        session,
        Claim(
            task_id=task.id,
            statement="candidate preserves the documented print(42) contract",
        ),
    )
    claim2 = repo_base.save(
        session,
        Claim(task_id=task.id, statement="second claim with no module coverage"),
    )
    ledger = repo_base.save(
        session,
        IntentLedger(
            project_id=project.id,
            task_id=task.id,
            title="contract preservation intent",
            status="ACTIVE",
        ),
    )
    intent_item = repo_base.save(
        session,
        IntentItem(
            intent_ledger_id=ledger.id,
            task_id=task.id,
            kind=IntentKind.CONSTRAINT.value,
            statement=f"contract for claim {claim1.id} must be preserved",
            status="PENDING",
            authorized=True,
        ),
    )
    candidate = repo_base.save(
        session,
        CandidatePatch(
            change_id=change.id,
            task_id=task.id,
            status="PROPOSED",
            candidate_index=1,
            patch_ref="candidate-1",
            summary="preserve the verified contract behavior",
        ),
    )
    return {
        "project": project,
        "repository": repository,
        "change": change,
        "task": task,
        "claim1": claim1,
        "claim2": claim2,
        "ledger": ledger,
        "intent_item": intent_item,
        "candidate": candidate,
    }


def _plan(change_id: uuid.UUID, task_id: uuid.UUID) -> VerificationPlanRef:
    return VerificationPlanRef(
        verification_plan_id=uuid.uuid4(),
        change_id=change_id,
        task_id=task_id,
        intent_ledger_id=None,
        title="phase 9/10 integration plan",
        version=1,
        locked=True,
        status="LOCKED",
        cases=(
            VerificationCaseSpec(
                name="ghost regression check",
                kind="REGRESSION_CHECK",
                behaviors=("behavior:ghost-221",),
                method=f'"{PY}" -c "print(42)"',
                expected="no REGRESSION marker on stdout",
            ),
        ),
        coverage={"behavior:ghost-221": ("ghost regression check",)},
    )


def test_clean_wave_evidences_eligible_decision_chain() -> None:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ids = _seed(session)
        claim1 = ids["claim1"]
        claim2 = ids["claim2"]
        change = ids["change"]
        candidate = ids["candidate"]

        with (
            tempfile.TemporaryDirectory() as candidate_root,
            tempfile.TemporaryDirectory() as baseline_root,
        ):
            _write_workspace(Path(baseline_root), probe_line="print(42)\n")
            _write_workspace(Path(candidate_root), probe_line="print(42)\n")
            result = asyncio.run(
                run_verification_wave(
                    VerificationRunConfig(
                        session=session,
                        plan=_plan(change.id, ids["task"].id),
                        actor=VerificationActor(
                            actor_run_id="verifier-e2e-1",
                            role="INDEPENDENT_VERIFIER",
                            source_agent_run_id="coding-agent-run-1",
                        ),
                        candidate_root=candidate_root,
                        baseline_root=baseline_root,
                        run_id="verif-e2e-1",
                        claim_ids=(claim1.id, claim2.id),
                        settings=_wave_settings(regression=False),
                    )
                )
            )

        assert result.state == "COMPLETED"
        assert result.contract == "VERIFICATION_RESULT_V1"
        assert result.claims[str(claim1.id)] == ClaimAssessment.SUPPORTING
        assert result.claims[str(claim2.id)] == ClaimAssessment.INSUFFICIENT
        assert all(module.status == ModuleStatus.PASSED for module in result.modules)
        assert result.evidence
        assert all(record.claim_id == claim1.id for record in result.evidence)

        ghost_record = next(
            record
            for record in result.evidence
            if record.source.startswith("ghost_replay.")
        )
        assert ghost_record.machine_result["regression_reproduced"] is False
        assert ghost_record.exit_code == 0

        for record in result.evidence:
            row = session.get(Evidence, record.evidence_id)
            assert row is not None
            assert row.claim_id == claim1.id
        assert evidence_for_claim(session, claim2.id) == []

        handoff = admit_verification_result(result)
        assert handoff.decision_allowed is True
        assert str(handoff.as_dict()["run_id"]) == "verif-e2e-1"
        require_candidate_id(result, result.candidate_id)

        change_id = str(change.id)
        candidate_patch_id = str(candidate.id)
        deltas = compute_behavioral_deltas(
            session=session,
            change_id=change_id,
            candidate_patch_id=candidate_patch_id,
            claim_ids=(str(claim1.id),),
            verification_result=result,
            baseline_claim_ids=frozenset(),
            candidates_claim_ids=frozenset({str(claim1.id)}),
        )
        assert len(deltas) == 1
        delta = deltas[0]
        assert delta.classification == "ADDED"
        assert delta.intent_alignment == "PENDING"
        assert delta.authorized is None
        assert delta.evidence_ids == tuple(
            sorted(str(record.evidence_id) for record in result.evidence)
        )

        second = compute_behavioral_deltas(
            session=session,
            change_id=change_id,
            candidate_patch_id=candidate_patch_id,
            claim_ids=(str(claim1.id),),
            verification_result=result,
            baseline_claim_ids=frozenset(),
            candidates_claim_ids=frozenset({str(claim1.id)}),
        )
        assert delta.id == second[0].id

        full = compute_behavioral_deltas(
            session=session,
            change_id=change_id,
            candidate_patch_id=candidate_patch_id,
            claim_ids=(str(claim1.id), str(claim2.id)),
            verification_result=result,
            baseline_claim_ids=frozenset(),
            candidates_claim_ids=frozenset({str(claim1.id)}),
        )
        full_by_claim = {record.claim_id: record for record in full}
        assert full_by_claim[str(claim1.id)].classification == "ADDED"
        assert full_by_claim[str(claim2.id)].classification == "UNEXPLAINED"
        assert full_by_claim[str(claim2.id)].evidence_ids == ()

        alignments = evaluate_intent_alignment(
            session=session,
            verification_result=result,
            deltas=deltas,
            intent_items=(ids["intent_item"],),
        )
        assert len(alignments) == 1
        alignment = alignments[0]
        assert alignment.status == "ALIGNED"
        assert alignment.verdict == "AUTHORIZED"
        assert alignment.score == 0.9
        assert alignment.intent_item_id == str(ids["intent_item"].id)

        decision = decide_certification(
            verification_result=result,
            deltas=deltas,
            alignments=alignments,
        )
        assert decision.code == DecisionCode.ELIGIBLE_TO_CONTINUE
        assert decision.allow_merge is True
        assert decision.reason_failures == ()
        assert decision.candidate_id == result.candidate_id
        assert decision.run_id == "verif-e2e-1"


def test_regression_wave_forces_evidence_bound_repair_loop() -> None:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ids = _seed(session)
        claim1 = ids["claim1"]
        claim2 = ids["claim2"]
        change = ids["change"]
        task = ids["task"]
        candidate = ids["candidate"]

        with (
            tempfile.TemporaryDirectory() as candidate_root,
            tempfile.TemporaryDirectory() as baseline_root,
        ):
            _write_workspace(Path(baseline_root), probe_line="print(42)\n")
            _write_workspace(
                Path(candidate_root), probe_line='print("REGRESSION reproduced")\n'
            )
            result = asyncio.run(
                run_verification_wave(
                    VerificationRunConfig(
                        session=session,
                        plan=_plan(change.id, task.id),
                        actor=VerificationActor(
                            actor_run_id="verifier-e2e-2",
                            role="INDEPENDENT_VERIFIER",
                            source_agent_run_id="coding-agent-run-2",
                        ),
                        candidate_root=candidate_root,
                        baseline_root=baseline_root,
                        run_id="verif-repair-1",
                        claim_ids=(claim1.id, claim2.id),
                        settings=_wave_settings(regression=True),
                    )
                )
            )

        assert result.state == "COMPLETED"
        assert result.contract == "VERIFICATION_RESULT_V1"
        assert result.claims[str(claim1.id)] == ClaimAssessment.CONFLICTING
        assert result.claims[str(claim2.id)] == ClaimAssessment.INSUFFICIENT
        assert any(module.status == ModuleStatus.FAILED for module in result.modules)

        ghost_record = next(
            record
            for record in result.evidence
            if record.source.startswith("ghost_replay.")
        )
        assert ghost_record.machine_result["regression_reproduced"] is True
        assert ghost_record.severity == "HIGH"

        handoff = admit_verification_result(result)
        assert handoff.decision_allowed is True
        require_candidate_id(result, result.candidate_id)

        change_id = str(change.id)
        candidate_patch_id = str(candidate.id)
        deltas = compute_behavioral_deltas(
            session=session,
            change_id=change_id,
            candidate_patch_id=candidate_patch_id,
            claim_ids=(str(claim1.id),),
            verification_result=result,
            baseline_claim_ids=frozenset({str(claim1.id)}),
            candidates_claim_ids=frozenset({str(claim1.id)}),
        )
        assert len(deltas) == 1
        assert deltas[0].classification == "ALTERED"
        assert deltas[0].evidence_ids

        alignments = evaluate_intent_alignment(
            session=session,
            verification_result=result,
            deltas=deltas,
            intent_items=(ids["intent_item"],),
        )
        assert len(alignments) == 1
        assert alignments[0].status == "ALIGNED"
        assert alignments[0].verdict == "AUTHORIZED"

        decision = decide_certification(
            verification_result=result,
            deltas=deltas,
            alignments=alignments,
        )
        assert decision.code == DecisionCode.REPAIR_REQUIRED
        assert decision.allow_merge is False
        assert any("CONFLICTING" in failure for failure in decision.reason_failures)
        assert any(
            "HISTORICAL_GHOST_REPLAY" in failure for failure in decision.reason_failures
        )

        loop_result = asyncio.run(
            run_repair_loop(
                decision=decision,
                change_id=change_id,
                candidate_patch_id=candidate_patch_id,
                task_id=str(task.id),
                verification_result=result,
                deltas=deltas,
                alignments=alignments,
                session=session,
            )
        )
        assert loop_result.iterations
        for iteration in loop_result.iterations:
            assert iteration.candidate_index >= 2
            assert iteration.status == "CREATED"
            assert iteration.repair.evidence_ids

        original_row = session.get(CandidatePatch, candidate.id)
        assert original_row is not None
        assert original_row.candidate_index == 1
        assert original_row.patch_ref == "candidate-1"
        assert original_row.status == "PROPOSED"

        rows = repo_base.list_(session, CandidatePatch)
        for row in rows:
            assert "CERTIFIED" not in (row.status or "")
        new_candidates = [row for row in rows if row.candidate_index >= 2]
        assert new_candidates
        for row in new_candidates:
            assert row.patch_ref and row.patch_ref.startswith("repair_loop:")
            assert row.status == "PROPOSED"

        repairs = repo_base.list_(session, RepairPackage)
        assert repairs
        for package in repairs:
            assert package.status == "CREATED"
            assert package.candidate_patch_id is not None
            assert package.evidence_id is not None

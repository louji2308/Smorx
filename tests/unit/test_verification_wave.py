"""Phase 9 unit tests — the six verification modules and the concurrent wave runner.

Exercises real execution through ``smorx_tools.execution.CommandRunner``
(real subprocesses, real temp workspaces) and real persistence through the
behavioral evidence service on in-memory SQLite. Every test is synchronous
(``asyncio.run``), matching the repository convention of no pytest-asyncio
dependency.
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Base, Evidence
from smorx_precode.verification_plan import VerificationPlanRef
from smorx_verification.adversarial import run_adversarial_scenarios
from smorx_verification.boundary import VerificationActor
from smorx_verification.context import ModuleContext
from smorx_verification.contracts import ClaimAssessment, ModuleStatus, ModuleType
from smorx_verification.differential import run_differential_execution
from smorx_verification.evidence import EvidenceCollector
from smorx_verification.ghost_replay import run_historical_ghost_replay
from smorx_verification.metamorphic import run_metamorphic_checks
from smorx_verification.mutation import run_mutation_testing
from smorx_verification.runner import VerificationRunConfig, run_verification_wave
from smorx_verification.static_analysis import run_static_analysis
from sqlalchemy import select
from sqlalchemy.orm import Session


def _actor() -> VerificationActor:
    return VerificationActor(
        actor_run_id="verifier-test", source_agent_run_id="coding-agent-test"
    )


def _plan() -> VerificationPlanRef:
    return VerificationPlanRef(
        verification_plan_id=uuid.uuid4(),
        change_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        intent_ledger_id=None,
        title="verification wave unit test",
        version=1,
        locked=True,
        status="LOCKED",
        cases=(),
        coverage={},
    )


def _new_session() -> Session:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _collector(session: Session) -> EvidenceCollector:
    return EvidenceCollector(
        session=session, run_id=str(uuid.uuid4()), source="test_wave"
    )


def _context(
    candidate_root: str,
    *,
    session: Session,
    settings: dict[str, object] | None = None,
    baseline_root: str | None = None,
) -> ModuleContext:
    return ModuleContext(
        actor=_actor(),
        claim_ids=(uuid.uuid4(),),
        candidate_root=candidate_root,
        baseline_root=baseline_root,
        collector=_collector(session),
        settings=settings or {},
    )


class TestStaticAnalysis:
    def test_clean_demo_passes_and_emits_eligible_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            Path(candidate, "demo.py").write_text(
                "def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8"
            )
            with _new_session() as session:
                outcome = asyncio.run(
                    run_static_analysis(_context(candidate, session=session))
                )
            assert outcome.status == ModuleStatus.PASSED
            assert len(outcome.evidence) == 1
            record = outcome.evidence[0]
            assert record.machine_result["exit_code"] == 0
            assert record.module_status == "ELIGIBLE"

    def test_hardcoded_api_key_fails_with_high_record(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            Path(candidate, "demo.py").write_text(
                "api_key = 123\nprint(api_key)\n", encoding="utf-8"
            )
            with _new_session() as session:
                outcome = asyncio.run(
                    run_static_analysis(_context(candidate, session=session))
                )
            assert outcome.status == ModuleStatus.FAILED
            record = next(
                record
                for record in outcome.evidence
                if record.source == "static_analysis.secret_scan"
            )
            assert record.severity == "HIGH"
            assert record.machine_result["total_matched"] >= 1

    def test_non_directory_candidate_root_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            file_path = Path(base, "not_a_dir.py")
            file_path.write_text("x = 1\n", encoding="utf-8")
            with _new_session() as session:
                outcome = asyncio.run(
                    run_static_analysis(_context(str(file_path), session=session))
                )
            assert outcome.status == ModuleStatus.BLOCKED
            assert "not a directory" in outcome.summary

    def test_empty_directory_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                outcome = asyncio.run(
                    run_static_analysis(_context(candidate, session=session))
                )
            assert outcome.status == ModuleStatus.SKIPPED


class TestDifferentialExecution:
    def test_identical_behavior_passes(self) -> None:
        with (
            tempfile.TemporaryDirectory() as baseline,
            tempfile.TemporaryDirectory() as candidate,
            _new_session() as session,
        ):
            outcome = asyncio.run(
                run_differential_execution(
                    _context(
                        candidate,
                        session=session,
                        baseline_root=baseline,
                        settings={
                            "differential": {
                                "probes": [
                                    {
                                        "name": "p1",
                                        "args": ["python", "-c", "print(42)"],
                                    }
                                ]
                            }
                        },
                    )
                )
            )
        assert outcome.status == ModuleStatus.PASSED
        record = outcome.evidence[0]
        assert record.machine_result["behavior_equal"] is True
        assert record.machine_result["baseline_stdout_tail"] == "42"
        assert record.machine_result["candidate_stdout_tail"] == "42"

    def test_differing_probe_fails(self) -> None:
        with tempfile.TemporaryDirectory() as baseline:
            with tempfile.TemporaryDirectory() as candidate:
                Path(baseline, "probe.py").write_text("print(42)\n", encoding="utf-8")
                Path(candidate, "probe.py").write_text("print(43)\n", encoding="utf-8")
                with _new_session() as session:
                    outcome = asyncio.run(
                        run_differential_execution(
                            _context(
                                candidate,
                                session=session,
                                baseline_root=baseline,
                                settings={
                                    "differential": {
                                        "probes": [
                                            {
                                                "name": "p1",
                                                "args": ["python", "probe.py"],
                                            }
                                        ]
                                    }
                                },
                            )
                        )
                    )
            assert outcome.status == ModuleStatus.FAILED
            record = outcome.evidence[0]
            assert record.machine_result["behavior_equal"] is False
            assert record.severity == "HIGH"

    def test_missing_baseline_root_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                outcome = asyncio.run(
                    run_differential_execution(_context(candidate, session=session))
                )
            assert outcome.status == ModuleStatus.BLOCKED
            assert "baseline_root" in outcome.summary


class TestHistoricalGhostReplay:
    def test_regression_marker_fails_with_high_record(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            Path(candidate, "ghost_probe.py").write_text(
                'print("REGRESSION")\n', encoding="utf-8"
            )
            with _new_session() as session:
                outcome = asyncio.run(
                    run_historical_ghost_replay(
                        _context(
                            candidate,
                            session=session,
                            settings={
                                "ghost_replay": {
                                    "scenarios": [
                                        {
                                            "scenario_id": "G1",
                                            "regression_marker": "REGRESSION",
                                        }
                                    ]
                                }
                            },
                        )
                    )
                )
            assert outcome.status == ModuleStatus.FAILED
            record = outcome.evidence[0]
            assert record.severity == "HIGH"
            assert record.machine_result["regression_reproduced"] is True

    def test_clean_probe_passes(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            Path(candidate, "ghost_probe.py").write_text(
                'print("ok")\n', encoding="utf-8"
            )
            with _new_session() as session:
                outcome = asyncio.run(
                    run_historical_ghost_replay(
                        _context(
                            candidate,
                            session=session,
                            settings={
                                "ghost_replay": {
                                    "scenarios": [
                                        {
                                            "scenario_id": "G1",
                                            "regression_marker": "REGRESSION",
                                        }
                                    ]
                                }
                            },
                        )
                    )
                )
            assert outcome.status == ModuleStatus.PASSED
            assert outcome.summary == (
                "ghost replay: 1/1 scenarios hold (0 historical failure(s) still reproduce)"
            )


class TestMetamorphicChecks:
    def _run(
        self, session: Session, candidate: str, variants: list[list[str]]
    ) -> object:
        return asyncio.run(
            run_metamorphic_checks(
                _context(
                    candidate,
                    session=session,
                    settings={
                        "metamorphic": {
                            "checks": [
                                {
                                    "check_id": "C1",
                                    "args": ["python", "-c", "print(42)"],
                                    "variants": variants,
                                }
                            ]
                        }
                    },
                )
            )
        )

    def test_consistent_variants_pass(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                outcome = self._run(session, candidate, [["python", "-c", "print(42)"]])
            assert outcome.status == ModuleStatus.PASSED
            record = outcome.evidence[0]
            assert record.machine_result["variants_consistent"] is True

    def test_differing_variant_fails_with_high_record(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                outcome = self._run(session, candidate, [["python", "-c", "print(43)"]])
            assert outcome.status == ModuleStatus.FAILED
            record = outcome.evidence[0]
            assert record.machine_result["variants_consistent"] is False
            assert record.severity == "HIGH"


class TestAdversarialScenarios:
    def test_no_planted_holes_passes_and_must_block_verdicts(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                outcome = asyncio.run(
                    run_adversarial_scenarios(_context(candidate, session=session))
                )
            assert outcome.status == ModuleStatus.PASSED
            assert len(outcome.evidence) == 22
            blocked = {
                record.machine_result["case_id"]
                for record in outcome.evidence
                if record.machine_result["verdict"] == "BLOCKED"
            }
            assert blocked == {
                "ADV-08",
                "ADV-13",
                "ADV-14",
                "ADV-15",
                "ADV-16",
                "ADV-20",
                "ADV-22",
            }

    def test_planted_vulnerability_fails_with_finding(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                outcome = asyncio.run(
                    run_adversarial_scenarios(
                        _context(
                            candidate,
                            session=session,
                            settings={
                                "adversarial": {"planted_vulnerabilities": ["ADV-08"]}
                            },
                        )
                    )
                )
            assert outcome.status == ModuleStatus.FAILED
            assert len(outcome.evidence) == 22
            assert outcome.findings == ("ADV-08",)
            record = next(
                record
                for record in outcome.evidence
                if record.machine_result["case_id"] == "ADV-08"
            )
            assert record.machine_result["verdict"] == "HOLE_FOUND"


class TestMutationTesting:
    def test_killed_mutation_passes_and_leaves_candidate_intact(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            probe = Path(candidate, "ghost_probe.py")
            probe.write_text('print("42")\n', encoding="utf-8")
            with _new_session() as session:
                outcome = asyncio.run(
                    run_mutation_testing(
                        _context(
                            candidate,
                            session=session,
                            settings={
                                "mutation": {
                                    "mutations": [
                                        {
                                            "mutation_id": "M1",
                                            "target": "ghost_probe.py",
                                            "old": 'print("42")',
                                            "new": 'print("7")',
                                        }
                                    ],
                                    "expected_stdout": "42",
                                }
                            },
                        )
                    )
                )
            assert outcome.status == ModuleStatus.PASSED
            record = outcome.evidence[0]
            assert record.machine_result["killed"] is True
            assert record.machine_result["probe_stdout_tail"] == "7"
            assert probe.read_text(encoding="utf-8") == 'print("42")\n'


class TestVerificationWaveRunner:
    def test_end_to_end_completed(self) -> None:
        claim_id = uuid.uuid4()
        with (
            tempfile.TemporaryDirectory() as baseline,
            tempfile.TemporaryDirectory() as candidate,
            _new_session() as session,
        ):
            Path(baseline, "ghost_probe.py").write_text(
                'print("42")\n', encoding="utf-8"
            )
            Path(candidate, "ghost_probe.py").write_text(
                'print("42")\n', encoding="utf-8"
            )
            config = VerificationRunConfig(
                session=session,
                plan=_plan(),
                actor=_actor(),
                candidate_root=candidate,
                baseline_root=baseline,
                run_id=str(uuid.uuid4()),
                claim_ids=(claim_id,),
                settings={
                    "ghost_replay": {
                        "scenarios": [
                            {"scenario_id": "G1", "regression_marker": "REGRESSION"}
                        ]
                    },
                    "differential": {
                        "probes": [
                            {"name": "p1", "args": ["python", "-c", "print(42)"]}
                        ]
                    },
                    "mutation": {
                        "mutations": [
                            {
                                "mutation_id": "M1",
                                "target": "ghost_probe.py",
                                "old": 'print("42")',
                                "new": 'print("7")',
                            }
                        ],
                        "expected_stdout": "42",
                    },
                },
            )
            result = asyncio.run(run_verification_wave(config))
            assert result.state == "COMPLETED"
            assert result.contract == "VERIFICATION_RESULT_V1"
            assert len(result.evidence) > 0
            assert {module.module_type for module in result.modules} == set(ModuleType)
            terminal = {
                ModuleStatus.PASSED,
                ModuleStatus.FAILED,
                ModuleStatus.BLOCKED,
                ModuleStatus.SKIPPED,
            }
            assert all(module.status in terminal for module in result.modules)
            assert set(result.claims) == {str(claim_id)}
            assert result.claims[str(claim_id)] == ClaimAssessment.SUPPORTING
            rows = session.scalars(select(Evidence)).all()
            persisted_ids = {row.id for row in rows}
            assert len(persisted_ids) >= len(result.evidence)
            assert all(
                record.evidence_id in persisted_ids for record in result.evidence
            )

    def test_empty_modules_insufficient_evidence(self) -> None:
        claim_id = uuid.uuid4()
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                config = VerificationRunConfig(
                    session=session,
                    plan=_plan(),
                    actor=_actor(),
                    candidate_root=candidate,
                    claim_ids=(claim_id,),
                    modules=(),
                    settings={},
                )
                result = asyncio.run(run_verification_wave(config))
            assert result.state == "INSUFFICIENT_EVIDENCE"
            assert result.evidence == ()

    def test_differential_without_baseline_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as candidate:
            with _new_session() as session:
                config = VerificationRunConfig(
                    session=session,
                    plan=_plan(),
                    actor=_actor(),
                    candidate_root=candidate,
                    claim_ids=(uuid.uuid4(),),
                    modules=(ModuleType.DIFFERENTIAL_EXECUTION,),
                    settings={},
                )
                result = asyncio.run(run_verification_wave(config))
            assert result.state == "BLOCKED"
            assert any(
                module.status == ModuleStatus.BLOCKED for module in result.modules
            )

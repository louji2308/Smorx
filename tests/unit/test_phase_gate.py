"""Unit tests for the ``phase_gate`` Phase-0 gate.

The pure helpers ``structure_checks`` and ``finalize_phase0`` are tested
against fake repository structures so no dependency on the parallel packages
is required. The real ``evaluate_phase0`` is exercised only in one guarded
smoke test that is skipped when ``smorx_contracts`` is not yet importable.
"""

from __future__ import annotations

from pathlib import Path

import phase_gate
import pytest


def _make_full_structure(root: Path) -> None:
    for rel in phase_gate.REQUIRED_PATHS:
        (root / rel).mkdir(parents=True, exist_ok=True)


def test_structure_checks_pass_when_complete(tmp_path: Path) -> None:
    _make_full_structure(tmp_path)

    results = phase_gate.structure_checks(tmp_path)

    assert results, "structure check must report each required path"
    assert all(check.passed for check in results)


def test_structure_checks_report_missing_path(tmp_path: Path) -> None:
    _make_full_structure(tmp_path)
    (tmp_path / "packages" / "evidence").rmdir()

    results = phase_gate.structure_checks(tmp_path)

    failed = [check for check in results if not check.passed]
    assert failed, "missing packages/evidence must be reported"
    assert any("packages/evidence" in check.detail for check in failed)


def test_structure_checks_report_missing_nested_path(tmp_path: Path) -> None:
    _make_full_structure(tmp_path)
    for child in ("nebius", "docker"):
        (tmp_path / "infrastructure" / child).rmdir()
    (tmp_path / "infrastructure").rmdir()
    (tmp_path / "infrastructure").mkdir()

    results = phase_gate.structure_checks(tmp_path)

    failed = [check for check in results if not check.passed]
    assert any("infrastructure/nebius" in check.detail for check in failed)


def test_finalize_all_pass_is_pass() -> None:
    checks = [
        phase_gate.GateCheckResult("a", True, "ok"),
        phase_gate.GateCheckResult(
            "health_live", True, "live health check skipped (pass --live)"
        ),
    ]

    result = phase_gate.finalize_phase0(checks)

    assert result.status == "PHASE_0_PASS"
    assert result.failures == []
    assert result.phase == "0"
    assert result.evidence == {
        "a": "ok",
        "health_live": "live health check skipped (pass --live)",
    }


def test_finalize_any_failure_blocks() -> None:
    checks = [
        phase_gate.GateCheckResult("structure", True, "present"),
        phase_gate.GateCheckResult("contracts", False, "smorx_contracts import failed"),
    ]

    result = phase_gate.finalize_phase0(checks)

    assert result.status == "PHASE_0_BLOCKED"
    assert result.failures == ["contracts: smorx_contracts import failed"]


def test_finalize_empty_checks_is_pass() -> None:
    result = phase_gate.finalize_phase0([])

    assert result.status == "PHASE_0_PASS"
    assert result.failures == []


def test_finalize_phase3_all_pass_is_pass() -> None:
    checks = [
        phase_gate.GateCheckResult("phase3_structure", True, "present"),
        phase_gate.GateCheckResult("phase3_tests", True, "exit=0"),
        phase_gate.GateCheckResult("phase3_quality", True, "ruff + mypy clean"),
    ]

    result = phase_gate.finalize_phase3(checks)

    assert result.status == "PHASE_3_PASS"
    assert result.failures == []
    assert result.phase == "3"


def test_finalize_phase3_any_failure_blocks() -> None:
    checks = [
        phase_gate.GateCheckResult("phase3_imports", True, "ok"),
        phase_gate.GateCheckResult("phase3_tests", False, "exit=4: files missing"),
    ]

    result = phase_gate.finalize_phase3(checks)

    assert result.status == "PHASE_3_BLOCKED"
    assert result.failures == ["phase3_tests: exit=4: files missing"]


def test_finalize_phase4_all_pass_is_pass() -> None:
    checks = [
        phase_gate.GateCheckResult("phase4_imports", True, "ControlPlane ok"),
        phase_gate.GateCheckResult("phase4_tests", True, "exit=0"),
    ]

    result = phase_gate.finalize_phase4(checks)

    assert result.status == "PHASE_4_PASS"
    assert result.failures == []
    assert result.phase == "4"


def test_finalize_phase4_any_failure_blocks() -> None:
    checks = [
        phase_gate.GateCheckResult("phase4_quality", True, "clean"),
        phase_gate.GateCheckResult(
            "phase4_structure", False, "missing: packages/tools"
        ),
    ]

    result = phase_gate.finalize_phase4(checks)

    assert result.status == "PHASE_4_BLOCKED"
    assert result.failures == ["phase4_structure: missing: packages/tools"]


def test_evaluate_phase3_smoke_repo_root() -> None:
    pytest.importorskip("smorx_runtime")

    result = phase_gate.evaluate_phase3(root=phase_gate._repo_root(), live=False)

    assert isinstance(result, phase_gate.PhaseGateResult)
    assert result.status in ("PHASE_3_PASS", "PHASE_3_BLOCKED")


def test_evaluate_phase4_smoke_repo_root() -> None:
    pytest.importorskip("smorx_runtime")
    pytest.importorskip("smorx_tools")

    result = phase_gate.evaluate_phase4(root=phase_gate._repo_root(), live=False)

    assert isinstance(result, phase_gate.PhaseGateResult)
    assert result.status in ("PHASE_4_PASS", "PHASE_4_BLOCKED")


def test_evaluate_phase0_smoke_with_contracts(tmp_path: Path) -> None:
    pytest.importorskip("smorx_contracts")
    _make_full_structure(tmp_path)

    result = phase_gate.evaluate_phase0(root=tmp_path, live=False)

    assert isinstance(result, phase_gate.PhaseGateResult)
    assert result.status in ("PHASE_0_PASS", "PHASE_0_BLOCKED")
    contracts = next(check for check in result.checks if check.name == "contracts")
    assert contracts.passed is True
    health = next(check for check in result.checks if check.name == "health_live")
    assert "skipped" in health.detail


def test_finalize_phase910_all_pass_is_pass() -> None:
    checks = [
        phase_gate.GateCheckResult("phase9_structure", True, "present"),
        phase_gate.GateCheckResult("phase9_imports", True, "surface importable"),
        phase_gate.GateCheckResult("phase910_tests", True, "exit=0"),
    ]

    result = phase_gate.finalize_phase910(
        checks, started_at="2026-01-01T00:00:00+00:00"
    )

    assert result.status == "PHASE_910_PASS"
    assert result.failures == []


def test_finalize_phase910_any_failure_blocks() -> None:
    checks = [
        phase_gate.GateCheckResult("phase10_imports", True, "ok"),
        phase_gate.GateCheckResult("phase10_quality", False, "ruff exit=1"),
    ]

    result = phase_gate.finalize_phase910(
        checks, started_at="2026-01-01T00:00:00+00:00"
    )

    assert result.status == "PHASE_910_BLOCKED"
    assert result.failures == ["phase10_quality: ruff exit=1"]


def test_evaluate_phase9_smoke_repo_root() -> None:
    pytest.importorskip("smorx_verification")

    result = phase_gate.evaluate_phase9(root=phase_gate._repo_root(), live=False)

    assert isinstance(result, phase_gate.PhaseGateResult)
    assert result.status in ("PHASE_9_PASS", "PHASE_9_BLOCKED")


def test_evaluate_phase10_smoke_repo_root() -> None:
    pytest.importorskip("smorx_delta")

    result = phase_gate.evaluate_phase10(root=phase_gate._repo_root(), live=False)

    assert isinstance(result, phase_gate.PhaseGateResult)
    assert result.status in ("PHASE_10_PASS", "PHASE_10_BLOCKED")

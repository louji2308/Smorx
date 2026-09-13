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

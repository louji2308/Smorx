"""Machine-executable phase gates for the Software Evolution Intelligence System.

    python scripts/phase_gate.py [--phase 0|2|3|4|7|8|9|10|11|12] [--live] [--json]

Evaluates a phase exit gate and emits ``PHASE_N_PASS`` or ``PHASE_N_BLOCKED``
with a machine-readable evidence map. Exit code is ``0`` only for ``PASS``.

* Phase 0 — repository structure, contracts, quality, env, health.
* Phase 2 — behavioral data model: contracts importable, ``smorx_behavior``
  packages, migration revision present, full Phase-2 test suites green, quality
  gate extended to ``packages/behavior``.
* Phase 3 — orchestrator runtime: ``smorx_runtime`` structure, imported
  orchestrator/graph/waves/toolgate symbols, Phase-3 unit/integration suites
  green, ruff+format+mypy clean (with ``MYPYPATH``).
* Phase 4 — tool/control plane: ``smorx_tools`` structure, ``ControlPlane``
  satisfying ``CapabilityGateway``, Phase-4 unit/security/integration suites
  green, ruff+format+mypy clean.
* Phase 9 — independent verification: ``smorx_verification`` structure,
  importable verification surface with ``classify_claim`` truth table, joint
  Phase 9/10 suites green, quality clean.
* Phase 10 — behavioral delta / intent / certification: ``smorx_delta``
  structure, BLOCKED-handoff barrier enforced, joint Phase 9/10 suites green,
  quality clean.
* Phase 11 — certification: ``smorx_certification`` structure, certification
  surface importable (alignment/reverify/merge-gate/integrity/memory/
  archaeology), joint Phase 11/12 suites green, quality clean.
* Phase 12 — workflow: ``smorx_workflow`` structure, workflow surface
  importable (orchestrate/chaining/replay/reliability/failure-inject), joint
  Phase 11/12 suites green, quality clean.

The pure helpers ``structure_checks``, ``finalize_phase0``, ``finalize_phase2``,
``finalize_phase3``, ``finalize_phase4``, ``finalize_phase78``,
``finalize_phase910`` and ``finalize_phase1112`` are exported so
they can be exercised by unit tests without depending on the parallel packages
landed by other agents.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import env_check
import quality_gate

REQUIRED_PATHS: tuple[str, ...] = (
    "apps/api/app",
    "apps/web",
    "packages/contracts",
    "packages/agent-runtime",
    "packages/tools",
    "packages/evidence",
    "packages/behavior",
    "packages/verification",
    "packages/ui",
    "tests/unit",
    "tests/integration",
    "tests/e2e",
    "tests/security",
    "tests/evaluation",
    "docs/adr",
    "scripts",
    "infrastructure/docker",
    "infrastructure/nebius",
    ".github/workflows",
)

PHASE2_PATHS: tuple[str, ...] = (
    "packages/behavior/src/smorx_behavior/db",
    "packages/behavior/src/smorx_behavior/models",
    "packages/behavior/src/smorx_behavior/evidence",
    "packages/behavior/src/smorx_behavior/versioning",
    "packages/behavior/src/smorx_behavior/repo",
    "packages/behavior/src/smorx_behavior/seed",
    "packages/behavior/migrations/versions",
    "packages/contracts/src/smorx_contracts",
    "tests/unit/test_models.py",
    "tests/unit/test_evidence.py",
    "tests/unit/test_versioning.py",
    "tests/integration/test_references.py",
    "tests/integration/test_certificate.py",
    "tests/integration/test_lifecycle.py",
)

PHASE3_PATHS: tuple[str, ...] = (
    "packages/agent-runtime/src/smorx_runtime",
    "tests/unit/test_agents.py",
    "tests/unit/test_graph.py",
    "tests/unit/test_waves.py",
    "tests/unit/test_telemetry.py",
    "tests/unit/test_orchestrator.py",
    "tests/integration/test_phase3_phase4_integration.py",
)

PHASE4_PATHS: tuple[str, ...] = (
    "packages/tools/src/smorx_tools",
    "tests/unit/test_tool_layer.py",
    "tests/unit/test_policy_control_plane.py",
    "tests/unit/test_sandbox_human_repo.py",
    "tests/security/test_adversarial_guardrails.py",
    "tests/integration/test_phase3_phase4_integration.py",
)

PHASE7_PATHS: tuple[str, ...] = (
    "packages/precode/src/smorx_precode",
    "tests/unit/test_precode_change_definition.py",
    "tests/unit/test_precode_intent_compiler.py",
    "tests/unit/test_precode_intent_ledger.py",
    "tests/unit/test_precode_impact_and_plan.py",
    "tests/unit/test_precode_lock_gate.py",
    "tests/security/test_precode_adversarial.py",
    "tests/integration/test_phase7_phase8_flow.py",
)

PHASE8_PATHS: tuple[str, ...] = (
    "packages/develop/src/smorx_develop",
    "tests/unit/test_develop_barrier_handoff.py",
    "tests/unit/test_develop_sandbox_execution.py",
    "tests/unit/test_develop_loop.py",
    "tests/integration/test_phase7_phase8_flow.py",
)

PHASE9_PATHS: tuple[str, ...] = (
    "packages/verification/src/smorx_verification",
    "packages/verification/pyproject.toml",
    "tests/unit/test_verification_trust.py",
    "tests/unit/test_verification_wave.py",
    "tests/integration/test_phase9_phase10_flow.py",
)

PHASE10_PATHS: tuple[str, ...] = (
    "packages/delta/src/smorx_delta",
    "packages/delta/pyproject.toml",
    "tests/unit/test_delta_core.py",
    "tests/integration/test_phase9_phase10_flow.py",
)

PHASE11_PATHS: tuple[str, ...] = (
    "packages/certification/src/smorx_certification",
    "packages/certification/pyproject.toml",
    "tests/unit/test_certification_archaeology.py",
    "tests/unit/test_certification_memory.py",
    "tests/unit/test_certification_merge_gate.py",
)

PHASE12_PATHS: tuple[str, ...] = (
    "packages/workflow/src/smorx_workflow",
    "packages/workflow/pyproject.toml",
    "tests/unit/test_workflow_orchestrate.py",
    "tests/unit/test_workflow_replay.py",
    "tests/unit/test_workflow_reliability.py",
    "tests/unit/test_workflow_failure_inject.py",
    "tests/unit/workflow_helpers.py",
)

_SRC_PATHS: tuple[str, ...] = (
    "packages/contracts/src",
    "packages/behavior/src",
    "packages/agent-runtime/src",
    "packages/tools/src",
    "packages/precode/src",
    "packages/develop/src",
    "packages/verification/src",
    "packages/delta/src",
    "packages/certification/src",
    "packages/workflow/src",
)

PHASE2_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_models.py",
    "tests/unit/test_db_infra.py",
    "tests/unit/test_evidence.py",
    "tests/unit/test_versioning.py",
    "tests/integration",
)

PHASE3_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_agents.py",
    "tests/unit/test_graph.py",
    "tests/unit/test_waves.py",
    "tests/unit/test_telemetry.py",
    "tests/unit/test_orchestrator.py",
    "tests/integration/test_phase3_phase4_integration.py",
)

PHASE4_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_tool_layer.py",
    "tests/unit/test_policy_control_plane.py",
    "tests/unit/test_sandbox_human_repo.py",
    "tests/security/test_adversarial_guardrails.py",
    "tests/integration/test_phase3_phase4_integration.py",
)

PHASE7_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_precode_change_definition.py",
    "tests/unit/test_precode_intent_compiler.py",
    "tests/unit/test_precode_intent_ledger.py",
    "tests/unit/test_precode_impact_and_plan.py",
    "tests/unit/test_precode_lock_gate.py",
    "tests/security/test_precode_adversarial.py",
)

PHASE8_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_develop_barrier_handoff.py",
    "tests/unit/test_develop_sandbox_execution.py",
    "tests/unit/test_develop_loop.py",
    "tests/integration/test_phase7_phase8_flow.py",
)

PHASE9_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_verification_trust.py",
    "tests/unit/test_verification_wave.py",
)

PHASE10_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_delta_core.py",
    "tests/integration/test_phase9_phase10_flow.py",
)

PHASE11_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_certification_archaeology.py",
    "tests/unit/test_certification_memory.py",
    "tests/unit/test_certification_merge_gate.py",
)

PHASE12_TEST_SUITES: tuple[str, ...] = (
    "tests/unit/test_workflow_orchestrate.py",
    "tests/unit/test_workflow_replay.py",
    "tests/unit/test_workflow_reliability.py",
    "tests/unit/test_workflow_failure_inject.py",
    "tests/unit/test_certification_merge_gate.py",
)

PHASE2_MYPY_TARGETS: tuple[str, ...] = (
    "packages/contracts",
    "packages/behavior",
)

PHASE3_MYPY_TARGETS: tuple[str, ...] = (
    "packages/agent-runtime",
    "packages/tools",
)

PHASE4_MYPY_TARGETS: tuple[str, ...] = ("packages/tools",)

PHASE7_MYPY_TARGETS: tuple[str, ...] = ("packages/precode",)

PHASE8_MYPY_TARGETS: tuple[str, ...] = (
    "packages/precode",
    "packages/develop",
)

PHASE9_MYPY_TARGETS: tuple[str, ...] = ("packages/verification",)

PHASE10_MYPY_TARGETS: tuple[str, ...] = (
    "packages/verification",
    "packages/delta",
)

PHASE11_MYPY_TARGETS: tuple[str, ...] = ("packages/certification",)

PHASE12_MYPY_TARGETS: tuple[str, ...] = (
    "packages/certification",
    "packages/workflow",
)

_CONTRACT_COUNT = 17
_HEALTH_URL = "http://127.0.0.1:8765/health"
_HEALTH_TIMEOUT_SECONDS = 30


@dataclass
class GateCheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class PhaseGateResult:
    phase: str = "0"
    status: str = "PHASE_0_PASS"
    checks: list[GateCheckResult] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    evidence: dict[str, str] = field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_root() -> Path:
    start = Path(__file__).resolve().parent.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def _run(
    cmd: Sequence[str],
    cwd: Path,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, f"failed to run: {exc}"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _build_mypy_env(root: Path) -> dict[str, str]:
    """Environment with ``MYPYPATH`` pointing at the parallel ``src`` trees.

    Required whenever the packages are not pip-installed so mypy can resolve
    ``smorx_contracts``, ``smorx_runtime``, ``smorx_behavior`` and
    ``smorx_tools``.
    """
    env = dict(os.environ)
    env["MYPYPATH"] = os.pathsep.join(
        str((root / rel).resolve())
        for rel in (
            "packages/contracts/src",
            "packages/agent-runtime/src",
            "packages/behavior/src",
            "packages/tools/src",
            "packages/precode/src",
            "packages/develop/src",
            "packages/verification/src",
            "packages/delta/src",
            "packages/certification/src",
            "packages/workflow/src",
        )
    )
    return env


def _tail(output: str, limit: int = 2) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return " | ".join(lines[-limit:])[:500] if lines else "(no output)"


def structure_checks(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-0 directory structure; absent paths are failures."""
    results: list[GateCheckResult] = []
    for rel in REQUIRED_PATHS:
        if (root / rel).exists():
            results.append(GateCheckResult("structure", True, f"present: {rel}"))
        else:
            results.append(GateCheckResult("structure", False, f"missing: {rel}"))
    return results


def finalize_phase0(
    checks: Sequence[GateCheckResult],
    *,
    phase: str = "0",
    started_at: str | None = None,
) -> PhaseGateResult:
    """Derive the Phase-0 gate status from the collected checks."""
    return finalize(checks, phase=phase, started_at=started_at)


def finalize_phase2(
    checks: Sequence[GateCheckResult],
    *,
    phase: str = "2",
    started_at: str | None = None,
) -> PhaseGateResult:
    """Derive the Phase-2 gate status from the collected checks."""
    return finalize(checks, phase=phase, started_at=started_at)


def finalize_phase3(
    checks: Sequence[GateCheckResult],
    *,
    phase: str = "3",
    started_at: str | None = None,
) -> PhaseGateResult:
    """Derive the Phase-3 gate status from the collected checks."""
    return finalize(checks, phase=phase, started_at=started_at)


def finalize_phase4(
    checks: Sequence[GateCheckResult],
    *,
    phase: str = "4",
    started_at: str | None = None,
) -> PhaseGateResult:
    """Derive the Phase-4 gate status from the collected checks."""
    return finalize(checks, phase=phase, started_at=started_at)


def finalize(
    checks: Sequence[GateCheckResult],
    *,
    phase: str,
    started_at: str | None = None,
) -> PhaseGateResult:
    """Derive the gate status from the collected checks (shared core)."""
    failures = [f"{check.name}: {check.detail}" for check in checks if not check.passed]
    status = f"PHASE_{phase}_PASS" if not failures else f"PHASE_{phase}_BLOCKED"
    evidence = {check.name: check.detail for check in checks}
    return PhaseGateResult(
        phase=phase,
        status=status,
        checks=list(checks),
        failures=failures,
        started_at=started_at or _utc_now(),
        finished_at=_utc_now(),
        evidence=evidence,
    )


def _check_contracts() -> GateCheckResult:
    try:
        contracts = importlib.import_module("smorx_contracts")
    except ImportError as exc:
        return GateCheckResult(
            "contracts", False, f"smorx_contracts import failed: {exc}"
        )
    try:
        names = tuple(contracts.CONTRACT_NAMES)
        if len(names) != _CONTRACT_COUNT:
            return GateCheckResult(
                "contracts",
                False,
                f"CONTRACT_NAMES length {len(names)} != {_CONTRACT_COUNT}",
            )
        registry = contracts.get_registry()
        validate = getattr(registry, "validate", None) or contracts.validate_contract
        for name in names:
            instance = contracts.sample_instance(name)
            validate(name, instance)
            registry.schema_for(name)
        return GateCheckResult(
            "contracts", True, f"all {len(names)} contracts validated"
        )
    except Exception as exc:  # noqa: BLE001 - gate must capture any contract failure
        return GateCheckResult("contracts", False, f"contract validation failed: {exc}")


def _check_state_machine_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_state_machine.py",
            "tests/unit/test_loop_controls.py",
            "-q",
        ],
        root,
    )
    return GateCheckResult(
        "state_machine_tests", code == 0, f"exit={code}: {_tail(output)}"
    )


def _check_contract_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [sys.executable, "-m", "pytest", "tests/unit/test_contracts", "-q"], root
    )
    return GateCheckResult("contract_tests", code == 0, f"exit={code}: {_tail(output)}")


def _check_quality(root: Path) -> GateCheckResult:
    ruff = quality_gate.resolve_tool("ruff", root)
    if ruff is None:
        return GateCheckResult("quality", False, "ruff executable not found")
    lint_code, lint_output = _run(
        [ruff, "check", "scripts", "tests", "conftest.py"], root, timeout=240
    )
    mypy = quality_gate.resolve_tool("mypy", root)
    mypy_tool = [mypy] if mypy else [sys.executable, "-m", "mypy"]
    mypy_code, mypy_output = _run(
        [*mypy_tool, "packages/contracts", "packages/agent-runtime"],
        root,
        timeout=300,
        env=_build_mypy_env(root),
    )
    if lint_code != 0 or mypy_code != 0:
        return GateCheckResult(
            "quality",
            False,
            f"ruff exit={lint_code} ({_tail(lint_output)}) | mypy exit={mypy_code} ({_tail(mypy_output)})",
        )
    return GateCheckResult("quality", True, "ruff check + mypy clean")


def _check_phase2_structure(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-2 module/test home layout; absent paths are failures."""
    return [
        GateCheckResult("phase2_structure", (root / rel).exists(), f"present: {rel}")
        for rel in PHASE2_PATHS
    ]


def _check_phase2_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [sys.executable, "-m", "pytest", *PHASE2_TEST_SUITES, "-q"], root, timeout=600
    )
    return GateCheckResult("phase2_tests", code == 0, f"exit={code}: {_tail(output)}")


def _check_phase2_quality(root: Path) -> GateCheckResult:
    ruff = quality_gate.resolve_tool("ruff", root)
    if ruff is None:
        return GateCheckResult("phase2_quality", False, "ruff executable not found")
    lint_code, lint_output = _run(
        [
            ruff,
            "check",
            "packages/contracts",
            "packages/behavior",
            "tests/unit/test_models.py",
            "tests/unit/test_evidence.py",
            "tests/unit/test_versioning.py",
            "tests/integration",
        ],
        root,
        timeout=240,
    )
    mypy = quality_gate.resolve_tool("mypy", root)
    mypy_tool = [mypy] if mypy else [sys.executable, "-m", "mypy"]
    mypy_code, mypy_output = _run(
        [*mypy_tool, *PHASE2_MYPY_TARGETS],
        root,
        timeout=300,
        env=_build_mypy_env(root),
    )
    if lint_code != 0 or mypy_code != 0:
        return GateCheckResult(
            "phase2_quality",
            False,
            f"ruff exit={lint_code} ({_tail(lint_output)}) | mypy exit={mypy_code} ({_tail(mypy_output)})",
        )
    return GateCheckResult("phase2_quality", True, "ruff check + mypy clean")


def _check_phase3_structure(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-3 module/test home layout; absent paths are failures."""
    return [
        GateCheckResult("phase3_structure", (root / rel).exists(), f"present: {rel}")
        for rel in PHASE3_PATHS
    ]


def _check_phase4_structure(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-4 module/test home layout; absent paths are failures."""
    return [
        GateCheckResult("phase4_structure", (root / rel).exists(), f"present: {rel}")
        for rel in PHASE4_PATHS
    ]


def _check_phase3_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [sys.executable, "-m", "pytest", *PHASE3_TEST_SUITES, "-q"],
        root,
        timeout=600,
    )
    return GateCheckResult("phase3_tests", code == 0, f"exit={code}: {_tail(output)}")


def _check_phase4_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [sys.executable, "-m", "pytest", *PHASE4_TEST_SUITES, "-q"],
        root,
        timeout=600,
    )
    return GateCheckResult("phase4_tests", code == 0, f"exit={code}: {_tail(output)}")


def _check_quality_for(
    root: Path,
    *,
    ruff_targets: Sequence[str],
    mypy_targets: Sequence[str],
    name: str = "quality",
) -> GateCheckResult:
    """Parameterized phase quality gate: ruff check+format plus mypy.

    mypy runs with ``MYPYPATH`` so every phase gate type-checks correctly even
    when the packages are not pip-installed.
    """
    ruff = quality_gate.resolve_tool("ruff", root)
    if ruff is None:
        return GateCheckResult(name, False, "ruff executable not found")
    lint_code, lint_output = _run([ruff, "check", *ruff_targets], root, timeout=240)
    format_code, format_output = _run(
        [ruff, "format", "--check", *ruff_targets], root, timeout=240
    )
    mypy = quality_gate.resolve_tool("mypy", root)
    mypy_tool = [mypy] if mypy else [sys.executable, "-m", "mypy"]
    mypy_code, mypy_output = _run(
        [*mypy_tool, *mypy_targets],
        root,
        timeout=300,
        env=_build_mypy_env(root),
    )
    if lint_code != 0 or format_code != 0 or mypy_code != 0:
        return GateCheckResult(
            name,
            False,
            f"ruff exit={lint_code} ({_tail(lint_output)}) | "
            f"ruff-format exit={format_code} ({_tail(format_output)}) | "
            f"mypy exit={mypy_code} ({_tail(mypy_output)})",
        )
    return GateCheckResult(name, True, "ruff check + format + mypy clean")


def _check_phase3_quality(root: Path) -> GateCheckResult:
    ruff_targets = ("packages/agent-runtime", *PHASE3_TEST_SUITES)
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE3_MYPY_TARGETS,
        name="phase3_quality",
    )


def _check_phase4_quality(root: Path) -> GateCheckResult:
    ruff_targets = ("packages/tools", *PHASE4_TEST_SUITES)
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE4_MYPY_TARGETS,
        name="phase4_quality",
    )


def _check_phase7_quality(root: Path) -> GateCheckResult:
    ruff_targets = ("packages/precode", *PHASE7_TEST_SUITES)
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE7_MYPY_TARGETS,
        name="phase7_quality",
    )


def _check_phase8_quality(root: Path) -> GateCheckResult:
    ruff_targets = ("packages/develop", *PHASE8_TEST_SUITES)
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE8_MYPY_TARGETS,
        name="phase8_quality",
    )


def _check_phase78_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            *PHASE7_TEST_SUITES,
            *PHASE8_TEST_SUITES,
            "-q",
        ],
        root,
        timeout=900,
    )
    return GateCheckResult("phase78_tests", code == 0, f"exit={code}: {_tail(output)}")


def _check_phase7_imports(root: Path) -> GateCheckResult:
    """Verify the Phase-7 pre-coding surface imports (in-process)."""
    del root
    try:
        required = {
            "smorx_precode.change_definition": "define_change",
            "smorx_precode.intent_ledger": "lock_intent_ledger",
            "smorx_precode.impact": "build_semantic_impact",
            "smorx_precode.verification_plan": "build_verification_plan",
            "smorx_precode.lock_gate": "pre_coding_gate",
        }
        missing: list[str] = []
        for module_name, attr in required.items():
            module = importlib.import_module(module_name)
            if not hasattr(module, attr):
                missing.append(f"{module_name}.{attr}")
        if missing:
            return GateCheckResult(
                "phase7_imports", False, "missing symbols: " + ", ".join(missing)
            )
    except Exception as exc:  # noqa: BLE001 - gate must capture any import failure
        return GateCheckResult("phase7_imports", False, f"import failed: {exc}")
    return GateCheckResult(
        "phase7_imports", True, "change definition/ledger/impact/plan/gate importable"
    )


def _check_phase8_imports(root: Path) -> GateCheckResult:
    """Verify the Phase-8 develop surface imports and the barrier refuses
    unauthenticated handoff types (in-process, no sandbox)."""
    del root
    try:
        required = {
            "smorx_develop.handoff": "pre_coding_handoff",
            "smorx_develop.barrier": "ExecutionBarrier",
            "smorx_develop.agent": "CodingAgentLoop",
            "smorx_develop.candidates": "compare_candidates",
            "smorx_develop.trace": "verify_trace_integrity",
            "smorx_develop.sandbox": "DevelopmentSandbox",
        }
        missing: list[str] = []
        for module_name, attr in required.items():
            module = importlib.import_module(module_name)
            if not hasattr(module, attr):
                missing.append(f"{module_name}.{attr}")
        if missing:
            return GateCheckResult(
                "phase8_imports", False, "missing symbols: " + ", ".join(missing)
            )
        from smorx_develop.handoff import HandoffError, pre_coding_handoff

        try:
            pre_coding_handoff(None, context={"lock_state": "LOCKED"})  # type: ignore[arg-type]
        except HandoffError:
            pass
        else:
            return GateCheckResult(
                "phase8_imports",
                False,
                "handoff accepted a non-PreCodingContext object",
            )
    except Exception as exc:  # noqa: BLE001
        return GateCheckResult("phase8_imports", False, f"import failed: {exc}")
    return GateCheckResult(
        "phase8_imports", True, "handoff/barrier/loop/candidates/trace importable"
    )


def _check_phase78_structure(root: Path) -> list[GateCheckResult]:
    results: list[GateCheckResult] = []
    for label, paths in (
        ("phase7_structure", PHASE7_PATHS),
        ("phase8_structure", PHASE8_PATHS),
    ):
        missing = [rel for rel in paths if not (root / rel).exists()]
        if missing:
            results.append(
                GateCheckResult(label, False, "missing: " + ", ".join(missing))
            )
        else:
            results.append(
                GateCheckResult(label, True, f"all {len(paths)} required paths present")
            )
    return results


def _check_phase9_structure(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-9 module/test home layout; absent paths are failures."""
    return [
        GateCheckResult("phase9_structure", (root / rel).exists(), f"present: {rel}")
        for rel in PHASE9_PATHS
    ]


def _check_phase10_structure(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-10 module/test home layout; absent paths are failures."""
    return [
        GateCheckResult("phase10_structure", (root / rel).exists(), f"present: {rel}")
        for rel in PHASE10_PATHS
    ]


def _check_phase11_structure(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-11 module/test home layout; absent paths are failures."""
    return [
        GateCheckResult("phase11_structure", (root / rel).exists(), f"present: {rel}")
        for rel in PHASE11_PATHS
    ]


def _check_phase12_structure(root: Path) -> list[GateCheckResult]:
    """Verify the Phase-12 module/test home layout; absent paths are failures."""
    return [
        GateCheckResult("phase12_structure", (root / rel).exists(), f"present: {rel}")
        for rel in PHASE12_PATHS
    ]


def _check_phase9_quality(root: Path) -> GateCheckResult:
    ruff_targets = (
        "packages/verification",
        *PHASE9_TEST_SUITES,
        "tests/integration/test_phase9_phase10_flow.py",
    )
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE9_MYPY_TARGETS,
        name="phase9_quality",
    )


def _check_phase10_quality(root: Path) -> GateCheckResult:
    ruff_targets = ("packages/delta", *PHASE10_TEST_SUITES)
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE10_MYPY_TARGETS,
        name="phase10_quality",
    )


def _check_phase11_quality(root: Path) -> GateCheckResult:
    ruff_targets = ("packages/certification", *PHASE11_TEST_SUITES)
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE11_MYPY_TARGETS,
        name="phase11_quality",
    )


def _check_phase12_quality(root: Path) -> GateCheckResult:
    ruff_targets = (
        "packages/certification",
        "packages/workflow",
        *PHASE12_TEST_SUITES,
    )
    return _check_quality_for(
        root,
        ruff_targets=ruff_targets,
        mypy_targets=PHASE12_MYPY_TARGETS,
        name="phase12_quality",
    )


def _check_phase910_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            *PHASE9_TEST_SUITES,
            *PHASE10_TEST_SUITES,
            "-q",
        ],
        root,
        timeout=900,
    )
    return GateCheckResult("phase910_tests", code == 0, f"exit={code}: {_tail(output)}")


def _check_phase1112_tests(root: Path) -> GateCheckResult:
    code, output = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            *PHASE11_TEST_SUITES,
            *PHASE12_TEST_SUITES,
            "-q",
        ],
        root,
        timeout=900,
    )
    return GateCheckResult("phase1112_tests", code == 0, f"exit={code}: {_tail(output)}")


def _check_phase9_imports(root: Path) -> GateCheckResult:
    """Verify the Phase-9 verification surface imports (in-process)."""
    del root
    try:
        required = {
            "smorx_verification.contracts": ("VerificationResult", "classify_claim"),
            "smorx_verification.runner": (
                "VerificationRunConfig",
                "run_verification_wave",
            ),
            "smorx_verification.boundary": (
                "authorize_verification_actor",
                "guard_candidate_mutation",
            ),
            "smorx_verification.fusion": ("fuse_claim_evidence", "modules_passed"),
            "smorx_verification.control_center": ("ControlCenterModel",),
            "smorx_verification.adversarial": (
                "ADVERSARIAL_CASES",
                "run_adversarial_scenarios",
            ),
            "smorx_verification.static_analysis": ("run_static_analysis",),
            "smorx_verification.differential": ("run_differential_execution",),
            "smorx_verification.ghost_replay": ("run_historical_ghost_replay",),
            "smorx_verification.metamorphic": ("run_metamorphic_checks",),
            "smorx_verification.mutation": ("run_mutation_testing",),
        }
        missing: list[str] = []
        for module_name, attrs in required.items():
            module = importlib.import_module(module_name)
            for attr in attrs:
                if not hasattr(module, attr):
                    missing.append(f"{module_name}.{attr}")
        if missing:
            return GateCheckResult(
                "phase9_imports", False, "missing symbols: " + ", ".join(missing)
            )
        from smorx_verification.contracts import ClaimAssessment, classify_claim

        expected = (
            ((1, 0), ClaimAssessment.SUPPORTING),
            ((0, 1), ClaimAssessment.CONTRADICTING),
            ((1, 1), ClaimAssessment.CONFLICTING),
            ((0, 0), ClaimAssessment.INSUFFICIENT),
        )
        for (supporting, contradicting), expected_assessment in expected:
            actual = classify_claim(supporting=supporting, contradicting=contradicting)
            if actual != expected_assessment:
                return GateCheckResult(
                    "phase9_imports",
                    False,
                    f"classify_claim({supporting}, {contradicting}) returned "
                    f"{actual}, expected {expected_assessment}",
                )
    except Exception as exc:  # noqa: BLE001 - gate must capture any import failure
        return GateCheckResult("phase9_imports", False, f"import failed: {exc}")
    return GateCheckResult(
        "phase9_imports",
        True,
        "verification surface importable; classify_claim truth table ok",
    )


def _check_phase10_imports(root: Path) -> GateCheckResult:
    """Verify the Phase-10 delta surface imports and the handoff barrier
    refuses BLOCKED verification results (in-process, no sandbox)."""
    del root
    try:
        required = {
            "smorx_delta.handoff": ("admit_verification_result", "HandoffBarrierError"),
            "smorx_delta.deltas": ("compute_behavioral_deltas",),
            "smorx_delta.intent": ("evaluate_intent_alignment",),
            "smorx_delta.decision": ("decide_certification", "DecisionCode"),
            "smorx_delta.repair": ("build_repair_package",),
            "smorx_delta.repair_loop": ("run_repair_loop",),
        }
        missing: list[str] = []
        for module_name, attrs in required.items():
            module = importlib.import_module(module_name)
            for attr in attrs:
                if not hasattr(module, attr):
                    missing.append(f"{module_name}.{attr}")
        if missing:
            return GateCheckResult(
                "phase10_imports", False, "missing symbols: " + ", ".join(missing)
            )
        import uuid

        from smorx_delta.handoff import HandoffBarrierError, admit_verification_result
        from smorx_verification.contracts import VerificationResult

        blocked = VerificationResult(
            candidate_id="phase-gate-probe",
            verification_plan_id=uuid.uuid4(),
            plan_version=1,
            run_id="phase-gate-probe-run",
            change_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            modules=(),
            evidence=(),
            claims={},
            contradictions=(),
            state="BLOCKED",
        )
        try:
            admit_verification_result(blocked)
        except HandoffBarrierError:
            pass
        else:
            return GateCheckResult(
                "phase10_imports",
                False,
                "BLOCKED verification was admitted; Phase 10 must not decide",
            )
    except Exception as exc:  # noqa: BLE001 - gate must capture any import failure
        return GateCheckResult("phase10_imports", False, f"import failed: {exc}")
    return GateCheckResult(
        "phase10_imports",
        True,
        "delta surface importable; BLOCKED handoff correctly refused",
    )


def _check_phase11_imports(root: Path) -> GateCheckResult:
    """Verify the Phase-11 certification surface imports (in-process)."""
    del root
    try:
        required = {
            "smorx_certification.alignment": ("evaluate_alignment", "AlignmentVerdict"),
            "smorx_certification.reverify": (
                "run_reverification",
                "ReVerificationReport",
            ),
            "smorx_certification.merge_gate": (
                "evaluate_merge_gate",
                "MergeGateVerdict",
            ),
            "smorx_certification.certificate": ("build_certificate",),
            "smorx_certification.archaeology": ("persist_archaeology",),
            "smorx_certification.memory": ("run_memory_pipeline",),
            "smorx_certification.integrity": (
                "canonical_certificate_payload",
                "compute_integrity_hash",
            ),
        }
        missing: list[str] = []
        for module_name, attrs in required.items():
            module = importlib.import_module(module_name)
            for attr in attrs:
                if not hasattr(module, attr):
                    missing.append(f"{module_name}.{attr}")
        if missing:
            return GateCheckResult(
                "phase11_imports", False, "missing symbols: " + ", ".join(missing)
            )
    except Exception as exc:  # noqa: BLE001 - gate must capture any import failure
        return GateCheckResult("phase11_imports", False, f"import failed: {exc}")
    return GateCheckResult(
        "phase11_imports", True, "certification surface importable"
    )


def _check_phase12_imports(root: Path) -> GateCheckResult:
    """Verify the Phase-12 workflow surface imports (in-process)."""
    del root
    try:
        required = {
            "smorx_workflow.orchestrate": (
                "workflow_id",
                "DEFAULT_PHASES",
                "PHASE_EVENT_KINDS",
                "build_demo_scenario",
                "run_e2e_workflow",
                "run_phases",
            ),
            "smorx_workflow.chaining": (
                "canonical_payload",
                "event_digest",
                "next_sequence",
            ),
            "smorx_workflow.replay": (
                "ordered_events",
                "replay_from_evidence_graph",
                "ReplayResult",
            ),
            "smorx_workflow.reliability": (
                "idempotency_guard",
                "cleanup_stale_sandboxes",
                "resume_workflow",
                "reset_workflow",
                "ReliabilityReport",
            ),
            "smorx_workflow.failure_inject": (
                "inject_failure",
                "FailureInjectionMode",
                "InjectionResult",
            ),
        }
        missing: list[str] = []
        for module_name, attrs in required.items():
            module = importlib.import_module(module_name)
            for attr in attrs:
                if not hasattr(module, attr):
                    missing.append(f"{module_name}.{attr}")
        if missing:
            return GateCheckResult(
                "phase12_imports", False, "missing symbols: " + ", ".join(missing)
            )
    except Exception as exc:  # noqa: BLE001 - gate must capture any import failure
        return GateCheckResult("phase12_imports", False, f"import failed: {exc}")
    return GateCheckResult(
        "phase12_imports", True, "workflow surface importable"
    )


def _check_phase3_imports(root: Path) -> GateCheckResult:
    """Verify the Phase-3 runtime surface imports (in-process)."""
    del root
    try:
        required = {
            "smorx_runtime.orchestrator": "Orchestrator",
            "smorx_runtime.graph": "TaskGraph",
            "smorx_runtime.waves": "ParallelWaveEngine",
            "smorx_runtime.toolgate": "CapabilityGateway",
        }
        missing: list[str] = []
        for module_name, attr in required.items():
            module = importlib.import_module(module_name)
            if not hasattr(module, attr):
                missing.append(f"{module_name}.{attr}")
        if missing:
            return GateCheckResult(
                "phase3_imports", False, "missing symbols: " + ", ".join(missing)
            )
    except Exception as exc:  # noqa: BLE001 - gate must capture any import failure
        return GateCheckResult("phase3_imports", False, f"import failed: {exc}")
    return GateCheckResult(
        "phase3_imports", True, "orchestrator/graph/waves/toolgate symbols importable"
    )


def _check_phase4_imports(root: Path) -> GateCheckResult:
    """Verify ``ControlPlane`` satisfies ``CapabilityGateway`` (in-process).

    Constructs a real ``ControlPlane`` with the documented constructor kwargs
    (registry/engine/audit) — no sandbox, no network, no host mutation.
    """
    del root
    try:
        from smorx_runtime.toolgate import CapabilityGateway
        from smorx_tools.audit import AuditTrail
        from smorx_tools.control import ControlPlane
        from smorx_tools.policies import PolicyEngine
        from smorx_tools.tool import ToolRegistry
    except ImportError as exc:
        return GateCheckResult("phase4_imports", False, f"import failed: {exc}")
    try:
        plane = ControlPlane(
            registry=ToolRegistry(),
            engine=PolicyEngine(),
            audit=AuditTrail(),
        )
        if not isinstance(plane, CapabilityGateway):
            return GateCheckResult(
                "phase4_imports",
                False,
                "ControlPlane does not satisfy smorx_runtime.toolgate.CapabilityGateway",
            )
    except Exception as exc:  # noqa: BLE001 - gate must capture any construct failure
        return GateCheckResult(
            "phase4_imports", False, f"ControlPlane construction failed: {exc}"
        )
    return GateCheckResult(
        "phase4_imports",
        True,
        "ControlPlane(registry, engine, audit) satisfies CapabilityGateway",
    )


def _check_env() -> GateCheckResult:
    declared = (
        os.environ.get("SMORX_APP_ENV") or os.environ.get("APP_ENV") or "development"
    )
    report = env_check.check_environment(os.environ, app_env=declared)
    if report.required_issues:
        details = "; ".join(
            f"{issue.name}: {issue.message}" for issue in report.required_issues
        )
        return GateCheckResult("env", False, details)
    return GateCheckResult("env", True, "no required env issues")


def _wait_for_health(proc: subprocess.Popen[str]) -> tuple[bool, float | None]:
    started = time.monotonic()
    deadline = started + _HEALTH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False, None
        try:
            with urllib.request.urlopen(_HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    return True, round(time.monotonic() - started, 2)
        except OSError:
            time.sleep(0.5)
    return False, None


def _check_health(root: Path, *, live: bool) -> GateCheckResult:
    if not live:
        return GateCheckResult(
            "health_live", True, "live health check skipped (pass --live)"
        )
    api_python = root / "apps" / "api" / ".venv" / "Scripts" / "python.exe"
    if not api_python.is_file():
        api_python = root / "apps" / "api" / ".venv" / "bin" / "python"
    if not api_python.is_file():
        api_python = Path(sys.executable)
    cmd = [
        str(api_python),
        "-m",
        "uvicorn",
        "app.main:create_app",
        "--factory",
        "--app-dir",
        "apps/api",
        "--port",
        "8765",
    ]
    proc = subprocess.Popen(
        cmd, cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        healthy, latency = _wait_for_health(proc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.SubprocessError:
            proc.kill()
    if healthy:
        return GateCheckResult("health_live", True, f"/health OK latency={latency}s")
    return GateCheckResult(
        "health_live",
        False,
        f"API /health did not reply within {_HEALTH_TIMEOUT_SECONDS}s",
    )


def _ensure_src_paths(root: Path) -> None:
    """Make the src packages importable for in-process contract/model checks."""
    for rel in _SRC_PATHS:
        candidate = str((root / rel).resolve())
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def evaluate_phase0(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the full Phase-0 exit gate.

    Args:
        root: Repository root to evaluate. Defaults to the git root.
        live: When True, also boot the API and probe ``/health``.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = list(structure_checks(base))
    checks.append(_check_contracts())
    checks.append(_check_state_machine_tests(base))
    checks.append(_check_contract_tests(base))
    checks.append(_check_quality(base))
    checks.append(_check_env())
    checks.append(_check_health(base, live=live))
    result = finalize_phase0(checks, started_at=started_at)
    result.phase = "0"
    return result


def evaluate_phase2(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the Phase-2 exit gate (behavioral data model & persistence).

    Args:
        root: Repository root to evaluate. Defaults to the git root.
        live: Accepted for CLI symmetry; unused in Phase 2 (no API surface).
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase2_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase2_tests(base))
    checks.append(_check_phase2_quality(base))
    checks.append(_check_env())
    result = finalize_phase2(checks, started_at=started_at)
    result.phase = "2"
    return result


def evaluate_phase3(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the Phase-3 exit gate (orchestrator runtime).

    Args:
        root: Repository root to evaluate. Defaults to the git root.
        live: Accepted for CLI symmetry; unused in Phase 3 (no API surface).
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase3_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase3_imports(base))
    checks.append(_check_phase3_tests(base))
    checks.append(_check_phase3_quality(base))
    checks.append(_check_env())
    result = finalize_phase3(checks, started_at=started_at)
    result.phase = "3"
    return result


def evaluate_phase4(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the Phase-4 exit gate (tool/control plane).

    Args:
        root: Repository root to evaluate. Defaults to the git root.
        live: Accepted for CLI symmetry; unused in Phase 4 (no API surface).
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase4_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase4_imports(base))
    checks.append(_check_phase4_tests(base))
    checks.append(_check_phase4_quality(base))
    checks.append(_check_env())
    result = finalize_phase4(checks, started_at=started_at)
    result.phase = "4"
    return result


def finalize_phase78(
    checks: list[GateCheckResult], *, started_at: str
) -> PhaseGateResult:
    """Shared finalize for the Phase 7/8 gates (same contract, joint suites)."""
    failures = [f"{check.name}: {check.detail}" for check in checks if not check.passed]
    return PhaseGateResult(
        status="PHASE_78_PASS" if not failures else "PHASE_78_BLOCKED",
        checks=checks,
        failures=failures,
        started_at=started_at,
        finished_at=_utc_now(),
    )


def evaluate_phase7(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the Phase-7 exit gate (Define + Analyze / pre-coding lock).

    PASS requires: structure present, contracts importable, pre-coding
    surface importable, all Phase-7 unit/adversarial suites green (which
    include the combined Phase 7→8 flow), quality clean, env clean.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase78_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase7_imports(base))
    checks.append(_check_phase78_tests(base))
    checks.append(_check_phase7_quality(base))
    checks.append(_check_env())
    result = finalize_phase78(checks, started_at=started_at)
    result.phase = "7"
    result.status = result.status.replace("PHASE_78_", "PHASE_7_")
    return result


def evaluate_phase8(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the Phase-8 exit gate (Develop / Coding Agent / sandbox loop).

    PASS requires: structure present, contracts importable, develop surface
    importable with handoff type-enforcement, all Phase-8 suites green
    (including the combined Phase 7→8 flow), quality clean, env clean.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase78_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase8_imports(base))
    checks.append(_check_phase78_tests(base))
    checks.append(_check_phase8_quality(base))
    checks.append(_check_env())
    result = finalize_phase78(checks, started_at=started_at)
    result.phase = "8"
    result.status = result.status.replace("PHASE_78_", "PHASE_8_")
    return result


def finalize_phase910(
    checks: Sequence[GateCheckResult], *, started_at: str
) -> PhaseGateResult:
    """Shared finalize for the Phase 9/10 gates (same contract, joint suites)."""
    failures = [f"{check.name}: {check.detail}" for check in checks if not check.passed]
    return PhaseGateResult(
        status="PHASE_910_PASS" if not failures else "PHASE_910_BLOCKED",
        checks=checks,
        failures=failures,
        started_at=started_at,
        finished_at=_utc_now(),
    )


def evaluate_phase9(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the Phase-9 exit gate (Verify / independent verification).

    PASS requires: structure present, contracts importable, verification
    surface importable with the ``classify_claim`` truth table, all joint
    Phase 9/10 suites green, quality clean, env clean.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase9_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase9_imports(base))
    checks.append(_check_phase910_tests(base))
    checks.append(_check_phase9_quality(base))
    checks.append(_check_env())
    result = finalize_phase910(checks, started_at=started_at)
    result.phase = "9"
    result.status = result.status.replace("PHASE_910_", "PHASE_9_")
    return result


def evaluate_phase10(
    root: Path | None = None, *, live: bool = False
) -> PhaseGateResult:
    """Evaluate the Phase-10 exit gate (Decide/Certify + behavioral delta).

    PASS requires: structure present, contracts importable, delta surface
    importable with the BLOCKED-handoff barrier enforced, all joint Phase 9/10
    suites green, quality clean, env clean.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase10_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase10_imports(base))
    checks.append(_check_phase910_tests(base))
    checks.append(_check_phase10_quality(base))
    checks.append(_check_env())
    result = finalize_phase910(checks, started_at=started_at)
    result.phase = "10"
    result.status = result.status.replace("PHASE_910_", "PHASE_10_")
    return result


def finalize_phase1112(
    checks: Sequence[GateCheckResult], *, started_at: str
) -> PhaseGateResult:
    """Shared finalize for the Phase 11/12 gates (same contract, joint suites)."""
    failures = [f"{check.name}: {check.detail}" for check in checks if not check.passed]
    return PhaseGateResult(
        status="PHASE_1112_PASS" if not failures else "PHASE_1112_BLOCKED",
        checks=checks,
        failures=failures,
        started_at=started_at,
        finished_at=_utc_now(),
    )


def evaluate_phase11(
    root: Path | None = None, *, live: bool = False
) -> PhaseGateResult:
    """Evaluate the Phase-11 exit gate (Certify / certification bindings).

    PASS requires: structure present, contracts importable, certification
    surface importable, all joint Phase 11/12 suites green, quality clean,
    env clean.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase11_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase11_imports(base))
    checks.append(_check_phase1112_tests(base))
    checks.append(_check_phase11_quality(base))
    checks.append(_check_env())
    result = finalize_phase1112(checks, started_at=started_at)
    result.phase = "11"
    result.status = result.status.replace("PHASE_1112_", "PHASE_11_")
    return result


def evaluate_phase12(
    root: Path | None = None, *, live: bool = False
) -> PhaseGateResult:
    """Evaluate the Phase-12 exit gate (workflow / orchestrated journey).

    PASS requires: structure present, contracts importable, workflow surface
    importable, all joint Phase 11/12 suites green, quality clean, env clean.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
    _ensure_src_paths(base)
    checks = []
    checks.extend(_check_phase12_structure(base))
    checks.append(_check_contracts())
    checks.append(_check_phase12_imports(base))
    checks.append(_check_phase1112_tests(base))
    checks.append(_check_phase12_quality(base))
    checks.append(_check_env())
    result = finalize_phase1112(checks, started_at=started_at)
    result.phase = "12"
    result.status = result.status.replace("PHASE_1112_", "PHASE_12_")
    return result


def _print_result(result: PhaseGateResult) -> None:
    print(f"PHASE {result.phase} EXIT GATE")
    for check in result.checks:
        state = "PASS" if check.passed else "FAIL"
        print(f"  {state:5s} {check.name}: {check.detail}")
    print(f"STATUS: {result.status}")
    for failure in result.failures:
        print(f"  BLOCKER: {failure}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a phase exit gate (0, 2, 3, 4, 7, 8, 9, 10, 11, 12)."
    )
    parser.add_argument(
        "--phase",
        type=str,
        choices=("0", "2", "3", "4", "7", "8", "9", "10", "11", "12"),
        default="0",
        help="phase gate to evaluate (default: 0)",
    )
    parser.add_argument(
        "--live", action="store_true", help="also boot the API and probe /health"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    args = parser.parse_args(argv)

    if args.phase == "2":
        result = evaluate_phase2(live=args.live)
    elif args.phase == "3":
        result = evaluate_phase3(live=args.live)
    elif args.phase == "4":
        result = evaluate_phase4(live=args.live)
    elif args.phase == "7":
        result = evaluate_phase7(live=args.live)
    elif args.phase == "8":
        result = evaluate_phase8(live=args.live)
    elif args.phase == "9":
        result = evaluate_phase9(live=args.live)
    elif args.phase == "10":
        result = evaluate_phase10(live=args.live)
    elif args.phase == "11":
        result = evaluate_phase11(live=args.live)
    elif args.phase == "12":
        result = evaluate_phase12(live=args.live)
    else:
        result = evaluate_phase0(live=args.live)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        _print_result(result)
    return 0 if result.status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

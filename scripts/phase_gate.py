"""Machine-executable Phase 0 gate for the Software Evolution Intelligence System.

    python scripts/phase_gate.py [--live] [--json]

Evaluates every Phase-0 exit-gate line item and emits ``PHASE_0_PASS`` or
``PHASE_0_BLOCKED`` with a machine-readable evidence map. Exit code is ``0``
only for ``PHASE_0_PASS``.

The pure helpers ``structure_checks`` and ``finalize_phase0`` are exported so
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


def _run(cmd: Sequence[str], cwd: Path, timeout: int = 300) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, f"failed to run: {exc}"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


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
    """Derive the gate status from the collected checks."""
    failures = [f"{check.name}: {check.detail}" for check in checks if not check.passed]
    status = "PHASE_0_PASS" if not failures else "PHASE_0_BLOCKED"
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
    mypy_code, mypy_output = _run(
        [sys.executable, "-m", "mypy", "packages/contracts", "packages/agent-runtime"],
        root,
        timeout=300,
    )
    if lint_code != 0 or mypy_code != 0:
        return GateCheckResult(
            "quality",
            False,
            f"ruff exit={lint_code} ({_tail(lint_output)}) | mypy exit={mypy_code} ({_tail(mypy_output)})",
        )
    return GateCheckResult("quality", True, "ruff check + mypy clean")


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


def evaluate_phase0(root: Path | None = None, *, live: bool = False) -> PhaseGateResult:
    """Evaluate the full Phase-0 exit gate.

    Args:
        root: Repository root to evaluate. Defaults to the git root.
        live: When True, also boot the API and probe ``/health``.
    """
    started_at = _utc_now()
    base = root.resolve() if root is not None else _repo_root()
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


def _print_result(result: PhaseGateResult) -> None:
    print("PHASE 0 EXIT GATE")
    for check in result.checks:
        state = "PASS" if check.passed else "FAIL"
        print(f"  {state:5s} {check.name}: {check.detail}")
    print(f"STATUS: {result.status}")
    for failure in result.failures:
        print(f"  BLOCKER: {failure}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the Phase-0 exit gate.")
    parser.add_argument(
        "--live", action="store_true", help="also boot the API and probe /health"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    args = parser.parse_args(argv)

    result = evaluate_phase0(live=args.live)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        _print_result(result)
    return 0 if result.status == "PHASE_0_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

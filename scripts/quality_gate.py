"""Development quality gate for the Software Evolution Intelligence System.

One command executes every repository gate in order:

    python scripts/quality_gate.py [--skip-web] [--json]

Every step result carries the real subprocess ``exit_code``; a step is never
fabricated as passing. Exit code of the CLI is ``0`` only when all non-skipped
steps pass.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

QUALITY_STEPS: tuple[str, ...] = (
    "env check",
    "secret scan",
    "dependency audit",
    "format check",
    "lint",
    "typecheck",
    "unit tests",
    "integration tests",
    "security tests",
    "build",
    "web build",
)

_WHITESPACE_STRIPPED_LINES = 3
_SUMMARY_MAX_CHARS = 600


@dataclass
class StepResult:
    step: str
    command: list[str]
    exit_code: int | None
    summary: str
    passed: bool
    skipped: bool


@dataclass
class QualityReport:
    steps: list[StepResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    @property
    def all_passed(self) -> bool:
        return all(step.skipped or step.passed for step in self.steps)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_tool(name: str, root: Path) -> str | None:
    """Resolve a tool executable, preferring the repository venv, then PATH."""
    if os.name == "nt":
        venv_bin = root / ".venv" / "Scripts" / f"{name}.exe"
    else:
        venv_bin = root / ".venv" / "bin" / name
    if venv_bin.is_file():
        return str(venv_bin)
    return shutil.which(name)


def run_command(
    cmd: list[str],
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


def mypy_env(root: Path) -> dict[str, str]:
    """Environment for mypy invocations against the parallel src layouts.

    When packages are not pip-installed (the default local state), mypy must
    resolve ``smorx_contracts``, ``smorx_runtime``, ``smorx_behavior`` and
    ``smorx_tools`` through ``MYPYPATH`` pointing at each ``src`` tree.
    """
    src_dirs = (
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
    env = dict(os.environ)
    env["MYPYPATH"] = os.pathsep.join(str((root / rel).resolve()) for rel in src_dirs)
    return env


def summarize(output: str) -> str:
    lines = [line for line in output.splitlines() if line.strip()][
        :_WHITESPACE_STRIPPED_LINES
    ]
    joined = " | ".join(lines)
    return joined[:_SUMMARY_MAX_CHARS] + (
        "..." if len(joined) > _SUMMARY_MAX_CHARS else ""
    )


def _step_env(root: Path) -> StepResult:
    cmd = [sys.executable, "scripts/validate_env.py"]
    code, output = run_command(cmd, root)
    return StepResult("env check", cmd, code, summarize(output), code == 0, False)


def _step_secret_scan(root: Path) -> StepResult:
    cmd = [sys.executable, "scripts/scan_secrets.py", "--root", str(root)]
    code, output = run_command(cmd, root)
    return StepResult("secret scan", cmd, code, summarize(output), code == 0, False)


def _step_dependency_audit(root: Path) -> StepResult:
    cmd = [sys.executable, "scripts/audit_deps.py"]
    code, output = run_command(cmd, root)
    return StepResult(
        "dependency audit", cmd, code, summarize(output), code == 0, False
    )


def _step_format(root: Path, ruff: str) -> StepResult:
    targets = [
        "scripts",
        "tests",
        "conftest.py",
        "packages/contracts",
        "packages/agent-runtime",
        "packages/behavior",
        "packages/tools",
        "packages/precode",
        "packages/develop",
        "packages/verification",
        "packages/delta",
        "packages/certification",
        "packages/workflow",
    ]
    cmd = [ruff, "format", "--check", *targets]
    code, output = run_command(cmd, root)
    return StepResult("format check", cmd, code, summarize(output), code == 0, False)


def _step_lint(root: Path, ruff: str) -> StepResult:
    targets = [
        "scripts",
        "tests",
        "conftest.py",
        "packages/contracts",
        "packages/agent-runtime",
        "packages/behavior",
        "packages/tools",
        "packages/precode",
        "packages/develop",
        "packages/verification",
        "packages/delta",
        "packages/certification",
        "packages/workflow",
    ]
    cmd = [ruff, "check", *targets]
    code, output = run_command(cmd, root)
    return StepResult("lint", cmd, code, summarize(output), code == 0, False)


def _step_typecheck(root: Path) -> StepResult:
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "packages/contracts",
        "packages/agent-runtime",
        "packages/behavior",
        "packages/tools",
        "packages/precode",
        "packages/develop",
        "packages/verification",
        "packages/delta",
        "packages/certification",
        "packages/workflow",
    ]
    code, output = run_command(cmd, root, env=mypy_env(root))
    return StepResult("typecheck", cmd, code, summarize(output), code == 0, False)


def _step_unit_tests(root: Path) -> StepResult:
    cmd = [sys.executable, "-m", "pytest", "tests/unit"]
    code, output = run_command(cmd, root)
    return StepResult("unit tests", cmd, code, summarize(output), code == 0, False)


def _step_integration_tests(root: Path) -> StepResult:
    cmd = [sys.executable, "-m", "pytest", "tests/integration"]
    code, output = run_command(cmd, root)
    return StepResult(
        "integration tests", cmd, code, summarize(output), code == 0, False
    )


def _step_security_tests(root: Path) -> StepResult:
    cmd = [sys.executable, "-m", "pytest", "tests/security"]
    code, output = run_command(cmd, root)
    return StepResult("security tests", cmd, code, summarize(output), code == 0, False)


def _step_build(root: Path) -> StepResult:
    targets = [
        "packages/contracts",
        "packages/agent-runtime",
        "packages/behavior",
        "packages/tools",
        "packages/precode",
        "packages/develop",
        "packages/verification",
        "packages/delta",
        "packages/certification",
        "packages/workflow",
        "apps/api/app",
    ]
    missing = [target for target in targets if not (root / target).is_dir()]
    existing = [target for target in targets if (root / target).is_dir()]
    if not existing:
        return StepResult(
            "build",
            [],
            None,
            "no build targets present: " + ", ".join(missing),
            False,
            False,
        )
    cmd = [sys.executable, "-m", "compileall", "-q", *existing]
    code, output = run_command(cmd, root)
    summary = summarize(output)
    missing_note = f"missing targets: {', '.join(missing)}" if missing else ""
    detail = "; ".join(part for part in (summary, missing_note) if part)
    # One or more future dirs may be absent; only "all targets missing" fails.
    return StepResult("build", cmd, code, detail, code == 0, False)


def _step_web_build(root: Path, *, skip_web: bool) -> StepResult:
    node_modules = root / "apps" / "web" / "node_modules"
    if skip_web:
        return StepResult("web build", [], None, "skipped via --skip-web", False, True)
    if not node_modules.is_dir():
        return StepResult("web build", [], None, "web not installed yet", False, True)
    npm = shutil.which("npm")
    if npm is None:
        return StepResult(
            "web build", ["npm run build"], None, "npm not found", False, True
        )
    cmd = [npm, "run", "build"]
    code, output = run_command(cmd, root / "apps" / "web", timeout=600)
    return StepResult("web build", cmd, code, summarize(output), code == 0, False)


def run_gates(*, skip_web: bool = False, root: Path | None = None) -> QualityReport:
    """Execute every quality step against ``root`` (defaults to the git root)."""
    base = (root or Path.cwd()).resolve()
    ruff = resolve_tool("ruff", base)
    report = QualityReport(started_at=_utc_now())
    report.steps.append(_step_env(base))
    report.steps.append(_step_secret_scan(base))
    report.steps.append(_step_dependency_audit(base))
    if ruff is None:
        for step_name in ("format check", "lint"):
            report.steps.append(
                StepResult(
                    step_name, [], None, "ruff executable not found", False, False
                )
            )
    else:
        report.steps.append(_step_format(base, ruff))
        report.steps.append(_step_lint(base, ruff))
    report.steps.append(_step_typecheck(base))
    report.steps.append(_step_unit_tests(base))
    report.steps.append(_step_integration_tests(base))
    report.steps.append(_step_security_tests(base))
    report.steps.append(_step_build(base))
    report.steps.append(_step_web_build(base, skip_web=skip_web))
    report.finished_at = _utc_now()
    return report


def _print_table(report: QualityReport) -> None:
    for step in report.steps:
        code = step.exit_code if step.exit_code is not None else "-"
        status = "SKIP" if step.skipped else ("PASS" if step.passed else "FAIL")
        print(f"{status:5s} {step.step:18s} exit={code!s:>4}  {step.summary}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run every development quality gate.")
    parser.add_argument(
        "--skip-web", action="store_true", help="skip the web build step"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    args = parser.parse_args(argv)

    report = run_gates(skip_web=args.skip_web)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        _print_table(report)
        state = "ALL GATES PASSED" if report.all_passed else "GATES FAILED"
        print(f"[quality_gate] {state}")
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

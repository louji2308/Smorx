"""Dependency audit for the Software Evolution Intelligence System.

Importable module (public API ``audit_dependencies``) and a runnable CLI:

    python scripts/audit_deps.py [--json]

Runs ``python -m pip check`` against the active interpreter and additionally
verifies that the top-level dependencies declared by the Python packages under
``packages/`` and ``apps/api`` are importable in the active environment.

Severity ``error`` fails the gate; severity ``warning`` is reported but does
not. If ``pip check`` cannot be started at all an ``error`` issue named
``pip`` is emitted.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

import tomllib

_PYPROJECTS = (
    "packages/contracts/pyproject.toml",
    "packages/agent-runtime/pyproject.toml",
    "apps/api/pyproject.toml",
)

_REQUIRES_LINE = re.compile(r"^(?P<package>[\w.-]+)\s+[\w.!+\-]+\s+requires ")
_SPEC_NAME = re.compile(r"^(?P<name>[A-Za-z0-9_.\-]+)")


@dataclass
class DepIssue:
    package: str
    message: str
    severity: str  # "error" | "warning"


@dataclass
class DepReport:
    issues: list[DepIssue] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def _run_pip_check(python: str) -> str | None:
    """Return combined ``pip check`` output, or ``None`` when it could not run."""
    try:
        proc = subprocess.run(
            [python, "-m", "pip", "check"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (proc.stdout or "") + (proc.stderr or "")


def _parse_pip_check(output: str) -> list[DepIssue]:
    issues: list[DepIssue] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or "No broken requirements found." in line:
            continue
        match = _REQUIRES_LINE.match(line)
        if match:
            issues.append(
                DepIssue(package=match.group("package"), message=line, severity="error")
            )
    return issues


def _top_level_deps(pyproject: Path) -> list[str]:
    try:
        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    raw_deps = data.get("project", {}).get("dependencies") or []
    names: list[str] = []
    for spec in raw_deps:
        match = _SPEC_NAME.match(spec)
        if match:
            names.append(match.group("name"))
    return names


def _import_name(dep_name: str) -> str:
    return re.sub(r"^python[-_]", "", dep_name.replace("-", "_"))


def _check_importability(pyproject: Path, workdir: Path) -> list[DepIssue]:
    issues: list[DepIssue] = []
    if not pyproject.is_file():
        issues.append(
            DepIssue(
                package=pyproject.parent.name,
                message=f"{pyproject.relative_to(workdir)} not found (package not implemented yet)",
                severity="warning",
            )
        )
        return issues
    for dep in _top_level_deps(pyproject):
        names = (
            (_import_name(dep),)
            if "-" not in dep
            else (_import_name(dep), dep.replace("-", "_"))
        )
        importable = any(importlib.util.find_spec(name) is not None for name in names)
        if not importable:
            issues.append(
                DepIssue(
                    package=dep,
                    message=f"{dep} declared in {pyproject.relative_to(workdir)} not importable in active venv",
                    severity="warning",
                )
            )
    return issues


def audit_dependencies(
    python: str | None = None, *, workdir: Path | None = None
) -> DepReport:
    """Audit the active environment's dependency consistency.

    Args:
        python: Interpreter used to run ``pip check``. Defaults to the running
            interpreter (``sys.executable``).
        workdir: Repository root used to locate package manifests.
    """
    base = Path(workdir) if workdir is not None else Path.cwd()
    interpreter = python or sys.executable
    report = DepReport()

    pip_output = _run_pip_check(interpreter)
    if pip_output is None:
        report.issues.append(
            DepIssue(package="pip", message="pip check failed to run", severity="error")
        )
    else:
        report.issues.extend(_parse_pip_check(pip_output))

    for rel in _PYPROJECTS:
        report.issues.extend(_check_importability(base / rel, base))

    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit the active environment's dependencies."
    )
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    args = parser.parse_args(argv)

    report = audit_dependencies()
    if args.json:
        payload = [asdict(issue) for issue in report.issues]
        payload.append({"healthy": report.healthy})
        print(json.dumps(payload, indent=2))
    else:
        for issue in report.issues:
            print(f"[{issue.severity}] {issue.package}: {issue.message}")
        state = "healthy" if report.healthy else "UNHEALTHY"
        print(
            f"[audit_deps] {state} ({len([i for i in report.issues if i.severity == 'error'])} error(s), "
            f"{len([i for i in report.issues if i.severity == 'warning'])} warning(s))"
        )
    return 0 if report.healthy else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

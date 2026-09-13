"""Environment validation toolkit for the Software Evolution Intelligence System.

Importable module (public API used by quality gates and unit tests) and a
runnable CLI:

    python scripts/env_check.py [--env production|development] [--json] [--root PATH]

Exit code is ``0`` when no *required* issue exists and ``1`` otherwise.
Recommendation-level issues (development without a Nebius key, missing
optional tooling) are reported but do not fail the gate.

The ``check_environment`` entry point accepts an injected ``environ`` mapping
so callers (and tests) can validate an arbitrary environment without touching
the real process environment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_ENV_EXAMPLE_REL = "apps/api/.env.example"
_MIN_PYTHON = (3, 11)
_TOOLS = ("git", "python", "node", "npm")
_VERSION_RE = re.compile(r"^(\d+\.\d+\.\d+)")


@dataclass
class EnvIssue:
    name: str
    ok: bool
    message: str
    required: bool = False


@dataclass
class EnvReport:
    environment: str
    python: str
    repo_root: str
    issues: list[EnvIssue] = field(default_factory=list)

    @property
    def required_issues(self) -> list[EnvIssue]:
        return [issue for issue in self.issues if issue.required and not issue.ok]

    def all_ok(self) -> bool:
        return all(issue.ok for issue in self.issues)

    def summary(self) -> str:
        lines = [
            f"environment : {self.environment}",
            f"python      : {self.python}",
            f"repo root   : {self.repo_root}",
            f"all_ok      : {self.all_ok()}",
            f"required    : {len(self.required_issues)} issue(s)",
        ]
        for issue in self.issues:
            state = "OK " if issue.ok else "!! "
            required = "REQUIRED" if issue.required else "optional"
            lines.append(f"  [{state}{required:8s}] {issue.name}: {issue.message}")
        return "\n".join(lines)


@dataclass
class ToolInfo:
    name: str
    available: bool
    version: str


@dataclass
class ToolReport:
    tools: dict[str, ToolInfo]

    @property
    def missing(self) -> dict[str, ToolInfo]:
        return {name: info for name, info in self.tools.items() if not info.available}


def _default_repo_root() -> Path:
    """Resolve the repository root by walking up from this script to ``.git``."""
    start = Path(__file__).resolve().parent.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path.cwd()


def check_environment(
    environ: Mapping[str, str] | None = None,
    *,
    app_env: str = "development",
    repo_root: Path | None = None,
    extra_env_files: Sequence[Path] = (),
) -> EnvReport:
    """Validate the execution environment and return a structured report.

    Args:
        environ: Environment mapping to validate. Defaults to ``os.environ``.
        app_env: The environment this run is targeting (``development`` or
            ``production``). Production declares Nebius credentials required.
        repo_root: Repository root used for config-surface checks. Defaults to
            the git root discovered from this script, else the cwd.
        extra_env_files: Additional config-file paths to check for presence.
    """
    environ = dict(environ) if environ is not None else dict(os.environ)
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    issues: list[EnvIssue] = []
    production = app_env.lower() == "production"

    py_version = (sys.version_info[0], sys.version_info[1])
    py_display = f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    if py_version >= _MIN_PYTHON:
        issues.append(
            EnvIssue("python", True, f"python {py_display} >= 3.11", required=True)
        )
    else:
        issues.append(
            EnvIssue(
                "python", False, f"python {py_display} < 3.11 required", required=True
            )
        )

    config_surface = root / _ENV_EXAMPLE_REL
    if config_surface.is_file():
        issues.append(
            EnvIssue("config-surface", True, f"{config_surface} exists", required=True)
        )
    else:
        issues.append(
            EnvIssue(
                "config-surface",
                False,
                f"{config_surface} missing (ensure repo root or pass --root)",
                required=True,
            )
        )

    declared = environ.get("SMORX_APP_ENV") or environ.get("APP_ENV")
    if declared and declared.lower() != app_env.lower():
        issues.append(
            EnvIssue(
                "env-consistency",
                False,
                f"environment dict declares '{declared}' but validating '{app_env}'",
                required=production,
            )
        )
    else:
        issues.append(
            EnvIssue(
                "env-consistency",
                True,
                f"'{app_env}' consistent with declared env",
                required=False,
            )
        )

    if environ.get("NEBIUS_API_KEY"):
        issues.append(EnvIssue("NEBIUS_API_KEY", True, "present", required=production))
    else:
        issues.append(
            EnvIssue(
                "NEBIUS_API_KEY",
                False,
                "missing (development may run degraded; production is blocked)",
                required=production,
            )
        )

    project_id = environ.get("NEBIUS_AI_PROJECT") or environ.get("NEBIUS_PROJECT_ID")
    if project_id:
        issues.append(
            EnvIssue(
                "NEBIUS_PROJECT",
                True,
                "NEBIUS_AI_PROJECT / NEBIUS_PROJECT_ID present",
                required=production,
            )
        )
    else:
        issues.append(
            EnvIssue(
                "NEBIUS_PROJECT",
                False,
                "missing (NEBIUS_AI_PROJECT or NEBIUS_PROJECT_ID; production is blocked)",
                required=production,
            )
        )

    for env_file in extra_env_files:
        path = Path(env_file)
        if path.is_file():
            issues.append(
                EnvIssue(
                    f"env-file:{path.name}", True, f"{path} exists", required=False
                )
            )
        else:
            issues.append(
                EnvIssue(
                    f"env-file:{path.name}", False, f"{path} missing", required=False
                )
            )

    return EnvReport(
        environment=app_env, python=py_display, repo_root=str(root), issues=issues
    )


def _tool_version(exe: str) -> str:
    try:
        proc = subprocess.run(
            [exe, "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    output = (proc.stdout or proc.stderr).strip()
    match = _VERSION_RE.search(output)
    return match.group(1) if match else (output.splitlines()[0] if output else "")


def check_tools() -> ToolReport:
    """Report the availability of foundational CLI tools (best effort)."""
    tools: dict[str, ToolInfo] = {}
    for name in _TOOLS:
        exe = shutil.which(name)
        if exe is None:
            tools[name] = ToolInfo(name=name, available=False, version="")
            continue
        tools[name] = ToolInfo(name=name, available=True, version=_tool_version(exe))
    return ToolReport(tools=tools)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cli(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the repository execution environment."
    )
    default_env = (
        os.environ.get("SMORX_APP_ENV") or os.environ.get("APP_ENV") or "development"
    )
    parser.add_argument(
        "--env", choices=("production", "development"), default=default_env
    )
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--root", default=None, help="repository root to validate")
    args = parser.parse_args(list(argv))

    root = Path(args.root) if args.root else None
    report = check_environment(os.environ, app_env=args.env, repo_root=root)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(report.summary())
    return 0 if not report.required_issues else 1


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))

"""Phase 9 — differential execution of the same probes against both workspaces.

Runs identical probes in the baseline and candidate roots and compares real
machine behavior (exit code and normalized stdout); divergences feed the
Behavioral Delta analysis in Phase 10.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from smorx_tools.execution import CommandResult, CommandRunner

from smorx_verification.context import ModuleContext
from smorx_verification.contracts import (
    EvidenceRecord,
    ModuleOutcome,
    ModuleStatus,
    ModuleType,
)

__all__ = ["MODULE_TYPE", "run_differential_execution"]

MODULE_TYPE = ModuleType.DIFFERENTIAL_EXECUTION

_STDOUT_TAIL_LIMIT = 500


def _is_directory(path: Path) -> bool:
    return path.is_dir()


@dataclass(frozen=True)
class _Probe:
    """One configured probe: a name plus the real command vector to run."""

    name: str
    args: tuple[str, ...]


_DEFAULT_PROBE = _Probe(name="default_probe", args=("python", "-c", "print(42)"))


def _load_probes(settings: dict[str, object]) -> list[_Probe]:
    """Read ``differential.probes`` from settings, falling back to the default."""
    raw = settings.get("differential")
    if not isinstance(raw, dict):
        return [_DEFAULT_PROBE]
    probes_raw = raw.get("probes")
    probes: list[_Probe] = []
    if isinstance(probes_raw, list):
        for entry in probes_raw:
            probe = _coerce_probe(entry)
            if probe is not None:
                probes.append(probe)
    return probes if probes else [_DEFAULT_PROBE]


def _coerce_probe(entry: object) -> _Probe | None:
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    args = entry.get("args")
    if not isinstance(name, str) or not isinstance(args, list) or not args:
        return None
    return _Probe(name=name, args=tuple(str(arg) for arg in args))


def _normalize_stdout(stdout: str) -> str:
    return "\n".join(line.rstrip() for line in stdout.splitlines()).strip()


def _stdout_tail(text: str, limit: int = _STDOUT_TAIL_LIMIT) -> str:
    return text if len(text) <= limit else "..." + text[-limit:]


async def _run_probe_in(runner: CommandRunner, probe: _Probe, cwd: Path) -> CommandResult:
    try:
        return await runner.run(probe.args, cwd=cwd)
    except OSError as exc:
        return CommandResult(
            exit_code=-1,
            stdout="",
            stderr=f"<probe launch failed: {exc!r}>",
            duration_seconds=0.0,
            timed_out=False,
            command_name=probe.name,
        )


async def run_differential_execution(ctx: ModuleContext) -> ModuleOutcome:
    """Run every configured probe in baseline and candidate roots and compare."""
    if ctx.baseline_root is None:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.BLOCKED,
            summary="baseline_root required for differential execution",
            findings=("baseline_root is missing",),
        )
    baseline_root = Path(ctx.baseline_root)
    if not _is_directory(baseline_root):
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.BLOCKED,
            summary="baseline_root required for differential execution",
            findings=(f"baseline_root not a directory: {ctx.baseline_root}",),
        )
    if not ctx.claim_ids:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no claims bound; differential evidence cannot be claim-eligible",
        )
    candidate_root = Path(ctx.candidate_root)
    if not _is_directory(candidate_root):
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.BLOCKED,
            summary=f"candidate_root is not a directory: {ctx.candidate_root}",
            findings=(f"candidate_root not a directory: {ctx.candidate_root}",),
        )
    started = time.monotonic()
    probes = _load_probes(ctx.settings)
    runner = CommandRunner(default_timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds))
    collector = ctx.require_collector()
    records: list[EvidenceRecord] = []
    findings: list[str] = []
    differing = 0
    for probe in probes:
        baseline_result = await _run_probe_in(runner, probe, baseline_root)
        candidate_result = await _run_probe_in(runner, probe, candidate_root)
        baseline_stdout = _normalize_stdout(baseline_result.stdout)
        candidate_stdout = _normalize_stdout(candidate_result.stdout)
        equal = (
            baseline_result.exit_code == candidate_result.exit_code
            and baseline_stdout == candidate_stdout
        )
        records.append(
            collector.emit(
                module_type=MODULE_TYPE,
                claim_id=ctx.claim_ids[0],
                source=f"differential_execution.{probe.name}",
                provenance=(
                    f"baseline_root={ctx.baseline_root};candidate_root={ctx.candidate_root}"
                ),
                machine_result={
                    "probe": probe.name,
                    "exit_code": candidate_result.exit_code,
                    "baseline_exit_code": baseline_result.exit_code,
                    "candidate_exit_code": candidate_result.exit_code,
                    "behavior_equal": equal,
                    "baseline_stdout_tail": _stdout_tail(baseline_stdout),
                    "candidate_stdout_tail": _stdout_tail(candidate_stdout),
                },
                exit_code=candidate_result.exit_code,
                severity="INFO" if equal else "HIGH",
                artifact="differential",
            )
        )
        if not equal:
            differing += 1
            findings.append(f"probe {probe.name!r} produced differing behavior")
    status = ModuleStatus.PASSED if differing == 0 else ModuleStatus.FAILED
    matched = len(probes) - differing
    summary = (
        f"ran {len(probes)} differential probe(s) in baseline and candidate roots; "
        f"{matched} matched and {differing} differed"
    )
    return ModuleOutcome(
        module_type=MODULE_TYPE,
        status=status,
        summary=summary,
        evidence=tuple(records),
        findings=tuple(findings),
        duration_seconds=time.monotonic() - started,
    )

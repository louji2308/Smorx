"""Historical Ghost Replay verification module.

Replays recorded failure scenarios (Ghosts) against the current candidate to
prove that a claimed repair actually holds. This module uses real execution,
never mocked responses. Ghost scenarios arrive via ``ctx.settings``; the
orchestrator/tests inject the failure/mutation scenario into the candidate
workspace before calling this module. The module's job is to replay each
scenario and decide regression-vs-repair from actual subprocess output.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from smorx_tools.execution import CommandRunner

from smorx_verification.context import ModuleContext
from smorx_verification.contracts import (
    EvidenceRecord,
    ModuleOutcome,
    ModuleStatus,
    ModuleType,
    now_utc,
)

MODULE_TYPE: ModuleType = ModuleType.HISTORICAL_GHOST_REPLAY


async def _run_scenario(
    runner: CommandRunner,
    args: Sequence[str],
    *,
    cwd: str,
    timeout_seconds: float,
) -> tuple[int, str, str, float, bool]:
    result = await runner.run(args, timeout_seconds=timeout_seconds, cwd=cwd)
    return (
        result.exit_code,
        result.stdout,
        result.stderr,
        result.duration_seconds,
        result.timed_out,
    )


async def run_historical_ghost_replay(ctx: ModuleContext) -> ModuleOutcome:
    """Replay Ghost scenarios and determine regression vs repair.

    If ``candidate_root`` contains ``ghost_probe.py`` at its root, it is
    executed as the scenario regardless of ``args``. Otherwise each
    scenario's ``args`` list is run via :class:`CommandRunner`. A regression
    is reproduced when the ``regression_marker`` substring appears in stdout.
    """
    started = now_utc()

    if not ctx.claim_ids:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no claims bound",
            duration_seconds=0.0,
        )

    scenarios: list[dict[str, Any]] = ctx.settings.get("ghost_replay", {}).get("scenarios", [])

    if not scenarios:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no ghost scenarios supplied",
            duration_seconds=(now_utc() - started).total_seconds(),
        )

    collector = ctx.require_collector()
    claim_id = ctx.claim_ids[0]
    runner = CommandRunner(
        default_timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds),
    )
    candidate_root = ctx.candidate_root
    ghost_probe = Path(candidate_root) / "ghost_probe.py"
    use_probe = ghost_probe.is_file()

    evidence_records: list[EvidenceRecord] = []
    findings: list[str] = []
    regressions = 0
    repaired = 0

    for scenario in scenarios:
        scenario_id = str(scenario["scenario_id"])
        regression_marker = str(scenario["regression_marker"])
        title = str(scenario.get("title", scenario_id))

        if use_probe:
            args: Sequence[str] = (sys.executable, str(ghost_probe))
        else:
            args = tuple(scenario["args"])

        exit_code, stdout, _stderr, duration, timed_out = await _run_scenario(
            runner,
            args,
            cwd=candidate_root,
            timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds),
        )

        stdout_tail = stdout[-2000:] if len(stdout) > 2000 else stdout
        marker_present = regression_marker in stdout

        machine_result: dict[str, Any] = {
            "scenario_id": scenario_id,
            "title": title,
            "regression_reproduced": marker_present,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_seconds": round(duration, 3),
            "stdout_tail": stdout_tail,
        }

        if marker_present:
            severity = "HIGH"
            regressions += 1
            findings.append(
                f"{title}: regression still reproduces (marker={regression_marker!r})",
            )
        else:
            severity = "INFO"
            repaired += 1
            findings.append(f"{title}: repair holds")

        record = collector.emit(
            module_type=MODULE_TYPE,
            claim_id=claim_id,
            source=f"ghost_replay.{scenario_id}",
            provenance=f"ghost_replay:{scenario_id}",
            machine_result=machine_result,
            exit_code=exit_code,
            severity=severity,
        )
        evidence_records.append(record)

    total = len(scenarios)
    status = ModuleStatus.PASSED if regressions == 0 else ModuleStatus.FAILED
    summary = (
        f"ghost replay: {repaired}/{total} scenarios hold "
        f"({regressions} historical failure(s) still reproduce)"
    )

    return ModuleOutcome(
        module_type=MODULE_TYPE,
        status=status,
        summary=summary,
        evidence=tuple(evidence_records),
        findings=tuple(findings),
        duration_seconds=(now_utc() - started).total_seconds(),
    )

"""Phase 9 — mutation-testing verification module.

Introduces small real mutations into an isolated OS temp copy of the candidate
source (never the candidate itself) and runs each mutated probe through the
bounded command runner. A mutation is killed when the probe's real stdout
differs from the expected unmutated stdout, proving the verification approach
would detect the behavioral change.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, cast

from smorx_tools.execution import CommandResult, CommandRunner

from smorx_verification.context import ModuleContext
from smorx_verification.contracts import EvidenceRecord, ModuleOutcome, ModuleStatus, ModuleType

MODULE_TYPE: ModuleType = ModuleType.MUTATION_TEST

GHOST_PROBE_NAME: str = "ghost_probe.py"
GHOST_DEFAULT_MUTATION: dict[str, object] = {
    "mutation_id": "GHOST_DEFAULT",
    "target": GHOST_PROBE_NAME,
    "old": "return 42",
    "new": "return 7",
}


def _collect_mutations(candidate_root: str, scope: dict[str, Any]) -> tuple[dict[str, object], ...]:
    raw = scope.get("mutations", [])
    if raw:
        return tuple(cast(dict[str, object], item) for item in raw if isinstance(item, dict))
    if (Path(candidate_root) / GHOST_PROBE_NAME).is_file():
        return (GHOST_DEFAULT_MUTATION,)
    return ()


def _copy_candidate(candidate_root: str, tmp_root: str) -> None:
    shutil.copytree(candidate_root, tmp_root, dirs_exist_ok=True)


def _destroy_tmp(tmp_root: str) -> None:
    shutil.rmtree(tmp_root, ignore_errors=True)


def _apply_mutation(tmp_root: str, target: str, old: str, new: str) -> None:
    target_path = Path(tmp_root) / target
    original = target_path.read_text(encoding="utf-8")
    replaced = original.replace(old, new) if old else original
    target_path.write_text(replaced, encoding="utf-8")


def _tail(text: str, limit: int = 200) -> str:
    stripped = text.strip()
    return stripped if len(stripped) <= limit else stripped[-limit:]


async def _run_probe(
    runner: CommandRunner, target: str, tmp_root: str, timeout_seconds: int
) -> CommandResult:
    return await runner.run((sys.executable, target), cwd=tmp_root, timeout_seconds=timeout_seconds)


async def run_mutation_testing(ctx: ModuleContext) -> ModuleOutcome:
    if not ctx.claim_ids:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no claims bound",
        )

    collector = ctx.require_collector()
    scope = cast(dict[str, Any], ctx.settings.get("mutation", {}))
    mutations = _collect_mutations(ctx.candidate_root, scope)
    expected_stdout = cast(str, scope.get("expected_stdout", "42"))
    runner = CommandRunner(default_timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds))
    records: list[EvidenceRecord] = []
    survived: list[str] = []
    killed_count = 0
    started_at = time.monotonic()
    tmp_root: str | None = None
    try:
        tmp_root = tempfile.mkdtemp(prefix="smorx_mutation_")
        _copy_candidate(ctx.candidate_root, tmp_root)
        for mutation in mutations:
            mutation_id = cast(str, mutation.get("mutation_id", ""))
            target = cast(str, mutation.get("target", ""))
            old = cast(str, mutation.get("old", ""))
            new = cast(str, mutation.get("new", ""))
            target_path = Path(tmp_root) / target
            if not target_path.is_file():
                killed = False
                probe_stdout_tail = "<target missing in temp copy>"
                probe_exit = -1
            else:
                _apply_mutation(tmp_root, target, old, new)
                result = await _run_probe(
                    runner, target, tmp_root, ctx.bounds.per_tool_timeout_seconds
                )
                probe_stdout_tail = _tail(result.stdout)
                probe_exit = result.exit_code
                killed = probe_stdout_tail != expected_stdout
            if killed:
                killed_count += 1
                severity = "INFO"
                exit_code = probe_exit
            else:
                survived.append(mutation_id)
                severity = "HIGH"
                exit_code = 1
            records.append(
                collector.emit(
                    module_type=MODULE_TYPE,
                    claim_id=ctx.claim_ids[0],
                    source=f"mutation.{mutation_id}",
                    provenance=f"{ctx.actor.actor_run_id}:{ctx.verification_case_id}",
                    artifact=target,
                    machine_result={
                        "mutation_id": mutation_id,
                        "exit_code": exit_code,
                        "killed": killed,
                        "probe_stdout_tail": probe_stdout_tail,
                        "expected_stdout": expected_stdout,
                    },
                    exit_code=exit_code,
                    severity=severity,
                )
            )
    finally:
        if tmp_root is not None:
            _destroy_tmp(tmp_root)

    status = ModuleStatus.FAILED if survived else ModuleStatus.PASSED
    total = len(mutations)
    return ModuleOutcome(
        module_type=MODULE_TYPE,
        status=status,
        summary=f"mutation testing: {killed_count}/{total} mutants killed",
        evidence=tuple(records),
        findings=tuple(survived),
        duration_seconds=time.monotonic() - started_at,
    )

"""Metamorphic Check verification module.

Verifies expected invariants under controlled transformations of the
candidate's own behavior (metamorphic oracle). Checks never mutate the
candidate; they only observe its behavior under argument permutations. Two
runs (base and variant) that accept the same inputs must produce identical
exit codes and normalized stdout.
"""

from __future__ import annotations

from collections.abc import Sequence
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

MODULE_TYPE: ModuleType = ModuleType.METAMORPHIC_CHECK


def _normalize_stdout(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


async def _run_check(
    runner: CommandRunner,
    args: Sequence[str],
    *,
    cwd: str,
    timeout_seconds: float,
) -> tuple[int, str, float]:
    result = await runner.run(args, timeout_seconds=timeout_seconds, cwd=cwd)
    return result.exit_code, result.stdout, result.duration_seconds


async def run_metamorphic_checks(ctx: ModuleContext) -> ModuleOutcome:
    """Run metamorphic checks and compare base vs variant outputs.

    Each check defines a base ``args`` set and one or more ``variants``.
    Every variant must produce the same exit code and normalized stdout as
    the base. Differing outputs indicate non-deterministic or
    transformation-dependent behavior.
    """
    started = now_utc()

    if not ctx.claim_ids:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no claims bound",
            duration_seconds=0.0,
        )

    checks: list[dict[str, Any]] = ctx.settings.get("metamorphic", {}).get("checks", [])

    if not checks:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no metamorphic checks supplied",
            duration_seconds=(now_utc() - started).total_seconds(),
        )

    collector = ctx.require_collector()
    claim_id = ctx.claim_ids[0]
    runner = CommandRunner(
        default_timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds),
    )
    candidate_root = ctx.candidate_root

    evidence_records: list[EvidenceRecord] = []
    findings: list[str] = []
    consistent_count = 0
    inconsistent_count = 0

    for check in checks:
        check_id = str(check["check_id"])
        title = str(check.get("title", check_id))
        base_args: Sequence[str] = check["args"]
        variants: list[Sequence[str]] = check["variants"]

        base_exit, base_stdout, _base_dur = await _run_check(
            runner,
            base_args,
            cwd=candidate_root,
            timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds),
        )
        base_normalized = _normalize_stdout(base_stdout)

        variant_exit_codes: list[int] = []
        all_consistent = True

        for variant_args in variants:
            v_exit, v_stdout, _v_dur = await _run_check(
                runner,
                variant_args,
                cwd=candidate_root,
                timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds),
            )
            v_normalized = _normalize_stdout(v_stdout)
            variant_exit_codes.append(v_exit)

            if v_exit != base_exit or v_normalized != base_normalized:
                all_consistent = False

        if all_consistent:
            severity = "INFO"
            consistent_count += 1
            findings.append(f"{title}: all variants consistent")
            diff_detail = ""
        else:
            severity = "HIGH"
            inconsistent_count += 1
            findings.append(f"{title}: variants inconsistent with base")
            diff_detail = f"base_exit={base_exit}, variant_exits={variant_exit_codes}"

        machine_result: dict[str, Any] = {
            "check_id": check_id,
            "title": title,
            "exit_code": base_exit,
            "variants_consistent": all_consistent,
            "base_exit_code": base_exit,
            "variant_exit_codes": variant_exit_codes,
            "base_stdout_length": len(base_stdout),
        }
        if diff_detail:
            machine_result["diff"] = diff_detail

        record = collector.emit(
            module_type=MODULE_TYPE,
            claim_id=claim_id,
            source=f"metamorphic.{check_id}",
            provenance=f"metamorphic:{check_id}",
            machine_result=machine_result,
            exit_code=base_exit,
            severity=severity,
        )
        evidence_records.append(record)

    total = len(checks)
    status = ModuleStatus.PASSED if inconsistent_count == 0 else ModuleStatus.FAILED
    summary = (
        f"metamorphic: {consistent_count}/{total} checks consistent "
        f"({inconsistent_count} inconsistent)"
    )

    return ModuleOutcome(
        module_type=MODULE_TYPE,
        status=status,
        summary=summary,
        evidence=tuple(evidence_records),
        findings=tuple(findings),
        duration_seconds=(now_utc() - started).total_seconds(),
    )

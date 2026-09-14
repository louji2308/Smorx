"""Phase 9 — independent static analysis of the candidate source tree.

Compiles the candidate's Python sources (without executing any candidate
code) and scans them for banned tokens. Each check emits its own evidence
record; the module never mutates the candidate (AGENTS.md §17/§37).
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from smorx_tools.execution import CommandRunner

from smorx_verification.context import ModuleContext
from smorx_verification.contracts import (
    EvidenceRecord,
    ModuleOutcome,
    ModuleStatus,
    ModuleType,
)

__all__ = ["MODULE_TYPE", "run_static_analysis"]

MODULE_TYPE = ModuleType.STATIC_ANALYSIS

_IGNORED_DIRS: frozenset[str] = frozenset({"node_modules", ".venv", "venv", "__pycache__", ".git"})

_BANNED_TOKENS: tuple[str, ...] = (
    "api_key",
    "password",
    "secret",
    "BEGIN PRIVATE KEY",
    "hardcoded",
)

_AST_FALLBACK_SOURCE = """\
import ast
import pathlib
import sys

_ignored = {"node_modules", ".venv", "venv", "__pycache__", ".git"}
root = pathlib.Path(sys.argv[1])
files = sorted(
    path
    for path in root.rglob("*.py")
    if not any(part in _ignored for part in path.relative_to(root).parts)
)
errors = 0
for path in files:
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError as exc:
        errors += 1
        print(f"syntax error in {path}: {exc.msg}")
print(f"parsed={len(files)} errors={errors}")
sys.exit(1 if errors else 0)
"""


@dataclass(frozen=True)
class _CompileCheck:
    """Outcome of one real compile check: the exit code and which parser ran."""

    exit_code: int
    parser: str


def _is_directory(path: Path) -> bool:
    return path.is_dir()


def _iter_python_files(root: Path) -> Iterator[Path]:
    """Yield every ``.py`` file under ``root``, skipping vendor/dependency dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _IGNORED_DIRS]
        for filename in filenames:
            if filename.endswith(".py"):
                yield Path(dirpath) / filename


async def _run_compile_check(runner: CommandRunner, root: Path) -> _CompileCheck:
    """Compile the tree once, falling back to ``ast`` when ``compileall`` is unusable."""
    result = await runner.run((sys.executable, "-m", "compileall", "-q", str(root)), cwd=root)
    if "No module named" not in result.stderr:
        return _CompileCheck(exit_code=result.exit_code, parser="compileall")
    return await _run_ast_compile_check(runner, root)


async def _run_ast_compile_check(runner: CommandRunner, root: Path) -> _CompileCheck:
    fd, name = tempfile.mkstemp(prefix="smorx_ast_check_", suffix=".py", text=True)
    os.close(fd)
    try:
        _write_ast_script(name)
        result = await runner.run((sys.executable, name, str(root)), cwd=root)
        return _CompileCheck(exit_code=result.exit_code, parser="ast")
    finally:
        os.unlink(name)


def _write_ast_script(name: str) -> None:
    Path(name).write_text(_AST_FALLBACK_SOURCE, encoding="utf-8")


def _scan_banned_tokens(
    files: Sequence[Path], root: Path, limit: int = 20
) -> tuple[list[str], int]:
    """Return (capped matched-file list, total count) from real file reads."""
    matched: list[str] = []
    total = 0
    for path in files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(token in content for token in _BANNED_TOKENS):
            total += 1
            if len(matched) < limit:
                matched.append(str(path.relative_to(root)))
    return sorted(matched), total


async def run_static_analysis(ctx: ModuleContext) -> ModuleOutcome:
    """Run the static-analysis module for the current verification wave."""
    if not ctx.claim_ids:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no claims bound; static analysis evidence cannot be claim-eligible",
        )
    root = Path(ctx.candidate_root)
    if not _is_directory(root):
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.BLOCKED,
            summary=f"candidate_root is not a directory: {ctx.candidate_root}",
            findings=(f"candidate_root not a directory: {ctx.candidate_root}",),
        )
    started = time.monotonic()
    files = sorted(_iter_python_files(root))
    if not files:
        return ModuleOutcome(
            module_type=MODULE_TYPE,
            status=ModuleStatus.SKIPPED,
            summary="no python sources found under candidate_root; nothing statically compiled",
        )
    collector = ctx.require_collector()
    runner = CommandRunner(default_timeout_seconds=float(ctx.bounds.per_tool_timeout_seconds))
    records: list[EvidenceRecord] = []
    findings: list[str] = []

    compile_check = await _run_compile_check(runner, root)
    records.append(
        collector.emit(
            module_type=MODULE_TYPE,
            claim_id=ctx.claim_ids[0],
            source="static_analysis.compile_all",
            provenance=f"candidate_root={ctx.candidate_root}",
            machine_result={
                "exit_code": compile_check.exit_code,
                "command": "compile_all",
                "files_checked": len(files),
                "parser": compile_check.parser,
            },
            exit_code=compile_check.exit_code,
            severity="HIGH" if compile_check.exit_code != 0 else "INFO",
            artifact="compileall",
        )
    )
    if compile_check.exit_code != 0:
        findings.append(f"compile_all failed with exit code {compile_check.exit_code}")

    matched_files, total_matched = _scan_banned_tokens(files, root)
    if total_matched:
        records.append(
            collector.emit(
                module_type=MODULE_TYPE,
                claim_id=ctx.claim_ids[0],
                source="static_analysis.secret_scan",
                provenance=f"candidate_root={ctx.candidate_root}",
                machine_result={
                    "matched_files": matched_files,
                    "total_matched": total_matched,
                },
                exit_code=0,
                severity="HIGH",
                artifact="secret_scan",
            )
        )
        findings.append(f"banned token(s) matched in {total_matched} file(s) under candidate_root")

    status = (
        ModuleStatus.FAILED
        if compile_check.exit_code != 0 or total_matched
        else ModuleStatus.PASSED
    )
    compile_statement = "compile_all " + ("failed" if compile_check.exit_code != 0 else "passed")
    token_statement = (
        f"banned-token scan matched {total_matched} file(s)"
        if total_matched
        else "banned-token scan found no matches"
    )
    summary = (
        f"statically analyzed {len(files)} python source file(s) under candidate_root: "
        f"{compile_statement} (exit {compile_check.exit_code}); {token_statement}"
    )
    return ModuleOutcome(
        module_type=MODULE_TYPE,
        status=status,
        summary=summary,
        evidence=tuple(records),
        findings=tuple(findings),
        duration_seconds=time.monotonic() - started,
    )

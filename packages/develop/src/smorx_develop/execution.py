"""Phase 8.6-8.8 — Machine-authoritative execution capture and failure taxonomy.

Every command/test run is captured with command, argument metadata, start
and end time, exit code, stdout, stderr, environment/sandbox identity,
artifacts, timeout, and a failure classification. The machine result is
authoritative over any model assertion (I2): a model claim of success can
never mark a run as passed.

Failures are normalized into the project taxonomy F1-F10. The classifier
records the OBSERVED failure; root cause is a separate diagnosis step
(§8.8: observed failure ≠ root cause).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from smorx_tools.execution import CommandResult
from smorx_tools.tool import ToolResultStatus

__all__ = [
    "ExecutionCapture",
    "ExecutionRecord",
    "ExecutionStats",
    "FailureCode",
    "classify_failure",
    "failure_code_for",
]


class FailureCode:
    """The project failure taxonomy (F1-F10)."""

    F1_SYNTAX_BUILD = "F1_SYNTAX_BUILD"
    F2_UNIT_TEST = "F2_UNIT_TEST"
    F3_INTEGRATION = "F3_INTEGRATION"
    F4_ENVIRONMENT_DEPENDENCY = "F4_ENVIRONMENT_DEPENDENCY"
    F5_TIMEOUT = "F5_TIMEOUT"
    F6_PERMISSION = "F6_PERMISSION"
    F7_TOOL = "F7_TOOL"
    F8_AMBIGUOUS_RESULT = "F8_AMBIGUOUS_RESULT"
    F9_ACCEPTANCE_CRITERION = "F9_ACCEPTANCE_CRITERION"
    F10_SAFETY_POLICY_BLOCK = "F10_SAFETY_POLICY_BLOCK"

    ALL: tuple[str, ...] = (
        F1_SYNTAX_BUILD,
        F2_UNIT_TEST,
        F3_INTEGRATION,
        F4_ENVIRONMENT_DEPENDENCY,
        F5_TIMEOUT,
        F6_PERMISSION,
        F7_TOOL,
        F8_AMBIGUOUS_RESULT,
        F9_ACCEPTANCE_CRITERION,
        F10_SAFETY_POLICY_BLOCK,
    )


_BUILD_HINTS: tuple[str, ...] = (
    "syntaxerror",
    "indentationerror",
    "compile error",
    "compilation failed",
    "build failed",
    "modulenotfounderror",
    "no module named",
    "typeerror:",
    "nameerror:",
    "unexpected token",
    "does not compile",
)


def failure_code_for(classification: str) -> str:
    """Map the tools-layer classification vocabulary onto F1-F10."""
    mapping = {
        "syntax/build failure": FailureCode.F1_SYNTAX_BUILD,
        "unit test failure": FailureCode.F2_UNIT_TEST,
        "integration failure": FailureCode.F3_INTEGRATION,
        "environment/dependency failure": FailureCode.F4_ENVIRONMENT_DEPENDENCY,
        "timeout": FailureCode.F5_TIMEOUT,
        "permission failure": FailureCode.F6_PERMISSION,
        "tool failure": FailureCode.F7_TOOL,
        "safety/policy block": FailureCode.F10_SAFETY_POLICY_BLOCK,
    }
    return mapping.get(classification, FailureCode.F8_AMBIGUOUS_RESULT)


def classify_failure(
    *,
    exit_code: int,
    stdout: str,
    stderr: str,
    kind: str,
    timed_out: bool = False,
    status: str = "",
) -> str:
    """Classify one executed command into F1-F10 (deterministic).

    ``kind`` is the caller's declared command kind (UNIT_TEST,
    INTEGRATION_TEST, BUILD, LINT, TYPECHECK, COMMAND). Non-zero exit on a
    test kind is F2/F3 by kind; a pytest-style ``N failed`` summary in the
    output confirms a test failure. Build hints in stderr promote to F1.
    """
    lowered_stderr = stderr.lower()
    lowered_out = stdout.lower()

    if timed_out:
        return FailureCode.F5_TIMEOUT
    if "permission denied" in lowered_stderr or "access denied" in lowered_stderr:
        return FailureCode.F6_PERMISSION
    if "policy" in lowered_stderr and "block" in lowered_stderr:
        return FailureCode.F10_SAFETY_POLICY_BLOCK
    if status == ToolResultStatus.DENIED.value:
        return FailureCode.F6_PERMISSION
    if status == ToolResultStatus.BLOCKED.value:
        return FailureCode.F10_SAFETY_POLICY_BLOCK
    if status == ToolResultStatus.UNAVAILABLE.value:
        return FailureCode.F4_ENVIRONMENT_DEPENDENCY
    if exit_code == 0:
        return ""

    if any(hint in lowered_stderr for hint in _BUILD_HINTS):
        return FailureCode.F1_SYNTAX_BUILD
    if kind in {"UNIT_TEST", "INTEGRATION_TEST", "TEST"}:
        failed_marker = " failed" in lowered_out or "failed=" in lowered_out
        return (
            (FailureCode.F3_INTEGRATION if kind == "INTEGRATION_TEST" else FailureCode.F2_UNIT_TEST)
            if failed_marker
            else FailureCode.F2_UNIT_TEST
        )
    if kind in {"BUILD", "LINT", "TYPECHECK"}:
        return FailureCode.F1_SYNTAX_BUILD
    if "import" in lowered_stderr or "module" in lowered_stderr:
        return FailureCode.F3_INTEGRATION
    return FailureCode.F8_AMBIGUOUS_RESULT


@dataclass(frozen=True)
class ExecutionRecord:
    """One machine-authoritative execution observation."""

    execution_id: str
    kind: str
    command: tuple[str, ...]
    cwd: str
    sandbox_id: str
    sandbox_backend: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    failure_code: str
    artifacts: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def as_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "kind": self.kind,
            "command": list(self.command),
            "cwd": self.cwd,
            "sandbox_id": self.sandbox_id,
            "sandbox_backend": self.sandbox_backend,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "stdout_tail": self.stdout[-4000:],
            "stderr_tail": self.stderr[-4000:],
            "timed_out": self.timed_out,
            "failure_code": self.failure_code,
            "passed": self.passed,
            "artifacts": list(self.artifacts),
            "notes": self.notes,
        }


class ExecutionCapture:
    """Records executions against an explicit sandbox identity."""

    def __init__(self, *, sandbox_id: str, sandbox_backend: str) -> None:
        self._sandbox_id = sandbox_id
        self._sandbox_backend = sandbox_backend
        self._records: list[ExecutionRecord] = []

    @property
    def records(self) -> tuple[ExecutionRecord, ...]:
        return tuple(self._records)

    def record(
        self,
        *,
        kind: str,
        command: tuple[str, ...],
        result: CommandResult,
        artifacts: Sequence[str] = (),
        notes: str = "",
        cwd: str = "",
    ) -> ExecutionRecord:
        """Capture one real :class:`CommandResult` into an attributed record.

        ``cwd`` records the sandbox working directory the command ran in.
        """
        failure_code = classify_failure(
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=result.timed_out,
            kind=kind,
        )
        record = ExecutionRecord(
            execution_id=f"exec-{uuid.uuid4().hex[:12]}",
            kind=kind,
            command=tuple(command),
            cwd=cwd,
            sandbox_id=self._sandbox_id,
            sandbox_backend=self._sandbox_backend,
            started_at=datetime.now(UTC) - timedelta(seconds=result.duration_seconds),
            finished_at=datetime.now(UTC),
            duration_seconds=result.duration_seconds,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=result.timed_out,
            failure_code=failure_code,
            artifacts=tuple(artifacts),
            notes=notes,
        )
        self._records.append(record)
        return record


class ExecutionStats:
    """Aggregate pass/fail view over captured records."""

    def __init__(self, records: tuple[ExecutionRecord, ...]) -> None:
        self.records = records

    @property
    def total(self) -> int:
        return len(self.records)

    @property
    def passed(self) -> int:
        return sum(1 for record in self.records if record.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def failure_codes(self) -> tuple[str, ...]:
        return tuple(record.failure_code for record in self.records if record.failure_code)

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "failure_codes": list(self.failure_codes),
        }

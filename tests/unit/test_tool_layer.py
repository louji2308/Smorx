"""Unit tests for the policy-controlled tool layer (Phase 4, Wave 2).

Covers the frozen contracts in ``smorx_tools.tool`` (enums, dataclasses,
registry) and the bounded execution/classification helpers in
``smorx_tools.execution``.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime
from types import MappingProxyType

import pytest
from smorx_tools.execution import (
    CommandResult,
    CommandRunner,
    ExecutionError,
    FailureClassifier,
    normalize_test_output,
)
from smorx_tools.tool import (
    ToolExecutionResult,
    ToolKind,
    ToolRegistry,
    ToolRequest,
    ToolResultStatus,
    ToolSpec,
    is_success,
)

_BASE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _spec(name: str, kind: ToolKind, *, capability: str = "*") -> ToolSpec:
    return ToolSpec(
        name=name,
        kind=kind,
        description=f"tool {name}",
        capability=capability,
    )


# ---------------------------------------------------------------------------
# tool.py: enums and helpers
# ---------------------------------------------------------------------------


def test_tool_kind_members_and_values() -> None:
    assert [kind.value for kind in ToolKind] == [
        "REPOSITORY",
        "FILE",
        "COMMAND",
        "TEST",
        "SANDBOX",
        "VERIFICATION",
        "MODEL",
        "POLICY",
        "CONTROL",
    ]
    assert ToolKind.REPOSITORY == "REPOSITORY"
    assert ToolKind.CONTROL == "CONTROL"


def test_tool_result_status_members_and_values() -> None:
    assert [status.value for status in ToolResultStatus] == [
        "SUCCEEDED",
        "FAILED",
        "TIMEOUT",
        "ERROR",
        "DENIED",
        "BLOCKED",
        "PENDING_REVIEW",
        "UNAVAILABLE",
    ]
    assert ToolResultStatus.SUCCEEDED == "SUCCEEDED"
    assert ToolResultStatus.UNAVAILABLE == "UNAVAILABLE"


def test_is_success_semantics() -> None:
    assert is_success(ToolResultStatus.SUCCEEDED)
    assert not is_success(ToolResultStatus.FAILED)
    assert not is_success(ToolResultStatus.TIMEOUT)
    assert not is_success(ToolResultStatus.ERROR)
    assert not is_success(ToolResultStatus.DENIED)
    assert not is_success(ToolResultStatus.BLOCKED)
    assert not is_success(ToolResultStatus.PENDING_REVIEW)
    assert not is_success(ToolResultStatus.UNAVAILABLE)


# ---------------------------------------------------------------------------
# tool.py: ToolSpec / ToolRequest / ToolExecutionResult / ToolRegistry
# ---------------------------------------------------------------------------


def test_tool_spec_construction() -> None:
    spec = ToolSpec(
        name="run.command",
        kind=ToolKind.COMMAND,
        description="Run a command",
        capability="CODING",
    )
    assert spec.name == "run.command"
    assert spec.kind is ToolKind.COMMAND
    assert spec.capability == "CODING"
    assert spec.risk == "low"
    assert spec.timeout_seconds == 30.0
    assert spec.requires_sandbox is False
    assert spec.mutates is False
    assert spec.requires_approval is False
    assert spec.handler is None


def test_registry_register_and_get() -> None:
    registry = ToolRegistry()
    spec = _spec("read.file", ToolKind.FILE, capability="CODING")
    registry.register(spec)
    assert registry.get("read.file") is spec
    assert registry.get("missing.tool") is None


def test_registry_duplicate_name_raises() -> None:
    registry = ToolRegistry()
    registry.register(_spec("dup.tool", ToolKind.FILE))
    with pytest.raises(ValueError):
        registry.register(_spec("dup.tool", ToolKind.COMMAND))


def test_registry_names_insertion_order() -> None:
    registry = ToolRegistry()
    registry.register(_spec("b.tool", ToolKind.FILE))
    registry.register(_spec("a.tool", ToolKind.FILE))
    assert registry.names() == ("b.tool", "a.tool")


def test_registry_tools_for_capability_includes_star() -> None:
    registry = ToolRegistry()
    registry.register(_spec("coding.tool", ToolKind.COMMAND, capability="CODING"))
    registry.register(_spec("everyone.tool", ToolKind.FILE, capability="*"))
    registry.register(
        _spec("analysis.tool", ToolKind.VERIFICATION, capability="ANALYSIS")
    )
    coding = registry.tools_for_capability("CODING")
    assert [spec.name for spec in coding] == ["coding.tool", "everyone.tool"]
    analysis = registry.tools_for_capability("ANALYSIS")
    assert [spec.name for spec in analysis] == ["everyone.tool", "analysis.tool"]
    writing = registry.tools_for_capability("WRITING")
    assert [spec.name for spec in writing] == ["everyone.tool"]


def test_tool_request_arguments_snapshot_is_frozen() -> None:
    arguments: dict[str, object] = {"repo": "demo"}
    request = ToolRequest(
        request_id="r-1",
        action_id="a-1",
        agent_id="agent-1",
        task_id="t-1",
        tool_name="read.file",
        arguments=arguments,
        created_at=_BASE,
    )
    assert isinstance(request.arguments, MappingProxyType)
    arguments["repo"] = "mutated-after-construction"
    assert request.arguments["repo"] == "demo"
    with pytest.raises(TypeError):
        request.arguments["repo"] = "nope"


def test_tool_execution_result_construction_and_artifacts_frozen() -> None:
    artifacts: dict[str, object] = {"files": ["a.py"]}
    result = ToolExecutionResult(
        invocation_id="inv-1",
        tool_name="run.command",
        request_id="r-1",
        status=ToolResultStatus.SUCCEEDED,
        started_at=_BASE,
        finished_at=_BASE,
        duration_seconds=0.1,
        artifacts=artifacts,
    )
    assert isinstance(result.artifacts, MappingProxyType)
    artifacts["files"] = ["b.py"]
    assert result.artifacts["files"] == ["a.py"]
    with pytest.raises(TypeError):
        result.artifacts["files"] = ["c.py"]
    assert result.exit_code is None
    assert result.error_classification == ""
    assert result.sandbox_id == ""
    assert result.provenance == ""


# ---------------------------------------------------------------------------
# execution.py: CommandRunner
# ---------------------------------------------------------------------------


def test_command_runner_run_python_success() -> None:
    result = asyncio.run(CommandRunner().run_python("print('hello-from-smorx')"))
    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert "hello-from-smorx" in result.stdout
    assert result.duration_seconds > 0.0
    assert result.command_name == "python"
    assert result.timed_out is False


def test_command_runner_run_python_self_failure() -> None:
    code = "import sys; sys.stderr.write('boom'); sys.exit(1)"
    result = asyncio.run(CommandRunner().run_python(code))
    assert result.exit_code == 1
    assert result.timed_out is False
    assert "boom" in result.stderr


def test_command_runner_timeout_kills_process() -> None:
    runner = CommandRunner()
    started_at = time.monotonic()
    result = asyncio.run(
        runner.run_python("import time; time.sleep(5)", timeout_seconds=0.5)
    )
    elapsed = time.monotonic() - started_at
    assert result.timed_out is True
    assert result.exit_code == -1
    assert elapsed < 3.0, f"timeout kill was not bounded: {elapsed:.2f}s"


def test_command_runner_env_does_not_leak() -> None:
    os.environ["SMORX_SECRET_TEST"] = "present-should-not-leak"
    try:
        code = "import os; print('PRESENT' if 'SMORX_SECRET_TEST' in os.environ else 'ABSENT')"
        result = asyncio.run(CommandRunner().run_python(code))
        assert result.exit_code == 0
        assert "ABSENT" in result.stdout
        assert "present-should-not-leak" not in result.stdout + result.stderr
    finally:
        os.environ.pop("SMORX_SECRET_TEST", None)


def test_execution_error_on_empty_args() -> None:
    runner = CommandRunner()
    with pytest.raises(ExecutionError):
        asyncio.run(runner.run([]))


# ---------------------------------------------------------------------------
# execution.py: FailureClassifier and normalize_test_output
# ---------------------------------------------------------------------------


def test_failure_classifier_matrix() -> None:
    classify = FailureClassifier.classify
    assert (
        classify(
            exit_code=1,
            stderr="boom",
            timed_out=False,
            status=ToolResultStatus.SUCCEEDED,
        )
        == "tool failure"
    )
    assert (
        classify(
            exit_code=0, stderr="", timed_out=True, status=ToolResultStatus.SUCCEEDED
        )
        == "timeout"
    )
    assert (
        classify(
            exit_code=0, stderr="", timed_out=False, status=ToolResultStatus.DENIED
        )
        == "permission failure"
    )
    assert (
        classify(
            exit_code=0, stderr="", timed_out=False, status=ToolResultStatus.BLOCKED
        )
        == "safety/policy block"
    )
    assert (
        classify(
            exit_code=0, stderr="", timed_out=False, status=ToolResultStatus.UNAVAILABLE
        )
        == "environment/dependency failure"
    )
    assert (
        classify(
            exit_code=2,
            stderr="compile error",
            timed_out=False,
            status=ToolResultStatus.SUCCEEDED,
        )
        == "syntax/build failure"
    )
    assert (
        classify(
            exit_code=65,
            stderr="syntaxerror",
            timed_out=False,
            status=ToolResultStatus.SUCCEEDED,
        )
        == "syntax/build failure"
    )
    assert (
        classify(
            exit_code=1,
            stderr="ImportError: no module",
            timed_out=False,
            status=ToolResultStatus.SUCCEEDED,
        )
        == "integration failure"
    )
    assert (
        classify(
            exit_code=0, stderr="", timed_out=False, status=ToolResultStatus.SUCCEEDED
        )
        == ""
    )


def test_failure_classifier_from_result() -> None:
    result = ToolExecutionResult(
        invocation_id="inv-2",
        tool_name="run.test",
        request_id="r-2",
        status=ToolResultStatus.FAILED,
        started_at=_BASE,
        finished_at=_BASE,
        duration_seconds=0.2,
        exit_code=1,
        stderr="boom",
    )
    assert FailureClassifier.from_result(result) == "tool failure"


def test_normalize_test_output_counts() -> None:
    result = normalize_test_output("3 passed", "", 0)
    assert result["passed"] == 3
    assert result["failed"] == 0
    assert result["errors"] == 0
    assert result["exit_code"] == 0


def test_normalize_test_output_mixed_counts() -> None:
    result = normalize_test_output("1 failed, 2 passed in 0.5s", "", 1)
    assert result["passed"] == 2
    assert result["failed"] == 1
    assert result["errors"] == 0
    assert result["exit_code"] == 1


def test_normalize_test_output_errors_word() -> None:
    result = normalize_test_output("2 errors, 3 passed", "", 2)
    assert result["errors"] == 2
    assert result["passed"] == 3
    assert result["exit_code"] == 2


def test_normalize_test_output_empty_uses_summary_tail() -> None:
    result = normalize_test_output("", "", 0)
    assert result == {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "exit_code": 0,
        "summary_tail": "",
    }


def test_normalize_test_output_summary_tail_truncated() -> None:
    stderr = "no summary available: " + "x" * 200
    result = normalize_test_output("boom", stderr, 1)
    assert result["passed"] == 0
    assert result["failed"] == 0
    assert result["errors"] == 0
    assert result["exit_code"] == 1
    tail = str(result["summary_tail"])
    assert len(tail) == 120
    assert tail == "x" * 120

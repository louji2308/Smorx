"""Phase 8 unit tests — sandbox (§8.5), execution capture (§8.6/8.7), failure taxonomy (§8.8).

Covers: LOCAL_WORKSPACE identity + honesty (backend label everywhere);
path containment; attributed mutations with before/after hashes; real
command execution with exit-code authority; checkpoint/rollback restoring
content; execution capture binding sandbox identity; the F1–F10 taxonomy
deterministic rules; and honest refusal when no environment is allowed.

Every test is synchronous (``asyncio.run``), matching the repository
convention of no pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from smorx_develop.execution import (
    ExecutionCapture,
    FailureCode,
    classify_failure,
    failure_code_for,
)
from smorx_develop.sandbox import (
    DevelopmentSandbox,
    SandboxUnavailableError,
)
from smorx_tools.execution import CommandResult

pytest.importorskip("smorx_develop.sandbox")


def _command_result(
    exit_code: int,
    *,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
    duration: float = 0.01,
) -> CommandResult:
    return CommandResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
        timed_out=timed_out,
        command_name="python",
    )


def test_local_workspace_identity_and_honest_labeling() -> None:
    import tempfile

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as source:
            Path(source, "readme.txt").write_text("hello", encoding="utf-8")
            sandbox = await DevelopmentSandbox.create(source_root=source)
            try:
                assert sandbox.identity.backend == "LOCAL_WORKSPACE"
                assert sandbox.identity.origin == str(Path(source).resolve())
                assert sandbox.identity.sandbox_id.startswith("local-")
                identity = sandbox.identity.as_dict()
                assert identity["backend"] == "LOCAL_WORKSPACE"
            finally:
                await sandbox.destroy()

    asyncio.run(_run())


def test_provider_unavailable_and_local_disallowed_raises() -> None:
    import tempfile

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as source:
            with pytest.raises(SandboxUnavailableError) as excinfo:
                await DevelopmentSandbox.create(
                    source_root=source,
                    control=None,
                    allow_local_workspace=False,
                )
            assert "refusing to fabricate" in str(excinfo.value)

    asyncio.run(_run())


def test_workspace_derives_from_source_and_contains_paths() -> None:
    import tempfile

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as source:
            Path(source, "src").mkdir()
            Path(source, "src", "app.py").write_text("print('x')\n", encoding="utf-8")
            sandbox = await DevelopmentSandbox.create(source_root=source)
            try:
                # The working state is a copy: editing it does not touch origin.
                sandbox.write_file(
                    "src/app.py", "print('mutated')\n", reason="test write"
                )
                assert "print('x')" in Path(source, "src", "app.py").read_text(
                    encoding="utf-8"
                )
                assert "print('mutated')" in sandbox.read_file("src/app.py")

                with pytest.raises(SandboxUnavailableError):
                    sandbox.write_file("../escape.py", "x", reason="should fail")
                with pytest.raises(SandboxUnavailableError):
                    sandbox.read_file("missing.py")
            finally:
                await sandbox.destroy()

    asyncio.run(_run())


def test_mutations_are_attributed_with_hashes() -> None:
    import tempfile

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as source:
            Path(source, "a.txt").write_text("original", encoding="utf-8")
            sandbox = await DevelopmentSandbox.create(source_root=source)
            try:
                mutation = sandbox.write_file("a.txt", "updated", reason="repair step")
                assert mutation.operation == "WRITE"
                assert mutation.reason == "repair step"
                assert mutation.before_sha256 != mutation.after_sha256
                deletion = sandbox.delete_file("a.txt", reason="cleanup")
                assert deletion.operation == "DELETE"
                assert deletion.after_sha256 == ""
                assert len(sandbox.mutations) == 2
            finally:
                await sandbox.destroy()

    asyncio.run(_run())


def test_rollback_restores_checkpoint_content() -> None:
    import tempfile

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as source:
            Path(source, "b.txt").write_text("v1", encoding="utf-8")
            sandbox = await DevelopmentSandbox.create(source_root=source)
            try:
                ref = await sandbox.checkpoint("before")
                sandbox.write_file("b.txt", "v2", reason="change")
                sandbox.write_file("c.txt", "new file", reason="addition")
                await sandbox.rollback(ref)
                assert sandbox.read_file("b.txt") == "v1"
                assert not sandbox.workspace_path().joinpath("c.txt").exists()
            finally:
                await sandbox.destroy()

    asyncio.run(_run())


def test_real_command_execution_exit_code_authority() -> None:
    import tempfile

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as source:
            sandbox = await DevelopmentSandbox.create(source_root=source)
            try:
                ok = await sandbox.execute(
                    (sys.executable, "-c", "print('MARKER-OK')"), timeout_seconds=30
                )
                assert ok.exit_code == 0
                assert "MARKER-OK" in ok.stdout

                fail = await sandbox.execute(
                    (sys.executable, "-c", "raise SystemExit(3)"), timeout_seconds=30
                )
                assert fail.exit_code == 3
                assert not fail.timed_out
            finally:
                await sandbox.destroy()

    asyncio.run(_run())


class TestFailureTaxonomy:
    def test_timeout_is_f5(self) -> None:
        assert (
            classify_failure(
                exit_code=-1, stdout="", stderr="", timed_out=True, kind="COMMAND"
            )
            == FailureCode.F5_TIMEOUT
        )

    def test_permission_is_f6(self) -> None:
        assert (
            classify_failure(
                exit_code=1,
                stdout="",
                stderr="permission denied: /etc/shadow",
                kind="COMMAND",
            )
            == FailureCode.F6_PERMISSION
        )

    def test_build_hints_are_f1(self) -> None:
        assert (
            classify_failure(
                exit_code=2, stdout="", stderr="SyntaxError: bad syntax", kind="BUILD"
            )
            == FailureCode.F1_SYNTAX_BUILD
        )

    def test_unit_test_failure_is_f2(self) -> None:
        assert (
            classify_failure(
                exit_code=1, stdout="1 failed, 2 passed", stderr="", kind="UNIT_TEST"
            )
            == FailureCode.F2_UNIT_TEST
        )

    def test_integration_failure_is_f3(self) -> None:
        assert (
            classify_failure(
                exit_code=1, stdout="1 failed", stderr="", kind="INTEGRATION_TEST"
            )
            == FailureCode.F3_INTEGRATION
        )

    def test_import_error_is_f3_for_command(self) -> None:
        assert classify_failure(
            exit_code=1,
            stdout="",
            stderr="ModuleNotFoundError: no module named 'x'",
            kind="COMMAND",
        ) in {FailureCode.F1_SYNTAX_BUILD, FailureCode.F3_INTEGRATION}

    def test_success_is_empty_code(self) -> None:
        assert (
            classify_failure(
                exit_code=0, stdout="", stderr="", timed_out=False, kind="COMMAND"
            )
            == ""
        )

    def test_unknown_nonzero_is_f8(self) -> None:
        assert (
            classify_failure(
                exit_code=42, stdout="", stderr="mysterious failure", kind="COMMAND"
            )
            == FailureCode.F8_AMBIGUOUS_RESULT
        )

    def test_failure_code_for_maps_tools_vocabulary(self) -> None:
        assert failure_code_for("timeout") == FailureCode.F5_TIMEOUT
        assert failure_code_for("syntax/build failure") == FailureCode.F1_SYNTAX_BUILD
        assert failure_code_for("weird case") == FailureCode.F8_AMBIGUOUS_RESULT

    def test_all_ten_codes_exist(self) -> None:
        assert len(FailureCode.ALL) == 10
        assert len(set(FailureCode.ALL)) == 10


def test_execution_capture_binds_sandbox_identity() -> None:
    capture = ExecutionCapture(
        sandbox_id="local-test", sandbox_backend="LOCAL_WORKSPACE"
    )
    record = capture.record(
        kind="UNIT_TEST",
        command=("pytest", "-q"),
        result=_command_result(1, stdout="1 failed"),
    )
    assert record.sandbox_id == "local-test"
    assert record.sandbox_backend == "LOCAL_WORKSPACE"
    assert record.failure_code == FailureCode.F2_UNIT_TEST
    assert record.passed is False
    assert capture.records[0].execution_id.startswith("exec-")

    ok = capture.record(
        kind="COMMAND", command=("echo", "hi"), result=_command_result(0)
    )
    assert ok.passed is True
    assert ok.failure_code == ""

    as_dict = record.as_dict()
    assert as_dict["sandbox_backend"] == "LOCAL_WORKSPACE"
    assert as_dict["passed"] is False

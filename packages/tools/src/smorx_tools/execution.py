"""Bounded, cross-platform command execution and failure classification.

:class:`CommandRunner` executes short-lived commands through ``asyncio`` with a
hard timeout and a scrubbed environment (only allowlisted keys survive). Raw
execution signals are mapped to the project failure-classification vocabulary
by :class:`FailureClassifier`, and ``normalize_test_output`` parses test-runner
summary lines into structured counts.
"""

from __future__ import annotations

import asyncio
import os
import re
import signal
import sys
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path

from smorx_tools.tool import ToolExecutionResult, ToolResultStatus

_REAP_TIMEOUT_SECONDS = 2.0
_DRAIN_AFTER_KILL_SECONDS = 2.0
_MINIMAL_ENV_KEYS: tuple[str, ...] = ("PATH", "SYSTEMROOT", "SystemRoot", "TEMP", "TMP")
_BUILD_HINTS: tuple[str, ...] = (
    "compile error",
    "compilation error",
    "syntaxerror",
    "indentationerror",
    "modulenotfounderror",
    "no module named",
    "fatal error",
    "build failed",
    "compile failed",
)

_PASSED_RE = re.compile(r"(\d+)\s+passed")
_FAILED_RE = re.compile(r"(\d+)\s+failed")
_ERRORS_RE = re.compile(r"(\d+)\s+errors?")


@dataclass(frozen=True)
class CommandResult:
    """A bounded subprocess outcome; command arguments are never stored."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    command_name: str


class ExecutionError(Exception):
    """Raised when a run request is invalid (for example, empty arguments)."""


class CommandRunner:
    """Runs short-lived commands with a hard timeout and no environment leakage.

    A subprocess is created via :func:`asyncio.create_subprocess_exec` with
    stdout/stderr captured to pipes. On timeout the process (and on POSIX its
    process group) is killed and the run is reported as ``timed_out``. Non-zero
    exit codes are ordinary :class:`CommandResult` values, never exceptions.
    """

    def __init__(self, *, default_timeout_seconds: float = 30.0) -> None:
        self._default_timeout_seconds = default_timeout_seconds

    async def run(
        self,
        args: Sequence[str],
        *,
        timeout_seconds: float | None = None,
        cwd: str | Path | None = None,
        env_allowlist: Sequence[str] = (),
    ) -> CommandResult:
        """Execute ``args`` and return a :class:`CommandResult`.

        The child environment contains only allowlisted keys, or an OS-safe
        minimal environment when the allowlist is empty, so the parent's full
        environment never leaks into an unsandboxed codepath. The run is
        bounded by ``timeout_seconds`` (or the runner default); a timeout kills
        the process and is reported rather than raised.
        """
        if not args:
            raise ExecutionError("command arguments must be non-empty")
        timeout = self._default_timeout_seconds if timeout_seconds is None else timeout_seconds
        if timeout <= 0:
            raise ExecutionError("timeout_seconds must be positive")
        env = self._build_env(env_allowlist)
        cwd_str = str(cwd) if cwd is not None else None
        process = await self._create_process(args, env=env, cwd=cwd_str)
        started_at = time.monotonic()
        timed_out = False
        try:
            stdout_raw, stderr_raw = await asyncio.wait_for(self._drain(process), timeout=timeout)
        except TimeoutError:
            timed_out = True
            self._kill_process(process)
            stdout_raw = await self._read_remaining(process.stdout)
            stderr_raw = await self._read_remaining(process.stderr)
        if not timed_out and await self._reap(process):
            timed_out = True
        exit_code = -1 if timed_out else (0 if process.returncode is None else process.returncode)
        return CommandResult(
            exit_code=exit_code,
            stdout=stdout_raw.decode("utf-8", errors="replace"),
            stderr=stderr_raw.decode("utf-8", errors="replace"),
            duration_seconds=time.monotonic() - started_at,
            timed_out=timed_out,
            command_name=Path(args[0]).name,
        )

    async def run_python(self, code: str, *, timeout_seconds: float | None = None) -> CommandResult:
        """Run ``code`` with the current interpreter (``sys.executable -c code``)."""
        result = await self.run(
            (sys.executable, "-c", code),
            timeout_seconds=timeout_seconds,
        )
        command_name = Path(sys.executable).name
        if command_name.lower().endswith(".exe"):
            command_name = command_name[:-4]
        return replace(result, command_name=command_name)

    async def _create_process(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str],
        cwd: str | None,
    ) -> asyncio.subprocess.Process:
        if os.name == "posix":
            return await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
                start_new_session=True,
            )
        return await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=cwd,
        )

    def _build_env(self, env_allowlist: Sequence[str]) -> dict[str, str]:
        env: dict[str, str] = {}
        source = env_allowlist if env_allowlist else _MINIMAL_ENV_KEYS
        for key in source:
            value = os.environ.get(key)
            if value is not None:
                env[key] = value
        if "PATH" not in env:
            path_value = os.environ.get("PATH")
            if path_value is not None:
                env["PATH"] = path_value
        return env

    async def _drain(self, process: asyncio.subprocess.Process) -> tuple[bytes, bytes]:
        stdout_reader = process.stdout
        stderr_reader = process.stderr
        if stdout_reader is None or stderr_reader is None:
            raise ExecutionError("stdout/stderr pipes were not configured")
        stdout_task = asyncio.create_task(stdout_reader.read())
        stderr_task = asyncio.create_task(stderr_reader.read())
        stdout_raw = await stdout_task
        stderr_raw = await stderr_task
        return stdout_raw, stderr_raw

    async def _read_remaining(self, stream: asyncio.StreamReader | None) -> bytes:
        if stream is None:
            return b""
        try:
            return await asyncio.wait_for(stream.read(), timeout=_DRAIN_AFTER_KILL_SECONDS)
        except (TimeoutError, ValueError, ConnectionError, RuntimeError):
            return b""

    async def _reap(self, process: asyncio.subprocess.Process) -> bool:
        """Wait for process exit; kill and return ``True`` when it lingers."""
        try:
            await asyncio.wait_for(process.wait(), timeout=_REAP_TIMEOUT_SECONDS)
            return False
        except TimeoutError:
            self._kill_process(process)
            with suppress(TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=_REAP_TIMEOUT_SECONDS)
            return True

    def _kill_process(self, process: asyncio.subprocess.Process) -> None:
        killpg = getattr(os, "killpg", None)
        getpgid = getattr(os, "getpgid", None)
        sigkill = getattr(signal, "SIGKILL", 9)
        if killpg is not None and getpgid is not None and process.pid is not None:
            try:
                killpg(getpgid(process.pid), sigkill)
                return
            except (ProcessLookupError, PermissionError):
                pass
        with suppress(ProcessLookupError, OSError):
            process.kill()


class FailureClassifier:
    """Maps raw execution signals to the project failure-classification vocabulary."""

    @staticmethod
    def classify(
        *,
        exit_code: int | None,
        stderr: str,
        timed_out: bool,
        status: ToolResultStatus,
    ) -> str:
        """Return a deterministic failure classification for the given signals.

        Documented branches, evaluated in order:

        1. ``timed_out=True`` -> ``"timeout"`` (overrides every other signal).
        2. ``status DENIED`` -> ``"permission failure"``.
        3. ``status BLOCKED`` -> ``"safety/policy block"``.
        4. ``status UNAVAILABLE`` -> ``"environment/dependency failure"``.
        5. ``exit_code in (2, 65)`` with a build/compile hint in ``stderr``
           -> ``"syntax/build failure"``.
        6. non-zero ``exit_code`` -> ``"integration failure"`` when ``stderr``
           mentions ``import`` (case-insensitive), otherwise ``"tool failure"``.
        7. otherwise (``exit_code == 0`` or absent, no earlier signal) -> ``""``.
        """
        if timed_out:
            return "timeout"
        if status == ToolResultStatus.DENIED:
            return "permission failure"
        if status == ToolResultStatus.BLOCKED:
            return "safety/policy block"
        if status == ToolResultStatus.UNAVAILABLE:
            return "environment/dependency failure"
        lowered_stderr = stderr.lower()
        if exit_code in (2, 65) and any(hint in lowered_stderr for hint in _BUILD_HINTS):
            return "syntax/build failure"
        if exit_code is not None and exit_code != 0:
            if "import" in lowered_stderr:
                return "integration failure"
            return "tool failure"
        return ""

    @staticmethod
    def from_result(result: ToolExecutionResult) -> str:
        """Classify a completed :class:`ToolExecutionResult`."""
        return FailureClassifier.classify(
            exit_code=result.exit_code,
            stderr=result.stderr,
            timed_out=result.status == ToolResultStatus.TIMEOUT,
            status=result.status,
        )


def normalize_test_output(stdout: str, stderr: str, exit_code: int) -> dict[str, object]:
    """Parse runner-style summary lines into structured test counts.

    Scans ``stdout`` and ``stderr`` for ``N passed``, ``N failed``, and
    ``N error(s)`` patterns and returns a deterministic dict containing
    ``passed``, ``failed``, ``errors``, and the given ``exit_code``. When none
    of the three patterns match, all counts are zero and the raw tail of the
    combined output is stored under ``summary_tail`` (truncated to 120 chars).
    """
    combined = f"{stdout}\n{stderr}" if stderr else stdout
    passed = sum(int(value) for value in _PASSED_RE.findall(combined))
    failed = sum(int(value) for value in _FAILED_RE.findall(combined))
    errors = sum(int(value) for value in _ERRORS_RE.findall(combined))
    result: dict[str, object] = {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "exit_code": exit_code,
    }
    if passed == 0 and failed == 0 and errors == 0:
        result["summary_tail"] = combined.strip()[-120:]
    return result

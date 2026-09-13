"""Nebius Token Factory ConTree sandbox adapter (Phase 1 infrastructure layer).

Implements :class:`SandboxExecutionPort` on the synchronous ``contree_sdk``
facade. The facade is blocking, so every SDK call that can reach the network
is moved to a worker thread via :func:`asyncio.to_thread`.

Mapping to ConTree primitives:

- ``create_sandbox`` -> ``images.use(base_image)`` (lazy handle; no network).
- ``run_command`` -> ``image.run(...).wait()`` (durable child state when
  ``disposable=False``).
- ``read_file`` -> ``image.read(path)``.
- ``write_file`` -> ``image.apply_files({path: content})`` (branched state).
- ``list_files`` -> ``image.ls(path)``.
- ``checkpoint`` -> durable ``shell="true"`` run (new immutable state uuid).
- ``rollback`` -> ``images.use(checkpoint_id)``.
- ``destroy`` -> local handle discard (the ConTree server keeps durable
  states until garbage collection; there is no explicit delete API).
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn, Protocol, cast
from uuid import UUID

from contree_sdk import ContreeSync  # type: ignore[import-untyped]  # SDK ships no py.typed
from contree_sdk.auth import IAMAuth  # type: ignore[import-untyped]  # SDK ships no py.typed
from contree_sdk.config import (  # type: ignore[import-untyped]  # SDK ships no py.typed
    ContreeConfig,
)
from contree_sdk.sdk.exceptions import (  # type: ignore[import-untyped]  # SDK ships no py.typed
    ApiTimeoutError,
    ContreeImageNotFoundError,
    NotFoundError,
    OperationTimedOutError,
)

from ...contracts import (
    Checkpoint,
    CommandRequest,
    CommandResult,
    ExecutionStatus,
    FileEntry,
    HealthStatus,
    ProviderHealthReport,
    RollbackResult,
    Sandbox,
    SandboxState,
)
from ...errors import (
    CommandTimeoutError,
    ConfigurationError,
    SandboxCreationError,
    SandboxExecutionError,
)
from ...observability import TraceContext, log_event, new_id, redact_secrets
from ...settings import Settings, get_settings
from .port import SANDBOX_PROVIDER

_MAX_ERROR_OUTPUT = 500


class _SandboxResult(Protocol):
    """Minimal, typed view of the ConTree execution result."""

    exit_code: int
    stdout: str | None
    stderr: str | None
    elapsed_time: timedelta

    @property
    def truncated(self) -> bool: ...


class _SandboxHandle(Protocol):
    """Typed surface of the (untyped) ConTree image/state handle."""

    uuid: UUID | None

    def run(self, *args: Any, **kwargs: Any) -> _SandboxHandle: ...
    def wait(self) -> _SandboxHandle: ...
    def read(self, image_path: str) -> bytes: ...
    def ls(self, path: str = "/") -> list[Any]: ...
    def apply_files(self, *args: Any, **kwargs: Any) -> _SandboxHandle: ...

    @property
    def result(self) -> _SandboxResult: ...


class ContreeSandboxAdapter:
    """Nebius Token Factory ConTree implementation of ``SandboxExecutionPort``."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings if settings is not None else get_settings()
        self._ctx = TraceContext()
        self._images: dict[str, _SandboxHandle] = {}
        self._states: dict[str, SandboxState] = {}
        cred_error = self._settings.sandbox_credentials_error()
        if cred_error:
            raise ConfigurationError(cred_error, provider=SANDBOX_PROVIDER)
        self._client: Any = self._build_sync_client()

    def _build_sync_client(self) -> Any:
        auth = IAMAuth(
            token=self._settings.nebius_api_key,
            project_id=self._settings.nebius_project,
            base_url=self._settings.contree_base_url.rstrip("/"),
        )
        config = ContreeConfig(
            auth=auth,
            operation_timeout=self._settings.sandbox_timeout_seconds,
            default_truncate_output_at=self._settings.output_truncate_at,
            operation_poll_secs_min=self._settings.sandbox_poll_secs,
        )
        return ContreeSync(config=config)

    def _require_image(self, sandbox_id: str) -> _SandboxHandle:
        image = self._images.get(sandbox_id)
        if image is None:
            raise SandboxExecutionError(
                f"Unknown sandbox {sandbox_id!r}; call create_sandbox first",
                provider=SANDBOX_PROVIDER,
                detail={"sandbox_id": sandbox_id},
            )
        return image

    def _set_state(self, sandbox_id: str, state: SandboxState) -> None:
        self._states[sandbox_id] = state

    @staticmethod
    def _build_run_kwargs(request: CommandRequest, *, timeout: float, truncate_at: int) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if request.shell:
            kwargs["shell"] = request.command
        else:
            kwargs["command"] = request.command
            if request.args:
                kwargs["args"] = request.args
        if request.environment:
            kwargs["env"] = request.environment
        if request.working_directory is not None:
            kwargs["cwd"] = request.working_directory
        if request.files:
            kwargs["files"] = request.files
        if request.stdin is not None:
            kwargs["stdin"] = request.stdin
        if request.tag:
            kwargs["tag"] = request.tag
        kwargs["timeout"] = timeout
        kwargs["disposable"] = request.disposable
        kwargs["truncate_output_at"] = truncate_at
        kwargs["preserve_env"] = request.preserve_env
        return kwargs

    def _raise_sandbox_error(self, sandbox_id: str, exc: Exception) -> NoReturn:
        raise SandboxExecutionError(
            f"Sandbox {sandbox_id} operation failed: {type(exc).__name__}",
            stderr=redact_secrets(str(exc))[:1000],
            provider=SANDBOX_PROVIDER,
            request_id=self._ctx.request_id,
            run_id=self._ctx.run_id,
            operation_id=self._ctx.operation_id,
            detail={"sandbox_id": sandbox_id},
        ) from exc

    def _raise_command_timeout(self, sandbox_id: str, timeout: float, *, detail: dict[str, Any] | None = None) -> NoReturn:
        extra: dict[str, Any] = dict(detail or {})
        extra.setdefault("sandbox_id", sandbox_id)
        raise CommandTimeoutError(
            f"Sandbox {sandbox_id} command exceeded its {timeout:g}s budget",
            provider=SANDBOX_PROVIDER,
            request_id=self._ctx.request_id,
            run_id=self._ctx.run_id,
            operation_id=self._ctx.operation_id,
            detail=extra,
        )

    async def create_sandbox(
        self,
        base_image: str,
        *,
        tag: str | None = None,
        label: str | None = None,
    ) -> Sandbox:
        try:
            handle = cast(_SandboxHandle, self._client.images.use(base_image))
        except Exception as exc:
            raise SandboxCreationError(
                f"Failed to resolve base image {base_image!r}: {type(exc).__name__}",
                provider=SANDBOX_PROVIDER,
                request_id=self._ctx.request_id,
                run_id=self._ctx.run_id,
                operation_id=self._ctx.operation_id,
                detail={"base_image": base_image, "error": redact_secrets(str(exc))[:1000]},
            ) from exc
        sandbox_id = str(handle.uuid) if handle.uuid is not None else new_id("sbox")
        self._images[sandbox_id] = handle
        self._set_state(sandbox_id, SandboxState.READY)
        log_event(
            "sandbox_created",
            self._ctx,
            sandbox_id=sandbox_id,
            base_image=base_image,
            tag=tag or "",
            label=label or "",
        )
        return Sandbox(
            sandbox_id=sandbox_id,
            state=SandboxState.READY,
            base_image=base_image,
            created_at=datetime.now(UTC),
            current_tag=tag,
        )

    async def run_command(self, sandbox_id: str, request: CommandRequest) -> CommandResult:
        image = self._require_image(sandbox_id)
        timeout = request.timeout_seconds or self._settings.command_timeout_seconds
        truncate_at = request.truncate_output_at or self._settings.output_truncate_at
        kwargs = self._build_run_kwargs(request, timeout=timeout, truncate_at=truncate_at)
        self._set_state(sandbox_id, SandboxState.EXECUTING)
        try:
            prepared = image.run(**kwargs)
            executed = await asyncio.to_thread(prepared.wait)
        except (ApiTimeoutError, OperationTimedOutError) as exc:
            self._set_state(sandbox_id, SandboxState.ERRORED)
            self._raise_command_timeout(sandbox_id, timeout, detail={"error": type(exc).__name__})
        except Exception as exc:
            self._set_state(sandbox_id, SandboxState.ERRORED)
            self._raise_sandbox_error(sandbox_id, exc)

        result = executed.result
        elapsed_ms = int(result.elapsed_time.total_seconds() * 1000)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if result.elapsed_time.total_seconds() > timeout:
            self._set_state(sandbox_id, SandboxState.ERRORED)
            self._raise_command_timeout(
                sandbox_id,
                timeout,
                detail={
                    "exit_code": int(result.exit_code),
                    "elapsed_ms": elapsed_ms,
                    "stdout_tail": redact_secrets(stdout[-_MAX_ERROR_OUTPUT:]),
                    "stderr_tail": redact_secrets(stderr[-_MAX_ERROR_OUTPUT:]),
                },
            )

        exit_code = int(result.exit_code)
        status = ExecutionStatus.SUCCEEDED if exit_code == 0 else ExecutionStatus.FAILED
        checkpoint_id: str | None = None
        if not request.disposable and executed.uuid is not None:
            checkpoint_id = str(executed.uuid)
            self._images[sandbox_id] = executed
        truncated = bool(result.truncated) or len(stdout) >= truncate_at
        self._set_state(sandbox_id, SandboxState.READY)
        log_event(
            "sandbox_command_completed",
            self._ctx,
            sandbox_id=sandbox_id,
            exit_code=exit_code,
            status=status.value,
            duration_ms=elapsed_ms,
            truncated=truncated,
        )
        return CommandResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=elapsed_ms,
            status=status,
            command=request.command,
            working_directory=request.working_directory,
            environment=request.environment,
            sandbox_id=sandbox_id,
            checkpoint_id=checkpoint_id,
            correlation_id=request.correlation_id,
            truncated=truncated,
            timestamp=datetime.now(UTC),
            provider=SANDBOX_PROVIDER,
        )

    async def read_file(self, sandbox_id: str, path: str) -> bytes:
        image = self._require_image(sandbox_id)
        try:
            return await asyncio.to_thread(image.read, path)
        except Exception as exc:
            self._raise_sandbox_error(sandbox_id, exc)

    async def write_file(self, sandbox_id: str, path: str, content: str | bytes) -> str:
        image = self._require_image(sandbox_id)
        try:
            branched = await asyncio.to_thread(image.apply_files, {path: content})
        except Exception as exc:
            self._raise_sandbox_error(sandbox_id, exc)
        self._images[sandbox_id] = branched
        self._set_state(sandbox_id, SandboxState.READY)
        new_state_id = str(branched.uuid) if branched.uuid is not None else sandbox_id
        log_event("sandbox_file_written", self._ctx, sandbox_id=sandbox_id, path=path, state_id=new_state_id)
        return new_state_id

    async def list_files(self, sandbox_id: str, path: str = "/") -> list[FileEntry]:
        image = self._require_image(sandbox_id)
        try:
            entries = await asyncio.to_thread(image.ls, path)
        except Exception as exc:
            self._raise_sandbox_error(sandbox_id, exc)
        return [
            FileEntry(
                path=str(entry.path),
                size=int(entry.size),
                is_dir=bool(entry.is_dir),
                mode=int(entry.mode),
            )
            for entry in entries
        ]

    async def checkpoint(self, sandbox_id: str, label: str | None = None) -> Checkpoint:
        image = self._require_image(sandbox_id)
        timeout = self._settings.command_timeout_seconds
        self._set_state(sandbox_id, SandboxState.EXECUTING)
        try:
            prepared = image.run(shell="true", disposable=False, timeout=timeout)
            executed = await asyncio.to_thread(prepared.wait)
        except (ApiTimeoutError, OperationTimedOutError) as exc:
            self._set_state(sandbox_id, SandboxState.ERRORED)
            self._raise_command_timeout(sandbox_id, timeout, detail={"error": type(exc).__name__})
        except Exception as exc:
            self._set_state(sandbox_id, SandboxState.ERRORED)
            self._raise_sandbox_error(sandbox_id, exc)
        if executed.uuid is None:
            self._set_state(sandbox_id, SandboxState.ERRORED)
            raise SandboxExecutionError(
                f"Checkpoint on sandbox {sandbox_id} produced no server state uuid",
                provider=SANDBOX_PROVIDER,
                request_id=self._ctx.request_id,
                run_id=self._ctx.run_id,
                operation_id=self._ctx.operation_id,
                detail={"sandbox_id": sandbox_id},
            )
        checkpoint_id = str(executed.uuid)
        if checkpoint_id != sandbox_id:
            self._images[checkpoint_id] = executed
            self._set_state(checkpoint_id, SandboxState.READY)
        self._set_state(sandbox_id, SandboxState.READY)
        log_event(
            "sandbox_checkpoint_created",
            self._ctx,
            sandbox_id=sandbox_id,
            checkpoint_id=checkpoint_id,
            label=label or "",
        )
        return Checkpoint(
            checkpoint_id=checkpoint_id,
            label=label,
            created_at=datetime.now(UTC),
            sandbox_id=sandbox_id,
        )

    async def rollback(self, sandbox_id: str, checkpoint_id: str) -> RollbackResult:
        previous = self._images.get(sandbox_id)
        previous_checkpoint_id = (
            str(previous.uuid) if previous is not None and previous.uuid is not None else ""
        )
        try:
            restored = cast(_SandboxHandle, self._client.images.use(checkpoint_id))
        except Exception as exc:
            self._raise_sandbox_error(sandbox_id, exc)
        self._images[sandbox_id] = restored
        self._set_state(sandbox_id, SandboxState.READY)
        log_event("sandbox_rolled_back", self._ctx, sandbox_id=sandbox_id, checkpoint_id=checkpoint_id)
        return RollbackResult(
            previous_checkpoint_id=previous_checkpoint_id,
            restored_checkpoint_id=checkpoint_id,
            restored_at=datetime.now(UTC),
            message="Sandbox state reset to checkpoint",
        )

    async def destroy(self, sandbox_id: str) -> bool:
        if sandbox_id not in self._images:
            log_event("sandbox_destroy_skipped", self._ctx, sandbox_id=sandbox_id)
            return False
        self._images.pop(sandbox_id, None)
        self._set_state(sandbox_id, SandboxState.TERMINATED)
        log_event("sandbox_destroyed", self._ctx, sandbox_id=sandbox_id)
        return True

    async def health(self) -> ProviderHealthReport:
        checked_at = datetime.now(UTC)
        cred_error = self._settings.sandbox_credentials_error()
        if cred_error:
            return ProviderHealthReport(
                provider=SANDBOX_PROVIDER,
                status=HealthStatus.UNHEALTHY,
                checked_at=checked_at,
                detail=cred_error,
            )
        probe_image = self._settings.sandbox_base_image
        started = time.monotonic()
        try:
            await asyncio.to_thread(self._client.images.use, probe_image, True)
        except (ContreeImageNotFoundError, NotFoundError) as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            return ProviderHealthReport(
                provider=SANDBOX_PROVIDER,
                status=HealthStatus.DEGRADED,
                latency_ms=latency_ms,
                checked_at=checked_at,
                detail=(
                    f"Sandbox API reachable but probe image {probe_image!r} is not "
                    f"provisioned in the project; import it to fully verify execution: "
                    f"{type(exc).__name__}"
                ),
                models_verified=[probe_image],
            )
        except Exception as exc:
            return ProviderHealthReport(
                provider=SANDBOX_PROVIDER,
                status=HealthStatus.UNHEALTHY,
                latency_ms=int((time.monotonic() - started) * 1000),
                checked_at=checked_at,
                detail=f"Sandbox API probe failed: {type(exc).__name__}: {redact_secrets(str(exc))[:500]}",
            )
        latency_ms = int((time.monotonic() - started) * 1000)
        return ProviderHealthReport(
            provider=SANDBOX_PROVIDER,
            status=HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            checked_at=checked_at,
            detail=f"Sandbox probe image {probe_image!r} verified in project",
            models_verified=[probe_image],
        )

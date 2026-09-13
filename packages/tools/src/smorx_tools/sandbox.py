"""Honest Nebius sandbox port with explicit ``UNAVAILABLE`` semantics.

Phase 4 ``smorx_tools.sandbox`` is the control surface through which the agent
runtime reaches a *real* sandbox provider: the Phase-1 ConTree adapter in
``apps/api`` today, the Nebius Token Factory sandbox later. The
:class:`SandboxControl` registry keeps at most one active provider and, when no
provider is bound, every operation returns an explicit ``UNAVAILABLE`` result so
the system can never mistake the absence of a sandbox for a successful, real
execution.

Provider implementations (the ``apps/api`` ConTree adapter, later a Nebius
adapter) implement the structural :class:`SandboxPort` protocol. The control
planes simply forward; they never fabricate execution results.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable


class SandboxStatus(StrEnum):
    """Lifecycle status of a sandbox as reported by the bound provider."""

    UNAVAILABLE = "UNAVAILABLE"
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    CHECKPOINTED = "CHECKPOINTED"
    TERMINATED = "TERMINATED"
    ERRORED = "ERRORED"


class SandboxCapability(StrEnum):
    """Capabilities a provider may advertise for a sandbox."""

    EXECUTE = "EXECUTE"
    CHECKPOINT = "CHECKPOINT"
    ROLLBACK = "ROLLBACK"
    ARTIFACTS = "ARTIFACTS"
    NETWORK = "NETWORK"


@dataclass(frozen=True)
class SandboxOperationResult:
    """Outcome of a single sandbox operation, captured for the evidence chain."""

    status: SandboxStatus
    operation: str
    sandbox_id: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    capabilities: tuple[SandboxCapability, ...] = ()
    message: str = ""
    artifacts: Mapping[str, object] = field(default_factory=dict)


@runtime_checkable
class SandboxPort(Protocol):
    """Structural protocol implemented by real sandbox provider adapters."""

    async def create(
        self,
        *,
        request_id: str,
        image: str,
        capabilities: Sequence[SandboxCapability] = (),
    ) -> SandboxOperationResult: ...

    async def inspect(self, *, sandbox_id: str) -> SandboxOperationResult: ...

    async def execute(
        self,
        *,
        sandbox_id: str,
        command: Sequence[str],
        timeout_seconds: float = 30.0,
    ) -> SandboxOperationResult: ...

    async def checkpoint(self, *, sandbox_id: str, label: str) -> SandboxOperationResult: ...

    async def rollback(self, *, sandbox_id: str, checkpoint_ref: str) -> SandboxOperationResult: ...

    async def destroy(self, *, sandbox_id: str) -> SandboxOperationResult: ...

    async def health(self) -> SandboxOperationResult: ...


_NO_PROVIDER_MESSAGE = "no sandbox provider bound"


class SandboxControl:
    """Registry of at most one active sandbox provider.

    With no provider bound, every operation returns an explicit
    ``UNAVAILABLE`` result — the control never fabricates a fake sandbox
    success. :meth:`bind` allows swapping the provider (used by later Nebius
    wiring and by tests); ``bind(None)`` unbinds the current provider.
    """

    def __init__(self, provider: SandboxPort | None = None) -> None:
        self._provider: SandboxPort | None = provider

    def bind(self, provider: SandboxPort | None) -> None:
        """Bind the active provider, or ``None`` to unbind (documented)."""
        self._provider = provider

    def provider(self) -> SandboxPort | None:
        """Return the currently bound provider, or ``None``."""
        return self._provider

    def is_available(self) -> bool:
        """``True`` only while a provider is bound."""
        return self._provider is not None

    def _unavailable(self, operation: str) -> SandboxOperationResult:
        return SandboxOperationResult(
            status=SandboxStatus.UNAVAILABLE,
            operation=operation,
            capabilities=(),
            message=_NO_PROVIDER_MESSAGE,
        )

    async def create(
        self,
        *,
        request_id: str,
        image: str,
        capabilities: Sequence[SandboxCapability] = (),
    ) -> SandboxOperationResult:
        provider = self._provider
        if provider is None:
            return self._unavailable("create")
        return await provider.create(request_id=request_id, image=image, capabilities=capabilities)

    async def inspect(self, *, sandbox_id: str) -> SandboxOperationResult:
        provider = self._provider
        if provider is None:
            return self._unavailable("inspect")
        return await provider.inspect(sandbox_id=sandbox_id)

    async def execute(
        self,
        *,
        sandbox_id: str,
        command: Sequence[str],
        timeout_seconds: float = 30.0,
    ) -> SandboxOperationResult:
        provider = self._provider
        if provider is None:
            return self._unavailable("execute")
        return await provider.execute(
            sandbox_id=sandbox_id,
            command=command,
            timeout_seconds=timeout_seconds,
        )

    async def checkpoint(self, *, sandbox_id: str, label: str) -> SandboxOperationResult:
        provider = self._provider
        if provider is None:
            return self._unavailable("checkpoint")
        return await provider.checkpoint(sandbox_id=sandbox_id, label=label)

    async def rollback(self, *, sandbox_id: str, checkpoint_ref: str) -> SandboxOperationResult:
        provider = self._provider
        if provider is None:
            return self._unavailable("rollback")
        return await provider.rollback(sandbox_id=sandbox_id, checkpoint_ref=checkpoint_ref)

    async def destroy(self, *, sandbox_id: str) -> SandboxOperationResult:
        provider = self._provider
        if provider is None:
            return self._unavailable("destroy")
        return await provider.destroy(sandbox_id=sandbox_id)

    async def health(self) -> SandboxOperationResult:
        provider = self._provider
        if provider is None:
            return self._unavailable("health")
        return await provider.health()

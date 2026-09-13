"""Phase 8.5 — Sandbox workflow.

Creates an isolated working state derived from the canonical repository,
with explicit identity and traceability. Two honest backends exist:

- ``PROVIDER`` — a real :class:`smorx_tools.sandbox.SandboxPort` provider
  is bound; lifecycle (create/execute/checkpoint/rollback/destroy) is
  delegated to it. This is the Nebius path.
- ``LOCAL_WORKSPACE`` — no provider is available, so a disposable local
  working copy is created from the source tree. It is IDENTIFIED as a
  local workspace everywhere it appears (identity, traces, evidence) and
  is never presented as a Nebius sandbox (AGENTS.md §3, §13).

If neither is permitted, :class:`SandboxUnavailableError` is raised — the
system refuses to pretend a sandbox exists.

Every consequential file mutation goes through :meth:`write_file` /
:meth:`delete_file`, which enforce workspace containment and record
path, operation, reason, and before/after content hashes for attribution
(Task → Decision → Tool Invocation → Execution Result → Mutation).
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import tempfile
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from smorx_tools.execution import CommandResult, CommandRunner
from smorx_tools.sandbox import SandboxCapability, SandboxControl, SandboxStatus

__all__ = [
    "DevelopmentSandbox",
    "FileMutation",
    "SandboxIdentity",
    "SandboxUnavailableError",
]


class SandboxUnavailableError(Exception):
    """Raised when no execution environment is available and local
    workspaces are not permitted — honesty over fabrication."""


@dataclass(frozen=True)
class SandboxIdentity:
    """Explicit, traceable identity of an isolated working state."""

    sandbox_id: str
    backend: str  # PROVIDER | LOCAL_WORKSPACE
    origin: str  # absolute source root the workspace derives from
    workspace_root: str  # PROVIDER: provider-side root or ''; LOCAL: local path
    provider_sandbox_id: str  # provider identifier when backend=PROVIDER
    created_at: datetime
    capabilities: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "backend": self.backend,
            "origin": self.origin,
            "workspace_root": self.workspace_root,
            "provider_sandbox_id": self.provider_sandbox_id,
            "created_at": self.created_at.isoformat(),
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True)
class FileMutation:
    """One attributed, consequential file mutation."""

    mutation_id: str
    operation: str  # WRITE | DELETE
    path: str  # workspace-relative
    reason: str
    before_sha256: str
    after_sha256: str
    at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "operation": self.operation,
            "path": self.path,
            "reason": self.reason,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "at": self.at.isoformat(),
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_source_root(source_root: str | Path) -> Path:
    """Validate and resolve the source root (sync helper for to_thread)."""
    origin = Path(source_root).resolve()
    if not origin.is_dir():
        raise SandboxUnavailableError(f"source root is not an existing directory: {origin}")
    return origin


def _derive_local_workspace(origin: Path) -> Path:
    """Create the disposable local working copy (sync helper: the blocking
    filesystem work stays out of the async ``create`` path)."""
    workspace = Path(tempfile.mkdtemp(prefix="smorx-dev-"))
    shutil.copytree(origin, workspace, dirs_exist_ok=True, symlinks=True)
    return workspace


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DevelopmentSandbox:
    """Isolated working state with controlled mutation and real execution."""

    def __init__(
        self,
        *,
        identity: SandboxIdentity,
        control: SandboxControl | None = None,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self._identity = identity
        self._control = control
        self._runner = command_runner or CommandRunner()
        self._mutations: list[FileMutation] = []
        self._checkpoints: dict[str, dict[str, bytes]] = {}
        self._destroyed = False

    # -- construction -----------------------------------------------------

    @classmethod
    async def create(
        cls,
        *,
        source_root: str | Path,
        control: SandboxControl | None = None,
        allow_local_workspace: bool = True,
        image: str = "python:3.11-slim",
        request_id: str | None = None,
    ) -> DevelopmentSandbox:
        """Derive an isolated working state from ``source_root``.

        Provider path: when a ``SandboxControl`` with a bound provider is
        supplied, the provider creates the sandbox and this object delegates
        execution/checkpoint/rollback/destroy to it.

        Local path: when no provider is available and
        ``allow_local_workspace`` is true, a disposable local working copy
        is created and honestly identified as ``LOCAL_WORKSPACE``.

        Otherwise raises :class:`SandboxUnavailableError` (never fabricates).
        """
        origin = await asyncio.to_thread(_resolve_source_root, source_root)

        if control is not None and control.is_available():
            result = await control.create(
                request_id=request_id or f"develop-{uuid.uuid4()}",
                image=image,
                capabilities=(
                    SandboxCapability.EXECUTE,
                    SandboxCapability.CHECKPOINT,
                    SandboxCapability.ROLLBACK,
                ),
            )
            if result.status not in {SandboxStatus.CREATED, SandboxStatus.READY}:
                raise SandboxUnavailableError(
                    f"provider sandbox creation failed: {result.status} {result.message}"
                )
            identity = SandboxIdentity(
                sandbox_id=f"sbx-{uuid.uuid4()}",
                backend="PROVIDER",
                origin=str(origin),
                workspace_root="",
                provider_sandbox_id=result.sandbox_id,
                created_at=datetime.now(UTC),
                capabilities=tuple(cap.name for cap in result.capabilities),
            )
            return cls(identity=identity, control=control)

        if not allow_local_workspace:
            raise SandboxUnavailableError(
                "no sandbox provider is bound and local workspaces are not "
                "permitted; refusing to fabricate an execution environment"
            )

        workspace = _derive_local_workspace(origin)
        identity = SandboxIdentity(
            sandbox_id=f"local-{uuid.uuid4()}",
            backend="LOCAL_WORKSPACE",
            origin=str(origin),
            workspace_root=str(workspace),
            provider_sandbox_id="",
            created_at=datetime.now(UTC),
            capabilities=("EXECUTE", "CHECKPOINT", "ROLLBACK", "MUTATE"),
        )
        return cls(identity=identity, control=None)

    # -- introspection ----------------------------------------------------

    @property
    def identity(self) -> SandboxIdentity:
        return self._identity

    @property
    def mutations(self) -> tuple[FileMutation, ...]:
        return tuple(self._mutations)

    def workspace_path(self) -> Path:
        if self._identity.backend != "LOCAL_WORKSPACE":
            raise SandboxUnavailableError(
                "workspace_path() is only valid for the LOCAL_WORKSPACE backend"
            )
        return Path(self._identity.workspace_root)

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": self._identity.as_dict(),
            "mutations": [m.as_dict() for m in self._mutations],
            "checkpoints": sorted(self._checkpoints),
        }

    # -- controlled mutation ----------------------------------------------

    def _resolve_inside(self, relative: str) -> Path:
        root = self.workspace_path().resolve()
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise SandboxUnavailableError(
                f"path escapes the sandbox workspace: {relative!r}"
            ) from None
        return candidate

    def write_file(self, relative_path: str, content: str | bytes, *, reason: str) -> FileMutation:
        """Controlled write inside the workspace with attribution."""
        target = self._resolve_inside(relative_path)
        before = _sha256_file(target) if target.is_file() else ""
        data = content.encode("utf-8") if isinstance(content, str) else content
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        mutation = FileMutation(
            mutation_id=f"mut-{uuid.uuid4()}",
            operation="WRITE",
            path=relative_path,
            reason=reason,
            before_sha256=before,
            after_sha256=_sha256_bytes(data),
            at=datetime.now(UTC),
        )
        self._mutations.append(mutation)
        return mutation

    def delete_file(self, relative_path: str, *, reason: str) -> FileMutation:
        """Controlled delete inside the workspace with attribution."""
        target = self._resolve_inside(relative_path)
        if not target.is_file():
            raise SandboxUnavailableError(f"cannot delete missing file: {relative_path!r}")
        before = _sha256_file(target)
        target.unlink()
        mutation = FileMutation(
            mutation_id=f"mut-{uuid.uuid4()}",
            operation="DELETE",
            path=relative_path,
            reason=reason,
            before_sha256=before,
            after_sha256="",
            at=datetime.now(UTC),
        )
        self._mutations.append(mutation)
        return mutation

    def read_file(self, relative_path: str) -> str:
        target = self._resolve_inside(relative_path)
        if not target.is_file():
            raise SandboxUnavailableError(f"no such file in workspace: {relative_path!r}")
        return target.read_text(encoding="utf-8", errors="replace")

    # -- execution ----------------------------------------------------------

    async def execute(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = 30.0,
        env_allowlist: Sequence[str] = (),
    ) -> CommandResult:
        """Run a real command inside the working state."""
        if self._destroyed:
            raise SandboxUnavailableError("sandbox has been destroyed")
        if self._identity.backend == "PROVIDER":
            assert self._control is not None
            result = await self._control.execute(
                sandbox_id=self._identity.provider_sandbox_id,
                command=command,
                timeout_seconds=timeout_seconds,
            )
            # Provider adapters report timeout through their own status/message
            # vocabulary; the local runner path reports timed_out natively.
            return CommandResult(
                exit_code=result.exit_code if result.exit_code is not None else -1,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=result.duration_seconds,
                timed_out=False,
                command_name=Path(command[0]).name if command else "",
            )
        return await self._runner.run(
            command,
            timeout_seconds=timeout_seconds,
            cwd=self._identity.workspace_root,
            env_allowlist=env_allowlist,
        )

    # -- checkpoint / rollback / destroy -----------------------------------

    async def checkpoint(self, label: str) -> str:
        """Capture a restorable checkpoint; return its reference."""
        if self._identity.backend == "PROVIDER":
            assert self._control is not None
            result = await self._control.checkpoint(
                sandbox_id=self._identity.provider_sandbox_id, label=label
            )
            if result.status != SandboxStatus.CHECKPOINTED:
                raise SandboxUnavailableError(f"provider checkpoint failed: {result.message}")
            return result.sandbox_id or label
        root = self.workspace_path()
        snapshot: dict[str, bytes] = {}
        for path in sorted(root.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
        self._checkpoints[label] = snapshot
        return label

    async def rollback(self, checkpoint_ref: str) -> None:
        """Restore the working state to a checkpoint."""
        if self._identity.backend == "PROVIDER":
            assert self._control is not None
            result = await self._control.rollback(
                sandbox_id=self._identity.provider_sandbox_id, checkpoint_ref=checkpoint_ref
            )
            if result.status == SandboxStatus.UNAVAILABLE:
                raise SandboxUnavailableError(f"provider rollback failed: {result.message}")
            return
        snapshot = self._checkpoints.get(checkpoint_ref)
        if snapshot is None:
            raise SandboxUnavailableError(f"unknown checkpoint: {checkpoint_ref!r}")
        root = self.workspace_path()
        current = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        for relative in sorted(current - set(snapshot)):
            (root / relative).unlink()
        for relative, data in snapshot.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    async def destroy(self) -> None:
        """Terminate the working state and release local resources."""
        if self._destroyed:
            return
        if self._identity.backend == "PROVIDER":
            assert self._control is not None
            await self._control.destroy(sandbox_id=self._identity.provider_sandbox_id)
        else:
            shutil.rmtree(self.workspace_path(), ignore_errors=True)
        self._destroyed = True

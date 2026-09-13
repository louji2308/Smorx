"""Unit tests for the sandbox port, the human control plane, and the repo toolkit.

Covers ``smorx_tools.sandbox`` (honest ``UNAVAILABLE`` semantics + provider
swapping), ``smorx_tools.human`` (pause/resume/abort approval lifecycle with
bounded expiry), and ``smorx_tools.repo`` (path safety + attributable
mutations). Sandbox tests run the async provider surface through
``asyncio.run`` so no async test plugin is required.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

import pytest
from smorx_tools.human import (
    ApprovalError,
    ApprovalStatus,
    ControlState,
    HumanControlPlane,
)
from smorx_tools.repo import PathSafety, PathSafetyError, RepositoryToolkit
from smorx_tools.sandbox import (
    SandboxCapability,
    SandboxControl,
    SandboxOperationResult,
    SandboxPort,
    SandboxStatus,
)

_NO_PROVIDER_MESSAGE = "no sandbox provider bound"


def _run(coro) -> object:
    return asyncio.run(coro)


class FakeProvider:
    """Test provider implementing the ``SandboxPort`` structural surface."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[str] = []
        self.capabilities = (SandboxCapability.EXECUTE, SandboxCapability.CHECKPOINT)

    def _result(
        self, operation: str, status: SandboxStatus, sandbox_id: str = ""
    ) -> SandboxOperationResult:
        return SandboxOperationResult(
            status=status,
            operation=operation,
            sandbox_id=sandbox_id,
            capabilities=self.capabilities,
        )

    async def create(
        self,
        *,
        request_id: str,
        image: str,
        capabilities: tuple[SandboxCapability, ...] = (),
    ) -> SandboxOperationResult:
        self.calls.append("create")
        return self._result("create", SandboxStatus.CREATED, f"{self.name}-sbx-1")

    async def inspect(self, *, sandbox_id: str) -> SandboxOperationResult:
        self.calls.append("inspect")
        return self._result("inspect", SandboxStatus.READY, sandbox_id)

    async def execute(
        self,
        *,
        sandbox_id: str,
        command: tuple[str, ...],
        timeout_seconds: float = 30.0,
    ) -> SandboxOperationResult:
        self.calls.append("execute")
        result = self._result("execute", SandboxStatus.RUNNING, sandbox_id)
        return SandboxOperationResult(
            status=result.status,
            operation=result.operation,
            sandbox_id=result.sandbox_id,
            exit_code=0,
            stdout="ok",
            capabilities=result.capabilities,
        )

    async def checkpoint(
        self, *, sandbox_id: str, label: str
    ) -> SandboxOperationResult:
        self.calls.append("checkpoint")
        return self._result("checkpoint", SandboxStatus.CHECKPOINTED, sandbox_id)

    async def rollback(
        self, *, sandbox_id: str, checkpoint_ref: str
    ) -> SandboxOperationResult:
        self.calls.append("rollback")
        return self._result("rollback", SandboxStatus.READY, sandbox_id)

    async def destroy(self, *, sandbox_id: str) -> SandboxOperationResult:
        self.calls.append("destroy")
        return self._result("destroy", SandboxStatus.TERMINATED, sandbox_id)

    async def health(self) -> SandboxOperationResult:
        self.calls.append("health")
        return self._result("health", SandboxStatus.READY)


# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------


def test_no_provider_create_is_honestly_unavailable() -> None:
    control = SandboxControl()
    result = _run(control.create(request_id="r1", image="python:3.11"))
    assert isinstance(result, SandboxOperationResult)
    assert result.status is SandboxStatus.UNAVAILABLE
    assert result.operation == "create"
    assert result.message == _NO_PROVIDER_MESSAGE
    assert result.capabilities == ()


def test_fake_provider_satisfies_sandbox_port_protocol() -> None:
    fake = FakeProvider("p1")
    assert isinstance(fake, SandboxPort)


def test_bound_provider_round_trip_preserves_sandbox_id() -> None:
    fake = FakeProvider("p1")
    control = SandboxControl(fake)
    assert control.is_available() is True

    created = _run(control.create(request_id="r1", image="python:3.11"))
    assert created.status is SandboxStatus.CREATED
    sbx = created.sandbox_id
    assert sbx == "p1-sbx-1"

    inspected = _run(control.inspect(sandbox_id=sbx))
    assert inspected.status is SandboxStatus.READY
    assert inspected.sandbox_id == sbx

    executed = _run(control.execute(sandbox_id=sbx, command=("echo", "hi")))
    assert executed.status is SandboxStatus.RUNNING
    assert executed.sandbox_id == sbx
    assert executed.exit_code == 0
    assert executed.stdout == "ok"

    checkpointed = _run(control.checkpoint(sandbox_id=sbx, label="milestone"))
    assert checkpointed.status is SandboxStatus.CHECKPOINTED

    rolled_back = _run(control.rollback(sandbox_id=sbx, checkpoint_ref="milestone"))
    assert rolled_back.status is SandboxStatus.READY

    destroyed = _run(control.destroy(sandbox_id=sbx))
    assert destroyed.status is SandboxStatus.TERMINATED
    assert destroyed.sandbox_id == sbx

    assert fake.calls == [
        "create",
        "inspect",
        "execute",
        "checkpoint",
        "rollback",
        "destroy",
    ]


def test_health_with_and_without_provider() -> None:
    control = SandboxControl()
    unhealthy = _run(control.health())
    assert unhealthy.status is SandboxStatus.UNAVAILABLE
    assert unhealthy.operation == "health"

    fake = FakeProvider("p1")
    control.bind(fake)
    healthy = _run(control.health())
    assert healthy.status is SandboxStatus.READY
    assert healthy.operation == "health"


def test_bind_switches_provider_and_old_is_no_longer_used() -> None:
    old_provider = FakeProvider("old")
    new_provider = FakeProvider("new")
    control = SandboxControl(old_provider)

    first = _run(control.create(request_id="r1", image="python:3.11"))
    assert first.sandbox_id == "old-sbx-1"
    assert old_provider.calls.count("create") == 1

    control.bind(new_provider)
    second = _run(control.create(request_id="r2", image="python:3.12"))
    assert second.sandbox_id == "new-sbx-1"
    assert old_provider.calls.count("create") == 1
    assert new_provider.calls.count("create") == 1


def test_bind_none_unbinds_provider() -> None:
    control = SandboxControl(FakeProvider("p1"))
    assert control.is_available() is True
    control.bind(None)
    assert control.is_available() is False
    assert control.provider() is None
    result = _run(control.execute(sandbox_id="sbx-1", command=("echo", "hi")))
    assert result.status is SandboxStatus.UNAVAILABLE
    assert result.operation == "execute"
    assert result.message == _NO_PROVIDER_MESSAGE


def test_is_available_tracks_binding_lifecycle() -> None:
    control = SandboxControl()
    assert control.is_available() is False
    fake = FakeProvider("p1")
    control.bind(fake)
    assert control.is_available() is True
    assert control.provider() is fake
    control.bind(None)
    assert control.is_available() is False


# ---------------------------------------------------------------------------
# Human control plane
# ---------------------------------------------------------------------------

APPROVAL_GATE_METHODS = ("is_paused", "can_execute", "approval_for")


@runtime_checkable
class _ApprovalGateShape(Protocol):
    """Structural mirror of the ApprovalGate protocol consumed by control.py."""

    def is_paused(self) -> bool: ...

    def can_execute(self) -> bool: ...

    def approval_for(self, action_id: str, tool_name: str) -> object | None: ...


def test_state_transitions_pause_resume_abort() -> None:
    plane = HumanControlPlane()
    assert plane.state is ControlState.RUNNING
    assert plane.can_execute() is True
    assert plane.is_paused() is False

    plane.pause()
    assert plane.state is ControlState.PAUSED
    assert plane.is_paused() is True
    assert plane.can_execute() is False

    plane.resume()
    assert plane.state is ControlState.RUNNING
    assert plane.can_execute() is True
    assert plane.is_paused() is False

    plane.abort()
    assert plane.state is ControlState.ABORTED
    assert plane.can_execute() is False

    with pytest.raises(ApprovalError):
        plane.resume()
    with pytest.raises(ApprovalError):
        plane.pause()


def test_request_approval_returns_unique_pending_requests() -> None:
    plane = HumanControlPlane()
    first = plane.request_approval(action_id="a1", tool_name="run", reason="risky")
    second = plane.request_approval(action_id="a1", tool_name="run", reason="again")

    assert first.status is ApprovalStatus.PENDING
    assert second.status is ApprovalStatus.PENDING
    assert first.approval_id != second.approval_id
    assert first.action_id == "a1"
    assert first.tool_name == "run"
    assert first.requested_at.tzinfo is not None
    assert first.expires_at is not None
    assert (first.expires_at - first.requested_at).total_seconds() == pytest.approx(
        300.0
    )

    pending = plane.pending_approvals()
    assert {request.approval_id for request in pending} == {
        first.approval_id,
        second.approval_id,
    }


def test_approve_records_decision_and_grants_approval() -> None:
    plane = HumanControlPlane()
    request = plane.request_approval(action_id="a1", tool_name="run")
    decided = plane.approve(request.approval_id, by="human")

    assert decided.status is ApprovalStatus.APPROVED
    assert decided.decided_at is not None
    assert decided.decided_by == "human"
    assert plane.approval_for("a1", "run") is decided
    assert plane.is_approved_for("a1", "run") is True
    assert plane.pending_approvals() == ()


def test_deny_revokes_execution() -> None:
    plane = HumanControlPlane()
    request = plane.request_approval(action_id="a1", tool_name="run")
    decided = plane.deny(request.approval_id, by="human")

    assert decided.status is ApprovalStatus.DENIED
    assert decided.decided_by == "human"
    assert plane.is_approved_for("a1", "run") is False
    assert plane.pending_approvals() == ()


def test_approve_non_pending_request_raises() -> None:
    plane = HumanControlPlane()
    request = plane.request_approval(action_id="a1", tool_name="run")
    plane.deny(request.approval_id)
    with pytest.raises(ApprovalError):
        plane.approve(request.approval_id)
    with pytest.raises(ApprovalError):
        plane.deny(request.approval_id)


def test_expired_approval_is_not_trusted_but_remains_visible() -> None:
    plane = HumanControlPlane()
    request = plane.request_approval(action_id="a1", tool_name="run", ttl_seconds=0.01)
    approved = plane.approve(request.approval_id)
    assert approved.status is ApprovalStatus.APPROVED

    time.sleep(0.05)

    assert plane.is_approved_for("a1", "run") is False

    pruned = plane.approval_for("a1", "run")
    assert pruned is not None
    assert pruned.status is ApprovalStatus.EXPIRED
    assert pruned.approval_id == request.approval_id
    assert pruned.action_id == "a1"
    assert pruned.tool_name == "run"
    assert pruned.decided_at is not None
    assert pruned.decided_by == "human"
    assert pruned.expires_at is not None


def test_approval_gate_shape_is_structural() -> None:
    plane = HumanControlPlane()
    assert isinstance(plane, _ApprovalGateShape)
    for method in APPROVAL_GATE_METHODS:
        assert callable(getattr(plane, method))

    request = plane.request_approval(action_id="a1", tool_name="run")
    assert plane.approval_for("a1", "run") is request
    assert plane.approval_for("missing", "run") is None
    assert plane.is_paused() is False
    assert plane.can_execute() is True


# ---------------------------------------------------------------------------
# Repo toolkit
# ---------------------------------------------------------------------------


def test_path_safety_accepts_internal_and_rejects_escapes(tmp_path: Path) -> None:
    safety = PathSafety(roots=[tmp_path])
    inside = safety.resolve("sub/dir/file.txt")
    assert inside.is_relative_to(tmp_path)

    assert safety.is_safe("sub/dir/file.txt")
    assert safety.is_safe(tmp_path / "file.txt")
    assert not safety.is_safe("../escape")
    assert not safety.is_safe(tmp_path.parent / "outside")

    with pytest.raises(PathSafetyError):
        safety.resolve("../escape")
    with pytest.raises(PathSafetyError):
        safety.resolve(str(tmp_path.parent / "outside"))


def test_write_creates_parent_dirs_and_read_round_trips(tmp_path: Path) -> None:
    toolkit = RepositoryToolkit(root=tmp_path)
    written = toolkit.write("a/b/c.txt", "hello")
    assert Path(written) == (tmp_path / "a/b/c.txt").resolve()
    assert toolkit.read("a/b/c.txt") == "hello"
    assert toolkit.exists("a/b/c.txt") is True


def test_create_refuses_existing_while_write_overwrites(tmp_path: Path) -> None:
    toolkit = RepositoryToolkit(root=tmp_path)
    toolkit.create("x.txt", "one")
    assert toolkit.read("x.txt") == "one"

    with pytest.raises(PathSafetyError):
        toolkit.create("x.txt", "two")

    toolkit.write("x.txt", "two")
    assert toolkit.read("x.txt") == "two"


def test_delete_removes_file_and_records_attribution(tmp_path: Path) -> None:
    toolkit = RepositoryToolkit(
        root=tmp_path,
        writer="orchestrator",
        reason="default-reason",
    )
    toolkit.write("f.txt", "data")
    deleted = toolkit.delete("f.txt", reason="cleanup")

    assert Path(deleted) == (tmp_path / "f.txt").resolve()
    assert toolkit.exists("f.txt") is False

    deletions = [m for m in toolkit.mutations() if m["operation"] == "delete"]
    assert len(deletions) == 1
    assert deletions[0]["writer"] == "orchestrator"
    assert deletions[0]["reason"] == "cleanup"


def test_delete_missing_path_raises(tmp_path: Path) -> None:
    toolkit = RepositoryToolkit(root=tmp_path)
    with pytest.raises(PathSafetyError):
        toolkit.delete("missing.txt")


def test_mutations_are_append_only_and_well_formed(tmp_path: Path) -> None:
    toolkit = RepositoryToolkit(root=tmp_path, writer="agent", reason="phase-4")
    toolkit.write("one.txt", "1")
    toolkit.create("two.txt", "2")
    toolkit.delete("one.txt", reason="done")

    mutations = toolkit.mutations()
    assert [m["operation"] for m in mutations] == ["write", "create", "delete"]
    for record in mutations:
        assert set(record.keys()) == {"path", "operation", "writer", "reason", "at"}
        assert record["writer"] == "agent"
        assert isinstance(record["path"], str)
        assert isinstance(record["reason"], str)
        assert isinstance(record["at"], str)
        assert Path(str(record["path"])).is_absolute()

    assert mutations[0]["reason"] == "phase-4"
    assert mutations[2]["reason"] == "done"


def test_list_files_returns_relative_sorted_listing(tmp_path: Path) -> None:
    toolkit = RepositoryToolkit(root=tmp_path)
    toolkit.write("d1/f1.txt", "")
    toolkit.write("d2/deep/f2.txt", "")
    toolkit.create("top.txt", "")

    assert toolkit.list_files() == ("d1/f1.txt", "d2/deep/f2.txt", "top.txt")
    assert toolkit.list_files("d2") == ("deep/f2.txt",)
    assert toolkit.list_files("nope") == ()


def test_escape_write_raises_and_records_nothing(tmp_path: Path) -> None:
    toolkit = RepositoryToolkit(root=tmp_path)
    with pytest.raises(PathSafetyError):
        toolkit.write("../escape.txt", "boom")
    assert toolkit.mutations() == ()

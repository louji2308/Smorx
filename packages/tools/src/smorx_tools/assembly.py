"""Assemble the default policy-controlled tool registry and control plane.

Phase 4 integration seam (orchestrator-owned): binds the concrete tools of
``smorx_tools`` (file/repository operations, bounded command execution,
sandbox dispatch) into a :class:`~smorx_tools.tool.ToolRegistry` and wires a
:class:`~smorx_tools.control.ControlPlane` over it with the risk policy
engine and audit trail.

Handlers never raise for an ordinary user-triggered problem: they return a
completed :class:`ToolExecutionResult` with an explicit status and
classification so the control plane records a truthful audit entry. Only
genuine invariant violations escape the tool itself.

Sandbox tools are fully honest: with no :class:`SandboxControl` provider
bound they return ``UNAVAILABLE`` (``environment/dependency failure``); the
Nebius provider wiring lands in a later phase and simply binds a provider.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from smorx_tools.audit import AuditTrail
from smorx_tools.control import ApprovalGate, ControlPlane
from smorx_tools.execution import (
    CommandResult,
    CommandRunner,
    FailureClassifier,
    normalize_test_output,
)
from smorx_tools.policies import PolicyEngine
from smorx_tools.repo import RepositoryToolkit
from smorx_tools.sandbox import SandboxControl, SandboxOperationResult
from smorx_tools.tool import (
    ToolExecutionResult,
    ToolKind,
    ToolRegistry,
    ToolRequest,
    ToolResultStatus,
    ToolSpec,
)

__all__ = [
    "assemble_control_plane",
    "assemble_default_registry",
]


def _result(
    request: ToolRequest,
    status: ToolResultStatus,
    *,
    stdout: str = "",
    stderr: str = "",
    exit_code: int | None = None,
    artifacts: dict[str, object] | None = None,
    classification: str = "",
    message: str = "",
) -> ToolExecutionResult:
    started_at = datetime.now(UTC)
    finished_at = datetime.now(UTC)
    return ToolExecutionResult(
        invocation_id=uuid4().hex,
        tool_name=request.tool_name,
        request_id=request.request_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=(finished_at - started_at).total_seconds(),
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        artifacts=dict(artifacts) if artifacts is not None else {},
        error_classification=classification,
        timeout_seconds=request.timeout_seconds,
        sandbox_id=request.sandbox_id,
        provenance=f"tool:{request.tool_name};task:{request.task_id}",
        message=message,
    )


def _ok(request: ToolRequest, *, stdout: str = "") -> ToolExecutionResult:
    return _result(request, ToolResultStatus.SUCCEEDED, stdout=stdout, exit_code=0)


def _failed(
    request: ToolRequest, message: str, classification: str = "tool failure"
) -> ToolExecutionResult:
    return _result(
        request,
        ToolResultStatus.FAILED,
        stderr=message,
        classification=classification,
        message=message,
    )


def _arg(request: ToolRequest, key: str, default: str = "") -> str:
    value = request.arguments.get(key)
    return value if isinstance(value, str) and value else default


def _sandbox_result(request: ToolRequest, operation: SandboxOperationResult) -> ToolExecutionResult:
    if operation.status.value == "UNAVAILABLE":
        return _result(
            request,
            ToolResultStatus.UNAVAILABLE,
            classification="environment/dependency failure",
            message=operation.message,
            artifacts={"sandbox_status": operation.status.value},
        )
    succeeded = operation.status.value in (
        "CREATED",
        "READY",
        "RUNNING",
        "CHECKPOINTED",
        "TERMINATED",
    )
    if not succeeded:
        return _result(
            request,
            ToolResultStatus.FAILED,
            stderr=operation.stderr,
            exit_code=operation.exit_code,
            classification=FailureClassifier.classify(
                exit_code=operation.exit_code,
                stderr=operation.stderr,
                timed_out=False,
                status=ToolResultStatus.FAILED,
            ),
            message=operation.message or "sandbox operation failed",
            artifacts={
                "sandbox_status": operation.status.value,
                "operation": operation.operation,
                "capabilities": [c.value for c in operation.capabilities],
            },
        )
    return _result(
        request,
        ToolResultStatus.SUCCEEDED,
        stdout=operation.stdout,
        exit_code=operation.exit_code or 0,
        message=operation.message,
        artifacts={
            "sandbox_status": operation.status.value,
            "operation": operation.operation,
            "sandbox_id": operation.sandbox_id,
            "capabilities": [c.value for c in operation.capabilities],
        },
    )


def assemble_default_registry(
    *,
    repo_root: Path,
    runner: CommandRunner | None = None,
    toolkit: RepositoryToolkit | None = None,
    sandbox_control: SandboxControl | None = None,
) -> ToolRegistry:
    """Build the default registry with real, bound handler implementations.

    ``repo_root`` is the only required parameter: it is the root the
    repository/file tools may read and mutate.
    """
    registry = ToolRegistry()
    root = repo_root.resolve()
    resolved_toolkit = toolkit if toolkit is not None else RepositoryToolkit(root=root)
    resolved_runner = runner if runner is not None else CommandRunner()
    resolved_sandbox = sandbox_control if sandbox_control is not None else SandboxControl()

    async def _h_repository_inspect(request: ToolRequest) -> ToolExecutionResult:
        base = _arg(request, "path")
        try:
            files = resolved_toolkit.list_files(base)
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        return _result(
            request,
            ToolResultStatus.SUCCEEDED,
            exit_code=0,
            artifacts={"files": files, "count": len(files)},
            message=f"inspected repository root {root}",
        )

    async def _h_file_read(request: ToolRequest) -> ToolExecutionResult:
        path = _arg(request, "path")
        if not path:
            return _failed(request, "no path provided")
        try:
            content = resolved_toolkit.read(path)
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        return _ok(request, stdout=content)

    async def _h_file_write(request: ToolRequest) -> ToolExecutionResult:
        path = _arg(request, "path")
        if not path:
            return _failed(request, "no path provided")
        content = request.arguments.get("content", "")
        if not isinstance(content, str):
            return _failed(request, "content must be a string")
        reason = _arg(request, "reason", resolved_toolkit.reason)
        try:
            resolved = resolved_toolkit.write(path, content, reason=reason)
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        return _ok(request, stdout=f"wrote {resolved}")

    async def _h_file_create(request: ToolRequest) -> ToolExecutionResult:
        path = _arg(request, "path")
        if not path:
            return _failed(request, "no path provided")
        content = request.arguments.get("content", "")
        if not isinstance(content, str):
            return _failed(request, "content must be a string")
        reason = _arg(request, "reason", resolved_toolkit.reason)
        try:
            resolved = resolved_toolkit.create(path, content, reason=reason)
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        return _ok(request, stdout=f"created {resolved}")

    async def _h_file_delete(request: ToolRequest) -> ToolExecutionResult:
        path = _arg(request, "path")
        if not path:
            return _failed(request, "no path provided")
        reason = _arg(request, "reason", resolved_toolkit.reason)
        try:
            resolved = resolved_toolkit.delete(path, reason=reason)
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        return _ok(request, stdout=f"deleted {resolved}")

    async def _h_command_run(request: ToolRequest) -> ToolExecutionResult:
        command = _arg(request, "command")
        python_code = _arg(request, "python_code")
        try:
            if python_code:
                outcome: CommandResult = await resolved_runner.run_python(
                    python_code, timeout_seconds=request.timeout_seconds
                )
            elif command:
                outcome = await resolved_runner.run(
                    tuple(command.split(" ")),
                    timeout_seconds=request.timeout_seconds,
                    cwd=root,
                )
            else:
                return _failed(request, "no command or python_code provided")
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        status = (
            ToolResultStatus.SUCCEEDED
            if outcome.exit_code == 0 and not outcome.timed_out
            else (ToolResultStatus.TIMEOUT if outcome.timed_out else ToolResultStatus.FAILED)
        )
        classification = FailureClassifier.classify(
            exit_code=outcome.exit_code,
            stderr=outcome.stderr,
            timed_out=outcome.timed_out,
            status=status,
        )
        return _result(
            request,
            status,
            stdout=outcome.stdout,
            stderr=outcome.stderr,
            exit_code=outcome.exit_code,
            classification=classification,
            message=f"command {outcome.command_name} finished in {outcome.duration_seconds:.3f}s",
        )

    async def _h_test_run(request: ToolRequest) -> ToolExecutionResult:
        target = _arg(request, "target")
        if not target:
            return _failed(request, "no target test path provided")
        try:
            outcome = await resolved_runner.run(
                ("python", "-m", "pytest", target, "-q"),
                timeout_seconds=request.timeout_seconds,
                cwd=root,
            )
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        parsed = normalize_test_output(outcome.stdout, outcome.stderr, outcome.exit_code)
        if outcome.exit_code == 0 and not outcome.timed_out:
            return _result(
                request,
                ToolResultStatus.SUCCEEDED,
                stdout=outcome.stdout,
                exit_code=0,
                artifacts=parsed,
                message=f"test.run passed on {target}",
            )
        status = ToolResultStatus.TIMEOUT if outcome.timed_out else ToolResultStatus.FAILED
        return _result(
            request,
            status,
            stdout=outcome.stdout,
            stderr=outcome.stderr,
            exit_code=outcome.exit_code,
            classification=FailureClassifier.classify(
                exit_code=outcome.exit_code,
                stderr=outcome.stderr,
                timed_out=outcome.timed_out,
                status=status,
            ),
            artifacts=parsed,
            message=f"test.run failed on {target}",
        )

    async def _h_evidence_record(request: ToolRequest) -> ToolExecutionResult:
        claim_id = _arg(request, "claim_id")
        if not claim_id:
            claims = request.arguments.get("claim_ids")
            if isinstance(claims, (list, tuple)):
                claim_id = str(claims[0])
        if not claim_id:
            return _failed(request, "no claim_id provided")
        evidence = request.arguments.get("evidence", {})
        path = f"evidence/{claim_id}.json"
        try:
            import json

            resolved = resolved_toolkit.write(
                path,
                json.dumps({"claim_id": claim_id, "evidence": evidence}, sort_keys=True),
                reason=request.action_id,
            )
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        return _ok(request, stdout=f"recorded evidence {claim_id} at {resolved}")

    async def _h_evidence_read(request: ToolRequest) -> ToolExecutionResult:
        claim_id = _arg(request, "claim_id")
        if not claim_id:
            return _failed(request, "no claim_id provided")
        try:
            content = resolved_toolkit.read(f"evidence/{claim_id}.json")
        except Exception as exc:
            return _failed(request, f"{type(exc).__name__}: {exc}")
        return _ok(request, stdout=content)

    def _sandbox_handler(
        operation: str,
    ) -> Callable[[ToolRequest], Awaitable[ToolExecutionResult]]:
        async def handler(request: ToolRequest) -> ToolExecutionResult:
            sandbox_id = request.sandbox_id or _arg(request, "sandbox_id")
            if operation == "create":
                outcome = await resolved_sandbox.create(
                    request_id=request.request_id, image=_arg(request, "image", "python:3.11-slim")
                )
            elif operation == "execute":
                if not sandbox_id:
                    return _failed(request, "no sandbox_id provided")
                command = _arg(request, "command", "true")
                outcome = await resolved_sandbox.execute(
                    sandbox_id=sandbox_id,
                    command=tuple(command.split(" ")),
                    timeout_seconds=request.timeout_seconds,
                )
            elif operation == "checkpoint":
                if not sandbox_id:
                    return _failed(request, "no sandbox_id provided")
                outcome = await resolved_sandbox.checkpoint(
                    sandbox_id=sandbox_id, label=_arg(request, "label", "commit")
                )
            elif operation == "rollback":
                if not sandbox_id:
                    return _failed(request, "no sandbox_id provided")
                outcome = await resolved_sandbox.rollback(
                    sandbox_id=sandbox_id, checkpoint_ref=_arg(request, "checkpoint_ref")
                )
            elif operation == "destroy":
                if not sandbox_id:
                    return _failed(request, "no sandbox_id provided")
                outcome = await resolved_sandbox.destroy(sandbox_id=sandbox_id)
            else:
                return _failed(request, f"unknown sandbox operation {operation!r}")
            return _sandbox_result(request, outcome)

        return handler

    specs: list[ToolSpec] = [
        ToolSpec(
            name="repository.inspect",
            kind=ToolKind.REPOSITORY,
            description="List files under the approved repository root.",
            capability="*",
            risk="low",
            mutates=False,
            handler=_h_repository_inspect,
        ),
        ToolSpec(
            name="file.read",
            kind=ToolKind.FILE,
            description="Read a file inside the approved root.",
            capability="*",
            risk="low",
            mutates=False,
            handler=_h_file_read,
        ),
        ToolSpec(
            name="file.write",
            kind=ToolKind.FILE,
            description="Write a file inside the approved root (attributable).",
            capability="CODING",
            risk="low",
            mutates=True,
            handler=_h_file_write,
        ),
        ToolSpec(
            name="file.create",
            kind=ToolKind.FILE,
            description="Create a new file (refuses existing paths).",
            capability="CODING",
            risk="low",
            mutates=True,
            handler=_h_file_create,
        ),
        ToolSpec(
            name="file.delete",
            kind=ToolKind.FILE,
            description="Delete a file inside the approved root (attributable).",
            capability="CODING",
            risk="high",
            mutates=True,
            requires_approval=True,
            handler=_h_file_delete,
        ),
        ToolSpec(
            name="command.run",
            kind=ToolKind.COMMAND,
            description="Run a bounded, allowlist-environment command in the repo.",
            capability="CODING",
            risk="high",
            timeout_seconds=30.0,
            requires_sandbox=False,
            mutates=True,
            handler=_h_command_run,
        ),
        ToolSpec(
            name="test.run",
            kind=ToolKind.TEST,
            description="Run a pytest target and record the parsed outcome.",
            capability="VERIFICATION",
            risk="low",
            timeout_seconds=120.0,
            requires_sandbox=False,
            mutates=False,
            handler=_h_test_run,
        ),
        ToolSpec(
            name="evidence.record",
            kind=ToolKind.VERIFICATION,
            description="Persist structured evidence JSON bound to a claim.",
            capability="EVIDENCE",
            risk="low",
            mutates=True,
            handler=_h_evidence_record,
        ),
        ToolSpec(
            name="evidence.read",
            kind=ToolKind.VERIFICATION,
            description="Read persisted structured evidence for a claim.",
            capability="EVIDENCE",
            risk="low",
            mutates=False,
            handler=_h_evidence_read,
        ),
        ToolSpec(
            name="sandbox.create",
            kind=ToolKind.SANDBOX,
            description="Provision a sandbox (UNAVAILABLE when no provider is bound).",
            capability="CODING",
            risk="medium",
            requires_sandbox=False,
            mutates=False,
            handler=_sandbox_handler("create"),
        ),
        ToolSpec(
            name="sandbox.execute",
            kind=ToolKind.SANDBOX,
            description="Execute a command inside a sandbox (UNAVAILABLE without provider).",
            capability="CODING",
            risk="high",
            requires_sandbox=False,
            mutates=True,
            handler=_sandbox_handler("execute"),
        ),
        ToolSpec(
            name="sandbox.checkpoint",
            kind=ToolKind.SANDBOX,
            description="Checkpoint a sandbox state.",
            capability="CODING",
            risk="medium",
            requires_sandbox=False,
            mutates=True,
            handler=_sandbox_handler("checkpoint"),
        ),
        ToolSpec(
            name="sandbox.rollback",
            kind=ToolKind.SANDBOX,
            description="Roll a sandbox back to a checkpoint.",
            capability="CODING",
            risk="medium",
            requires_sandbox=False,
            mutates=True,
            handler=_sandbox_handler("rollback"),
        ),
        ToolSpec(
            name="sandbox.destroy",
            kind=ToolKind.SANDBOX,
            description="Terminate and destroy a sandbox.",
            capability="CODING",
            risk="medium",
            requires_sandbox=False,
            mutates=True,
            handler=_sandbox_handler("destroy"),
        ),
    ]
    for spec in specs:
        registry.register(spec)
    return registry


def assemble_control_plane(
    *,
    registry: ToolRegistry | None = None,
    repo_root: Path | None = None,
    environment: str = "development",
    human: ApprovalGate | None = None,
    engine: PolicyEngine | None = None,
    audit: AuditTrail | None = None,
) -> ControlPlane:
    """Wire a :class:`ControlPlane` over the default registry.

    ``repo_root`` defaults to the current working directory. Pass a
    :class:`~smorx_tools.human.HumanControlPlane` as ``human`` to enable
    the human-approval path for high-risk tools.
    """
    root = repo_root.resolve() if repo_root is not None else Path.cwd().resolve()
    resolved_registry = (
        registry if registry is not None else assemble_default_registry(repo_root=root)
    )
    return ControlPlane(
        registry=resolved_registry,
        engine=engine if engine is not None else PolicyEngine(),
        audit=audit if audit is not None else AuditTrail(),
        human=human if human is not None else None,
        environment=environment,
    )

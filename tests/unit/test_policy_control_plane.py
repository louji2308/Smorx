"""Unit tests for Phase 4 policy/audit/control-plane implementation.

Covers the deterministic authorization resolution order, the risk-based
default policy (with production promotion), explicit rule override, human
review gating, real tool execution, out-of-band execution outcomes
(timeout, missing handler, unavailable sandbox, handler exception), the
append-only audit trail, the native ``execute_request`` path, and the
``smorx_runtime.toolgate.CapabilityGateway`` structural contract.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from smorx_runtime.agents import AgentAssignment, AgentContext
from smorx_runtime.capabilities import SpecialistCapability
from smorx_runtime.toolgate import CapabilityGateway, ToolDecision, ToolExecutionError
from smorx_tools.audit import AuditDecision, AuditTrail
from smorx_tools.control import ControlPlane
from smorx_tools.policies import (
    DEFAULT_RISK_POLICY,
    PolicyDecision,
    PolicyEngine,
    PolicyRule,
    ResourceKind,
    RiskLevel,
)
from smorx_tools.tool import (
    ToolExecutionResult,
    ToolKind,
    ToolRegistry,
    ToolRequest,
    ToolResultStatus,
    ToolSpec,
)

# ---------------------------------------------------------------------- #
# Fixtures / helpers
# ---------------------------------------------------------------------- #


async def _succeed(request: ToolRequest) -> ToolExecutionResult:
    return ToolExecutionResult(
        invocation_id=request.request_id,
        tool_name=request.tool_name,
        request_id=request.request_id,
        status=ToolResultStatus.SUCCEEDED,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_seconds=0.0,
        exit_code=0,
        stdout="ok",
        artifacts={"request_id": request.request_id},
    )


async def _slow(request: ToolRequest) -> ToolExecutionResult:
    del request
    await asyncio.sleep(100)
    raise AssertionError("unreachable")


async def _explode(request: ToolRequest) -> ToolExecutionResult:
    del request
    raise ValueError("boom")


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    specs = [
        ToolSpec(
            name="file.write",
            kind=ToolKind.FILE,
            description="write a path",
            capability="CODING",
            risk="low",
            handler=_succeed,
        ),
        ToolSpec(
            name="command.run",
            kind=ToolKind.COMMAND,
            description="run a command",
            capability="*",
            risk="high",
            handler=_succeed,
        ),
        ToolSpec(
            name="command.shell",
            kind=ToolKind.COMMAND,
            description="shell command",
            capability="*",
            risk="critical",
            handler=_succeed,
        ),
        ToolSpec(
            name="command.medium",
            kind=ToolKind.COMMAND,
            description="medium risk command",
            capability="*",
            risk="medium",
            handler=_succeed,
        ),
        ToolSpec(
            name="command.slow",
            kind=ToolKind.COMMAND,
            description="slow command",
            capability="*",
            risk="low",
            handler=_slow,
        ),
        ToolSpec(
            name="evidence.read",
            kind=ToolKind.FILE,
            description="read evidence",
            capability="*",
            risk="low",
            handler=_succeed,
        ),
        ToolSpec(
            name="evidence.capture",
            kind=ToolKind.FILE,
            description="capture evidence",
            capability="*",
            risk="low",
            handler=_succeed,
        ),
        ToolSpec(
            name="evidence.broken",
            kind=ToolKind.FILE,
            description="no handler registered",
            capability="*",
            risk="low",
            handler=None,
        ),
        ToolSpec(
            name="evidence.explode",
            kind=ToolKind.FILE,
            description="handler always raises",
            capability="*",
            risk="low",
            handler=_explode,
        ),
        ToolSpec(
            name="sandbox.execute",
            kind=ToolKind.SANDBOX,
            description="execute inside sandbox",
            capability="*",
            risk="low",
            requires_sandbox=True,
            handler=_succeed,
        ),
        ToolSpec(
            name="certificate.read",
            kind=ToolKind.VERIFICATION,
            description="read a certificate",
            capability="CERTIFICATION",
            risk="low",
            handler=_succeed,
        ),
    ]
    for spec in specs:
        registry.register(spec)
    return registry


def make_assignment(
    *,
    allowed_tools: tuple[str, ...] = (
        "command.",
        "file.",
        "evidence.",
        "sandbox.execute",
    ),
) -> AgentAssignment:
    context = AgentContext(
        run_id="run-1",
        phase="8",
        task_id="task-1",
        correlation_id="corr-1",
    )
    return AgentAssignment(
        id="a1",
        task_id="task-1",
        wave_id="w1",
        agent_id="agent-C",
        objective="do the work",
        capability=SpecialistCapability.CODING,
        context=context,
        inputs={},
        constraints=(),
        allowed_tools=allowed_tools,
        expected_artifact="artifact",
        timeout_seconds=10.0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@dataclass
class _Human:
    paused: bool = False
    executable: bool = True
    approval_status: str = "APPROVED"

    def is_paused(self) -> bool:
        return self.paused

    def can_execute(self) -> bool:
        return self.executable

    def approval_for(self, action_id: str, tool_name: str) -> object | None:
        del tool_name
        if self.approval_status is None:
            return None
        return SimpleNamespace(status=self.approval_status, action_id=action_id)


def make_plane(
    *, environment: str = "development", human: _Human | None = None
) -> ControlPlane:
    return ControlPlane(
        registry=make_registry(),
        engine=PolicyEngine(),
        audit=AuditTrail(),
        human=human,
        environment=environment,
    )


def run(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


# ---------------------------------------------------------------------- #
# Policy engine: risk defaults, promotion, explicit override
# ---------------------------------------------------------------------- #


def test_default_risk_policy_maps_risk_levels() -> None:
    assert DEFAULT_RISK_POLICY[RiskLevel.LOW] is PolicyDecision.ALLOW
    assert DEFAULT_RISK_POLICY[RiskLevel.MEDIUM] is PolicyDecision.ALLOW
    assert DEFAULT_RISK_POLICY[RiskLevel.HIGH] is PolicyDecision.REQUIRE_REVIEW
    assert DEFAULT_RISK_POLICY[RiskLevel.CRITICAL] is PolicyDecision.BLOCK


def test_low_risk_write_succeeds_in_production() -> None:
    plane = make_plane(environment="production")
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="file.write",
            arguments={"path": "demo.txt"},
            action_id="act-write",
        )
    )
    assert outcome.allowed is True
    assert outcome.executed is True
    assert outcome.decision is ToolDecision.ALLOW
    assert outcome.classification == ""
    assert outcome.audit_ref
    trail = plane.audit_trail()
    assert {r.decision for r in trail.records()} >= {
        AuditDecision.ALLOWED,
        AuditDecision.EXECUTED,
    }


def test_production_promotes_default_allowed_medium_to_review() -> None:
    plane = make_plane(environment="production")
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.medium",
            arguments={"command": "upload"},
            action_id="act-medium",
        )
    )
    assert outcome.allowed is False
    assert outcome.executed is False
    assert outcome.decision is ToolDecision.REQUIRE_REVIEW
    assert outcome.reviewed is True

    dev_plane = make_plane(environment="development")
    dev_outcome = run(
        dev_plane.execute(
            assignment=make_assignment(),
            tool_name="command.medium",
            arguments={"command": "upload"},
            action_id="act-medium-dev",
        )
    )
    assert dev_outcome.decision is ToolDecision.ALLOW
    assert dev_outcome.executed is True


def test_explicit_allow_rule_overrides_default_policy() -> None:
    plural = PolicyEngine(
        rules=(
            PolicyRule(
                id="allow-internal-shell",
                decision=PolicyDecision.ALLOW,
                resource=ResourceKind.COMMAND,
                tool_name="command.shell",
                reason="internal-only exception",
            ),
        )
    )
    plane = ControlPlane(
        registry=make_registry(),
        engine=plural,
        audit=AuditTrail(),
        environment="development",
    )
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.shell",
            arguments={"command": "ls"},
            action_id="act-shell",
        )
    )
    assert outcome.decision is ToolDecision.ALLOW
    assert outcome.executed is True

    blocked_plane = make_plane()
    blocked = run(
        blocked_plane.execute(
            assignment=make_assignment(),
            tool_name="command.shell",
            arguments={"command": "ls"},
            action_id="act-shell-2",
        )
    )
    assert blocked.decision is ToolDecision.BLOCK
    assert blocked.allowed is False


def test_critical_tool_blocked_by_default_policy() -> None:
    plane = make_plane()
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.shell",
            arguments={"command": "rm -rf /"},
            action_id="act-shell-crit",
        )
    )
    assert outcome.decision is ToolDecision.BLOCK
    assert outcome.allowed is False
    assert outcome.executed is False
    assert outcome.classification == "safety/policy block"
    audit_record = plane.audit_trail().records()[-1]
    assert audit_record.decision is AuditDecision.BLOCKED
    assert "blocked by policy" in audit_record.reasons


# ---------------------------------------------------------------------- #
# Authorization resolution order
# ---------------------------------------------------------------------- #


def test_high_risk_command_requires_review_without_human() -> None:
    plane = make_plane()
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.run",
            arguments={"command": "pytest"},
            action_id="act-run",
        )
    )
    assert outcome.decision is ToolDecision.REQUIRE_REVIEW
    assert outcome.allowed is False
    assert outcome.executed is False
    assert outcome.reviewed is True
    assert plane.audit_trail().records()[-1].decision is AuditDecision.REVIEW


def test_human_approval_allows_high_risk_tool() -> None:
    plane = make_plane(human=_Human(approval_status="APPROVED"))
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.run",
            arguments={"command": "pytest"},
            action_id="act-run-approved",
        )
    )
    assert outcome.decision is ToolDecision.ALLOW
    assert outcome.executed is True
    allowed_records = [
        r
        for r in plane.audit_trail().by_tool("command.run")
        if r.decision is AuditDecision.ALLOWED
    ]
    assert allowed_records and "human approved" in allowed_records[0].reasons


def test_paused_human_defers_to_review_even_with_approval() -> None:
    plane = make_plane(human=_Human(paused=True, approval_status="APPROVED"))
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.run",
            arguments={"command": "pytest"},
            action_id="act-run-paused",
        )
    )
    assert outcome.decision is ToolDecision.REQUIRE_REVIEW
    assert outcome.executed is False


def test_unknown_tool_denied() -> None:
    plane = make_plane()
    authorization = run(
        plane.authorize(
            assignment=make_assignment(),
            tool_name="nope.does_not_exist",
            arguments={},
            action_id="act-unknown",
        )
    )
    assert authorization.decision is ToolDecision.DENY
    assert "unknown tool" in authorization.reasons
    assert plane.audit_trail().records()[-1].decision is AuditDecision.DENIED


def test_capability_mismatch_denied() -> None:
    plane = make_plane()
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="certificate.read",
            arguments={},
            action_id="act-cert",
        )
    )
    assert outcome.decision is ToolDecision.DENY
    assert "capability mismatch" in outcome.result["reason"]  # type: ignore[operator]


def test_tool_not_allowed_for_assignment_denied() -> None:
    plane = make_plane()
    assignment = make_assignment(allowed_tools=("file.",))
    outcome = run(
        plane.execute(
            assignment=assignment,
            tool_name="evidence.capture",
            arguments={},
            action_id="act-not-allowed",
        )
    )
    assert outcome.decision is ToolDecision.DENY
    assert "not allowed for assignment" in outcome.result["reason"]  # type: ignore[operator]


def test_duplicate_execution_denied() -> None:
    plane = make_plane()
    first = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="file.write",
            arguments={"path": "a.txt"},
            action_id="act-dup",
        )
    )
    assert first.executed is True
    second = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="file.write",
            arguments={"path": "a.txt"},
            action_id="act-dup",
        )
    )
    assert second.decision is ToolDecision.DENY
    assert "duplicate invocation" in second.result["reason"]  # type: ignore[operator]
    assert second.executed is False


# ---------------------------------------------------------------------- #
# Execution outcomes
# ---------------------------------------------------------------------- #


def test_missing_handler_fails_with_tool_failure() -> None:
    plane = make_plane()
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="evidence.broken",
            arguments={},
            action_id="act-broken",
        )
    )
    assert outcome.allowed is True
    assert outcome.executed is True
    assert outcome.classification == "tool failure"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.FAILED


def test_requires_sandbox_without_sandbox_is_unavailable() -> None:
    plane = make_plane()
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="sandbox.execute",
            arguments={},
            action_id="act-sandbox",
        )
    )
    assert outcome.allowed is True
    assert outcome.executed is True
    assert outcome.classification == "environment/dependency failure"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.CANCELLED


def test_timeout_classified_and_audited() -> None:
    plane = make_plane()
    outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.slow",
            arguments={"command": "sleep"},
            action_id="act-slow",
            timeout_seconds=0.1,
        )
    )
    assert outcome.allowed is True
    assert outcome.executed is True
    assert outcome.classification == "timeout"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.TIMEOUT


def test_handler_exception_raises_and_audits_failure() -> None:
    plane = make_plane()
    with pytest.raises(ToolExecutionError) as excinfo:
        run(
            plane.execute(
                assignment=make_assignment(),
                tool_name="evidence.explode",
                arguments={},
                action_id="act-explode",
            )
        )
    assert "boom" in str(excinfo.value)
    assert plane.audit_trail().records()[-1].decision is AuditDecision.FAILED


# ---------------------------------------------------------------------- #
# Audit trail
# ---------------------------------------------------------------------- #


def test_audit_trail_queries_and_summary() -> None:
    plane = make_plane()
    file_outcome = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="file.write",
            arguments={"path": "x"},
            action_id="act-a",
        )
    )
    run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="certificate.read",
            arguments={},
            action_id="act-a",
        )
    )
    reviewed = run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="command.run",
            arguments={"command": "pytest"},
            action_id="act-a",
        )
    )
    trail = plane.audit_trail()
    assert trail.has_invocation(str(file_outcome.invocation_id))
    assert len(trail.by_tool("file.write")) == 2
    assert trail.by_agent("agent-C")
    assert trail.has_action("act-a", "command.run")
    summary = trail.summary()
    assert summary["total"] == 4
    assert summary["decisions"] == {
        "ALLOWED": 1,
        "DENIED": 1,
        "EXECUTED": 1,
        "REVIEW": 1,
    }
    assert summary["tools"]["file.write"] == 2
    assert reviewed.invocation_id


# ---------------------------------------------------------------------- #
# Native execute_request path
# ---------------------------------------------------------------------- #


def test_execute_request_native_allow_path() -> None:
    plane = make_plane(environment="production")
    request = ToolRequest(
        request_id="req-1",
        action_id="act-native",
        agent_id="agent-C",
        task_id="task-1",
        tool_name="file.write",
        arguments={"path": "native.txt"},
        assignment_capabilities=("CODING",),
        allowed_tools=("file.",),
        phase="8",
        environment="production",
        timeout_seconds=5.0,
    )
    result = run(plane.execute_request(request))
    assert result.status is ToolResultStatus.SUCCEEDED
    assert result.tool_name == "file.write"
    assert result.request_id == "req-1"
    assert result.artifacts["request_id"] == "req-1"
    assert len(plane.audit_trail().by_tool("file.write")) == 2


def test_execute_request_native_deny_path() -> None:
    plane = make_plane()
    request = ToolRequest(
        request_id="req-2",
        action_id="act-native-deny",
        agent_id="agent-C",
        task_id="task-1",
        tool_name="sandbox.execute",
        arguments={},
        assignment_capabilities=("CODING",),
        allowed_tools=("file.",),
        phase="8",
        environment="development",
        timeout_seconds=5.0,
    )
    result = run(plane.execute_request(request))
    assert result.status is ToolResultStatus.DENIED
    assert result.error_classification == "permission failure"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.DENIED


# ---------------------------------------------------------------------- #
# Structural contract
# ---------------------------------------------------------------------- #


def test_control_plane_satisfies_capability_gateway() -> None:
    plane = make_plane()
    assert isinstance(plane, CapabilityGateway)
    authorization = run(
        plane.authorize(
            assignment=make_assignment(),
            tool_name="file.write",
            arguments={"path": "g.txt"},
            action_id="act-gateway",
        )
    )
    assert authorization.decision is ToolDecision.ALLOW
    assert authorization.risk_level == "low"

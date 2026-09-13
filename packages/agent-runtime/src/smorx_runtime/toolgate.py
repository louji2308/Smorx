"""Tool-authorization gateway for the agent runtime.

The orchestrator consumes :class:`CapabilityGateway` to authorize and execute
tool calls on behalf of sub-agents.  Phase 3 ships :class:`MemoryGateway`, a
deterministic enforcement double: an assignment may only invoke tools listed in
``assignment.allowed_tools`` (see ``assignment_allows_tool``) and structured
execution results are produced without touching the host.  Phase 4 replaces the
double with the real policy + audit gateway; the protocol contracted here is
the stable seam the orchestrator is built against.

Every ``execute`` returns a :class:`ToolOutcome` with structured, machine-
readable results so later phases (and independent verification) can reason
about what actually happened instead of trusting a model assertion.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import uuid4

from smorx_runtime.agents import AgentAssignment, assignment_allows_tool


class ToolDecision(StrEnum):
    """Policy disposition for a single tool invocation."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_REVIEW = "REQUIRE_REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ToolAuthorization:
    """The gateway's disposition for one tool invocation.

    ``ALLOW`` is the only decision that permits execution.  ``DENY`` and
    ``BLOCK`` forbid it; ``REQUIRE_REVIEW`` defers it to a human/policy review.
    """

    decision: ToolDecision
    reasons: tuple[str, ...] = ()
    risk_level: str = "low"


@dataclass(frozen=True)
class ToolOutcome:
    """Machine-readable result of one tool invocation attempt.

    ``allowed`` is ``True`` only when the decision was ``ALLOW``.  ``executed``
    records whether the tool actually ran; an authorized call that failed for
    execution reasons is ``allowed=True, executed=True`` with a non-empty
    ``classification``.
    """

    invocation_id: str
    allowed: bool
    decision: ToolDecision
    tool_name: str
    result: Mapping[str, object]
    classification: str = ""
    reviewed: bool = False
    audit_ref: str = ""
    executed: bool = False


@runtime_checkable
class CapabilityGateway(Protocol):
    """Contract the orchestrator consumes for authorized tool execution."""

    async def authorize(
        self,
        *,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
    ) -> ToolAuthorization: ...

    async def execute(
        self,
        *,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
        timeout_seconds: float | None = None,
    ) -> ToolOutcome: ...


class UnauthorizedToolError(Exception):
    """Raised when tool execution is attempted without an ALLOW decision."""


class ToolExecutionError(Exception):
    """Raised when an authorized tool call fails during real execution."""


class MemoryGateway:
    """Phase-3 enforcement double for :class:`CapabilityGateway`.

    An assignment may only invoke tools allowed by its capability contract
    (``assignment_allowed_tool``).  Allowed tools produce a deterministic,
    structured success result; disallowed tools are denied without executing.
    Every attempt is recorded for attribution so the orchestrator can prove
    what was invoked and with what authority.
    """

    def __init__(self) -> None:
        self._invocations: list[dict[str, object]] = []

    async def authorize(
        self,
        *,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
    ) -> ToolAuthorization:
        if assignment_allows_tool(assignment, tool_name):
            return ToolAuthorization(
                decision=ToolDecision.ALLOW,
                reasons=(f"tool {tool_name!r} allowed for capability {assignment.capability!r}",),
                risk_level="low",
            )
        return ToolAuthorization(
            decision=ToolDecision.DENY,
            reasons=(f"tool {tool_name!r} not in allowed_tools for the assignment",),
            risk_level="low",
        )

    async def execute(
        self,
        *,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
        timeout_seconds: float | None = None,
    ) -> ToolOutcome:
        del timeout_seconds
        authorization = await self.authorize(
            assignment=assignment,
            tool_name=tool_name,
            arguments=arguments,
            action_id=action_id,
        )
        invocation_id = uuid4().hex
        if authorization.decision is not ToolDecision.ALLOW:
            self._invocations.append(
                {
                    "action_id": action_id,
                    "invocation_id": invocation_id,
                    "tool_name": tool_name,
                    "allowed": False,
                    "executed": False,
                    "decision": authorization.decision.value,
                    "reason": authorization.reasons[0] if authorization.reasons else "denied",
                }
            )
            return ToolOutcome(
                invocation_id=invocation_id,
                allowed=False,
                decision=authorization.decision,
                tool_name=tool_name,
                result={"reason": "tool not allowed"},
                executed=False,
            )
        self._invocations.append(
            {
                "action_id": action_id,
                "invocation_id": invocation_id,
                "tool_name": tool_name,
                "allowed": True,
                "executed": True,
                "decision": authorization.decision.value,
                "argument_keys": sorted(arguments),
            }
        )
        return ToolOutcome(
            invocation_id=invocation_id,
            allowed=True,
            decision=ToolDecision.ALLOW,
            tool_name=tool_name,
            result={
                "tool_name": tool_name,
                "status": "SUCCEEDED",
                "executed_at": datetime.now(UTC).isoformat(),
                "arguments_summary": sorted(arguments),
            },
            executed=True,
        )

    def invocations(self) -> tuple[dict[str, object], ...]:
        """Audit trail of every authorization attempt (attribution)."""
        return tuple(self._invocations)

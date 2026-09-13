"""Policy-controlled tool gateway implementing ``smorx_runtime.toolgate``.

Phase 4 ``smorx_tools.control`` binds the tool registry, the policy engine,
and the audit trail into :class:`ControlPlane`, a real enforcement gateway
for ``smorx_runtime.toolgate.CapabilityGateway`` (duck-typed; the protocol is
only used for a structural self-check, never at the seam).

Authorization resolution order (deterministic, evaluated in this order):

1. Unknown tool -> ``DENY`` reason ``"unknown tool"``, audit ``DENIED``.
2. Duplicate execution guard: an earlier record for the same
   ``(action_id, tool_name)`` with decision ``EXECUTED`` -> ``DENY`` reason
   ``"duplicate invocation"``, audit ``DENIED``.
3. Capability check: ``tool.capability != "*"`` and the tool capability is not
   among the assignment(/)request's capabilities -> ``DENY`` reason
   ``"capability mismatch"``, audit ``DENIED``.
4. Allowed-tools check (exact name or dotted-prefix match, the same semantics
   as ``smorx_runtime.agents.assignment_allows_tool``): present tools outside
   the allowed set -> ``DENY`` reason ``"not allowed for assignment"``.
5. Policy evaluation via :class:`PolicyEngine`; the resource kind is derived
   from the tool kind (``FILE -> PATH``, ``COMMAND -> COMMAND``,
   ``SANDBOX -> SANDBOX``, ``REPOSITORY -> FILE``, else ``TOOL``):
   - ``BLOCK`` -> authorization ``BLOCK``, audit ``BLOCKED``.
   - ``DENY`` -> authorization ``DENY``, audit ``DENIED``.
   - ``REQUIRE_REVIEW`` -> consult the human gate:
       * no human channel -> authorization ``REQUIRE_REVIEW``, audit
         ``REVIEW`` (``tool.requires_approval`` does not change this outcome:
         without a human channel the only honest disposition is review);
       * human paused or not executable -> ``REQUIRE_REVIEW``, audit
         ``REVIEW`` (paused blocks execution but is recorded, not BLOCKED);
       * human returns an approval object with ``status == "APPROVED"`` ->
         ``ALLOW``, audit ``ALLOWED`` with reason ``"human approved"``;
       * otherwise -> ``REQUIRE_REVIEW``, audit ``REVIEW``.
6. ``ALLOW`` -> authorization ``ALLOW``, audit ``ALLOWED``.

Execution mapping (returned / pre-built ``ToolExecutionResult`` statuses):

* ``SUCCEEDED`` -> ``ToolOutcome(allowed=True, executed=True, decision=ALLOW,
  result=artifacts or {stdout, stderr, exit_code}, classification="")``,
  audit ``EXECUTED``.
* ``FAILED`` -> audit ``FAILED``, classification ``error_classification`` or
  ``"tool failure"``.
* ``TIMEOUT`` -> audit ``TIMEOUT``, classification ``"timeout"``.
* ``DENIED``/``BLOCKED`` -> ``allowed=False, executed=False``.
* ``UNAVAILABLE`` -> classification ``"environment/dependency failure"``,
  audit ``CANCELLED`` (execution never started).
* ``ERROR`` (no handler registered) -> classification ``"tool failure"``,
  audit ``FAILED``.

Contract-discipline notes:

* ``execute`` / ``execute_request`` never raise for a policy denial; denials
  always return ``allowed=False`` outcomes / ``DENIED``-style results.
* A handler exception that escapes ``asyncio.wait_for`` is first audited as
  ``FAILED`` (``tool failure``) and then re-raised as
  :class:`ToolExecutionError`; it never silently becomes "success".
* Every invocation records an audit record; ``audit_ref`` is always the
  relevant record's ``audit_id``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from smorx_runtime.agents import AgentAssignment, assignment_allows_tool
from smorx_runtime.toolgate import (
    CapabilityGateway,
    ToolAuthorization,
    ToolDecision,
    ToolExecutionError,
    ToolOutcome,
    UnauthorizedToolError,
)

from smorx_tools.audit import AuditDecision, AuditRecord, AuditTrail
from smorx_tools.policies import (
    PolicyContext,
    PolicyDecision,
    PolicyEngine,
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

__all__ = [
    "ApprovalGate",
    "ControlPlane",
    "ToolAuthorization",
    "ToolDecision",
    "ToolExecutionError",
    "ToolOutcome",
    "UnauthorizedToolError",
]


class ApprovalGate(Protocol):
    """Structural human-control surface consumed by :class:`ControlPlane`.

    ``smorx_tools.human.HumanControlPlane`` satisfies this protocol
    structurally; ``ControlPlane`` deliberately does not hard-import it.
    """

    def is_paused(self) -> bool: ...

    def can_execute(self) -> bool: ...

    def approval_for(self, action_id: str, tool_name: str) -> object | None: ...


@dataclass(frozen=True)
class _AuthView:
    """Normalized inputs for one authorization attempt (assignment or request)."""

    request_id: str
    action_id: str
    agent_id: str
    task_id: str
    tool_name: str
    arguments: Mapping[str, object]
    capabilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    environment: str


class ControlPlane:
    """Real policy-controlled tool gateway (see module docstring for rules)."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        engine: PolicyEngine,
        audit: AuditTrail,
        human: ApprovalGate | None = None,
        environment: str = "development",
    ) -> None:
        self._registry: ToolRegistry = registry
        self._engine: PolicyEngine = engine
        self._audit: AuditTrail = audit
        self._human: ApprovalGate | None = human
        self._environment: str = environment
        assert isinstance(self, CapabilityGateway), "ControlPlane must satisfy CapabilityGateway"

    # ------------------------------------------------------------------ #
    # smorx_runtime.toolgate.CapabilityGateway
    # ------------------------------------------------------------------ #

    async def authorize(
        self,
        *,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
    ) -> ToolAuthorization:
        """Resolve authorization for ``assignment``; only ``ALLOW`` permits run."""
        view = self._view_from_assignment(assignment, tool_name, arguments, action_id)
        authorization, _ = self._authorize(
            self._registry.get(tool_name), view, assignment=assignment
        )
        return authorization

    async def execute(
        self,
        *,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
        timeout_seconds: float | None = None,
    ) -> ToolOutcome:
        """Authorize and (when ALLOWed) execute ``tool_name`` for ``assignment``.

        Authorization runs once, inside this call; a denial never raises, it
        returns an ``allowed=False`` :class:`ToolOutcome` with the denial audit
        record's ``audit_id`` as ``audit_ref``.
        """
        view = self._view_from_assignment(assignment, tool_name, arguments, action_id)
        spec = self._registry.get(tool_name)
        authorization, auth_record = self._authorize(spec, view, assignment=assignment)
        if authorization.decision is not ToolDecision.ALLOW:
            return self._denied_outcome(authorization, auth_record, tool_name)
        assert spec is not None
        timeout = timeout_seconds if timeout_seconds is not None else spec.timeout_seconds
        request = self._build_request(assignment, spec, view, timeout)
        result, record = await self._execute_authorized(request, spec)
        return replace(self._outcome_from_result(result), audit_ref=record.audit_id)

    async def authorize_and_execute(
        self,
        *,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
        timeout_seconds: float | None = None,
    ) -> ToolOutcome:
        """Combined convenience: one authorization, then execution when ALLOWed."""
        return await self.execute(
            assignment=assignment,
            tool_name=tool_name,
            arguments=arguments,
            action_id=action_id,
            timeout_seconds=timeout_seconds,
        )

    # ------------------------------------------------------------------ #
    # Native control-plane API
    # ------------------------------------------------------------------ #

    async def execute_request(self, request: ToolRequest) -> ToolExecutionResult:
        """Authorize and execute a prebuilt :class:`ToolRequest` (native path).

        The request itself carries the capabilities, allowed tools, action id,
        sandbox id, and environment used for authorization (no synthetic
        assignment is fabricated). Returns a :class:`ToolExecutionResult`
        directly; a denial produces a ``DENIED``/``BLOCKED``/``PENDING_REVIEW``
        result (never an exception).
        """
        spec = self._registry.get(request.tool_name)
        view = _AuthView(
            request_id=request.request_id,
            action_id=request.action_id,
            agent_id=request.agent_id,
            task_id=request.task_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
            capabilities=tuple(request.assignment_capabilities),
            allowed_tools=tuple(request.allowed_tools),
            environment=request.environment,
        )
        authorization, auth_record = self._authorize(spec, view, assignment=None)
        if authorization.decision is not ToolDecision.ALLOW:
            return self._denied_result(request, authorization, auth_record)
        assert spec is not None
        result, _ = await self._execute_authorized(request, spec)
        return result

    def tool_spec(self, name: str) -> ToolSpec | None:
        """The registered spec for ``name``, or ``None``."""
        return self._registry.get(name)

    def audit_trail(self) -> AuditTrail:
        """The append-only audit trail every decision and execution writes to."""
        return self._audit

    def tool_registry(self) -> ToolRegistry:
        """The tool registry this plane gates."""
        return self._registry

    # ------------------------------------------------------------------ #
    # Authorization resolution
    # ------------------------------------------------------------------ #

    def _view_from_assignment(
        self,
        assignment: AgentAssignment,
        tool_name: str,
        arguments: Mapping[str, object],
        action_id: str,
    ) -> _AuthView:
        return _AuthView(
            request_id=uuid4().hex,
            action_id=action_id,
            agent_id=assignment.agent_id,
            task_id=assignment.task_id,
            tool_name=tool_name,
            arguments=arguments,
            capabilities=(assignment.capability.value,),
            allowed_tools=tuple(assignment.allowed_tools),
            environment=self._environment,
        )

    def _authorize(
        self,
        spec: ToolSpec | None,
        view: _AuthView,
        *,
        assignment: AgentAssignment | None,
    ) -> tuple[ToolAuthorization, AuditRecord]:
        if spec is None:
            return self._denied("unknown tool", view, spec=None)
        previous = self._latest_for(view.action_id, view.tool_name)
        if previous is not None and previous.decision is AuditDecision.EXECUTED:
            return self._denied("duplicate invocation", view, spec=spec)
        if spec.capability != "*" and spec.capability not in view.capabilities:
            return self._denied("capability mismatch", view, spec=spec)
        if assignment is not None:
            allowed = assignment_allows_tool(assignment, view.tool_name)
        else:
            allowed = self._allowed_by(view.allowed_tools, view.tool_name)
        if not allowed:
            return self._denied("not allowed for assignment", view, spec=spec)
        decision = self._engine.evaluate(self._policy_context(spec, view))
        if decision is PolicyDecision.BLOCK:
            return self._authorized(
                spec, view, ToolDecision.BLOCK, "blocked by policy", AuditDecision.BLOCKED
            )
        if decision is PolicyDecision.DENY:
            return self._authorized(
                spec, view, ToolDecision.DENY, "denied by policy", AuditDecision.DENIED
            )
        if decision is PolicyDecision.REQUIRE_REVIEW:
            return self._resolve_review(spec, view)
        return self._authorized(
            spec, view, ToolDecision.ALLOW, "policy allows", AuditDecision.ALLOWED
        )

    def _resolve_review(
        self, spec: ToolSpec, view: _AuthView
    ) -> tuple[ToolAuthorization, AuditRecord]:
        reason = "policy requires review"
        human = self._human
        if human is None:
            return self._authorized(
                spec, view, ToolDecision.REQUIRE_REVIEW, reason, AuditDecision.REVIEW
            )
        if human.is_paused() or not human.can_execute():
            return self._authorized(
                spec, view, ToolDecision.REQUIRE_REVIEW, reason, AuditDecision.REVIEW
            )
        approval = human.approval_for(view.action_id, view.tool_name)
        approved = approval is not None and getattr(approval, "status", None) == "APPROVED"
        if approved:
            return self._authorized(
                spec, view, ToolDecision.ALLOW, "human approved", AuditDecision.ALLOWED
            )
        return self._authorized(
            spec, view, ToolDecision.REQUIRE_REVIEW, reason, AuditDecision.REVIEW
        )

    def _denied(
        self, reason: str, view: _AuthView, *, spec: ToolSpec | None
    ) -> tuple[ToolAuthorization, AuditRecord]:
        if spec is None:
            risk_level = "low"
            resource_kind = ResourceKind.TOOL.value
            resource_ref = ""
        else:
            risk_level = spec.risk
            resource_kind = self._resource_for_kind(spec.kind).value
            resource_ref = self._resource_ref(view.arguments)
        record = self._record(
            view,
            AuditDecision.DENIED,
            reasons=(reason,),
            risk_level=risk_level,
            resource_kind=resource_kind,
            resource_ref=resource_ref,
        )
        return ToolAuthorization(
            decision=ToolDecision.DENY, reasons=(reason,), risk_level=risk_level
        ), record

    def _authorized(
        self,
        spec: ToolSpec,
        view: _AuthView,
        decision: ToolDecision,
        reason: str,
        audit_decision: AuditDecision,
    ) -> tuple[ToolAuthorization, AuditRecord]:
        record = self._record(
            view,
            audit_decision,
            reasons=(reason,),
            risk_level=spec.risk,
            resource_kind=self._resource_for_kind(spec.kind).value,
            resource_ref=self._resource_ref(view.arguments),
        )
        return ToolAuthorization(decision=decision, reasons=(reason,), risk_level=spec.risk), record

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    async def _execute_authorized(
        self, request: ToolRequest, spec: ToolSpec
    ) -> tuple[ToolExecutionResult, AuditRecord]:
        if spec.requires_sandbox and not request.sandbox_id:
            result = self._raw_result(
                request,
                status=ToolResultStatus.UNAVAILABLE,
                error_classification="environment/dependency failure",
                message="requires a sandbox but no sandbox_id was provided",
            )
            return result, self._record_execution(request, spec, result)
        handler = spec.handler
        if handler is None:
            result = self._raw_result(
                request,
                status=ToolResultStatus.ERROR,
                error_classification="tool failure",
                message="no handler registered",
            )
            return result, self._record_execution(request, spec, result)
        started_at = datetime.now(UTC)
        try:
            result = await asyncio.wait_for(handler(request), timeout=request.timeout_seconds)
        except TimeoutError:
            result = self._raw_result(
                request,
                status=ToolResultStatus.TIMEOUT,
                error_classification="timeout",
                message=f"tool timed out after {request.timeout_seconds:g}s",
                started_at=started_at,
                timeout_seconds=request.timeout_seconds,
            )
            return result, self._record_execution(request, spec, result)
        except Exception as exc:
            # A handler exception escapes as ToolExecutionError, but is first
            # audited as FAILED so the failure stays attributable.
            failure = self._raw_result(
                request,
                status=ToolResultStatus.ERROR,
                error_classification="tool failure",
                message=f"{type(exc).__name__}: {exc}",
                started_at=started_at,
                timeout_seconds=request.timeout_seconds,
            )
            self._record_execution(request, spec, failure)
            raise ToolExecutionError(
                f"tool {request.tool_name!r} raised {type(exc).__name__}: {exc}"
            ) from exc
        return result, self._record_execution(request, spec, result)

    def _denied_outcome(
        self, authorization: ToolAuthorization, record: AuditRecord, tool_name: str
    ) -> ToolOutcome:
        if authorization.decision is ToolDecision.BLOCK:
            classification = "safety/policy block"
        elif authorization.decision is ToolDecision.DENY:
            classification = "permission failure"
        else:
            classification = ""
        return ToolOutcome(
            invocation_id=record.invocation_id,
            allowed=False,
            decision=authorization.decision,
            tool_name=tool_name,
            result={"reason": " ".join(authorization.reasons) or "denied by policy", "errors": []},
            classification=classification,
            reviewed=authorization.decision is ToolDecision.REQUIRE_REVIEW,
            audit_ref=record.audit_id,
            executed=False,
        )

    def _denied_result(
        self, request: ToolRequest, authorization: ToolAuthorization, record: AuditRecord
    ) -> ToolExecutionResult:
        if authorization.decision is ToolDecision.BLOCK:
            status = ToolResultStatus.BLOCKED
            classification = "safety/policy block"
        elif authorization.decision is ToolDecision.DENY:
            status = ToolResultStatus.DENIED
            classification = "permission failure"
        else:
            status = ToolResultStatus.PENDING_REVIEW
            classification = ""
        now = datetime.now(UTC)
        return ToolExecutionResult(
            invocation_id=record.invocation_id,
            tool_name=request.tool_name,
            request_id=request.request_id,
            status=status,
            started_at=now,
            finished_at=now,
            duration_seconds=0.0,
            error_classification=classification,
            timeout_seconds=request.timeout_seconds,
            sandbox_id=request.sandbox_id,
            message=" ".join(authorization.reasons),
        )

    def _outcome_from_result(self, result: ToolExecutionResult) -> ToolOutcome:
        status = result.status
        decision = ToolDecision.ALLOW
        allowed = True
        executed = True
        classification = ""
        reviewed = False
        payload: Mapping[str, object] = {}
        if status is ToolResultStatus.SUCCEEDED:
            if result.artifacts:
                payload = result.artifacts
            else:
                payload = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code if result.exit_code is not None else 0,
                }
        elif status is ToolResultStatus.FAILED:
            classification = result.error_classification or "tool failure"
            payload = {
                "status": "FAILED",
                "message": result.message,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        elif status is ToolResultStatus.TIMEOUT:
            classification = "timeout"
            payload = {
                "status": "TIMEOUT",
                "timeout_seconds": result.timeout_seconds,
                "message": result.message,
            }
        elif status is ToolResultStatus.UNAVAILABLE:
            classification = "environment/dependency failure"
            payload = {"status": "UNAVAILABLE", "message": result.message}
        elif status is ToolResultStatus.ERROR:
            classification = result.error_classification or "tool failure"
            payload = {"status": "ERROR", "message": result.message}
        elif status is ToolResultStatus.DENIED:
            allowed = False
            executed = False
            decision = ToolDecision.DENY
            payload = {"status": "DENIED", "message": result.message}
        elif status is ToolResultStatus.BLOCKED:
            allowed = False
            executed = False
            decision = ToolDecision.BLOCK
            payload = {"status": "BLOCKED", "message": result.message}
        elif status is ToolResultStatus.PENDING_REVIEW:
            allowed = False
            executed = False
            decision = ToolDecision.REQUIRE_REVIEW
            reviewed = True
            payload = {"status": "PENDING_REVIEW", "message": result.message}
        return ToolOutcome(
            invocation_id=result.invocation_id,
            allowed=allowed,
            decision=decision,
            tool_name=result.tool_name,
            result=payload,
            classification=classification,
            reviewed=reviewed,
            executed=executed,
        )

    # ------------------------------------------------------------------ #
    # Request construction
    # ------------------------------------------------------------------ #

    def _build_request(
        self,
        assignment: AgentAssignment,
        spec: ToolSpec,
        view: _AuthView,
        timeout_seconds: float,
    ) -> ToolRequest:
        sandbox_value = view.arguments.get("sandbox_id")
        return ToolRequest(
            request_id=view.request_id,
            action_id=view.action_id,
            agent_id=view.agent_id,
            task_id=view.task_id,
            tool_name=view.tool_name,
            arguments=dict(view.arguments),
            assignment_capabilities=view.capabilities,
            allowed_tools=view.allowed_tools,
            phase=assignment.context.phase,
            environment=self._environment,
            timeout_seconds=timeout_seconds,
            sandbox_id=sandbox_value if isinstance(sandbox_value, str) else "",
        )

    def _raw_result(
        self,
        request: ToolRequest,
        *,
        status: ToolResultStatus,
        error_classification: str = "",
        message: str = "",
        started_at: datetime | None = None,
        timeout_seconds: float | None = None,
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        artifacts: Mapping[str, object] | None = None,
    ) -> ToolExecutionResult:
        started = started_at if started_at is not None else datetime.now(UTC)
        finished = datetime.now(UTC)
        return ToolExecutionResult(
            invocation_id=uuid4().hex,
            tool_name=request.tool_name,
            request_id=request.request_id,
            status=status,
            started_at=started,
            finished_at=finished,
            duration_seconds=(finished - started).total_seconds(),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            artifacts=dict(artifacts) if artifacts is not None else {},
            error_classification=error_classification,
            timeout_seconds=timeout_seconds
            if timeout_seconds is not None
            else request.timeout_seconds,
            sandbox_id=request.sandbox_id,
            message=message,
        )

    # ------------------------------------------------------------------ #
    # Policy context / resource mapping
    # ------------------------------------------------------------------ #

    def _policy_context(self, spec: ToolSpec, view: _AuthView) -> PolicyContext:
        return PolicyContext(
            environment=view.environment,
            agent_id=view.agent_id,
            task_id=view.task_id,
            tool_name=view.tool_name,
            risk=RiskLevel(spec.risk),
            resource=self._resource_for_kind(spec.kind),
            resource_ref=self._resource_ref(view.arguments),
        )

    @staticmethod
    def _resource_for_kind(kind: ToolKind) -> ResourceKind:
        """Map a tool kind to the resource kind used for policy rules.

        Per the frozen Phase 4 contract: ``FILE/PATH -> PATH``,
        ``COMMAND -> COMMAND``, ``SANDBOX -> SANDBOX``,
        ``REPOSITORY -> FILE``, everything else ``TOOL``. The current
        ``ToolKind`` catalog has no ``PATH`` member, so ``FILE`` alone maps to
        ``PATH``.
        """
        if kind is ToolKind.FILE:
            return ResourceKind.PATH
        if kind is ToolKind.REPOSITORY:
            return ResourceKind.FILE
        if kind is ToolKind.COMMAND:
            return ResourceKind.COMMAND
        if kind is ToolKind.SANDBOX:
            return ResourceKind.SANDBOX
        return ResourceKind.TOOL

    @staticmethod
    def _resource_ref(arguments: Mapping[str, object]) -> str:
        """The resource reference for audit: first present key wins."""
        for key in ("resource_ref", "path", "target", "command"):
            value = arguments.get(key)
            if isinstance(value, str) and value:
                return value
        return ""

    @staticmethod
    def _allowed_by(allowed_tools: Sequence[str], tool_name: str) -> bool:
        """Exact or dotted-prefix match, mirroring ``assignment_allows_tool``."""
        for entry in allowed_tools:
            if tool_name == entry:
                return True
            if entry.endswith(".") and tool_name.startswith(entry):
                return True
        return False

    # ------------------------------------------------------------------ #
    # Audit
    # ------------------------------------------------------------------ #

    def _record(
        self,
        view: _AuthView,
        decision: AuditDecision,
        *,
        reasons: Sequence[str],
        risk_level: str,
        resource_kind: str,
        resource_ref: str,
    ) -> AuditRecord:
        record = AuditRecord(
            audit_id=uuid4().hex,
            recorded_at=datetime.now(UTC),
            invocation_id=uuid4().hex,
            request_id=view.request_id,
            action_id=view.action_id,
            agent_id=view.agent_id,
            task_id=view.task_id,
            tool_name=view.tool_name,
            decision=decision,
            reasons=tuple(reasons),
            risk_level=risk_level,
            resource_kind=resource_kind,
            resource_ref=resource_ref,
        )
        self._audit.record(record)
        return record

    def _record_execution(
        self, request: ToolRequest, spec: ToolSpec, result: ToolExecutionResult
    ) -> AuditRecord:
        record = AuditRecord(
            audit_id=uuid4().hex,
            recorded_at=datetime.now(UTC),
            invocation_id=result.invocation_id,
            request_id=request.request_id,
            action_id=request.action_id,
            agent_id=request.agent_id,
            task_id=request.task_id,
            tool_name=result.tool_name,
            decision=self._audit_decision_for(result.status),
            reasons=(f"status {result.status.value}",),
            risk_level=spec.risk,
            resource_kind=self._resource_for_kind(spec.kind).value,
            resource_ref=self._resource_ref(request.arguments),
            exit_code=result.exit_code,
            outcome_classification=result.error_classification,
            status=result.status.value,
            result_summary=(result.message or result.stdout)[:200],
        )
        self._audit.record(record)
        return record

    @staticmethod
    def _audit_decision_for(status: ToolResultStatus) -> AuditDecision:
        if status is ToolResultStatus.SUCCEEDED:
            return AuditDecision.EXECUTED
        if status is ToolResultStatus.FAILED:
            return AuditDecision.FAILED
        if status is ToolResultStatus.TIMEOUT:
            return AuditDecision.TIMEOUT
        if status is ToolResultStatus.ERROR:
            return AuditDecision.FAILED
        if status is ToolResultStatus.DENIED:
            return AuditDecision.DENIED
        if status is ToolResultStatus.BLOCKED:
            return AuditDecision.BLOCKED
        if status is ToolResultStatus.UNAVAILABLE:
            return AuditDecision.CANCELLED
        if status is ToolResultStatus.PENDING_REVIEW:
            return AuditDecision.REVIEW
        raise AssertionError(f"unhandled tool result status: {status}")

    def _latest_for(self, action_id: str, tool_name: str) -> AuditRecord | None:
        for record in reversed(self._audit.records()):
            if record.action_id == action_id and record.tool_name == tool_name:
                return record
        return None

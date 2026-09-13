"""Adversarial guardrail and enforcement tests for the agent runtime and the
policy-controlled tool layer.

Every scenario is deterministic, real (no mocks), self-contained, and asserts
the observable/behavioral outcome -- never a process-exit-code-only check. The
suite proves that the ``smorx_runtime`` orchestrator and the ``smorx_tools``
control plane reject misuse: unknown tools, capability mismatches, duplicate
invocations, timeouts, sandbox absence, policy blocks, no-progress loops, and
out-of-band bypass are all detected without masking success.

The runtime runs via ``asyncio.run`` (no pytest-asyncio dependency); each test
holds under two seconds of wall time.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import uuid4

import pytest
from smorx_runtime.agents import (
    AgentAssignment,
    AgentContext,
    AgentEvidence,
    AgentFailure,
    AgentResult,
    AgentSpec,
    validate_result,
)
from smorx_runtime.capabilities import SpecialistCapability
from smorx_runtime.graph import TaskGraph, TaskKind, TaskSpec
from smorx_runtime.orchestrator import (
    InvalidWorkflowTransition,
    OrchestrationBlocked,
    Orchestrator,
    OrchestratorConfig,
    RetryPolicy,
    WorkflowPhase,
)
from smorx_runtime.toolgate import (
    ToolDecision,
    ToolExecutionError,
    UnauthorizedToolError,
)
from smorx_runtime.waves import (
    ParallelWaveEngine,
    WaveResult,
    WaveRunRequest,
    WaveStatus,
)
from smorx_tools.assembly import assemble_control_plane, assemble_default_registry
from smorx_tools.audit import AuditDecision, AuditTrail
from smorx_tools.control import ControlPlane
from smorx_tools.execution import CommandRunner, FailureClassifier
from smorx_tools.policies import PolicyDecision, PolicyEngine, PolicyRule, ResourceKind
from smorx_tools.repo import RepositoryToolkit
from smorx_tools.tool import (
    ToolExecutionResult,
    ToolKind,
    ToolRegistry,
    ToolRequest,
    ToolResultStatus,
    ToolSpec,
)

T = TypeVar("T")

Behaviour = Callable[[AgentAssignment, object], Awaitable[AgentResult]]


def _run(awaitable: Awaitable[T]) -> T:
    return asyncio.run(awaitable)


def _now() -> datetime:
    return datetime.now(UTC)


def _before() -> datetime:
    return _now() - timedelta(seconds=1)


def make_assignment(
    *,
    task_id: str = "task-1",
    agent_id: str = "agent-C",
    capability: SpecialistCapability = SpecialistCapability.CODING,
    allowed_tools: tuple[str, ...] = (
        "file.",
        "command.run",
        "test.run",
        "sandbox.",
        "evidence.",
        "repository.inspect",
    ),
    timeout_seconds: float = 30.0,
) -> AgentAssignment:
    context = AgentContext(
        run_id=f"run-{uuid4().hex[:8]}",
        phase="8",
        task_id=task_id,
        correlation_id=f"corr-{uuid4().hex[:8]}",
    )
    return AgentAssignment(
        id=f"{task_id}-assignment-{uuid4().hex[:8]}",
        task_id=task_id,
        wave_id="w-guardrail",
        agent_id=agent_id,
        objective=f"execute {task_id}",
        capability=capability,
        context=context,
        inputs={},
        constraints=(),
        allowed_tools=allowed_tools,
        expected_artifact="",
        timeout_seconds=timeout_seconds,
        created_at=_now(),
    )


def make_request(
    tool_name: str,
    action_id: str,
    *,
    arguments: Mapping[str, object] | None = None,
    capabilities: tuple[str, ...] = ("CODING",),
    allowed: tuple[str, ...] = (),
    timeout_seconds: float = 30.0,
) -> ToolRequest:
    return ToolRequest(
        request_id=f"req-{uuid4().hex[:8]}",
        action_id=action_id,
        agent_id="agent-C",
        task_id="task-1",
        tool_name=tool_name,
        arguments=dict(arguments) if arguments is not None else {},
        assignment_capabilities=capabilities,
        allowed_tools=allowed,
        phase="8",
        environment="development",
        timeout_seconds=timeout_seconds,
    )


def _result(
    assignment: AgentAssignment,
    *,
    status: str = "SUCCEEDED",
    classification: str = "tool failure",
    summary: str = "ok",
    artifacts: Mapping[str, object] | None = None,
    claims: tuple[str, ...] = (),
    evidence: tuple[AgentEvidence, ...] | None = None,
    task_id: str | None = None,
    assignment_id: str | None = None,
) -> AgentResult:
    started_at = _before()
    finished_at = _now()
    task = task_id if task_id is not None else assignment.task_id
    ref = assignment_id if assignment_id is not None else assignment.id
    payload = dict(artifacts) if artifacts is not None else {"exit_code": 0}
    if status == "SUCCEEDED":
        success_evidence = (
            evidence
            if evidence is not None
            else (
                AgentEvidence(
                    evidence_id=f"ev:{task}:{ref}",
                    source=f"task:{task}",
                    timestamp=finished_at,
                    evidence_type="EXECUTION_RESULT",
                    claim_id=claims[0] if claims else None,
                    machine_result=payload,
                ),
            )
        )
        return AgentResult(
            assignment_id=ref,
            task_id=task,
            status="SUCCEEDED",
            started_at=started_at,
            finished_at=finished_at,
            claims=claims,
            artifacts=payload,
            evidence=success_evidence,
            failures=(),
            execution_references=(),
            confidence=1.0,
            summary=summary,
        )
    return AgentResult(
        assignment_id=ref,
        task_id=task,
        status="FAILED",
        started_at=started_at,
        finished_at=finished_at,
        claims=(),
        artifacts={},
        evidence=(),
        failures=(
            AgentFailure(
                failure_id=f"f:{task}:{ref}",
                classification=classification,
                summary=summary,
                observed_at=finished_at,
            ),
        ),
        confidence=1.0,
        summary=summary,
    )


async def _default_behaviour(
    assignment: AgentAssignment, _factory: object
) -> AgentResult:
    return _result(assignment)


class FakeExecutor:
    """Runs a task-specific behaviour under a bounded writer-side timeout."""

    def __init__(self, factory: FakeFactory, spec: AgentSpec) -> None:
        self._factory = factory
        self.spec = spec

    async def execute(self, assignment: AgentAssignment) -> AgentResult:
        self._factory.seen_assignments.append(assignment)
        self._factory.execution_order.append(assignment.task_id)
        behaviour = self._factory.behaviours.get(assignment.task_id, _default_behaviour)
        try:
            return await asyncio.wait_for(
                behaviour(assignment, self._factory), timeout=self._factory.timeout
            )
        except TimeoutError:
            return _result(
                assignment,
                status="FAILED",
                classification="timeout",
                summary="bounded execution did not finish",
            )
        except Exception as exc:  # noqa: BLE001 - scripted behaviour failures become FAILED results
            return _result(
                assignment, status="FAILED", summary=f"{type(exc).__name__}: {exc}"
            )


class FakeFactory:
    """Produces executors whose behaviour is keyed by ``task_id``."""

    def __init__(
        self,
        behaviours: Mapping[str, Behaviour] | None = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        self.behaviours = dict(behaviours or {})
        self.timeout = timeout
        self.created: list[AgentSpec] = []
        self.seen_assignments: list[AgentAssignment] = []
        self.execution_order: list[str] = []

    def create(
        self, spec: AgentSpec, *, allowed_tools: tuple[str, ...] = ()
    ) -> FakeExecutor:
        del allowed_tools
        self.created.append(spec)
        return FakeExecutor(self, spec)


def _task(
    task_id: str,
    *,
    kind: TaskKind = TaskKind.INDEPENDENT,
    depends_on: tuple[str, ...] = (),
) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        capability=SpecialistCapability.CODING,
        kind=kind,
        depends_on=depends_on,
        description=f"execute {task_id}",
    )


def _graph(*specs: TaskSpec) -> TaskGraph:
    graph = TaskGraph()
    for spec in specs:
        graph.add(spec)
    return graph


def _context() -> AgentContext:
    return AgentContext(
        run_id=f"run-{uuid4().hex[:8]}",
        phase="guardrail",
        task_id="orchestration",
        correlation_id=f"corr-{uuid4().hex[:8]}",
    )


async def _succeed(_request: ToolRequest) -> ToolExecutionResult:
    now = _now()
    return ToolExecutionResult(
        invocation_id=_request.request_id,
        tool_name=_request.tool_name,
        request_id=_request.request_id,
        status=ToolResultStatus.SUCCEEDED,
        started_at=now,
        finished_at=now,
        duration_seconds=0.0,
        exit_code=0,
        stdout="ok",
    )


async def _slow(_request: ToolRequest) -> ToolExecutionResult:
    await asyncio.sleep(5)
    raise AssertionError("unreachable after timeout")


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="file.write",
            kind=ToolKind.FILE,
            description="attributable file write",
            capability="CODING",
            risk="low",
            handler=_succeed,
        )
    )
    registry.register(
        ToolSpec(
            name="command.slow",
            kind=ToolKind.COMMAND,
            description="slow command",
            capability="*",
            risk="low",
            handler=_slow,
        )
    )
    return registry


class _Soon:
    """Executor that returns fast, evidence-bearing results."""

    async def execute(self, assignment: AgentAssignment) -> AgentResult:
        return _result(assignment)


class _Hang:
    """Executor that sleeps far beyond any per-task timeout or cancellation."""

    async def execute(self, _assignment: AgentAssignment) -> AgentResult:
        await asyncio.sleep(3600)
        raise AssertionError("unreachable")


async def _set_after(event: asyncio.Event, delay: float) -> None:
    await asyncio.sleep(delay)
    event.set()


def test_unknown_tool_denied(tmp_path) -> None:
    plane = assemble_control_plane(repo_root=tmp_path)
    outcome = _run(
        plane.execute(
            assignment=make_assignment(),
            tool_name="definitely.not.there",
            arguments={},
            action_id="act-unknown",
        )
    )
    assert outcome.decision is ToolDecision.DENY
    assert outcome.allowed is False
    assert outcome.executed is False
    assert outcome.classification == "permission failure"
    assert "unknown tool" in outcome.result["reason"]
    assert plane.audit_trail().records()[-1].decision is AuditDecision.DENIED


def test_tool_outside_capability_denied(tmp_path) -> None:
    plane = assemble_control_plane(repo_root=tmp_path)
    assignment = make_assignment(allowed_tools=("evidence.record",))
    outcome = _run(
        plane.execute(
            assignment=assignment,
            tool_name="evidence.record",
            arguments={"claim_id": "C-1", "evidence": {}},
            action_id="act-mismatch",
        )
    )
    assert outcome.decision is ToolDecision.DENY
    assert outcome.allowed is False
    assert outcome.executed is False
    assert "capability mismatch" in str(outcome.result["reason"])
    assert outcome.classification == "permission failure"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.DENIED


def test_tool_timeout_classified() -> None:
    plane = ControlPlane(
        registry=make_registry(),
        engine=PolicyEngine(),
        audit=AuditTrail(),
        environment="development",
    )
    request = make_request(
        "command.slow", "act-timeout", allowed=("command.slow",), timeout_seconds=0.1
    )
    result = _run(plane.execute_request(request))
    assert result.status is ToolResultStatus.TIMEOUT
    assert result.error_classification == "timeout"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.TIMEOUT


def test_nonzero_exit_classified() -> None:
    outcome = _run(CommandRunner().run_python("raise SystemExit(3)"))
    assert outcome.exit_code == 3
    assert outcome.timed_out is False
    classification = FailureClassifier.classify(
        exit_code=outcome.exit_code,
        stderr=outcome.stderr,
        timed_out=outcome.timed_out,
        status=ToolResultStatus.FAILED,
    )
    assert classification == "tool failure"


def test_success_claim_without_evidence_flagged(tmp_path) -> None:
    bare = AgentResult(
        assignment_id="a1",
        task_id="t1",
        status="SUCCEEDED",
        started_at=_before(),
        finished_at=_now(),
    )
    issues = validate_result(bare)
    assert "SUCCEEDED without evidence" in issues

    async def _bare_success(
        assignment: AgentAssignment, _factory: object
    ) -> AgentResult:
        return AgentResult(
            assignment_id=assignment.id,
            task_id=assignment.task_id,
            status="SUCCEEDED",
            started_at=_before(),
            finished_at=_now(),
            claims=(),
            artifacts={"exit_code": 0},
            evidence=(),
            failures=(),
            execution_references=(),
            confidence=1.0,
            summary="success claimed without evidence",
        )

    graph = _graph(_task("bare"))
    factory = FakeFactory({"bare": _bare_success})
    orch = Orchestrator()
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(orch.run(graph=graph, executor_factory=factory, run_context=_context()))
    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert any(
        contradiction.severity == "mismatch"
        and contradiction.claim_id == "__validation__"
        for contradiction in report.contradictions
    )
    assert orch.state.task_statuses["bare"] == "FAILED"
    assert "bare" not in orch.state.completed_tasks


def test_contradictory_findings_detected(tmp_path) -> None:
    async def _claim_supported(
        assignment: AgentAssignment, _factory: object
    ) -> AgentResult:
        return _result(
            assignment,
            claims=("CLAIM-X",),
            artifacts={"claim_id": "CLAIM-X", "agreed": True, "exit_code": 0},
            summary="evidence A supports CLAIM-X",
        )

    async def _claim_contradicted(
        assignment: AgentAssignment, _factory: object
    ) -> AgentResult:
        return _result(
            assignment,
            claims=("CLAIM-X",),
            artifacts={"claim_id": "CLAIM-X", "agreed": False, "exit_code": 1},
            summary="evidence B contradicts CLAIM-X",
        )

    graph = _graph(_task("x"), _task("y"))
    factory = FakeFactory({"x": _claim_supported, "y": _claim_contradicted})
    orch = Orchestrator()
    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )
    assert report.status == "COMPLETED"
    assert any(
        contradiction.severity == "conflict" and contradiction.claim_id == "CLAIM-X"
        for contradiction in report.contradictions
    )


def test_one_timeout_others_finish_partial(tmp_path) -> None:
    async def _run_partial_wave() -> WaveResult:
        tasks = (_task("a"), _task("b"), _task("slow"))
        assignments = {
            "a": make_assignment(task_id="a", timeout_seconds=30.0),
            "b": make_assignment(task_id="b", timeout_seconds=30.0),
            "slow": make_assignment(task_id="slow", timeout_seconds=0.1),
        }
        executors = {"a": _Soon(), "b": _Soon(), "slow": _Hang()}
        request = WaveRunRequest(
            wave_id="w-partial",
            tasks=tasks,
            assignments=assignments,
            executors=executors,
        )
        return await ParallelWaveEngine().run_wave(request)

    wave = _run(_run_partial_wave())
    assert wave.status is WaveStatus.PARTIAL
    assert wave.task_failures["slow"].classification == "timeout"
    assert set(wave.task_results) == {"a", "b"}
    assert all(result.evidence for result in wave.task_results.values())
    assert all(result.status == "SUCCEEDED" for result in wave.task_results.values())


def test_failed_specialist_replaced(tmp_path) -> None:
    calls = {"n": 0}

    async def _always_varying_failure(
        assignment: AgentAssignment, _factory: object
    ) -> AgentResult:
        calls["n"] += 1
        raise RuntimeError(f"variant-{calls['n']}")

    graph = _graph(_task("hard"))
    factory = FakeFactory({"hard": _always_varying_failure})
    orch = Orchestrator()
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(orch.run(graph=graph, executor_factory=factory, run_context=_context()))
    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert any(decision.kind == "replace_agent" for decision in report.decisions)
    assert any(spec.agent_id.endswith("-replacement1") for spec in factory.created)


def test_duplicate_invocation_denied(tmp_path) -> None:
    registry = assemble_default_registry(repo_root=tmp_path)
    plane = assemble_control_plane(registry=registry, repo_root=tmp_path)
    arguments = {"path": "dup.txt", "content": "x"}
    first = _run(
        plane.execute_request(
            make_request(
                "file.write",
                "act-dup",
                arguments=arguments,
                allowed=("file.write",),
            )
        )
    )
    assert first.status is ToolResultStatus.SUCCEEDED
    second = _run(
        plane.execute_request(
            make_request(
                "file.write",
                "act-dup",
                arguments=arguments,
                allowed=("file.write",),
            )
        )
    )
    assert second.status is ToolResultStatus.DENIED
    assert second.error_classification == "permission failure"
    assert "duplicate invocation" in second.message
    executed = [
        record
        for record in plane.audit_trail().records()
        if record.action_id == "act-dup" and record.decision is AuditDecision.EXECUTED
    ]
    assert len(executed) == 1


def test_retry_budget_exhausted_blocks(tmp_path) -> None:
    async def _stable_failure(
        assignment: AgentAssignment, _factory: object
    ) -> AgentResult:
        raise RuntimeError("stable boom")

    graph = _graph(_task("stable"))
    factory = FakeFactory({"stable": _stable_failure})
    orch = Orchestrator(
        config=OrchestratorConfig(
            retry=RetryPolicy(
                max_retries_per_task=1, allow_replacement=False, no_progress_threshold=5
            )
        )
    )
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(orch.run(graph=graph, executor_factory=factory, run_context=_context()))
    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert report.next_transition == "BLOCKED"
    assert any(decision.kind == "retry" for decision in report.decisions)
    assert report.decisions[-1].kind == "BLOCKED"


def test_no_progress_identical_signatures_blocks(tmp_path) -> None:
    async def _stable_failure(
        assignment: AgentAssignment, _factory: object
    ) -> AgentResult:
        raise RuntimeError("boom")

    graph = _graph(_task("doomed"))
    factory = FakeFactory({"doomed": _stable_failure})
    orch = Orchestrator(
        config=OrchestratorConfig(
            retry=RetryPolicy(
                max_retries_per_task=1, allow_replacement=True, no_progress_threshold=2
            )
        )
    )
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(orch.run(graph=graph, executor_factory=factory, run_context=_context()))
    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert report.next_transition == "BLOCKED"
    assert any(decision.kind == "no_progress_block" for decision in report.decisions)


def test_serialized_task_never_concurrent(tmp_path) -> None:
    graph = _graph(_task("a"), _task("s", kind=TaskKind.SERIALIZED))
    orch = Orchestrator()
    plan = orch.plan_waves(graph)
    assert len(plan[0]) == 1
    assert plan[0][0].id == "s"
    factory = FakeFactory()
    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )
    assert report.status == "COMPLETED"
    assert report.wave_summaries[0]["tasks"] == ["s"]
    assert factory.execution_order == ["s", "a"]


def test_dangerous_policy_block(tmp_path) -> None:
    engine = PolicyEngine(
        rules=(
            PolicyRule(
                id="block-write",
                decision=PolicyDecision.BLOCK,
                resource=ResourceKind.TOOL,
                tool_name="file.write",
                reason="write permanently forbidden in this environment",
            ),
            PolicyRule(
                id="block-write-resource",
                decision=PolicyDecision.BLOCK,
                resource=ResourceKind.PATH,
                tool_name="file.write",
                reason="path resources are forbidden",
            ),
        )
    )
    plane = ControlPlane(
        registry=make_registry(),
        engine=engine,
        audit=AuditTrail(),
        environment="development",
    )
    outcome = _run(
        plane.execute(
            assignment=make_assignment(allowed_tools=("file.write",)),
            tool_name="file.write",
            arguments={"path": "secret.txt", "content": "x"},
            action_id="act-block",
        )
    )
    assert outcome.decision is ToolDecision.BLOCK
    assert outcome.allowed is False
    assert outcome.executed is False
    assert outcome.classification == "safety/policy block"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.BLOCKED


def test_incomplete_execution_result(tmp_path) -> None:
    plane = assemble_control_plane(repo_root=tmp_path)
    now = _now()
    incomplete = ToolExecutionResult(
        invocation_id="inv-1",
        tool_name="file.write",
        request_id="req-1",
        status=ToolResultStatus.FAILED,
        started_at=now,
        finished_at=now,
        duration_seconds=0.0,
        exit_code=None,
        stdout="",
        stderr="",
        message="the tool failed before producing a result",
    )
    assert (
        FailureClassifier.classify(
            exit_code=None,
            stderr="",
            timed_out=False,
            status=ToolResultStatus.FAILED,
        )
        == ""
    )
    outcome = plane._outcome_from_result(incomplete)
    assert outcome.classification == "tool failure"
    assert outcome.result["status"] == "FAILED"
    assert outcome.allowed is True
    assert outcome.executed is True


def test_sandbox_unavailable_is_honest(tmp_path) -> None:
    registry = assemble_default_registry(repo_root=tmp_path)
    plane = assemble_control_plane(registry=registry, repo_root=tmp_path)
    result = _run(
        plane.execute_request(
            make_request(
                "sandbox.create",
                "act-sandbox",
                arguments={"image": "python:3.11-slim"},
                allowed=("sandbox.",),
            )
        )
    )
    assert result.status is ToolResultStatus.UNAVAILABLE
    assert result.error_classification == "environment/dependency failure"
    assert result.sandbox_id == ""
    assert "sandbox_id" not in result.artifacts
    assert result.artifacts["sandbox_status"] == "UNAVAILABLE"
    assert plane.audit_trail().records()[-1].decision is AuditDecision.CANCELLED


def test_control_plane_bypass_attempt(tmp_path) -> None:
    assert issubclass(UnauthorizedToolError, Exception)
    assert issubclass(ToolExecutionError, Exception)

    async def _bypass() -> None:
        toolkit = RepositoryToolkit(root=tmp_path, writer="bypass-probe")
        registry = assemble_default_registry(repo_root=tmp_path, toolkit=toolkit)
        trail = AuditTrail()
        plane = assemble_control_plane(
            registry=registry, repo_root=tmp_path, audit=trail
        )
        spec = registry.get("file.write")
        assert spec is not None
        assert spec.handler is not None
        request = make_request(
            "file.write",
            "act-bypass",
            arguments={"path": "bypass.txt", "content": "sneaky"},
            allowed=("file.write",),
        )
        result = await spec.handler(request)
        assert result.status is ToolResultStatus.SUCCEEDED
        assert trail.records() == ()
        assert not trail.has_invocation(result.invocation_id)
        writes = [
            mutation
            for mutation in toolkit.mutations()
            if mutation["operation"] == "write"
        ]
        assert writes
        assert not any(record.action_id == "act-bypass" for record in trail.records())
        denied = await plane.execute(
            assignment=make_assignment(),
            tool_name="no.such.tool",
            arguments={},
            action_id="act-bypass-deny",
        )
        assert denied.allowed is False
        assert denied.executed is False

    _run(_bypass())


def test_partial_wave_failure_surfaces(tmp_path) -> None:
    async def _stable_failure(
        assignment: AgentAssignment, _factory: object
    ) -> AgentResult:
        return _result(
            assignment,
            status="FAILED",
            classification="tool failure",
            summary="stable defect in module under test",
        )

    graph = _graph(_task("f"), _task("g"), _task("h"))
    factory = FakeFactory(
        {
            "f": _stable_failure,
            "g": _default_behaviour,
            "h": _default_behaviour,
        }
    )
    orch = Orchestrator(
        config=OrchestratorConfig(
            retry=RetryPolicy(max_retries_per_task=0, allow_replacement=False)
        )
    )
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(orch.run(graph=graph, executor_factory=factory, run_context=_context()))
    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert any(failure.classification == "tool failure" for failure in report.failures)
    summary = report.wave_summaries[0]
    assert summary["status"] == "FAILED"
    assert "f" in summary["tasks"]
    assert any(str(item).startswith("tool failure:") for item in summary["failures"])
    assert {evidence.source for evidence in report.evidence} >= {"task:g", "task:h"}


def test_mid_execution_cancellation(tmp_path) -> None:
    async def _run_cancelled_wave() -> WaveResult:
        tasks = (_task("x"), _task("y"))
        assignments = {
            "x": make_assignment(task_id="x", timeout_seconds=10.0),
            "y": make_assignment(task_id="y", timeout_seconds=10.0),
        }
        executors = {"x": _Hang(), "y": _Hang()}
        request = WaveRunRequest(
            wave_id="w-cancel",
            tasks=tasks,
            assignments=assignments,
            executors=executors,
        )
        event = asyncio.Event()
        fire = asyncio.create_task(_set_after(event, 0.1))
        try:
            return await ParallelWaveEngine(wave_timeout_seconds=30.0).run_wave(
                request, cancel_event=event
            )
        finally:
            await fire

    wave = _run(_run_cancelled_wave())
    assert wave.status is WaveStatus.CANCELLED
    assert wave.incomplete_agents
    assert all(timing.status == "CANCELLED" for timing in wave.timings)


def test_stale_result_ignored(tmp_path) -> None:
    async def _stale(assignment: AgentAssignment, _factory: object) -> AgentResult:
        return _result(assignment, task_id="elsewhere", assignment_id="bogus-id")

    graph = _graph(_task("good"), _task("stale"))
    factory = FakeFactory({"good": _default_behaviour, "stale": _stale})
    orch = Orchestrator()
    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )
    assert report.status == "COMPLETED"
    assert any(
        contradiction.severity == "mismatch"
        and contradiction.claim_id == "__stale_result__"
        for contradiction in report.contradictions
    )
    assert orch.state.task_statuses["stale"] == "CANCELLED"
    assert "stale" not in orch.state.completed_tasks
    assert {evidence.source for evidence in report.evidence} == {"task:good"}


def test_invalid_state_transition_rejected(tmp_path) -> None:
    del tmp_path
    orch = Orchestrator()
    orch.transition(WorkflowPhase.INSPECTING)
    orch.transition(WorkflowPhase.PLANNING)
    orch.transition(WorkflowPhase.DISPATCHING)
    with pytest.raises(InvalidWorkflowTransition) as excinfo:
        orch.transition(WorkflowPhase.BLOCKED, reason="illegal jump")
    assert excinfo.value.current is WorkflowPhase.DISPATCHING
    assert excinfo.value.attempted is WorkflowPhase.BLOCKED

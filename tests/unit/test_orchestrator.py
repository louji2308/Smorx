"""Unit tests for dependency-aware wave orchestration.

These tests exercise the :class:`Orchestrator` through a scripted
``FakeExecutorFactory`` whose behaviour is controlled per task, using
:class:`MemoryGateway` to prove that tool invocations are capability-gated.
Async tests run via ``asyncio.run`` (no pytest-asyncio dependency).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from smorx_runtime.agents import (
    AgentAssignment,
    AgentContext,
    AgentEvidence,
    AgentFailure,
    AgentResult,
    AgentSpec,
)
from smorx_runtime.capabilities import CAPABILITY_CATALOG
from smorx_runtime.graph import TaskGraph, TaskKind, TaskSpec
from smorx_runtime.orchestrator import (
    InvalidWorkflowTransition,
    OrchestrationBlocked,
    Orchestrator,
    OrchestratorConfig,
    RetryPolicy,
    WorkflowPhase,
)
from smorx_runtime.toolgate import MemoryGateway

Behaviour = Callable[
    [AgentAssignment, AgentSpec, MemoryGateway], Awaitable[AgentResult]
]


def _result(
    assignment: AgentAssignment,
    *,
    status: str = "SUCCEEDED",
    classification: str = "",
    summary: str = "ok",
    artifacts: Mapping[str, object] | None = None,
    claims: tuple[str, ...] = (),
    evidence: tuple[AgentEvidence, ...] | None = None,
    task_id: str | None = None,
    assignment_id: str | None = None,
) -> AgentResult:
    """Build a discipline-valid :class:`AgentResult` bound to ``assignment``."""
    started_at = datetime.now(UTC) - timedelta(seconds=1)
    finished_at = datetime.now(UTC)
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
            next_recommendation="",
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
                classification=classification or "failed",
                summary=summary,
                observed_at=finished_at,
            ),
        ),
        confidence=1.0,
        next_recommendation="",
        summary=summary,
    )


async def _default_behaviour(
    assignment: AgentAssignment,
    spec: AgentSpec,
    gateway: MemoryGateway,
) -> AgentResult:
    del spec, gateway
    return _result(assignment)


class FakeExecutor:
    """Runs a task-specific behaviour coroutine under a bounded timeout."""

    def __init__(self, factory: FakeFactory, spec: AgentSpec) -> None:
        self._factory = factory
        self.spec = spec

    async def execute(self, assignment: AgentAssignment) -> AgentResult:
        self._factory.seen_assignments.append(assignment)
        self._factory.execution_order.append(assignment.task_id)
        behaviour = self._factory.behaviours.get(assignment.task_id, _default_behaviour)
        try:
            return await asyncio.wait_for(
                behaviour(assignment, self.spec, self._factory.gateway),
                timeout=self._factory.timeout,
            )
        except TimeoutError:
            return _result(
                assignment,
                status="FAILED",
                classification="timeout",
                summary="per-agent timeout exceeded",
            )
        except Exception as exc:  # noqa: BLE001 - scripted behaviour failures become FAILED results
            return _result(
                assignment,
                status="FAILED",
                classification="execution_failure",
                summary=str(exc),
            )


class FakeFactory:
    """Produces executors whose behaviour is keyed by ``task_id``."""

    def __init__(
        self,
        behaviours: Mapping[str, Behaviour] | None = None,
        *,
        gateway: MemoryGateway,
        timeout: float = 30.0,
    ) -> None:
        self.behaviours = dict(behaviours or {})
        self.gateway = gateway
        self.timeout = timeout
        self.created: list[AgentSpec] = []
        self.seen_assignments: list[AgentAssignment] = []
        self.execution_order: list[str] = []

    def create(
        self,
        spec: AgentSpec,
        *,
        allowed_tools: tuple[str, ...] = (),
    ) -> FakeExecutor:
        del allowed_tools
        self.created.append(spec)
        return FakeExecutor(self, spec)


def _run(coro: Awaitable[object]) -> object:
    return asyncio.run(coro)


def _context() -> AgentContext:
    return AgentContext(
        run_id=f"run-test-{uuid4().hex[:8]}",
        phase="orchestration",
        task_id="orchestrator",
        correlation_id=f"corr-{uuid4().hex[:8]}",
    )


def _task(
    task_id: str,
    *,
    capability: object = None,
    kind: TaskKind = TaskKind.INDEPENDENT,
    depends_on: tuple[str, ...] = (),
    description: str = "",
) -> TaskSpec:
    cap = capability if capability is not None else next(iter(CAPABILITY_CATALOG))
    assert cap is not None
    return TaskSpec(
        id=task_id,
        capability=cap,
        kind=kind,
        depends_on=tuple(depends_on),
        description=description or f"execute {task_id}",
    )


def _graph(*specs: TaskSpec) -> TaskGraph:
    graph = TaskGraph()
    for spec in specs:
        graph.add(spec)
    return graph


def _contains_subsequence(values: list[str], subsequence: list[str]) -> bool:
    iterator = iter(values)
    return all(element in iterator for element in subsequence)


def test_parallel_wave_planning_three_independents() -> None:
    graph = _graph(_task("a"), _task("b"), _task("c"))
    factory = FakeFactory(gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    phase_values = [phase.value for phase in report.phases]
    assert _contains_subsequence(
        phase_values,
        ["PLANNING", "DISPATCHING", "EXECUTING", "COLLECTING", "COMPLETED"],
    )
    assert len(report.wave_summaries) == 1
    assert set(report.wave_summaries[0]["tasks"]) == {"a", "b", "c"}
    assert len(factory.execution_order) == 3
    assert orch.phase == WorkflowPhase.COMPLETED


def test_dependency_chain_runs_b_after_a() -> None:
    graph = _graph(_task("a"), _task("b", depends_on=("a",)))
    factory = FakeFactory(gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    assert report.wave_summaries[0]["tasks"] == ["a"]
    assert report.wave_summaries[1]["tasks"] == ["b"]
    assert len(report.wave_summaries) == 2
    assert factory.execution_order == ["a", "b"]
    assert orch.state.completed_tasks == ["a", "b"]


def test_result_fusion_and_evidence() -> None:
    graph = _graph(_task("a"), _task("b"))
    factory = FakeFactory(gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    assert {evidence.source for evidence in report.evidence} == {"task:a", "task:b"}
    assert set(orch.state.agent_results) == {"a", "b"}
    assert set(orch.state.completed_tasks) == {"a", "b"}


def test_conflict_detection_same_claim_contradictory_evidence() -> None:
    async def claim_true(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del spec, gateway
        return _result(
            assignment,
            artifacts={"claim_id": "AUTH-017", "agreed": True, "exit_code": 0},
            claims=("AUTH-017",),
            summary="auth rule enforced",
        )

    async def claim_false(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del spec, gateway
        return _result(
            assignment,
            artifacts={"claim_id": "AUTH-017", "agreed": False, "exit_code": 1},
            claims=("AUTH-017",),
            summary="auth rule violated",
        )

    graph = _graph(_task("x"), _task("y"))
    factory = FakeFactory({"x": claim_true, "y": claim_false}, gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    conflicts = [c for c in report.contradictions if c.severity == "conflict"]
    assert any(c.claim_id == "AUTH-017" for c in conflicts)
    assert len(orch.state.conflicts) >= 1


def test_timeout_handling_is_bounded_and_retries() -> None:
    calls = {"n": 0}

    async def sleepy_then_fast(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del spec, gateway
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.sleep(0.5)
        return _result(assignment)

    graph = _graph(_task("slow"))
    factory = FakeFactory(
        {"slow": sleepy_then_fast}, gateway=MemoryGateway(), timeout=30.0
    )
    orch = Orchestrator(config=OrchestratorConfig(per_agent_timeout_seconds=0.1))

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    assert any(failure.classification == "timeout" for failure in report.failures)
    assert any(decision.kind == "retry" for decision in report.decisions)


def test_no_progress_identical_signatures_block() -> None:
    async def bomb(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del assignment, spec, gateway
        raise RuntimeError("boom")

    graph = _graph(_task("doomed"))
    factory = FakeFactory({"doomed": bomb}, gateway=MemoryGateway())
    orch = Orchestrator(
        config=OrchestratorConfig(retry=RetryPolicy(no_progress_threshold=2))
    )

    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(orch.run(graph=graph, executor_factory=factory, run_context=_context()))

    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert report.next_transition == "BLOCKED"
    assert any(decision.kind == "no_progress_block" for decision in report.decisions)
    assert orch.phase == WorkflowPhase.BLOCKED


def test_retry_records_decision_and_completes() -> None:
    calls = {"n": 0}

    async def flaky(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del spec, gateway
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("first attempt blows up")
        return _result(assignment)

    graph = _graph(_task("flaky"))
    factory = FakeFactory({"flaky": flaky}, gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    assert any(decision.kind == "retry" for decision in report.decisions)
    assert len(report.wave_summaries) == 2


def test_replacement_created_then_blocked_when_still_failing() -> None:
    calls = {"n": 0}

    async def always_varying_failure(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del assignment, spec, gateway
        calls["n"] += 1
        raise RuntimeError(f"variant-{calls['n']}")

    graph = _graph(_task("hard"))
    factory = FakeFactory({"hard": always_varying_failure}, gateway=MemoryGateway())
    orch = Orchestrator()

    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(orch.run(graph=graph, executor_factory=factory, run_context=_context()))

    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert any(decision.kind == "replace_agent" for decision in report.decisions)
    assert any(spec.agent_id.endswith("-replacement1") for spec in factory.created)


def test_permission_assignment_and_tool_gating() -> None:
    capability = next(iter(CAPABILITY_CATALOG))
    allowed_tools = tuple(CAPABILITY_CATALOG[capability].allowed_tool_prefixes)

    async def use_tools(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del spec
        chosen = allowed_tools[0] if allowed_tools else "execute"
        granted = await gateway.execute(
            assignment=assignment,
            tool_name=chosen,
            arguments={"probe": "x"},
            action_id=f"act:{assignment.task_id}:1",
        )
        assert granted.allowed is True
        assert granted.executed is True
        denied = await gateway.execute(
            assignment=assignment,
            tool_name="not-a-real-tool",
            arguments={},
            action_id=f"act:{assignment.task_id}:2",
        )
        assert denied.allowed is False
        assert denied.executed is False
        return _result(assignment, artifacts={"exit_code": 0, "tool": chosen})

    task = _task("probe", capability=capability)
    graph = _graph(task)
    factory = FakeFactory({"probe": use_tools}, gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    assert set(factory.seen_assignments[0].allowed_tools) == set(allowed_tools)
    invocations = factory.gateway.invocations()
    assert all(
        invocation["tool_name"] in set(allowed_tools)
        for invocation in invocations
        if invocation["allowed"]
    )
    assert any(
        not invocation["allowed"] and invocation["tool_name"] == "not-a-real-tool"
        for invocation in invocations
    )
    assert any(invocation["executed"] for invocation in invocations)


def test_stale_result_flagged_mismatch_and_ignored() -> None:
    async def good(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del spec, gateway
        return _result(assignment)

    async def stale(
        assignment: AgentAssignment, spec: AgentSpec, gateway: MemoryGateway
    ) -> AgentResult:
        del spec, gateway
        return _result(assignment, task_id="elsewhere", assignment_id="bogus-id")

    graph = _graph(_task("good"), _task("stale"))
    factory = FakeFactory({"good": good, "stale": stale}, gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    mismatches = [c for c in report.contradictions if c.severity == "mismatch"]
    assert any(c.claim_id == "__stale_result__" for c in mismatches)
    assert orch.state.task_statuses["stale"] == "CANCELLED"
    assert {evidence.source for evidence in report.evidence} == {"task:good"}


def test_invalid_transition_raises() -> None:
    orch = Orchestrator()
    with pytest.raises(InvalidWorkflowTransition):
        orch.transition(WorkflowPhase.COMPLETED)

    orch.transition(WorkflowPhase.INSPECTING)
    with pytest.raises(InvalidWorkflowTransition):
        orch.transition(WorkflowPhase.EXECUTING)

    orch.transition(WorkflowPhase.PLANNING)
    orch.transition(WorkflowPhase.DISPATCHING)
    with pytest.raises(InvalidWorkflowTransition):
        orch.transition(WorkflowPhase.COMPLETED)


def test_reconciler_runs_last_after_dependencies() -> None:
    alpha = _task("alpha")
    beta = _task("beta")
    gamma = _task("gamma")
    reconciler = _task(
        "reconciler",
        kind=TaskKind.RECONCILER,
        depends_on=("alpha", "beta", "gamma"),
    )
    graph = _graph(alpha, beta, gamma, reconciler)
    factory = FakeFactory(gateway=MemoryGateway())
    orch = Orchestrator()

    report = _run(
        orch.run(graph=graph, executor_factory=factory, run_context=_context())
    )

    assert report.status == "COMPLETED"
    assert len(report.wave_summaries) == 2
    assert report.wave_summaries[1]["tasks"] == ["reconciler"]
    assert "RECONCILING" in [phase.value for phase in report.phases]
    assert any(decision.kind == "reconcile" for decision in report.decisions)

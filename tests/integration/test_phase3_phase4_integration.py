"""Phase 3/4 integration: Orchestrator over the real Phase 4 ControlPlane.

The tests drive the dependency-aware ``Orchestrator`` through a gateway-backed
executor that performs REAL tool executions through ``smorx_tools.control``:
file writes land on disk, ``command.run`` spawns a real subprocess, evidence is
persisted, the audit trail records every ALLOW/DENY/REVIEW/EXECUTE, and
high-risk or mismatched tools produce honest blocked workflows.

Every test is synchronous (``asyncio.run``, no pytest-asyncio dependency), all
executions are real, and every executor reports an evidence-bearing
``AgentResult`` that satisfies the ``validate_result`` discipline. The only
test-side policy is the ``Mode`` callable, which decides which real tool each
assignment invokes with which arguments.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
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
from smorx_runtime.capabilities import SpecialistCapability
from smorx_runtime.graph import TaskGraph, TaskKind, TaskSpec
from smorx_runtime.orchestrator import (
    OrchestrationBlocked,
    OrchestrationReport,
    Orchestrator,
    OrchestratorConfig,
    RetryPolicy,
    WorkflowPhase,
)
from smorx_runtime.toolgate import CapabilityGateway, ToolDecision, ToolOutcome
from smorx_tools.assembly import assemble_control_plane, assemble_default_registry
from smorx_tools.audit import AuditDecision
from smorx_tools.control import ControlPlane
from smorx_tools.human import HumanControlPlane
from smorx_tools.tool import ToolKind, ToolSpec

Step = tuple[str, Mapping[str, object]]
Steps = Sequence[Step]
Mode = Callable[[AgentAssignment], Steps]

_APPROVAL_TASK = "approve-run"
_WRITE_CONTENTS = {
    "t0": "content-t0",
    "t1": "content-t1",
    "t2": "content-t2",
}


class PlaneExecutor:
    """Real-gateway executor: one authorized tool step per ``Mode`` entry.

    Every step is executed through ``plane.authorize_and_execute`` with a
    deterministic action id derived only from ``task_id`` and ``agent_id``.
    Successful steps produce evidence; failed or denied steps produce failure
    records, so the returned ``AgentResult`` always passes ``validate_result``.
    """

    def __init__(self, factory: PlaneExecutorFactory, spec: AgentSpec) -> None:
        del spec
        self._factory = factory

    async def execute(self, assignment: AgentAssignment) -> AgentResult:
        started_at = datetime.now(UTC)
        delay = self._factory.gate_delay_seconds
        if delay > 0:
            await asyncio.sleep(delay)
        action_id = f"{assignment.task_id}:{assignment.agent_id}"
        outcomes: list[ToolOutcome] = []
        for tool_name, arguments in self._factory.mode(assignment):
            outcome = await self._factory.plane.authorize_and_execute(
                assignment=assignment,
                tool_name=tool_name,
                arguments=arguments,
                action_id=action_id,
            )
            outcomes.append(outcome)
        self._factory.record(assignment, outcomes)
        finished_at = datetime.now(UTC)
        return self._result_from_outcomes(assignment, outcomes, started_at, finished_at)

    @staticmethod
    def _was_success(outcome: ToolOutcome) -> bool:
        return outcome.allowed and outcome.executed and not outcome.classification

    def _result_from_outcomes(
        self,
        assignment: AgentAssignment,
        outcomes: Sequence[ToolOutcome],
        started_at: datetime,
        finished_at: datetime,
    ) -> AgentResult:
        evidence = tuple(
            self._evidence(assignment, outcome, finished_at)
            for outcome in outcomes
            if self._was_success(outcome)
        )
        failures = tuple(
            self._failure(assignment, outcome, finished_at)
            for outcome in outcomes
            if not self._was_success(outcome)
        )
        if not failures:
            return AgentResult(
                assignment_id=assignment.id,
                task_id=assignment.task_id,
                status="SUCCEEDED",
                started_at=started_at,
                finished_at=finished_at,
                claims=(),
                artifacts=dict(outcomes[-1].result),
                evidence=evidence,
                failures=(),
                execution_references=tuple(
                    outcome.invocation_id for outcome in outcomes
                ),
                confidence=1.0,
                next_recommendation="",
                summary=f"executed {len(outcomes)} authorized tool step(s)",
            )
        return AgentResult(
            assignment_id=assignment.id,
            task_id=assignment.task_id,
            status="FAILED",
            started_at=started_at,
            finished_at=finished_at,
            claims=(),
            artifacts={},
            evidence=evidence,
            failures=failures,
            confidence=1.0,
            next_recommendation="",
            summary=failures[0].summary,
        )

    @staticmethod
    def _evidence(
        assignment: AgentAssignment, outcome: ToolOutcome, timestamp: datetime
    ) -> AgentEvidence:
        return AgentEvidence(
            evidence_id=(
                f"ev:{assignment.task_id}:{assignment.agent_id}:"
                f"{outcome.invocation_id[:12]}"
            ),
            source=f"task:{assignment.task_id}",
            timestamp=timestamp,
            evidence_type="EXECUTION_RESULT",
            claim_id=None,
            machine_result=dict(outcome.result),
            provenance=(
                f"tool:{outcome.tool_name};task:{assignment.task_id};"
                f"audit:{outcome.audit_ref}"
            ),
            related_execution=outcome.invocation_id,
        )

    @staticmethod
    def _failure(
        assignment: AgentAssignment, outcome: ToolOutcome, observed_at: datetime
    ) -> AgentFailure:
        if outcome.decision is ToolDecision.REQUIRE_REVIEW:
            classification = "permission failure"
            summary = "tool requires human review"
        elif outcome.decision is ToolDecision.DENY:
            classification = "permission failure"
            summary = f"tool {outcome.tool_name} denied: {outcome.result.get('reason', 'denied')}"
        elif outcome.decision is ToolDecision.BLOCK:
            classification = "safety/policy block"
            summary = f"tool {outcome.tool_name} blocked by policy"
        else:
            classification = outcome.classification or "tool failure"
            summary = f"tool {outcome.tool_name} failed: {classification}"
        return AgentFailure(
            failure_id=(
                f"f:{assignment.task_id}:{assignment.agent_id}:"
                f"{outcome.invocation_id[:12]}"
            ),
            classification=classification,
            summary=summary,
            observed_at=observed_at,
        )


class PlaneExecutorFactory:
    """Creates gateway-driven executors and records what actually executed."""

    def __init__(
        self,
        plane: ControlPlane,
        mode: Mode,
        *,
        gate_delay_seconds: float = 0.0,
    ) -> None:
        self.plane = plane
        self.mode = mode
        self.gate_delay_seconds = gate_delay_seconds
        self.created: list[AgentSpec] = []
        self.allowed_tools_seen: list[tuple[str, ...]] = []
        self.seen_assignments: list[AgentAssignment] = []
        self.outcomes: list[ToolOutcome] = []

    def create(
        self, spec: AgentSpec, *, allowed_tools: tuple[str, ...] = ()
    ) -> PlaneExecutor:
        self.created.append(spec)
        self.allowed_tools_seen.append(allowed_tools)
        return PlaneExecutor(self, spec)

    def record(
        self, assignment: AgentAssignment, outcomes: Sequence[ToolOutcome]
    ) -> None:
        self.seen_assignments.append(assignment)
        self.outcomes.extend(outcomes)


def _run(coro: Awaitable[OrchestrationReport]) -> OrchestrationReport:
    return asyncio.run(coro)


def _context() -> AgentContext:
    return AgentContext(
        run_id=f"run-{uuid4().hex[:8]}",
        phase="8",
        task_id="orchestrator",
        correlation_id=f"corr-{uuid4().hex[:8]}",
    )


def _blocking_config() -> OrchestratorConfig:
    return OrchestratorConfig(
        per_agent_timeout_seconds=30.0,
        retry=RetryPolicy(
            max_retries_per_task=0,
            allow_replacement=False,
            no_progress_threshold=1,
        ),
    )


def _graph(*tasks: TaskSpec) -> TaskGraph:
    graph = TaskGraph()
    for task in tasks:
        graph.add(task)
    return graph


def _plane(
    repo_root: Path,
    *,
    human: HumanControlPlane | None = None,
    extra_tools: Sequence[ToolSpec] = (),
) -> ControlPlane:
    registry = assemble_default_registry(repo_root=repo_root)
    for spec in extra_tools:
        registry.register(spec)
    return assemble_control_plane(repo_root=repo_root, registry=registry, human=human)


def _coding_task(task_id: str, description: str) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        capability=SpecialistCapability.CODING,
        description=description,
    )


def _write_coding_mode(assignment: AgentAssignment) -> Steps:
    index = assignment.task_id[-1]
    return (
        (
            "file.write",
            {
                "path": f"out/{assignment.task_id}.txt",
                "content": _WRITE_CONTENTS[assignment.task_id],
                "claim_id": f"AUTH-0{index}",
            },
        ),
    )


def _reconcile_evidence_mode(assignment: AgentAssignment) -> Steps:
    del assignment
    return (
        ("file.read", {"path": "out/t0.txt"}),
        (
            "evidence.record",
            {
                "claim_id": "AUTH-CHAIN",
                "evidence": {
                    "verified": True,
                    "subject": "out/t0.txt",
                    "trace": "parallel writes -> independent read -> recorded evidence",
                },
            },
        ),
    )


def _command_run_mode(assignment: AgentAssignment) -> Steps:
    del assignment
    return (("command.run", {"python_code": "print('APPROVED-RUN')"}),)


def _trust_chain_mode(assignment: AgentAssignment) -> Steps:
    if assignment.task_id == "rec":
        return _reconcile_evidence_mode(assignment)
    return _write_coding_mode(assignment)


def test_end_to_end_trust_chain_completed(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    assert isinstance(plane, CapabilityGateway)
    orchestrator = Orchestrator(gateway=plane)

    graph = _graph(
        _coding_task("t0", "write out/t0.txt"),
        _coding_task("t1", "write out/t1.txt"),
        _coding_task("t2", "write out/t2.txt"),
        TaskSpec(
            id="rec",
            capability=SpecialistCapability.EVIDENCE,
            kind=TaskKind.RECONCILER,
            description="read one written file back and record claim evidence",
            depends_on=("t0", "t1", "t2"),
        ),
    )
    factory = PlaneExecutorFactory(plane, _trust_chain_mode, gate_delay_seconds=0.05)
    report = _run(
        orchestrator.run(
            graph=graph,
            executor_factory=factory,
            run_context=_context(),
        )
    )

    assert report.status == "COMPLETED"
    assert report.phases[-1] is WorkflowPhase.COMPLETED
    assert report.contradictions == ()
    for task_id in ("t0", "t1", "t2"):
        written = tmp_path / "out" / f"{task_id}.txt"
        assert written.read_text(encoding="utf-8") == _WRITE_CONTENTS[task_id]
    first_wave = report.telemetry["waves"][0]
    assert first_wave["parallelism_high_water"] >= 2
    evidence_by_source = {evidence.source: evidence for evidence in report.evidence}
    assert set(evidence_by_source) == {"task:t0", "task:t1", "task:t2", "task:rec"}
    assert all(evidence.machine_result for evidence in report.evidence)
    assert any(
        record.decision is AuditDecision.EXECUTED
        and record.tool_name == "evidence.record"
        for record in plane.audit_trail().records()
    )
    decisions = plane.audit_trail().summary()["decisions"]
    assert decisions.get("ALLOWED", 0) >= 5
    assert decisions.get("EXECUTED", 0) >= 5


def test_missing_handler_is_failed_result(tmp_path: Path) -> None:
    plane = _plane(
        tmp_path,
        extra_tools=(
            ToolSpec(
                name="file.noop",
                kind=ToolKind.FILE,
                description="declared tool with no handler",
                capability="CODING",
                risk="low",
                handler=None,
            ),
        ),
    )

    def noop_mode(assignment: AgentAssignment) -> Steps:
        del assignment
        return (("file.noop", {}),)

    graph = _graph(
        TaskSpec(
            id="noop",
            capability=SpecialistCapability.CODING,
            description="invoke a tool without a handler",
        )
    )
    factory = PlaneExecutorFactory(plane, noop_mode)
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(
            Orchestrator(gateway=plane, config=_blocking_config()).run(
                graph=graph,
                executor_factory=factory,
                run_context=_context(),
            )
        )
    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert report.next_transition == "BLOCKED"
    assert report.failures[0].classification == "tool failure"
    assert report.failures[0].summary == "tool file.noop failed: tool failure"

    outcome = factory.outcomes[0]
    assert outcome.allowed is True
    assert outcome.executed is True
    assert outcome.classification == "tool failure"
    assert plane.audit_trail().by_tool("file.noop")[-1].decision is AuditDecision.FAILED


def test_requires_review_then_human_approval_re_runs(tmp_path: Path) -> None:
    human = HumanControlPlane()
    graph = _graph(
        TaskSpec(
            id=_APPROVAL_TASK,
            capability=SpecialistCapability.CODING,
            description="run one high-risk command",
        )
    )

    plane_blocked = _plane(tmp_path, human=human)
    factory_blocked = PlaneExecutorFactory(plane_blocked, _command_run_mode)
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(
            Orchestrator(gateway=plane_blocked, config=_blocking_config()).run(
                graph=graph,
                executor_factory=factory_blocked,
                run_context=_context(),
            )
        )
    first_report = excinfo.value.report
    assert first_report.status == "BLOCKED"
    assert first_report.contradictions == ()

    command_records = plane_blocked.audit_trail().by_tool("command.run")
    assert any(record.decision is AuditDecision.REVIEW for record in command_records)
    assert not any(
        record.decision is AuditDecision.EXECUTED for record in command_records
    )
    assert factory_blocked.outcomes[0].decision is ToolDecision.REQUIRE_REVIEW
    assert factory_blocked.outcomes[0].executed is False
    assert factory_blocked.outcomes[0].reviewed is True

    action_id = f"{_APPROVAL_TASK}:{_APPROVAL_TASK}-agent"
    approval = human.request_approval(
        action_id=action_id,
        tool_name="command.run",
        reason="trusted one-off command for the demo",
    )
    human.approve(approval.approval_id, by="reviewer")

    plane_approved = _plane(tmp_path, human=human)
    factory_approved = PlaneExecutorFactory(plane_approved, _command_run_mode)
    second_report = _run(
        Orchestrator(gateway=plane_approved).run(
            graph=graph,
            executor_factory=factory_approved,
            run_context=_context(),
        )
    )
    assert second_report.status == "COMPLETED"
    approved_records = plane_approved.audit_trail().by_tool("command.run")
    assert any(record.decision is AuditDecision.ALLOWED for record in approved_records)
    assert any(record.decision is AuditDecision.EXECUTED for record in approved_records)
    allowed_record = next(
        record
        for record in approved_records
        if record.decision is AuditDecision.ALLOWED
    )
    assert "human approved" in allowed_record.reasons
    stdout = str(factory_approved.outcomes[0].result.get("stdout", ""))
    assert "APPROVED-RUN" in stdout


def test_policy_denial_capability_mismatch_blocks(tmp_path: Path) -> None:
    plane = _plane(tmp_path)

    def denied_mode(assignment: AgentAssignment) -> Steps:
        del assignment
        return (
            ("evidence.record", {"claim_id": "AUTH-DENY", "evidence": {"probe": True}}),
        )

    graph = _graph(
        TaskSpec(
            id="denied",
            capability=SpecialistCapability.CODING,
            description="CODING agent attempts an EVIDENCE-only tool",
        )
    )
    factory = PlaneExecutorFactory(plane, denied_mode)
    with pytest.raises(OrchestrationBlocked) as excinfo:
        _run(
            Orchestrator(gateway=plane, config=_blocking_config()).run(
                graph=graph,
                executor_factory=factory,
                run_context=_context(),
            )
        )
    report = excinfo.value.report
    assert report.status == "BLOCKED"
    assert report.next_transition == "BLOCKED"
    assert report.failures[0].classification == "permission failure"
    assert factory.outcomes[0].decision is ToolDecision.DENY
    assert factory.outcomes[0].classification == "permission failure"
    denied = [
        record
        for record in plane.audit_trail().records()
        if record.decision is AuditDecision.DENIED
    ]
    assert denied
    assert any("capability mismatch" in record.reasons for record in denied)


def test_serialized_task_runs_alone_and_writes_safely(tmp_path: Path) -> None:
    plane = _plane(tmp_path)

    def shared_write_mode(assignment: AgentAssignment) -> Steps:
        return (
            (
                "file.write",
                {
                    "path": "shared.txt",
                    "content": f"writer {assignment.task_id}",
                },
            ),
        )

    graph = _graph(
        _coding_task("w1", "write shared.txt"),
        _coding_task("w2", "write shared.txt"),
        TaskSpec(
            id="serial",
            capability=SpecialistCapability.CODING,
            kind=TaskKind.SERIALIZED,
            description="write shared.txt once alone",
            depends_on=("w1", "w2"),
        ),
    )
    factory = PlaneExecutorFactory(plane, shared_write_mode)
    report = _run(
        Orchestrator(gateway=plane).run(
            graph=graph,
            executor_factory=factory,
            run_context=_context(),
        )
    )
    assert report.status == "COMPLETED"
    assert len(report.wave_summaries) == 2
    assert report.wave_summaries[0]["tasks"] == ["w1", "w2"]
    assert report.wave_summaries[1]["tasks"] == ["serial"]
    assert (tmp_path / "shared.txt").read_text(encoding="utf-8") == "writer serial"


def test_concurrency_not_serialized(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    tasks = tuple(
        _coding_task(
            f"parallel-{index}", f"independently write out/parallel-{index}.txt"
        )
        for index in range(3)
    )
    graph = _graph(*tasks)

    def parallel_write_mode(assignment: AgentAssignment) -> Steps:
        return (
            (
                "file.write",
                {
                    "path": f"out/{assignment.task_id}.txt",
                    "content": assignment.task_id,
                },
            ),
        )

    factory = PlaneExecutorFactory(plane, parallel_write_mode, gate_delay_seconds=0.05)
    report = _run(
        Orchestrator(gateway=plane).run(
            graph=graph,
            executor_factory=factory,
            run_context=_context(),
        )
    )
    assert report.status == "COMPLETED"
    first_wave = report.telemetry["waves"][0]
    assert first_wave["parallelism_high_water"] >= 2
    assert first_wave["max_cross_task_overlap_seconds"] > 0
    assert len(factory.seen_assignments) == 3

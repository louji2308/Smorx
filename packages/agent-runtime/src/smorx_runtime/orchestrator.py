"""Dependency-aware wave orchestration for the agent runtime.

The orchestrator plans work into waves from a :class:`TaskGraph`, dispatches one
:class:`AgentAssignment` per task through an :class:`AgentExecutorFactory`,
runs each wave through :class:`ParallelWaveEngine`, reconciles failures with a
bounded :class:`RetryPolicy` (retry -> replacement -> no-progress block),
detects contradictory evidence at COLLECTING, and emits an evidence-rich
:class:`OrchestrationReport`.

The workflow is an explicit state machine (see :data:`WORKFLOW_TRANSITIONS`).
``BLOCKED`` is a legitimate terminal state and is never reported as success:
when the workflow cannot finish, :meth:`Orchestrator.run` raises
:class:`OrchestrationBlocked` carrying the report so the failure is observable
evidence, not a silent default.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from smorx_runtime.agents import (
    AgentAssignment,
    AgentContext,
    AgentEvidence,
    AgentExecutorFactory,
    AgentFailure,
    AgentResult,
    AgentSpec,
    validate_result,
)
from smorx_runtime.capabilities import CAPABILITY_CATALOG
from smorx_runtime.graph import TaskGraph, TaskKind, TaskSpec
from smorx_runtime.loop_controls import LoopControls
from smorx_runtime.telemetry import ParallelismTelemetry
from smorx_runtime.toolgate import CapabilityGateway, MemoryGateway
from smorx_runtime.waves import ParallelWaveEngine, WaveRunRequest

SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"


class WorkflowPhase(StrEnum):
    """Orchestrator lifecycle phases."""

    IDLE = "IDLE"
    INSPECTING = "INSPECTING"
    PLANNING = "PLANNING"
    DISPATCHING = "DISPATCHING"
    EXECUTING = "EXECUTING"
    COLLECTING = "COLLECTING"
    RECONCILING = "RECONCILING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


#: Legal workflow transitions.  COMPLETED and BLOCKED are terminal.
WORKFLOW_TRANSITIONS: dict[WorkflowPhase, tuple[WorkflowPhase, ...]] = {
    WorkflowPhase.IDLE: (WorkflowPhase.INSPECTING,),
    WorkflowPhase.INSPECTING: (WorkflowPhase.PLANNING,),
    WorkflowPhase.PLANNING: (WorkflowPhase.DISPATCHING,),
    WorkflowPhase.DISPATCHING: (WorkflowPhase.EXECUTING,),
    WorkflowPhase.EXECUTING: (WorkflowPhase.COLLECTING,),
    WorkflowPhase.COLLECTING: (
        WorkflowPhase.RECONCILING,
        WorkflowPhase.COMPLETED,
        WorkflowPhase.BLOCKED,
    ),
    WorkflowPhase.RECONCILING: (
        WorkflowPhase.DISPATCHING,
        WorkflowPhase.COMPLETED,
        WorkflowPhase.BLOCKED,
    ),
    WorkflowPhase.COMPLETED: (),
    WorkflowPhase.BLOCKED: (),
}


class InvalidWorkflowTransition(Exception):
    """Raised when a workflow transition is not permitted by the contract."""

    def __init__(self, current: WorkflowPhase, attempted: WorkflowPhase) -> None:
        super().__init__(f"invalid workflow transition from {current.value} to {attempted.value}")
        self.current = current
        self.attempted = attempted


class OrchestrationBlocked(Exception):
    """Raised by ``run()`` when the workflow ends in ``BLOCKED``.

    Carries the :class:`OrchestrationReport` so the blocking evidence is
    preserved and inspectable rather than lost in an exception trace.
    """

    def __init__(self, report: OrchestrationReport) -> None:
        self.report = report
        super().__init__(f"orchestration ended BLOCKED (run {report.orchestrator_run_id})")


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded repair policy for failed tasks.

    ``failure_signature`` collapses a failure into a comparable string so
    materially equivalent repeated failures can be detected (no-progress rule,
    ``Requirements & Contract.md`` section 10).
    """

    max_retries_per_task: int = 1
    allow_replacement: bool = True
    no_progress_threshold: int = 2
    failure_signature: Callable[[AgentFailure], str] = lambda f: f"{f.classification}|{f.summary}"


@dataclass(frozen=True)
class OrchestratorConfig:
    """Runtime bounds for the orchestrator."""

    max_parallelism: int = 3
    per_agent_timeout_seconds: float = 30.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass(frozen=True)
class Contradiction:
    """A detected conflict or mismatch between collected results."""

    claim_id: str
    refs: tuple[str, ...]
    statements: tuple[str, ...]
    severity: str
    detected_at: datetime


@dataclass(frozen=True)
class OrchestrationDecision:
    """One auditable orchestrator decision."""

    decision_id: str
    kind: str
    detail: Mapping[str, object]


@dataclass(frozen=True)
class OrchestrationReport:
    """Evidence-rich terminal report of one orchestration run."""

    orchestrator_run_id: str
    status: Literal["COMPLETED", "BLOCKED"]
    phases: tuple[WorkflowPhase, ...]
    wave_summaries: tuple[dict[str, object], ...]
    decisions: tuple[OrchestrationDecision, ...]
    contradictions: tuple[Contradiction, ...]
    failures: tuple[AgentFailure, ...]
    evidence: tuple[AgentEvidence, ...]
    telemetry: Mapping[str, object]
    next_transition: str


@dataclass
class OrchestratorState:
    """Live execution ledger for the current orchestration run.

    Important state lives here (not only in logs) so the workflow can be
    inspected, audited, and resumed at any point.
    """

    phase: WorkflowPhase = WorkflowPhase.IDLE
    active_wave_id: str = ""
    pending_tasks: list[str] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)
    task_dependencies: dict[str, frozenset[str]] = field(default_factory=dict)
    task_statuses: dict[str, str] = field(default_factory=dict)
    active_agents: dict[str, str] = field(default_factory=dict)
    completed_agents: list[str] = field(default_factory=list)
    agent_results: dict[str, AgentResult] = field(default_factory=dict)
    evidence: list[AgentEvidence] = field(default_factory=list)
    failures: list[AgentFailure] = field(default_factory=list)
    conflicts: list[Contradiction] = field(default_factory=list)
    decisions: list[OrchestrationDecision] = field(default_factory=list)
    phase_history: list[str] = field(default_factory=list)
    next_transition: str = ""


class Orchestrator:
    """Dependency-aware wave orchestrator with bounded repair and reporting."""

    def __init__(
        self,
        *,
        gateway: CapabilityGateway | None = None,
        config: OrchestratorConfig | None = None,
        loop_controls: LoopControls | None = None,
    ) -> None:
        self._gateway: CapabilityGateway = gateway if gateway is not None else MemoryGateway()
        effective_config = config if config is not None else OrchestratorConfig()
        timeout_seconds = effective_config.per_agent_timeout_seconds
        threshold = effective_config.retry.no_progress_threshold
        if loop_controls is not None:
            if timeout_seconds == 0:
                timeout_seconds = loop_controls.per_agent_timeout_seconds
            threshold = loop_controls.no_progress_threshold
        self._config = OrchestratorConfig(
            max_parallelism=effective_config.max_parallelism,
            per_agent_timeout_seconds=timeout_seconds,
            retry=RetryPolicy(
                max_retries_per_task=effective_config.retry.max_retries_per_task,
                allow_replacement=effective_config.retry.allow_replacement,
                no_progress_threshold=threshold,
                failure_signature=effective_config.retry.failure_signature,
            ),
        )
        self._timeout_seconds = timeout_seconds
        self._threshold = threshold
        self._engine = ParallelWaveEngine(wave_timeout_seconds=self._timeout_seconds)
        self._telemetry = ParallelismTelemetry()
        self._state = OrchestratorState()
        self._run_id = ""
        self._wave_seq = 0
        self._wave_summaries: list[dict[str, object]] = []
        self._run_counts: dict[str, int] = {}
        self._replaced: dict[str, int] = {}
        self._issued_assignments: dict[str, AgentAssignment] = {}

    @property
    def phase(self) -> WorkflowPhase:
        return self._state.phase

    @property
    def state(self) -> OrchestratorState:
        return self._state

    def transition(self, target: WorkflowPhase, *, reason: str = "") -> None:
        current = self._state.phase
        if target not in WORKFLOW_TRANSITIONS[current]:
            raise InvalidWorkflowTransition(current, target)
        del reason
        self._state.phase = target
        self._state.phase_history.append(target.value)

    def plan_waves(self, graph: TaskGraph) -> list[tuple[TaskSpec, ...]]:
        return graph.waves(completed=(), max_parallelism=self._config.max_parallelism)

    async def run(
        self,
        *,
        graph: TaskGraph,
        executor_factory: AgentExecutorFactory,
        run_context: AgentContext,
        assignment_decorator: Callable[[AgentAssignment], AgentAssignment] | None = None,
    ) -> OrchestrationReport:
        self._run_id = f"run-{uuid4().hex[:12]}"
        self._state = OrchestratorState()
        self._wave_summaries = []
        self._run_counts = {}
        self._replaced = {}
        self._wave_seq = 0
        self._issued_assignments = {}
        self._telemetry = ParallelismTelemetry()

        plan = self.plan_waves(graph)
        self._record_decision(
            "wave_planned",
            {"plan": [len(wave) for wave in plan], "run_id": self._run_id},
        )
        for wave in plan:
            for task in wave:
                self._state.task_dependencies[task.id] = frozenset(task.depends_on)
                self._state.pending_tasks.append(task.id)
                self._state.task_statuses[task.id] = "QUEUED"

        self.transition(WorkflowPhase.INSPECTING, reason="run context received")
        self.transition(WorkflowPhase.PLANNING, reason=f"{len(plan)} wave(s) planned")
        self.transition(WorkflowPhase.DISPATCHING, reason="orchestration begins")

        follow_ups: list[TaskSpec] = []
        wave_tasks: tuple[TaskSpec, ...]
        wave_index = 0
        last_signature: dict[str, str] = {}
        signature_consecutive: dict[str, int] = {}
        blocked = False
        block_reason = ""
        block_kind = "BLOCKED"
        block_mismatch = False

        while not blocked:
            if follow_ups:
                wave_tasks = (follow_ups.pop(0),)
            elif wave_index < len(plan):
                wave_tasks = plan[wave_index]
                wave_index += 1
            else:
                break

            self._ensure_dispatch_ready(upcoming=wave_tasks)
            wave_output, timed_out = await self._execute_wave(
                wave_tasks=wave_tasks,
                run_context=run_context,
                executor_factory=executor_factory,
                assignment_decorator=assignment_decorator,
            )
            self.transition(
                WorkflowPhase.COLLECTING,
                reason=f"wave {self._state.active_wave_id} collected",
            )

            failures_by_task = self._collect_wave(
                wave_tasks=wave_tasks,
                wave_output=wave_output,
                timed_out=timed_out,
            )

            failed_in_wave = [t.id for t in wave_tasks if t.id in failures_by_task]
            cancelled_in_wave = [
                t.id for t in wave_tasks if self._state.task_statuses.get(t.id) == "CANCELLED"
            ]
            wave_task_ids = {t.id for t in wave_tasks}
            self._wave_summaries.append(
                {
                    "wave_id": self._state.active_wave_id,
                    "status": ("FAILED" if failed_in_wave or cancelled_in_wave else "COMPLETED"),
                    "tasks": [t.id for t in wave_tasks],
                    "failures": [
                        f"{f.classification}: {f.summary}"
                        for task_id, f in failures_by_task.items()
                        if task_id in wave_task_ids
                    ],
                }
            )
            self._record_decision(
                "wave_completed",
                {
                    "wave_id": self._state.active_wave_id,
                    "tasks": [t.id for t in wave_tasks],
                    "failed": failed_in_wave,
                    "cancelled": cancelled_in_wave,
                },
            )

            staged_follow_ups: list[TaskSpec] = []
            for task in wave_tasks:
                failure = failures_by_task.get(task.id)
                if failure is None:
                    continue
                signature = self._config.retry.failure_signature(failure)
                consecutive = signature_consecutive.get(task.id, 0)
                if last_signature.get(task.id) == signature:
                    consecutive += 1
                else:
                    consecutive = 1
                last_signature[task.id] = signature
                signature_consecutive[task.id] = consecutive

                if consecutive >= self._threshold:
                    blocked = True
                    block_reason = (
                        f"no progress: {consecutive} consecutive identical failure "
                        f"signatures for task {task.id}"
                    )
                    block_kind = "no_progress_block"
                    block_mismatch = failure.classification == "mismatch"
                    self._record_decision(
                        "no_progress_block",
                        {
                            "task_id": task.id,
                            "signature": signature,
                            "consecutive": consecutive,
                            "threshold": self._threshold,
                        },
                    )
                    break

                runs = self._run_counts.get(task.id, 0)
                if runs <= self._config.retry.max_retries_per_task:
                    self._record_decision(
                        "retry",
                        {
                            "task_id": task.id,
                            "attempt": runs + 1,
                            "signature": signature,
                        },
                    )
                    staged_follow_ups.append(task)
                elif self._config.retry.allow_replacement and task.id not in self._replaced:
                    self._replaced[task.id] = 1
                    self._record_decision(
                        "replace_agent",
                        {
                            "task_id": task.id,
                            "replacement_weight": 2,
                            "agent_id": f"{task.id}-replacement1",
                        },
                    )
                    staged_follow_ups.append(task)
                else:
                    blocked = True
                    block_reason = (
                        f"task {task.id} failed after retries and replacement are exhausted"
                    )
                    block_kind = (
                        "human_review_block" if failure.classification == "mismatch" else "BLOCKED"
                    )
                    block_mismatch = failure.classification == "mismatch"
                    self._record_decision(
                        block_kind,
                        {"task_id": task.id, "signature": signature},
                    )
                    break

            if blocked:
                break
            if staged_follow_ups:
                follow_ups.extend(staged_follow_ups)
                self._record_decision(
                    "reconcile",
                    {
                        "retries": [t.id for t in staged_follow_ups],
                        "replaced": [t.id for t in staged_follow_ups if t.id in self._replaced],
                    },
                )
                continue

            if wave_index >= len(plan) and not follow_ups:
                self.transition(WorkflowPhase.COMPLETED, reason="all waves completed")
                self._state.next_transition = "COMPLETED"
                break

        if blocked:
            self._state.next_transition = "HUMAN_REVIEW" if block_mismatch else "BLOCKED"
            self.transition(WorkflowPhase.BLOCKED, reason=f"{block_kind}: {block_reason}")
            raise OrchestrationBlocked(self._build_report("BLOCKED"))

        return self._build_report("COMPLETED")

    def _ensure_dispatch_ready(self, *, upcoming: tuple[TaskSpec, ...]) -> None:
        if self._state.phase == WorkflowPhase.COLLECTING:
            self.transition(
                WorkflowPhase.RECONCILING,
                reason="reconciling collected evidence",
            )
            self.transition(WorkflowPhase.DISPATCHING, reason="dispatching next wave")
        elif self._state.phase == WorkflowPhase.RECONCILING:
            self.transition(WorkflowPhase.DISPATCHING, reason="dispatching next wave")
        if any(getattr(task, "kind", None) is TaskKind.RECONCILER for task in upcoming):
            self._record_decision(
                "reconcile",
                {"tasks": [t.id for t in upcoming], "kind": "reconciler"},
            )

    async def _execute_wave(
        self,
        *,
        wave_tasks: tuple[TaskSpec, ...],
        run_context: AgentContext,
        executor_factory: AgentExecutorFactory,
        assignment_decorator: Callable[[AgentAssignment], AgentAssignment] | None,
    ) -> tuple[object | None, bool]:
        self._wave_seq += 1
        wave_id = f"{self._run_id}-w{self._wave_seq}"
        self._state.active_wave_id = wave_id
        self._issued_assignments = {}

        assignments: dict[str, AgentAssignment] = {}
        executors = {}
        for task in wave_tasks:
            run_no = self._run_counts.get(task.id, 0)
            if task.id in self._replaced:
                weight = self._replaced[task.id] + 1
                agent_id = f"{task.id}-replacement{self._replaced[task.id]}"
            else:
                weight = 1
                agent_id = f"{task.id}-agent"
            capability = task.capability
            allowed_tools = tuple(CAPABILITY_CATALOG[capability].allowed_tool_prefixes)
            assignment = AgentAssignment(
                id=f"{self._run_id}:{task.id}:{run_no}",
                task_id=task.id,
                wave_id=wave_id,
                agent_id=agent_id,
                objective=task.description,
                capability=capability,
                context=run_context,
                inputs=dict(task.inputs),
                constraints=tuple(task.depends_on),
                allowed_tools=allowed_tools,
                expected_artifact="",
                timeout_seconds=self._timeout_seconds,
                created_at=datetime.now(UTC),
            )
            if assignment_decorator is not None:
                assignment = assignment_decorator(assignment)
            spec = AgentSpec(
                agent_id=agent_id,
                name=capability.value,
                capability=capability,
                replacement_weight=weight,
            )
            assignments[task.id] = assignment
            executors[task.id] = executor_factory.create(spec, allowed_tools=allowed_tools)
            self._issued_assignments[task.id] = assignment
            self._state.active_agents[task.id] = agent_id
            self._state.task_statuses[task.id] = "RUNNING"
            self._run_counts[task.id] = run_no + 1

        self.transition(
            WorkflowPhase.EXECUTING,
            reason=f"wave {wave_id} executing {len(wave_tasks)} task(s)",
        )
        request = WaveRunRequest(
            wave_id=wave_id,
            tasks=wave_tasks,
            assignments=assignments,
            executors=executors,
        )
        budget = self._timeout_seconds * max(1, len(wave_tasks)) + 2.0
        timed_out = False
        try:
            wave_output: object | None = await asyncio.wait_for(
                self._engine.run_wave(request), timeout=budget
            )
        except TimeoutError:
            wave_output = None
            timed_out = True
        except Exception as exc:
            wave_output = None
            self._record_decision(
                "reconcile",
                {"wave_id": wave_id, "error": str(exc), "kind": "wave_error"},
            )
        if self._engine.last_wave_telemetry is not None:
            self._telemetry.record_wave(self._engine.last_wave_telemetry)
        return wave_output, timed_out

    def _collect_wave(
        self,
        *,
        wave_tasks: tuple[TaskSpec, ...],
        wave_output: object | None,
        timed_out: bool,
    ) -> dict[str, AgentFailure]:
        """Collect, validate, and persist results for one wave.

        Returns the representative failure per failed task so the caller can
        drive the bounded retry/replacement policy.
        """
        obtained: dict[str, AgentResult] = {}
        engine_failures: dict[str, AgentFailure] = {}
        if wave_output is not None:
            results_map = getattr(wave_output, "task_results", None)
            if results_map:
                for task_id, result in dict(results_map).items():
                    if isinstance(result, AgentResult):
                        obtained[str(task_id)] = result
            failures_map = getattr(wave_output, "task_failures", None)
            if failures_map:
                for task_id, entry in dict(failures_map).items():
                    if isinstance(entry, AgentFailure):
                        engine_failures[str(task_id)] = entry
                    else:
                        engine_failures[str(task_id)] = self._make_failure(
                            classification=str(getattr(entry, "classification", "failed")),
                            summary=str(getattr(entry, "summary", "wave failure")),
                        )

        failures_by_task: dict[str, AgentFailure] = {}
        for task in wave_tasks:
            self._drop_pending(task.id)
            if self._state.task_statuses.get(task.id) not in ("QUEUED", "RUNNING"):
                continue

            if timed_out:
                failures_by_task[task.id] = self._make_failure(
                    classification="timeout",
                    summary="wave exceeded per-agent timeout budget",
                )
                self._mark_failed(task.id, failures_by_task[task.id])
                continue

            if task.id not in obtained:
                if task.id in engine_failures:
                    failures_by_task[task.id] = engine_failures[task.id]
                    self._mark_failed(task.id, engine_failures[task.id])
                else:
                    failures_by_task[task.id] = self._make_failure(
                        classification="no_result",
                        summary="no result produced for task",
                    )
                    self._mark_failed(task.id, failures_by_task[task.id])
                continue

            result = obtained[task.id]
            issued = self._issued_assignments.get(task.id)
            stale = issued is None or (
                str(getattr(result, "task_id", "")) != task.id
                or str(getattr(result, "assignment_id", "")) != issued.id
            )
            if stale:
                self._state.conflicts.append(
                    Contradiction(
                        claim_id="__stale_result__",
                        refs=(task.id,),
                        statements=(
                            f"result for task {task.id} carried task_id="
                            f"{getattr(result, 'task_id', '')!r} and assignment_id="
                            f"{getattr(result, 'assignment_id', '')!r}",
                        ),
                        severity="mismatch",
                        detected_at=datetime.now(UTC),
                    )
                )
                self._state.task_statuses[task.id] = "CANCELLED"
                continue

            if self._status_str(result) != SUCCEEDED:
                embedded = getattr(result, "failures", None)
                if embedded:
                    failures_by_task[task.id] = embedded[0]
                else:
                    failures_by_task[task.id] = self._make_failure(
                        classification="failed",
                        summary=str(getattr(result, "summary", "failed")),
                    )
                self._mark_failed(task.id, failures_by_task[task.id])
                continue

            issues = validate_result(result)
            if issues:
                self._state.conflicts.append(
                    Contradiction(
                        claim_id="__validation__",
                        refs=(task.id,),
                        statements=(issues[0],),
                        severity="mismatch",
                        detected_at=datetime.now(UTC),
                    )
                )
                failures_by_task[task.id] = self._make_failure(
                    classification="mismatch",
                    summary=f"result validation failed: {issues[0]}",
                )
                self._mark_failed(task.id, failures_by_task[task.id])
                continue

            self._mark_succeeded(task.id, result)

        self._detect_conflicts(wave_tasks=wave_tasks, obtained=obtained)
        return failures_by_task

    def _detect_conflicts(
        self,
        *,
        wave_tasks: tuple[TaskSpec, ...],
        obtained: dict[str, AgentResult],
    ) -> None:
        claim_groups: dict[str, list[tuple[str, AgentResult]]] = {}
        for task in wave_tasks:
            result = obtained.get(task.id)
            if result is None or self._state.task_statuses.get(task.id) == "CANCELLED":
                continue
            for claim_id in self._extract_claims(result):
                claim_groups.setdefault(claim_id, []).append((task.id, result))

        for claim_id, entries in claim_groups.items():
            if len(entries) < 2:
                continue
            first = entries[0][1]
            second = entries[1][1]
            first_succeeded = self._status_str(first) == SUCCEEDED
            second_succeeded = self._status_str(second) == SUCCEEDED
            if first_succeeded == second_succeeded and self._artifacts(first) == self._artifacts(
                second
            ):
                continue
            statements = tuple(
                getattr(result, "summary", "")
                for _task_id, result in entries
                if getattr(result, "summary", "")
            )
            if not statements:
                statements = tuple(getattr(result, "summary", "") for _task_id, result in entries)
            self._state.conflicts.append(
                Contradiction(
                    claim_id=claim_id,
                    refs=tuple(task_id for task_id, _ in entries),
                    statements=statements,
                    severity="conflict",
                    detected_at=datetime.now(UTC),
                )
            )

    def _mark_succeeded(self, task_id: str, result: AgentResult) -> None:
        self._state.task_statuses[task_id] = SUCCEEDED
        self._state.completed_tasks.append(task_id)
        self._state.agent_results[task_id] = result
        issued = self._issued_assignments.get(task_id)
        if issued is not None:
            self._state.completed_agents.append(issued.agent_id)
        if result.evidence:
            self._state.evidence.extend(result.evidence)
        else:
            self._state.evidence.append(self._evidence_from(result))

    def _mark_failed(self, task_id: str, failure: AgentFailure) -> None:
        self._state.task_statuses[task_id] = FAILED
        self._state.failures.append(failure)

    def _drop_pending(self, task_id: str) -> None:
        if task_id in self._state.pending_tasks:
            self._state.pending_tasks.remove(task_id)

    def _evidence_from(self, result: AgentResult) -> AgentEvidence:
        claims = self._extract_claims(result)
        return AgentEvidence(
            evidence_id=f"ev-{uuid4().hex[:12]}",
            source=f"task:{result.task_id}",
            timestamp=datetime.now(UTC),
            evidence_type="EXECUTION_RESULT",
            claim_id=claims[0] if claims else None,
            machine_result=self._artifacts(result),
        )

    @staticmethod
    def _extract_claims(result: AgentResult) -> list[str]:
        refs: list[str] = [str(claim) for claim in getattr(result, "claims", None) or ()]
        for key in ("claim_id", "claim"):
            value = getattr(result, "artifacts", {}).get(key)
            if value:
                refs.append(str(value))
        multi = getattr(result, "artifacts", {}).get("claim_ids")
        if multi:
            for value in multi:
                refs.append(str(value))
        return list(dict.fromkeys(refs))

    @staticmethod
    def _artifacts(result: AgentResult) -> dict[str, object]:
        raw = getattr(result, "artifacts", None)
        if isinstance(raw, Mapping):
            return {str(key): value for key, value in raw.items()}
        return {}

    @staticmethod
    def _status_str(result: AgentResult) -> str:
        status = getattr(result, "status", FAILED)
        value = getattr(status, "value", None)
        if value is None:
            value = status
        return str(value).upper()

    @staticmethod
    def _make_failure(*, classification: str, summary: str) -> AgentFailure:
        return AgentFailure(
            failure_id=f"f-{uuid4().hex[:12]}",
            classification=classification,
            summary=summary,
            observed_at=datetime.now(UTC),
        )

    def _record_decision(self, kind: str, detail: Mapping[str, object]) -> None:
        self._state.decisions.append(
            OrchestrationDecision(
                decision_id=f"dec-{uuid4().hex[:12]}",
                kind=kind,
                detail=dict(detail),
            )
        )

    def _build_report(self, status: Literal["COMPLETED", "BLOCKED"]) -> OrchestrationReport:
        return OrchestrationReport(
            orchestrator_run_id=self._run_id,
            status=status,
            phases=tuple(WorkflowPhase(phase) for phase in self._state.phase_history),
            wave_summaries=tuple(self._wave_summaries),
            decisions=tuple(self._state.decisions),
            contradictions=tuple(self._state.conflicts),
            failures=tuple(self._state.failures),
            evidence=tuple(self._state.evidence),
            telemetry=dict(self._telemetry.summary()),
            next_transition=self._state.next_transition,
        )

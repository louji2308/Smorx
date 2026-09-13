"""Unit tests for the parallel wave engine (real asyncio concurrency).

Executors are defined locally per test; the runtime package intentionally does
not ship a synthetic executor.  Every test drives the async engine through
``asyncio.run`` and asserts on real wall-clock evidence.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from smorx_runtime.agents import AgentAssignment, AgentContext, AgentResult
from smorx_runtime.capabilities import SpecialistCapability
from smorx_runtime.graph import TaskSpec
from smorx_runtime.waves import ParallelWaveEngine, WaveRunRequest, WaveStatus

_TASK_IDS = ("alpha", "beta", "gamma")


def _assignment(task_id: str, *, timeout_seconds: float = 30.0) -> AgentAssignment:
    return AgentAssignment(
        id=f"assignment-{task_id}",
        task_id=task_id,
        wave_id="test-wave",
        agent_id=f"agent-{task_id}",
        objective=f"complete {task_id}",
        capability=SpecialistCapability.CODING,
        context=AgentContext(
            run_id="test-run",
            phase="3",
            task_id=task_id,
            correlation_id=f"corr-{task_id}",
        ),
        inputs={},
        constraints=(),
        allowed_tools=("file.", "command.run", "test.run"),
        expected_artifact=f"artifact-{task_id}",
        timeout_seconds=timeout_seconds,
        created_at=datetime.now(UTC),
    )


def _task(task_id: str) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        capability=SpecialistCapability.CODING,
        description=f"task {task_id}",
    )


def _result(assignment: AgentAssignment) -> AgentResult:
    started_at = datetime.now(UTC)
    finished_at = datetime.now(UTC)
    return AgentResult(
        assignment_id=assignment.id,
        task_id=assignment.task_id,
        status="SUCCEEDED",
        started_at=started_at,
        finished_at=finished_at,
        summary=f"completed {assignment.task_id}",
        execution_references=(f"exec://{assignment.task_id}",),
    )


def test_wave_runs_tasks_concurrently() -> None:
    entry_events: list[str] = []

    class EntryExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            entry_events.append(assignment.task_id)
            await asyncio.sleep(0.2)
            return _result(assignment)

    async def scenario() -> dict[str, object]:
        tasks = tuple(_task(task_id) for task_id in _TASK_IDS)
        assignments = {task_id: _assignment(task_id) for task_id in _TASK_IDS}
        executors = {task_id: EntryExecutor() for task_id in _TASK_IDS}
        engine = ParallelWaveEngine()
        started = datetime.now(UTC)
        result = await engine.run_wave(
            WaveRunRequest(
                wave_id="parallel-wave",
                tasks=tasks,
                assignments=assignments,
                executors=executors,
            )
        )
        elapsed = (datetime.now(UTC) - started).total_seconds()
        return {
            "elapsed": elapsed,
            "entry_events": tuple(entry_events),
            "status": result.status,
            "task_results": tuple(result.task_results),
            "telemetry": engine.last_wave_telemetry,
        }

    outcome = asyncio.run(scenario())

    assert sorted(outcome["entry_events"]) == list(_TASK_IDS)
    assert outcome["status"] is WaveStatus.COMPLETED
    assert tuple(sorted(outcome["task_results"])) == _TASK_IDS
    assert outcome["elapsed"] < 0.5

    telemetry = outcome["telemetry"]
    assert telemetry is not None
    assert telemetry.parallelism_high_water == 3
    assert telemetry.max_cross_task_overlap_seconds > 0.0


def test_results_collected_per_task_id() -> None:
    class ReturningExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            return _result(assignment)

    async def scenario() -> dict[str, object]:
        tasks = tuple(_task(task_id) for task_id in _TASK_IDS)
        assignments = {task_id: _assignment(task_id) for task_id in _TASK_IDS}
        executors = {task_id: ReturningExecutor() for task_id in _TASK_IDS}
        result = await ParallelWaveEngine().run_wave(
            WaveRunRequest(
                wave_id="collect-wave",
                tasks=tasks,
                assignments=assignments,
                executors=executors,
            )
        )
        return {
            "status": result.status,
            "task_results": dict(result.task_results),
            "task_failures": dict(result.task_failures),
            "timings": result.timings,
            "wall_seconds": result.wall_seconds,
            "incomplete_agents": result.incomplete_agents,
        }

    outcome = asyncio.run(scenario())

    results = outcome["task_results"]
    assert sorted(results) == list(_TASK_IDS)
    assert all(value.task_id == key for key, value in results.items())
    assert outcome["status"] is WaveStatus.COMPLETED
    assert outcome["task_failures"] == {}
    assert len(outcome["timings"]) == 3
    assert outcome["wall_seconds"] >= 0.0
    assert outcome["incomplete_agents"] == ()


def test_per_agent_timeout_marks_task_timed_out() -> None:
    class SlowExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            await asyncio.sleep(1.0)
            return _result(assignment)

    class InstantExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            return _result(assignment)

    async def scenario() -> dict[str, object]:
        tasks = (_task("a"), _task("b"))
        assignments = {
            "a": _assignment("a", timeout_seconds=0.1),
            "b": _assignment("b"),
        }
        executors = {"a": SlowExecutor(), "b": InstantExecutor()}
        result = await ParallelWaveEngine().run_wave(
            WaveRunRequest(
                wave_id="timeout-wave",
                tasks=tasks,
                assignments=assignments,
                executors=executors,
            )
        )
        return {
            "status": result.status,
            "task_results": dict(result.task_results),
            "task_failures": dict(result.task_failures),
            "timings": {timing.task_id: timing for timing in result.timings},
            "incomplete_agents": result.incomplete_agents,
        }

    outcome = asyncio.run(scenario())

    assert outcome["status"] is WaveStatus.PARTIAL
    assert sorted(outcome["task_results"]) == ["b"]
    timing_a = outcome["timings"]["a"]
    assert timing_a.status == "TIMEOUT"
    assert timing_a.timed_out is True
    assert outcome["task_failures"]["a"].classification == "timeout"
    assert outcome["incomplete_agents"] == ("a",)


def test_executor_failure_is_classified_as_tool_failure() -> None:
    class FailingExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            raise RuntimeError("boom")

    class InstantExecutor:
        async def execute(self, assignment: AgentAssignment) -> AgentResult:
            return _result(assignment)

    async def scenario() -> dict[str, object]:
        tasks = (_task("a"), _task("b"))
        assignments = {"a": _assignment("a"), "b": _assignment("b")}
        executors = {"a": FailingExecutor(), "b": InstantExecutor()}
        result = await ParallelWaveEngine().run_wave(
            WaveRunRequest(
                wave_id="failure-wave",
                tasks=tasks,
                assignments=assignments,
                executors=executors,
            )
        )
        return {
            "status": result.status,
            "task_results": dict(result.task_results),
            "task_failures": dict(result.task_failures),
            "timings": {timing.task_id: timing for timing in result.timings},
        }

    outcome = asyncio.run(scenario())

    assert outcome["status"] is WaveStatus.PARTIAL
    assert sorted(outcome["task_results"]) == ["b"]
    failure = outcome["task_failures"]["a"]
    assert failure.classification == "tool failure"
    assert "RuntimeError" in failure.summary
    assert outcome["timings"]["a"].status == "FAILED"


def test_cancel_event_cancels_outstanding_tasks() -> None:
    async def scenario() -> dict[str, object]:
        blocker = asyncio.Event()

        class BlockingExecutor:
            async def execute(self, assignment: AgentAssignment) -> AgentResult:
                await blocker.wait()
                return _result(assignment)

        tasks = (_task("a"),)
        assignments = {"a": _assignment("a")}
        executors = {"a": BlockingExecutor()}
        cancel_event = asyncio.Event()
        engine = ParallelWaveEngine()
        started = datetime.now(UTC)

        async def set_cancel() -> None:
            await asyncio.sleep(0.1)
            cancel_event.set()

        cancel_setter = asyncio.create_task(set_cancel())
        result = await engine.run_wave(
            WaveRunRequest(
                wave_id="cancel-wave",
                tasks=tasks,
                assignments=assignments,
                executors=executors,
            ),
            cancel_event=cancel_event,
        )
        elapsed = (datetime.now(UTC) - started).total_seconds()
        await cancel_setter
        return {
            "status": result.status,
            "elapsed": elapsed,
            "timings": result.timings,
            "incomplete_agents": result.incomplete_agents,
        }

    outcome = asyncio.run(scenario())

    assert outcome["status"] is WaveStatus.CANCELLED
    assert outcome["elapsed"] < 2.0
    assert [timing.status for timing in outcome["timings"]] == ["CANCELLED"]
    assert outcome["incomplete_agents"] == ("a",)


def test_cancel_event_set_before_start_returns_cancelled() -> None:
    async def scenario() -> WaveStatus:
        cancel_event = asyncio.Event()
        cancel_event.set()
        result = await ParallelWaveEngine().run_wave(
            WaveRunRequest(
                wave_id="pre-cancelled",
                tasks=(_task("a"),),
                assignments={"a": _assignment("a")},
                executors={"a": _InstantExecutor()},
            ),
            cancel_event=cancel_event,
        )
        return result.status

    assert asyncio.run(scenario()) is WaveStatus.CANCELLED


def test_empty_wave_raises_value_error() -> None:
    async def scenario() -> None:
        with pytest.raises(ValueError):
            await ParallelWaveEngine().run_wave(
                WaveRunRequest(
                    wave_id="empty-wave",
                    tasks=(),
                    assignments={},
                    executors={},
                )
            )

    asyncio.run(scenario())


def test_missing_assignment_raises_value_error() -> None:
    async def scenario() -> None:
        with pytest.raises(ValueError):
            await ParallelWaveEngine().run_wave(
                WaveRunRequest(
                    wave_id="incomplete-wave",
                    tasks=(_task("a"),),
                    assignments={},
                    executors={},
                )
            )

    asyncio.run(scenario())


class _InstantExecutor:
    async def execute(self, assignment: AgentAssignment) -> AgentResult:
        return _result(assignment)

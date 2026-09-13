"""Parallel wave engine for the multi-agent orchestrator.

The engine executes every task of a :class:`WaveRunRequest` with real
``asyncio`` concurrency (``create_task`` + ``gather``), records per-task
:class:`TaskTiming` entries, classifies per-task failures, derives the wave
status, and computes :class:`WaveTelemetry` so the orchestrator can prove that
independent tasks actually ran in parallel (see :mod:`smorx_runtime.telemetry`).
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from smorx_runtime.agents import AgentAssignment, AgentExecutor, AgentFailure, AgentResult
from smorx_runtime.graph import TaskSpec
from smorx_runtime.telemetry import TaskTiming, WaveTelemetry, overlap_seconds

_INCOMPLETE_STATUSES = frozenset({"TIMEOUT", "CANCELLED"})


class WaveStatus(StrEnum):
    """Lifecycle status of one executed wave."""

    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class WaveResult:
    """Outcome of one executed wave with per-task results, failures and timings."""

    wave_id: str
    status: WaveStatus
    task_results: Mapping[str, AgentResult]
    task_failures: Mapping[str, AgentFailure]
    timings: tuple[TaskTiming, ...]
    started_at: datetime
    finished_at: datetime
    wall_seconds: float
    incomplete_agents: tuple[str, ...]


@dataclass(frozen=True)
class WaveRunRequest:
    """Everything required to execute one wave concurrently."""

    wave_id: str
    tasks: tuple[TaskSpec, ...]
    assignments: Mapping[str, AgentAssignment]
    executors: Mapping[str, AgentExecutor]


def _derive_status(
    results: Mapping[str, AgentResult],
    failures: Mapping[str, AgentFailure],
    cancelled: bool,
) -> WaveStatus:
    """Derive the wave status from observed task outcomes."""
    if cancelled:
        return WaveStatus.CANCELLED
    if not failures:
        return WaveStatus.COMPLETED
    if results:
        return WaveStatus.PARTIAL
    return WaveStatus.FAILED


def _summarize_timings(
    timings: tuple[TaskTiming, ...],
    wave_started_at: datetime,
    wave_finished_at: datetime,
) -> tuple[float, int, float, datetime, datetime]:
    """Compute wall time, parallelism high-water and max pairwise overlap."""
    if not timings:
        wall_seconds = (wave_finished_at - wave_started_at).total_seconds()
        return wall_seconds, 0, 0.0, wave_started_at, wave_finished_at
    window_start = min(timing.started_at for timing in timings)
    window_finish = max(timing.finished_at for timing in timings)
    wall_seconds = (window_finish - window_start).total_seconds()

    events: list[tuple[datetime, int]] = []
    for timing in timings:
        events.append((timing.started_at, 1))
        events.append((timing.finished_at, -1))
    events.sort(key=lambda event: (event[0], event[1]))
    active = 0
    high_water = 0
    for _, delta in events:
        active += delta
        if active > high_water:
            high_water = active

    max_overlap = 0.0
    for index, left in enumerate(timings):
        for right in timings[index + 1 :]:
            overlap = overlap_seconds(left, right)
            if overlap > max_overlap:
                max_overlap = overlap
    return wall_seconds, high_water, max_overlap, window_start, window_finish


class ParallelWaveEngine:
    """Executes all tasks of a wave concurrently and returns real telemetry."""

    def __init__(self, *, wave_timeout_seconds: float | None = None) -> None:
        self._wave_timeout_seconds = wave_timeout_seconds
        self.last_wave_telemetry: WaveTelemetry | None = None

    async def run_wave(
        self,
        request: WaveRunRequest,
        *,
        cancel_event: asyncio.Event | None = None,
    ) -> WaveResult:
        """Run every task in ``request`` concurrently and collect the results.

        Tasks start together via ``asyncio.gather``; per-task timeouts come
        from ``min(assignment.timeout_seconds, wave_timeout_seconds)``.  A
        raised :class:`asyncio.CancelledError` is only produced by the engine's
        own cancellation and is recorded as a ``CANCELLED`` timing.
        """
        if not request.tasks:
            raise ValueError("run_wave requires at least one task in the wave")
        missing = [
            task.id
            for task in request.tasks
            if task.id not in request.assignments or task.id not in request.executors
        ]
        if missing:
            raise ValueError(f"missing assignment or executor for tasks: {', '.join(missing)}")

        wave_started_at = datetime.now(UTC)
        if cancel_event is not None and cancel_event.is_set():
            wave_finished_at = datetime.now(UTC)
            return self._compose_result(
                request,
                WaveStatus.CANCELLED,
                {},
                {},
                (),
                wave_started_at,
                wave_finished_at,
            )

        results: dict[str, AgentResult] = {}
        failures: dict[str, AgentFailure] = {}
        timings: list[TaskTiming] = []

        async def run_task(task: TaskSpec) -> None:
            assignment = request.assignments[task.id]
            executor = request.executors[task.id]
            started_at = datetime.now(UTC)
            status = "SUCCEEDED"
            timed_out = False
            try:
                timeout = self._task_timeout(assignment)
                if math.isinf(timeout):
                    agent_result = await executor.execute(assignment)
                else:
                    agent_result = await asyncio.wait_for(
                        executor.execute(assignment), timeout=timeout
                    )
                results[task.id] = agent_result
            except TimeoutError:
                status = "TIMEOUT"
                timed_out = True
                failures[task.id] = self._failure(
                    task.id, "timeout", f"task {task.id} exceeded its timeout"
                )
            except asyncio.CancelledError:
                status = "CANCELLED"
            except Exception as exc:
                status = "FAILED"
                failures[task.id] = self._failure(
                    task.id, "tool failure", f"{type(exc).__name__}: {exc}"
                )
            finally:
                finished_at = datetime.now(UTC)
                timings.append(
                    TaskTiming(
                        task_id=task.id,
                        agent_id=assignment.agent_id,
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_seconds=(finished_at - started_at).total_seconds(),
                        status=status,
                        timed_out=timed_out,
                    )
                )

        task_futures = [
            asyncio.create_task(run_task(task), name=f"wave-{request.wave_id}:task-{task.id}")
            for task in request.tasks
        ]

        cancelled = False
        if cancel_event is None:
            await asyncio.gather(*task_futures, return_exceptions=True)
        else:
            cancel_future = asyncio.create_task(self._await_cancel(cancel_event))
            await asyncio.wait({cancel_future, *task_futures}, return_when=asyncio.FIRST_COMPLETED)
            if cancel_event.is_set():
                cancelled = True
                for future in task_futures:
                    if not future.done():
                        future.cancel()
            if not cancel_future.done():
                cancel_future.cancel()
            await asyncio.gather(*task_futures, return_exceptions=True)
            await asyncio.gather(cancel_future, return_exceptions=True)

        wave_finished_at = datetime.now(UTC)
        status = _derive_status(results, failures, cancelled)
        return self._compose_result(
            request,
            status,
            results,
            failures,
            tuple(timings),
            wave_started_at,
            wave_finished_at,
        )

    def _task_timeout(self, assignment: AgentAssignment) -> float:
        wave_timeout = self._wave_timeout_seconds
        if wave_timeout is None:
            return assignment.timeout_seconds
        return min(assignment.timeout_seconds, wave_timeout)

    def _failure(self, task_id: str, classification: str, summary: str) -> AgentFailure:
        return AgentFailure(
            failure_id=f"{task_id}:{classification}",
            classification=classification,
            summary=summary,
            observed_at=datetime.now(UTC),
        )

    @staticmethod
    async def _await_cancel(cancel_event: asyncio.Event) -> None:
        await cancel_event.wait()

    def _compose_result(
        self,
        request: WaveRunRequest,
        status: WaveStatus,
        results: Mapping[str, AgentResult],
        failures: Mapping[str, AgentFailure],
        timings: tuple[TaskTiming, ...],
        wave_started_at: datetime,
        wave_finished_at: datetime,
    ) -> WaveResult:
        wall_seconds, high_water, max_overlap, window_start, window_finish = _summarize_timings(
            timings, wave_started_at, wave_finished_at
        )
        self.last_wave_telemetry = WaveTelemetry(
            wave_id=request.wave_id,
            timings=timings,
            started_at=window_start,
            finished_at=window_finish,
            wall_seconds=wall_seconds,
            parallelism_high_water=high_water,
            max_cross_task_overlap_seconds=max_overlap,
        )
        incomplete_agents = tuple(
            timing.task_id for timing in timings if timing.status in _INCOMPLETE_STATUSES
        )
        return WaveResult(
            wave_id=request.wave_id,
            status=status,
            task_results=results,
            task_failures=failures,
            timings=timings,
            started_at=wave_started_at,
            finished_at=wave_finished_at,
            wall_seconds=wall_seconds,
            incomplete_agents=incomplete_agents,
        )

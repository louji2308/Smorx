"""Timing and parallelism telemetry for the parallel agent runtime.

Durings an execution phase the orchestrator assigns independent work to several
specialist sub-agents and expects real parallelism.  :class:`ParallelismTelemetry`
records the per-wave timing evidence so that concurrency can be *proved* rather
than asserted: :meth:`ParallelismTelemetry.prove_concurrency` only returns
``True`` when at least two involved tasks actually overlapped in wall-clock
time and the observed high-water mark was ``>= 2``.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TaskTiming:
    """Fine-grained timing record for one executed task."""

    task_id: str
    agent_id: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    status: str
    timed_out: bool = False


@dataclass(frozen=True)
class WaveTelemetry:
    """Aggregate, machine-readable telemetry for one wave run."""

    wave_id: str
    timings: tuple[TaskTiming, ...]
    started_at: datetime
    finished_at: datetime
    wall_seconds: float
    parallelism_high_water: int
    max_cross_task_overlap_seconds: float


def overlap_seconds(left: TaskTiming, right: TaskTiming) -> float:
    """Return the overlap of two task intervals in seconds, never negative.

    Intervals are half-open ``[start, finished_at)``: two tasks whose intervals
    merely touch at a single instant do **not** count as overlapping, so the
    result is ``0.0`` for adjacent non-overlapping tasks and strictly greater
    than ``0`` exactly when a positive overlap exists.
    """
    latest_start = max(left.started_at, right.started_at)
    earliest_finish = min(left.finished_at, right.finished_at)
    return max(0.0, (earliest_finish - latest_start).total_seconds())


class ParallelismTelemetry:
    """Append-only record of wave telemetry used to prove concurrency."""

    def __init__(self) -> None:
        self._waves: list[WaveTelemetry] = []

    def record_wave(self, wave: WaveTelemetry) -> None:
        """Append one completed wave's telemetry to the record."""
        self._waves.append(wave)

    def waves(self) -> tuple[WaveTelemetry, ...]:
        """All recorded wave telemetry entries, in record order."""
        return tuple(self._waves)

    def prove_concurrency(self, task_ids: Collection[str]) -> bool:
        """Whether the listed tasks demonstrably ran in parallel.

        ``True`` only when at least two of the listed tasks produced a positive
        overlap interval *and* the high-water mark observed across the
        involved waves was at least ``2``.
        """
        ids = set(task_ids)
        involved = [
            wave for wave in self._waves if any(timing.task_id in ids for timing in wave.timings)
        ]
        if not involved:
            return False
        if max(wave.parallelism_high_water for wave in involved) < 2:
            return False
        relevant = [timing for wave in involved for timing in wave.timings if timing.task_id in ids]
        for index, left in enumerate(relevant):
            for right in relevant[index + 1 :]:
                if overlap_seconds(left, right) > 0.0:
                    return True
        return False

    def summary(self) -> dict[str, object]:
        """Return a JSON-serializable summary of the recorded waves."""
        return {
            "wave_count": len(self._waves),
            "waves": [
                {
                    "wave_id": wave.wave_id,
                    "started_at": wave.started_at.isoformat(),
                    "finished_at": wave.finished_at.isoformat(),
                    "wall_seconds": wave.wall_seconds,
                    "parallelism_high_water": wave.parallelism_high_water,
                    "max_cross_task_overlap_seconds": wave.max_cross_task_overlap_seconds,
                    "task_count": len(wave.timings),
                    "tasks": [
                        {
                            "task_id": timing.task_id,
                            "agent_id": timing.agent_id,
                            "status": timing.status,
                            "duration_seconds": timing.duration_seconds,
                            "timed_out": timing.timed_out,
                        }
                        for timing in wave.timings
                    ],
                }
                for wave in self._waves
            ],
        }

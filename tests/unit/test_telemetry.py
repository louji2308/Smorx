"""Unit tests for timing and parallelism telemetry."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from smorx_runtime.telemetry import (
    ParallelismTelemetry,
    TaskTiming,
    WaveTelemetry,
    overlap_seconds,
)

_BASE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _timing(
    task_id: str,
    started_at: datetime,
    finished_at: datetime,
    *,
    status: str = "SUCCEEDED",
) -> TaskTiming:
    return TaskTiming(
        task_id=task_id,
        agent_id=f"agent-{task_id}",
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=(finished_at - started_at).total_seconds(),
        status=status,
    )


def _wave(
    wave_id: str, timings: tuple[TaskTiming, ...], *, high_water: int
) -> WaveTelemetry:
    started_at = min(timing.started_at for timing in timings)
    finished_at = max(timing.finished_at for timing in timings)
    return WaveTelemetry(
        wave_id=wave_id,
        timings=timings,
        started_at=started_at,
        finished_at=finished_at,
        wall_seconds=(finished_at - started_at).total_seconds(),
        parallelism_high_water=high_water,
        max_cross_task_overlap_seconds=0.0,
    )


def test_record_wave_stores_waves_in_order() -> None:
    telemetry = ParallelismTelemetry()
    wave_one = _wave(
        "w1", (_timing("a", _BASE, _BASE + timedelta(seconds=1)),), high_water=1
    )
    wave_two = _wave(
        "w2",
        (_timing("b", _BASE + timedelta(seconds=2), _BASE + timedelta(seconds=3)),),
        high_water=1,
    )
    telemetry.record_wave(wave_one)
    telemetry.record_wave(wave_two)

    waves = telemetry.waves()
    assert isinstance(waves, tuple)
    assert [wave.wave_id for wave in waves] == ["w1", "w2"]


def test_overlap_seconds_zero_for_adjacent_intervals() -> None:
    first = _timing("a", _BASE, _BASE + timedelta(seconds=1))
    second = _timing("b", _BASE + timedelta(seconds=1), _BASE + timedelta(seconds=2))
    assert overlap_seconds(first, second) == 0.0


def test_overlap_seconds_zero_for_disjoint_intervals() -> None:
    first = _timing("a", _BASE, _BASE + timedelta(seconds=1))
    second = _timing("b", _BASE + timedelta(seconds=5), _BASE + timedelta(seconds=6))
    assert overlap_seconds(first, second) == 0.0


def test_overlap_seconds_positive_for_overlapping_intervals() -> None:
    first = _timing("a", _BASE, _BASE + timedelta(seconds=2))
    second = _timing("b", _BASE + timedelta(seconds=1), _BASE + timedelta(seconds=3))
    assert overlap_seconds(first, second) == 1.0


def test_prove_concurrency_false_for_non_overlapping_tasks() -> None:
    timings = (
        _timing("a", _BASE, _BASE + timedelta(seconds=1)),
        _timing("b", _BASE + timedelta(seconds=2), _BASE + timedelta(seconds=3)),
    )
    telemetry = ParallelismTelemetry()
    telemetry.record_wave(_wave("w1", timings, high_water=1))
    assert telemetry.prove_concurrency(("a", "b")) is False


def test_prove_concurrency_true_for_overlapping_pair() -> None:
    timings = (
        _timing("a", _BASE, _BASE + timedelta(seconds=2)),
        _timing("b", _BASE + timedelta(seconds=1), _BASE + timedelta(seconds=3)),
    )
    telemetry = ParallelismTelemetry()
    telemetry.record_wave(_wave("w1", timings, high_water=2))
    assert telemetry.prove_concurrency(("a", "b")) is True


def test_prove_concurrency_gated_by_high_water() -> None:
    timings = (
        _timing("a", _BASE, _BASE + timedelta(seconds=2)),
        _timing("b", _BASE + timedelta(seconds=1), _BASE + timedelta(seconds=3)),
    )
    telemetry = ParallelismTelemetry()
    telemetry.record_wave(_wave("w1", timings, high_water=1))
    assert telemetry.prove_concurrency(("a", "b")) is False


def test_prove_concurrency_false_for_unknown_task_ids() -> None:
    telemetry = ParallelismTelemetry()
    telemetry.record_wave(
        _wave("w1", (_timing("a", _BASE, _BASE + timedelta(seconds=1)),), high_water=1)
    )
    assert telemetry.prove_concurrency(("ghost",)) is False


def test_summary_is_json_serializable() -> None:
    telemetry = ParallelismTelemetry()
    timings = (
        _timing("a", _BASE, _BASE + timedelta(seconds=1)),
        _timing("b", _BASE + timedelta(milliseconds=500), _BASE + timedelta(seconds=2)),
    )
    telemetry.record_wave(_wave("w1", timings, high_water=2))

    summary = telemetry.summary()
    payload = json.dumps(summary)

    assert isinstance(payload, str)
    assert summary["wave_count"] == 1
    wave_summary = summary["waves"][0]
    assert wave_summary["wave_id"] == "w1"
    assert wave_summary["parallelism_high_water"] == 2
    assert wave_summary["task_count"] == 2

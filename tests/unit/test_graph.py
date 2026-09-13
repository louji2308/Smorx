"""Unit tests for the dependency-aware task graph and wave planning."""

from __future__ import annotations

import pytest
from smorx_runtime.capabilities import SpecialistCapability
from smorx_runtime.graph import TaskGraph, TaskGraphError, TaskKind, TaskSpec

_INDEPENDENT = TaskKind.INDEPENDENT


def _task(
    task_id: str,
    *,
    kind: TaskKind = _INDEPENDENT,
    depends_on: tuple[str, ...] = (),
) -> TaskSpec:
    return TaskSpec(
        id=task_id,
        capability=SpecialistCapability.CODING,
        kind=kind,
        description=f"task {task_id}",
        depends_on=depends_on,
    )


def _ids(waves: list[tuple[TaskSpec, ...]]) -> list[list[str]]:
    return [[task.id for task in wave] for wave in waves]


def test_independent_tasks_all_ready_at_start() -> None:
    graph = TaskGraph()
    for task_id in ("a", "b", "c"):
        graph.add(_task(task_id))
    ready = graph.ready(completed=())
    assert sorted(task.id for task in ready) == ["a", "b", "c"]
    assert graph.remaining(completed=()) == graph.tasks()


def test_dependent_task_not_ready_until_dependency_completed() -> None:
    graph = TaskGraph()
    graph.add(_task("a"))
    graph.add(_task("b"))
    graph.add_dependency("b", "a")

    assert [task.id for task in graph.ready(())] == ["a"]
    assert [task.id for task in graph.ready(("a",))] == ["b"]
    assert graph.dependencies_of("b") == ("a",)


def test_cycle_detection_raises_task_graph_error() -> None:
    graph = TaskGraph()
    graph.add(_task("a"))
    graph.add(_task("b"))
    graph.add_dependency("a", "b")
    with pytest.raises(TaskGraphError):
        graph.add_dependency("b", "a")
    with pytest.raises(TaskGraphError):
        graph.add_dependency("a", "a")


def test_unknown_dependency_raises_task_graph_error() -> None:
    graph = TaskGraph()
    graph.add(_task("a"))
    with pytest.raises(TaskGraphError):
        graph.add_dependency("a", "missing")
    with pytest.raises(TaskGraphError):
        graph.add_dependency("missing", "a")


def test_duplicate_id_raises_task_graph_error() -> None:
    graph = TaskGraph()
    graph.add(_task("a"))
    with pytest.raises(TaskGraphError):
        graph.add(_task("a"))


def test_waves_three_independent_pack_in_one_parallel_wave() -> None:
    graph = TaskGraph()
    for task_id in ("a", "b", "c"):
        graph.add(_task(task_id))
    plan = graph.waves(completed=(), max_parallelism=3)
    assert _ids(plan) == [["a", "b", "c"]]


def test_waves_max_parallelism_one_serializes_independents() -> None:
    graph = TaskGraph()
    for task_id in ("a", "b", "c"):
        graph.add(_task(task_id))
    plan = graph.waves(completed=(), max_parallelism=1)
    assert _ids(plan) == [["a"], ["b"], ["c"]]


def test_waves_serialized_task_gets_own_single_task_wave() -> None:
    graph = TaskGraph()
    for task_id in ("a", "b", "c"):
        graph.add(_task(task_id))
    graph.add(_task("mutate", kind=TaskKind.SERIALIZED))

    plan = graph.waves(completed=(), max_parallelism=3)
    scheduled = sorted(task.id for wave in plan for task in wave)
    assert scheduled == ["a", "b", "c", "mutate"]
    assert len(plan) == 2
    for wave in plan:
        if any(task.id == "mutate" for task in wave):
            assert len(wave) == 1


def test_waves_dependent_chain_runs_in_order() -> None:
    graph = TaskGraph()
    graph.add(_task("a"))
    graph.add(_task("b", depends_on=("a",)))
    graph.add(_task("c", depends_on=("b",)))
    plan = graph.waves(completed=())
    assert _ids(plan) == [["a"], ["b"], ["c"]]


def test_waves_reconciler_runs_after_its_dependencies() -> None:
    graph = TaskGraph()
    for task_id in ("a", "b", "c"):
        graph.add(_task(task_id))
    graph.add(_task("merge", kind=TaskKind.RECONCILER, depends_on=("a", "b", "c")))
    plan = graph.waves(completed=())
    assert [sorted(wave) for wave in _ids(plan)] == [["a", "b", "c"], ["merge"]]


def test_waves_partial_completed_set_returns_unscheduled_remainder() -> None:
    graph = TaskGraph()
    graph.add(_task("a"))
    graph.add(_task("b", depends_on=("a",)))
    graph.add(_task("c", depends_on=("b",)))
    plan = graph.waves(completed=("a", "b"))
    assert _ids(plan) == [["c"]]


def test_waves_plan_is_deterministic() -> None:
    graph = TaskGraph()
    graph.add(_task("inspect"))
    for task_id in ("analyze-tests", "analyze-deps", "analyze-runtime"):
        graph.add(_task(task_id, depends_on=("inspect",)))
    graph.add(_task("merge", kind=TaskKind.RECONCILER, depends_on=(task_id,)))
    graph.add(_task("sandbox-mutate", kind=TaskKind.SERIALIZED, depends_on=("merge",)))

    first = _ids(graph.waves(()))
    second = _ids(graph.waves(()))
    assert first == second
    third = _ids(graph.waves((), max_parallelism=2))
    assert third == _ids(graph.waves((), max_parallelism=2))

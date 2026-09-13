"""Dependency-aware task graph for the parallel orchestrator.

The orchestrator decomposes a phase into :class:`TaskSpec` units and organizes
them into a :class:`TaskGraph`.  :meth:`TaskGraph.waves` layers the ready tasks
into deterministic execution waves; the :class:`TaskKind` of every task
controls how aggressively it may be packed with others:

* ``INDEPENDENT`` / ``DEPENDENT`` -- packed together up to ``max_parallelism``;
* ``RECONCILER`` -- joins a wave only once its dependencies are complete and is
  still subject to ``max_parallelism``;
* ``SERIALIZED`` -- a shared-mutation boundary that must never run concurrently
  with anything, so it is always emitted alone in its own single-task wave.

The layering is greedy and deterministic: candidate tasks are sorted by
``(kind priority, id)`` so the same graph and completed-set always produce the
same plan (``IMPLEMENTATION_PLAN.md`` phase 3.3).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType

from smorx_runtime.capabilities import SpecialistCapability


class TaskKind(StrEnum):
    """Execution kind of a task; controls how it is layered into waves."""

    INDEPENDENT = "INDEPENDENT"
    DEPENDENT = "DEPENDENT"
    RECONCILER = "RECONCILER"
    SERIALIZED = "SERIALIZED"


_TASK_KIND_PRIORITY: dict[TaskKind, int] = {member: index for index, member in enumerate(TaskKind)}


@dataclass(frozen=True)
class TaskSpec:
    """One unit of delegable work in the task graph."""

    id: str
    capability: SpecialistCapability
    kind: TaskKind = TaskKind.INDEPENDENT
    description: str = ""
    depends_on: tuple[str, ...] = ()
    timeout_seconds: float | None = None
    inputs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))


class TaskGraphError(ValueError):
    """Raised when a graph mutation would corrupt task scheduling."""


class TaskGraph:
    """Immutable-task registry with dependency checking and wave planning."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskSpec] = {}

    def add(self, task: TaskSpec) -> None:
        """Register ``task``; duplicate ids are rejected."""
        if task.id in self._tasks:
            raise TaskGraphError(f"duplicate task id: {task.id!r}")
        self._tasks[task.id] = task

    def add_dependency(self, task_id: str, dependency_id: str) -> None:
        """Declare that ``task_id`` depends on ``dependency_id``.

        Raises :class:`TaskGraphError` for unknown ids or whenever the edge
        would introduce a cycle (including a self-reference).
        """
        self._require_task(task_id)
        self._require_task(dependency_id)
        task = self._tasks[task_id]
        if dependency_id in task.depends_on:
            return
        if self._creates_cycle(task_id, dependency_id):
            raise TaskGraphError(
                f"dependency {task_id!r} -> {dependency_id!r} would create a cycle"
            )
        self._tasks[task_id] = replace(task, depends_on=(*task.depends_on, dependency_id))

    def tasks(self) -> tuple[TaskSpec, ...]:
        """All registered tasks in insertion order."""
        return tuple(self._tasks.values())

    def dependencies_of(self, task_id: str) -> tuple[str, ...]:
        """Direct dependency ids of ``task_id`` (unknown ids raise)."""
        self._require_task(task_id)
        return self._tasks[task_id].depends_on

    def has_task(self, task_id: str) -> bool:
        return task_id in self._tasks

    def ready(self, completed: Collection[str]) -> tuple[TaskSpec, ...]:
        """Tasks not in ``completed`` whose every dependency is completed."""
        done = set(completed)
        return tuple(
            task
            for task in self._tasks.values()
            if task.id not in done and all(dep in done for dep in task.depends_on)
        )

    def remaining(self, completed: Collection[str]) -> tuple[TaskSpec, ...]:
        """Tasks not yet present in ``completed``, in insertion order."""
        done = set(completed)
        return tuple(task for task in self._tasks.values() if task.id not in done)

    def waves(
        self,
        completed: Collection[str],
        max_parallelism: int | None = None,
    ) -> list[tuple[TaskSpec, ...]]:
        """Return the full deterministic wave plan from the given completed-set.

        Greedy layering: every wave collects all currently ready tasks.
        ``SERIALIZED`` tasks are always emitted alone; every other ready task
        is packed into waves of at most ``max_parallelism`` (``None`` =
        unlimited).  Candidates are sorted by ``(kind priority, id)`` so the
        plan is reproducible.
        """
        if max_parallelism is not None and max_parallelism < 1:
            raise TaskGraphError(f"max_parallelism must be >= 1, got {max_parallelism}")
        done: set[str] = set(completed)
        unscheduled = set(self._tasks) - done
        plan: list[tuple[TaskSpec, ...]] = []
        while unscheduled:
            candidates = [
                task
                for task in self._tasks.values()
                if task.id in unscheduled and all(dep in done for dep in task.depends_on)
            ]
            if not candidates:
                raise TaskGraphError(
                    "tasks remain unscheduled but none are ready; the graph contains "
                    "a cycle or references an unknown dependency"
                )
            candidates.sort(key=lambda task: (_TASK_KIND_PRIORITY[task.kind], task.id))
            serialized = [task for task in candidates if task.kind is TaskKind.SERIALIZED]
            non_serialized = [task for task in candidates if task.kind is not TaskKind.SERIALIZED]
            for task in serialized:
                plan.append((task,))
                unscheduled.discard(task.id)
                done.add(task.id)
            if serialized:
                continue
            capacity = len(non_serialized) if max_parallelism is None else max_parallelism
            for index in range(0, len(non_serialized), capacity):
                wave = tuple(non_serialized[index : index + capacity])
                plan.append(wave)
                for task in wave:
                    unscheduled.discard(task.id)
                    done.add(task.id)
        return plan

    def _require_task(self, task_id: str) -> None:
        if task_id not in self._tasks:
            raise TaskGraphError(f"unknown task id: {task_id!r}")

    def _creates_cycle(self, task_id: str, dependency_id: str) -> bool:
        """True when adding ``task_id -> dependency_id`` would close a cycle."""
        if task_id == dependency_id:
            return True
        seen: set[str] = set()
        stack = [dependency_id]
        while stack:
            current = stack.pop()
            current_task = self._tasks.get(current)
            if current_task is None:
                continue
            for dep in current_task.depends_on:
                if dep == task_id:
                    return True
                if dep not in seen:
                    seen.add(dep)
                    stack.append(dep)
        return False

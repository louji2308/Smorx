"""Phase 7.1 — Change Definition.

Normalizes a raw human request into a structured, validated change
definition and persists it as a real ``Task`` row plus the owning
``Change``. Incomplete requests are rejected with a
:class:`TaskDefinitionError` naming every missing requirement — the
module never silently infers critical requirements (master prompt §7.1).

The execution budget is part of the definition because Phase 8 loop
bounds are contract inputs, not implementation accidents.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from smorx_behavior.models import Change, Project, Repository, Task
from smorx_behavior.repo import base as repo_base
from sqlalchemy.orm import Session

__all__ = [
    "Budget",
    "ChangeDefinition",
    "ChangeDefinitionError",
    "ChangeDefinitionResult",
    "TaskDefinitionError",
    "define_change",
    "get_change_definition",
]

_REQUIRED_FIELDS: tuple[str, ...] = (
    "objective",
    "repository",
    "acceptance_criteria",
)
# Fields we refuse to infer. A request missing them is incomplete; we do
# not guess defaults for critical requirements (§7.1).
_UNINFERABLE_FIELDS: tuple[str, ...] = ("objective", "repository", "acceptance_criteria")

_VALID_PRIORITIES: frozenset[str] = frozenset({"LOW", "NORMAL", "HIGH", "CRITICAL"})


class ChangeDefinitionError(Exception):
    """Base error for change-definition failures."""


class TaskDefinitionError(ChangeDefinitionError):
    """Raised when a human request is incomplete or ambiguous.

    ``missing`` names every required field that was absent or empty so the
    caller can repair the request instead of guessing intent.
    """

    def __init__(self, message: str, *, missing: list[str]) -> None:
        super().__init__(message)
        self.missing = missing


@dataclass(frozen=True)
class Budget:
    """Execution budget handed to the Phase 8 loop-bounds controller."""

    max_iterations: int = 5
    max_runtime_seconds: int = 600
    max_commands: int = 40
    max_repair_attempts: int = 3
    no_progress_threshold: int = 2
    per_tool_timeout_seconds: int = 60
    per_agent_timeout_seconds: int = 300

    def as_dict(self) -> dict[str, int]:
        return {
            "max_iterations": self.max_iterations,
            "max_runtime_seconds": self.max_runtime_seconds,
            "max_commands": self.max_commands,
            "max_repair_attempts": self.max_repair_attempts,
            "no_progress_threshold": self.no_progress_threshold,
            "per_tool_timeout_seconds": self.per_tool_timeout_seconds,
            "per_agent_timeout_seconds": self.per_agent_timeout_seconds,
        }


@dataclass(frozen=True)
class ChangeDefinition:
    """Normalized view of the validated human request."""

    objective: str
    repository_name: str
    constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    priority: str
    budget: Budget

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "repository": self.repository_name,
            "constraints": list(self.constraints),
            "acceptance_criteria": list(self.acceptance_criteria),
            "priority": self.priority,
            "budget": self.budget.as_dict(),
        }


@dataclass(frozen=True)
class ChangeDefinitionResult:
    """The persisted Task/Change rows plus the normalized definition."""

    definition: ChangeDefinition
    task_id: uuid.UUID
    change_id: uuid.UUID
    repository_id: uuid.UUID
    task_row: Task
    change_row: Change


def _reject_incomplete(payload: dict[str, Any]) -> None:
    missing: list[str] = []
    for field_name in _REQUIRED_FIELDS:
        value = payload.get(field_name)
        if (
            value is None
            or (isinstance(value, str) and not value.strip())
            or (isinstance(value, (list, tuple)) and len(value) == 0)
        ):
            missing.append(field_name)
    if missing:
        uninferable = [name for name in missing if name in _UNINFERABLE_FIELDS]
        message = "incomplete human request; missing required fields: " + ", ".join(missing)
        if uninferable:
            message += f" ({', '.join(uninferable)} cannot be inferred and must be supplied)"
        raise TaskDefinitionError(message, missing=missing)


def _normalize_priority(raw: Any) -> str:
    priority = str(raw or "NORMAL").strip().upper()
    if priority not in _VALID_PRIORITIES:
        raise TaskDefinitionError(
            f"invalid priority {priority!r}; expected one of {sorted(_VALID_PRIORITIES)}",
            missing=["priority"],
        )
    return priority


def _find_repository(session: Session, name: str) -> Repository:
    repository = session.query(Repository).filter(Repository.name == name).first()
    if repository is None:
        raise TaskDefinitionError(
            f"unknown repository {name!r}; the target repository must be registered "
            "before a change can be defined against it",
            missing=["repository"],
        )
    return repository


def define_change(
    session: Session,
    *,
    project_id: uuid.UUID,
    request: dict[str, Any],
    requested_by: str | None = None,
) -> ChangeDefinitionResult:
    """Normalize and persist a human request.

    ``request`` keys: ``objective`` (required), ``repository`` (required,
    the registered repository slug), ``acceptance_criteria`` (required,
    non-empty list), ``constraints`` (optional list), ``priority``
    (optional, default ``NORMAL``), and ``budget`` (optional mapping of
    :class:`Budget` fields).

    Raises :class:`TaskDefinitionError` when the request is incomplete,
    the priority is invalid, or the repository is not registered. Raises
    :class:`ValueError` when the ``project_id`` has no project row.
    """
    if not isinstance(request, dict):
        raise TaskDefinitionError("request payload must be a mapping", missing=["objective"])

    payload = dict(request)
    _reject_incomplete(payload)

    objective = str(payload["objective"]).strip()
    repository_name = str(payload["repository"]).strip()
    raw_criteria = payload["acceptance_criteria"]
    criteria = tuple(str(item).strip() for item in raw_criteria if str(item).strip())
    if not criteria:
        raise TaskDefinitionError(
            "acceptance_criteria contained no usable entries", missing=["acceptance_criteria"]
        )
    constraints = tuple(
        str(item).strip() for item in (payload.get("constraints") or []) if str(item).strip()
    )
    priority = _normalize_priority(payload.get("priority"))

    raw_budget = payload.get("budget") or {}
    unknown_budget_keys = sorted(set(raw_budget) - set(Budget().as_dict()))
    if unknown_budget_keys:
        raise TaskDefinitionError(
            f"unknown budget keys: {', '.join(unknown_budget_keys)}", missing=[]
        )
    budget = Budget(**{**Budget().as_dict(), **raw_budget})  # type: ignore[arg-type]

    project = repo_base.get(session, Project, project_id)
    if project is None:
        raise ValueError(f"unknown project_id {project_id}")

    repository = _find_repository(session, repository_name)

    change = Change(
        repository_id=repository.id,
        title=objective[:400],
        description=objective,
        status="OPEN",
    )
    repo_base.save(session, change)

    task = Task(
        project_id=project.id,
        repository_id=repository.id,
        change_id=change.id,
        title=objective[:400],
        description=objective,
        priority=priority,
        requested_by=requested_by,
        acceptance_criteria=list(criteria),
    )
    repo_base.save(session, task)

    definition = ChangeDefinition(
        objective=objective,
        repository_name=repository_name,
        constraints=constraints,
        acceptance_criteria=criteria,
        priority=priority,
        budget=budget,
    )
    return ChangeDefinitionResult(
        definition=definition,
        task_id=task.id,
        change_id=change.id,
        repository_id=repository.id,
        task_row=task,
        change_row=change,
    )


def get_change_definition(session: Session, task_id: uuid.UUID) -> ChangeDefinition:
    """Rebuild the normalized definition view from the persisted Task row."""
    task = repo_base.get(session, Task, task_id)
    if task is None:
        raise TaskDefinitionError(f"unknown task_id {task_id}", missing=[])
    repository = (
        repo_base.get(session, Repository, task.repository_id) if task.repository_id else None
    )
    if repository is None:
        raise TaskDefinitionError(
            f"task {task_id} has no repository binding", missing=["repository"]
        )
    budget = Budget()
    return ChangeDefinition(
        objective=task.title,
        repository_name=repository.name,
        constraints=(),
        acceptance_criteria=tuple(task.acceptance_criteria or ()),
        priority=task.priority,
        budget=budget,
    )

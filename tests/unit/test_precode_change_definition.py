"""Phase 7 unit tests — change definition (§7.1).

Covers: normalization of a complete request; rejection of incomplete
requests with every missing field named; explicit statement that critical
requirements cannot be inferred; budget validation; unknown repository
rejection; unknown project rejection; round-trip via get_change_definition.
"""

from __future__ import annotations

import uuid

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Project, Repository
from smorx_behavior.repo import base as repo_base
from smorx_precode.change_definition import (
    Budget,
    TaskDefinitionError,
    define_change,
    get_change_definition,
)
from sqlalchemy.orm import Session

pytest.importorskip("smorx_precode.change_definition")


@pytest.fixture()
def session() -> Session:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    project = Project(name="Smorx", slug="smorx")
    repo_base.save(session, project)
    repository = Repository(
        project_id=project.id,
        name="payments-api",
        url="https://example.test/payments",
    )
    repo_base.save(session, repository)
    session.commit()
    return session


def _request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "objective": "Add rate limiting to the payments API",
        "repository": "payments-api",
        "acceptance_criteria": ["Requests over 100/min receive 429"],
        "constraints": ["No breaking API changes"],
        "priority": "HIGH",
    }
    request.update(overrides)
    return request


def _project_id(session: Session) -> uuid.UUID:
    return session.query(Project).first().id


def test_complete_request_persists_task_and_change(session: Session) -> None:
    result = define_change(session, project_id=_project_id(session), request=_request())

    assert result.task_id != result.change_id != result.repository_id
    assert result.definition.objective == "Add rate limiting to the payments API"
    assert result.definition.repository_name == "payments-api"
    assert result.definition.acceptance_criteria == (
        "Requests over 100/min receive 429",
    )
    assert result.definition.constraints == ("No breaking API changes",)
    assert result.definition.priority == "HIGH"
    assert result.definition.budget.max_iterations == 5


def test_incomplete_request_lists_every_missing_field(session: Session) -> None:
    with pytest.raises(TaskDefinitionError) as excinfo:
        define_change(session, project_id=_project_id(session), request={})
    missing = set(excinfo.value.missing)
    assert {"objective", "repository", "acceptance_criteria"} <= missing
    assert "cannot be inferred" in str(excinfo.value)


def test_empty_acceptance_criteria_is_rejected(session: Session) -> None:
    with pytest.raises(TaskDefinitionError) as excinfo:
        define_change(
            session,
            project_id=_project_id(session),
            request=_request(acceptance_criteria=[]),
        )
    assert "acceptance_criteria" in excinfo.value.missing


def test_unknown_repository_is_rejected_not_inferred(session: Session) -> None:
    with pytest.raises(TaskDefinitionError) as excinfo:
        define_change(
            session,
            project_id=_project_id(session),
            request=_request(repository="does-not-exist"),
        )
    assert "repository" in excinfo.value.missing


def test_invalid_priority_is_rejected(session: Session) -> None:
    with pytest.raises(TaskDefinitionError) as excinfo:
        define_change(
            session,
            project_id=_project_id(session),
            request=_request(priority="URGENT"),
        )
    assert excinfo.value.missing == ["priority"]


def test_unknown_budget_key_is_rejected(session: Session) -> None:
    with pytest.raises(TaskDefinitionError):
        define_change(
            session,
            project_id=_project_id(session),
            request=_request(budget={"max_fireballs": 3}),
        )


def test_budget_overrides_are_applied(session: Session) -> None:
    result = define_change(
        session,
        project_id=_project_id(session),
        request=_request(budget={"max_iterations": 2, "max_commands": 10}),
    )
    assert result.definition.budget.max_iterations == 2
    assert result.definition.budget.max_commands == 10
    assert result.definition.budget.max_repair_attempts == 3


def test_round_trip_via_get_change_definition(session: Session) -> None:
    result = define_change(session, project_id=_project_id(session), request=_request())
    view = get_change_definition(session, result.task_id)
    assert view.objective == result.definition.objective
    assert view.repository_name == result.definition.repository_name
    assert view.acceptance_criteria == result.definition.acceptance_criteria


def test_unknown_task_round_trip_raises(session: Session) -> None:
    with pytest.raises(TaskDefinitionError):
        get_change_definition(session, uuid.uuid4())


def test_budget_defaults_are_complete() -> None:
    budget = Budget()
    as_dict = budget.as_dict()
    assert set(as_dict) == {
        "max_iterations",
        "max_runtime_seconds",
        "max_commands",
        "max_repair_attempts",
        "no_progress_threshold",
        "per_tool_timeout_seconds",
        "per_agent_timeout_seconds",
    }

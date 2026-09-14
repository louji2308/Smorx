"""Shared deterministic test helpers for Phase 12 workflow tests.

Every fixture is built by explicit ORM calls over the in-memory engine.
No dependency on ``build_seed``; the full AUTH-017 graph is constructed
so tests can manipulate individual rows independently.
"""

from __future__ import annotations

from typing import Any

from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import (
    Behavior,
    Change,
    Ghost,
    Project,
    Repository,
    Task,
)
from sqlalchemy import event
from sqlalchemy.orm import Session


def make_engine() -> Any:
    """In-memory SQLite engine with FK enforcement enabled."""
    eng = create_sync_engine("sqlite:///:memory:")

    @event.listens_for(eng, "connect")
    def _enforce_fk(dbapi_conn: Any, _rec: Any) -> None:  # pragma: no cover
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    return eng


def make_session(engine: Any) -> Session:
    """Return a new ``Session`` bound to ``engine``."""
    return Session(engine)


def build_auth017(session: Session) -> dict[str, Any]:
    """Build the AUTH-017 governing graph (no Run/Task – caller creates those).

    Returns a dict with keys:
        project, repository, change, behaviors (dict[name, Behavior]),
        ghost_row (Ghost | None).
    """
    project = Project(name="Payments API", slug="payments-api", meta={})
    session.add(project)
    session.flush()

    repository = Repository(
        project=project,
        name="smorx/payments-api",
        url="https://github.com/smorx/payments-api.git",
        default_branch="main",
        meta={},
    )
    session.add(repository)
    session.flush()

    change = Change(
        repository=repository,
        external_id="184",
        commit_sha="a1b2c3d4e5f6",
        title="AUTH-017 refresh token forged-token hardening",
        description="Verify signature and issuer before tenant wiring.",
        status="OPEN",
    )
    session.add(change)
    session.flush()

    behaviors: dict[str, Behavior] = {}
    for name in ("tenant isolation", "authorization", "session behavior"):
        beh = Behavior(
            repository=repository,
            name=name,
            description=f"{name} behavior for AUTH-017.",
            category="SECURITY",
            protected=True,
            discovered_at=None,
        )
        session.add(beh)
        session.flush()
        behaviors[name] = beh

    ghost_row = Ghost(
        repository=repository,
        name="221",
        description="Replay scenario: forged refresh token accepted before fix.",
        hypothetical=True,
        status="CANDIDATE",
        payload={"scenario": "ghost-221"},
    )
    session.add(ghost_row)
    session.flush()

    return {
        "project": project,
        "repository": repository,
        "change": change,
        "behaviors": behaviors,
        "ghost_row": ghost_row,
    }


def make_task(
    session: Session,
    *,
    project: Project,
    change: Change,
    key: str = "AUTH-017",
) -> Task:
    """Create a task linked to ``change`` with deterministic defaults."""
    task = Task(
        project=project,
        repository_id=change.repository_id,
        change_id=change.id,
        title=f"AUTH-017 token refresh must reject forged requests ({key})",
        status="CREATED",
        priority="HIGH",
        acceptance_criteria=[
            "A forged refresh token returns 401",
            "Tenant isolation is preserved across refresh",
            "Replayed Ghost #221 scenario passes",
        ],
    )
    session.add(task)
    session.flush()
    return task


def make_run(session: Session, task: Task) -> Any:
    """Create a RUNNING run for ``task`` using the canonical AUTH-017 run token."""
    from smorx_behavior.models import Run, RunStatus
    from smorx_workflow.orchestrate import workflow_id

    run_token = "e2e/run/AUTH-017"
    run_id = workflow_id(run_token)
    existing = session.get(Run, run_id)
    if existing is not None:
        return existing
    run = Run(
        id=run_id,
        task_id=task.id,
        kind="AGENT",
        status=RunStatus.RUNNING.value,
        environment={"provider": "LOCAL", "runtime": "in-memory-sqlite"},
    )
    session.add(run)
    session.flush()
    return run

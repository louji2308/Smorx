# mypy: disable-error-code="import-untyped"

"""Persistence bootstrap helpers for the Phase 6 behavior adapter.

Owns the lifecycle of the behavioral SQLite database used by
``SqlAlchemyBehaviorAdapter``: sync engine creation, idempotent schema
bootstrap, deterministic demo seeding (only when empty), and the sync session
factory. All helpers reuse the persistence primitives shipped by
``smorx_behavior`` so the adapter never invents its own infrastructure
(AGENTS.md section 8).
"""

from __future__ import annotations

from pathlib import Path

from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Project
from smorx_behavior.seed.demo import build_seed
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

__all__ = [
    "DEFAULT_BEHAVIOR_DATABASE_URL",
    "behavior_session_factory",
    "create_behavior_engine",
    "ensure_behavior_schema",
    "seed_demo_scenario_if_empty",
]

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BEHAVIOR_DATABASE_URL = f"sqlite:///{(_REPO_ROOT / 'demo-seed.sqlite').as_posix()}"


def create_behavior_engine(database_url: str) -> Engine:
    """Build the sync SQLAlchemy engine for the behavioral database.

    ``sqlite+aiosqlite`` URLs are normalized to plain sqlite and SQLite
    connections allow cross-thread use by ``create_sync_engine``.
    """
    return create_sync_engine(database_url)


def ensure_behavior_schema(engine: Engine) -> None:
    """Create every behavioral table on ``engine`` idempotently."""
    Base.metadata.create_all(engine)


def seed_demo_scenario_if_empty(engine: Engine) -> None:
    """Seed the deterministic demo scenario only when no Project exists.

    ``build_seed`` is idempotent; the count guard keeps a database that
    already holds real projects untouched. The seed commits its own
    transaction.
    """
    with Session(engine) as session:
        project_count = int(session.scalar(select(func.count()).select_from(Project)) or 0)
        if project_count == 0:
            build_seed(session)


def behavior_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a sync session factory bound to ``engine``.

    ``expire_on_commit=False`` keeps hydrated instances usable after
    ``activate()`` commits its transition.
    """
    return sessionmaker(engine, expire_on_commit=False)

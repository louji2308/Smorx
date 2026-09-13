"""Alembic environment for the behavioral persistence layer.

The schema is the source of truth: ``target_metadata`` is ``Base.metadata``
and autogenerate compares the current database against it. ``DATABASE_URL``
is read from the environment (file SQLite fallback when unset) and a sync
engine drives migrations (``sqlite+aiosqlite`` URLs are normalized to
``sqlite://`` automatically).

ORM model tables register on ``Base.metadata`` by importing
``smorx_behavior.models`` (side-effect convention); the ``models`` package
must import every ORM model module so that autogenerate and the bootstrap
helper see the full schema.

Bootstrap helper: ``SMORX_BOOTSTRAP=create`` (``drop``) emits
``create_all`` (``drop_all``) against the target database and exits. This is
for development and evaluation only; real schema evolution flows through
revisions.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    """Resolve the migration target URL from ``DATABASE_URL``."""
    return os.environ.get("DATABASE_URL", "sqlite:///./smorx.db")


def run_bootstrap(action: str) -> None:
    """Create or drop every table in ``Base.metadata`` via the sync engine."""
    if action not in {"create", "drop"}:
        raise RuntimeError(f"'SMORX_BOOTSTRAP' must be 'create' or 'drop', got {action!r}")
    engine = create_sync_engine(database_url())
    with engine.begin() as connection:
        if action == "create":
            target_metadata.create_all(connection)
        else:
            target_metadata.drop_all(connection)


def run_migrations_offline() -> None:
    """Generate SQL statements without a live connection."""
    url = database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live sync connection."""
    engine = create_sync_engine(database_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


bootstrap_action = os.environ.get("SMORX_BOOTSTRAP")
if bootstrap_action:
    run_bootstrap(bootstrap_action)
elif context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

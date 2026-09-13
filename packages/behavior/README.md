# smorx-behavior

Behavioral data model and persistence layer for the Software Evolution
Intelligence System.

Phase 2 (`IMPLEMENTATION_PLAN.md`) foundation: portable SQLAlchemy 2.0
primitives and Alembic scaffolding. Product models are owned by the
behavioral model agent under `src/smorx_behavior/models/`.

## Public API

- `smorx_behavior.db.naming` — `CONVENTION` for constraint/index names.
- `smorx_behavior.db.base` — `Base` (DeclarativeBase) and `metadata`.
- `smorx_behavior.db.types` — `UTCDateTime`, `GUID`, `JSONType`.
- `smorx_behavior.db.mixins` — `UUIDPkMixin`, `TimestampMixin`.
- `smorx_behavior.db.settings` — `DBConfig` with `from_env()`.
- `smorx_behavior.db.engine` — `create_engine_from_config`,
  `session_factory`, `create_sync_engine`.

## Configuration

Copy `.env.example` and set `DATABASE_URL`. Default is a file-backed
SQLite database (`sqlite+aiosqlite:///./smorx.db`). PostgreSQL URLs
(`postgresql+asyncpg://...`) work with the same engine factories; pooling
hints are ignored for SQLite.

## Migrations

```text
cd packages/behavior
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

`migrations/env.py` reads `DATABASE_URL` (default file SQLite) and uses
`Base.metadata` for autogenerate comparison. `SMORX_BOOTSTRAP=create|drop`
emits `create_all`/`drop_all` against the target database for development
and evaluation only; real schema evolution flows through revisions.

## Tests

```text
python -m pytest tests/unit/test_db_infra.py -q
```
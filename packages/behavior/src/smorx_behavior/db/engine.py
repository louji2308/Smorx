"""Async and sync engine factories for the behavioral persistence layer."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from smorx_behavior.db.settings import DBConfig

__all__ = ["create_engine_from_config", "create_sync_engine", "session_factory"]


def _is_sqlite_memory(url: str) -> bool:
    return url.startswith("sqlite") and (
        "memory" in url or url.endswith("://") or url.endswith(":")
    )


def _async_sqlite_url(url: str) -> str:
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def _sync_sqlite_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


def create_engine_from_config(config: DBConfig) -> AsyncEngine:
    """Build an :class:`AsyncEngine` from a :class:`DBConfig`.

    SQLite URLs are normalized to the aiosqlite driver; pool-size hints are
    only applied to pool-capable backends. In-memory SQLite uses a static
    pool so one connection persists for the lifetime of the engine.
    """
    url = _async_sqlite_url(config.resolved_url())
    options: dict = {}
    if _is_sqlite_memory(url):
        options["poolclass"] = StaticPool
    elif not url.startswith("sqlite"):
        if config.pool_size is not None:
            options["pool_size"] = config.pool_size
        if config.max_overflow is not None:
            options["max_overflow"] = config.max_overflow
    return create_async_engine(url, **options)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to ``engine``.

    ``expire_on_commit=False`` keeps hydrated instances useful after commit.
    """
    return async_sessionmaker(engine, expire_on_commit=False)


def create_sync_engine(url: str) -> Engine:
    """Create a sync engine for tests and Alembic.

    ``sqlite+aiosqlite`` URLs are normalized to ``sqlite://``; in-memory
    SQLite uses a static pool.
    """
    sync_url = _sync_sqlite_url(url)
    options: dict = {}
    if sync_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if _is_sqlite_memory(sync_url):
            options["poolclass"] = StaticPool
    return create_engine(sync_url, **options)

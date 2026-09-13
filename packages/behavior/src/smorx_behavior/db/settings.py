"""Runtime configuration for the persistence layer.

This is a thin dataclass; no external settings library is used. Values may
embed credentials, so they are only ever read from the environment and are
never logged or printed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./smorx.db"

__all__ = ["DEFAULT_DATABASE_URL", "DBConfig"]


@dataclass(frozen=True, slots=True)
class DBConfig:
    """Connection configuration for the behavioral database."""

    database_url: str | None = None
    pool_size: int | None = None
    max_overflow: int | None = None

    def resolved_url(self) -> str:
        """Return the effective URL, substituting the SQLite fallback."""
        return self.database_url or DEFAULT_DATABASE_URL

    @classmethod
    def from_env(cls) -> DBConfig:
        """Build config from ``DATABASE_URL``, ``DB_POOL_SIZE``, ``DB_MAX_OVERFLOW``."""
        return cls(
            database_url=os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL,
            pool_size=_env_int("DB_POOL_SIZE"),
            max_overflow=_env_int("DB_MAX_OVERFLOW"),
        )


def _env_int(name: str) -> int | None:
    """Parse an optional environment variable as ``int``, ignoring empties."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None

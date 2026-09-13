"""Naming conventions for constraints and indexes.

Centralized so every table created against ``Base.metadata`` produces
deterministic, greppable constraint/index names on every backend
(SQLite, PostgreSQL, ...).
"""

from __future__ import annotations

CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "uq": "uc_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

__all__ = ["CONVENTION"]

"""Declarative base shared by every behavioral model."""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from smorx_behavior.db.naming import CONVENTION


class Base(DeclarativeBase):
    """Declarative base configured with the project naming conventions."""

    metadata = MetaData(naming_convention=CONVENTION)


metadata = Base.metadata

__all__ = ["Base", "metadata"]

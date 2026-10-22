"""Declarative base and shared column types."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB on PostgreSQL, generic JSON elsewhere (SQLite for local dev and tests).
JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def utcnow() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


def timestamp_column(**kwargs) -> Mapped[datetime]:
    """Create a timezone-aware timestamp column."""
    return mapped_column(DateTime(timezone=True), **kwargs)


def id_column() -> Mapped[str]:
    """Create the primary key column used by every entity."""
    return mapped_column(String(32), primary_key=True)


__all__ = [
    "Base",
    "JSONType",
    "id_column",
    "timestamp_column",
    "utcnow",
]

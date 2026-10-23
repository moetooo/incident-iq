"""Shared schema helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel

UTC = timezone.utc

T = TypeVar("T")


def to_iso(value: datetime | None) -> str | None:
    """Return an ISO 8601 UTC timestamp with a trailing ``Z``."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class Page(BaseModel, Generic[T]):
    """Generic page envelope used by every list endpoint."""

    items: list[T]
    total: int

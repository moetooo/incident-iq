"""Incident schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncidentStatus, SeverityLevel
from app.schemas.common import Page, to_iso


class IncidentCreate(BaseModel):
    """Request body for incident creation."""

    title: str = Field(min_length=1, max_length=200)
    service: str = Field(min_length=1, max_length=100)
    severity: SeverityLevel
    description: str = Field(default="", max_length=4000)


class IncidentRead(BaseModel):
    """Incident representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    service: str
    severity: SeverityLevel
    status: IncidentStatus
    description: str
    created_at: str
    updated_at: str
    resolved_at: str | None = None

    @classmethod
    def from_model(cls, incident) -> IncidentRead:
        """Build the response object from an ORM instance."""
        return cls(
            id=incident.id,
            title=incident.title,
            service=incident.service,
            severity=incident.severity,
            status=incident.status,
            description=incident.description,
            created_at=to_iso(incident.created_at),
            updated_at=to_iso(incident.updated_at),
            resolved_at=to_iso(incident.resolved_at),
        )


class IncidentList(Page[IncidentRead]):
    """List response for incidents."""

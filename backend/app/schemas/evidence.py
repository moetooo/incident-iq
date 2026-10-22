"""Evidence schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EvidenceType
from app.schemas.common import Page, to_iso


class EvidenceCollectRequest(BaseModel):
    """Request body for evidence collection."""

    scenario_id: str | None = Field(default=None, max_length=100)


class EvidenceRead(BaseModel):
    """Evidence representation returned by the API."""

    id: str
    incident_id: str
    type: EvidenceType
    source: str
    timestamp: str
    summary: str
    details: dict[str, Any]
    confidence: float

    @classmethod
    def from_model(cls, evidence) -> EvidenceRead:
        """Build the response object from an ORM instance."""
        return cls(
            id=evidence.id,
            incident_id=evidence.incident_id,
            type=evidence.type,
            source=evidence.source,
            timestamp=to_iso(evidence.timestamp),
            summary=evidence.summary,
            details=evidence.details or {},
            confidence=evidence.confidence,
        )


class EvidenceCollectResponse(BaseModel):
    """Response of the evidence collection endpoint."""

    incident_id: str
    collected: int
    stored: int
    items: list[EvidenceRead]
    warnings: list[str] = Field(default_factory=list)


class EvidenceList(Page[EvidenceRead]):
    """List response for evidence."""

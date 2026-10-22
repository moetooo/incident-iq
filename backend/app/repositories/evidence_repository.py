"""Evidence repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.models.evidence import Evidence


class EvidenceRepository:
    """Persistence operations for evidence."""

    def list_for_incident(self, session: Session, incident_id: str) -> list[Evidence]:
        """Return every evidence item of an incident, oldest first."""
        statement = (
            select(Evidence)
            .where(Evidence.incident_id == incident_id)
            .order_by(Evidence.timestamp.asc(), Evidence.id.asc())
        )
        return list(session.execute(statement).scalars().all())

    def existing_fingerprints(self, session: Session, incident_id: str) -> set[str]:
        """Return the fingerprints already stored for an incident."""
        statement = select(Evidence.fingerprint).where(Evidence.incident_id == incident_id)
        return {value for value in session.execute(statement).scalars().all()}

    def add(
        self,
        session: Session,
        *,
        incident_id: str,
        type: str,
        source: str,
        summary: str,
        details: dict[str, Any],
        confidence: float,
        fingerprint: str,
        timestamp: datetime,
    ) -> Evidence:
        """Store a single evidence item."""
        evidence = Evidence(
            id=new_id("evidence"),
            incident_id=incident_id,
            type=type,
            source=source,
            summary=summary,
            details=details,
            confidence=confidence,
            fingerprint=fingerprint,
            timestamp=timestamp,
        )
        session.add(evidence)
        session.flush()
        return evidence

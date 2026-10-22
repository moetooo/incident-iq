"""Incident repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db.base import utcnow
from app.models.enums import IncidentStatus, SeverityLevel
from app.models.incident import Incident


class IncidentRepository:
    """Persistence operations for incidents."""

    def create(
        self,
        session: Session,
        *,
        title: str,
        service: str,
        severity: SeverityLevel,
        description: str = "",
    ) -> Incident:
        """Create and return a new incident."""
        incident = Incident(
            id=new_id("incident"),
            title=title,
            service=service,
            severity=severity.value,
            description=description,
            status=IncidentStatus.TRIGGERED.value,
        )
        session.add(incident)
        session.flush()
        return incident

    def get(self, session: Session, incident_id: str) -> Incident | None:
        """Return the incident with the given id, if it exists."""
        return session.get(Incident, incident_id)

    def list(
        self,
        session: Session,
        *,
        status: str | None = None,
        severity: str | None = None,
        service: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Incident], int]:
        """Return a page of incidents and the total number of matches."""
        statement = select(Incident)
        count_statement = select(func.count()).select_from(Incident)

        if status:
            statement = statement.where(Incident.status == status)
            count_statement = count_statement.where(Incident.status == status)
        if severity:
            statement = statement.where(Incident.severity == severity)
            count_statement = count_statement.where(Incident.severity == severity)
        if service:
            statement = statement.where(Incident.service == service)
            count_statement = count_statement.where(Incident.service == service)

        total = session.execute(count_statement).scalar_one()
        statement = statement.order_by(Incident.created_at.desc(), Incident.id.desc())
        statement = statement.limit(limit).offset(offset)
        items = list(session.execute(statement).scalars().all())
        return items, int(total)

    def set_status(
        self,
        session: Session,
        incident: Incident,
        status: IncidentStatus,
        *,
        resolved: bool = False,
    ) -> Incident:
        """Update the incident status."""
        incident.status = status.value
        if resolved and incident.resolved_at is None:
            incident.resolved_at = utcnow()
        session.flush()
        return incident

"""Incident lifecycle service."""

from __future__ import annotations

from app.core.errors import NotFoundError
from app.models.enums import IncidentStatus
from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreate


class IncidentService:
    """Use cases for the incident lifecycle."""

    def __init__(self, incident_repository: IncidentRepository) -> None:
        self.incident_repository = incident_repository

    def create(self, session, request: IncidentCreate) -> Incident:
        """Create an incident in the ``triggered`` state."""
        incident = self.incident_repository.create(
            session,
            title=request.title,
            service=request.service,
            severity=request.severity,
            description=request.description,
        )
        return incident

    def get_or_raise(self, session, incident_id: str) -> Incident:
        """Return an incident or raise a not-found error."""
        incident = self.incident_repository.get(session, incident_id)
        if incident is None:
            raise NotFoundError(
                "Incident does not exist",
                code="INCIDENT_NOT_FOUND",
                details={"incident_id": incident_id},
            )
        return incident

    def list(
        self,
        session,
        *,
        status: str | None = None,
        severity: str | None = None,
        service: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Incident], int]:
        """Return a page of incidents."""
        return self.incident_repository.list(
            session,
            status=status,
            severity=severity,
            service=service,
            limit=limit,
            offset=offset,
        )

    def set_status(
        self,
        session,
        incident: Incident,
        status: IncidentStatus,
        *,
        resolved: bool = False,
    ) -> Incident:
        """Move an incident to a new status."""
        return self.incident_repository.set_status(session, incident, status, resolved=resolved)

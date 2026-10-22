"""Incident endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_incident_service
from app.db.session import get_db
from app.models.enums import IncidentStatus, SeverityLevel
from app.schemas.incident import IncidentCreate, IncidentList, IncidentRead
from app.services.incident_service import IncidentService

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=IncidentList, summary="List incidents")
def list_incidents(
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    severity: SeverityLevel | None = Query(default=None),
    service: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentList:
    """Return a page of incidents."""
    items, total = incident_service.list(
        session,
        status=status_filter.value if status_filter else None,
        severity=severity.value if severity else None,
        service=service,
        limit=limit,
        offset=offset,
    )
    return IncidentList(items=[IncidentRead.from_model(item) for item in items], total=total)


@router.post(
    "/incidents",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an incident",
)
def create_incident(
    payload: IncidentCreate,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentRead:
    """Create a new incident."""
    incident = incident_service.create(session, payload)
    session.commit()
    return IncidentRead.from_model(incident)


@router.get("/incidents/{incident_id}", response_model=IncidentRead, summary="Get an incident")
def get_incident(
    incident_id: str,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentRead:
    """Return a single incident."""
    incident = incident_service.get_or_raise(session, incident_id)
    return IncidentRead.from_model(incident)

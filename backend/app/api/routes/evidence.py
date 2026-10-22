"""Evidence endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_evidence_service, get_incident_service
from app.db.session import get_db
from app.schemas.evidence import (
    EvidenceCollectRequest,
    EvidenceCollectResponse,
    EvidenceList,
    EvidenceRead,
)
from app.services.evidence_service import EvidenceService
from app.services.incident_service import IncidentService

router = APIRouter(tags=["evidence"])


@router.post(
    "/incidents/{incident_id}/evidence",
    response_model=EvidenceCollectResponse,
    summary="Collect evidence for an incident",
)
def collect_evidence(
    incident_id: str,
    payload: EvidenceCollectRequest | None = None,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
    evidence_service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceCollectResponse:
    """Collect evidence from the simulator and persist it."""
    incident = incident_service.get_or_raise(session, incident_id)
    scenario_id = payload.scenario_id if payload else None
    result = evidence_service.collect(session, incident, scenario_id)
    session.commit()
    return EvidenceCollectResponse(
        incident_id=incident.id,
        collected=result.collected,
        stored=result.stored,
        items=[EvidenceRead.from_model(item) for item in result.items],
        warnings=result.warnings,
    )


@router.get(
    "/incidents/{incident_id}/evidence",
    response_model=EvidenceList,
    summary="List the evidence of an incident",
)
def list_evidence(
    incident_id: str,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
    evidence_service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceList:
    """Return every evidence item collected for an incident."""
    incident_service.get_or_raise(session, incident_id)
    items = evidence_service.list_for_incident(session, incident_id)
    return EvidenceList(items=[EvidenceRead.from_model(item) for item in items], total=len(items))

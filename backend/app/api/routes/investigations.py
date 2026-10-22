"""Investigation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    get_incident_service,
    get_investigation_repository,
    get_investigation_service,
)
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.repositories.investigation_repository import InvestigationRepository
from app.schemas.common import to_iso
from app.schemas.investigation import (
    HypothesisRead,
    InvestigateRequest,
    InvestigationList,
    InvestigationRead,
    RemediationProposal,
)
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService

router = APIRouter(tags=["investigations"])


@router.post(
    "/incidents/{incident_id}/investigate",
    response_model=InvestigationRead,
    summary="Run an investigation for an incident",
)
def investigate(
    incident_id: str,
    payload: InvestigateRequest | None = None,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
    investigation_service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationRead:
    """Collect evidence, analyse it and propose remediations."""
    incident = incident_service.get_or_raise(session, incident_id)
    scenario_id = payload.scenario_id if payload else None
    report = investigation_service.run(session, incident, scenario_id)
    session.commit()
    return report


@router.get(
    "/incidents/{incident_id}/investigations",
    response_model=InvestigationList,
    summary="List the investigations of an incident",
)
def list_investigations(
    incident_id: str,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
    repository: InvestigationRepository = Depends(get_investigation_repository),
) -> InvestigationList:
    """Return every investigation run for an incident, newest first."""
    incident_service.get_or_raise(session, incident_id)
    investigations = repository.list_for_incident(session, incident_id)
    items = [_to_read(repository, session, investigation) for investigation in investigations]
    return InvestigationList(items=items, total=len(items))


@router.get(
    "/incidents/{incident_id}/investigations/{investigation_id}",
    response_model=InvestigationRead,
    summary="Get an investigation report",
)
def get_investigation(
    incident_id: str,
    investigation_id: str,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
    repository: InvestigationRepository = Depends(get_investigation_repository),
) -> InvestigationRead:
    """Return a single investigation report."""
    incident_service.get_or_raise(session, incident_id)
    investigation = repository.get(session, investigation_id)
    if investigation is None or investigation.incident_id != incident_id:
        raise NotFoundError(
            "Investigation does not exist",
            code="INVESTIGATION_NOT_FOUND",
            details={"investigation_id": investigation_id},
        )
    return _to_read(repository, session, investigation)


def _to_read(
    repository: InvestigationRepository, session: Session, investigation
) -> InvestigationRead:
    """Build the response object for a stored investigation."""
    root_causes, alternatives = repository.hypotheses_for(session, investigation.id)

    def _hypothesis(row) -> HypothesisRead:
        return HypothesisRead(
            id=row.id,
            kind=row.kind,
            cause=row.cause,
            explanation=row.explanation,
            confidence=row.confidence,
            evidence_ids=list(row.evidence_ids or []),
            recommended_action_type=row.recommended_action_type,
        )

    return InvestigationRead(
        id=investigation.id,
        incident_id=investigation.incident_id,
        status=investigation.status,
        summary=investigation.summary,
        root_cause_hypotheses=[_hypothesis(row) for row in root_causes],
        alternative_hypotheses=[_hypothesis(row) for row in alternatives],
        recommended_checks=list(investigation.recommended_checks or []),
        proposed_remediations=[
            RemediationProposal(**proposal)
            for proposal in (investigation.proposed_remediations or [])
        ],
        knowledge_sources=list(investigation.knowledge_sources or []),
        evidence_ids=list(investigation.evidence_ids or []),
        llm_used=investigation.llm_used,
        provider=investigation.provider,
        model=investigation.model,
        warnings=list(investigation.warnings or []),
        created_at=to_iso(investigation.created_at),
    )

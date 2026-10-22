"""Remediation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_incident_service,
    get_remediation_repository,
    get_remediation_service,
    require_operator,
)
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.incident import Incident
from app.repositories.remediation_repository import RemediationRepository
from app.schemas.remediation import (
    RemediationCreate,
    RemediationDecision,
    RemediationList,
    RemediationRead,
)
from app.services.incident_service import IncidentService
from app.services.remediation_service import RemediationService

router = APIRouter(tags=["remediations"])


@router.post(
    "/incidents/{incident_id}/remediations",
    response_model=RemediationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a remediation proposal",
)
def create_remediation(
    incident_id: str,
    payload: RemediationCreate,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
    remediation_service: RemediationService = Depends(get_remediation_service),
) -> RemediationRead:
    """Create a remediation proposal. It is never executed by this endpoint."""
    incident = incident_service.get_or_raise(session, incident_id)
    remediation = remediation_service.create_proposal(
        session,
        incident,
        action=payload.action,
        parameters=payload.parameters,
        rationale=payload.rationale,
        actor="operator",
    )
    session.commit()
    return RemediationRead.from_model(remediation)


@router.get(
    "/incidents/{incident_id}/remediations",
    response_model=RemediationList,
    summary="List the remediations of an incident",
)
def list_remediations(
    incident_id: str,
    session: Session = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
    repository: RemediationRepository = Depends(get_remediation_repository),
) -> RemediationList:
    """Return every remediation of an incident, newest first."""
    incident_service.get_or_raise(session, incident_id)
    remediations = repository.list_for_incident(session, incident_id)
    return RemediationList(
        items=[RemediationRead.from_model(item) for item in remediations],
        total=len(remediations),
    )


@router.post(
    "/remediations/{remediation_id}/approve",
    response_model=RemediationRead,
    summary="Approve and execute a remediation",
)
def approve_remediation(
    remediation_id: str,
    payload: RemediationDecision | None = None,
    operator_id: str = Depends(require_operator),
    session: Session = Depends(get_db),
    remediation_service: RemediationService = Depends(get_remediation_service),
    repository: RemediationRepository = Depends(get_remediation_repository),
) -> RemediationRead:
    """Approve a remediation explicitly and dispatch the allowlisted action."""
    remediation = _get_or_raise(repository, session, remediation_id)
    remediation = remediation_service.approve(
        session,
        remediation,
        operator_id=operator_id,
        note=payload.note if payload else None,
    )
    session.commit()
    return RemediationRead.from_model(remediation, _incident_status(session, remediation))


@router.post(
    "/remediations/{remediation_id}/reject",
    response_model=RemediationRead,
    summary="Reject a remediation",
)
def reject_remediation(
    remediation_id: str,
    payload: RemediationDecision | None = None,
    operator_id: str = Depends(require_operator),
    session: Session = Depends(get_db),
    remediation_service: RemediationService = Depends(get_remediation_service),
    repository: RemediationRepository = Depends(get_remediation_repository),
) -> RemediationRead:
    """Reject a remediation. No action is dispatched."""
    remediation = _get_or_raise(repository, session, remediation_id)
    remediation = remediation_service.reject(
        session,
        remediation,
        operator_id=operator_id,
        note=payload.note if payload else None,
    )
    session.commit()
    return RemediationRead.from_model(remediation, _incident_status(session, remediation))


@router.post(
    "/remediations/{remediation_id}/execute",
    response_model=RemediationRead,
    summary="Execute an approved remediation",
)
def execute_remediation(
    remediation_id: str,
    session: Session = Depends(get_db),
    remediation_service: RemediationService = Depends(get_remediation_service),
    repository: RemediationRepository = Depends(get_remediation_repository),
) -> RemediationRead:
    """Execute an already approved remediation."""
    remediation = _get_or_raise(repository, session, remediation_id)
    remediation = remediation_service.execute(session, remediation, actor="operator")
    session.commit()
    return RemediationRead.from_model(remediation, _incident_status(session, remediation))


def _get_or_raise(
    repository: RemediationRepository, session: Session, remediation_id: str
):
    """Return a remediation or raise a not-found error."""
    remediation = repository.get(session, remediation_id)
    if remediation is None:
        raise NotFoundError(
            "Remediation does not exist",
            code="REMEDIATION_NOT_FOUND",
            details={"remediation_id": remediation_id},
        )
    return remediation


def _incident_status(session: Session, remediation) -> str | None:
    """Return the current status of the incident of a remediation."""
    incident = session.get(Incident, remediation.incident_id)
    return incident.status if incident is not None else None

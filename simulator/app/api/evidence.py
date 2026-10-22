from fastapi import APIRouter, Query
from typing import Optional

from app.models.evidence import EvidenceListResponse
from app.models.deployment import DeploymentListResponse
from app.models.metrics import SimulatorMetrics
from app.services.state_service import simulator_state_service

router = APIRouter(prefix="/internal", tags=["Internal Telemetry"])


@router.get("/evidence", response_model=EvidenceListResponse)
def get_evidence(
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    type: Optional[str] = Query(None, description="Filter by evidence type (log, metric, deployment, state)"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max items to return")
) -> EvidenceListResponse:
    """Retrieves generated evidence for investigation and RCA."""
    items = simulator_state_service.get_evidence(
        scenario_id=scenario_id,
        evidence_type=type,
        limit=limit
    )
    return EvidenceListResponse(items=items, total=len(items))


@router.get("/deployments", response_model=DeploymentListResponse)
def get_deployments() -> DeploymentListResponse:
    """Retrieves recent deployment history for change correlation."""
    items = simulator_state_service.get_deployments()
    return DeploymentListResponse(items=items, total=len(items))


@router.get("/metrics", response_model=SimulatorMetrics)
def get_metrics() -> SimulatorMetrics:
    """Retrieves current telemetry metrics snapshot."""
    return simulator_state_service.get_metrics()

from fastapi import APIRouter, HTTPException, Path
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.core.logging import logger
from app.models.scenario import (
    ScenarioId,
    ScenarioTriggerResponse,
    ResetResponse,
    ScenarioStatus,
)
from app.services.state_service import simulator_state_service

router = APIRouter(prefix="/demo/scenarios", tags=["Demo Scenarios"])


@router.get("", response_model=List[Dict[str, Any]])
def list_available_scenarios() -> List[Dict[str, Any]]:
    """List all available demo scenarios supported by the simulator."""
    current = simulator_state_service.get_current_scenario()
    return [
        {
            "id": ScenarioId.NORMAL.value,
            "title": "Healthy Payment API",
            "description": "Baseline healthy state with low latency and 0% errors",
            "is_active": current == ScenarioId.NORMAL
        },
        {
            "id": ScenarioId.DATABASE_FAILURE.value,
            "title": "Database Connection Pool Exhaustion",
            "description": "Database pool saturation (50/50) causing connection checkout timeouts",
            "is_active": current == ScenarioId.DATABASE_FAILURE
        },
        {
            "id": ScenarioId.PAYMENT_TIMEOUT.value,
            "title": "Payment Gateway Timeout",
            "description": "Downstream banking gateway timeouts causing p95 latency to exceed SLA",
            "is_active": current == ScenarioId.PAYMENT_TIMEOUT
        },
        {
            "id": ScenarioId.BAD_DEPLOYMENT.value,
            "title": "Bad Deployment Rollout",
            "description": "Rollout of v2.4.1 containing NullPointerException causing elevated 500 error rate",
            "is_active": current == ScenarioId.BAD_DEPLOYMENT
        }
    ]


@router.post("/{scenario_id}/trigger", response_model=ScenarioTriggerResponse)
def trigger_scenario(
    scenario_id: str = Path(..., description="Scenario ID to trigger (normal, database_failure, payment_timeout, bad_deployment)")
) -> ScenarioTriggerResponse:
    """Triggers a simulated incident scenario."""
    try:
        scenario_enum = ScenarioId(scenario_id)
    except ValueError:
        valid_ids = [s.value for s in ScenarioId]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario_id '{scenario_id}'. Valid scenarios: {valid_ids}"
        )

    status = simulator_state_service.trigger_scenario(scenario_enum)
    evidence_items = simulator_state_service.get_evidence()

    logger.info(
        f"Triggered scenario: {scenario_id}",
        extra={"extra_data": {"scenario": scenario_id, "healthy": status.is_healthy}}
    )

    return ScenarioTriggerResponse(
        status="ok",
        scenario_id=status.scenario_id,
        message=f"Scenario '{status.scenario_id.value}' triggered successfully",
        activated_at=status.activated_at,
        evidence_count_generated=len(evidence_items),
        health_status="healthy" if status.is_healthy else "degraded"
    )


@router.post("/reset", response_model=ResetResponse)
def reset_scenario() -> ResetResponse:
    """Restores the simulator to a known healthy baseline state."""
    simulator_state_service.reset()
    now_iso = datetime.now(timezone.utc).isoformat()
    logger.info("Simulator reset executed via /demo/scenarios/reset")
    return ResetResponse(
        status="ok",
        scenario=ScenarioId.NORMAL,
        message="Simulator reset to healthy state",
        reset_at=now_iso
    )
